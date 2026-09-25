# pyright: strict
"""Private compilation context shared by block and architecture builders.

One Build owns the core type table, extern instances and assembled blocks.
A block is assembled on first use, with sub-blocks ahead of their caller.
An architecture uses one Build for all exports, retaining shared declaration
identity and deterministic order.

Types are registered on first use: a header or struct class the first
time a program meets it (through `headers`, `metadata`, a parameter, a
local or a lookahead), depth first so that a struct's field types precede
it; an `Enum` the same way. Errors are declared up front from the `Errors`
classes given, after core.p4's seven.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import get_args, get_origin

from p4blo.edsl.blocks import Block, ExternResult
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
            raise EdslError(f"extern instance {name!r} is not listed in externs=[...]")
        return core

    def declare_errors(self, errors: type[Errors] | Sequence[type[Errors]]) -> None:
        """Register user errors before any block body is assembled."""
        classes = [errors] if isinstance(errors, type) else errors
        for errors in classes:
            if not (isinstance(errors, type) and issubclass(errors, Errors)):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise EdslError(f"errors are Errors classes, got {errors!r}")
            if errors is CoreErrors:
                continue
            for member in errors.__members__:
                with provenance():
                    self.core.error(member)

    def declare_externs(self, externs: Sequence[Extern]) -> None:
        for instance in externs:
            self.extern(instance)

    def finish(self) -> pb.Program:
        """Return declarations after checking all deferred extern calls."""
        if self.pending:
            result = self.pending[0]
            where = f" (defined at {result.location})" if result.location else ""
            raise EdslError(
                f"the result of {result.method}(...) was never assigned{where}", location=None
            )
        with provenance():
            return self.core.build()


__all__ = ["Build"]
