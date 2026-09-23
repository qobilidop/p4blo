"""Typed generated programs, shrinking, and systematic scalar boundaries.

Unlike packet fuzzing of fixed corpus programs, these change the program
being compared. Every generated expression is placed in an observable
context and independently validated; no expected arithmetic is shared
between the interpreters. Failed programs are concrete replay bundles.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.programs import binary, bits, boolean, scalar_program
from p4blo.drt.replay import save
from p4blo.drt.run import LeanRunner, ProtocolError, compare_cases
from p4blo.v0 import p4blo_pb2 as pb

WIDTHS = st.sampled_from([1, 7, 8, 9, 16, 31, 32, 64, 65, 127])
ARITHMETIC = [
    pb.BINARY_OP_ADD,
    pb.BINARY_OP_SUB,
    pb.BINARY_OP_MUL,
    pb.BINARY_OP_ADD_SAT,
    pb.BINARY_OP_SUB_SAT,
    pb.BINARY_OP_BIT_AND,
    pb.BINARY_OP_BIT_OR,
    pb.BINARY_OP_BIT_XOR,
]
COMPARISONS = [
    pb.BINARY_OP_EQ,
    pb.BINARY_OP_NE,
    pb.BINARY_OP_LT,
    pb.BINARY_OP_LE,
    pb.BINARY_OP_GT,
    pb.BINARY_OP_GE,
]


@st.composite
def scalar(draw: st.DrawFn, width: int | None, depth: int = 3) -> pb.Expr:
    """Shrinking preserves the requested type, including nested operands."""
    kinds = ["leaf"] if depth == 0 else ["leaf", "unary", "binary", "cast", "mux"]
    if width is not None and depth:
        kinds += ["slice", "shift"]
        if width > 1:
            kinds.append("concat")
    kind = draw(st.sampled_from(kinds))
    if kind == "leaf":
        if width is None:
            return boolean(draw(st.booleans()))
        maximum = (1 << width) - 1
        edges = sorted({0, 1, maximum, maximum - 1, min(width, maximum)})
        return bits(width, draw(st.one_of(st.sampled_from(edges), st.integers(0, maximum))))
    if kind == "unary":
        op = (
            pb.UNARY_OP_NOT
            if width is None
            else draw(st.sampled_from([pb.UNARY_OP_COMPLEMENT, pb.UNARY_OP_NEGATE]))
        )
        return pb.Expr(unary=pb.Unary(op=op, operand=draw(scalar(width, depth - 1))))
    if kind == "binary":
        if width is None:
            op = draw(st.sampled_from([*COMPARISONS, pb.BINARY_OP_AND, pb.BINARY_OP_OR]))
            operand_width = None if op in (pb.BINARY_OP_AND, pb.BINARY_OP_OR) else draw(WIDTHS)
        else:
            op, operand_width = draw(st.sampled_from(ARITHMETIC)), width
        return binary(
            op, draw(scalar(operand_width, depth - 1)), draw(scalar(operand_width, depth - 1))
        )
    if kind == "cast":
        source_width = 1 if width is None else draw(WIDTHS)
        target = pb.Type(boolean=pb.BoolType()) if width is None else pb.Type(bits=width)
        return pb.Expr(cast=pb.Cast(to=target, operand=draw(scalar(source_width, depth - 1))))
    if kind == "mux":
        return pb.Expr(
            mux=pb.Mux(
                **{
                    "condition": draw(scalar(None, depth - 1)),
                    "then": draw(scalar(width, depth - 1)),
                    "otherwise": draw(scalar(width, depth - 1)),
                }
            )
        )
    assert width is not None
    if kind == "slice":
        lo = draw(st.integers(0, 16))
        extra = draw(st.integers(0, 16))
        return pb.Expr(
            slice=pb.Slice(
                operand=draw(scalar(width + lo + extra, depth - 1)),
                hi=lo + width - 1,
                lo=lo,
            )
        )
    if kind == "shift":
        op = draw(st.sampled_from([pb.BINARY_OP_SHL, pb.BINARY_OP_SHR]))
        return binary(op, draw(scalar(width, depth - 1)), draw(scalar(draw(WIDTHS), depth - 1)))
    assert kind == "concat"
    left_width = draw(st.integers(1, width - 1))
    return binary(
        pb.BINARY_OP_CONCAT,
        draw(scalar(left_width, depth - 1)),
        draw(scalar(width - left_width, depth - 1)),
    )


def check_expression(expression: pb.Expr, width: int | None, lean_binary: Path) -> None:
    program = scalar_program(expression, width)
    loaded = arch.load(program)  # Generator mistakes fail; never filter them out.
    cases = [Case(pb.Entries(), 0, b"")]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "program.json"
        path.write_text(ir.dump_json(program))
        try:
            with LeanRunner([lean_binary], path, 4) as runner:
                report = compare_cases("scalar", loaded, cases, 4, runner.run)
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
