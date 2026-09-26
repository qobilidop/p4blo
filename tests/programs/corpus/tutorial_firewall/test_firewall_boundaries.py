"""Independent parser, packet and persistent-state boundary expectations."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo.arch import entry, v1model
from p4blo.arch import wire as arch_wire
from p4blo.drt.case import Case
from p4blo.drt.run import LeanRunner, run_python
from p4blo.drt.state import snapshot
from p4blo.interp.values import Header
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracles.bmv2 import run as bmv2
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build
from tests.support.firewall import (
    expected_state,
)
from tests.support.firewall_boundaries import (
    FRAME,
    check_original_bmv2,
    compare_with_replay,
    observer_output,
    parse_expectation,
    parser_observer,
    persistence,
    truncated,
)
from tests.support.firewall_boundaries import (
    original_bmv2 as original_bmv2,
)


@pytest.mark.parametrize("length", range(55))
def test_atomic_parser_boundaries(length: int) -> None:
    loaded = v1model.load(build())
    metadata = loaded.metadata.zero()
    loaded.metadata.write(metadata, "ingress_port", 1)
    result = entry.run_parser(
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
    loaded = v1model.load(build())
    item = truncated(length)
    switch = v1model.V1Model(4)
    assert (
        tuple(switch.run(loaded, loaded.entries(item.case.entries), 1, item.case.packet))
        == item.outputs
    )
    assert switch.diagnostics == []
    assert snapshot(loaded) == item.state


@pytest.mark.parametrize("length", range(54))
def test_valid_malformed_valid_state_persists(length: int) -> None:
    loaded = v1model.load(build())
    for item in persistence(length):
        assert tuple(run_python(loaded, item.case, 4)) == item.outputs
        assert snapshot(loaded) == item.state


def test_parser_observer_preserves_the_original_parser() -> None:
    original = build()
    observer = parser_observer()
    assert [b for b in original.blocks if b.kind == pb.BLOCK_KIND_PARSER] == [
        b for b in observer.blocks if b.kind == pb.BLOCK_KIND_PARSER
    ]
    loaded = v1model.load(observer)
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
    path.write_text(arch_wire.dump_json(program))
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
    path.write_text(arch_wire.dump_json(program))
    with LeanRunner([lean_binary], path, 4) as runner:
        for item in sequence:
            result = runner.run(item.case)
            assert result.error is None and result.diagnostic is None
            assert result.outputs == item.outputs
            assert result.state == item.state


@pytest.mark.parametrize("length", [0, 1, 13, 14, 15, 33, 34, 35, 47, 48, 49, 53, 54])
def test_original_boundaries_on_bmv2(original_bmv2: tuple[str, bmv2.Compiled], length: int) -> None:
    check_original_bmv2(*original_bmv2, [truncated(length)])


@pytest.mark.parametrize("length", [0, 13, 14, 33, 34, 48, 53])
def test_original_boundary_persistence_on_bmv2(
    original_bmv2: tuple[str, bmv2.Compiled], length: int
) -> None:
    check_original_bmv2(*original_bmv2, persistence(length))
