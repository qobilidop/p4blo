"""Expression evaluation: one hand-computed case per operator, then
Hypothesis properties, per docs/ir-semantics.md, "Values"."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.interp import InterpError
from p4blo.interp.env import Env
from p4blo.interp.expr import evaluate, read_lvalue, write_lvalue
from p4blo.interp.values import Bits, EnumValue, ErrorValue, Header, Stack, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb

PROGRAM = """
errors: "NoError"
errors: "PacketTooShort"
header_types {
  name: "h8" fields { name: "f" type { bits: 8 } } fields { name: "flag" type { boolean {} } }
}
struct_types {
  name: "H"
  fields { name: "h" type { header: "h8" } }
  fields { name: "hs" type { stack { header: "h8" size: 2 } } }
}
struct_types { name: "M" }
enum_types { name: "color" members: "red" members: "blue" }
headers: "H"
metadata: "M"
blocks {
  name: "ctl" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  locals { name: "x" type { bits: 8 } }
  locals { name: "y" type { bits: 8 } }
  locals { name: "w" type { bits: 4 } }
  locals { name: "b" type { boolean {} } }
  locals { name: "c" type { enum_type: "color" } }
  locals { name: "e" type { error {} } }
}
"""


def env() -> Env:
    index = BoundIndex.build(arch_wire.load_text(PROGRAM))
    return Env.for_block(index, index.blocks["ctl"], {})


# Expression builders, so that a test reads like the P4 it checks.


def lit(width: int, value: int) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=width, value=str(value))))


def boolean(value: bool) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(boolean=value))


def var(name: str) -> pb.Expr:
    return pb.Expr(var=name)


def op(kind: pb.BinaryOp, left: pb.Expr, right: pb.Expr) -> pb.Expr:
    return pb.Expr(binary=pb.Binary(op=kind, left=left, right=right))


def un(kind: pb.UnaryOp, operand: pb.Expr) -> pb.Expr:
    return pb.Expr(unary=pb.Unary(op=kind, operand=operand))


def cast(to: pb.Type, operand: pb.Expr) -> pb.Expr:
    return pb.Expr(cast=pb.Cast(to=to, operand=operand))


def member(base: pb.Expr, field: str) -> pb.Expr:
    return pb.Expr(member=pb.Member(base=base, field=field))


def index(base: pb.Expr, i: pb.Expr) -> pb.Expr:
    return pb.Expr(index=pb.Index(base=base, index=i))


def lv(text: str) -> pb.LValue:
    from google.protobuf import text_format

    return text_format.Parse(text, pb.LValue())


HDR_H = member(var("hdr"), "h")
HDR_HS = member(var("hdr"), "hs")


def ev(expr: pb.Expr, e: Env | None = None) -> Value:
    return evaluate(expr, e or env())


# ---------------------------------------------------------------------------
# Hand-computed cases
# ---------------------------------------------------------------------------


def test_literals() -> None:
    assert ev(lit(8, 255)) == Bits(8, 255)
    assert ev(boolean(False)) is False
    assert ev(
        pb.Expr(literal=pb.Literal(enum_member=pb.EnumLiteral(enum_type="color", member="blue")))
    ) == EnumValue("color", "blue")
    assert ev(pb.Expr(literal=pb.Literal(error="PacketTooShort"))) == ErrorValue("PacketTooShort")
    with pytest.raises(InterpError):
        ev(lit(8, 256))


def test_variables_start_at_zero() -> None:
    e = env()
    assert ev(var("x"), e) == Bits(8, 0)
    assert ev(var("b"), e) is False
    assert ev(var("c"), e) == EnumValue("color", "red")
    assert ev(var("e"), e) == ErrorValue("NoError")
    with pytest.raises(InterpError):
        ev(var("nope"), e)


@pytest.mark.parametrize(
    ("kind", "a", "b", "expected"),
    [
        (pb.BINARY_OP_ADD, 250, 10, 4),
        (pb.BINARY_OP_SUB, 3, 5, 254),
        (pb.BINARY_OP_MUL, 16, 17, 16),
        (pb.BINARY_OP_ADD_SAT, 250, 10, 255),
        (pb.BINARY_OP_SUB_SAT, 3, 5, 0),
        (pb.BINARY_OP_BIT_AND, 0b1100, 0b1010, 0b1000),
        (pb.BINARY_OP_BIT_OR, 0b1100, 0b1010, 0b1110),
        (pb.BINARY_OP_BIT_XOR, 0b1100, 0b1010, 0b0110),
        (pb.BINARY_OP_SHL, 0b1011, 5, 0b01100000),
        (pb.BINARY_OP_SHR, 0b10110000, 5, 0b101),
        (pb.BINARY_OP_SHL, 1, 8, 0),
        (pb.BINARY_OP_SHR, 255, 9, 0),
    ],
)
def test_bits_arithmetic(kind: pb.BinaryOp, a: int, b: int, expected: int) -> None:
    assert ev(op(kind, lit(8, a), lit(8, b))) == Bits(8, expected)


def test_shift_amount_width_does_not_matter() -> None:
    assert ev(op(pb.BINARY_OP_SHL, lit(8, 1), lit(32, 3))) == Bits(8, 8)
    assert ev(op(pb.BINARY_OP_SHR, lit(8, 128), lit(2, 3))) == Bits(8, 16)


def test_concat_puts_left_in_the_high_bits() -> None:
    assert ev(op(pb.BINARY_OP_CONCAT, lit(4, 0xA), lit(8, 0x5C))) == Bits(12, 0xA5C)


@pytest.mark.parametrize(
    ("kind", "a", "b", "expected"),
    [
        (pb.BINARY_OP_LT, 1, 2, True),
        (pb.BINARY_OP_LE, 2, 2, True),
        (pb.BINARY_OP_GT, 200, 100, True),
        (pb.BINARY_OP_GE, 1, 2, False),
        (pb.BINARY_OP_EQ, 7, 7, True),
        (pb.BINARY_OP_NE, 7, 7, False),
    ],
)
def test_comparisons_are_unsigned(kind: pb.BinaryOp, a: int, b: int, expected: bool) -> None:
    assert ev(op(kind, lit(8, a), lit(8, b))) is expected


def test_equality_on_every_type() -> None:
    e = env()
    assert ev(op(pb.BINARY_OP_EQ, var("c"), var("c")), e) is True
    assert ev(op(pb.BINARY_OP_EQ, var("e"), var("e")), e) is True
    assert ev(op(pb.BINARY_OP_EQ, boolean(True), var("b")), e) is False
    # Two invalid headers are equal whatever their fields.
    write_lvalue(
        lv('member { base { var: "hdr" } field: "h" }'), Header("h8", False, [Bits(8, 9), True]), e
    )
    assert ev(op(pb.BINARY_OP_EQ, HDR_H, index(HDR_HS, lit(8, 0))), e) is True
    assert ev(op(pb.BINARY_OP_NE, var("hdr"), var("hdr")), e) is False


def test_logical_operators_short_circuit() -> None:
    # The right operand would fail to evaluate, so it must not be reached.
    bad = op(pb.BINARY_OP_LT, var("b"), var("b"))
    assert ev(op(pb.BINARY_OP_AND, boolean(False), bad)) is False
    assert ev(op(pb.BINARY_OP_OR, boolean(True), bad)) is True
    assert ev(op(pb.BINARY_OP_AND, boolean(True), boolean(True))) is True
    assert ev(op(pb.BINARY_OP_OR, boolean(False), boolean(False))) is False


def test_unary_operators() -> None:
    assert ev(un(pb.UNARY_OP_NOT, boolean(True))) is False
    assert ev(un(pb.UNARY_OP_COMPLEMENT, lit(8, 0b10101010))) == Bits(8, 0b01010101)
    assert ev(un(pb.UNARY_OP_NEGATE, lit(8, 1))) == Bits(8, 255)
    assert ev(un(pb.UNARY_OP_NEGATE, lit(8, 0))) == Bits(8, 0)


def test_casts() -> None:
    assert ev(cast(pb.Type(bits=4), lit(8, 0xAB))) == Bits(4, 0xB)  # truncation keeps the low bits
    assert ev(cast(pb.Type(bits=16), lit(8, 0xAB))) == Bits(16, 0xAB)  # zero extension
    assert ev(cast(pb.Type(bits=1), boolean(True))) == Bits(1, 1)
    assert ev(cast(pb.Type(bits=1), boolean(False))) == Bits(1, 0)
    assert ev(cast(pb.Type(boolean=pb.BoolType()), lit(1, 1))) is True
    assert ev(cast(pb.Type(boolean=pb.BoolType()), lit(1, 0))) is False


def test_slice() -> None:
    sliced = pb.Expr(slice=pb.Slice(operand=lit(8, 0b10110100), hi=5, lo=2))
    assert ev(sliced) == Bits(4, 0b1101)
    whole = pb.Expr(slice=pb.Slice(operand=lit(8, 0xC3), hi=7, lo=0))
    assert ev(whole) == Bits(8, 0xC3)


def test_mux_evaluates_only_the_chosen_branch() -> None:
    bad = op(pb.BINARY_OP_LT, var("b"), var("b"))
    assert ev(pb.Expr(mux=pb.Mux(condition=boolean(True), then=lit(8, 1), otherwise=bad))) == Bits(
        8, 1
    )
    assert ev(pb.Expr(mux=pb.Mux(condition=boolean(False), then=bad, otherwise=lit(8, 2)))) == Bits(
        8, 2
    )


def test_is_valid_and_member_of_invalid_header_reads_stored_fields() -> None:
    e = env()
    assert ev(pb.Expr(is_valid=pb.IsValid(header=HDR_H)), e) is False
    write_lvalue(
        lv('member { base { member { base { var: "hdr" } field: "h" } } field: "f" }'),
        Bits(8, 42),
        e,
    )
    assert ev(pb.Expr(is_valid=pb.IsValid(header=HDR_H)), e) is False
    assert ev(member(HDR_H, "f"), e) == Bits(8, 42)


def test_stack_index_and_last_index() -> None:
    e = env()
    stack = read_lvalue(lv('member { base { var: "hdr" } field: "hs" }'), e)
    assert isinstance(stack, Stack)
    last = pb.Expr(last_index=pb.LastIndex(stack=HDR_HS))
    assert ev(last, e) == Bits(32, 2**32 - 1)  # nextIndex == 0 wraps
    stack.next_index = 2
    assert ev(last, e) == Bits(32, 1)
    stack.elements[1].fields[0] = Bits(8, 7)
    assert ev(member(index(HDR_HS, lit(32, 1)), "f"), e) == Bits(8, 7)
    # Out of range: an invalid header with zero fields.
    assert ev(index(HDR_HS, lit(32, 9)), e) == Header("h8", False, [Bits(8, 0), False])


def test_write_lvalue_copies_and_read_lvalue_references() -> None:
    e = env()
    source = Header("h8", True, [Bits(8, 1), True])
    write_lvalue(lv('member { base { var: "hdr" } field: "h" }'), source, e)
    source.fields[0] = Bits(8, 2)
    stored = read_lvalue(lv('member { base { var: "hdr" } field: "h" }'), e)
    assert stored == Header("h8", True, [Bits(8, 1), True])
    hdr = e.read("hdr")
    assert isinstance(hdr, Struct)
    assert stored is hdr.fields[0]


def test_next_is_not_an_lvalue_outside_extract() -> None:
    # The validator allows `hs.next` only as an extract target, which
    # `stmt.extract` handles itself; the lvalue paths never see it.
    e = env()
    nxt = lv('next { stack { member { base { var: "hdr" } field: "hs" } } }')
    with pytest.raises(InterpError):
        write_lvalue(nxt, Header("h8", True, [Bits(8, 1), True]), e)
    with pytest.raises(InterpError):
        read_lvalue(nxt, e)
    hdr = e.read("hdr")
    assert isinstance(hdr, Struct)
    stack = hdr.fields[1]
    assert isinstance(stack, Stack)
    assert stack.next_index == 0 and not stack.elements[0].valid


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@st.composite
def width_and_two_values(draw: st.DrawFn) -> tuple[int, int, int]:
    width = draw(st.integers(1, 80))
    top = (1 << width) - 1
    return width, draw(st.integers(0, top)), draw(st.integers(0, top))


@given(width_and_two_values())
def test_wrapping_arithmetic_agrees_with_modular(triple: tuple[int, int, int]) -> None:
    width, a, b = triple
    modulus = 1 << width
    assert ev(op(pb.BINARY_OP_ADD, lit(width, a), lit(width, b))) == Bits(width, (a + b) % modulus)
    assert ev(op(pb.BINARY_OP_SUB, lit(width, a), lit(width, b))) == Bits(width, (a - b) % modulus)
    assert ev(op(pb.BINARY_OP_MUL, lit(width, a), lit(width, b))) == Bits(width, (a * b) % modulus)


@given(width_and_two_values())
def test_saturating_operators_clamp(triple: tuple[int, int, int]) -> None:
    width, a, b = triple
    top = (1 << width) - 1
    assert ev(op(pb.BINARY_OP_ADD_SAT, lit(width, a), lit(width, b))) == Bits(
        width, min(a + b, top)
    )
    assert ev(op(pb.BINARY_OP_SUB_SAT, lit(width, a), lit(width, b))) == Bits(width, max(a - b, 0))


@given(width_and_two_values(), st.integers(0, 200))
def test_shifts_by_the_width_or_more_give_zero(triple: tuple[int, int, int], k: int) -> None:
    width, a, _ = triple
    left = ev(op(pb.BINARY_OP_SHL, lit(width, a), lit(8, k)))
    right = ev(op(pb.BINARY_OP_SHR, lit(width, a), lit(8, k)))
    if k >= width:
        assert left == Bits(width, 0) and right == Bits(width, 0)
    else:
        assert left == Bits(width, (a << k) % (1 << width)) and right == Bits(width, a >> k)


@given(width_and_two_values(), st.integers(1, 80))
def test_concat_then_slice_roundtrips(triple: tuple[int, int, int], other_width: int) -> None:
    width, a, b = triple
    b %= 1 << other_width
    both = op(pb.BINARY_OP_CONCAT, lit(width, a), lit(other_width, b))
    high = pb.Expr(slice=pb.Slice(operand=both, hi=width + other_width - 1, lo=other_width))
    low = pb.Expr(slice=pb.Slice(operand=both, hi=other_width - 1, lo=0))
    assert ev(high) == Bits(width, a)
    assert ev(low) == Bits(other_width, b)


@given(width_and_two_values(), st.integers(1, 80))
def test_cast_truncates_or_zero_extends(triple: tuple[int, int, int], to: int) -> None:
    width, a, _ = triple
    result = ev(cast(pb.Type(bits=to), lit(width, a)))
    assert isinstance(result, Bits)
    assert result == Bits(to, a % (1 << to))
    if to >= width:
        assert result.value == a


@given(width_and_two_values())
def test_equality_is_reflexive_and_matches_value(triple: tuple[int, int, int]) -> None:
    width, a, b = triple
    assert ev(op(pb.BINARY_OP_EQ, lit(width, a), lit(width, a))) is True
    assert ev(op(pb.BINARY_OP_EQ, lit(width, a), lit(width, b))) is (a == b)
    assert ev(op(pb.BINARY_OP_LT, lit(width, a), lit(width, b))) is (a < b)
