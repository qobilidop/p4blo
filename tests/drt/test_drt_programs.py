"""Typed generated programs, shrinking, and systematic scalar boundaries.

Unlike packet fuzzing of fixed corpus programs, these change the program
being compared. Every generated expression is placed in an observable
context and independently validated; no expected arithmetic is shared
between the interpreters. Failed programs are concrete replay bundles.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.generate import generate
from p4blo.drt.programs import (
    ARITHMETIC,
    COMPARISONS,
    Leaves,
    binary,
    bits,
    boolean,
    packet_scalar_program,
    parser_condition_program,
    scalar_expression,
    scalar_program,
)
from p4blo.drt.programs import WIDTHS as PROGRAM_WIDTHS
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.v0 import p4blo_pb2 as pb
from tests.drt.test_drt_families import HypothesisChooser

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
    program: pb.Program, lean_binary: Path, cases: Sequence[Case] = (Case(pb.Entries(), 0, b""),)
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


def test_lean_agrees_on_cast_slice_mux_boundaries(lean_binary: Path) -> None:
    for value in (False, True):
        check_expression(
            pb.Expr(unary=pb.Unary(op=pb.UNARY_OP_NOT, operand=boolean(value))), None, lean_binary
        )
        check_expression(
            pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=boolean(value))), 1, lean_binary
        )
        check_expression(
            pb.Expr(cast=pb.Cast(to=pb.Type(boolean=pb.BoolType()), operand=bits(1, int(value)))),
            None,
            lean_binary,
        )
        check_expression(
            pb.Expr(
                mux=pb.Mux(
                    **{
                        "condition": boolean(value),
                        "then": bits(7, 21),
                        "otherwise": bits(7, 106),
                    }
                )
            ),
            7,
            lean_binary,
        )
    for source in (1, 8, 65):
        for target in (1, 7, 8, 9, 65):
            check_expression(
                pb.Expr(
                    cast=pb.Cast(to=pb.Type(bits=target), operand=bits(source, (1 << source) - 1))
                ),
                target,
                lean_binary,
            )
    for hi, lo in ((0, 0), (7, 7), (7, 0), (6, 2)):
        check_expression(
            pb.Expr(slice=pb.Slice(operand=bits(8, 0xDA), hi=hi, lo=lo)), hi - lo + 1, lean_binary
        )


def test_lean_agrees_on_faulting_unselected_branches(lean_binary: Path) -> None:
    trap = pb.Expr(
        cast=pb.Cast(
            to=pb.Type(boolean=pb.BoolType()),
            operand=pb.Expr(lookahead=pb.Lookahead(type=pb.Type(bits=1))),
        )
    )
    cases = [
        (binary(pb.BINARY_OP_AND, boolean(False), trap), "NoMatch"),
        (binary(pb.BINARY_OP_OR, boolean(True), trap), "NoError"),
        (binary(pb.BINARY_OP_AND, boolean(True), trap), "PacketTooShort"),
        (binary(pb.BINARY_OP_OR, boolean(False), trap), "PacketTooShort"),
        (
            pb.Expr(
                mux=pb.Mux(**{"condition": boolean(True), "then": boolean(True), "otherwise": trap})
            ),
            "NoError",
        ),
        (
            pb.Expr(
                mux=pb.Mux(
                    **{"condition": boolean(False), "then": trap, "otherwise": boolean(True)}
                )
            ),
            "NoError",
        ),
    ]
    for condition, expected_error in cases:
        program = parser_condition_program(condition, expected_error)
        check_program(program, lean_binary)
        assert run_python(arch.reference.load(program), Case(pb.Entries(), 0, b""), 4) == [
            (0, b"\x80")
        ]


@pytest.mark.parametrize("width", [1, 7, 8, 9, 31, 32, 65])
def test_lean_agrees_on_every_scalar_operator(width: int, lean_binary: Path) -> None:
    maximum = (1 << width) - 1
    for op in ARITHMETIC + COMPARISONS:
        for x, y in [(maximum, 1), (0, maximum), (maximum, maximum)]:
            check_expression(
                binary(op, bits(width, x), bits(width, y)),
                None if op in COMPARISONS else width,
                lean_binary,
            )
    for op in (pb.BINARY_OP_SHL, pb.BINARY_OP_SHR):
        for amount in (0, width - 1, width, width + 1, 65535):
            check_expression(binary(op, bits(width, maximum), bits(16, amount)), width, lean_binary)
    check_expression(
        binary(pb.BINARY_OP_CONCAT, bits(width, maximum), bits(3, 5)), width + 3, lean_binary
    )
    for op in (pb.UNARY_OP_COMPLEMENT, pb.UNARY_OP_NEGATE):
        check_expression(
            pb.Expr(unary=pb.Unary(op=op, operand=bits(width, maximum))), width, lean_binary
        )


@pytest.mark.parametrize(
    "op", [pb.BINARY_OP_AND, pb.BINARY_OP_OR, pb.BINARY_OP_EQ, pb.BINARY_OP_NE]
)
def test_lean_agrees_on_boolean_truth_tables(op: pb.BinaryOp, lean_binary: Path) -> None:
    for left in (False, True):
        for right in (False, True):
            check_expression(binary(op, boolean(left), boolean(right)), None, lean_binary)


@settings(max_examples=200, deadline=None, derandomize=True)
@given(data=st.data(), width=st.one_of(st.none(), WIDTHS))
def test_lean_agrees_on_shrinking_typed_programs(
    lean_binary: Path, data: st.DataObject, width: int | None
) -> None:
    check_expression(data.draw(scalar(width)), width, lean_binary)


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    data=st.data(),
    width=st.one_of(st.none(), WIDTHS),
    seed=st.integers(0, 2**32 - 1),
)
def test_lean_agrees_on_shrinking_packet_programs(
    lean_binary: Path, data: st.DataObject, width: int | None, seed: int
) -> None:
    """Leaves that read fields, locals, a stack element and validity of a
    parsed input, so that each packet computes something else."""
    program = packet_scalar_program(data.draw(packet_scalar(width)), width)
    check_program(program, lean_binary, generate(ir.Index.build(program), seed, 4))
