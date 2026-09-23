"""Independent bounded expression codec vectors and exact decoder diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_codec_leaves import assert_leaf, same_json


@dataclass(frozen=True)
class Expression:
    wire: dict[str, object]
    value: dict[str, object]


def var(name: str) -> Expression:
    return Expression({"var": name}, {"tag": "var", "name": name})


def node(tag: str, **fields: Expression | str | int) -> Expression:
    wire: dict[str, object] = {}
    value: dict[str, object] = {"tag": tag}
    for key, child in fields.items():
        if isinstance(child, Expression):
            wire[key], value[key] = child.wire, child.value
        else:
            value[key] = child
            if child != "" and child != 0:
                wire[key] = child
    return Expression({tag: wire}, value)


def expressions() -> list[Expression]:
    left, right = var("left"), var("right")
    condition = Expression(
        {"literal": {"boolean": False}},
        {"tag": "literal", "value": {"tag": "boolean", "value": False}},
    )
    result = [
        var(""),
        var('quoted"\\\n名字'),
        condition,
        Expression(
            {"literal": {"bits": {"value": str(10**100)}}},
            {"tag": "literal", "value": {"tag": "bits", "width": 0, "value": str(10**100)}},
        ),
        node("member", base=left, field=""),
        node("index", base=left, index=right),
        node("last_index", stack=left),
        node("slice", operand=left, hi=0, lo=0),
        node("slice", operand=left, hi=2**32 - 1, lo=7),
        node("slice", operand=left, hi=1, lo=2),
        node("is_valid", header=left),
        node("mux", condition=condition, **{"then": left, "otherwise": right}),
    ]
    for op in ["NOT", "COMPLEMENT", "NEGATE"]:
        result.append(node("unary", op=f"UNARY_OP_{op}", operand=left))
    for op in [
        "ADD",
        "SUB",
        "MUL",
        "ADD_SAT",
        "SUB_SAT",
        "BIT_AND",
        "BIT_OR",
        "BIT_XOR",
        "SHL",
        "SHR",
        "CONCAT",
        "EQ",
        "NE",
        "LT",
        "LE",
        "GT",
        "GE",
        "AND",
        "OR",
    ]:
        result.append(node("binary", op=f"BINARY_OP_{op}", left=left, right=right))
    for type_wire, type_value in [
        ({"bits": 0}, {"tag": "bits", "width": 0}),
        ({"stack": {}}, {"tag": "stack", "header": "", "size": 0}),
    ]:
        result.extend(
            [
                Expression(
                    {"cast": {"to": type_wire, "operand": left.wire}},
                    {"tag": "cast", "to": type_value, "operand": left.value},
                ),
                Expression(
                    {"lookahead": {"type": type_wire}}, {"tag": "lookahead", "type": type_value}
                ),
            ]
        )
    result.append(
        node(
            "mux",
            condition=condition,
            **{
                "then": node(
                    "binary",
                    op="BINARY_OP_SUB",
                    left=node("member", base=left, field="x"),
                    right=node("index", base=right, index=var("i")),
                ),
                "otherwise": node("slice", operand=right, hi=8, lo=3),
            },
        )
    )
    return result


def malformed() -> list[tuple[object, str]]:
    return [
        (None, "leaf: expected an object"),
        ([], "leaf: expected an object"),
        ({}, "leaf: no kind set"),
        ({"annotation": 1}, "leaf: no kind set"),
        ({"var": None}, "leaf: no kind set"),
        (
            {"var": "x", "literal": {"boolean": True}},
            "leaf: more than one kind set: [literal, var]",
        ),
        ({"member": None}, "leaf: no kind set"),
        ({"member": 1}, "leaf.member: expected an object"),
        ({"member": {}}, "leaf.member.base: no kind set"),
        ({"member": {"base": None}}, "leaf.member.base: no kind set"),
        ({"member": {"base": {}, "field": 1}}, "leaf.member.base: no kind set"),
        ({"member": {"base": {"var": "x"}, "field": 1}}, "leaf.member.field: expected a string"),
        ({"index": {"base": {}, "index": {}}}, "leaf.index.base: no kind set"),
        ({"index": {"base": {"var": "x"}}}, "leaf.index.index: no kind set"),
        ({"unary": {"operand": {}}}, "leaf.unary.op: unspecified"),
        (
            {"binary": {"op": "BINARY_OP_SUB", "left": {}, "right": {}}},
            "leaf.binary.left: no kind set",
        ),
        ({"cast": {"operand": {}}}, "leaf.cast.to: no kind set"),
        (
            {"slice": {"operand": {"var": "x"}, "hi": 2**32}},
            "leaf.slice.hi: 4294967296 does not fit in uint32",
        ),
        (
            {"mux": {"condition": {"var": "x"}, "then": {}, "otherwise": {}}},
            "leaf.mux.then: no kind set",
        ),
        (
            {"lookahead": {"type": {"bits": -1}}},
            "leaf.lookahead.type.bits: expected a non-negative integer",
        ),
    ]


def normalized() -> list[tuple[object, Expression]]:
    return [
        ({"var": None, "literal": {"boolean": False}}, expressions()[2]),
        ({"var": "x", "annotation": {"ignored": True}}, var("x")),
        (
            {"member": {"base": {"var": "x"}, "field": None}},
            node("member", base=var("x"), field=""),
        ),
        (
            {"slice": {"operand": {"var": "x"}, "hi": "0008", "lo": None}},
            node("slice", operand=var("x"), hi=8, lo=0),
        ),
        (
            {"literal": {"bits": {"width": "0008", "value": "0007"}}},
            Expression(
                {"literal": {"bits": {"width": 8, "value": "7"}}},
                {"tag": "literal", "value": {"tag": "bits", "width": 8, "value": "7"}},
            ),
        ),
    ]


@pytest.mark.parametrize("expr", expressions())
def test_expr_protobuf_known_answers(expr: Expression) -> None:
    value = json_format.ParseDict(expr.wire, pb.Expr())
    program = pb.Program()
    program.blocks.add().body.add().emit.value.CopyFrom(value)
    recovered = ir.load_json(ir.dump_json(program)).blocks[0].body[0].emit.value
    assert recovered == value
    encoded = json_format.MessageToDict(value, preserving_proto_field_name=True)
    assert same_json(encoded, expr.wire)


@pytest.mark.parametrize("expr", expressions())
def test_lean_agrees_expr_known_answers(lean_binary: Path, expr: Expression) -> None:
    actual = assert_leaf(
        lean_binary, "expr", expr.wire, {"value": expr.value, "encoded": expr.wire}
    )
    # Decode the actual Lean-produced payload using the public Python codec.
    actual_wire = actual["encoded"]
    assert isinstance(actual_wire, dict)
    value = json_format.ParseDict(actual_wire, pb.Expr())
    program = pb.Program()
    program.blocks.add().body.add().emit.value.CopyFrom(value)
    recovered = ir.load_json(ir.dump_json(program)).blocks[0].body[0].emit.value
    assert recovered == json_format.ParseDict(expr.wire, pb.Expr())


@pytest.mark.parametrize("wire,message", malformed())
def test_lean_agrees_expr_exact_errors(lean_binary: Path, wire: object, message: str) -> None:
    assert_leaf(lean_binary, "expr", wire, {"error": message})


@pytest.mark.parametrize("wire,expr", normalized())
def test_lean_agrees_expr_normalization(lean_binary: Path, wire: object, expr: Expression) -> None:
    assert_leaf(lean_binary, "expr", wire, {"value": expr.value, "encoded": expr.wire})
