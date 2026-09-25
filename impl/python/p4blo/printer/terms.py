"""The printer's terms: types, literals, expressions, lvalues, and the
pieces of declarations they make up.

Each function turns one IR node into P4-16 text and needs nothing but the
node: no index, no architecture. Every non-leaf operand is parenthesized,
so precedence never matters, and literals carry their width, `8w255`.
"""

from __future__ import annotations

from collections.abc import Iterable

from p4blo.v0 import p4blo_pb2 as pb


class PrintError(Exception):
    """The program uses something the printer, or the architecture it
    prints for, cannot express."""


# The name of the packet parameter the printer adds to parsers and
# deparsers, where core.p4's packet_in and packet_out are.
PACKET = "packet"


# ---------------------------------------------------------------------------
# Types and literals
# ---------------------------------------------------------------------------


def print_type(t: pb.Type) -> str:
    """A type as P4 writes it; a stack as `t[N]`, valid only in declarations."""
    match t.WhichOneof("kind"):
        case "bits":
            return f"bit<{t.bits}>"
        case "boolean":
            return "bool"
        case "header":
            return t.header
        case "struct":
            return t.struct
        case "enum_type":
            return t.enum_type
        case "error":
            return "error"
        case "stack":
            return f"{t.stack.header}[{t.stack.size}]"
        case _:
            raise PrintError("type has no kind")


def print_literal(lit: pb.Literal) -> str:
    match lit.WhichOneof("value"):
        case "bits":
            return f"{lit.bits.width}w{lit.bits.value}"
        case "boolean":
            return "true" if lit.boolean else "false"
        case "enum_member":
            return f"{lit.enum_member.enum_type}.{lit.enum_member.member}"
        case "error":
            return f"error.{lit.error}"
        case _:
            raise PrintError("literal has no value")


def print_bits(width: int, value: int) -> str:
    return f"{width}w{value}"


# ---------------------------------------------------------------------------
# Expressions and lvalues
# ---------------------------------------------------------------------------

_UNARY_OPS: dict[int, str] = {
    pb.UNARY_OP_NOT: "!",
    pb.UNARY_OP_COMPLEMENT: "~",
    pb.UNARY_OP_NEGATE: "-",
}

_BINARY_OPS: dict[int, str] = {
    pb.BINARY_OP_ADD: "+",
    pb.BINARY_OP_SUB: "-",
    pb.BINARY_OP_MUL: "*",
    pb.BINARY_OP_ADD_SAT: "|+|",
    pb.BINARY_OP_SUB_SAT: "|-|",
    pb.BINARY_OP_BIT_AND: "&",
    pb.BINARY_OP_BIT_OR: "|",
    pb.BINARY_OP_BIT_XOR: "^",
    pb.BINARY_OP_SHL: "<<",
    pb.BINARY_OP_SHR: ">>",
    pb.BINARY_OP_CONCAT: "++",
    pb.BINARY_OP_EQ: "==",
    pb.BINARY_OP_NE: "!=",
    pb.BINARY_OP_LT: "<",
    pb.BINARY_OP_LE: "<=",
    pb.BINARY_OP_GT: ">",
    pb.BINARY_OP_GE: ">=",
    pb.BINARY_OP_AND: "&&",
    pb.BINARY_OP_OR: "||",
}

# Expression kinds that bind tighter than any operator and need no
# parentheses as operands.
_ATOMS = frozenset({"literal", "var", "member", "index", "last_index", "is_valid", "lookahead"})


def print_expr(e: pb.Expr) -> str:
    """An expression, with every non-leaf sub-expression parenthesized."""
    match e.WhichOneof("kind"):
        case "literal":
            return print_literal(e.literal)
        case "var":
            return e.var
        case "member":
            return f"{_operand(e.member.base)}.{e.member.field}"
        case "index":
            return f"{_operand(e.index.base)}[{print_expr(e.index.index)}]"
        case "last_index":
            return f"{_operand(e.last_index.stack)}.lastIndex"
        case "unary":
            op = _UNARY_OPS.get(e.unary.op)
            if op is None:
                raise PrintError("unary expression has no operator")
            return f"{op}{_operand(e.unary.operand)}"
        case "binary":
            op = _BINARY_OPS.get(e.binary.op)
            if op is None:
                raise PrintError("binary expression has no operator")
            return f"{_operand(e.binary.left)} {op} {_operand(e.binary.right)}"
        case "cast":
            return f"({print_type(e.cast.to)}) {_operand(e.cast.operand)}"
        case "slice":
            return f"{_operand(e.slice.operand)}[{e.slice.hi}:{e.slice.lo}]"
        case "is_valid":
            return f"{_operand(e.is_valid.header)}.isValid()"
        case "mux":
            m = e.mux
            return f"{_operand(m.condition)} ? {_operand(m.then)} : {_operand(m.otherwise)}"
        case "lookahead":
            return f"{PACKET}.lookahead<{print_type(e.lookahead.type)}>()"
        case _:
            raise PrintError("expression has no kind")


def _operand(e: pb.Expr) -> str:
    text = print_expr(e)
    return text if e.WhichOneof("kind") in _ATOMS else f"({text})"


def print_lvalue(lv: pb.LValue) -> str:
    match lv.WhichOneof("kind"):
        case "var":
            return lv.var
        case "member":
            return f"{print_lvalue(lv.member.base)}.{lv.member.field}"
        case "index":
            return f"{print_lvalue(lv.index.base)}[{print_expr(lv.index.index)}]"
        case "next":
            return f"{print_lvalue(lv.next.stack)}.next"
        case _:
            raise PrintError("lvalue has no kind")


def print_arg(arg: pb.Arg) -> str:
    match arg.WhichOneof("kind"):
        case "expr":
            return print_expr(arg.expr)
        case "lvalue":
            return print_lvalue(arg.lvalue)
        case _:
            raise PrintError("argument has no kind")


def print_args(args: Iterable[pb.Arg]) -> str:
    return ", ".join(print_arg(a) for a in args)


def print_action_call(call: pb.ActionCall) -> str:
    return f"{call.action}({', '.join(print_literal(a) for a in call.args)})"


# ---------------------------------------------------------------------------
# Pieces of declarations
# ---------------------------------------------------------------------------

_DIRECTIONS: dict[int, str] = {
    pb.DIRECTION_NONE: "",
    pb.DIRECTION_IN: "in ",
    pb.DIRECTION_OUT: "out ",
    pb.DIRECTION_INOUT: "inout ",
}


def print_param(param: pb.Param) -> str:
    direction = _DIRECTIONS.get(param.direction)
    if direction is None:
        raise PrintError(f"parameter {param.name!r} has no direction")
    return f"{direction}{print_type(param.type)} {param.name}"


def print_target(target: pb.Target) -> str:
    match target.WhichOneof("kind"):
        case "state":
            return target.state
        case "accept":
            return "accept"
        case "reject":
            return "reject"
        case _:
            raise PrintError("transition target has no kind")


def _print_key_set(ks: pb.KeySet) -> str:
    match ks.WhichOneof("kind"):
        case "exact":
            return print_literal(ks.exact)
        case "masked":
            return f"{print_literal(ks.masked.value)} &&& {print_literal(ks.masked.mask)}"
        case "range":
            return f"{print_literal(ks.range.lo)}..{print_literal(ks.range.hi)}"
        case "dont_care":
            return "_"
        case _:
            raise PrintError("key set has no kind")


def print_key_sets(sets: Iterable[pb.KeySet]) -> str:
    sets = list(sets)
    if all(s.WhichOneof("kind") == "dont_care" for s in sets):
        return "default"
    if len(sets) == 1:
        return _print_key_set(sets[0])
    return f"({', '.join(_print_key_set(s) for s in sets)})"


_MATCH_KINDS: dict[int, str] = {
    pb.MATCH_KIND_EXACT: "exact",
    pb.MATCH_KIND_LPM: "lpm",
    pb.MATCH_KIND_TERNARY: "ternary",
}


def print_key(key: pb.Key) -> str:
    kind = _MATCH_KINDS.get(key.match_kind)
    if kind is None:
        raise PrintError("table key has no match kind")
    expr = print_expr(key.expr)
    text = f"{expr}: {kind}"
    if key.name and key.name != expr:
        text += f' @name("{key.name}")'
    return f"{text};"


def print_key_value(value: pb.KeyValue, match_kind: int, width: int) -> str:
    match value.WhichOneof("kind"):
        case "exact":
            return print_bits(width, int(value.exact))
        case "lpm":
            prefix = value.lpm.prefix_len
            if prefix > width:
                raise PrintError(f"prefix length {prefix} exceeds key width {width}")
            mask = ((1 << prefix) - 1) << (width - prefix)
            return f"{print_bits(width, int(value.lpm.value))} &&& {print_bits(width, mask)}"
        case "ternary":
            t = value.ternary
            return f"{print_bits(width, int(t.value))} &&& {print_bits(width, int(t.mask))}"
        case _:
            raise PrintError("entry key value has no kind")
