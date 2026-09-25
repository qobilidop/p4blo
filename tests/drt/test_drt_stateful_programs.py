"""Whole sequences over generated, validated stateful switch programs.

Hypothesis shrinks typed configurations and width-bounded packet fields.
Program validity is checked by compare_program, never assumed or filtered.
Every request compares packets and abstract extern state from the same prefix.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import arch
from p4blo.drt.case import Case
from p4blo.drt.replay import load, save
from p4blo.drt.run import (
    Divergence,
    Outcome,
    ProtocolError,
    Report,
    compare_program,
    python_outcome,
    request_json,
)
from p4blo.drt.stateful_programs import (
    UPDATE_OPS,
    WIDTHS,
    Condition,
    StatefulSpec,
    WriteOrder,
    packet,
    stateful_program,
)
from p4blo.v0 import p4blo_pb2 as pb

CONDITIONS: tuple[Condition, ...] = ("always", "nonzero", "old_lt_data")
WRITE_ORDERS: tuple[WriteOrder, ...] = ("computed", "computed_then_data", "data_then_computed")


def boundary_fields(spec: StatefulSpec) -> list[tuple[int, int]]:
    maximum = (1 << spec.width) - 1
    return [
        (0, maximum),
        (0, 1),
        (0, maximum),
        (spec.register_size - 1, 0),
        (spec.register_size, maximum),
        (spec.counter_size - 1, 1),
        (spec.counter_size, maximum),
        (255, maximum),
        (0, 0),
    ]


def cases_for(spec: StatefulSpec, fields: list[tuple[int, int]]) -> list[Case]:
    return [
        Case(pb.Entries(), i % 4, packet(spec, index, data))
        for i, (index, data) in enumerate(fields)
    ]


def failure_path(report: Report, directory: Path) -> Path:
    """Hash the entire experiment so shrinking cannot overwrite other prefixes."""
    assert report.program_ir is not None
    digest = hashlib.sha256(report.program_ir.SerializeToString())
    for case in report.inputs:
        digest.update(request_json(case).encode())
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"stateful-{digest.hexdigest()[:24]}.json"


def check_sequence(spec: StatefulSpec, fields: list[tuple[int, int]], lean_binary: Path) -> None:
    cases = cases_for(spec, fields)
    try:
        report = compare_program(stateful_program(spec), cases, 4, [lean_binary])
    except ProtocolError as error:
        assert error.report is not None, "comparison must retain a replayable protocol failure"
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        bundle = failure_path(report, directory)
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    assert report.cases == len(cases)


@st.composite
def campaigns(draw: st.DrawFn) -> tuple[StatefulSpec, list[tuple[int, int]]]:
    spec = StatefulSpec(
        width=draw(st.sampled_from(WIDTHS)),
        register_size=draw(st.integers(1, 4)),
        counter_size=draw(st.integers(1, 4)),
        op=draw(st.sampled_from(UPDATE_OPS)),
        condition=draw(st.sampled_from(CONDITIONS)),
        write_order=draw(st.sampled_from(WRITE_ORDERS)),
        read_after_write=draw(st.booleans()),
        count_updates=draw(st.booleans()),
    )
    maximum = (1 << spec.width) - 1
    index = st.one_of(
        st.sampled_from([0, spec.register_size - 1, spec.register_size, spec.counter_size, 255]),
        st.integers(0, 255),
    )
    data = st.one_of(st.sampled_from([0, 1, maximum - 1, maximum]), st.integers(0, maximum))
    fields = draw(st.lists(st.tuples(index, data), min_size=2, max_size=16))
    return spec, fields


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
    loaded = arch.load(stateful_program(spec))
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


def test_stateful_replay_retains_program_and_every_request(tmp_path: Path) -> None:
    spec = StatefulSpec(16, 2, 3, pb.BINARY_OP_SUB_SAT, count_updates=True)
    cases = cases_for(spec, boundary_fields(spec))
    program = stateful_program(spec)
    report = Report(
        program.name, 0, 4, inputs=tuple(cases), program_ir=program, protocol_error="peer lost"
    )
    bundle = failure_path(report, tmp_path)
    save(report, bundle)
    restored_program, restored_cases, ports, seed = load(bundle)
    assert restored_program == program
    assert restored_cases == cases
    assert (ports, seed) == (4, 0)
    shorter = Report(program.name, 0, 4, inputs=tuple(cases[:-1]), program_ir=program)
    assert failure_path(shorter, tmp_path) != bundle


@pytest.mark.parametrize("protocol_failure", [False, True])
def test_stateful_failure_path_saves_the_complete_experiment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, protocol_failure: bool
) -> None:
    spec = StatefulSpec(8, 2, 3, pb.BINARY_OP_ADD)
    fields = [(0, 4), (0, 7), (2, 9)]

    def fail_comparison(
        program: pb.Program, cases: Sequence[Case], ports: int, _command: Sequence[str | Path]
    ) -> Report:
        report = Report(program.name, 0, ports, inputs=tuple(cases), program_ir=program, cases=2)
        if protocol_failure:
            report.protocol_error = "injected lost peer"
            raise ProtocolError(report.protocol_error, report)
        report.divergences.append(
            Divergence(1, cases[1], Outcome(outputs=((0, b"original"),)), Outcome(outputs=()))
        )
        return report

    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    monkeypatch.setitem(check_sequence.__globals__, "compare_program", fail_comparison)
    with pytest.raises(pytest.fail.Exception, match="replay"):
        check_sequence(spec, fields, tmp_path / "unused-comparator")
    bundles = list(tmp_path.glob("stateful-*.json"))
    assert len(bundles) == 1
    program, cases, ports, seed = load(bundles[0])
    assert program == stateful_program(spec)
    assert cases == cases_for(spec, fields)
    assert (ports, seed) == (4, 0)
