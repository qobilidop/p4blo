"""What the IL bridge's modules share: errors, values, IR helpers, scopes.

`p4blo.frontend.spectec_il` translates programs, `p4blo.frontend.blocks`
their blocks and `p4blo.frontend.v1model` the architecture layer; this
module holds what all three use: the two errors that name the coverage
page's rows and the IL productions, compile-time values, small builders of
IR messages, readers of IL nodes, and the scopes names are resolved in.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from google.protobuf.message import Message

from p4blo.frontend import il
from p4blo.frontend.il import Node
from p4blo.v0 import p4blo_pb2 as pb

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FrontendError(Exception):
    """The program cannot be translated."""


class Excluded(FrontendError):
    """The program uses a construct docs/p4-spec-coverage.md excludes.

    `row` is the row's IL construct as the page writes it, and `category`
    the exclusion category: "by thesis", "by elaboration" or "by scope".
    """

    def __init__(self, row: str, category: str, detail: str = "") -> None:
        self.row = row
        self.category = category
        self.detail = detail
        text = f"excluded, {category}: {row}"
        super().__init__(f"{text} ({detail})" if detail else text)


class NotTranslated(FrontendError):
    """A construct the bridge does not translate yet, named by production."""

    def __init__(self, production: str, detail: str = "") -> None:
        self.production = production
        self.detail = detail
        text = f"not translated: {production}"
        super().__init__(f"{text} ({detail})" if detail else text)


# ---------------------------------------------------------------------------
# Compile-time values
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bits:
    width: int
    value: int


@dataclass(frozen=True)
class Int:
    """An arbitrary-precision `int`, before a cast gives it a width."""

    value: int


@dataclass(frozen=True)
class ErrorVal:
    name: str


@dataclass(frozen=True)
class EnumVal:
    enum_type: str
    member: str


type Val = Bits | Int | bool | ErrorVal | EnumVal


def _wrap(width: int, value: int) -> Bits:
    return Bits(width, value % (1 << width))


# ---------------------------------------------------------------------------
# IR construction helpers
# ---------------------------------------------------------------------------


def bits_type(width: int) -> pb.Type:
    return pb.Type(bits=width)


BOOL = pb.Type(boolean=pb.BoolType())
ERROR = pb.Type(error=pb.ErrorType())


def lit_bits(width: int, value: int) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=width, value=str(value))))


def lit_bool(value: bool) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(boolean=value))


def var(name: str) -> pb.Expr:
    return pb.Expr(var=name)


def member(base: pb.Expr, name: str) -> pb.Expr:
    return pb.Expr(member=pb.Member(base=base, field=name))


def binary(op: int, left: pb.Expr, right: pb.Expr) -> pb.Expr:
    return pb.Expr(binary=pb.Binary(op=op, left=left, right=right))  # type: ignore[arg-type]


def unary(op: int, operand: pb.Expr) -> pb.Expr:
    return pb.Expr(unary=pb.Unary(op=op, operand=operand))  # type: ignore[arg-type]


def lvar(name: str) -> pb.LValue:
    return pb.LValue(var=name)


def lmember(base: pb.LValue, name: str) -> pb.LValue:
    return pb.LValue(member=pb.LMember(base=base, field=name))


def assign(target: pb.LValue, value: pb.Expr) -> pb.Stmt:
    return pb.Stmt(assign=pb.Assign(target=target, value=value))


def literal_of(val: Val) -> pb.Literal | None:
    """The IR literal of a compile-time value; None for an unsized int."""
    match val:
        case bool():
            return pb.Literal(boolean=val)
        case Bits():
            return pb.Literal(bits=pb.BitsLiteral(width=val.width, value=str(val.value)))
        case ErrorVal():
            return pb.Literal(error=val.name)
        case EnumVal():
            return pb.Literal(
                enum_member=pb.EnumLiteral(enum_type=val.enum_type, member=val.member)
            )
        case Int():
            return None


def expr_to_lvalue(e: pb.Expr) -> pb.LValue | None:
    """The lvalue an access-path expression denotes, or None."""
    match e.WhichOneof("kind"):
        case "var":
            return lvar(e.var)
        case "member":
            base = expr_to_lvalue(e.member.base)
            return None if base is None else lmember(base, e.member.field)
        case "index":
            base = expr_to_lvalue(e.index.base)
            if base is None:
                return None
            return pb.LValue(index=pb.LIndex(base=base, index=e.index.index))
        case _:
            return None


def lvalue_to_expr(lv: pb.LValue) -> pb.Expr:
    match lv.WhichOneof("kind"):
        case "var":
            return var(lv.var)
        case "member":
            return member(lvalue_to_expr(lv.member.base), lv.member.field)
        case "index":
            return pb.Expr(index=pb.Index(base=lvalue_to_expr(lv.index.base), index=lv.index.index))
        case _:
            raise NotTranslated("lvalueIR", "stack.next read as a value")


type Access = tuple[str | int | None, ...]


def access(e: pb.Expr | pb.LValue) -> Access | None:
    """The validator's static access path of an lvalue-shaped expression:
    the variable, then a field name or a literal index (None when computed)
    per step; None when `e` is not an access path."""
    kind = e.WhichOneof("kind")
    if kind == "var":
        return (e.var,)
    if kind == "member":
        base = access(e.member.base)
        return None if base is None else (*base, e.member.field)
    if kind == "index":
        base = access(e.index.base)
        if base is None:
            return None
        i = e.index.index
        known = i.WhichOneof("kind") == "literal" and i.literal.WhichOneof("value") == "bits"
        return (*base, int(i.literal.bits.value) if known else None)
    if kind == "next" and isinstance(e, pb.LValue):
        base = access(e.next.stack)
        return None if base is None else (*base, None)
    return None


def reads(e: pb.Expr) -> list[Access]:
    """The access paths an expression reads, each maximal."""
    out: list[Access] = []

    def visit(m: Message) -> None:
        if isinstance(m, pb.Expr):
            a = access(m)
            if a is not None:
                out.append(a)
                return
        for _, value in m.ListFields():
            if isinstance(value, Message):
                visit(value)
            elif not isinstance(value, str | bytes | int | float | bool):
                for x in value:
                    if isinstance(x, Message):
                        visit(x)

    visit(e)
    return out


def may_alias(a: Access, b: Access) -> bool:
    """The validator's rule: paths agree wherever both are known."""
    return all(x is None or y is None or x == y for x, y in zip(a, b, strict=False))


# ---------------------------------------------------------------------------
# Small IL readers
# ---------------------------------------------------------------------------

UNALIAS = ("TYPEDEF % %", "TYPE % %")


def strip_alias(t: Node) -> Node:
    """A type with typedefs and newtypes removed (P4 `type` is elaborated
    like `typedef`: a newtype only forbids implicit casts)."""
    while t.c in UNALIAS:
        t = t.node(1)
    return t


def typed_parts(te: Node) -> tuple[Node, Node, str]:
    """A typed expression's expression, type and compile-time-known note."""
    if te.c != "% # %":
        raise il.ILError(f"expected a typed expression, got {te.t} {te.c!r}")
    note = te.node(1)
    return te.node(0), note.node(0), note.node(1).c


def lvalue_parts(tl: Node) -> tuple[Node, Node]:
    if tl.c != "% # %":
        raise il.ILError(f"expected a typed lvalue, got {tl.t} {tl.c!r}")
    return tl.node(0), tl.node(1).node(0)


def prefixed_name(n: Node) -> tuple[str, bool]:
    """A prefixedNameIR as (name, top-level?)."""
    if n.c == "_BARE %":
        return n.text(0), False
    if n.c == ". %":
        return n.text(0), True
    raise il.ILError(f"not a prefixed name: {n.c!r}")


def direction(d: Node) -> int:
    return {
        "IN": pb.DIRECTION_IN,
        "OUT": pb.DIRECTION_OUT,
        "INOUT": pb.DIRECTION_INOUT,
        "/* empty */": pb.DIRECTION_NONE,
    }[d.c]


@dataclass(frozen=True)
class ParamIL:
    """A parameterIR: `annotations direction type name default`."""

    name: str
    direction: int
    type: Node
    node: Node

    @staticmethod
    def of(p: Node) -> ParamIL:
        if p.c != "% % % % %":
            raise il.ILError(f"expected a parameter, got {p.c!r}")
        if p.opt(4) is not None:
            raise NotTranslated("parameterIR", f"{p.text(3)} has a default value")
        return ParamIL(p.text(3), direction(p.node(1)), p.node(2), p)


def is_packet_type(t: Node) -> str | None:
    t = strip_alias(t)
    if t.c == "EXTERN % <%> %" and t.text(0) in ("packet_in", "packet_out"):
        return t.text(0)
    return None


# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------


@dataclass
class VarB:
    """An IR variable: a block param or local, or an action param."""

    name: str


@dataclass
class ConstB:
    value: Val


@dataclass
class TableB:
    name: str


@dataclass
class ActionB:
    """An action visible from a block: its IL declaration and IR name."""

    name: str
    decl: Node


@dataclass
class BlockInstB:
    """A sub-parser or sub-control instance: calls go to `block`."""

    block: str
    decl: Node


@dataclass
class ExternInstB:
    instance: str
    extern_type: str


@dataclass
class FunctionB:
    decl: Node


@dataclass
class ExternFunctionB:
    name: str
    decl: Node


@dataclass
class IntrinsicB:
    """The architecture's intrinsic metadata parameter (v1model's
    `standard_metadata`), which only the architecture binding may read."""

    name: str


@dataclass
class BoundArgB:
    """An action parameter bound in a table's action list: every use of it
    in the per-table copy is the bound expression, translated where used, in
    the scope of the table that bound it."""

    te: Node
    scope: Scope


@dataclass
class BadConstB:
    """A constant whose value the bridge cannot represent; using it fails."""

    error: FrontendError


type Binding = (
    VarB
    | ConstB
    | TableB
    | ActionB
    | BlockInstB
    | ExternInstB
    | FunctionB
    | ExternFunctionB
    | IntrinsicB
    | BoundArgB
    | BadConstB
)


class Scope:
    """Nested name bindings, innermost last."""

    def __init__(self, frames: list[dict[str, Binding]] | None = None) -> None:
        self.frames: list[dict[str, Binding]] = frames if frames is not None else [{}]

    def child(self) -> Scope:
        return Scope([*self.frames, {}])

    def bind(self, name: str, binding: Binding) -> None:
        self.frames[-1][name] = binding

    def lookup(self, name: str, top: bool = False) -> Binding | None:
        frames = self.frames[:1] if top else reversed(self.frames)
        for frame in frames:
            if name in frame:
                return frame[name]
        return None


# ---------------------------------------------------------------------------
# Renaming and walking IR
# ---------------------------------------------------------------------------


def rename_block_vars(block: pb.Block, mapping: dict[str, str]) -> None:
    """Rename block params and locals and every reference to them; an
    action's own parameters shadow the block's names inside it."""
    for v in [*block.params, *block.locals]:
        v.name = mapping.get(v.name, v.name)
    _rename_in(block.body, mapping)
    for s in block.states:
        _rename_in(s.body, mapping)
        _rename_in([s.transition], mapping)
    for t in block.tables:
        _rename_in(t.keys, mapping)
    for a in block.actions:
        shadow = {p.name for p in a.params}
        _rename_in(a.body, {k: v for k, v in mapping.items() if k not in shadow})


def _rename_in(messages: Iterable[object], mapping: dict[str, str]) -> None:
    for m in messages:
        _rename(m, mapping)


def _rename(m: object, mapping: dict[str, str]) -> None:
    if isinstance(m, pb.Expr | pb.LValue) and m.WhichOneof("kind") == "var" and m.var in mapping:
        m.var = mapping[m.var]
        return
    list_fields = getattr(m, "ListFields", None)
    if list_fields is None:
        return
    for fd, value in list_fields():
        if fd.message_type is None:
            continue
        if isinstance(value, Message):
            _rename(value, mapping)
        else:
            for x in value:
                _rename(x, mapping)


def walk_stmts(stmts: Iterable[pb.Stmt]) -> Iterator[pb.Stmt]:
    for s in stmts:
        yield s
        if s.WhichOneof("kind") == "conditional":
            yield from walk_stmts(s.conditional.then)
            yield from walk_stmts(s.conditional.otherwise)
