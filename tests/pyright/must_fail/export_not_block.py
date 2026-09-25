# expect: reportArgumentType line 13
"""A library member must be a parser, control or deparser class."""

from __future__ import annotations

from p4blo.edsl import BlockLibrary


class NotABlock:
    pass


library = BlockLibrary(NotABlock)
