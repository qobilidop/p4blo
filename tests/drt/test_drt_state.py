"""State-only faults must be observable even when no packet changes."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from p4blo import arch, ir
from p4blo.arch.externs.counter import Counter
from p4blo.arch.externs.register import Register
from p4blo.drt.case import Case
from p4blo.drt.run import (
    Divergence,
    LeanRunner,
    Outcome,
    ProtocolError,
    compare_cases,
    parse_reply,
    python_outcome,
)
from p4blo.drt.state import Observation, decode, encode, snapshot
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]


def test_state_roundtrip_is_lossless_and_independent_of_object_order() -> None:
    state = (
        Observation("c", "counter", values=(2**100, 0)),
        Observation("r", "register", 16384, (2**16383, 0)),
        Observation("s", "checksum16"),
    )
    wire = encode(state)
    assert decode(dict(reversed(list(wire.items())))) == state
    assert decode(json.loads(json.dumps(wire))) == state


@pytest.mark.parametrize(
    "state",
    [
        None,
        [],
        {"r": {"kind": "unknown"}},
        {"r": {"kind": "register", "width": True, "values": ["0x0"]}},
        {"r": {"kind": "register", "width": 1, "values": ["0x2"]}},
        {"r": {"kind": "register", "width": 8, "values": [1]}},
        {"c": {"kind": "counter", "values": ["-0x1"]}},
        {"c": {"kind": "counter", "values": ["0x01"]}},
        {"c": {"kind": "counter", "values": ["0xA"]}},
        {"c": {"kind": "counter", "values": ["١"]}},
        {"c": {"kind": "checksum16", "ignored_state": [1]}},
    ],
)
def test_state_replies_are_checked_without_coercion(state: object) -> None:
    with pytest.raises(ProtocolError):
        parse_reply(json.dumps({"outputs": [], "state": state}))


def test_missing_state_cannot_make_an_old_comparator_pass() -> None:
    with pytest.raises(ProtocolError):
        parse_reply('{"outputs": []}')


def test_state_snapshot_is_not_aliased_to_live_cells() -> None:
    loaded = arch.reference.load(
        ir.load_text(ROOT / "tests/corpus/register_bounds/register_bounds.txtpb")
    )
    before = snapshot(loaded)
    register = next(e for e in loaded.externs.values() if isinstance(e, Register))
    register.cells[0] = Bits(register.width, 7)
    after = snapshot(loaded)
    assert before != after
    assert all(not any(item.values) for item in before)


def test_silent_counter_mutation_is_a_divergence() -> None:
    program = ir.load_text(ROOT / "tests/corpus/stateful/stateful.txtpb")
    loaded, mutant = arch.reference.load(program), arch.reference.load(program)

    def corrupt(case: Case):
        outcome = python_outcome(mutant, case, 4)
        # Corrupt a counter without changing any visible packet.
        counter = next(e for e in mutant.externs.values() if isinstance(e, Counter))
        counter.counts[0] += 1
        return replace(outcome, state=snapshot(mutant))

    report = compare_cases("stateful", loaded, [Case(pb.Entries(), 0, b"\x00")], 4, corrupt)
    assert len(report.divergences) == 1
    difference = report.divergences[0]
    assert difference.python.outputs == difference.lean.outputs
    assert difference.python.state != difference.lean.state


def test_state_difference_is_visible_even_when_errors_match() -> None:
    program = ir.load_text(ROOT / "tests/corpus/stateful/stateful.txtpb")
    loaded = arch.reference.load(program)
    outcome = python_outcome(loaded, Case(pb.Entries(), 99, b""), 4)
    assert outcome.error is not None
    assert not outcome.agrees_with(replace(outcome, state=()))


def test_state_only_diagnostics_show_values_without_decimal_limits() -> None:
    left = Outcome(outputs=(), state=(Observation("counter", "counter", values=(2**16384,)),))
    right = replace(left, state=(Observation("counter", "counter", values=(3,)),))
    difference = Divergence(2, Case(pb.Entries(), 0, b""), left, right)
    description = difference.describe()
    assert "case 2: Python no packet; Lean no packet" in description
    assert "state counter:" in description
    assert hex(2**16384) in description
    assert '"0x3"' in description
    missing = replace(difference, lean=replace(right, state=()))
    assert "Lean null" in missing.describe()


def wide_register_roundtrip(tmp_path: Path, command: list[str | Path]) -> None:
    program = ir.load_text(ROOT / "tests/corpus/register_bounds/register_bounds.txtpb")
    for field in program.header_types[0].fields:
        field.type.bits = 16384
    program.extern_types[0].methods[0].params[0].type.bits = 16384
    program.extern_types[0].methods[1].params[1].type.bits = 16384
    program.blocks[1].locals[0].type.bits = 16384
    loaded = arch.reference.load(program)  # Includes validation of the widened program.
    packet = bytes(2048) + b"\x80" + bytes(2047) + bytes(2048)
    program_json = tmp_path / "wide.json"
    program_json.write_text(ir.dump_json(program))
    with LeanRunner(command, program_json, 4) as runner:
        report = compare_cases("wide", loaded, [Case(pb.Entries(), 0, packet)], 4, runner.run)
    assert report.passed, report.divergences
    assert snapshot(loaded)[0].values[0].bit_length() == 16384


def test_wide_register_roundtrips_through_fake_peer(tmp_path: Path) -> None:
    wide_register_roundtrip(tmp_path, [sys.executable, "-m", "p4blo.drt.fake_lean"])


def test_lean_agrees_on_wide_register_state(tmp_path: Path, lean_binary: Path) -> None:
    wide_register_roundtrip(tmp_path, [lean_binary])
