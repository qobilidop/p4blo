"""The printer's programs: a whole IR program as P4-16 text.

`ProgramPrinter` prints the declarations and the blocks, and nothing an
architecture decides: a program printed by it alone includes only
core.p4 and has no `main`. An architecture binds it by subclassing and
overriding the hooks below, each of which does nothing here:

  preamble         the first lines: a comment and the includes
  extern_instance  how an extern instance is instantiated
  role_params      parameters the architecture adds to an exported block
  binding          statements around an exported parser's start state and
                   an exported control's `apply`
  postamble        the last lines: the architecture's own blocks and `main`

and `stmt_printer`, the class that prints statements, for extern calls of
another form. `missing_roles` prints an empty block for each role no block
is exported as, for the postamble of an architecture whose package needs
all three.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import ClassVar

from p4blo import ir
from p4blo.printer.statements import INDENT, StmtPrinter, block_stmts, instance_name
from p4blo.printer.terms import (
    PACKET,
    PrintError,
    print_action_call,
    print_bits,
    print_expr,
    print_key,
    print_key_sets,
    print_key_value,
    print_literal,
    print_param,
    print_target,
    print_type,
)
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator import ValidationError
from p4blo.validator.typer import expr_type


def print_program(program: pb.BlockLibrary, *, index: ir.Index | None = None) -> str:
    """The program's declarations and blocks, with no architecture."""
    if index is None:
        index = ir.Index.build(program)
    return ProgramPrinter(index).render()


@dataclass
class ProgramPrinter:
    """Conventions of the output, chosen for correctness over readability:

    - scalar locals get their zero initializer (docs/ir-semantics.md,
      uninitialized variables), so p4c does not warn and an oracle starts
      where the reference interpreter does;
    - a callee is declared before its callers, and each sub-block is
      instantiated once in its caller;
    - an extern instance is instantiated inside the one block that uses it
      when that block is exported, at top level otherwise;
    - a table with a ternary key prints non-const `entries` with
      `priority = N` and `largest_priority_wins = true`, because p4c refuses
      priorities on `const entries` and rejects `@priority` annotations; the
      entries are sorted by descending priority to match p4c's expectation.
    """

    index: ir.Index
    roles: Mapping[str, str] = field(default_factory=dict)
    out: list[str] = field(default_factory=list)
    stmt_printer: ClassVar[type[StmtPrinter]] = StmtPrinter

    def __post_init__(self) -> None:
        self.p = self.index.program
        self.stmts = self.stmt_printer(self.index)
        self.exported = set(self.roles.values())
        self.top_level_externs, self.block_externs = self._place_externs()

    # -- output helpers

    def line(self, depth: int, text: str = "") -> None:
        self.out.append(f"{INDENT * depth}{text}" if text else "")

    def lines(self, lines: Iterable[str]) -> None:
        self.out.extend(lines)

    def render(self) -> str:
        p = self.p
        self.preamble()
        self.errors()
        for enum in p.enum_types:
            self.enum(enum)
        for header in p.header_types:
            self.header(header)
        for struct in p.struct_types:
            self.struct(struct)
        if self.top_level_externs:
            self.line(0)
            for name in self.top_level_externs:
                decl = self.extern_instance(self.index.extern_instances[name])
                if decl is not None:
                    self.line(0, decl)
        for block in self._block_order():
            self.block(block)
        self.postamble()
        return "\n".join(self.out) + "\n"

    # -- the hooks an architecture overrides

    def preamble(self) -> None:
        self.line(0, f"// {self.p.name}: printed by p4blo. Do not edit.")
        self.line(0, "#include <core.p4>")

    def extern_instance(self, instance: pb.ExternInstance) -> str | None:
        """The instantiation of an extern instance, or None when it has none."""
        args = ", ".join(print_literal(a) for a in instance.args)
        return f"{instance.extern_type}({args}) {instance.name};"

    def role_params(self, role: str) -> list[str]:
        """The parameters an architecture adds after the IR's, for the block
        exported as `role`."""
        return []

    def binding(self, block: pb.Block) -> tuple[list[str], list[str]]:
        """The prologue and epilogue of the exported `block`: around its
        start state for a parser, around its `apply` for a control."""
        return [], []

    def postamble(self) -> None:
        pass

    # -- declarations

    def errors(self) -> None:
        extra = [e for e in self.p.errors if e not in ir.CORE_ERRORS]
        if extra:
            self.line(0)
            self.line(0, f"error {{ {', '.join(extra)} }}")

    def enum(self, enum: pb.EnumType) -> None:
        self.line(0)
        self.line(0, f"enum {enum.name} {{ {', '.join(enum.members)} }}")

    def header(self, header: pb.HeaderType) -> None:
        self._fields("header", header.name, header.fields)

    def struct(self, struct: pb.StructType) -> None:
        self._fields("struct", struct.name, struct.fields)

    def _fields(self, keyword: str, name: str, fields: Iterable[pb.Field]) -> None:
        self.line(0)
        self.line(0, f"{keyword} {name} {{")
        for f in fields:
            self.line(1, f"{print_type(f.type)} {f.name};")
        self.line(0, "}")

    # -- externs

    def _place_externs(self) -> tuple[list[str], dict[str, list[str]]]:
        """Where each extern instance is instantiated.

        Inside the one block that uses it when that block is exported, and
        so instantiated exactly once by the architecture's package; at top
        level otherwise, which keeps one piece of state per IR instance
        however many times a sub-block is instantiated.
        """
        users: dict[str, list[str]] = {name: [] for name in self.index.extern_instances}
        for block in self.p.blocks:
            seen: set[str] = set()
            for stmt in block_stmts(block):
                if stmt.WhichOneof("kind") == "call_extern":
                    seen.add(stmt.call_extern.instance)
            for name in seen:
                users[name].append(block.name)
        top: list[str] = []
        per_block: dict[str, list[str]] = {b.name: [] for b in self.p.blocks}
        for name, blocks in users.items():
            if len(blocks) == 1 and blocks[0] in self.exported:
                per_block[blocks[0]].append(name)
            else:
                top.append(name)
        return top, per_block

    # -- blocks

    def _block_order(self) -> list[pb.Block]:
        """Program order, except that a callee precedes its callers."""
        order: list[pb.Block] = []
        seen: set[str] = set()

        def visit(block: pb.Block) -> None:
            if block.name in seen:
                return
            seen.add(block.name)
            callees = {
                s.call_block.block
                for s in block_stmts(block)
                if s.WhichOneof("kind") == "call_block"
            }
            for other in self.p.blocks:
                if other.name in callees:
                    visit(other)
            order.append(block)

        for block in self.p.blocks:
            visit(block)
        return order

    def role(self, block: pb.Block) -> str | None:
        for role, name in self.roles.items():
            if name == block.name:
                return role
        return None

    def _signature(self, block: pb.Block) -> str:
        """The parameter list: the role's signature for an exported block,
        the block's own parameters otherwise, with the packet first for
        parsers and deparsers and the architecture's own last."""
        params = [print_param(p) for p in block.params]
        match self.role(block):
            case "parser":
                self._expect_params(block, [pb.DIRECTION_OUT, pb.DIRECTION_INOUT])
                params = [f"packet_in {PACKET}", *params, *self.role_params("parser")]
            case "control":
                self._expect_params(block, [pb.DIRECTION_INOUT, pb.DIRECTION_INOUT])
                params = [*params, *self.role_params("control")]
            case "deparser":
                self._expect_params(block, [pb.DIRECTION_IN])
                params = [f"packet_out {PACKET}", *params, *self.role_params("deparser")]
            case None:
                if block.kind == pb.BLOCK_KIND_PARSER:
                    params = [f"packet_in {PACKET}", *params]
                elif block.kind == pb.BLOCK_KIND_DEPARSER:
                    params = [f"packet_out {PACKET}", *params]
            case role:
                raise PrintError(f"unknown export role {role!r}")
        return ", ".join(params)

    @staticmethod
    def _expect_params(block: pb.Block, directions: list[int]) -> None:
        if [p.direction for p in block.params] != directions:
            raise PrintError(f"block {block.name!r} does not have its role's signature")

    def block(self, block: pb.Block) -> None:
        keyword = "parser" if block.kind == pb.BLOCK_KIND_PARSER else "control"
        self.line(0)
        self.line(0, f"{keyword} {block.name}({self._signature(block)}) {{")
        for name in self.block_externs[block.name]:
            decl = self.extern_instance(self.index.extern_instances[name])
            if decl is not None:
                self.line(1, decl)
        for callee in self._callees_in_order(block):
            self.line(1, f"{callee}() {instance_name(callee)};")
        for local in block.locals:
            self.line(1, self._local(local))
        if block.kind == pb.BLOCK_KIND_PARSER:
            self.states(block)
        else:
            for action in block.actions:
                self.action(action)
            for table in block.tables:
                self.table(table, block)
            self.apply(block)
        self.line(0, "}")

    def _callees_in_order(self, block: pb.Block) -> list[str]:
        callees: list[str] = []
        for s in block_stmts(block):
            if s.WhichOneof("kind") == "call_block" and s.call_block.block not in callees:
                callees.append(s.call_block.block)
        return callees

    def _local(self, local: pb.Var) -> str:
        decl = f"{print_type(local.type)} {local.name}"
        init = self._zero(local.type)
        return f"{decl} = {init};" if init is not None else f"{decl};"

    def _zero(self, t: pb.Type) -> str | None:
        """The zero value of a scalar type, as docs/ir-semantics.md defines it;
        None for a compound type, which P4 cannot initialize inline."""
        match t.WhichOneof("kind"):
            case "bits":
                return print_bits(t.bits, 0)
            case "boolean":
                return "false"
            case "enum_type":
                members = self.index.enum_types[t.enum_type].members
                return f"{t.enum_type}.{members[0]}" if members else None
            case "error":
                return "error.NoError"
            case _:
                return None

    # -- parsers

    def states(self, block: pb.Block) -> None:
        """The states, the binding's prologue first in the exported parser's
        start state, and a synthesized `start` when the IR's start state has
        another name, as P4 requires one named `start`. The prologue then
        goes into the synthesized state; a loop back into the start state
        re-runs it."""
        prologue: list[str] = []
        if self.role(block) == "parser":
            prologue, _ = self.binding(block)
        names = {s.name for s in block.states}
        if block.start_state != "start":
            if "start" in names:
                raise PrintError(
                    f"parser {block.name!r} starts at {block.start_state!r} "
                    "but also has a state named 'start'"
                )
            self.line(1, "state start {")
            for s in prologue:
                self.line(2, s)
            self.line(2, f"transition {block.start_state};")
            self.line(1, "}")
            prologue = []
        for state in block.states:
            self.state(state, prologue if state.name == block.start_state else [])

    def state(self, state: pb.State, prologue: Iterable[str] = ()) -> None:
        self.line(1, f"state {state.name} {{")
        for s in prologue:
            self.line(2, s)
        self.lines(self.stmts.block(state.body, 2))
        self.transition(state.transition)
        self.line(1, "}")

    def transition(self, t: pb.Transition) -> None:
        match t.WhichOneof("kind"):
            case "direct":
                self.line(2, f"transition {print_target(t.direct)};")
            case "select":
                self.select(t.select)
            case _:
                raise PrintError("transition has no kind")

    def select(self, select: pb.Select) -> None:
        keys = ", ".join(print_expr(k) for k in select.keys)
        self.line(2, f"transition select({keys}) {{")
        for case in select.cases:
            self.line(3, f"{print_key_sets(case.sets)}: {print_target(case.target)};")
        self.line(2, "}")

    # -- controls

    def action(self, action: pb.Action) -> None:
        if action.name == "NoAction":
            # core.p4 declares it; redeclaring it would clash. The IR has no
            # implicit declarations, so a program's NoAction is an ordinary
            # action that runs whatever body it has; only the one core.p4
            # means can be elided (the validator's NOACTION_RESERVED).
            if action.body or action.params:
                raise PrintError("NoAction with a body or parameters cannot be printed for core.p4")
            return
        params = ", ".join(print_param(p) for p in action.params)
        self.line(1, f"action {action.name}({params}) {{")
        self.lines(self.stmts.block(action.body, 2))
        self.line(1, "}")

    def table(self, table: pb.Table, block: pb.Block) -> None:
        self.line(1, f"table {table.name} {{")
        if table.keys:
            self.line(2, "key = {")
            for key in table.keys:
                self.line(3, print_key(key))
            self.line(2, "}")
        default = (
            print_action_call(table.default_action)
            if table.HasField("default_action")
            else "NoAction()"
        )
        actions = list(table.actions)
        if not table.HasField("default_action") and "NoAction" not in actions:
            # p4c requires the default action to be in the list.
            actions.append("NoAction")
        self.line(2, "actions = {")
        for name in actions:
            self.line(3, f"{name};")
        self.line(2, "}")
        const = "const " if table.const_default_action else ""
        self.line(2, f"{const}default_action = {default};")
        if table.const_entries:
            self.entries(table, block)
        if table.size:
            self.line(2, f"size = {table.size};")
        self.line(1, "}")

    def entries(self, table: pb.Table, block: pb.Block) -> None:
        widths = [self._key_width(key, block) for key in table.keys]
        ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in table.keys)
        entries = list(table.const_entries)
        if ternary:
            # p4c refuses priorities on const entries; the mutable form with
            # largest_priority_wins says the same thing, and p4c warns unless
            # the list is in descending priority order.
            entries.sort(key=lambda e: -e.priority)
            self.line(2, "entries = {")
        else:
            self.line(2, "const entries = {")
        for entry in entries:
            values = [
                print_key_value(v, k.match_kind, w)
                for v, k, w in zip(entry.keys, table.keys, widths, strict=True)
            ]
            keys = values[0] if len(values) == 1 else f"({', '.join(values)})"
            priority = f"priority = {entry.priority}: " if ternary else ""
            self.line(3, f"{priority}{keys} : {print_action_call(entry.action)};")
        self.line(2, "}")
        if ternary:
            self.line(2, "largest_priority_wins = true;")

    def _key_width(self, key: pb.Key, block: pb.Block) -> int:
        """The width of a table key, so that LPM prefixes become masks and
        entry values carry their width; the validator's typer decides it."""
        try:
            t = expr_type(key.expr, self.index, self.index.scopes[block.name])
        except ValidationError as e:
            raise PrintError(str(e)) from None
        if t.WhichOneof("kind") != "bits":
            raise PrintError(
                f"table key {print_expr(key.expr)} is {print_type(t)}; entries need a bit<N> key"
            )
        return t.bits

    def apply(self, block: pb.Block) -> None:
        prologue: list[str] = []
        epilogue: list[str] = []
        if self.role(block) == "control":
            prologue, epilogue = self.binding(block)
        self.line(1, "apply {")
        for s in prologue:
            self.line(2, s)
        self.lines(self.stmts.block(block.body, 2))
        for s in epilogue:
            self.line(2, s)
        self.line(1, "}")
