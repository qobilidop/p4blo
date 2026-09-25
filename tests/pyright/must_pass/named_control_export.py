"""A named control export builds without packet pipeline blocks."""

from __future__ import annotations

from p4blo.edsl import Control, Program, Struct


class Headers(Struct):
    pass


class Metadata(Struct):
    pass


class Policy(Control[Headers, Metadata]):
    pass


program = Program(
    "named_control", headers=Headers, metadata=Metadata, exports={"policy": Policy}
)
