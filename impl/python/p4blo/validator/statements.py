"""Statements, one method per kind.

Whether a statement may stand in its block kind is decided first, from the
placement table in `names`; each kind's own rules follow.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.calls import CallChecks
from p4blo.validator.diagnostics import (
    BLOCK_KIND_STMT,
    REF_UNRESOLVED,
    STACK_COUNT,
    STMT_INVALID,
    TYPE_MISMATCH,
)
from p4blo.validator.names import (
    KIND_NAMES,
    STMTS_BY_KIND,
    Scope,
)
from p4blo.validator.types import (
    describe,
    is_bits32,
    is_boolean,
    is_header,
    is_stack,
    kind_of,
    same_type,
)


class StatementChecks(CallChecks):
    """Every statement kind of the schema."""

    def check_stmts(self, stmts: Sequence[pb.Stmt], scope: Scope, path: str) -> None:
        for i, stmt in enumerate(stmts):
            self.check_stmt(stmt, scope, f"{path}[{i}]")

    def check_stmt(self, stmt: pb.Stmt, scope: Scope, path: str) -> None:
        kind = stmt.WhichOneof("kind")
        if kind is None:
            self.report(STMT_INVALID, "statement has no kind", path)
            return
        if kind not in STMTS_BY_KIND[scope.block.kind]:
            self.report(
                BLOCK_KIND_STMT,
                f"{kind} is not allowed in a {KIND_NAMES[scope.block.kind]}",
                path,
            )
            return
        path = f"{path}.{kind}"
        match kind:
            case "assign":
                self.check_assign(stmt.assign, scope, path)
            case "conditional":
                self.check_if(stmt.conditional, scope, path)
            case "apply":
                self.check_apply(stmt.apply, scope, path)
            case "call_action":
                self.check_call_action(stmt.call_action, scope, path)
            case "call_block":
                self.check_call_block(stmt.call_block, scope, path)
            case "call_extern":
                self.check_call_extern(stmt.call_extern, scope, path)
            case "set_valid":
                self.expect_lvalue(
                    stmt.set_valid.header, is_header, "a header", scope, f"{path}.header"
                )
            case "set_invalid":
                self.expect_lvalue(
                    stmt.set_invalid.header, is_header, "a header", scope, f"{path}.header"
                )
            case "push":
                self.check_push_pop(stmt.push.stack, stmt.push.count, scope, path)
            case "pop":
                self.check_push_pop(stmt.pop.stack, stmt.pop.count, scope, path)
            case "extract":
                self.check_extract(stmt.extract, scope, path)
            case "advance":
                # core.p4's `advance(in bit<32> sizeInBits)`: the IR is
                # post-elaboration, so the frontend owes the cast.
                self.expect_expr(stmt.advance.bits, is_bits32, "bit<32>", scope, f"{path}.bits")
            case "verify":
                self.check_verify(stmt.verify, scope, path)
            case "emit":
                self.check_emit(stmt.emit, scope, path)

    def check_assign(self, stmt: pb.Assign, scope: Scope, path: str) -> None:
        target = self.type_of_lvalue(stmt.target, scope, f"{path}.target")
        value = self.type_of(stmt.value, scope, f"{path}.value")
        if target is not None and value is not None and not same_type(target, value):
            self.report(
                TYPE_MISMATCH,
                f"cannot assign {describe(value)} to {describe(target)}",
                path,
            )

    def check_if(self, stmt: pb.If, scope: Scope, path: str) -> None:
        self.expect_expr(stmt.condition, is_boolean, "boolean", scope, f"{path}.condition")
        self.check_stmts(stmt.then, scope, f"{path}.then")
        self.check_stmts(stmt.otherwise, scope, f"{path}.otherwise")

    def check_apply(self, stmt: pb.Apply, scope: Scope, path: str) -> None:
        if scope.action is not None:
            self.report(BLOCK_KIND_STMT, "apply is not allowed inside an action", path)
            return
        self.resolve_local(stmt.table, scope.names.tables, "table", scope, f"{path}.table")
        if stmt.HasField("hit"):
            self.expect_lvalue(stmt.hit, is_boolean, "boolean", scope, f"{path}.hit")

    def check_extract(self, stmt: pb.Extract, scope: Scope, path: str) -> None:
        """The target is a header lvalue, or `stack.next`, which is allowed
        nowhere else (docs/ir-semantics.md, "Header stacks")."""
        target = stmt.target
        if target.WhichOneof("kind") == "next":
            self.expect_lvalue(
                target.next.stack, is_stack, "a stack", scope, f"{path}.target.next.stack"
            )
        else:
            self.expect_lvalue(target, is_header, "a header", scope, f"{path}.target")

    def check_push_pop(self, stack: pb.LValue, count: int, scope: Scope, path: str) -> None:
        self.expect_lvalue(stack, is_stack, "a stack", scope, f"{path}.stack")
        if count < 1:
            self.report(STACK_COUNT, "count must be at least 1", f"{path}.count")

    def check_verify(self, stmt: pb.Verify, scope: Scope, path: str) -> None:
        self.expect_expr(stmt.condition, is_boolean, "boolean", scope, f"{path}.condition")
        if stmt.error not in self.idx.errors:
            self.report(REF_UNRESOLVED, f"no error named {stmt.error!r}", f"{path}.error")

    def check_emit(self, stmt: pb.Emit, scope: Scope, path: str) -> None:
        t = self.type_of(stmt.value, scope, f"{path}.value")
        if t is not None and not self.emittable(t, set()):
            self.report(
                TYPE_MISMATCH,
                f"emit takes a header, a stack, or a struct of those; got {describe(t)}",
                f"{path}.value",
            )

    def emittable(self, t: pb.Type, visiting: set[str]) -> bool:
        match kind_of(t):
            case "header" | "stack":
                return True
            case "struct":
                if t.struct in visiting:
                    return False
                fields = self.idx.struct_types[t.struct].fields
                return all(self.emittable(f.type, visiting | {t.struct}) for f in fields)
            case _:
                return False
