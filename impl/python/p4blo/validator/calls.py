"""Calls: to actions, to blocks and to extern methods.

Arguments are checked against parameters for count, form and type, and for
aliasing, which is judged on the static access path an lvalue names. The
block call graph, and each block's action call graph, must be acyclic, so
every run terminates.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    ARG_COUNT,
    ARG_DIRECTION,
    ARG_TYPE,
    BLOCK_KIND_STMT,
    CALL_ALIAS,
    CALL_CYCLE,
    CALL_KIND,
    EXTERN_RESULT,
    REF_UNRESOLVED,
)
from p4blo.validator.names import (
    DIRECTION_NAMES,
    KIND_NAMES,
    OUT_DIRECTIONS,
    Scope,
)
from p4blo.validator.typer import Typer
from p4blo.validator.types import (
    describe,
    parse_decimal,
    same_type,
)

# A static description of the storage an lvalue or lvalue-shaped expression
# names: the variable, then one step per member (field name) or index (the
# literal index, or None when it is computed). Two accesses may alias when
# they agree on every step where both are known.
type Access = tuple[str | int | None, ...]


def may_alias(a: Access, b: Access) -> bool:
    for x, y in zip(a, b, strict=False):
        if x is not None and y is not None and x != y:
            return False
    return True


class CallChecks(Typer):
    """Action, block and extern calls, their arguments, and the call graph."""

    def check_call_action(self, stmt: pb.CallAction, scope: Scope, path: str) -> None:
        action = self.resolve_local(
            stmt.action, scope.names.actions, "action", scope, f"{path}.action"
        )
        if action is None:
            return
        if scope.action is not None:
            self.action_calls.setdefault(scope.action.name, []).append((action.name, path))
        self.check_args(stmt.args, action.params, scope, path)

    def check_call_block(self, stmt: pb.CallBlock, scope: Scope, path: str) -> None:
        if scope.action is not None:
            # P4 forbids applying a control or parser from an action (§14.1).
            self.report(BLOCK_KIND_STMT, "call_block is not allowed inside an action", path)
            return
        callee = self.resolve(stmt.block, self.idx.blocks, "block", f"{path}.block")
        if callee is None:
            return
        self.calls.setdefault(scope.block.name, []).append((callee.name, path))
        # A block calls only blocks of its own kind, so a deparser, which has
        # no entries, never reaches a table (proto, CallBlock).
        if callee.kind != scope.block.kind:
            kind = KIND_NAMES[scope.block.kind]
            self.report(
                CALL_KIND,
                f"a {kind} may only call a {kind}; "
                f"{callee.name!r} is a {KIND_NAMES.get(callee.kind, 'block without kind')}",
                f"{path}.block",
            )
        self.check_args(stmt.args, callee.params, scope, path)

    def check_call_extern(self, stmt: pb.CallExtern, scope: Scope, path: str) -> None:
        instance = self.resolve(
            stmt.instance, self.idx.extern_instances, "extern instance", f"{path}.instance"
        )
        if instance is None:
            return
        ext = self.idx.extern_types.get(instance.extern_type)
        if ext is None:
            return  # reported at the instance
        method = next((m for m in ext.methods if m.name == stmt.method), None)
        if method is None:
            self.report(
                REF_UNRESOLVED, f"extern {ext.name} has no method {stmt.method!r}", f"{path}.method"
            )
            return
        self.check_args(stmt.args, method.params, scope, path)
        if method.HasField("returns"):
            if not stmt.HasField("result"):
                self.report(
                    EXTERN_RESULT, f"method {method.name!r} returns a value; result is unset", path
                )
            else:
                t = self.type_of_lvalue(stmt.result, scope, f"{path}.result")
                if (
                    t is not None
                    and self.type_ok(method.returns)
                    and not same_type(t, method.returns)
                ):
                    self.report(
                        EXTERN_RESULT,
                        f"result is {describe(t)}, method returns {describe(method.returns)}",
                        f"{path}.result",
                    )
        elif stmt.HasField("result"):
            self.report(EXTERN_RESULT, f"method {method.name!r} returns nothing", f"{path}.result")

    def check_args(
        self, args: Sequence[pb.Arg], params: Sequence[pb.Param], scope: Scope, path: str
    ) -> None:
        """Arguments against params, and the aliasing rule.

        Aliasing is judged statically and conservatively: two arguments may
        alias when their access paths (variable, then fields and indices)
        agree wherever both are known; a computed index is unknown and
        matches any index. Only `out` and `inout` arguments take part: an
        `in` argument is copied in before anything is written back, so its
        overlapping an out argument changes nothing (§6.8). Two out or inout
        arguments that may alias are an error, so copy-back order never
        matters (docs/ir-semantics.md, "Block calls").
        """
        if len(args) != len(params):
            self.report(ARG_COUNT, f"expected {len(params)} arguments, got {len(args)}", path)
            return
        accesses: list[tuple[str, Access | None]] = []
        for i, (arg, param) in enumerate(zip(args, params, strict=True)):
            apath = f"{path}.args[{i}]"
            kind = arg.WhichOneof("kind")
            wants_out = param.direction in OUT_DIRECTIONS
            if kind is None:
                self.report(ARG_DIRECTION, "argument has no kind", apath)
                continue
            if wants_out and kind != "lvalue":
                self.report(
                    ARG_DIRECTION,
                    f"param {param.name!r} is {DIRECTION_NAMES[param.direction]}; "
                    "the argument must be an out lvalue",
                    apath,
                )
                continue
            if not wants_out and kind != "expr":
                self.report(
                    ARG_DIRECTION,
                    f"param {param.name!r} is {DIRECTION_NAMES[param.direction]}; "
                    "the argument must be an in expression",
                    apath,
                )
                continue
            if kind == "expr":
                t = self.type_of(arg.expr, scope, f"{apath}.expr")
            else:
                t = self.type_of_lvalue(arg.lvalue, scope, f"{apath}.lvalue")
                accesses.append((apath, self.lvalue_access(arg.lvalue)))
            if t is not None and self.type_ok(param.type) and not same_type(t, param.type):
                self.report(
                    ARG_TYPE,
                    f"argument is {describe(t)}, param {param.name!r} is {describe(param.type)}",
                    apath,
                )
        for j, (apath, b) in enumerate(accesses):
            if b is None:
                continue
            if any(a is not None and may_alias(a, b) for _, a in accesses[:j]):
                self.report(CALL_ALIAS, "argument may alias an earlier out argument", apath)

    def lvalue_access(self, lvalue: pb.LValue) -> Access | None:
        match lvalue.WhichOneof("kind"):
            case "var":
                return (lvalue.var,)
            case "member":
                base = self.lvalue_access(lvalue.member.base)
                return None if base is None else (*base, lvalue.member.field)
            case "index":
                base = self.lvalue_access(lvalue.index.base)
                return None if base is None else (*base, self.static_index(lvalue.index.index))
            case "next":
                base = self.lvalue_access(lvalue.next.stack)
                return None if base is None else (*base, None)
            case _:
                return None

    @staticmethod
    def static_index(expr: pb.Expr) -> int | None:
        if expr.WhichOneof("kind") == "literal" and expr.literal.WhichOneof("value") == "bits":
            return parse_decimal(expr.literal.bits.value)
        return None

    def check_call_graph(self) -> None:
        """No cycle among CallBlock edges, so every run terminates. Actions
        are checked the same way per block, so the call graph of blocks and
        actions together is acyclic (docs/ir-semantics.md, "Controls")."""
        self.report_cycles(self.idx.blocks, self.calls, "block")

    def report_cycles(
        self, nodes: Iterable[str], edges: dict[str, list[tuple[str, str]]], what: str
    ) -> None:
        """Every cycle in `edges` over `nodes`, reported at the call that
        closes it."""
        white, grey, black = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(nodes, white)

        def visit(name: str, trail: list[str]) -> None:
            color[name] = grey
            for callee, path in edges.get(name, ()):
                if callee not in color:
                    continue
                if color[callee] == grey:
                    chain = [*trail, name]
                    cycle = " -> ".join([*chain[chain.index(callee) :], callee])
                    self.report(CALL_CYCLE, f"{what} calls form a cycle: {cycle}", path)
                elif color[callee] == white:
                    visit(callee, [*trail, name])
            color[name] = black

        for name in color:
            if color[name] == white:
                visit(name, [])
