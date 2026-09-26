"""Shared drt stateful programs fixtures and campaign helpers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from hypothesis import strategies as st

from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import (
    ProtocolError,
    Report,
    compare_program,
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
