"""Independent parser, packet and persistent-state boundary expectations."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from p4blo import arch, interp, ir, validator
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import LeanRunner, ProtocolError, compare_program, run_python
from p4blo.drt.state import snapshot
from p4blo.interp.values import Header
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.tutorial_firewall.tutorial_firewall import build
from tests.oracle import firewall as original
from tests.oracle.bmv2 import run as bmv2
from tests.programs.test_firewall import (
    SENTINEL_OUTPUT,
    Step,
    assert_original_observations,
    expected_state,
    forwarded,
    observation_plan,
    packet,
    step,
)

FRAME = packet(12346, flags=2, seq=1001)
assert len(FRAME) == 54


@dataclass(frozen=True)
class ParseExpectation:
    consumed: int
    accepted: bool
    error: str
    valid: tuple[bool, bool, bool]


def parse_expectation(length: int) -> ParseExpectation:
    assert 0 <= length <= 54
    consumed = 54 if length == 54 else 34 if length >= 34 else 14 if length >= 14 else 0
    return ParseExpectation(
        consumed,
        length == 54,
        "NoError" if length == 54 else "PacketTooShort",
        (length >= 14, length >= 34, length == 54),
    )


def truncated(length: int, inserted: set[int] | None = None) -> Step:
    inserted = set() if inserted is None else inserted
    data = FRAME[:length]
    normal = step(data if length >= 34 else FRAME, 1, 2, inserted)
    state = expected_state(inserted | ({12346} if length == 54 else set()))
    output = (2, forwarded(data, 2)) if length >= 34 else (0, data)
    return Step(Case(normal.case.entries, 1, data), (output,), state)


def persistence(length: int) -> list[Step]:
    """A malformed different flow must neither insert bits nor reset an established one."""
    assert length < 54
    return [
        step(packet(flags=2, seq=1000), 1, 2, {12345}),
        truncated(length, {12345}),
        step(packet(inbound=True, seq=1002), 2, 1, {12345}),
        step(packet(12346, inbound=True, seq=1003), 2, None, {12345}),
    ]


@pytest.mark.parametrize("length", range(55))
def test_atomic_parser_boundaries(length: int) -> None:
    loaded = arch.reference.load(build())
    metadata = loaded.metadata.zero()
    loaded.metadata.write(metadata, "ingress_port", 1)
    result = interp.run_parser(
        loaded.index, loaded.block("parser"), FRAME[:length], metadata, loaded.externs
    )
    expected = parse_expectation(length)
    assert result.accepted == expected.accepted
    assert result.error.name == expected.error
    assert result.consumed_bits == 8 * expected.consumed
    assert all(isinstance(value, Header) for value in result.headers.fields)
    assert (
        tuple(value.valid for value in result.headers.fields if isinstance(value, Header))
        == expected.valid
    )
    assert snapshot(loaded) == expected_state(set())


@pytest.mark.parametrize("length", range(55))
def test_unmodified_firewall_packet_and_state_boundaries(length: int) -> None:
    loaded = arch.reference.load(build())
    item = truncated(length)
    switch = arch.Switch(4)
    assert (
        tuple(switch.run(loaded, loaded.entries(item.case.entries), 1, item.case.packet))
        == item.outputs
    )
    assert switch.diagnostics == []
    assert snapshot(loaded) == item.state


@pytest.mark.parametrize("length", range(54))
def test_valid_malformed_valid_state_persists(length: int) -> None:
    loaded = arch.reference.load(build())
    for item in persistence(length):
        assert tuple(run_python(loaded, item.case, 4)) == item.outputs
        assert snapshot(loaded) == item.state


def member(base: pb.Expr, name: str) -> pb.Expr:
    return pb.Expr(member=pb.Member(base=base, field=name))


def parser_observer() -> pb.Program:
    """Instrument only the observer, never rewrite the parser under test."""
    program = build()
    original_parser = next(b for b in program.blocks if b.kind == pb.BLOCK_KIND_PARSER)
    parser_bytes = original_parser.SerializeToString(deterministic=True)
    field_names = ["short_error", "no_error", "ethernet_valid", "ipv4_valid", "tcp_valid"]
    probe = program.header_types.add(name="ParserProbe")
    for name in field_names:
        probe.fields.add(name=name, type=pb.Type(bits=8))
    headers = next(t for t in program.struct_types if t.name == program.headers)
    headers.fields.add(name="probe", type=pb.Type(header="ParserProbe"))
    metadata = next(t for t in program.struct_types if t.name == program.metadata)
    metadata.fields.add(name="parser_error", type=pb.Type(error=pb.ErrorType()))
    control = next(b for b in program.blocks if b.kind == pb.BLOCK_KIND_CONTROL)
    del control.body[:]
    del control.actions[:]
    del control.tables[:]
    del control.locals[:]
    target = pb.LValue(member=pb.LMember(base=pb.LValue(var="hdr"), field="probe"))
    control.body.add(set_valid=pb.SetValid(header=target))
    error = member(pb.Expr(var="meta"), "parser_error")
    conditions = [
        pb.Expr(
            binary=pb.Binary(
                op=pb.BINARY_OP_EQ, left=error, right=pb.Expr(literal=pb.Literal(error=name))
            )
        )
        for name in ["PacketTooShort", "NoError"]
    ] + [
        pb.Expr(is_valid=pb.IsValid(header=member(pb.Expr(var="hdr"), name)))
        for name in ["ethernet", "ipv4", "tcp"]
    ]
    for name, condition in zip(field_names, conditions, strict=True):
        value = pb.Expr(mux=pb.Mux(condition=condition))
        value.mux.then.literal.bits.CopyFrom(pb.BitsLiteral(width=8, value="1"))
        value.mux.otherwise.literal.bits.CopyFrom(pb.BitsLiteral(width=8, value="0"))
        control.body.add(
            assign=pb.Assign(
                target=pb.LValue(member=pb.LMember(base=target, field=name)), value=value
            )
        )
    deparser = next(b for b in program.blocks if b.kind == pb.BLOCK_KIND_DEPARSER)
    del deparser.body[:]
    deparser.body.add(emit=pb.Emit(value=member(pb.Expr(var="hdr"), "probe")))
    assert original_parser.SerializeToString(deterministic=True) == parser_bytes
    assert validator.validate(program) == []
    return program


def observer_output(length: int) -> bytes:
    expected = parse_expectation(length)
    return (
        bytes([int(not expected.accepted), int(expected.accepted), *expected.valid])
        + FRAME[expected.consumed : length]
    )


def compare_with_replay(
    program: pb.Program, cases: Sequence[Case], lean_binary: Path, profile: str
) -> None:
    """Retain the entire sequence before any narrower known-answer assertion."""
    try:
        report = compare_program(program, cases, 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        target = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        target.mkdir(parents=True, exist_ok=True)
        bundle = target / f"firewall-boundary-{profile}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    assert report.cases == len(cases)


def test_parser_observer_preserves_the_original_parser() -> None:
    original = build()
    observer = parser_observer()
    assert [b for b in original.blocks if b.kind == pb.BLOCK_KIND_PARSER] == [
        b for b in observer.blocks if b.kind == pb.BLOCK_KIND_PARSER
    ]
    loaded = arch.reference.load(observer)
    for length in range(55):
        assert run_python(loaded, Case(pb.Entries(), 1, FRAME[:length]), 4) == [
            (0, observer_output(length))
        ]
        assert snapshot(loaded) == expected_state(set())


def test_lean_agrees_on_parser_error_and_validity_boundaries(
    lean_binary: Path, tmp_path: Path
) -> None:
    program = parser_observer()
    cases = [Case(pb.Entries(), 1, FRAME[:length]) for length in range(55)]
    compare_with_replay(program, cases, lean_binary, "observer-all-cuts")
    path = tmp_path / "parser-observer.json"
    path.write_text(ir.dump_json(program))
    with LeanRunner([lean_binary], path, 4) as runner:
        for length in range(55):
            result = runner.run(Case(pb.Entries(), 1, FRAME[:length]))
            assert result.error is None and result.diagnostic is None
            assert result.outputs == ((0, observer_output(length)),)
            assert result.state == expected_state(set())


@pytest.mark.parametrize("length", range(55))
def test_lean_agrees_on_unmodified_boundary_state(
    lean_binary: Path, tmp_path: Path, length: int
) -> None:
    sequence = [truncated(length)] if length == 54 else [truncated(length), *persistence(length)]
    program = build()
    compare_with_replay(program, [item.case for item in sequence], lean_binary, f"cut-{length}")
    path = tmp_path / "firewall.json"
    path.write_text(ir.dump_json(program))
    with LeanRunner([lean_binary], path, 4) as runner:
        for item in sequence:
            result = runner.run(item.case)
            assert result.error is None and result.diagnostic is None
            assert result.outputs == item.outputs
            assert result.state == item.state


@pytest.fixture(scope="module")
def original_bmv2() -> tuple[str, bmv2.Compiled]:
    image = bmv2.default_image()
    unavailable = bmv2.unavailable(image)
    if unavailable:
        pytest.skip(unavailable)
    return image, bmv2.compile_program(image, original.source())


def check_original_bmv2(image: str, compiled: bmv2.Compiled, sequence: list[Step]) -> None:
    plan = observation_plan(sequence)
    request = plan.request(compiled)
    for phase in request["phases"]:
        phase["post_commands"] = [
            "register_read MyIngress.bloom_filter_1",
            "register_read MyIngress.bloom_filter_2",
        ]
        phase["completion_packet"] = {"port": 2, "data": SENTINEL_OUTPUT.hex()}
    reply = bmv2._driver(image, "replay", json.dumps(request))
    assert_original_observations(sequence, plan, reply)


@pytest.mark.parametrize("length", [0, 1, 13, 14, 15, 33, 34, 35, 47, 48, 49, 53, 54])
def test_original_boundaries_on_bmv2(original_bmv2: tuple[str, bmv2.Compiled], length: int) -> None:
    check_original_bmv2(*original_bmv2, [truncated(length)])


@pytest.mark.parametrize("length", [0, 13, 14, 33, 34, 48, 53])
def test_original_boundary_persistence_on_bmv2(
    original_bmv2: tuple[str, bmv2.Compiled], length: int
) -> None:
    check_original_bmv2(*original_bmv2, persistence(length))
