"""State-only faults must be observable even when no packet changes."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.run import ProtocolError, compare_cases, parse_reply, python_outcome
from p4blo.drt.state import Observation, decode, encode, snapshot
from p4blo.externs.counter import Counter
from p4blo.externs.register import Register
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[1]


def test_state_roundtrip_is_lossless_and_independent_of_object_order() -> None:
    state = (
        Observation("c", "counter", values=(2**100, 0)),
        Observation("r", "register", 129, (2**128, 0)),
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
        {"r": {"kind": "register", "width": True, "values": ["0"]}},
        {"r": {"kind": "register", "width": 1, "values": ["2"]}},
        {"r": {"kind": "register", "width": 8, "values": [1]}},
        {"c": {"kind": "counter", "values": ["-1"]}},
        {"c": {"kind": "counter", "values": ["01"]}},
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
    loaded = arch.load(ir.load_text(ROOT / "corpus/register_bounds/register_bounds.txtpb"))
    before = snapshot(loaded)
    register = next(e for e in loaded.externs.values() if isinstance(e, Register))
    register.cells[0] = Bits(register.width, 7)
    after = snapshot(loaded)
    assert before != after
    assert all(not any(item.values) for item in before)


def test_silent_counter_mutation_is_a_divergence() -> None:
    program = ir.load_text(ROOT / "corpus/stateful/stateful.txtpb")
    loaded, mutant = arch.load(program), arch.load(program)

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
    program = ir.load_text(ROOT / "corpus/stateful/stateful.txtpb")
    loaded = arch.load(program)
    outcome = python_outcome(loaded, Case(pb.Entries(), 99, b""), 4)
    assert outcome.error is not None
    assert not outcome.agrees_with(replace(outcome, state=()))
