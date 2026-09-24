# pyright: strict
"""The program: roles as keywords, classes and instances as references.

    program = Program("forwarder", headers=headers, metadata=metadata,
                      parser=MyParser, control=MyIngress, deparser=MyDeparser,
                      externs=[csum], errors=errors)
    program.build()  # a pb.Program

`build()` runs the second clock once (see `p4blo.edsl.__init__`): it makes
a core `Program`, declares the errors, registers the headers and metadata
structs and every type they reach, declares the externs in the order
given, then assembles the parser, the control and the deparser in that
order, each a class instantiated once with its methods run against a
recording `self`. A sub-block is built when first called, ahead of its
caller. Each `build()` starts afresh, so a program may be built twice.

Types are registered on first use: a header or struct class the first
time a program meets it (through `headers`, `metadata`, a parameter, a
local or a lookahead), depth first so that a struct's field types precede
it; an `Enum` the same way. Errors are declared up front from the `Errors`
classes given, after core.p4's seven.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, get_args, get_origin

from p4blo.edsl.blocks import Block, Control, Deparser, ExternResult, Parser
from p4blo.edsl.core.blocks import Block as CoreBlock
from p4blo.edsl.core.program import Program as CoreProgram
from p4blo.edsl.core.types import ExternInstance as CoreExternInstance
from p4blo.edsl.core.types import ExternType as CoreExternType
from p4blo.edsl.errors import EdslError, provenance
from p4blo.edsl.externs import Extern
from p4blo.edsl.values import CoreErrors, Enum, Errors
from p4blo.edsl.views import Header, Stack, Struct, View, direction_of, pb_type_of
from p4blo.v0 import p4blo_pb2 as pb


class Build:
    """One build of one program: the core program under construction and
    what has been registered with it so far."""

    def __init__(self, name: str) -> None:
        with provenance():
            self.core = CoreProgram(name)
        self.registered: set[type] = set()
        self.blocks: dict[type[Block], CoreBlock] = {}
        self.extern_types: dict[str, CoreExternType] = {}
        self.externs: dict[int, CoreExternInstance] = {}
        self.pending: list[ExternResult] = []

    # -- types -------------------------------------------------------------

    def pb_type(self, annotation: object) -> pb.Type:
        """The IR type of an annotation, registering what it names."""
        self.register(annotation)
        return pb_type_of(annotation)

    def register(self, annotation: object) -> None:
        _, t = direction_of(annotation)
        if isinstance(t, type) and issubclass(t, View | Enum):
            self._register_type(t)
        elif get_origin(t) is Stack:
            header = get_args(t)[0]
            if isinstance(header, type) and issubclass(header, Header):
                self._register_type(header)

    def _register_type(self, cls: type[View] | type[Enum]) -> None:
        if cls in self.registered:
            return
        self.registered.add(cls)
        with provenance():
            if issubclass(cls, Enum):
                self.core.enum(cls.__ir_name__, *cls.__members__)
                return
            for spec in cls.__fields__.values():
                self.register(spec.annotation)
            fields = {spec.ir_name: spec.kind.pb_type for spec in cls.__fields__.values()}
            if issubclass(cls, Header):
                self.core.header(cls.__ir_name__, **fields)
            else:
                self.core.struct(cls.__ir_name__, **fields)

    def struct(self, cls: object, what: str) -> str:
        if not (isinstance(cls, type) and issubclass(cls, Struct)):
            raise EdslError(f"{what} must be a Struct class, got {cls!r}")
        self._register_type(cls)
        return cls.__ir_name__

    # -- blocks and externs ------------------------------------------------

    def block(self, cls: type[Block], *, before: CoreBlock | None = None) -> CoreBlock:
        """The core block of `cls`, assembled on first use."""
        if cls not in self.blocks:
            cls._assemble(self, before)  # pyright: ignore[reportPrivateUsage]
        return self.blocks[cls]

    def extern(self, instance: object) -> None:
        if not isinstance(instance, Extern):
            raise EdslError(
                f"externs are extern instances such as Register[bit8](...), got {instance!r}"
            )
        if id(instance) in self.externs:
            raise EdslError(f"extern instance {instance.name!r} is listed twice")
        self.externs[id(instance)] = instance._declare(self)  # pyright: ignore[reportPrivateUsage]

    def extern_core(self, instance: object) -> CoreExternInstance:
        core = self.externs.get(id(instance))
        if core is None:
            name = instance.name if isinstance(instance, Extern) else repr(instance)
            raise EdslError(f"extern instance {name!r} is not listed in Program(externs=[...])")
        return core


class Program:
    """A program: its name, types, blocks by role, externs and errors."""

    def __init__(
        self,
        name: str,
        *,
        headers: type[Struct],
        metadata: type[Struct],
        parser: type[Parser[Any, Any]],
        control: type[Control[Any, Any]],
        deparser: type[Deparser[Any]],
        externs: Sequence[Extern] = (),
        errors: type[Errors] | Sequence[type[Errors]] = (),
    ) -> None:
        self.name = name
        self.headers = headers
        self.metadata = metadata
        self.parser = parser
        self.control = control
        self.deparser = deparser
        self.externs = list(externs)
        self.errors: list[type[Errors]] = [errors] if isinstance(errors, type) else list(errors)
        for role, cls, kind in (
            ("parser", parser, Parser),
            ("control", control, Control),
            ("deparser", deparser, Deparser),
        ):
            if not (isinstance(cls, type) and issubclass(cls, kind)):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise EdslError(f"{role} must be a {kind.__name__} class, got {cls!r}")

    def build(self) -> pb.Program:
        """The IR of the program, built afresh."""
        build = Build(self.name)
        for errors in self.errors:
            if not (isinstance(errors, type) and issubclass(errors, Errors)):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise EdslError(f"errors are Errors classes, got {errors!r}")
            if errors is CoreErrors:
                continue
            for member in errors.__members__:
                with provenance():
                    build.core.error(member)
        with provenance():
            build.core.headers = build.core.types.structs[build.struct(self.headers, "headers")]
            build.core.metadata = build.core.types.structs[build.struct(self.metadata, "metadata")]
        for instance in self.externs:
            build.extern(instance)
        for role, cls in (
            ("parser", self.parser),
            ("control", self.control),
            ("deparser", self.deparser),
        ):
            block = build.block(cls)
            with provenance():
                build.core.export(role, block)
        if build.pending:
            result = build.pending[0]
            where = f" (defined at {result.location})" if result.location else ""
            raise EdslError(
                f"the result of {result.method}(...) was never assigned{where}", location=None
            )
        with provenance():
            return build.core.build()


__all__ = ["Build", "Program"]
