"""Real Lean execution conformance."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings

from p4blo.arch import v1model
from p4blo.drt.run import (
    python_outcome,
)
from p4blo.drt.stateful_programs import (
    UPDATE_OPS,
    WIDTHS,
    Condition,
    StatefulSpec,
    stateful_program,
)
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt_stateful_programs import (
    CONDITIONS,
    WRITE_ORDERS,
    boundary_fields,
    campaigns,
    cases_for,
    check_sequence,
)


@settings(max_examples=100, deadline=None, derandomize=True)
@given(campaign=campaigns())
def test_lean_agrees_on_shrinking_stateful_program_sequences(
    lean_binary: Path, campaign: tuple[StatefulSpec, list[tuple[int, int]]]
) -> None:
    spec, fields = campaign
    check_sequence(spec, fields, lean_binary)


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("op", UPDATE_OPS)
def test_lean_agrees_on_stateful_width_operator_and_write_order_boundaries(
    lean_binary: Path, width: int, op: pb.BinaryOp
) -> None:
    for write_order in WRITE_ORDERS:
        for read_after_write in (False, True):
            # Different capacities exercise register-OOB/counter-in-range and
            # the reverse, as well as the shared last/first valid boundaries.
            for register_size, counter_size in ((1, 4), (4, 1)):
                spec = StatefulSpec(
                    width,
                    register_size,
                    counter_size,
                    op,
                    write_order=write_order,
                    read_after_write=read_after_write,
                    count_updates=True,
                )
                check_sequence(spec, boundary_fields(spec), lean_binary)


@pytest.mark.parametrize("condition", CONDITIONS)
def test_lean_agrees_on_stateful_conditional_writes_and_counts(
    lean_binary: Path, condition: Condition
) -> None:
    for count_updates in (False, True):
        spec = StatefulSpec(
            8, 2, 2, pb.BINARY_OP_ADD, condition=condition, count_updates=count_updates
        )
        check_sequence(spec, [(0, 2), (0, 0), (0, 1), (0, 255), (0, 0), (1, 3)], lean_binary)


def test_lean_agrees_on_stateful_known_answer_sequence(lean_binary: Path) -> None:
    spec = StatefulSpec(8, 1, 1, pb.BINARY_OP_ADD)
    fields = [(0, 255), (0, 1), (1, 7), (0, 2)]
    check_sequence(spec, fields, lean_binary)
    loaded = v1model.load(stateful_program(spec))
    outcomes = [python_outcome(loaded, case, 4) for case in cases_for(spec, fields)]
    assert [o.outputs for o in outcomes] == [
        ((0, b"\x00\xff\xff"),),
        ((0, b"\x00\x01\x00"),),
        ((0, b"\x01\x07\x00"),),
        ((0, b"\x00\x02\x02"),),
    ]
    assert [(o.state[0].values, o.state[1].values) for o in outcomes] == [
        ((1,), (255,)),
        ((2,), (0,)),
        ((2,), (0,)),
        ((3,), (2,)),
    ]
