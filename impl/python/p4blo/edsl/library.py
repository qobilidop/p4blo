# pyright: strict
"""Architecture-free collections of typed block definitions.

Compiling a library records block bodies and their transitive declarations.
It does not choose the program's H/M roots, export roles or packet pipeline;
architecture support makes those choices separately. The protobuf result
can be checked by the core library validator.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.edsl._build import Build
from p4blo.edsl.blocks import Block, Control, Deparser, Parser
from p4blo.edsl.errors import EdslError
from p4blo.edsl.externs import Extern
from p4blo.edsl.values import Errors
from p4blo.v0 import p4blo_pb2 as pb


def _is_block_class(value: object) -> bool:
    return isinstance(value, type) and issubclass(value, (Parser, Control, Deparser))


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

    def compile(self) -> pb.BlockLibrary:
        """Record these blocks and their dependencies, with no exports."""
        build = Build("block_library")
        build.declare_errors(self.errors)
        build.declare_externs(self.externs)
        for block in self.blocks:
            build.block(block)
        return build.finish()


__all__ = ["BlockLibrary"]
