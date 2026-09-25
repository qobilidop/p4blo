# pyright: strict
"""Architecture-free collections of typed block definitions.

Compiling a library records block bodies and their transitive declarations.
It does not choose the program's H/M roots, export roles or packet pipeline;
an architecture makes those choices when it assembles a complete IR program.
The result is an authoring artifact, not a whole-program validity certificate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from p4blo.edsl._build import Build
from p4blo.edsl.blocks import Block, Control, Deparser, Parser
from p4blo.edsl.errors import EdslError
from p4blo.edsl.externs import Extern
from p4blo.edsl.values import Errors
from p4blo.v0 import p4blo_pb2 as pb


def _is_block_class(value: object) -> bool:
    return isinstance(value, type) and issubclass(value, (Parser, Control, Deparser))


@dataclass(frozen=True)
class CompiledLibrary:
    """Recorded blocks and declarations, without architecture choices."""

    blocks: tuple[pb.Block, ...]
    header_types: tuple[pb.HeaderType, ...]
    struct_types: tuple[pb.StructType, ...]
    enum_types: tuple[pb.EnumType, ...]
    extern_types: tuple[pb.ExternType, ...]
    extern_instances: tuple[pb.ExternInstance, ...]
    errors: tuple[str, ...]


class BlockLibrary:
    """Ordered block definitions with shared extern instances and errors.

    Every call to `compile()` starts a fresh context. Sub-blocks reached by
    calls are included once, ahead of their callers. No architecture is
    selected here; loaders supply extern implementations separately.
    """

    def __init__(
        self,
        *blocks: type[Block],
        externs: Sequence[Extern] = (),
        errors: type[Errors] | Sequence[type[Errors]] = (),
    ) -> None:
        if not blocks:
            raise EdslError("a BlockLibrary needs at least one block")
        seen: set[type[Block]] = set()
        for block in blocks:
            if not _is_block_class(block):
                raise EdslError(
                    "a BlockLibrary member must be a Parser, Control or "
                    f"Deparser class, got {block!r}"
                )
            if block in seen:
                raise EdslError(f"block {block.__ir_name__!r} is listed twice")
            seen.add(block)
        self.blocks = blocks
        self.externs = tuple(externs)
        self.errors = (errors,) if isinstance(errors, type) else tuple(errors)

    def compile(self) -> CompiledLibrary:
        """Record these blocks and their dependencies, with no exports."""
        build = Build("block_library")
        build.declare_errors(self.errors)
        build.declare_externs(self.externs)
        for block in self.blocks:
            build.block(block)
        fragment = build.finish()
        return CompiledLibrary(
            blocks=tuple(fragment.blocks),
            header_types=tuple(fragment.header_types),
            struct_types=tuple(fragment.struct_types),
            enum_types=tuple(fragment.enum_types),
            extern_types=tuple(fragment.extern_types),
            extern_instances=tuple(fragment.extern_instances),
            errors=tuple(fragment.errors),
        )


__all__ = ["BlockLibrary", "CompiledLibrary"]
