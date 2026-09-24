"""The program builder.

A `Program` collects declarations in the order they are made and builds a
`pb.Program` from them. It starts with core.p4's seven errors, as the IR
requires, and owns the `TypeTable` every expression consults.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from p4blo.edsl.core.blocks import Block, Control, Deparser, Parser
from p4blo.edsl.core.expr import EnumType, Errors, Expr, Operand, constant, literal
from p4blo.edsl.core.types import (
    EdslError,
    ExternInstance,
    ExternType,
    HeaderType,
    MethodSpec,
    ParamSpec,
    StructType,
    TypeLike,
    TypeTable,
    as_type,
)
from p4blo.ir import CORE_ERRORS
from p4blo.v0 import p4blo_pb2 as pb


class Program:
    """A p4blo program under construction."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.types = TypeTable(errors=list(CORE_ERRORS))
        self.errors = Errors(self.types)
        self._names: dict[str, str] = {}
        self._header_types: list[HeaderType] = []
        self._struct_types: list[StructType] = []
        self._enum_types: list[EnumType] = []
        self._extern_types: list[ExternType] = []
        self._extern_instances: list[ExternInstance] = []
        self._blocks: list[Block] = []
        self._exports: list[tuple[str, str]] = []
        self._headers: StructType | None = None
        self._metadata: StructType | None = None

    # -- names -------------------------------------------------------------

    def declares(self, name: str) -> bool:
        """Whether `name` is taken at program level."""
        return name in self._names

    def _declare(self, name: str, what: str) -> None:
        if not name:
            raise EdslError(f"a {what} needs a name")
        if name in self._names:
            raise EdslError(f"{what} {name!r} reuses the name of a {self._names[name]}")
        self._names[name] = what

    # -- types -------------------------------------------------------------

    def header(self, name: str, /, **fields: TypeLike) -> HeaderType:
        """Declare a header type; keyword fields are bit<N> or bool, in order."""
        self._declare(name, "header")
        h = HeaderType(name, fields)
        self._header_types.append(h)
        self.types.headers[name] = h
        return h

    def struct(self, name: str, /, **fields: TypeLike) -> StructType:
        """Declare a struct type; keyword fields may be any type, in order."""
        self._declare(name, "struct")
        s = StructType(name, fields)
        self._struct_types.append(s)
        self.types.structs[name] = s
        return s

    def enum(self, name: str, *members: str) -> EnumType:
        """Declare a plain enum; `e.MEMBER` is then a literal."""
        self._declare(name, "enum")
        e = EnumType(self.types, name, members)
        self._enum_types.append(e)
        self.types.enums[name] = list(members)
        return e

    def error(self, name: str) -> Expr:
        """Declare an error after the core ones and return its literal."""
        if not name:
            raise EdslError("an error needs a name")
        if name in self.types.errors:
            raise EdslError(f"error {name!r} is already declared")
        self.types.errors.append(name)
        return self.errors[name]

    def literal(self, value: Operand, type: TypeLike) -> Expr:
        """A literal of an explicit type, for when no operand supplies one."""
        return literal(self.types, value, as_type(type))

    # -- H and M -----------------------------------------------------------

    @property
    def headers(self) -> StructType | None:
        """The struct type of the headers value H."""
        return self._headers

    @headers.setter
    def headers(self, struct: StructType) -> None:
        self.set_headers(struct)

    def set_headers(self, struct: StructType) -> None:
        self._headers = self._own_struct(struct, "headers")

    @property
    def metadata(self) -> StructType | None:
        """The struct type of the metadata value M."""
        return self._metadata

    @metadata.setter
    def metadata(self, struct: StructType) -> None:
        self.set_metadata(struct)

    def set_metadata(self, struct: StructType) -> None:
        self._metadata = self._own_struct(struct, "metadata")

    def _own_struct(self, struct: StructType, what: str) -> StructType:
        if not isinstance(struct, StructType) or self.types.structs.get(struct.name) is not struct:
            raise EdslError(f"{what} must be a struct declared by this program")
        return struct

    # -- externs -----------------------------------------------------------

    def extern_type(
        self,
        name: str,
        *,
        constructor: Sequence[TypeLike | tuple[str, TypeLike]] = (),
        methods: Mapping[str, Sequence[ParamSpec] | MethodSpec] = {},
    ) -> ExternType:
        """Declare a monomorphic extern type.

        `constructor` lists the constructor parameter types; `methods` maps a
        method name to its `(name, direction, type)` params, or to
        `method(params, returns=type)` when it returns a value.
        """
        self._declare(name, "extern type")
        t = ExternType(name, constructor, methods)
        self._extern_types.append(t)
        return t

    def extern_instance(self, name: str, extern_type: ExternType, *args: Operand) -> ExternInstance:
        """Instantiate an extern; args are constants of the constructor's types."""
        self._declare(name, "extern instance")
        if not isinstance(extern_type, ExternType):
            raise EdslError(f"extern_instance needs an extern type, got {extern_type!r}")
        params = extern_type.constructor_params
        if len(args) != len(params):
            raise EdslError(
                f"extern {extern_type.name} takes {len(params)} constructor args, got {len(args)}"
            )
        values = [constant(self.types, a, p.type) for a, p in zip(args, params, strict=True)]
        inst = ExternInstance(name, extern_type, values)
        self._extern_instances.append(inst)
        return inst

    # -- blocks ------------------------------------------------------------

    def _default_params(self, name: str, spec: Sequence[tuple[str, str]]) -> list[ParamSpec]:
        params: list[ParamSpec] = []
        for pname, direction in spec:
            struct = self._headers if pname == "hdr" else self._metadata
            if struct is None:
                raise EdslError(
                    f"block {name}: set the program's headers and metadata structs first, "
                    "or give params explicitly"
                )
            params.append((pname, direction, struct))
        return params

    def parser(self, name: str, params: Sequence[ParamSpec] | None = None) -> Parser:
        """Declare a parser; by default over `(out H hdr, inout M meta)`."""
        if params is None:
            params = self._default_params(name, [("hdr", "out"), ("meta", "inout")])
        return self._add_block(Parser(self, name, params))

    def control(self, name: str, params: Sequence[ParamSpec] | None = None) -> Control:
        """Declare a control; by default over `(inout H hdr, inout M meta)`."""
        if params is None:
            params = self._default_params(name, [("hdr", "inout"), ("meta", "inout")])
        return self._add_block(Control(self, name, params))

    def deparser(self, name: str, params: Sequence[ParamSpec] | None = None) -> Deparser:
        """Declare a deparser; by default over `(in H hdr)`."""
        if params is None:
            params = self._default_params(name, [("hdr", "in")])
        return self._add_block(Deparser(self, name, params))

    def _add_block[B: Block](self, block: B) -> B:
        return self.add_block(block)

    def add_block[B: Block](self, block: B, *, before: Block | None = None) -> B:
        """Declare a block constructed directly; `before` places it ahead of
        a declared block, for a callee discovered while building its caller."""
        self._declare(block.name, "block")
        if before is None:
            self._blocks.append(block)
        else:
            self._blocks.insert(self._blocks.index(before), block)
        return block

    def block(self, name: str) -> Block:
        for b in self._blocks:
            if b.name == name:
                return b
        raise EdslError(f"no block {name!r}")

    def export(self, role: str, block: Block | str) -> None:
        """Offer a block to the architecture under `role`."""
        if not role:
            raise EdslError("an export needs a role")
        if any(r == role for r, _ in self._exports):
            raise EdslError(f"role {role!r} is exported twice")
        name = self.block(block.name if isinstance(block, Block) else block).name
        self._exports.append((role, name))

    # -- build -------------------------------------------------------------

    def build(self) -> pb.Program:
        """The IR of everything declared so far, in declaration order."""
        program = pb.Program(name=self.name, errors=self.types.errors)
        program.header_types.extend(h.build() for h in self._header_types)
        program.struct_types.extend(s.build() for s in self._struct_types)
        program.enum_types.extend(e.build() for e in self._enum_types)
        program.extern_types.extend(t.build() for t in self._extern_types)
        program.extern_instances.extend(i.build() for i in self._extern_instances)
        program.blocks.extend(b.build() for b in self._blocks)
        if self._headers is not None:
            program.headers = self._headers.name
        if self._metadata is not None:
            program.metadata = self._metadata.name
        for role, block in self._exports:
            program.exports.add(role=role, block=block)
        return program
