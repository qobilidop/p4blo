"""Static types and widths of IR types and expressions.

Expressions carry no annotations (docs/design.md, "The IR is
post-elaboration"): a leaf's type comes from its declaration and an
operator's from its operands. `type_of` recomputes that where the interpreter
needs a width before it has a value: the width of a table key at installation
and of the header an `extract` or `lookahead` reads.
"""

from __future__ import annotations

from p4blo.interp.api import InterpError
from p4blo.ir import BlockScope, Index
from p4blo.v0 import p4blo_pb2 as pb

BITS_32 = pb.Type(bits=32)
BOOLEAN = pb.Type(boolean=pb.BoolType())

BOOLEAN_OPS = frozenset(
    {
        pb.BINARY_OP_EQ,
        pb.BINARY_OP_NE,
        pb.BINARY_OP_LT,
        pb.BINARY_OP_LE,
        pb.BINARY_OP_GT,
        pb.BINARY_OP_GE,
        pb.BINARY_OP_AND,
        pb.BINARY_OP_OR,
    }
)


def width_of(type: pb.Type, index: Index) -> int:
    """The number of packet bits a value of `type` occupies."""
    match type.WhichOneof("kind"):
        case "bits":
            return type.bits
        case "boolean":
            return 1
        case "header":
            return sum(width_of(f.type, index) for f in index.header_types[type.header].fields)
        case "struct":
            return sum(width_of(f.type, index) for f in index.struct_types[type.struct].fields)
        case "stack":
            return type.stack.size * width_of(pb.Type(header=type.stack.header), index)
        case kind:
            raise InterpError(f"a value of kind {kind!r} has no width")


def literal_type(literal: pb.Literal) -> pb.Type:
    match literal.WhichOneof("value"):
        case "bits":
            return pb.Type(bits=literal.bits.width)
        case "boolean":
            return BOOLEAN
        case "enum_member":
            return pb.Type(enum_type=literal.enum_member.enum_type)
        case "error":
            return pb.Type(error=pb.ErrorType())
        case _:
            raise InterpError("literal has no value")


def type_of(expr: pb.Expr, index: Index, scope: BlockScope, action: str | None = None) -> pb.Type:
    """The static type of `expr` as seen from `scope`, or from `action` in it."""

    def sub(e: pb.Expr) -> pb.Type:
        return type_of(e, index, scope, action)

    match expr.WhichOneof("kind"):
        case "literal":
            return literal_type(expr.literal)
        case "var":
            return scope.var(expr.var, action).type
        case "member":
            base = sub(expr.member.base)
            name = base.header if base.WhichOneof("kind") == "header" else base.struct
            for f in index.fields(name):
                if f.name == expr.member.field:
                    return f.type
            raise InterpError(f"{name} has no field {expr.member.field!r}")
        case "index":
            return pb.Type(header=sub(expr.index.base).stack.header)
        case "last_index":
            return BITS_32
        case "unary":
            return sub(expr.unary.operand)
        case "binary":
            if expr.binary.op in BOOLEAN_OPS:
                return BOOLEAN
            left = sub(expr.binary.left)
            if expr.binary.op == pb.BINARY_OP_CONCAT:
                return pb.Type(bits=left.bits + sub(expr.binary.right).bits)
            return left
        case "cast":
            return expr.cast.to
        case "slice":
            return pb.Type(bits=expr.slice.hi - expr.slice.lo + 1)
        case "is_valid":
            return BOOLEAN
        case "mux":
            return sub(expr.mux.then)
        case "lookahead":
            return expr.lookahead.type
        case _:
            raise InterpError("expression has no kind")
