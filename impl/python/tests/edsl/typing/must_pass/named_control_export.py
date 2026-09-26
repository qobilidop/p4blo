"""A named control export builds without packet pipeline blocks."""

from __future__ import annotations

from p4blo import arch
from p4blo.edsl import BlockLibrary, Control, Struct


class Headers(Struct):
    pass


class Metadata(Struct):
    pass


class Policy(Control[Headers, Metadata]):
    pass


library = BlockLibrary(Policy)
fragment = library.compile()
program = arch.assemble(
    library,
    name="named_control",
    headers=Headers,
    metadata=Metadata,
    exports={"policy": Policy},
)
