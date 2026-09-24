"""Action/Block wire-only answers, independent of production codecs/validation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from tests import test_codec_declarations as declaration
from tests import test_codec_parser as parser
from tests import test_codec_stmt as statement
from tests import test_codec_tables as table
from tests.test_codec_expr import Expression
from tests.test_codec_leaves import BlockCodecKind, assert_leaf, leaves, same_json


@dataclass(frozen=True)
class BlockCase(Expression):
    kind: BlockCodecKind


BLOCK_KINDS = ["BLOCK_KIND_PARSER", "BLOCK_KIND_CONTROL", "BLOCK_KIND_DEPARSER"]
KINDS: list[BlockCodecKind] = ["action", "block"]


def record(label: BlockCodecKind, **fields: str | list[Expression]) -> BlockCase:
    wire: dict[str, object] = {}
    value: dict[str, object] = {}
    for key, child in fields.items():
        if isinstance(child, list):
            value[key] = [x.value for x in child]
            if child:
                wire[key] = [x.wire for x in child]
        else:
            value[key] = child
            if child:
                wire[key] = child
    return BlockCase(wire, value, label)


def action(
    name: str = "", params: Sequence[Expression] = (), body: Sequence[Expression] = ()
) -> BlockCase:
    return record("action", name=name, params=list(params), body=list(body))


def block(
    kind: str = "BLOCK_KIND_CONTROL",
    name: str = "",
    params: Sequence[Expression] = (),
    locals: Sequence[Expression] = (),
    actions: Sequence[Expression] = (),
    tables: Sequence[Expression] = (),
    states: Sequence[Expression] = (),
    start: str = "",
    body: Sequence[Expression] = (),
) -> BlockCase:
    return record(
        "block",
        name=name,
        kind=kind,
        params=list(params),
        locals=list(locals),
        actions=list(actions),
        tables=list(tables),
        states=list(states),
        start_state=start,
        body=list(body),
    )


def cases() -> list[BlockCase]:
    types = [Expression(v.wire, v.value) for v in leaves() if v.kind == "type"]
    params = [
        declaration.decl("param", "same" if i % 2 else "", type=t, direction=d)
        for i, t in enumerate(types)
        for d in declaration.DIRECTIONS
    ]
    variables = [declaration.decl("var", "same", type=t) for t in types]
    bodies = statement.cases()
    actions = [action()]
    actions += [
        action(d, params[i::4], bodies[i : i + 3]) for i, d in enumerate(declaration.DIRECTIONS)
    ]
    actions += [action("same", params, bodies), action("same", params[::-1], bodies[:3][::-1])]
    tables = [t for t in table.cases() if t.kind == "table"]
    states = [s for s in parser.cases() if s.kind == "state"]
    result = list(actions)
    for kind in BLOCK_KINDS:
        result += [
            block(kind),
            block(kind, start="Unresolved"),
            block(
                kind, 'quoted"\\\n名字', params, variables, actions, tables, states, "other", bodies
            ),
            block(
                kind,
                "other",
                params[:3][::-1],
                variables[:3][::-1],
                actions[:3][::-1],
                tables[:3][::-1],
                states[:3][::-1],
                'quoted"\\\n名字',
                bodies[:3][::-1],
            ),
        ]
    return result


def malformed() -> list[tuple[BlockCodecKind, object, str]]:
    result: list[tuple[BlockCodecKind, object, str]] = []
    for kind in KINDS:
        for wire in (None, [], False, 0, "object"):
            result.append((kind, wire, "leaf: expected an object"))
        result.append((kind, {"name": False}, "leaf.name: expected a string"))
    result.append(("block", {}, "leaf.kind: unspecified"))
    for bad, error in [
        (None, "unspecified"),
        ("BLOCK_KIND_UNSPECIFIED", "unspecified"),
        ("OTHER_UNSPECIFIED", "unspecified"),
        (0, "expected a string"),
        (1, "expected a string"),
        (False, "expected a string"),
        ({}, "expected a string"),
        ([], "expected a string"),
        ("", 'unknown value ""'),
        ("BAD", 'unknown value "BAD"'),
    ]:
        result.append(("block", {"kind": bad}, f"leaf.kind: {error}"))
    list_fields: list[tuple[BlockCodecKind, list[str]]] = [
        ("action", ["params", "body"]),
        ("block", ["params", "locals", "actions", "tables", "states", "body"]),
    ]
    for kind, fields in list_fields:
        for field in fields:
            prefix: dict[str, object] = {"kind": BLOCK_KINDS[1]} if kind == "block" else {}
            for bad in (False, {}, "array"):
                result.append((kind, {**prefix, field: bad}, f"leaf.{field}: expected an array"))
            result.append((kind, {**prefix, field: [None]}, f"leaf.{field}[0]: expected an object"))
    result += [
        ("action", {"name": False, "params": False}, "leaf.name: expected a string"),
        ("action", {"params": False, "body": False}, "leaf.params: expected an array"),
        (
            "block",
            {"kind": BLOCK_KINDS[1], "start_state": False},
            "leaf.start_state: expected a string",
        ),
    ]
    ordered: list[tuple[str, object, str]] = [
        ("name", False, "expected a string"),
        ("kind", "BAD", 'unknown value "BAD"'),
        ("params", False, "expected an array"),
        ("locals", False, "expected an array"),
        ("actions", False, "expected an array"),
        ("tables", False, "expected an array"),
        ("states", False, "expected an array"),
        ("start_state", False, "expected a string"),
        ("body", False, "expected an array"),
    ]
    for (first, bad, error), (second, bad2, _) in zip(ordered, ordered[1:], strict=False):
        result.append(
            ("block", {"kind": BLOCK_KINDS[1], first: bad, second: bad2}, f"leaf.{first}: {error}")
        )
    valid_param = declaration.decl("param", type=declaration.ZERO, direction="DIRECTION_NONE")
    valid_var = declaration.decl("var", type=declaration.ZERO)
    valid_stmt = statement.cases()[0]
    for member, wire, error in declaration.malformed():
        if member not in {"param", "var"}:
            continue
        assert error.startswith("leaf")
        field, good = ("params", valid_param) if member == "param" else ("locals", valid_var)
        result.append(
            (
                "block",
                {"kind": BLOCK_KINDS[1], field: [good.wire, wire]},
                f"leaf.{field}[1]" + error[4:],
            )
        )
        if member == "param":
            result.append(("action", {"params": [good.wire, wire]}, "leaf.params[1]" + error[4:]))
    for wire, error in statement.malformed():
        assert error.startswith("leaf")
        for kind in KINDS:
            prefix = {"kind": BLOCK_KINDS[1]} if kind == "block" else {}
            result.append(
                (kind, {**prefix, "body": [valid_stmt.wire, wire]}, "leaf.body[1]" + error[4:])
            )
    for member, wire, error in table.malformed():
        if member == "table":
            result.append(
                (
                    "block",
                    {"kind": BLOCK_KINDS[1], "tables": [{}, wire]},
                    "leaf.tables[1]" + error[4:],
                )
            )
    for member, wire, error in parser.malformed():
        if member == "state":
            result.append(
                (
                    "block",
                    {"kind": BLOCK_KINDS[1], "states": [{"transition": {"select": {}}}, wire]},
                    "leaf.states[1]" + error[4:],
                )
            )
    action_errors = [(wire, error) for kind, wire, error in result if kind == "action"]
    for wire, error in action_errors:
        result.append(
            (
                "block",
                {"kind": BLOCK_KINDS[1], "actions": [{}, wire]},
                "leaf.actions[1]" + error[4:],
            )
        )
    return result


def normalized() -> list[tuple[BlockCodecKind, object, BlockCase]]:
    result: list[tuple[BlockCodecKind, object, BlockCase]] = [
        ("action", {"annotation": False}, action()),
        ("action", {"name": None, "params": None, "body": None}, action()),
    ]
    for field in ["name", "params", "body"]:
        empty: object = "" if field == "name" else []
        result.append(("action", {field: empty}, action()))
    for kind in BLOCK_KINDS:
        result.append(("block", {"kind": kind, "annotation": False}, block(kind)))
        for field in [
            "name",
            "params",
            "locals",
            "actions",
            "tables",
            "states",
            "start_state",
            "body",
        ]:
            for empty in (None, "" if field in {"name", "start_state"} else []):
                result.append(("block", {"kind": kind, field: empty}, block(kind)))
    for member, wire, value in declaration.normalized():
        if member == "param":
            result.append(("action", {"params": [wire]}, action(params=[value])))
        if member == "var":
            result.append(
                ("block", {"kind": BLOCK_KINDS[1], "locals": [wire]}, block(locals=[value]))
            )
    for wire, value in statement.normalized():
        result.append(("action", {"body": [wire]}, action(body=[value])))
    for member, wire, value in table.normalized():
        if member == "table":
            result.append(
                ("block", {"kind": BLOCK_KINDS[1], "tables": [wire]}, block(tables=[value]))
            )
    for member, wire, value in parser.normalized():
        if member == "state":
            result.append(
                ("block", {"kind": BLOCK_KINDS[1], "states": [wire]}, block(states=[value]))
            )
    return result


def requests() -> list[tuple[dict[str, object], dict[str, object]]]:
    result: list[tuple[dict[str, object], dict[str, object]]] = [
        ({"kind": c.kind, "wire": c.wire}, {"value": c.value, "encoded": c.wire}) for c in cases()
    ]
    for kind, wire, error in malformed():
        result.append(({"kind": kind, "wire": wire}, {"error": error}))
    for kind, wire, c in normalized():
        result.append(({"kind": kind, "wire": wire}, {"value": c.value, "encoded": c.wire}))
    return result


def protobuf_value(kind: BlockCodecKind, wire: dict[str, object]) -> tuple[Message, object]:
    program = pb.Program()
    wrapper = program.blocks.add()
    value = wrapper if kind == "block" else wrapper.actions.add()
    value.SetInParent()
    json_format.ParseDict(wire, value)
    recovered_block = ir.load_json(ir.dump_json(program)).blocks[0]
    recovered = recovered_block if kind == "block" else recovered_block.actions[0]
    assert recovered == value
    return recovered, json_format.MessageToDict(recovered, preserving_proto_field_name=True)


def test_block_baseline_contract() -> None:
    rows = requests()
    assert (len(cases()), len(malformed()), len(normalized()), len(rows)) == (19, 384, 95, 498)
    assert rows and len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)
    assert {c.value["kind"] for c in cases() if c.kind == "block"} == set(BLOCK_KINDS)


@pytest.mark.parametrize("case", cases())
def test_block_protobuf_known_answers(case: BlockCase) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_block_known_answers(lean_binary: Path, case: BlockCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    recovered, encoded = protobuf_value(case.kind, wire)
    expected, _ = protobuf_value(case.kind, case.wire)
    assert recovered == expected and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_block_exact_errors(
    lean_binary: Path, kind: BlockCodecKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_block_normalization(
    lean_binary: Path, kind: BlockCodecKind, wire: object, case: BlockCase
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    encoded = actual["encoded"]
    assert isinstance(encoded, dict)
    _, canonical = protobuf_value(kind, encoded)
    assert same_json(canonical, case.wire)
