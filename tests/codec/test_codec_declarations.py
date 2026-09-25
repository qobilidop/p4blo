"""Independent nine-declaration wire/constructor/default/error-order anchors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from tests.codec.test_codec_expr import Expression
from tests.codec.test_codec_leaves import DeclarationKind, assert_leaf, leaves, same_json


@dataclass(frozen=True)
class Declaration(Expression):
    kind: DeclarationKind


def decl(
    kind: DeclarationKind, name: str = "", **fields: Expression | list[Expression] | str | None
) -> Declaration:
    """Hand-built wire and complete abstract record, independent of protobuf/Lean."""
    wire: dict[str, object] = {"name": name} if name else {}
    value: dict[str, object] = {"name": name}
    for key, child in fields.items():
        if isinstance(child, Expression):
            wire[key], value[key] = child.wire, child.value
        elif isinstance(child, list):
            value[key] = [x.value for x in child]
            if child:
                wire[key] = [x.wire for x in child]
        else:
            value[key] = child
            if child is not None and child != "":
                wire[key] = child
    return Declaration(wire, value, kind)


def enum(name: str, members: list[str]) -> Declaration:
    wire: dict[str, object] = {"name": name} if name else {}
    if members:
        wire["members"] = members
    return Declaration(wire, {"name": name, "members": members}, "enum_type")


ZERO = Expression({"bits": 0}, {"tag": "bits", "width": 0})
BOOL = Expression({"boolean": {}}, {"tag": "boolean"})
DIRECTIONS = ["DIRECTION_NONE", "DIRECTION_IN", "DIRECTION_OUT", "DIRECTION_INOUT"]
KINDS: list[DeclarationKind] = [
    "field",
    "header_type",
    "struct_type",
    "enum_type",
    "var",
    "param",
    "method",
    "extern_type",
    "extern_instance",
]


def cases() -> list[Declaration]:
    types = [Expression(v.wire, v.value) for v in leaves() if v.kind == "type"]
    literals = [Expression(v.wire, v.value) for v in leaves() if v.kind == "literal"]
    result: list[Declaration] = []
    for kind in ("field", "var"):
        for i, type_ in enumerate(types):
            result.append(decl(kind, "" if i % 2 else 'quoted"\\\n名字', type=type_))
    params = [
        decl("param", "p" if i % 2 else "", type=types[i], direction=direction)
        for i, direction in enumerate(DIRECTIONS)
    ]
    result += params
    # No semantic restrictions: duplicate/empty names, aggregate header fields.
    fields: list[Expression] = [decl("field", "same", type=type_) for type_ in types]
    for kind in ("header_type", "struct_type"):
        result += [decl(kind, fields=[]), decl(kind, "Aggregate", fields=fields)]
    result += [enum("", []), enum("", ["", "same", "same", 'quoted"\\\n名字'])]
    methods = [
        decl("method", params=[], returns=None),
        decl("method", "same", params=list(params), returns=ZERO),
        decl("method", "same", params=list(reversed(params)), returns=types[-1]),
    ]
    result += methods
    # Each optional return Ty family, including unresolved aggregate and maximum.
    result += [decl("method", "returns", params=[], returns=type_) for type_ in types]
    result += [
        decl("extern_type", constructor_params=[], methods=[]),
        decl("extern_type", "Unresolved", constructor_params=list(params), methods=list(methods)),
        decl("extern_instance", extern_type="", args=[]),
        decl("extern_instance", "object", extern_type="MissingType", args=literals),
    ]
    return result


def malformed() -> list[tuple[DeclarationKind, object, str]]:
    result: list[tuple[DeclarationKind, object, str]] = []
    for kind in KINDS:
        for wire in (None, [], False, "not an object"):
            result.append((kind, wire, "leaf: expected an object"))
        result.append((kind, {"name": False}, "leaf.name: expected a string"))
    for kind in ("field", "var", "param"):
        for wire in ({}, {"type": None}, {"type": {}}, {"type": {}, "direction": "BAD"}):
            result.append((kind, wire, "leaf.type: no kind set"))
        for type_ in (False, []):
            result.append((kind, {"type": type_}, "leaf.type: expected an object"))
        for type_ in ({"bits": 2**32}, {"stack": {"size": 2**32}}):
            path = "bits" if "bits" in type_ else "stack.size"
            result.append(
                (kind, {"type": type_}, f"leaf.type.{path}: 4294967296 does not fit in uint32")
            )
        result.append(
            (kind, {"name": 1, "type": {}, "direction": "BAD"}, "leaf.name: expected a string")
        )
    for direction, error in [
        (None, "unspecified"),
        ("DIRECTION_UNSPECIFIED", "unspecified"),
        ("OTHER_UNSPECIFIED", "unspecified"),
        (0, "expected a string"),
        (2, "expected a string"),
        (False, "expected a string"),
        ("BAD", 'unknown value "BAD"'),
    ]:
        result.append(
            ("param", {"type": ZERO.wire, "direction": direction}, f"leaf.direction: {error}")
        )
    result.append(("param", {"type": ZERO.wire}, "leaf.direction: unspecified"))
    # Generic arrays plus exact zero/later first-error positions for every list.
    for kind, key, good, bad, child_error in [
        ("header_type", "fields", {"type": ZERO.wire}, {}, ".type: no kind set"),
        ("struct_type", "fields", {"type": BOOL.wire}, {}, ".type: no kind set"),
        ("enum_type", "members", "first", False, ": expected a string"),
        (
            "method",
            "params",
            {"type": ZERO.wire, "direction": "DIRECTION_OUT"},
            {},
            ".type: no kind set",
        ),
        (
            "extern_type",
            "constructor_params",
            {"type": ZERO.wire, "direction": "DIRECTION_NONE"},
            {},
            ".type: no kind set",
        ),
        ("extern_type", "methods", {}, {"returns": {}}, ".returns: no kind set"),
        ("extern_instance", "args", {"boolean": False}, {}, ": no kind set"),
    ]:
        for wrong in ({}, False, "array"):
            result.append((kind, {key: wrong}, f"leaf.{key}: expected an array"))
        for prefix in ([], [good], [good, good]):
            result.append(
                (kind, {key: [*prefix, bad, None]}, f"leaf.{key}[{len(prefix)}]{child_error}")
            )
        result.append(
            (
                kind,
                {key: [None]},
                f"leaf.{key}[0]"
                + (": expected a string" if kind == "enum_type" else ": expected an object"),
            )
        )
    result += [
        ("method", {"name": 1, "params": False, "returns": {}}, "leaf.name: expected a string"),
        ("method", {"params": False, "returns": {}}, "leaf.params: expected an array"),
        ("method", {"params": [{}], "returns": {}}, "leaf.params[0].type: no kind set"),
        ("method", {"returns": {}}, "leaf.returns: no kind set"),
        ("method", {"returns": False}, "leaf.returns: expected an object"),
        (
            "method",
            {"returns": {"bits": 2**32}},
            "leaf.returns.bits: 4294967296 does not fit in uint32",
        ),
        (
            "extern_type",
            {"name": 0, "constructor_params": False, "methods": False},
            "leaf.name: expected a string",
        ),
        (
            "extern_type",
            {"constructor_params": False, "methods": False},
            "leaf.constructor_params: expected an array",
        ),
        (
            "extern_type",
            {"constructor_params": [{}], "methods": False},
            "leaf.constructor_params[0].type: no kind set",
        ),
        (
            "extern_type",
            {
                "methods": [
                    {},
                    {"params": [{"type": BOOL.wire, "direction": "DIRECTION_INOUT"}, {"type": {}}]},
                ]
            },
            "leaf.methods[1].params[1].type: no kind set",
        ),
        (
            "extern_type",
            {"methods": [{}, {"returns": {"stack": {"size": 2**32}}}]},
            "leaf.methods[1].returns.stack.size: 4294967296 does not fit in uint32",
        ),
        (
            "extern_instance",
            {"name": 0, "extern_type": 1, "args": False},
            "leaf.name: expected a string",
        ),
        (
            "extern_instance",
            {"extern_type": 1, "args": False},
            "leaf.extern_type: expected a string",
        ),
        (
            "extern_instance",
            {"args": [{"bits": {"width": 2**32, "value": "bad"}}]},
            "leaf.args[0].bits.width: 4294967296 does not fit in uint32",
        ),
        (
            "extern_instance",
            {"args": [{"boolean": False}, {"bits": {}}]},
            "leaf.args[1].bits.value: expected a decimal number, got an empty string",
        ),
        (
            "extern_instance",
            {"args": [{"error": ""}, {"bits": {"value": "-1"}}]},
            'leaf.args[1].bits.value: expected a decimal number, got "-1"',
        ),
    ]
    return result


def normalized() -> list[tuple[DeclarationKind, object, Declaration]]:
    result: list[tuple[DeclarationKind, object, Declaration]] = []
    for kind in KINDS:
        if kind in ("field", "var", "param"):
            case = decl(
                kind, type=ZERO, **({"direction": "DIRECTION_NONE"} if kind == "param" else {})
            )
        elif kind in ("header_type", "struct_type"):
            case = decl(kind, fields=[])
        elif kind == "enum_type":
            case = enum("", [])
        elif kind == "method":
            case = decl(kind, params=[], returns=None)
        elif kind == "extern_type":
            case = decl(kind, constructor_params=[], methods=[])
        else:
            case = decl(kind, extern_type="", args=[])
        for name in (None, ""):
            result.append((kind, {**case.wire, "name": name, "annotation": False}, case))
        # Explicit null and empty repeated fields; optional null is not {}.
        lists = {k: v for k, v in case.value.items() if isinstance(v, list)}
        if lists:
            for empty in (None, []):
                wire = {**case.wire, **dict.fromkeys(lists, empty)}
                if kind == "method":
                    wire["returns"] = None
                if kind == "extern_instance":
                    wire["extern_type"] = None
                result.append((kind, wire, case))
    result.extend(
        [
            (
                "extern_instance",
                {"args": [{"bits": {"width": "0008", "value": "00099"}}]},
                decl(
                    "extern_instance",
                    extern_type="",
                    args=[
                        Expression(
                            {"bits": {"width": 8, "value": "99"}},
                            {"tag": "bits", "width": 8, "value": "99"},
                        )
                    ],
                ),
            )
        ]
    )
    return result


def requests() -> list[tuple[dict[str, object], dict[str, object]]]:
    """Frozen ordered baseline source. New campaign controls belong separately."""
    result: list[tuple[dict[str, object], dict[str, object]]] = [
        ({"kind": c.kind, "wire": c.wire}, {"value": c.value, "encoded": c.wire}) for c in cases()
    ]
    for k, w, e in malformed():
        result.append(({"kind": k, "wire": w}, {"error": e}))
    for k, w, c in normalized():
        result.append(({"kind": k, "wire": w}, {"value": c.value, "encoded": c.wire}))
    return result


def protobuf_value(kind: DeclarationKind, wire: dict[str, object]) -> tuple[Message, object]:
    """Canonical public adapter only: no validation, Index or interpreter."""
    program = pb.Program()
    match kind:
        case "field":
            value = program.header_types.add().fields.add()
        case "header_type":
            value = program.header_types.add()
        case "struct_type":
            value = program.struct_types.add()
        case "enum_type":
            value = program.enum_types.add()
        case "var":
            value = program.blocks.add().locals.add()
        case "param":
            value = program.blocks.add().params.add()
        case "method":
            value = program.extern_types.add().methods.add()
        case "extern_type":
            value = program.extern_types.add()
        case "extern_instance":
            value = program.extern_instances.add()
    json_format.ParseDict(wire, value)
    p = ir.load_json(ir.dump_json(program))
    match kind:
        case "field":
            recovered = p.header_types[0].fields[0]
        case "header_type":
            recovered = p.header_types[0]
        case "struct_type":
            recovered = p.struct_types[0]
        case "enum_type":
            recovered = p.enum_types[0]
        case "var":
            recovered = p.blocks[0].locals[0]
        case "param":
            recovered = p.blocks[0].params[0]
        case "method":
            recovered = p.extern_types[0].methods[0]
        case "extern_type":
            recovered = p.extern_types[0]
        case "extern_instance":
            recovered = p.extern_instances[0]
    assert recovered == value
    return recovered, json_format.MessageToDict(recovered, preserving_proto_field_name=True)


def test_declaration_baseline_contract() -> None:
    rows = requests()
    assert len(rows) == 247
    assert len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)
    assert {c.value["direction"] for c in cases() if c.kind == "param"} == set(DIRECTIONS)


@pytest.mark.parametrize("case", cases())
def test_declaration_protobuf_known_answers(case: Declaration) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_declaration_known_answers(lean_binary: Path, case: Declaration) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    actual_wire = actual["encoded"]
    assert isinstance(actual_wire, dict)
    actual_value, encoded = protobuf_value(case.kind, actual_wire)
    expected_value, _ = protobuf_value(case.kind, case.wire)
    assert actual_value == expected_value and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_declaration_exact_errors(
    lean_binary: Path, kind: DeclarationKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_declaration_normalization(
    lean_binary: Path, kind: DeclarationKind, wire: object, case: Declaration
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    encoded = actual["encoded"]
    assert isinstance(encoded, dict)
    _, canonical = protobuf_value(kind, encoded)
    assert same_json(canonical, case.wire)
