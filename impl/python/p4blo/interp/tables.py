"""Installed table entries and the match algorithm.

See docs/ir-semantics.md, "Tables": exact, longest prefix, and largest priority
among ternary matches; const entries first; the default action on a miss.
Tables are block-scoped, so they are addressed by `(block, table)` names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from p4blo.interp.api import InterpError
from p4blo.interp.values import Bits
from p4blo.interp.widths import type_of, width_of
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
        """The program's const entries and defaults, then the host's."""
        installed = cls(index)
        for block in index.program.blocks:
            for table in block.tables:
                ref = (block.name, table.name)
                installed.entries[ref] = []
                installed.default_actions[ref] = (
                    table.default_action if table.HasField("default_action") else None
                )
                for entry in table.const_entries:
                    installed.install(ref, entry)
        if host is not None:
            for te in host.tables:
                ref = (te.block, te.table)
                for entry in te.entries:
                    installed.install(ref, entry)
                if te.HasField("default_action"):
                    installed.set_default(ref, te.default_action)
        return installed

    def table(self, ref: TableRef) -> pb.Table:
        block, name = ref
        try:
            return self.index.scopes[block].tables[name]
        except KeyError:
            raise InstallError(f"no table {name!r} in block {block!r}") from None

    def key_widths(self, ref: TableRef) -> list[int]:
        scope = self.index.scopes[ref[0]]
        widths: list[int] = []
        for key in self.table(ref).keys:
            type = type_of(key.expr, self.index, scope)
            if type.WhichOneof("kind") != "bits":
                raise InterpError(f"key {key.name!r} of table {ref[1]!r} is not bits")
            widths.append(width_of(type, self.index))
        return widths

    def install(self, table: TableRef, entry: pb.Entry) -> None:
        """Add an entry after checking it fits the table and ties nothing.

        Ternary tables order by priority, and two entries of equal priority
        whose key sets overlap are rejected. Other tables require priority
        0 and reject an entry whose keys repeat an installed one's.
        """
        decl = self.table(table)
        widths = self.key_widths(table)
        if len(entry.keys) != len(decl.keys):
            raise InstallError(f"table {decl.name!r} has {len(decl.keys)} keys")
        for key, kv, width in zip(decl.keys, entry.keys, widths, strict=True):
            check_key_value(key, kv, width)
        self.check_action(table, entry.action)
        ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in decl.keys)
        if not ternary and entry.priority != 0:
            raise InstallError(f"table {decl.name!r} has no ternary key; priority must be 0")
        for other in self.entries[table]:
            if ternary:
                if other.priority == entry.priority and overlaps(entry, other, widths):
                    raise InstallError(
                        f"table {decl.name!r}: overlapping entries at priority {entry.priority}"
                    )
            elif same_keys(entry, other):
                raise InstallError(f"table {decl.name!r}: duplicate entry")
        self.entries[table].append(entry)

    def set_default(self, table: TableRef, action: pb.ActionCall | None) -> None:
        """Replace a non-const default action; `None` restores the program's
        own, since a host cannot remove a default."""
        decl = self.table(table)
        if decl.const_default_action:
            raise InstallError(f"table {decl.name!r} has a const default action")
        if action is None:
            action = decl.default_action if decl.HasField("default_action") else None
        else:
            self.check_action(table, action)
        self.default_actions[table] = action

    def check_action(self, table: TableRef, call: pb.ActionCall) -> None:
        """The call names one of the table's actions and carries one literal
        of the declared type per directionless parameter. The action is the
        table's block's, by name: two blocks may declare identical tables."""
        decl = self.table(table)
        if call.action not in decl.actions:
            raise InstallError(f"table {decl.name!r} has no action {call.action!r}")
        action = self.index.scopes[table[0]].actions[call.action]
        if any(p.direction != pb.DIRECTION_NONE for p in action.params):
            raise InstallError(f"action {action.name!r} has directional parameters")
        if len(call.args) != len(action.params):
            raise InstallError(f"action {action.name!r} takes {len(action.params)} arguments")
        for param, arg in zip(action.params, call.args, strict=True):
            check_literal(arg, param.type, f"argument for {action.name}.{param.name}")

    def lookup(self, table: TableRef, keys: list[Bits]) -> Match:
        """The entry that matches best, or the default action on a miss."""
        decl = self.table(table)
        if len(keys) != len(decl.keys):
            raise InterpError(f"table {decl.name!r} has {len(decl.keys)} keys")
        ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in decl.keys)
        best: pb.Entry | None = None
        for entry in self.entries[table]:
            if all(key_value_matches(kv, k) for kv, k in zip(entry.keys, keys, strict=True)):
                if best is None or beats(entry, best, ternary):
                    best = entry
        if best is None:
            return Match(self.default_actions[table], False)
        return Match(best.action, True)


# ---------------------------------------------------------------------------
# Entry values
# ---------------------------------------------------------------------------


_DECIMAL = re.compile(r"[0-9]+")


def decimal(text: str, width: int, what: str) -> int:
    """A decimal entry value that fits in `width` bits: digits only, as the
    validator's `parse_decimal` reads const entries, so a host entry and a
    const entry agree on what is decimal."""
    if not _DECIMAL.fullmatch(text):
        raise InstallError(f"{what} {text!r} is not decimal")
    value = int(text)
    if value >= 1 << width:
        raise InstallError(f"{what} {text!r} does not fit in {width} bits")
    return value


KIND_OF_MATCH = {
    pb.MATCH_KIND_EXACT: "exact",
    pb.MATCH_KIND_LPM: "lpm",
    pb.MATCH_KIND_TERNARY: "ternary",
}


def check_key_value(key: pb.Key, kv: pb.KeyValue, width: int) -> None:
    """The value's kind is the key's match kind, it fits the key's width,
    and it is canonical: no set bit outside an LPM prefix or a ternary
    mask."""
    kind = kv.WhichOneof("kind")
    if kind != KIND_OF_MATCH.get(key.match_kind):
        raise InstallError(f"key {key.name!r} wants a {KIND_OF_MATCH.get(key.match_kind)} value")
    match kind:
        case "exact":
            decimal(kv.exact, width, "exact value")
        case "lpm":
            value = decimal(kv.lpm.value, width, "lpm value")
            if kv.lpm.prefix_len > width:
                raise InstallError(f"prefix length {kv.lpm.prefix_len} exceeds width {width}")
            if value & ((1 << (width - kv.lpm.prefix_len)) - 1):
                raise InstallError(f"lpm value {kv.lpm.value!r} has bits outside its prefix")
        case "ternary":
            value = decimal(kv.ternary.value, width, "ternary value")
            mask = decimal(kv.ternary.mask, width, "ternary mask")
            if value & ~mask:
                raise InstallError(f"ternary value {kv.ternary.value!r} has bits outside its mask")


def check_literal(literal: pb.Literal, type: pb.Type, what: str) -> None:
    """`literal` is a constant of `type`: the same kind, and for bits the
    declared width and a decimal value that fits (docs/ir-semantics.md,
    "Entries name their action")."""
    match literal.WhichOneof("value"), type.WhichOneof("kind"):
        case "bits", "bits":
            if literal.bits.width != type.bits:
                raise InstallError(f"{what} is bit<{literal.bits.width}>, not bit<{type.bits}>")
            decimal(literal.bits.value, type.bits, what)
        case ("boolean", "boolean") | ("error", "error"):
            pass
        case "enum_member", "enum_type":
            if literal.enum_member.enum_type != type.enum_type:
                raise InstallError(f"{what} is not an enum {type.enum_type}")
        case _:
            raise InstallError(f"{what} has the wrong type")


def key_value_matches(kv: pb.KeyValue, key: Bits) -> bool:
    """Exact equality, prefix equality, or equality under the mask."""
    match kv.WhichOneof("kind"):
        case "exact":
            return key.value == int(kv.exact)
        case "lpm":
            shift = key.width - kv.lpm.prefix_len
            return (key.value >> shift) == (int(kv.lpm.value) >> shift)
        case "ternary":
            mask = int(kv.ternary.mask)
            return (key.value & mask) == (int(kv.ternary.value) & mask)
        case _:
            raise InterpError("key value has no kind")


def beats(entry: pb.Entry, best: pb.Entry, ternary: bool) -> bool:
    """Whether `entry` wins over `best` when both match: larger priority in
    a ternary table, longer prefix otherwise. Exact tables never tie."""
    if ternary:
        return entry.priority > best.priority
    return prefix_length(entry) > prefix_length(best)


def prefix_length(entry: pb.Entry) -> int:
    return sum(kv.lpm.prefix_len for kv in entry.keys if kv.WhichOneof("kind") == "lpm")


def same_keys(a: pb.Entry, b: pb.Entry) -> bool:
    """Two entries of an exact or LPM table with identical keys: equal
    exact values, and equal prefixes of equal length (values are canonical,
    so the prefix is the value)."""
    for x, y in zip(a.keys, b.keys, strict=True):
        match x.WhichOneof("kind"):
            case "exact":
                if int(x.exact) != int(y.exact):
                    return False
            case "lpm":
                if x.lpm.prefix_len != y.lpm.prefix_len or int(x.lpm.value) != int(y.lpm.value):
                    return False
    return True


def overlaps(a: pb.Entry, b: pb.Entry, widths: list[int]) -> bool:
    """Whether some key value matches both entries: every key overlaps."""
    for x, y, width in zip(a.keys, b.keys, widths, strict=True):
        match x.WhichOneof("kind"):
            case "exact":
                if int(x.exact) != int(y.exact):
                    return False
            case "lpm":
                shift = width - min(x.lpm.prefix_len, y.lpm.prefix_len)
                if (int(x.lpm.value) >> shift) != (int(y.lpm.value) >> shift):
                    return False
            case "ternary":
                mask = int(x.ternary.mask) & int(y.ternary.mask)
                if (int(x.ternary.value) & mask) != (int(y.ternary.value) & mask):
                    return False
    return True
