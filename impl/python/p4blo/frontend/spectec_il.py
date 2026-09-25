"""The IL bridge: P4-SpecTec's typed and instantiated IL to p4blo IR.

A P4 program enters p4blo through the language's own typing and
instantiation: P4-SpecTec's `Program_ok` and `Program_inst` relations run
on the source (`p4blo.frontend.export`), and this package translates what
they produce, construct by construct, as docs/p4-spec-coverage.md
prescribes. An `in` row is translated to its IR message; an `elaborated`
row performs the elaboration the page names; an `excluded` row raises
`Excluded`, naming the row. What the bridge does not attempt yet raises
`NotTranslated`, naming the IL production. This module holds the program
level (declarations, types, extern types and instances, blocks, the
result); `p4blo.frontend.blocks` translates each parser and control; the
architecture layer, V1Switch and its intrinsic metadata, is bound by
`p4blo.frontend.v1model`, the v1model shim of `p4blo.arch.v1model` run in
reverse.

The output is ordinary IR, checked by `p4blo.validator` before it is
returned. Names the IR needs and P4 does not give are made here and
reported in `Translation.notes`: fresh locals for what an elaboration
introduces, and renamings where a P4 name would collide in the IR's
flatter scopes.

The elaborations, briefly (the coverage page has one row each):

- Types: typedefs and `type` are their definitions; a serializable enum is
  its underlying `bit<N>` and its members literals.
- Constants: only what the IR cannot hold is folded: named constants,
  arbitrary-precision `int` arithmetic with the casts that size it, `/`
  and `%`, enum members and `hs.size`. The IL has already made every
  implicit cast explicit, so this also sizes every unsized literal.
- Statements: blocks are flattened, their variables hoisted to
  `Block.locals` (renamed when a name is taken) and their initializers
  become assignments where they stood; compound assignment is the binary
  form; a slice as an lvalue is the read-modify-write of the whole field;
  `switch` on `action_run` is a marker local and an if-chain; `switch` on
  a value is an if-chain; a list or record initializer of a header or
  struct is a fresh local assigned field by field.
- Calls: named arguments are put in parameter order; an extern method, a
  function or a table's `hit` in expression position goes through a fresh
  local, under an `if` when the operand is evaluated lazily; a function is
  inlined; an `in` argument overlapping an `out` one, an `out` argument
  aliasing another, and a slice as an `out` argument go through fresh
  locals, which is P4's copy-in and copy-out made explicit; an action bound
  in a table's action list gets one copy per table.
- Blocks: a sub-parser or sub-control instance is a `CallBlock` naming the
  block, and a block with constructor parameters, or one that owns extern
  state and is instantiated twice, becomes one block per instantiation.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from p4blo import ir, validator
from p4blo.frontend import il
from p4blo.frontend.common import (
    BOOL,
    ERROR,
    ActionB,
    BadConstB,
    Bits,
    ConstB,
    EnumVal,
    ErrorVal,
    Excluded,
    ExternFunctionB,
    FrontendError,
    FunctionB,
    Int,
    NotTranslated,
    Scope,
    Val,
    _wrap,
    bits_type,
    rename_block_vars,
    strip_alias,
    walk_stmts,
)
from p4blo.frontend.il import Node
from p4blo.frontend.normalize import drop_self_assignments
from p4blo.v0 import p4blo_pb2 as pb

if TYPE_CHECKING:
    from p4blo.frontend.blocks import Architecture, BlockCx
    from p4blo.frontend.export import Exporter

__all__ = [
    "Excluded",
    "FrontendError",
    "NotTranslated",
    "Translation",
    "Translator",
    "translate",
    "translate_source",
]


# ---------------------------------------------------------------------------
# The result
# ---------------------------------------------------------------------------


@dataclass
class Translation:
    """A translated program and what the translation had to decide."""

    program: pb.Program
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Program-level state
# ---------------------------------------------------------------------------


class Translator:
    """One program's translation. `p4blo.frontend.v1model` drives it."""

    def __init__(self, export: il.Export, name: str) -> None:
        self.export = export
        self.name = name
        self.notes: list[str] = []
        self.decls = export.declarations
        self.order: dict[str, int] = {}
        self.errors: list[str] = []
        self.header_types: dict[str, pb.HeaderType] = {}
        self.struct_types: dict[str, pb.StructType] = {}
        self.enum_types: dict[str, pb.EnumType] = {}
        self.extern_types: dict[str, pb.ExternType] = {}
        self.extern_instances: dict[str, pb.ExternInstance] = {}
        self.blocks: dict[str, pb.Block] = {}
        # Blocks by (declaration name, constructor argument values).
        self.instantiations: dict[tuple[str, tuple[Val, ...]], str] = {}
        self.block_decls: dict[str, Node] = {}
        self.top_actions: dict[str, Node] = {}
        self.field_renames: dict[tuple[str, str], str] = {}
        self.global_scope = Scope()
        # Set by the architecture binding.
        self.arch: Architecture | None = None
        self._collect()

    # -- declarations

    def _collect(self) -> None:
        scope = self.global_scope
        for i, d in enumerate(self.decls):
            match d.c:
                case "ERROR {%}":
                    for n in d.list(0):
                        if isinstance(n, str) and n not in self.errors:
                            self.errors.append(n)
                case "MATCH_KIND {%}":
                    pass
                case "% CONST % % % ;":
                    # Every constant of the includes is bound; one the IR
                    # cannot represent fails only where it is used.
                    try:
                        scope.bind(d.text(2), ConstB(self.const_value(d.node(1), d.node(3))))
                    except FrontendError as e:
                        scope.bind(d.text(2), BadConstB(e))
                case (
                    "% HEADER % <%> {%}"
                    | "% STRUCT % <%> {%}"
                    | "% HEADER_UNION % <%> {%}"
                    | "% ENUM % {%}"
                    | "% ENUM % % {%}"
                ):
                    name = d.text(1) if d.c != "% ENUM % % {%}" else d.text(2)
                    self.order.setdefault(name, i)
                case "% TYPEDEF % % ;" | "% TYPE % % ;":
                    target = d.a[1]
                    if isinstance(target, Node) and target.t.endswith("DeclarationIR"):
                        self.order.setdefault(target.text(1), i)
                case "% PARSER % <% , %> (%) (%) {% %}" | (
                    "% CONTROL % <% , %> (%) (%) {% APPLY %}"
                ):
                    self.block_decls[d.text(1)] = d
                    self.order.setdefault(d.text(1), i)
                case "% ACTION % (%) %":
                    self.top_actions[d.text(1)] = d
                    scope.bind(d.text(1), ActionB(d.text(1), d))
                case "% % <% , %> (%) %" | "% % %":
                    if d.t == "functionDeclarationIR":
                        scope.bind(self.function_name(d), FunctionB(d))
                case "% EXTERN % ;":
                    fname = d.node(1).text(1)
                    scope.bind(fname, ExternFunctionB(fname, d))
                case _:
                    if d.t == "functionDeclarationIR":
                        scope.bind(self.function_name(d), FunctionB(d))

    @staticmethod
    def function_name(d: Node) -> str:
        return d.node(1).text(1)

    # -- compile-time values

    def const_value(self, t: Node, init: Node) -> Val:
        """The value of a constant declaration's `= _VALUE v` initializer."""
        if init.c != "= _VALUE %":
            raise il.ILError(f"unexpected constant initializer {init.c!r}")
        v = self.value(init.node(0), t)
        if v is None:
            raise NotTranslated("constantDeclarationIR", f"a {strip_alias(t).c!r} constant")
        return v

    def value(self, v: Node, t: Node | None = None) -> Val | None:
        """A run-time value (`2.1.1-value.watsup`) as a compile-time value."""
        match v.c:
            case "% W %":
                return _wrap(v.num(0), v.num(1))
            case "D %":
                return Int(v.num(0))
            case "% S %":
                raise Excluded("literalExpressionIR: nat S int (signed)", "by scope")
            case "TRUE":
                return True
            case "FALSE":
                return False
            case "_B %":
                b = v.a[0]
                return bool(b)
            case "ERROR . %":
                return ErrorVal(v.text(0))
            case "% . %":
                return self.enum_value(v.text(0), v.text(1), t)
            case "% . % . %":
                inner = v.node(2)
                return self.value(inner)
            case _:
                return None

    def enum_value(self, enum_name: str, member_name: str, t: Node | None) -> Val:
        decl = self.enum_decl(enum_name)
        if decl is not None and decl.c == "% ENUM % % {%}":
            for nv in decl.nodes(3):
                if nv.text(0) == member_name:
                    val = self.value(nv.node(1))
                    if val is None:
                        break
                    underlying = strip_alias(decl.node(1))
                    return self.cast_val(val, underlying) or val
            raise NotTranslated("namedValueIR", f"{enum_name}.{member_name}")
        return EnumVal(enum_name, member_name)

    def enum_decl(self, name: str) -> Node | None:
        for d in self.decls:
            if d.c == "% ENUM % {%}" and d.text(1) == name:
                return d
            if d.c == "% ENUM % % {%}" and d.text(2) == name:
                return d
        return None

    def cast_val(self, v: Val, t: Node) -> Val | None:
        t = strip_alias(t)
        match t.c:
            case "BIT <%>":
                n = t.num(0)
                match v:
                    case Int() | Bits():
                        return _wrap(n, v.value)
                    case bool():
                        return Bits(1, int(v)) if n == 1 else None
                    case _:
                        return None
            case "BOOL":
                match v:
                    case bool():
                        return v
                    case Bits() if v.width == 1:
                        return bool(v.value)
                    case _:
                        return None
            case "INT":
                match v:
                    case Int():
                        return v
                    case Bits():
                        return Int(v.value)
                    case _:
                        return None
            case "ENUM % <%> {%}":
                return self.cast_val(v, t.node(1))
            case "SET <%>":
                return self.cast_val(v, t.node(0))
            case "ERROR" | "ENUM % {%}":
                return v if isinstance(v, ErrorVal | EnumVal) else None
            case _:
                return None

    # -- types

    def type_of(self, t: Node, what: str = "") -> pb.Type:
        """The IR type of a typeIR, registering the declarations it needs."""
        t = strip_alias(t)
        match t.c:
            case "BIT <%>":
                n = t.num(0)
                if n < 1:
                    raise NotTranslated("fixedBitTypeIR", "bit<0>")
                return bits_type(n)
            case "BOOL":
                return BOOL
            case "ERROR":
                return ERROR
            case "HEADER % <%> {%}":
                self._generic_check(t)
                self._header(t)
                return pb.Type(header=t.text(0))
            case "STRUCT % <%> {%}":
                self._generic_check(t)
                self._struct(t)
                return pb.Type(struct=t.text(0))
            case "HEADER_STACK % [%]":
                elem = strip_alias(t.node(0))
                if elem.c != "HEADER % <%> {%}":
                    raise Excluded("headerStackTypeIR of header unions", "by scope")
                self.type_of(elem)
                return pb.Type(stack=pb.StackType(header=elem.text(0), size=t.num(1)))
            case "ENUM % {%}":
                self._enum(t)
                return pb.Type(enum_type=t.text(0))
            case "ENUM % <%> {%}":
                return self.type_of(t.node(1))
            case "STRING":
                raise Excluded("stringTypeIR (STRING)", "by scope", what)
            case "INT":
                raise Excluded("intTypeIR (INT)", "by elaboration", what)
            case "INT <%>":
                raise Excluded("fixedIntTypeIR (INT<n>)", "by scope", what)
            case "VARBIT <%>":
                raise Excluded("varBitTypeIR (VARBIT<n>)", "by scope", what)
            case "HEADER_UNION % <%> {%}":
                raise Excluded("headerUnionTypeIR", "by scope", t.text(0))
            case "LIST <%>" | "TUPLE <%>":
                raise Excluded("listTypeIR, tupleTypeIR", "by elaboration", what)
            case "ARRAY % [%]":
                raise Excluded("arrayTypeIR (ARRAY t[n])", "by scope", what)
            case "MATCH_KIND":
                raise NotTranslated("matchKindTypeIR", "a value of type match_kind")
            case "VOID":
                raise il.ILError("void has no IR type")
            case _:
                raise NotTranslated(t.t, f"type {t.short()}")

    def _generic_check(self, t: Node) -> None:
        if t.list(1):
            raise Excluded(
                "typeArgumentIR, type arguments on STRUCT, HEADER, EXTERN, PARSER, CONTROL",
                "by elaboration",
                t.text(0),
            )

    def _fields(self, t: Node) -> list[pb.Field]:
        out: list[pb.Field] = []
        for f in t.nodes(2):
            name = self.field_name(t, f.text(2))
            out.append(pb.Field(name=name, type=self.type_of(f.node(1), f.text(2))))
        return out

    def field_name(self, t: Node, name: str) -> str:
        """A field's IR name: its own, unless the architecture binding had
        to rename it (a user field named like a contract field)."""
        t = strip_alias(t)
        if t.c == "STRUCT % <%> {%}":
            return self.field_renames.get((t.text(0), name), name)
        return name

    def _header(self, t: Node) -> None:
        name = t.text(0)
        if name in self.header_types:
            return
        self.header_types[name] = pb.HeaderType(name=name)  # placeholder against cycles
        fields = self._fields(t)
        for f in fields:
            if f.type.WhichOneof("kind") not in ("bits", "boolean"):
                raise Excluded(
                    "headerTypeIR field of a non-bit type", "by scope", f"{name}.{f.name}"
                )
        self.header_types[name] = pb.HeaderType(name=name, fields=fields)

    def _struct(self, t: Node) -> None:
        name = t.text(0)
        if name in self.struct_types:
            return
        self.struct_types[name] = pb.StructType(name=name)
        self.struct_types[name] = pb.StructType(name=name, fields=self._fields(t))

    def _enum(self, t: Node) -> None:
        name = t.text(0)
        if name not in self.enum_types:
            members = [m for m in t.list(1) if isinstance(m, str)]
            self.enum_types[name] = pb.EnumType(name=name, members=members)

    # -- blocks

    def role_block(self, decl: Node, args: Sequence[Node], kind: str, part: str) -> pb.Block:
        """The block for one of the package's arguments."""
        from p4blo.frontend.blocks import BlockCx, ctor_value, translate_block

        folder = BlockCx(self, decl, "__args__", kind, self.global_scope)
        values = [ctor_value(folder, a) for a in args]
        name = decl.text(1)
        if name in self.blocks:
            name = self.fresh_program_name(name)
        meta_index = {"parser": 2, "control": 1}.get(kind)
        cx = translate_block(self, decl, name, kind, values, part, meta_index)
        self.blocks[name] = cx.block
        self.instantiations[(decl.text(1), tuple(values))] = name
        return cx.block

    def sub_block(self, decl: Node, args: Sequence[Node], caller: BlockCx) -> str:
        """The block a sub-parser or sub-control instantiation calls."""
        from p4blo.frontend.blocks import block_kind, ctor_value, owns_state, translate_block

        values = [ctor_value(caller, a) for a in args]
        key: tuple[str, tuple[Val, ...]] = (decl.text(1), tuple(values))
        if owns_state(decl):
            # Each instantiation of a block with extern state is its own block.
            key = (decl.text(1), (*values, Int(len(self.instantiations))))
        if key in self.instantiations:
            return self.instantiations[key]
        base = decl.text(1)
        name = base if base not in self.blocks else self.fresh_program_name(base)
        self.instantiations[key] = name
        self.blocks[name] = pb.Block(name=name)  # reserve the name against recursion
        kind = block_kind(decl)
        if kind != caller.kind:
            raise NotTranslated(
                "instantiationIR", f"{caller.kind} {caller.block.name} calls {kind} {base}"
            )
        cx = translate_block(self, decl, name, kind, values)
        self.blocks[name] = cx.block
        if values or name != base:
            self.notes.append(f"{base} instantiated as block {name}")
        return name

    def ordered_blocks(self, roots: Sequence[str]) -> list[pb.Block]:
        """Every block reachable from the roles, callees before callers."""
        out: list[pb.Block] = []
        seen: set[str] = set()

        def visit(name: str) -> None:
            if name in seen:
                return
            seen.add(name)
            block = self.blocks[name]
            stmts = list(block.body) + [s for st in block.states for s in st.body]
            for s in walk_stmts(stmts):
                if s.WhichOneof("kind") == "call_block":
                    visit(s.call_block.block)
            out.append(block)

        for r in roots:
            visit(r)
        return out

    # -- program assembly

    def fresh_program_name(self, base: str) -> str:
        taken = self.program_names()
        name, i = base, 0
        while name in taken:
            name = f"{base}_{i}"
            i += 1
        return name

    def program_names(self) -> set[str]:
        return (
            set(self.header_types)
            | set(self.struct_types)
            | set(self.enum_types)
            | set(self.extern_types)
            | set(self.extern_instances)
            | set(self.blocks)
            | set(self.block_decls)
        )

    def add_extern_type(self, decl: pb.ExternType) -> str:
        """Add a monomorphic extern type, reusing an identical one; a second
        signature of the same family is named `family.suffix`."""
        family = decl.name
        for name, existing in self.extern_types.items():
            if ir.extern_family(name) == family:
                probe = pb.ExternType()
                probe.CopyFrom(decl)
                probe.name = name
                if probe == existing:
                    return name
        name = family
        i = 1
        while name in self.extern_types:
            name = f"{family}.{i}"
            i += 1
        decl = copy.deepcopy(decl)
        decl.name = name
        self.extern_types[name] = decl
        return name

    def add_extern_instance(self, base: str, extern_type: str, args: Sequence[pb.Literal]) -> str:
        name = base if base not in self.program_names() else self.fresh_program_name(base)
        self.extern_instances[name] = pb.ExternInstance(
            name=name, extern_type=extern_type, args=list(args)
        )
        return name

    def assemble(
        self,
        blocks: Sequence[pb.Block],
        headers: str,
        metadata: str,
        exports: Sequence[tuple[str, str]],
    ) -> pb.Program:
        """The program, declarations in source order."""

        def ordered[T](table: dict[str, T]) -> list[T]:
            return [table[k] for k in sorted(table, key=lambda k: self.order.get(k, 1 << 30))]

        errors = list(ir.CORE_ERRORS) + [e for e in self.errors if e not in ir.CORE_ERRORS]
        program = pb.Program(
            name=self.name,
            errors=errors,
            header_types=ordered(self.header_types),
            struct_types=ordered(self.struct_types),
            enum_types=ordered(self.enum_types),
            extern_types=list(self.extern_types.values()),
            extern_instances=list(self.extern_instances.values()),
            blocks=list(blocks),
            headers=headers,
            metadata=metadata,
            exports=[pb.Export(role=r, block=b) for r, b in exports],
        )
        return program


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def translate(export: il.Export, name: str = "program") -> Translation:
    """Translate an export. The package must be one `p4blo.frontend.v1model`
    binds; the result is validated."""
    from p4blo.frontend import v1model

    tr = Translator(export, name)
    program = v1model.bind(tr)
    program = finish(program, tr.notes)
    problems = validator.validate(program)
    if problems:
        text = "\n".join(str(p) for p in problems[:20])
        raise FrontendError(f"the translation of {name} does not validate:\n{text}")
    return Translation(program, tr.notes)


def translate_source(
    source: Path, exporter: Exporter | None = None, name: str | None = None
) -> Translation:
    """Export `source` with P4-SpecTec and translate it."""
    from p4blo.frontend.export import ExportError, find_exporter

    if exporter is None:
        exporter = find_exporter()
        if exporter is None:
            raise ExportError("no P4-SpecTec checkout; run tests/oracle/build.sh")
    export = exporter.export(Path(source))
    return translate(export, name or Path(source).stem)


# ---------------------------------------------------------------------------
# Finishing passes
# ---------------------------------------------------------------------------


def finish(program: pb.Program, notes: list[str]) -> pb.Program:
    """Remove self-assignments and rename block-scope names that collide in
    the IR's scopes."""
    program = copy.deepcopy(program)
    top = (
        {d.name for d in program.header_types}
        | {d.name for d in program.struct_types}
        | {d.name for d in program.enum_types}
        | {d.name for d in program.extern_types}
        | {d.name for d in program.extern_instances}
        | {d.name for d in program.blocks}
    )
    for block in program.blocks:
        # `x = x` does nothing; the printer's shim produces it
        # (`meta.ingress_port = standard_metadata.ingress_port` read back).
        drop_self_assignments(block.body)
        for st in block.states:
            drop_self_assignments(st.body)
        for a in block.actions:
            drop_self_assignments(a.body)
        action_params = {p.name for a in block.actions for p in a.params}
        other = (
            {a.name for a in block.actions}
            | {t.name for t in block.tables}
            | {s.name for s in block.states}
        )
        taken = set(top) | action_params | other
        mapping: dict[str, str] = {}
        seen: set[str] = set()
        for v in [*block.params, *block.locals]:
            if v.name in top or v.name in action_params or v.name in other or v.name in seen:
                new, i = f"{v.name}_", 0
                while new in taken or new in seen:
                    new = f"{v.name}_{i}"
                    i += 1
                notes.append(
                    f"{block.name}: {v.name} renamed {new}, a name taken in the IR's scopes"
                )
                mapping[v.name] = new
                taken.add(new)
            seen.add(mapping[v.name] if v.name in mapping else v.name)
        if mapping:
            rename_block_vars(block, mapping)
    return program
