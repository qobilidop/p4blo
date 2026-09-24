"""Host-entry wire observations, separate from installation and packet execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo.v0 import p4blo_pb2 as pb
from tests import test_codec_tables as table
from tests.test_codec_expr import Expression
from tests.test_codec_leaves import EntriesCodecKind, assert_leaf, key_leaves, leaves, same_json


@dataclass(frozen=True)
class EntriesCase(Expression):
    kind: EntriesCodecKind


KINDS: list[EntriesCodecKind] = ["table_entries", "entries"]


def table_entries(
    block: str = "",
    name: str = "",
    entries: list[Expression] | None = None,
    default: Expression | None = None,
) -> EntriesCase:
    entries = [] if entries is None else entries
    wire: dict[str, object] = {}
    if block:
        wire["block"] = block
    if name:
        wire["table"] = name
    if entries:
        wire["entries"] = [e.wire for e in entries]
    if default is not None:
        wire["default_action"] = default.wire
    return EntriesCase(
        wire,
        {
            "block": block,
            "table": name,
            "entries": [e.value for e in entries],
            "default_action": None if default is None else default.value,
        },
        "table_entries",
    )


def entries(tables: list[Expression] | None = None) -> EntriesCase:
    tables = [] if tables is None else tables
    return EntriesCase(
        {"tables": [t.wire for t in tables]} if tables else {},
        {"tables": [t.value for t in tables]},
        "entries",
    )


def cases() -> list[EntriesCase]:
    keys = [Expression(k.wire, k.value) for _, k in key_leaves()]
    literals = [Expression(x.wire, x.value) for x in leaves() if x.kind == "literal"]
    call = table.call("Unresolved", literals)
    body: list[Expression] = [
        table.entry(),
        table.entry(keys, call, 2**32 - 1),
        table.entry(keys[::-1], table.call("Other"), 7),
    ]
    records = [
        table_entries(),
        table_entries("BlockOnly"),
        table_entries(name="TableOnly"),
        table_entries(default=table.call()),
        table_entries(default=call),
        table_entries("left", "right", body, call),
        table_entries("right", "left", body[::-1], table.call()),
    ]
    return [
        *records,
        entries(),
        entries([records[0]]),
        entries(list(records)),
        entries(list(reversed(records))),
    ]


def malformed() -> list[tuple[EntriesCodecKind, object, str]]:
    result: list[tuple[EntriesCodecKind, object, str]] = []
    for kind in KINDS:
        for bad in (None, [], False, 0, "object"):
            result.append((kind, bad, "leaf: expected an object"))
    for field in ["block", "table"]:
        result.append(("table_entries", {field: False}, f"leaf.{field}: expected a string"))
    for kind, field, good in [
        ("table_entries", "entries", {"action": {}}),
        ("entries", "tables", {}),
    ]:
        result.append((kind, {field: False}, f"leaf.{field}: expected an array"))
        result.append((kind, {field: [good, None]}, f"leaf.{field}[1]: expected an object"))
    result.append(
        ("table_entries", {"default_action": False}, "leaf.default_action: expected an object")
    )
    for first, second, what in [
        ("block", "table", "string"),
        ("table", "entries", "string"),
        ("entries", "default_action", "array"),
    ]:
        result.append(
            (
                "table_entries",
                {first: False, second: False},
                f"leaf.{first}: expected an {what}"
                if what == "array"
                else f"leaf.{first}: expected a {what}",
            )
        )
    for member, wire, error in table.malformed():
        # Bounded selected leaf errors, not a second copy of the entire table matrix.
        if member == "entry" and ("4294967296" in error or wire == {"action": False}):
            result.append(
                (
                    "table_entries",
                    {"entries": [{"action": {}}, wire]},
                    error.replace("leaf", "leaf.entries[1]", 1),
                )
            )
        if member == "action_call" and "4294967296" in error:
            result.append(
                (
                    "table_entries",
                    {"default_action": wire},
                    error.replace("leaf", "leaf.default_action", 1),
                )
            )
    selected = list(result)
    for kind, wire, error in selected:
        if kind == "table_entries" and isinstance(wire, dict):
            result.append(
                ("entries", {"tables": [{}, wire]}, error.replace("leaf", "leaf.tables[1]", 1))
            )
    return result


def normalized() -> list[tuple[EntriesCodecKind, object, EntriesCase]]:
    result: list[tuple[EntriesCodecKind, object, EntriesCase]] = [
        ("table_entries", {"unknown_field": False}, table_entries()),
        ("entries", {"unknown_field": False}, entries()),
        ("table_entries", {"default_action": None}, table_entries()),
        ("table_entries", {"entries": [{}]}, table_entries(entries=[table.entry()])),
        ("entries", {"tables": [{"default_action": None}]}, entries([table_entries()])),
        ("entries", {"tables": [{"defaultAction": {}}]}, entries([table_entries()])),
    ]
    for field in ["block", "table", "entries"]:
        for empty in (None, [] if field == "entries" else ""):
            result.append(("table_entries", {field: empty}, table_entries()))
    for empty in (None, []):
        result.append(("entries", {"tables": empty}, entries()))
    return result


def requests() -> list[tuple[dict[str, object], dict[str, object]]]:
    rows: list[tuple[dict[str, object], dict[str, object]]] = [
        ({"kind": c.kind, "wire": c.wire}, {"value": c.value, "encoded": c.wire}) for c in cases()
    ]
    for k, w, e in malformed():
        rows.append(({"kind": k, "wire": w}, {"error": e}))
    for k, w, c in normalized():
        rows.append(({"kind": k, "wire": w}, {"value": c.value, "encoded": c.wire}))
    return rows


def protobuf_value(kind: EntriesCodecKind, wire: dict[str, object]) -> tuple[Message, object]:
    wrapper = wire if kind == "entries" else {"tables": [wire]}
    parsed = json_format.ParseDict(wrapper, pb.Entries())
    recovered = json_format.Parse(
        json_format.MessageToJson(parsed, preserving_proto_field_name=True), pb.Entries()
    )
    assert parsed == recovered
    value = recovered if kind == "entries" else recovered.tables[0]
    return value, json_format.MessageToDict(value, preserving_proto_field_name=True)


def test_entries_inventory() -> None:
    rows = requests()
    assert (len(cases()), len(malformed()), len(normalized()), len(rows)) == (11, 36, 14, 61)
    assert rows and len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)


@pytest.mark.parametrize("case", cases())
def test_entries_public_known_answers(case: EntriesCase) -> None:
    _, canonical = protobuf_value(case.kind, case.wire)
    assert same_json(canonical, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_entries_answers(lean_binary: Path, case: EntriesCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    _, canonical = protobuf_value(case.kind, wire)
    assert same_json(canonical, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_entries_errors(
    lean_binary: Path, kind: EntriesCodecKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_entries_defaults(
    lean_binary: Path, kind: EntriesCodecKind, wire: object, case: EntriesCase
) -> None:
    assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})


@pytest.mark.parametrize("kind", KINDS)
def test_entries_unknown_fields_outside_canonical_domain(kind: EntriesCodecKind) -> None:
    with pytest.raises(json_format.ParseError, match="unknown_field"):
        protobuf_value(kind, {"unknown_field": False})


def test_entries_protojson_alias_is_not_shared_wire_contract() -> None:
    _, alias = protobuf_value("entries", {"tables": [{"defaultAction": {}}]})
    assert same_json(alias, {"tables": [{"default_action": {}}]})
