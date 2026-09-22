"""Load, save and index IR programs.

The text format is the readable representation and the golden format; binary
and JSON are transports. `Index` resolves ids to declarations and is shared by
the validator, the interpreter and the printer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from google.protobuf import json_format, text_format

from p4blo.v0 import p4blo_pb2 as pb

# Core errors, at the indices Program.errors must give them.
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


class DuplicateId(Exception):
    """Two declarations share an id, or a declaration has id 0."""


type Declaration = (
    pb.HeaderType
    | pb.StructType
    | pb.EnumType
    | pb.ExternType
    | pb.ExternInstance
    | pb.Block
    | pb.Action
    | pb.Table
    | pb.State
    | pb.Param
    | pb.Var
)


@dataclass
class Index:
    """Every declaration of a program by id.

    Built by `Index.build`, which raises `DuplicateId` on a repeated or zero
    id. `owner` maps a block-scoped declaration (param, local, action, table,
    state, action param) to the id of the block or action that declares it.
    """

    program: pb.Program
    header_types: dict[int, pb.HeaderType] = field(default_factory=dict)
    struct_types: dict[int, pb.StructType] = field(default_factory=dict)
    enum_types: dict[int, pb.EnumType] = field(default_factory=dict)
    extern_types: dict[int, pb.ExternType] = field(default_factory=dict)
    extern_instances: dict[int, pb.ExternInstance] = field(default_factory=dict)
    blocks: dict[int, pb.Block] = field(default_factory=dict)
    actions: dict[int, pb.Action] = field(default_factory=dict)
    tables: dict[int, pb.Table] = field(default_factory=dict)
    states: dict[int, pb.State] = field(default_factory=dict)
    vars: dict[int, pb.Param | pb.Var] = field(default_factory=dict)
    owner: dict[int, int] = field(default_factory=dict)
    all: dict[int, Declaration] = field(default_factory=dict)

    @classmethod
    def build(cls, program: pb.Program) -> Index:
        index = cls(program)

        def add(table: dict, decl, owner: int | None = None) -> None:
            if decl.id == 0 or decl.id in index.all:
                raise DuplicateId(f"id {decl.id} ({decl.name!r})")
            table[decl.id] = decl
            index.all[decl.id] = decl
            if owner is not None:
                index.owner[decl.id] = owner

        for d in program.header_types:
            add(index.header_types, d)
        for d in program.struct_types:
            add(index.struct_types, d)
        for d in program.enum_types:
            add(index.enum_types, d)
        for d in program.extern_types:
            add(index.extern_types, d)
        for d in program.extern_instances:
            add(index.extern_instances, d)
        for b in program.blocks:
            add(index.blocks, b)
            for p in b.params:
                add(index.vars, p, b.id)
            for v in b.locals:
                add(index.vars, v, b.id)
            for a in b.actions:
                add(index.actions, a, b.id)
                for p in a.params:
                    add(index.vars, p, a.id)
            for t in b.tables:
                add(index.tables, t, b.id)
            for s in b.states:
                add(index.states, s, b.id)
        return index

    def exported(self, role: str) -> pb.Block:
        for e in self.program.exports:
            if e.role == role:
                return self.blocks[e.block]
        raise KeyError(role)
