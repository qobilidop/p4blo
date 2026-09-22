"""Load, save and index IR programs.

The text format is the readable representation and the golden format; binary
and JSON are transports. `Index` resolves names to declarations and is shared
by the validator, the interpreter and the printer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from google.protobuf import json_format, text_format

from p4blo.v0 import p4blo_pb2 as pb

# Core errors, in the order Program.errors must begin with.
CORE_ERRORS: tuple[str, ...] = (
    "NoError",
    "PacketTooShort",
    "NoMatch",
    "StackOutOfBounds",
    "HeaderTooShort",
    "ParserTimeout",
    "ParserInvalidArgument",
)


def load_text(source: str | Path) -> pb.Program:
    """Parse a program from text format, given the text or a path to it."""
    text = source.read_text() if isinstance(source, Path) else source
    return text_format.Parse(text, pb.Program())


def dump_text(program: pb.Program) -> str:
    return text_format.MessageToString(program)


def load_binary(data: bytes) -> pb.Program:
    return pb.Program.FromString(data)


def dump_binary(program: pb.Program) -> bytes:
    return program.SerializeToString(deterministic=True)


def load_json(text: str) -> pb.Program:
    return json_format.Parse(text, pb.Program())


def dump_json(program: pb.Program) -> str:
    return json_format.MessageToJson(program, preserving_proto_field_name=True)


class DuplicateName(Exception):
    """Two declarations share a name in one scope, or a name is empty."""


@dataclass
class BlockScope:
    """The declarations of one block, each by name.

    `vars` holds the block's params and locals. Action params are under
    `action_params[action_name]`; an action body sees those plus `vars`.
    """

    block: pb.Block
    vars: dict[str, pb.Param | pb.Var] = field(default_factory=dict)
    actions: dict[str, pb.Action] = field(default_factory=dict)
    action_params: dict[str, dict[str, pb.Param]] = field(default_factory=dict)
    tables: dict[str, pb.Table] = field(default_factory=dict)
    states: dict[str, pb.State] = field(default_factory=dict)

    def var(self, name: str, action: str | None = None) -> pb.Param | pb.Var:
        """The variable `name` sees from the block body, or from `action`."""
        if action is not None and name in self.action_params[action]:
            return self.action_params[action][name]
        return self.vars[name]


@dataclass
class Index:
    """Every declaration of a program by name.

    Built by `Index.build`, which raises `DuplicateName` on a repeated or
    empty name within a scope and on a block-level name that reuses a
    program-level one. Program-level declarations share one namespace, as
    the schema says, and `program_names` holds all of them.
    """

    program: pb.Program
    header_types: dict[str, pb.HeaderType] = field(default_factory=dict)
    struct_types: dict[str, pb.StructType] = field(default_factory=dict)
    enum_types: dict[str, pb.EnumType] = field(default_factory=dict)
    extern_types: dict[str, pb.ExternType] = field(default_factory=dict)
    extern_instances: dict[str, pb.ExternInstance] = field(default_factory=dict)
    blocks: dict[str, pb.Block] = field(default_factory=dict)
    scopes: dict[str, BlockScope] = field(default_factory=dict)
    program_names: set[str] = field(default_factory=set)
    errors: dict[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, program: pb.Program) -> Index:
        index = cls(program)

        def add(table: dict, decl, taken: set[str], where: str) -> None:
            if not decl.name:
                raise DuplicateName(f"empty name in {where}")
            if decl.name in taken:
                raise DuplicateName(f"{decl.name!r} declared twice in {where}")
            taken.add(decl.name)
            table[decl.name] = decl

        top = index.program_names
        for d in program.header_types:
            add(index.header_types, d, top, "program")
        for d in program.struct_types:
            add(index.struct_types, d, top, "program")
        for d in program.enum_types:
            add(index.enum_types, d, top, "program")
        for d in program.extern_types:
            add(index.extern_types, d, top, "program")
        for d in program.extern_instances:
            add(index.extern_instances, d, top, "program")
        for b in program.blocks:
            add(index.blocks, b, top, "program")
        for i, name in enumerate(program.errors):
            if not name or name in index.errors:
                raise DuplicateName(f"error {name!r} at {i}")
            index.errors[name] = i

        for b in program.blocks:
            scope = BlockScope(b)
            taken = set(top)
            where = f"block {b.name!r}"
            for p in b.params:
                add(scope.vars, p, taken, where)
            for v in b.locals:
                add(scope.vars, v, taken, where)
            for a in b.actions:
                add(scope.actions, a, taken, where)
                params: dict[str, pb.Param] = {}
                action_taken = set(taken)
                for p in a.params:
                    add(params, p, action_taken, f"action {a.name!r} of {where}")
                scope.action_params[a.name] = params
            for t in b.tables:
                add(scope.tables, t, taken, where)
            for s in b.states:
                add(scope.states, s, taken, where)
            index.scopes[b.name] = scope
        return index

    def exported(self, role: str) -> pb.Block:
        for e in self.program.exports:
            if e.role == role:
                return self.blocks[e.block]
        raise KeyError(role)

    def fields(self, type_name: str) -> list[pb.Field]:
        """The fields of a header or struct type."""
        if type_name in self.header_types:
            return list(self.header_types[type_name].fields)
        return list(self.struct_types[type_name].fields)

    def field_index(self, type_name: str, field_name: str) -> int:
        for i, f in enumerate(self.fields(type_name)):
            if f.name == field_name:
                return i
        raise KeyError(f"{type_name}.{field_name}")


def dotted_path(expr: pb.Expr) -> str | None:
    """A key expression as the dotted path a host names it by, or None.

    Only a chain of field accesses off a variable has one: `hdr.ipv4.dstAddr`.
    """
    match expr.WhichOneof("kind"):
        case "var":
            return expr.var
        case "member":
            base = dotted_path(expr.member.base)
            return None if base is None else f"{base}.{expr.member.field}"
        case _:
            return None


def key_name(key: pb.Key) -> str | None:
    """The name a host uses for a table key: `Key.name`, else its dotted path."""
    return key.name or dotted_path(key.expr)
