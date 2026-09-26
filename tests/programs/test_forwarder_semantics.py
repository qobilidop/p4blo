"""Whole-packet anchors and complete-state observations for the Python forwarder.

The generic Lean endpoint checks serialized programs against Python; known
answers and injected faults independently test the observable behavior.
"""

from __future__ import annotations

import dataclasses
import itertools
import os
from pathlib import Path
from typing import Any, cast

import pytest
from google.protobuf.message import Message

from p4blo import arch, stf
from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.forwarder.forwarder import build

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests/corpus/forwarder"
VECTORS = sorted(CORPUS.glob("*.stf"))


def assert_program_identity(program: apb.BlockAssembly) -> None:
    assert program == build(), "program differs from Python authoring"
    assert program == arch_wire.load_text(CORPUS / "forwarder.txtpb"), (
        "program differs from frozen golden"
    )
    assert validator.validate(program) == []


@pytest.fixture(scope="module")
def forwarder() -> apb.BlockAssembly:
    assert {"forward.stf", "miss.stf", "non_ipv4.stf", "lpm_precedence.stf", "too_short.stf"} <= {
        vector.name for vector in VECTORS
    }, "required forwarder STF vector is missing"
    program = arch_wire.load_text(CORPUS / "forwarder.txtpb")
    assert_program_identity(program)
    return program


def compare_and_save(
    program: apb.BlockAssembly, cases: list[Case], lean_binary: Path, label: str
) -> None:
    try:
        report = compare_program(program, cases, 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ROOT / ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"lean-forwarder-{label}.json"
        save(report, destination)
        pytest.fail(f"complete mismatch saved to {destination}: {report}")
    assert report.agreed == len(cases)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_lean_agrees_forwarder_stf(
    forwarder: apb.BlockAssembly, lean_binary: Path, vector: Path
) -> None:
    statements = stf.parse(vector.read_text())
    index = BoundIndex.build(forwarder)
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    # Public STF replay does installation/grouping. This pass collects input,
    # deliberately ignoring its expected-output failures; the next passes assert.
    stf.replay(index, statements, collect)
    assert cases, f"forwarder vector has no packet requests: {vector.name}"
    compare_and_save(forwarder, cases, lean_binary, vector.stem)
    loaded = v1model.load(forwarder)
    stf.assert_replay(index, statements, arch.stf_driver(v1model.V1Model(ports=4), loaded))


def edge_case(ttl: int) -> tuple[Case, list[tuple[int, bytes]]]:
    index = BoundIndex.build(arch_wire.load_text(CORPUS / "forwarder.txtpb"))
    installed = stf.parse(
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:0x000000000202, port:2)"
    )
    packet = bytes.fromhex("00000000010100000000000108004500001a00010000")
    packet += bytes([ttl]) + bytes.fromhex("1100000a0001010a000202deadbeefcafe")
    # Literal answers are independent of authored field accessors and either
    # interpreter. Source is old destination 0x101, NOT old source 1/new dst0x202.
    ttl_checksum = {0: "ff11a4cf", 1: "0011a3d0"}[ttl]
    expected = bytes.fromhex(
        "00000000020200000000010108004500001a00010000"
        + ttl_checksum
        + "0a0001010a000202deadbeefcafe"
    )
    return Case(stf.to_entries(index, installed), 0, packet), [(2, expected)]


@pytest.mark.parametrize("ttl", [0, 1])
def test_lean_agrees_forwarder_wrapping_ttl(
    forwarder: apb.BlockAssembly, lean_binary: Path, ttl: int
) -> None:
    case, expected = edge_case(ttl)
    compare_and_save(forwarder, [case], lean_binary, f"ttl-{ttl}")
    assert run_python(v1model.load(forwarder), case, 4) == expected


def test_lean_agrees_forwarder_detects_saturating_python_subtraction(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A real evaluator fault: save before checking output; replay live/restored."""
    original = expr.bits_binary
    hits = 0

    def saturating(op: int, left: Bits, right: Bits) -> Value:
        nonlocal hits
        if op == pb.BINARY_OP_SUB and left.width == 8 and left.value == 0 and right.value == 1:
            hits += 1
            return Bits(8, 0)
        return original(op, left, right)

    case, expected = edge_case(0)
    bundle = tmp_path / "forwarder-saturating-subtraction.json"
    with monkeypatch.context() as fault:
        fault.setattr(expr, "bits_binary", saturating)
        report = compare_program(forwarder, [case], 4, [lean_binary])
        save(report, bundle)
        assert hits == 1 and report.agreed == 0 and len(report.divergences) == 1
        assert report.protocol_error is None and report.both_errored == 0
        program, cases, ports, seed = replay.load(bundle)
        assert program == forwarder and cases == [case] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert hits == 2 and live.agreed == 0 and len(live.divergences) == 1
        divergence = live.divergences[0]
        assert divergence.lean.outputs == tuple(expected)
        assert divergence.python.outputs == tuple(edge_case(1)[1])
        for outcome in [divergence.python, divergence.lean]:
            assert outcome.error is None and outcome.diagnostic is None
        assert divergence.python.state == divergence.lean.state
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1 and restored.both_errored == 0


def test_lean_agrees_forwarder_checksum_after_drop(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dropped packet cannot reveal this stateless checksum call in its output.

    Retain a scoped execution observation, separately from packet agreement.
    """
    original = stmt.call_extern
    observed: list[tuple[int, int]] = []

    def observe(call: pb.CallExtern, env: Env) -> None:
        original(call, env)
        if env.block.name == "MyIngress" and call.instance == "csum":
            metadata = expr.expect_struct(env.read("meta"))
            headers = expr.expect_struct(env.read("hdr"))
            ipv4 = expr.expect_header(headers.fields[1])
            observed.append(
                (expr.expect_bits(metadata.fields[1]).value, expr.expect_bits(ipv4.fields[9]).value)
            )

    case, _ = edge_case(0)
    case = Case(pb.Entries(), case.ingress_port, case.packet)
    with monkeypatch.context() as spy:
        spy.setattr(stmt, "call_extern", observe)
        compare_and_save(forwarder, [case], lean_binary, "drop-checksum")
    assert observed == [(511, 0xA3D0)]


def freeze(value: Any) -> object:
    """Detached, exact-type contents of every field of this finite Env profile.

    Includes complete dataclasses/maps/protobufs, packet/emitter slots and
    extern-instance state; never retains a mutable object as the expected value.
    Unknown object forms fail closed instead of falling back to repr/equality.
    """
    kind = type(value)
    if value is None or kind in (str, bytes, int, bool, float):
        return kind, value
    if isinstance(value, Message):
        return kind, value.SerializeToString(deterministic=True)
    if isinstance(value, dict):
        return kind, tuple(sorted(((freeze(k), freeze(v)) for k, v in value.items()), key=repr))
    if isinstance(value, list | tuple):
        return kind, tuple(freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return kind, tuple(sorted((freeze(item) for item in value), key=repr))
    if dataclasses.is_dataclass(value):
        return kind, tuple(
            (field.name, freeze(getattr(value, field.name))) for field in dataclasses.fields(value)
        )
    slots = tuple(
        name
        for cls in kind.__mro__
        for name in getattr(cls, "__slots__", ())
        if name not in {"__dict__", "__weakref__"}
    )
    if slots or hasattr(value, "__dict__"):
        return (
            kind,
            tuple((name, freeze(getattr(value, name))) for name in slots),
            freeze(vars(value)) if hasattr(value, "__dict__") else None,
        )
    raise TypeError(f"unobserved runtime value {kind}")


def invalid_env(
    program: apb.BlockAssembly, valid: bool, sentinel: bool, port: int, ttl: int
) -> Env:
    loaded = v1model.load(program)
    installed = loaded.entries(edge_case(0)[0].entries)
    installed.default_actions[("MyIngress", "ipv4_lpm")] = pb.ActionCall(action="NoAction")
    loaded.externs["sentinel"] = Register(2, 8)
    loaded.externs["sentinel"].cells[:] = [Bits(8, 7), Bits(8, 9)]
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.value, emitter.width = 0x1234, 13
    env = Env.for_block(
        loaded.index,
        loaded.index.blocks["MyIngress"],
        loaded.externs,
        entries=installed,
        packet=packet,
        emitter=emitter,
        visits={("sentinel", "state"): 13},
    )
    env.vars["hdr"] = Struct(
        "headers",
        [
            Header("ethernet_t", valid, [Bits(48, 0x101), Bits(48, 1), Bits(16, 0x0800)]),
            Header(
                "ipv4_t",
                False,
                [
                    Bits(4, 4),
                    Bits(4, 5),
                    Bits(8, 17),
                    Bits(16, 26),
                    Bits(16, 1),
                    Bits(3, 0),
                    Bits(13, 0),
                    Bits(8, ttl),
                    Bits(8, 17),
                    Bits(16, 0x9876),
                    Bits(32, 0x0A000101),
                    Bits(32, 0x0A000202),
                ],
            ),
        ],
    )
    env.vars["meta"] = Struct("metadata", [Bits(9, 3), Bits(9, port)])
    # Retain unrelated boolean-state coverage independently of packet fate.
    env.vars["untouched_flag"] = sentinel
    return env


def observe_invalid_control(env: Env) -> None:
    before = freeze(env)
    stmt.execute(env.block.body, env)
    assert freeze(env) == before, "invalid IPv4 changed complete Python control state"


@pytest.mark.parametrize(
    "valid,sentinel,port,ttl",
    list(itertools.product([False, True], [False, True], [0, 3], [0, 1, 255])),
)
def test_python_forwarder_invalid_python_state(
    forwarder: apb.BlockAssembly, valid: bool, sentinel: bool, port: int, ttl: int
) -> None:
    """Complete-state known answers for invalid IPv4 profiles."""
    observe_invalid_control(invalid_env(forwarder, valid, sentinel, port, ttl))


@pytest.mark.parametrize("fault", ["ingress", "cursor-type", "entries", "index", "scope", "extern"])
def test_lean_agrees_forwarder_invalid_observer_kills_hidden_effect(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    original = stmt.execute_one
    hits = 0

    def corrupt(statement: pb.Stmt, env: Env) -> None:
        nonlocal hits
        original(statement, env)
        if env.block.name != "MyIngress" or not statement.HasField("conditional"):
            return
        if not statement.conditional.then[0].HasField("apply"):
            return
        headers = expr.expect_struct(env.read("hdr"))
        if expr.expect_header(headers.fields[1]).valid:
            return
        hits += 1
        if fault == "ingress":
            expr.expect_struct(env.read("meta")).fields[0] = Bits(9, 7)
        elif fault == "cursor-type":
            assert env.packet is not None
            cast(Any, env.packet).cursor = float(env.packet.cursor)
        elif fault == "entries":
            assert env.entries is not None
            env.entries.entries.clear()
        elif fault == "index":
            env.index.errors["NoError"] = 99
        elif fault == "scope":
            env.scope.actions.pop("NoAction")
        else:
            register = env.externs["sentinel"]
            assert isinstance(register, Register)
            register.cells[0] = Bits(8, 8)

    with monkeypatch.context() as patch:
        patch.setattr(stmt, "execute_one", corrupt)
        if fault == "ingress":
            # Confirm the actual reviewer-found survivor at the weaker public
            # packet boundary: it executes once and still emits exact ARP bytes.
            arp = bytes.fromhex(
                "ffffffffffff000000000001080600010800060400010000000000010a0001010000000000000a000202"
            )
            case = Case(pb.Entries(), 0, arp)
            report = compare_program(forwarder, [case], 4, [lean_binary])
            assert hits == 1 and report.passed and report.agreed == 1
            assert run_python(v1model.load(forwarder), case, 4) == [(0, arp)] and hits == 2
        prior = hits
        with pytest.raises(AssertionError, match="complete Python control state"):
            observe_invalid_control(invalid_env(forwarder, True, False, 3, 0))
        assert hits == prior + 1


def test_lean_agrees_forwarder_protocol_error_retains_inputs(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Transport-error handling unit test, not a semantic fault/Lean simulation."""
    case, _ = edge_case(0)
    report = compare_program(forwarder, [case], 4, [lean_binary])
    assert report.passed
    report.protocol_error = "injected transport failure after the actual request"

    def failed(*_args: object, **_kwargs: object) -> None:
        raise ProtocolError(report.protocol_error or "transport failure", report)

    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    monkeypatch.setattr("tests.programs.test_forwarder_semantics.compare_program", failed)
    with pytest.raises(pytest.fail.Exception, match="complete mismatch saved"):
        compare_and_save(forwarder, [case], lean_binary, "transport")
    program, cases, ports, seed = replay.load(tmp_path / "lean-forwarder-transport.json")
    assert program == forwarder and cases == [case] and (ports, seed) == (4, 0)
