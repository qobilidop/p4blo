"""Static types and widths of IR types and expressions.

Expressions carry no annotations (docs/design.md, "The IR is
post-elaboration"): a leaf's type comes from its declaration and an
operator's from its operands. `type_of` asks the validator's typer for that
where the interpreter needs a width before it has a value, the width of a
table key at installation; the typer is the one implementation, so the
interpreter and the validator cannot disagree about a type.
"""

from __future__ import annotations

from p4blo.interp.api import InterpError
from p4blo.ir import BlockScope, Index
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator import ValidationError
from p4blo.validator.typer import expr_type


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


def type_of(expr: pb.Expr, index: Index, scope: BlockScope, action: str | None = None) -> pb.Type:
    """The static type of `expr` as seen from `scope`, or from `action` in it:
    the validator's typer (`p4blo.validator.typer.expr_type`), with a failure
    reported as the interpreter's own error."""
    try:
        return expr_type(expr, index, scope, action)
    except ValidationError as e:
        raise InterpError(str(e)) from None
