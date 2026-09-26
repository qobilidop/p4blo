"""The expression typer: the type of every expression and lvalue.

Expressions carry no annotations (docs/design.md, "The IR is
post-elaboration"): a leaf's type comes from its declaration and an
operator's from its operands, as the comments on the operators in the schema
say. `Typer` computes that bottom-up and reports every problem on the way,
which is how the validator typechecks. It is also the only code in the
package that computes an expression's type: `expr_type` runs the same
methods on a program `check` accepted, for the interpreter, the printer and
the STF reader, which need a width before they have a value (the width of a
table key, of the header an `extract` or `lookahead` reads). One function
means the validator and its consumers cannot disagree about a type;
impl/python/tests/validator/test_typer.py guards the seam.
"""

from __future__ import annotations

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    CAST_INVALID,
    EXPR_INVALID,
    LVALUE_READONLY,
    NEXT_ONLY_EXTRACT,
    PARSER_ONLY,
    REF_UNRESOLVED,
    SLICE_RANGE,
    TYPE_INVALID,
    TYPE_MISMATCH,
    Diagnostic,
    ValidationError,
)
from p4blo.validator.names import (
    DIRECTION_NAMES,
    Scope,
)
from p4blo.validator.types import (
    BITS32,
    BOOLEAN,
    TypeChecks,
    bits_type,
    describe,
    is_bits,
    is_boolean,
    is_header,
    is_stack,
    kind_of,
    same_type,
)


class Typer(TypeChecks):
    """The types of expressions and lvalues, reporting every problem found."""

    def expect_expr(self, expr: pb.Expr, ok, what: str, scope: Scope, path: str) -> pb.Type | None:
        """The type of `expr`, reporting TYPE_MISMATCH unless `ok(type)`."""
        t = self.type_of(expr, scope, path)
        if t is not None and not ok(t):
            self.report(TYPE_MISMATCH, f"expected {what}, got {describe(t)}", path)
            return None
        return t

    def type_of(self, expr: pb.Expr, scope: Scope, path: str) -> pb.Type | None:
        """The type of an expression, or None once a problem is reported.

        Bottom-up: each operator's result type is determined by its operands,
        as the comments on the operators in the schema say.
        """
        match expr.WhichOneof("kind"):
            case "literal":
                return self.type_of_literal(expr.literal, f"{path}.literal")
            case "var":
                decl = self.resolve_var(expr.var, scope, f"{path}.var")
                if decl is None or not self.type_ok(decl.type):
                    return None
                return decl.type
            case "member":
                base = self.type_of(expr.member.base, scope, f"{path}.member.base")
                return self.type_of_field(base, expr.member.field, f"{path}.member")
            case "index":
                return self.type_of_index(expr.index.base, expr.index.index, scope, f"{path}.index")
            case "last_index":
                # P4 §8.18 and SpecTec's Expr_ok/headerStack-lastIndex allow
                # lastIndex only in a parser (docs/ir-semantics.md, "`hs.lastIndex`").
                if not scope.in_parser:
                    self.report(PARSER_ONLY, "stack.lastIndex is allowed only in a parser", path)
                self.expect_expr(
                    expr.last_index.stack, is_stack, "a stack", scope, f"{path}.last_index.stack"
                )
                return BITS32
            case "unary":
                return self.type_of_unary(expr.unary, scope, f"{path}.unary")
            case "binary":
                return self.type_of_binary(expr.binary, scope, f"{path}.binary")
            case "cast":
                return self.type_of_cast(expr.cast, scope, f"{path}.cast")
            case "slice":
                return self.type_of_slice(expr.slice, scope, f"{path}.slice")
            case "is_valid":
                self.expect_expr(
                    expr.is_valid.header, is_header, "a header", scope, f"{path}.is_valid.header"
                )
                return BOOLEAN
            case "mux":
                return self.type_of_mux(expr.mux, scope, f"{path}.mux")
            case "lookahead":
                return self.type_of_lookahead(expr.lookahead, scope, f"{path}.lookahead")
            case _:
                self.report(EXPR_INVALID, "expression has no kind", path)
                return None

    def type_of_field(self, base: pb.Type | None, name: str, path: str) -> pb.Type | None:
        """The type of field `name` of a header or struct value of type `base`."""
        if base is None:
            return None
        if kind_of(base) not in ("header", "struct"):
            self.report(
                TYPE_MISMATCH, f"expected a header or struct, got {describe(base)}", f"{path}.base"
            )
            return None
        type_name = base.header if is_header(base) else base.struct
        for f in self.idx.fields(type_name):
            if f.name == name:
                return f.type if self.type_ok(f.type) else None
        self.report(REF_UNRESOLVED, f"{describe(base)} has no field {name!r}", f"{path}.field")
        return None

    def type_of_index(
        self, base: pb.Expr, index: pb.Expr, scope: Scope, path: str
    ) -> pb.Type | None:
        stack = self.expect_expr(base, is_stack, "a stack", scope, f"{path}.base")
        self.expect_expr(index, is_bits, "bits", scope, f"{path}.index")
        return pb.Type(header=stack.stack.header) if stack is not None else None

    def type_of_unary(self, expr: pb.Unary, scope: Scope, path: str) -> pb.Type | None:
        match expr.op:
            case pb.UNARY_OP_NOT:
                return self.expect_expr(
                    expr.operand, is_boolean, "boolean", scope, f"{path}.operand"
                )
            case pb.UNARY_OP_COMPLEMENT | pb.UNARY_OP_NEGATE:
                return self.expect_expr(expr.operand, is_bits, "bits", scope, f"{path}.operand")
            case _:
                self.report(EXPR_INVALID, "unary operator is unspecified", f"{path}.op")
                self.type_of(expr.operand, scope, f"{path}.operand")
                return None

    def type_of_binary(self, expr: pb.Binary, scope: Scope, path: str) -> pb.Type | None:
        left = self.type_of(expr.left, scope, f"{path}.left")
        right = self.type_of(expr.right, scope, f"{path}.right")
        if left is None or right is None:
            return None

        def mismatch(message: str) -> None:
            self.report(
                TYPE_MISMATCH,
                f"{pb.BinaryOp.Name(expr.op)}: {message}; "
                f"got {describe(left)} and {describe(right)}",
                path,
            )

        match expr.op:
            case (
                pb.BINARY_OP_ADD
                | pb.BINARY_OP_SUB
                | pb.BINARY_OP_MUL
                | pb.BINARY_OP_ADD_SAT
                | pb.BINARY_OP_SUB_SAT
                | pb.BINARY_OP_BIT_AND
                | pb.BINARY_OP_BIT_OR
                | pb.BINARY_OP_BIT_XOR
            ):
                if is_bits(left) and same_type(left, right):
                    return left
                mismatch("operands must be bits of one width")
            case pb.BINARY_OP_SHL | pb.BINARY_OP_SHR:
                if is_bits(left) and is_bits(right):
                    return left
                mismatch("operands must be bits")
            case pb.BINARY_OP_CONCAT:
                if is_bits(left) and is_bits(right):
                    return bits_type(left.bits + right.bits)
                mismatch("operands must be bits")
            case pb.BINARY_OP_EQ | pb.BINARY_OP_NE:
                if same_type(left, right):
                    return BOOLEAN
                mismatch("operands must have one type")
            case pb.BINARY_OP_LT | pb.BINARY_OP_LE | pb.BINARY_OP_GT | pb.BINARY_OP_GE:
                if is_bits(left) and same_type(left, right):
                    return BOOLEAN
                mismatch("operands must be bits of one width")
            case pb.BINARY_OP_AND | pb.BINARY_OP_OR:
                if is_boolean(left) and is_boolean(right):
                    return BOOLEAN
                mismatch("operands must be boolean")
            case _:
                self.report(EXPR_INVALID, "binary operator is unspecified", f"{path}.op")
        return None

    def type_of_cast(self, expr: pb.Cast, scope: Scope, path: str) -> pb.Type | None:
        to_ok = self.check_type(expr.to, f"{path}.to")
        operand = self.type_of(expr.operand, scope, f"{path}.operand")
        if not to_ok or operand is None:
            return None
        to = expr.to
        allowed = (
            (is_bits(operand) and is_bits(to))
            or (is_boolean(operand) and is_bits(to) and to.bits == 1)
            or (is_bits(operand) and operand.bits == 1 and is_boolean(to))
        )
        if not allowed:
            self.report(CAST_INVALID, f"cannot cast {describe(operand)} to {describe(to)}", path)
            return None
        return to

    def type_of_slice(self, expr: pb.Slice, scope: Scope, path: str) -> pb.Type | None:
        operand = self.expect_expr(expr.operand, is_bits, "bits", scope, f"{path}.operand")
        if operand is None:
            return None
        if not expr.lo <= expr.hi < operand.bits:
            self.report(
                SLICE_RANGE,
                f"[{expr.hi}:{expr.lo}] needs lo <= hi < {operand.bits}",
                path,
            )
            return None
        return bits_type(expr.hi - expr.lo + 1)

    def type_of_mux(self, expr: pb.Mux, scope: Scope, path: str) -> pb.Type | None:
        self.expect_expr(expr.condition, is_boolean, "boolean", scope, f"{path}.condition")
        then = self.type_of(expr.then, scope, f"{path}.then")
        else_ = self.type_of(expr.otherwise, scope, f"{path}.otherwise")
        if then is None or else_ is None:
            return None
        if not same_type(then, else_):
            self.report(
                TYPE_MISMATCH,
                f"branches differ: {describe(then)} and {describe(else_)}",
                path,
            )
            return None
        return then

    def type_of_lookahead(self, expr: pb.Lookahead, scope: Scope, path: str) -> pb.Type | None:
        if not scope.in_parser:
            self.report(PARSER_ONLY, "lookahead is allowed only in a parser", path)
        if not self.check_type(expr.type, f"{path}.type"):
            return None
        # What has a packet width: bool is one bit (docs/ir-semantics.md, "lookahead").
        if not (is_bits(expr.type) or is_boolean(expr.type) or is_header(expr.type)):
            self.report(
                TYPE_MISMATCH,
                f"lookahead reads bits, a boolean or a header, not {describe(expr.type)}",
                f"{path}.type",
            )
            return None
        return expr.type

    def expect_lvalue(
        self, lvalue: pb.LValue, ok, what: str, scope: Scope, path: str
    ) -> pb.Type | None:
        t = self.type_of_lvalue(lvalue, scope, path)
        if t is not None and not ok(t):
            self.report(TYPE_MISMATCH, f"expected {what}, got {describe(t)}", path)
            return None
        return t

    def type_of_lvalue(self, lvalue: pb.LValue, scope: Scope, path: str) -> pb.Type | None:
        """The type of an lvalue, or None once a problem is reported. The
        root must be writable: not an `in` or directionless param."""
        match lvalue.WhichOneof("kind"):
            case "var":
                decl = self.resolve_var(lvalue.var, scope, f"{path}.var")
                if decl is None:
                    return None
                if isinstance(decl, pb.Param) and decl.direction in (
                    pb.DIRECTION_IN,
                    pb.DIRECTION_NONE,
                ):
                    self.report(
                        LVALUE_READONLY,
                        f"{DIRECTION_NAMES[decl.direction]} param {decl.name!r} cannot be written",
                        f"{path}.var",
                    )
                    return None
                return decl.type if self.type_ok(decl.type) else None
            case "member":
                base = self.type_of_lvalue(lvalue.member.base, scope, f"{path}.member.base")
                return self.type_of_field(base, lvalue.member.field, f"{path}.member")
            case "index":
                stack = self.expect_lvalue(
                    lvalue.index.base, is_stack, "a stack", scope, f"{path}.index.base"
                )
                self.expect_expr(lvalue.index.index, is_bits, "bits", scope, f"{path}.index.index")
                return pb.Type(header=stack.stack.header) if stack is not None else None
            case "next":
                # `check_extract` handles the one place it may appear.
                self.report(NEXT_ONLY_EXTRACT, "stack.next is only the target of an extract", path)
                return None
            case _:
                self.report(EXPR_INVALID, "lvalue has no kind", path)
                return None


def expr_type(
    expr: pb.Expr, index: ir.Index, scope: ir.BlockScope, action: str | None = None
) -> pb.Type:
    """The type of `expr` in a program `check` accepted, as seen from the
    body of `scope`'s block, or from `action` in it.

    The same methods the validator typechecks with, for callers that need a
    width before they have a value: the interpreter, the printer and the STF
    reader. An expression that does not type there raises `ValidationError`
    with what the validator would report, which a checked program never
    does.
    """
    typer = Typer(index.program, index=index)
    decl = scope.actions[action] if action is not None else None
    t = typer.type_of(expr, Scope(scope.block, "", scope, decl), "expr")
    if t is None or typer.diagnostics:
        raise ValidationError(
            typer.diagnostics or [Diagnostic(TYPE_INVALID, "expression has no valid type", "expr")]
        )
    return t
