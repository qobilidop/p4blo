"""Shared drt programs fixtures and campaign helpers."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

import pytest
from hypothesis import strategies as st

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.programs import WIDTHS as PROGRAM_WIDTHS
from p4blo.drt.programs import (
    Leaves,
    scalar_expression,
    scalar_program,
)
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt_families import HypothesisChooser

WIDTHS = st.sampled_from(PROGRAM_WIDTHS)


@st.composite
def scalar(draw: st.DrawFn, width: int | None, depth: int = 3) -> pb.Expr:
    """Shrinking preserves the requested type, including nested operands:
    every decision of `scalar_expression` is drawn from a typed menu."""
    return scalar_expression(HypothesisChooser(draw), width, depth)


@st.composite
def packet_scalar(draw: st.DrawFn, width: int | None) -> pb.Expr:
    """The same, with leaves that read the parsed input."""
    return scalar_expression(HypothesisChooser(draw), width, 3, Leaves(packet=True))


def check_expression(expression: pb.Expr, width: int | None, lean_binary: Path) -> None:
    check_program(scalar_program(expression, width), lean_binary)


def check_program(
    program: apb.BlockAssembly,
    lean_binary: Path,
    cases: Sequence[Case] = (Case(pb.Entries(), 0, b""),),
) -> None:
    # compare_program validates; generator mistakes fail, never get filtered.
    try:
        report = compare_program(program, cases, 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        target = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        target.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(program.SerializeToString()).hexdigest()[:16]
        bundle = target / f"scalar-{digest}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
