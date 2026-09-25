"""Blocks and their actions.

A block's shape must fit its kind; its actions, tables, states and body are
then checked by the classes this one builds on.
"""

from __future__ import annotations

from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    BLOCK_KIND_SHAPE,
    NOACTION_RESERVED,
    PARSER_START_STATE,
)
from p4blo.validator.names import (
    ACTION_PARAM_DIRECTIONS,
    BLOCK_PARAM_DIRECTIONS,
    KIND_NAMES,
    Scope,
)
from p4blo.validator.parsers import ParserChecks
from p4blo.validator.tables import TableChecks


class BlockChecks(ParserChecks, TableChecks):
    """Blocks and actions."""

    def check_block(self, block: pb.Block, path: str) -> None:
        self.check_params(block.params, BLOCK_PARAM_DIRECTIONS, f"{path}.params", "block")
        for i, v in enumerate(block.locals):
            self.check_type(v.type, f"{path}.locals[{i}].type")
        if block.kind not in KIND_NAMES:
            self.report(BLOCK_KIND_SHAPE, "block has no kind", path)
            return
        scope = Scope(block, path, self.idx.scopes[block.name])
        if block.kind == pb.BLOCK_KIND_PARSER:
            if not block.states:
                self.report(BLOCK_KIND_SHAPE, "a parser has at least one state", path)
            elif block.start_state not in scope.names.states:
                self.report(
                    PARSER_START_STATE,
                    f"start_state {block.start_state!r} is not a state of this parser",
                    f"{path}.start_state",
                )
            if block.body:
                self.report(BLOCK_KIND_SHAPE, "a parser has states, not a body", f"{path}.body")
            if block.actions:
                self.report(BLOCK_KIND_SHAPE, "a parser has no actions", f"{path}.actions")
            if block.tables:
                self.report(BLOCK_KIND_SHAPE, "a parser has no tables", f"{path}.tables")
        else:
            kind = KIND_NAMES[block.kind]
            if block.states:
                self.report(BLOCK_KIND_SHAPE, f"a {kind} has a body, not states", f"{path}.states")
            if block.start_state:
                self.report(BLOCK_KIND_SHAPE, f"a {kind} has no start state", f"{path}.start_state")
        self.action_calls = {}
        for i, action in enumerate(block.actions):
            self.check_action(action, scope, f"{path}.actions[{i}]")
        self.report_cycles(scope.names.actions, self.action_calls, "action")
        for i, table in enumerate(block.tables):
            self.check_table(table, scope, f"{path}.tables[{i}]")
        for i, state in enumerate(block.states):
            self.check_state(state, scope, f"{path}.states[{i}]")
        for i, stmt in enumerate(block.body):
            self.check_stmt(stmt, scope, f"{path}.body[{i}]")

    def check_action(self, action: pb.Action, scope: Scope, path: str) -> None:
        if action.name == "NoAction" and (action.body or action.params):
            # The IR has no implicit declarations, so a program's NoAction is
            # an ordinary action; the name is reserved for the one core.p4
            # means, which every P4 reader and the printer's shim assume
            # (docs/ir-semantics.md, "Tables").
            self.report(NOACTION_RESERVED, "NoAction must have no body and no parameters", path)
        self.check_params(action.params, ACTION_PARAM_DIRECTIONS, f"{path}.params", "action")
        inner = Scope(scope.block, scope.path, scope.names, action)
        for i, stmt in enumerate(action.body):
            self.check_stmt(stmt, inner, f"{path}.body[{i}]")
