"""Tables, their keys and their const entries.

A const entry's key values become patterns so that two entries can be
compared: a ternary table forbids two overlapping entries of one priority,
and any other table forbids two entries with the same keys.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    ACTION_ARGS,
    ENTRY_DUPLICATE,
    ENTRY_PRIORITY,
    ENTRY_RANGE,
    ENTRY_SHAPE,
    KEY_NAME,
    KEY_TYPE,
    PARAM_DIRECTION,
    TABLE_ACTIONS,
    TABLE_KEY_MIX,
    TABLE_LPM_COUNT,
)
from p4blo.validator.names import (
    Scope,
)
from p4blo.validator.typer import Typer
from p4blo.validator.types import (
    describe,
    is_bits,
    parse_decimal,
)


@dataclass(frozen=True)
class ExactPattern:
    value: int | str


@dataclass(frozen=True)
class LpmPattern:
    value: int
    prefix_len: int
    width: int

    @property
    def mask(self) -> int:
        return ((1 << self.prefix_len) - 1) << (self.width - self.prefix_len)


@dataclass(frozen=True)
class TernaryPattern:
    value: int
    mask: int


type KeyPattern = ExactPattern | LpmPattern | TernaryPattern


def patterns_overlap(a: KeyPattern, b: KeyPattern) -> bool:
    """Whether some key value matches both patterns."""
    match a, b:
        case ExactPattern(), ExactPattern():
            return a.value == b.value
        case LpmPattern(), LpmPattern():
            mask = a.mask & b.mask
            return a.value & mask == b.value & mask
        case TernaryPattern(), TernaryPattern():
            mask = a.mask & b.mask
            return a.value & mask == b.value & mask
        case _:
            return False


def patterns_equal(a: KeyPattern, b: KeyPattern) -> bool:
    """Whether two patterns match exactly the same key values."""
    match a, b:
        case LpmPattern(), LpmPattern():
            return a.prefix_len == b.prefix_len and a.value & a.mask == b.value & b.mask
        case TernaryPattern(), TernaryPattern():
            return a.mask == b.mask and a.value & a.mask == b.value & b.mask
        case _:
            return a == b


class TableChecks(Typer):
    """Table keys, action lists, default actions and const entries."""

    def check_table(self, table: pb.Table, scope: Scope, path: str) -> None:
        key_types = self.check_keys(table, scope, path)
        kinds = [k.match_kind for k in table.keys]
        if kinds.count(pb.MATCH_KIND_LPM) > 1:
            self.report(TABLE_LPM_COUNT, "a table has at most one lpm key", f"{path}.keys")
        if pb.MATCH_KIND_LPM in kinds and pb.MATCH_KIND_TERNARY in kinds:
            self.report(TABLE_KEY_MIX, "a table with an lpm key has no ternary key", f"{path}.keys")

        if not table.actions:
            self.report(TABLE_ACTIONS, "table lists no actions", f"{path}.actions")
        listed: set[str] = set()
        for i, name in enumerate(table.actions):
            apath = f"{path}.actions[{i}]"
            if name in listed:
                self.report(TABLE_ACTIONS, f"action {name!r} listed twice", apath)
            listed.add(name)
            action = self.resolve_local(name, scope.names.actions, "action", scope, apath)
            if action is not None and any(p.direction != pb.DIRECTION_NONE for p in action.params):
                self.report(
                    PARAM_DIRECTION,
                    f"action {name!r} is invoked by a table, so its params must be directionless",
                    apath,
                )
        if table.HasField("default_action"):
            self.check_action_call(table.default_action, table, scope, f"{path}.default_action")

        has_ternary = pb.MATCH_KIND_TERNARY in kinds
        patterns: list[list[KeyPattern] | None] = []
        for i, entry in enumerate(table.const_entries):
            epath = f"{path}.const_entries[{i}]"
            patterns.append(self.check_entry(entry, table, key_types, has_ternary, scope, epath))
        for j, b in enumerate(patterns):
            if b is None:
                continue
            for i, a in enumerate(patterns[:j]):
                if a is None:
                    continue
                epath = f"{path}.const_entries[{j}]"
                if has_ternary:
                    same_priority = (
                        table.const_entries[i].priority == table.const_entries[j].priority
                    )
                    overlap = all(patterns_overlap(x, y) for x, y in zip(a, b, strict=True))
                    if same_priority and overlap:
                        self.report(
                            ENTRY_PRIORITY,
                            f"entries {i} and {j} overlap with the same priority",
                            epath,
                        )
                elif all(patterns_equal(x, y) for x, y in zip(a, b, strict=True)):
                    self.report(ENTRY_DUPLICATE, f"entries {i} and {j} have the same keys", epath)

    def check_keys(self, table: pb.Table, scope: Scope, path: str) -> list[pb.Type | None]:
        names: set[str] = set()
        key_types: list[pb.Type | None] = []
        for i, key in enumerate(table.keys):
            kpath = f"{path}.keys[{i}]"
            name = ir.key_name(key)
            if name is not None:
                if name in names:
                    self.report(KEY_NAME, f"key name {name!r} used twice", f"{kpath}.name")
                names.add(name)
            t = self.type_of(key.expr, scope, f"{kpath}.expr")
            match key.match_kind:
                case pb.MATCH_KIND_EXACT | pb.MATCH_KIND_LPM | pb.MATCH_KIND_TERNARY:
                    # Table keys are bits only; the frontend casts a boolean or
                    # enum key. Select keys may be any scalar.
                    if t is not None and not is_bits(t):
                        self.report(
                            KEY_TYPE,
                            f"{pb.MatchKind.Name(key.match_kind)} key must be bits, "
                            f"got {describe(t)}",
                            kpath,
                        )
                        t = None
                case _:
                    self.report(KEY_TYPE, "match kind is unspecified", f"{kpath}.match_kind")
                    t = None
            key_types.append(t)
        return key_types

    def check_action_call(
        self, call: pb.ActionCall, table: pb.Table, scope: Scope, path: str
    ) -> None:
        """An action call from a table: default action or entry."""
        action = self.resolve_local(
            call.action, scope.names.actions, "action", scope, f"{path}.action"
        )
        if action is None:
            return
        if call.action not in table.actions:
            self.report(
                TABLE_ACTIONS,
                f"action {call.action!r} is not in the table's action list",
                f"{path}.action",
            )
        self.check_literal_args(call.args, action.params, f"{path}.args", ACTION_ARGS)

    def check_entry(
        self,
        entry: pb.Entry,
        table: pb.Table,
        key_types: Sequence[pb.Type | None],
        has_ternary: bool,
        scope: Scope,
        path: str,
    ) -> list[KeyPattern] | None:
        """One const entry; returns its patterns when every key value parsed."""
        self.check_action_call(entry.action, table, scope, f"{path}.action")
        if not has_ternary and entry.priority != 0:
            self.report(
                ENTRY_PRIORITY, "only a table with a ternary key has priorities", f"{path}.priority"
            )
        if len(entry.keys) != len(table.keys):
            self.report(
                ENTRY_SHAPE,
                f"entry has {len(entry.keys)} values for {len(table.keys)} keys",
                f"{path}.keys",
            )
            return None
        patterns: list[KeyPattern | None] = [
            self.key_pattern(value, key, t, f"{path}.keys[{i}]")
            for i, (value, key, t) in enumerate(zip(entry.keys, table.keys, key_types, strict=True))
        ]
        if any(p is None for p in patterns):
            return None
        return cast(list[KeyPattern], patterns)

    def key_pattern(
        self, value: pb.KeyValue, key: pb.Key, t: pb.Type | None, path: str
    ) -> KeyPattern | None:
        """A key value against its key: the right kind, decimal, in range."""
        kind = value.WhichOneof("kind")
        expected = {
            pb.MATCH_KIND_EXACT: "exact",
            pb.MATCH_KIND_LPM: "lpm",
            pb.MATCH_KIND_TERNARY: "ternary",
        }.get(key.match_kind)
        if kind is None:
            self.report(ENTRY_SHAPE, "key value has no kind", path)
            return None
        if expected is None:
            return None  # the key itself was reported
        if kind != expected:
            self.report(ENTRY_SHAPE, f"key is {expected}, value is {kind}", path)
            return None
        if t is None:
            return None

        def in_width(text: str, what: str, vpath: str) -> int | None:
            number = parse_decimal(text)
            if number is None:
                self.report(ENTRY_SHAPE, f"{what} {text!r} is not decimal", vpath)
            elif number >= 1 << t.bits:
                self.report(ENTRY_RANGE, f"{what} {text} does not fit in {describe(t)}", vpath)
            else:
                return number
            return None

        match kind:
            case "exact":
                number = in_width(value.exact, "value", f"{path}.exact")
                return None if number is None else ExactPattern(number)
            case "lpm":
                number = in_width(value.lpm.value, "value", f"{path}.lpm.value")
                if value.lpm.prefix_len > t.bits:
                    self.report(
                        ENTRY_RANGE,
                        f"prefix length {value.lpm.prefix_len} exceeds {describe(t)}",
                        f"{path}.lpm.prefix_len",
                    )
                    return None
                if number is None:
                    return None
                pattern = LpmPattern(number, value.lpm.prefix_len, t.bits)
                if number & ~pattern.mask:
                    self.report(
                        ENTRY_RANGE, "lpm value has bits below its prefix", f"{path}.lpm.value"
                    )
                    return None
                return pattern
            case _:
                number = in_width(value.ternary.value, "value", f"{path}.ternary.value")
                mask = in_width(value.ternary.mask, "mask", f"{path}.ternary.mask")
                if number is None or mask is None:
                    return None
                if number & ~mask:
                    self.report(
                        ENTRY_RANGE,
                        "ternary value has bits outside its mask",
                        f"{path}.ternary.value",
                    )
                    return None
                return TernaryPattern(number, mask)
