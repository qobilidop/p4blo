"""Installed table entries and the match algorithm.

See docs/semantics.md, "Tables": exact, longest prefix, and largest priority
among ternary matches; const entries first; the default action on a miss.
Tables are block-scoped, so they are addressed by `(block, table)` names.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from p4blo.interp.values import Bits
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


class InstallError(Exception):
    """An entry does not fit its table: wrong arity, width, action, missing
    priority, or a duplicate that would create a tie."""


@dataclass(slots=True)
class Match:
    """The result of a lookup: the action to run and whether an entry hit."""

    action: pb.ActionCall | None
    hit: bool


type TableRef = tuple[str, str]
"""`(block name, table name)`."""


@dataclass(slots=True)
class InstalledEntries:
    """Everything installed in every table of a program.

    Built from the program's const entries, then extended by the host's
    `pb.Entries`. Installation checks every entry against its table and
    raises `InstallError` on a mismatch.
    """

    index: Index
    entries: dict[TableRef, list[pb.Entry]] = field(default_factory=dict)
    default_actions: dict[TableRef, pb.ActionCall | None] = field(default_factory=dict)

    @classmethod
    def build(cls, index: Index, host: pb.Entries | None = None) -> InstalledEntries:
        raise NotImplementedError

    def install(self, table: TableRef, entry: pb.Entry) -> None:
        raise NotImplementedError

    def set_default(self, table: TableRef, action: pb.ActionCall | None) -> None:
        raise NotImplementedError

    def lookup(self, table: TableRef, keys: list[Bits]) -> Match:
        raise NotImplementedError
