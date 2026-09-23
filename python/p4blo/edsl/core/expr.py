"""Typed expressions.

An `Expr` wraps a `pb.Expr` together with its `pb.Type`, and when the
expression is a path (a variable, a field of one, an element of a stack)
also the `pb.LValue` that names the same place. Operators build new
expressions and check what the schema requires of their operands: equal
widths for arithmetic, booleans for logic, a header for `is_valid`.

Integer literals have no width of their own in P4; the frontend gives them
one from context. The eDSL does the same: an `int` operand takes the type
of the Expr it meets (`hdr.ipv4.ttl - 1` makes `1` a `bit<8>`), an
assignment takes its target's type, an argument takes its parameter's.
A literal that does not fit, or an int where no context supplies a width,
is an `EdslError`; the one exception is a shift amount, whose width P4
leaves free, so an int amount too large for the left operand's width takes
the smallest width that holds it (`_shift`). Nothing else is inferred, and
no cast is ever inserted: `x.cast(bit(16))` is the only way one appears in
the IR.
"""

from __future__ import annotations

from p4blo.edsl.core.types import (
    EdslError,
    TypeLike,
    TypeTable,
    as_type,
    boolean,
    error_t,
    is_bits,
    is_boolean,
    type_str,
)
from p4blo.v0 import p4blo_pb2 as pb

type Operand = Expr | int | bool
"""What an operator accepts beside an Expr: a Python int for a bit<N>
literal, a Python bool for a boolean literal."""

BIT32: pb.Type = pb.Type(bits=32)


class Expr:
    """A typed expression, possibly an lvalue.

    `node` is None for `stack.next`, which the schema allows only as an
    lvalue; `lvalue` is None for anything that is not a path.

    A field is reached as an attribute, `hdr.ipv4.ttl`, except when its
    name is one of this class's own: `type`, `types`, `node`, `lvalue`,
    `pb`, `lval`, `width`, `next`, `last`, `last_index`, `is_literal`,
    `is_valid`, `cast`, `add_sat`, `sub_sat` and `field` itself. Those
    attributes win, so `hdr.eth.type` is the expression's `pb.Type`, not
    the member; `hdr.eth.field("type")` always means the field.
    """

    __slots__ = ("types", "type", "node", "lvalue")

    def __init__(
        self,
        types: TypeTable,
        type: pb.Type,
        node: pb.Expr | None,
        lvalue: pb.LValue | None = None,
    ) -> None:
        self.types = types
        self.type = type
        self.node = node
        self.lvalue = lvalue

    def __repr__(self) -> str:
        return f"Expr({type_str(self.type)})"

    # -- what the IR sees --------------------------------------------------

    @property
    def pb(self) -> pb.Expr:
        """The expression, for use as a value."""
        if self.node is None:
            raise EdslError("stack.next may only be written to, not read")
        return self.node

    @property
    def lval(self) -> pb.LValue:
        """The expression as a place to write, when it is one."""
        if self.lvalue is None:
            raise EdslError(f"not an lvalue: {self!r}")
        return self.lvalue

    @property
    def is_literal(self) -> bool:
        return self.node is not None and self.node.WhichOneof("kind") == "literal"

    @property
    def width(self) -> int:
        if not is_bits(self.type):
            raise EdslError(f"{type_str(self.type)} has no width")
        return self.type.bits

    # -- paths -------------------------------------------------------------

    def __getattr__(self, name: str) -> Expr:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.field(name)

    def field(self, name: str) -> Expr:
        """The field `name` of a header or struct value, whatever its name."""
        fields = self.types.fields(self.type)
        if fields is None:
            raise EdslError(f"{type_str(self.type)} has no fields, so no field {name!r}")
        if name not in fields:
            raise EdslError(
                f"{type_str(self.type)} has no field {name!r}; fields are {', '.join(fields)}"
            )
        node = pb.Expr(member=pb.Member(base=self.pb, field=name))
        lvalue = None
        if self.lvalue is not None:
            lvalue = pb.LValue(member=pb.LMember(base=self.lvalue, field=name))
        return Expr(self.types, fields[name], node, lvalue)

    def __getitem__(self, key: int | slice | Expr) -> Expr:
        if isinstance(key, slice):
            return self._slice(key)
        if self.type.WhichOneof("kind") != "stack":
            raise EdslError(f"{type_str(self.type)} is not a stack; x[i] indexes a stack")
        index = literal(self.types, key, BIT32) if not isinstance(key, Expr) else key
        if not is_bits(index.type):
            raise EdslError(f"a stack index is bit<N>, not {type_str(index.type)}")
        element = pb.Type(header=self.type.stack.header)
        node = pb.Expr(index=pb.Index(base=self.pb, index=index.pb))
        lvalue = None
        if self.lvalue is not None:
            lvalue = pb.LValue(index=pb.LIndex(base=self.lvalue, index=index.pb))
        return Expr(self.types, element, node, lvalue)

    def _slice(self, key: slice) -> Expr:
        hi, lo = key.start, key.stop
        if key.step is not None or not isinstance(hi, int) or not isinstance(lo, int):
            raise EdslError("a bit slice is written x[hi:lo] with integer hi and lo")
        if not (0 <= lo <= hi < self.width):
            raise EdslError(f"slice [{hi}:{lo}] is out of range for {type_str(self.type)}")
        node = pb.Expr(slice=pb.Slice(operand=self.pb, hi=hi, lo=lo))
        return Expr(self.types, pb.Type(bits=hi - lo + 1), node)

    def _stack(self, what: str) -> pb.Type:
        if self.type.WhichOneof("kind") != "stack":
            raise EdslError(f"{what} needs a stack, got {type_str(self.type)}")
        return pb.Type(header=self.type.stack.header)

    @property
    def next(self) -> Expr:
        """`stack.next`: the target of an extract into a stack. Write-only."""
        element = self._stack("next")
        return Expr(self.types, element, None, pb.LValue(next=pb.Next(stack=self.lval)))

    @property
    def last_index(self) -> Expr:
        """`stack.lastIndex`, a bit<32>."""
        self._stack("last_index")
        return Expr(self.types, BIT32, pb.Expr(last_index=pb.LastIndex(stack=self.pb)))

    @property
    def last(self) -> Expr:
        """`stack.last`, which is `stack[stack.lastIndex]`: an lvalue when
        the stack is one."""
        return self[self.last_index]

    def is_valid(self) -> Expr:
        if self.type.WhichOneof("kind") != "header":
            raise EdslError(f"is_valid needs a header, got {type_str(self.type)}")
        return Expr(self.types, boolean, pb.Expr(is_valid=pb.IsValid(header=self.pb)))

    # -- operators ---------------------------------------------------------

    def _same(self, other: Operand, op: str) -> Expr:
        """`other` as an Expr of this expression's type."""
        if isinstance(other, Expr):
            if other.type != self.type:
                raise EdslError(
                    f"{op}: operands differ, {type_str(self.type)} vs {type_str(other.type)}"
                )
            return other
        return literal(self.types, other, self.type)

    def _binary(self, op: pb.BinaryOp, other: Expr, result: pb.Type) -> Expr:
        node = pb.Expr(binary=pb.Binary(op=op, left=self.pb, right=other.pb))
        return Expr(self.types, result, node)

    def _arith(self, op: pb.BinaryOp, other: Operand, sym: str) -> Expr:
        rhs = self._same(other, sym)
        if not is_bits(self.type):
            raise EdslError(f"{sym} needs bit<N> operands, got {type_str(self.type)}")
        return self._binary(op, rhs, self.type)

    def _compare(self, op: pb.BinaryOp, other: Operand, sym: str) -> Expr:
        rhs = self._same(other, sym)
        if not is_bits(self.type):
            raise EdslError(f"{sym} needs bit<N> operands, got {type_str(self.type)}")
        return self._binary(op, rhs, boolean)

    def _logic_or_bitwise(
        self,
        logic: pb.BinaryOp,
        bitwise: pb.BinaryOp,
        other: Operand,
        sym: str,
    ) -> Expr:
        rhs = self._same(other, sym)
        if is_boolean(self.type):
            return self._binary(logic, rhs, boolean)
        if is_bits(self.type):
            return self._binary(bitwise, rhs, self.type)
        raise EdslError(f"{sym} needs bit<N> or bool operands, got {type_str(self.type)}")

    def _shift(self, op: pb.BinaryOp, other: Operand, sym: str) -> Expr:
        """`self << other` or `self >> other`, typed as the left operand.

        The shift amount is any `bit<M>` and its width does not affect the
        result (docs/semantics.md, "Shifts"), so an int amount takes the
        left operand's width when it fits, as any other int operand would,
        and otherwise the smallest width that holds it: `bit<2> x << 4` is
        the P4 expression it looks like, with `4` a `bit<3>`, and is 0.
        """
        if not is_bits(self.type):
            raise EdslError(f"{sym} needs a bit<N> left operand, got {type_str(self.type)}")
        if isinstance(other, Expr):
            amount = other
        else:
            width = self.type.bits
            if isinstance(other, int) and not isinstance(other, bool) and other >= (1 << width):
                width = other.bit_length()
            amount = literal(self.types, other, pb.Type(bits=width))
        if not is_bits(amount.type):
            raise EdslError(f"{sym} needs a bit<N> shift amount, got {type_str(amount.type)}")
        return self._binary(op, amount, self.type)

    def __add__(self, other: Operand) -> Expr:
        return self._arith(pb.BINARY_OP_ADD, other, "+")

    def __radd__(self, other: Operand) -> Expr:
        return self._same(other, "+") + self

    def __sub__(self, other: Operand) -> Expr:
        return self._arith(pb.BINARY_OP_SUB, other, "-")

    def __rsub__(self, other: Operand) -> Expr:
        return self._same(other, "-") - self

    def __mul__(self, other: Operand) -> Expr:
        return self._arith(pb.BINARY_OP_MUL, other, "*")

    def __rmul__(self, other: Operand) -> Expr:
        return self._same(other, "*") * self

    def add_sat(self, other: Operand) -> Expr:
        """Saturating add, P4's `|+|`."""
        return self._arith(pb.BINARY_OP_ADD_SAT, other, "|+|")

    def sub_sat(self, other: Operand) -> Expr:
        """Saturating subtract, P4's `|-|`."""
        return self._arith(pb.BINARY_OP_SUB_SAT, other, "|-|")

    def __and__(self, other: Operand) -> Expr:
        """Bitwise and on bit<N>; logical and on bool."""
        return self._logic_or_bitwise(pb.BINARY_OP_AND, pb.BINARY_OP_BIT_AND, other, "&")

    def __rand__(self, other: Operand) -> Expr:
        return self._same(other, "&") & self

    def __or__(self, other: Operand) -> Expr:
        """Bitwise or on bit<N>; logical or on bool."""
        return self._logic_or_bitwise(pb.BINARY_OP_OR, pb.BINARY_OP_BIT_OR, other, "|")

    def __ror__(self, other: Operand) -> Expr:
        return self._same(other, "|") | self

    def __xor__(self, other: Operand) -> Expr:
        return self._arith(pb.BINARY_OP_BIT_XOR, other, "^")

    def __rxor__(self, other: Operand) -> Expr:
        return self._same(other, "^") ^ self

    def __lshift__(self, other: Operand) -> Expr:
        return self._shift(pb.BINARY_OP_SHL, other, "<<")

    def __rshift__(self, other: Operand) -> Expr:
        return self._shift(pb.BINARY_OP_SHR, other, ">>")

    def __invert__(self) -> Expr:
        """Bitwise complement on bit<N>; logical not on bool."""
        if is_boolean(self.type):
            op = pb.UNARY_OP_NOT
        elif is_bits(self.type):
            op = pb.UNARY_OP_COMPLEMENT
        else:
            raise EdslError(f"~ needs bit<N> or bool, got {type_str(self.type)}")
        return Expr(self.types, self.type, pb.Expr(unary=pb.Unary(op=op, operand=self.pb)))

    def __neg__(self) -> Expr:
        if not is_bits(self.type):
            raise EdslError(f"unary - needs bit<N>, got {type_str(self.type)}")
        node = pb.Expr(unary=pb.Unary(op=pb.UNARY_OP_NEGATE, operand=self.pb))
        return Expr(self.types, self.type, node)

    def __eq__(self, other: object) -> Expr:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._binary(pb.BINARY_OP_EQ, self._same(_operand(other), "=="), boolean)

    def __ne__(self, other: object) -> Expr:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._binary(pb.BINARY_OP_NE, self._same(_operand(other), "!="), boolean)

    def __lt__(self, other: Operand) -> Expr:
        return self._compare(pb.BINARY_OP_LT, other, "<")

    def __le__(self, other: Operand) -> Expr:
        return self._compare(pb.BINARY_OP_LE, other, "<=")

    def __gt__(self, other: Operand) -> Expr:
        return self._compare(pb.BINARY_OP_GT, other, ">")

    def __ge__(self, other: Operand) -> Expr:
        return self._compare(pb.BINARY_OP_GE, other, ">=")

    def __hash__(self) -> int:
        return id(self)

    def __bool__(self) -> bool:
        raise EdslError(
            "an Expr has no truth value; use b.if_(cond) for control flow, "
            "mux(cond, a, b) for a conditional value, and & | ~ for logic"
        )

    def cast(self, to: TypeLike) -> Expr:
        """An explicit cast: bit<N> to bit<M>, bool to bit<1>, bit<1> to bool."""
        target = as_type(to)
        allowed = (
            (is_bits(self.type) and is_bits(target))
            or (is_boolean(self.type) and target == pb.Type(bits=1))
            or (self.type == pb.Type(bits=1) and is_boolean(target))
        )
        if not allowed:
            raise EdslError(f"no cast from {type_str(self.type)} to {type_str(target)}")
        return Expr(self.types, target, pb.Expr(cast=pb.Cast(to=target, operand=self.pb)))


def _operand(value: object) -> Operand:
    if isinstance(value, Expr | int):
        return value
    raise EdslError(f"not an expression: {value!r}")


def literal(types: TypeTable, value: Operand, type: pb.Type) -> Expr:
    """`value` as an Expr of `type`: an Expr must already have it, a Python
    bool needs a bool context, a Python int a bit<N> context it fits."""
    if isinstance(value, Expr):
        if value.type != type:
            raise EdslError(f"expected {type_str(type)}, got {type_str(value.type)}")
        return value
    kind = type.WhichOneof("kind")
    if isinstance(value, bool):
        if kind != "boolean":
            raise EdslError(f"{value} is a bool, but {type_str(type)} is expected here")
        return Expr(types, type, pb.Expr(literal=pb.Literal(boolean=value)))
    if isinstance(value, int):
        if kind != "bits":
            raise EdslError(f"integer {value} needs a bit<N> context, not {type_str(type)}")
        if not 0 <= value < (1 << type.bits):
            raise EdslError(f"{value} does not fit in {type_str(type)}")
        lit = pb.Literal(bits=pb.BitsLiteral(width=type.bits, value=str(value)))
        return Expr(types, type, pb.Expr(literal=lit))
    raise EdslError(f"not an expression: {value!r}")


def constant(types: TypeTable, value: Operand, type: pb.Type) -> pb.Literal:
    """`value` as a `pb.Literal` of `type`, for entries, keysets and arguments."""
    expr = literal(types, value, type)
    if not expr.is_literal:
        raise EdslError(f"a constant is needed here, got {expr!r}")
    return expr.pb.literal


def concat(left: Expr, right: Expr, *rest: Expr) -> Expr:
    """`left ++ right ++ ...`, of width the sum, the first operand in the
    high bits. More than two operands chain from the left, as P4's `++`
    associates: `concat(a, b, c)` is `concat(concat(a, b), c)`."""
    out = _concat(left, right)
    for operand in rest:
        out = _concat(out, operand)
    return out


def _concat(left: Expr, right: Expr) -> Expr:
    if not isinstance(left, Expr) or not isinstance(right, Expr):
        raise EdslError("concat needs Exprs; an int has no width of its own here")
    if not (is_bits(left.type) and is_bits(right.type)):
        raise EdslError(f"concat needs bit<N> operands, got {left!r} and {right!r}")
    node = pb.Expr(binary=pb.Binary(op=pb.BINARY_OP_CONCAT, left=left.pb, right=right.pb))
    return Expr(left.types, pb.Type(bits=left.width + right.width), node)


def mux(condition: Operand, then: Operand, otherwise: Operand) -> Expr:
    """`condition ? then : otherwise`; the branches share one type, which an
    int branch takes from the other."""
    exprs = [e for e in (condition, then, otherwise) if isinstance(e, Expr)]
    if not exprs:
        raise EdslError("mux needs at least one Expr among its operands")
    types = exprs[0].types
    cond = literal(types, condition, boolean)
    if isinstance(then, Expr):
        t, o = then, then._same(otherwise, "mux")
    elif isinstance(otherwise, Expr):
        t, o = otherwise._same(then, "mux"), otherwise
    else:
        raise EdslError("mux needs an Expr branch to give an int branch its width")
    node = pb.Expr(mux=pb.Mux(condition=cond.pb, then=t.pb, otherwise=o.pb))
    return Expr(types, t.type, node)


class EnumType:
    """A declared enum; `color.RED` is the member literal."""

    def __init__(self, types: TypeTable, name: str, members: tuple[str, ...]) -> None:
        if not name:
            raise EdslError("an enum needs a name")
        if not members:
            raise EdslError(f"enum {name} needs at least one member")
        if len(set(members)) != len(members):
            raise EdslError(f"enum {name}: a member is repeated")
        self.types = types
        self.name = name
        self.members = members

    @property
    def type(self) -> pb.Type:
        return pb.Type(enum_type=self.name)

    def __getattr__(self, member: str) -> Expr:
        if member.startswith("_"):
            raise AttributeError(member)
        if member not in self.members:
            raise EdslError(
                f"enum {self.name} has no member {member!r}; members are {', '.join(self.members)}"
            )
        lit = pb.Literal(enum_member=pb.EnumLiteral(enum_type=self.name, member=member))
        return Expr(self.types, self.type, pb.Expr(literal=lit))

    def build(self) -> pb.EnumType:
        return pb.EnumType(name=self.name, members=self.members)


class Errors:
    """The program's error values by name: `p.errors.PacketTooShort`."""

    def __init__(self, types: TypeTable) -> None:
        self._types = types

    def __getattr__(self, name: str) -> Expr:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def __getitem__(self, name: str) -> Expr:
        if name not in self._types.errors:
            raise EdslError(f"no error {name!r}; errors are {', '.join(self._types.errors)}")
        return Expr(self._types, error_t, pb.Expr(literal=pb.Literal(error=name)))

    def __contains__(self, name: str) -> bool:
        return name in self._types.errors
