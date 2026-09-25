# expect: reportArgumentType line 25
"""An export value must be a parser, control or deparser class."""

from __future__ import annotations

from p4blo.edsl import Program, Struct


class Headers(Struct):
    pass


class Metadata(Struct):
    pass


class NotABlock:
    pass


program = Program(
    "bad_export",
    headers=Headers,
    metadata=Metadata,
    exports={"policy": NotABlock},
)
