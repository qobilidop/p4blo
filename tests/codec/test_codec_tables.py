"""Independent table declaration observations: no validation or table execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from tests.codec.test_codec_expr import Expression, expressions, var
from tests.codec.test_codec_leaves import TableKind, assert_leaf, key_leaves, leaves, same_json


@dataclass(frozen=True)
class TableCase(Expression):
    kind: TableKind


def record(
    kind: TableKind,
    **fields: Expression | list[Expression] | list[str] | str | int | bool | None,
) -> TableCase:
    wire: dict[str, object] = {}
    value: dict[str, object] = {}
    for key, child in fields.items():
        if isinstance(child, Expression):
            wire[key], value[key] = child.wire, child.value
        elif isinstance(child, list):
            value[key] = [x.value if isinstance(x, Expression) else x for x in child]
            if child:
                wire[key] = [x.wire if isinstance(x, Expression) else x for x in child]
        else:
            value[key] = child
            if child is not None and child != "" and child != 0:
                wire[key] = child
    return TableCase(wire, value, kind)


MATCH_KINDS = ["MATCH_KIND_EXACT", "MATCH_KIND_LPM", "MATCH_KIND_TERNARY"]
KINDS: list[TableKind] = ["table_key", "action_call", "entry", "table"]


def call(name: str = "", args: list[Expression] | None = None) -> TableCase:
    return record("action_call", action=name, args=[] if args is None else args)


def entry(
    keys: list[Expression] | None = None, action: Expression | None = None, priority: int = 0
) -> TableCase:
    # Entry's nonoptional action always re-encodes a present message, even {}.
    return record(
        "entry",
        keys=[] if keys is None else keys,
        action=call() if action is None else action,
        priority=priority,
    )


def table(
    name: str = "",
    keys: list[Expression] | None = None,
    actions: list[str] | None = None,
    default: Expression | None = None,
    const: bool = False,
    entries: list[Expression] | None = None,
    size: int = 0,
) -> TableCase:
    return record(
        "table",
        name=name,
        keys=[] if keys is None else keys,
        actions=[] if actions is None else actions,
        default_action=default,
        const_default_action=const,
        const_entries=[] if entries is None else entries,
        size=size,
    )


def cases() -> list[TableCase]:
    keys = [
        record(
            "table_key",
            expr=e,
            match_kind=MATCH_KINDS[i % 3],
            name="" if i % 2 else 'quoted"\\\n名字',
        )
        for i, e in enumerate(expressions())
    ]
    literals = [Expression(v.wire, v.value) for v in leaves() if v.kind == "literal"]
    values = [Expression(v.wire, v.value) for _, v in key_leaves()]
    calls = [call(), call("Unresolved", literals), call('quoted"\\\n名字', literals[:3][::-1])]
    entries = [
        entry(),
        entry(values, calls[1], 2**32 - 1),
        entry(list(reversed(values[:3])), calls[2], 17),
    ]
    result = keys + calls + entries
    for const in (False, True):
        for default in (None, call(), calls[1]):
            result.append(table(default=default, const=const))
    result += [
        table(
            "", list(keys), ["last", "", "last", "first"], calls[1], True, list(entries), 2**32 - 1
        ),
        table(
            "unequal",
            [keys[2], keys[0], keys[1]],
            ["Missing"],
            None,
            False,
            [entries[2], entries[0]],
            1,
        ),
    ]
    return result


def malformed() -> list[tuple[TableKind, object, str]]:
    result: list[tuple[TableKind, object, str]] = []
    for kind in KINDS:
        for wire in (None, [], False, "not an object"):
            result.append((kind, wire, "leaf: expected an object"))
    for wire in ({}, {"expr": None}, {"expr": {}}, {"expr": {}, "match_kind": "BAD", "name": 1}):
        result.append(("table_key", wire, "leaf.expr: no kind set"))
    for expr in (False, []):
        result.append(("table_key", {"expr": expr}, "leaf.expr: expected an object"))
    for match, error in [
        (None, "unspecified"),
        ("MATCH_KIND_UNSPECIFIED", "unspecified"),
        (0, "expected a string"),
        (1, "expected a string"),
        (False, "expected a string"),
        ("BAD", 'unknown value "BAD"'),
    ]:
        result.append(
            (
                "table_key",
                {"expr": {"var": "x"}, "match_kind": match, "name": False},
                f"leaf.match_kind: {error}",
            )
        )
    result += [
        ("table_key", {"expr": {"var": "x"}}, "leaf.match_kind: unspecified"),
        (
            "table_key",
            {"expr": {"var": "x"}, "match_kind": "MATCH_KIND_EXACT", "name": False},
            "leaf.name: expected a string",
        ),
        (
            "table_key",
            {"expr": {"lookahead": {"type": {"bits": 2**32}}}},
            "leaf.expr.lookahead.type.bits: 4294967296 does not fit in uint32",
        ),
        (
            "table_key",
            {"expr": {"literal": {"bits": {"width": 2**32, "value": "0"}}}},
            "leaf.expr.literal.bits.width: 4294967296 does not fit in uint32",
        ),
        (
            "table_key",
            {"expr": {"slice": {"operand": {"var": "x"}, "hi": 2**32}}},
            "leaf.expr.slice.hi: 4294967296 does not fit in uint32",
        ),
        (
            "table_key",
            {"expr": {"slice": {"operand": {"var": "x"}, "lo": 2**32}}},
            "leaf.expr.slice.lo: 4294967296 does not fit in uint32",
        ),
    ]
    for kind, key, good, bad, suffix in [
        ("action_call", "args", {"boolean": False}, {}, ": no kind set"),
        ("entry", "keys", {"exact": "0"}, {}, ": no kind set"),
        (
            "table",
            "keys",
            {"expr": {"var": "x"}, "match_kind": "MATCH_KIND_EXACT"},
            {},
            ".expr: no kind set",
        ),
        ("table", "actions", "first", False, ": expected a string"),
        ("table", "const_entries", {}, {"action": False}, ".action: expected an object"),
    ]:
        for wrong in ({}, False, "array"):
            result.append((kind, {key: wrong}, f"leaf.{key}: expected an array"))
        for prefix in ([], [good], [good, good]):
            result.append((kind, {key: [*prefix, bad, None]}, f"leaf.{key}[{len(prefix)}]{suffix}"))
        result.append(
            (
                kind,
                {key: [None]},
                f"leaf.{key}[0]"
                + (": expected a string" if key == "actions" else ": expected an object"),
            )
        )
    numeric_fields: list[tuple[TableKind, str]] = [("entry", "priority"), ("table", "size")]
    for kind, key in numeric_fields:
        for n, error in [
            (2**32, "4294967296 does not fit in uint32"),
            (-1, "expected a non-negative integer"),
            (False, "expected a number"),
            ("-1", 'expected a decimal number, got "-1"'),
        ]:
            result.append((kind, {key: n}, f"leaf.{key}: {error}"))
    result += [
        ("action_call", {"action": False, "args": [{}]}, "leaf.action: expected a string"),
        (
            "action_call",
            {"args": [{"bits": {"width": 2**32, "value": "0"}}]},
            "leaf.args[0].bits.width: 4294967296 does not fit in uint32",
        ),
        ("entry", {"keys": [{}], "action": False, "priority": False}, "leaf.keys[0]: no kind set"),
        ("entry", {"action": False, "priority": False}, "leaf.action: expected an object"),
        (
            "entry",
            {"action": {"args": [{}]}, "priority": False},
            "leaf.action.args[0]: no kind set",
        ),
        (
            "entry",
            {"keys": [{"lpm": {"value": "0", "prefix_len": 2**32}}]},
            "leaf.keys[0].lpm.prefix_len: 4294967296 does not fit in uint32",
        ),
        (
            "entry",
            {"keys": [{"ternary": {"value": "1"}}]},
            "leaf.keys[0].ternary.mask: expected a decimal number, got an empty string",
        ),
        (
            "entry",
            {"keys": [{"exact": "0"}, {"exact": "-1"}]},
            'leaf.keys[1].exact: expected a decimal number, got "-1"',
        ),
        (
            "entry",
            {"action": {"args": [{"bits": {"width": 2**32, "value": "0"}}]}},
            "leaf.action.args[0].bits.width: 4294967296 does not fit in uint32",
        ),
        ("table", {"name": False, "keys": [{}], "actions": False}, "leaf.name: expected a string"),
        ("table", {"keys": [{}], "actions": False}, "leaf.keys[0].expr: no kind set"),
        (
            "table",
            {"actions": [False], "default_action": False},
            "leaf.actions[0]: expected a string",
        ),
        (
            "table",
            {"default_action": False, "const_default_action": 1},
            "leaf.default_action: expected an object",
        ),
        (
            "table",
            {"default_action": {"args": [{}]}, "const_default_action": 1},
            "leaf.default_action.args[0]: no kind set",
        ),
        (
            "table",
            {"const_default_action": "true", "const_entries": [None]},
            "leaf.const_default_action: expected a boolean",
        ),
        ("table", {"const_default_action": 0}, "leaf.const_default_action: expected a boolean"),
        (
            "table",
            {"const_entries": [None], "size": False},
            "leaf.const_entries[0]: expected an object",
        ),
        (
            "table",
            {"keys": [{"expr": {"lookahead": {"type": {"stack": {"size": 2**32}}}}}]},
            "leaf.keys[0].expr.lookahead.type.stack.size: 4294967296 does not fit in uint32",
        ),
        (
            "table",
            {"default_action": {"args": [{"bits": {"width": 2**32, "value": "0"}}]}},
            "leaf.default_action.args[0].bits.width: 4294967296 does not fit in uint32",
        ),
        (
            "table",
            {"const_entries": [{}, {"priority": 2**32}]},
            "leaf.const_entries[1].priority: 4294967296 does not fit in uint32",
        ),
        (
            "table",
            {"const_entries": [{}, {"keys": [{"lpm": {"value": "0", "prefix_len": 2**32}}]}]},
            "leaf.const_entries[1].keys[0].lpm.prefix_len: 4294967296 does not fit in uint32",
        ),
        (
            "table",
            {
                "const_entries": [
                    {},
                    {
                        "action": {
                            "args": [{"boolean": False}, {"bits": {"width": 2**32, "value": "0"}}]
                        }
                    },
                ]
            },
            "leaf.const_entries[1].action.args[1].bits.width: 4294967296 does not fit in uint32",
        ),
    ]
    return result


def normalized() -> list[tuple[TableKind, object, TableCase]]:
    result: list[tuple[TableKind, object, TableCase]] = []
    # Entry{} is not its canonical encoding: actual encoder emits action:{}.
    for wire in ({}, {"action": None}):
        result.append(("entry", wire, entry()))
    result += [
        ("table", {"default_action": None}, table()),
        ("table", {"const_default_action": None}, table()),
        ("table", {"const_default_action": False}, table()),
    ]
    list_fields: list[tuple[TableKind, str, TableCase]] = [
        ("action_call", "args", call()),
        ("entry", "keys", entry()),
        ("table", "keys", table()),
        ("table", "actions", table()),
        ("table", "const_entries", table()),
    ]
    for kind, key, case in list_fields:
        for value in (None, []):
            result.append((kind, {key: value}, case))
    number_fields: list[tuple[TableKind, str, TableCase]] = [
        ("entry", "priority", entry()),
        ("table", "size", table()),
    ]
    for kind, key, case in number_fields:
        for value in (None, 0, "0000"):
            result.append((kind, {key: value}, case))
        result.append(
            (
                kind,
                {key: "004294967295"},
                entry(priority=2**32 - 1) if kind == "entry" else table(size=2**32 - 1),
            )
        )
    string_fields: list[tuple[TableKind, str, TableCase]] = [
        ("action_call", "action", call()),
        ("table", "name", table()),
    ]
    for kind, key, case in string_fields:
        for value in (None, ""):
            result.append((kind, {key: value, "annotation": False}, case))
    result.append(
        (
            "table_key",
            {"expr": {"var": "x"}, "match_kind": "MATCH_KIND_LPM", "name": None},
            record("table_key", expr=var("x"), match_kind="MATCH_KIND_LPM", name=""),
        )
    )
    result.append(
        (
            "entry",
            {"keys": [{"exact": "0007"}]},
            entry([Expression({"exact": "7"}, {"tag": "exact", "value": "7"})]),
        )
    )
    return result


def requests() -> list[tuple[dict[str, object], dict[str, object]]]:
    """Ordered frozen baseline; preserve existing codec inventories and kind labels."""
    result: list[tuple[dict[str, object], dict[str, object]]] = []
    for c in cases():
        result.append(({"kind": c.kind, "wire": c.wire}, {"value": c.value, "encoded": c.wire}))
    for k, w, e in malformed():
        result.append(({"kind": k, "wire": w}, {"error": e}))
    for k, w, c in normalized():
        result.append(({"kind": k, "wire": w}, {"value": c.value, "encoded": c.wire}))
    return result


def protobuf_value(kind: TableKind, wire: dict[str, object]) -> tuple[Message, object]:
    p = pb.Program()
    t = p.blocks.add().tables.add()
    match kind:
        case "table_key":
            value = t.keys.add()
        case "action_call":
            value = t.default_action
        case "entry":
            value = t.const_entries.add()
        case "table":
            value = t
    # Empty messages still have presence; do not let {} erase an optional call.
    value.SetInParent()
    json_format.ParseDict(wire, value)
    rt = ir.load_json(ir.dump_json(p)).blocks[0].tables[0]
    match kind:
        case "table_key":
            recovered = rt.keys[0]
        case "action_call":
            assert rt.HasField("default_action")
            recovered = rt.default_action
        case "entry":
            recovered = rt.const_entries[0]
        case "table":
            recovered = rt
    assert recovered == value
    return recovered, json_format.MessageToDict(recovered, preserving_proto_field_name=True)


def test_table_baseline_contract() -> None:
    rows = requests()
    assert len(rows) == 181
    assert len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)
    assert "key" not in KINDS  # Existing leaf kind continues to mean KeyValue.
    assert {c.value["match_kind"] for c in cases() if c.kind == "table_key"} == set(MATCH_KINDS)


@pytest.mark.parametrize("case", cases())
def test_table_protobuf_known_answers(case: TableCase) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_table_known_answers(lean_binary: Path, case: TableCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    actual_value, encoded = protobuf_value(case.kind, wire)
    expected_value, _ = protobuf_value(case.kind, case.wire)
    assert actual_value == expected_value and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_table_exact_errors(
    lean_binary: Path, kind: TableKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_table_normalization(
    lean_binary: Path, kind: TableKind, wire: object, case: TableCase
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    _, canonical = protobuf_value(kind, wire)
    assert same_json(canonical, case.wire)
