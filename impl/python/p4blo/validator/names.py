"""Names, references, scopes, and where each statement may stand.

`Scope` is where a statement or expression stands. The tables below it are
the placement rules of the schema as data: which statements each block kind
allows, which parameter directions each owner allows, and the signature an
exported block must have. `NameChecks` resolves references, reporting why
one does not resolve (REF_UNRESOLVED, REF_KIND, SCOPE_VAR, SCOPE_DECL), and
checks the small namespaces and the error list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.base import Checker
from p4blo.validator.diagnostics import (
    ERROR_LIST,
    NAME_DUPLICATE,
    NAME_EMPTY,
    REF_KIND,
    REF_UNRESOLVED,
    SCOPE_DECL,
    SCOPE_VAR,
)


@dataclass(frozen=True)
class Scope:
    """Where a statement or expression stands: a block, and within it
    possibly an action. Variables visible here are the block's params and
    locals, plus the action's params inside an action body."""

    block: pb.Block
    path: str
    names: ir.BlockScope
    action: pb.Action | None = None

    def var(self, name: str) -> pb.Param | pb.Var | None:
        if self.action is not None:
            params = self.names.action_params[self.action.name]
            if name in params:
                return params[name]
        return self.names.vars.get(name)

    @property
    def in_parser(self) -> bool:
        return self.block.kind == pb.BLOCK_KIND_PARSER


_ANY_BLOCK_STMTS = frozenset(
    {
        "assign",
        "conditional",
        "call_block",
        "call_extern",
        "set_valid",
        "set_invalid",
        "push",
        "pop",
    }
)


# The table above `Stmt` in the schema, as data.
STMTS_BY_KIND: dict[int, frozenset[str]] = {
    pb.BLOCK_KIND_PARSER: _ANY_BLOCK_STMTS | {"extract", "advance", "verify"},
    pb.BLOCK_KIND_CONTROL: _ANY_BLOCK_STMTS | {"apply", "call_action"},
    pb.BLOCK_KIND_DEPARSER: _ANY_BLOCK_STMTS | {"emit"},
}


BLOCK_PARAM_DIRECTIONS = frozenset({pb.DIRECTION_IN, pb.DIRECTION_OUT, pb.DIRECTION_INOUT})


ACTION_PARAM_DIRECTIONS = BLOCK_PARAM_DIRECTIONS | {pb.DIRECTION_NONE}


OUT_DIRECTIONS = frozenset({pb.DIRECTION_OUT, pb.DIRECTION_INOUT})


DIRECTION_NAMES: dict[int, str] = {
    pb.DIRECTION_UNSPECIFIED: "unspecified",
    pb.DIRECTION_NONE: "directionless",
    pb.DIRECTION_IN: "in",
    pb.DIRECTION_OUT: "out",
    pb.DIRECTION_INOUT: "inout",
}


KIND_NAMES = {
    pb.BLOCK_KIND_PARSER: "parser",
    pb.BLOCK_KIND_CONTROL: "control",
    pb.BLOCK_KIND_DEPARSER: "deparser",
}


# The signature an exported block must have, by kind: (direction, H or M).
EXPORT_SIGNATURES: dict[int, tuple[tuple[int, str], ...]] = {
    pb.BLOCK_KIND_PARSER: ((pb.DIRECTION_OUT, "H"), (pb.DIRECTION_INOUT, "M")),
    pb.BLOCK_KIND_CONTROL: ((pb.DIRECTION_INOUT, "H"), (pb.DIRECTION_INOUT, "M")),
    pb.BLOCK_KIND_DEPARSER: ((pb.DIRECTION_IN, "H"),),
}


class NameChecks(Checker):
    """Names unique and non-empty, and references resolved from a scope."""

    def check_names(self, names: Sequence[str], path: str, what: str) -> None:
        """Names unique and non-empty within one of the small namespaces the
        Index does not cover: fields, enum members, methods, method params."""
        seen: set[str] = set()
        for i, name in enumerate(names):
            if not name:
                self.report(NAME_EMPTY, f"{what} has no name", f"{path}[{i}]")
            elif name in seen:
                self.report(NAME_DUPLICATE, f"{what} {name!r} declared twice", f"{path}[{i}]")
            seen.add(name)

    def resolve[T](
        self, name: str, table: dict[str, T], what: str, path: str, quiet: bool = False
    ) -> T | None:
        """A program-level reference, or None after reporting why not."""
        decl = table.get(name)
        if decl is not None:
            return decl
        if quiet:
            return None
        if name in self.idx.program_names:
            self.report(REF_KIND, f"{name!r} is not a {what}", path)
        elif name:
            self.report(REF_UNRESOLVED, f"no {what} named {name!r}", path)
        else:
            self.report(REF_UNRESOLVED, f"{what} reference is unset", path)
        return None

    def resolve_local[T](
        self, name: str, table: dict[str, T], what: str, scope: Scope, path: str
    ) -> T | None:
        """A block-scoped reference (action, table or state) of the current
        block, or None after reporting why not."""
        decl = table.get(name)
        if decl is not None:
            return decl
        names = scope.names
        if not name:
            self.report(REF_UNRESOLVED, f"{what} reference is unset", path)
        elif (
            name in names.vars
            or name in names.actions
            or name in names.tables
            or name in names.states
            or name in self.idx.program_names
        ):
            self.report(REF_KIND, f"{name!r} is not a {what}", path)
        elif any(name in getattr(s, what + "s") for s in self.idx.scopes.values()):
            self.report(SCOPE_DECL, f"{what} {name!r} belongs to another block", path)
        else:
            self.report(REF_UNRESOLVED, f"no {what} named {name!r}", path)
        return None

    def resolve_var(self, name: str, scope: Scope, path: str) -> pb.Param | pb.Var | None:
        decl = scope.var(name)
        if decl is not None:
            return decl
        names = scope.names
        if not name:
            self.report(REF_UNRESOLVED, "variable reference is unset", path)
        elif (
            name in names.actions
            or name in names.tables
            or name in names.states
            or name in self.idx.program_names
        ):
            self.report(REF_KIND, f"{name!r} is not a variable", path)
        elif any(
            name in s.vars or any(name in ps for ps in s.action_params.values())
            for s in self.idx.scopes.values()
        ):
            self.report(SCOPE_VAR, f"variable {name!r} is not visible here", path)
        else:
            self.report(REF_UNRESOLVED, f"no variable named {name!r}", path)
        return None

    def check_errors(self) -> None:
        core = tuple(self.program.errors[: len(ir.CORE_ERRORS)])
        if core != ir.CORE_ERRORS:
            self.report(
                ERROR_LIST,
                f"errors must begin with {', '.join(ir.CORE_ERRORS)}; got {', '.join(core)}",
                "errors",
            )
