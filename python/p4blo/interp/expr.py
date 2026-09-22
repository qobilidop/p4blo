"""Expressions and lvalues.

`evaluate` has one function per `Expr` kind and implements docs/semantics.md,
"Values". `read_lvalue` and `write_lvalue` implement "Headers" and "Header
stacks": a read of an invalid header returns its stored fields, a read past a
stack's end returns a zero invalid header, a write past its end does nothing,
and a write to `hs.next` fills the next slot or raises `StackOutOfBounds`.

Every `Bits` result goes through `Bits` or `Bits.wrap`, which enforce the
width invariant. `evaluate` returns references to stored compound values;
`write_lvalue` copies, so no two variables ever share storage.
"""

from __future__ import annotations

from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.errors import STACK_OUT_OF_BOUNDS, ParseError
from p4blo.interp.values import (
    Bits,
    EnumValue,
    ErrorValue,
    Header,
    Stack,
    Struct,
    Value,
    copy,
    equal,
    zero,
)
from p4blo.interp.widths import width_of
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb

# ---------------------------------------------------------------------------
# Narrowing helpers: a validated program never fails these.
# ---------------------------------------------------------------------------


def expect_bits(value: Value) -> Bits:
    if isinstance(value, Bits):
        return value
    raise InterpError(f"expected bits, got {type(value).__name__}")


def expect_bool(value: Value) -> bool:
    if isinstance(value, bool):
        return value
    raise InterpError(f"expected boolean, got {type(value).__name__}")


def expect_header(value: Value) -> Header:
    if isinstance(value, Header):
        return value
    raise InterpError(f"expected header, got {type(value).__name__}")


def expect_struct(value: Value) -> Struct:
    if isinstance(value, Struct):
        return value
    raise InterpError(f"expected struct, got {type(value).__name__}")


def expect_stack(value: Value) -> Stack:
    if isinstance(value, Stack):
        return value
    raise InterpError(f"expected header stack, got {type(value).__name__}")


# ---------------------------------------------------------------------------
# Literals and packet representations
# ---------------------------------------------------------------------------


def literal_value(literal: pb.Literal) -> Value:
    match literal.WhichOneof("value"):
        case "bits":
            try:
                return Bits(literal.bits.width, int(literal.bits.value))
            except ValueError as e:
                raise InterpError(f"bad bits literal: {e}") from None
        case "boolean":
            return literal.boolean
        case "enum_member":
            return EnumValue(literal.enum_member.enum_type, literal.enum_member.member)
        case "error":
            return ErrorValue(literal.error)
        case _:
            raise InterpError("literal has no value")


def zero_header(type_name: str, index: Index) -> Header:
    return expect_header(zero(pb.Type(header=type_name), index))


def header_from_bits(type_name: str, raw: int, index: Index) -> Header:
    """A valid header whose fields hold `raw`, first field in the high bits
    (docs/semantics.md, "Extract sets the target valid")."""
    fields: list[Value] = []
    remaining = width_of(pb.Type(header=type_name), index)
    for f in index.header_types[type_name].fields:
        width = width_of(f.type, index)
        remaining -= width
        chunk = (raw >> remaining) & ((1 << width) - 1)
        fields.append(chunk == 1 if f.type.WhichOneof("kind") == "boolean" else Bits(width, chunk))
    return Header(type_name, True, fields)


def header_to_bits(header: Header) -> tuple[int, int]:
    """The `(width, value)` of a header's fields concatenated, first field
    in the high bits; the inverse of `header_from_bits`."""
    width = 0
    value = 0
    for f in header.fields:
        if isinstance(f, bool):
            value = (value << 1) | int(f)
            width += 1
        else:
            bits = expect_bits(f)
            value = (value << bits.width) | bits.value
            width += bits.width
    return width, value


def value_from_bits(type: pb.Type, raw: int, index: Index) -> Value:
    """The value of `type` that `raw` spells: what `lookahead<T>` returns."""
    match type.WhichOneof("kind"):
        case "bits":
            return Bits(type.bits, raw)
        case "boolean":
            return raw == 1
        case "header":
            return header_from_bits(type.header, raw, index)
        case kind:
            raise InterpError(f"cannot read a value of kind {kind!r} from the packet")


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


def evaluate(expr: pb.Expr, env: Env) -> Value:
    match expr.WhichOneof("kind"):
        case "literal":
            return literal_value(expr.literal)
        case "var":
            return env.read(expr.var)
        case "member":
            return member(expr.member, env)
        case "index":
            return index_element(expr.index, env)
        case "last_index":
            return last_index(expr.last_index, env)
        case "unary":
            return unary(expr.unary, env)
        case "binary":
            return binary(expr.binary, env)
        case "cast":
            return cast(expr.cast, env)
        case "slice":
            return slice_bits(expr.slice, env)
        case "is_valid":
            return expect_header(evaluate(expr.is_valid.header, env)).valid
        case "mux":
            return mux(expr.mux, env)
        case "lookahead":
            return lookahead(expr.lookahead, env)
        case _:
            raise InterpError("expression has no kind")


def field_of(container: Value, field: str, index: Index) -> Value:
    """Field `field` of a header or struct; an invalid header's stored
    fields are returned as they are (docs/semantics.md, "Headers")."""
    if not isinstance(container, Header | Struct):
        raise InterpError(f"{type(container).__name__} has no fields")
    return container.fields[index.field_index(container.type_name, field)]


def member(m: pb.Member, env: Env) -> Value:
    return field_of(evaluate(m.base, env), m.field, env.index)


def element_of(stack: Stack, i: int, index: Index) -> Header:
    """`hs[i]`; past the end, a zero invalid header not stored anywhere
    (docs/semantics.md, "Index out of range")."""
    if i < len(stack.elements):
        return stack.elements[i]
    return zero_header(stack.header_type, index)


def index_element(ix: pb.Index, env: Env) -> Value:
    stack = expect_stack(evaluate(ix.base, env))
    i = expect_bits(evaluate(ix.index, env)).value
    return element_of(stack, i, env.index)


def last_index(li: pb.LastIndex, env: Env) -> Bits:
    """`nextIndex - 1` as a `bit<32>`, wrapping at `nextIndex == 0`."""
    stack = expect_stack(evaluate(li.stack, env))
    return Bits.wrap(32, stack.next_index - 1)


def unary(u: pb.Unary, env: Env) -> Value:
    operand = evaluate(u.operand, env)
    match u.op:
        case pb.UNARY_OP_NOT:
            return not expect_bool(operand)
        case pb.UNARY_OP_COMPLEMENT:
            x = expect_bits(operand)
            return Bits.wrap(x.width, ~x.value)
        case pb.UNARY_OP_NEGATE:
            x = expect_bits(operand)
            return Bits.wrap(x.width, -x.value)
        case _:
            raise InterpError("unary operator unspecified")


def binary(b: pb.Binary, env: Env) -> Value:
    # `&&` and `||` short-circuit, so the right operand may not be evaluated.
    if b.op == pb.BINARY_OP_AND:
        return expect_bool(evaluate(b.left, env)) and expect_bool(evaluate(b.right, env))
    if b.op == pb.BINARY_OP_OR:
        return expect_bool(evaluate(b.left, env)) or expect_bool(evaluate(b.right, env))
    left = evaluate(b.left, env)
    right = evaluate(b.right, env)
    # `==` and `!=` are defined on every type.
    if b.op == pb.BINARY_OP_EQ:
        return equal(left, right)
    if b.op == pb.BINARY_OP_NE:
        return not equal(left, right)
    return bits_binary(b.op, expect_bits(left), expect_bits(right))


def bits_binary(op: int, x: Bits, y: Bits) -> Value:
    """The `bit<N>` operators of docs/semantics.md, "Values"."""
    n = x.width
    match op:
        case pb.BINARY_OP_ADD:
            return Bits.wrap(n, x.value + y.value)
        case pb.BINARY_OP_SUB:
            return Bits.wrap(n, x.value - y.value)
        case pb.BINARY_OP_MUL:
            return Bits.wrap(n, x.value * y.value)
        case pb.BINARY_OP_ADD_SAT:
            return Bits(n, min(x.value + y.value, (1 << n) - 1))
        case pb.BINARY_OP_SUB_SAT:
            return Bits(n, max(x.value - y.value, 0))
        case pb.BINARY_OP_BIT_AND:
            return Bits(n, x.value & y.value)
        case pb.BINARY_OP_BIT_OR:
            return Bits(n, x.value | y.value)
        case pb.BINARY_OP_BIT_XOR:
            return Bits(n, x.value ^ y.value)
        case pb.BINARY_OP_SHL:
            # A shift by the width or more gives 0, whatever the amount's width.
            return Bits.wrap(n, x.value << y.value) if y.value < n else Bits(n, 0)
        case pb.BINARY_OP_SHR:
            return Bits(n, x.value >> y.value) if y.value < n else Bits(n, 0)
        case pb.BINARY_OP_CONCAT:
            # The left operand lands in the high bits.
            return Bits(x.width + y.width, (x.value << y.width) | y.value)
        case pb.BINARY_OP_LT:
            return x.value < y.value
        case pb.BINARY_OP_LE:
            return x.value <= y.value
        case pb.BINARY_OP_GT:
            return x.value > y.value
        case pb.BINARY_OP_GE:
            return x.value >= y.value
        case _:
            raise InterpError("binary operator unspecified")


def cast(c: pb.Cast, env: Env) -> Value:
    """Bits to bits truncates or zero-extends; `bool` and `bit<1>` map onto
    each other (docs/semantics.md, "Casts")."""
    operand = evaluate(c.operand, env)
    match c.to.WhichOneof("kind"):
        case "bits":
            if isinstance(operand, bool):
                return Bits(c.to.bits, int(operand))
            return Bits.wrap(c.to.bits, expect_bits(operand).value)
        case "boolean":
            return expect_bits(operand).value == 1
        case kind:
            raise InterpError(f"no cast to {kind!r}")


def slice_bits(s: pb.Slice, env: Env) -> Bits:
    """`operand[hi:lo]`, width `hi - lo + 1`."""
    x = expect_bits(evaluate(s.operand, env))
    width = s.hi - s.lo + 1
    return Bits(width, (x.value >> s.lo) & ((1 << width) - 1))


def mux(m: pb.Mux, env: Env) -> Value:
    """Only the chosen branch is evaluated."""
    if expect_bool(evaluate(m.condition, env)):
        return evaluate(m.then, env)
    return evaluate(m.otherwise, env)


def lookahead(la: pb.Lookahead, env: Env) -> Value:
    """Read `width(T)` bits without moving the cursor; a header result is
    valid (docs/semantics.md, "lookahead")."""
    packet = env.require_packet()
    raw = packet.peek(width_of(la.type, env.index))
    return value_from_bits(la.type, raw, env.index)


# ---------------------------------------------------------------------------
# Lvalues
# ---------------------------------------------------------------------------


def read_lvalue(lv: pb.LValue, env: Env) -> Value:
    """The value an lvalue currently denotes, as a reference into storage
    where one exists."""
    match lv.WhichOneof("kind"):
        case "var":
            return env.read(lv.var)
        case "member":
            return field_of(read_lvalue(lv.member.base, env), lv.member.field, env.index)
        case "index":
            stack = expect_stack(read_lvalue(lv.index.base, env))
            i = expect_bits(evaluate(lv.index.index, env)).value
            return element_of(stack, i, env.index)
        case "next":
            stack = expect_stack(read_lvalue(lv.next.stack, env))
            if stack.next_index >= len(stack.elements):
                raise ParseError(STACK_OUT_OF_BOUNDS)
            return stack.elements[stack.next_index]
        case _:
            raise InterpError("lvalue has no kind")


def write_lvalue(lv: pb.LValue, value: Value, env: Env) -> None:
    """Store a copy of `value` at `lv`.

    A whole-header write copies validity and fields; a write through a
    stack index past the end does nothing; a write to `hs.next` fills
    `hs[nextIndex]`, makes it valid and increments `nextIndex`, or raises
    `StackOutOfBounds` when the stack is full.
    """
    match lv.WhichOneof("kind"):
        case "var":
            env.write(lv.var, copy(value))
        case "member":
            # A container past a stack's end is a fresh zero header, so
            # writing into it changes nothing, as the semantics require.
            container = read_lvalue(lv.member.base, env)
            if not isinstance(container, Header | Struct):
                raise InterpError(f"{type(container).__name__} has no fields")
            container.fields[env.index.field_index(container.type_name, lv.member.field)] = copy(
                value
            )
        case "index":
            stack = expect_stack(read_lvalue(lv.index.base, env))
            i = expect_bits(evaluate(lv.index.index, env)).value
            if i < len(stack.elements):
                stack.elements[i] = expect_header(copy(value))
        case "next":
            stack = expect_stack(read_lvalue(lv.next.stack, env))
            if stack.next_index >= len(stack.elements):
                raise ParseError(STACK_OUT_OF_BOUNDS)
            header = expect_header(copy(value))
            header.valid = True
            stack.elements[stack.next_index] = header
            stack.next_index += 1
        case _:
            raise InterpError("lvalue has no kind")
