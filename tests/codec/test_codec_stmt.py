"""Independent statement constructor/wire/default/error-order codec anchors."""

from __future__ import annotations

from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb
from tests.codec.test_codec_expr import Expression, expressions, node, var
from tests.codec.test_codec_leaves import assert_leaf, same_json


def stmt(tag: str, **fields: Expression | list[Expression] | str | int | None) -> Expression:
    wire: dict[str, object] = {}
    value: dict[str, object] = {"tag": tag}
    for key, child in fields.items():
        if isinstance(child, Expression):
            wire[key], value[key] = child.wire, child.value
        elif isinstance(child, list):
            value[key] = [x.value for x in child]
            if child:
                wire[key] = [x.wire for x in child]
        else:
            value[key] = child
            if child is not None and child != "" and child != 0:
                wire[key] = child
    return Expression({tag: wire}, value)


def arg(tag: str, child: Expression) -> Expression:
    return Expression({tag: child.wire}, {"tag": tag, "value": child.value})


def conditional(condition: Expression, yes: list[Expression], no: list[Expression]) -> Expression:
    return stmt("conditional", condition=condition, **{"then": yes, "otherwise": no})


def cases() -> list[Expression]:
    x, y, c = var("target"), var("value"), expressions()[2]
    args = [arg("expr", y), arg("lvalue", x), arg("expr", expressions()[3])]
    first = stmt("assign", target=x, value=y)
    second = stmt("set_invalid", header=var("header"))
    result = [
        first,
        stmt("assign", target=var(""), value=expressions()[3]),
        conditional(c, [], []),
        conditional(c, [first, second], [stmt("emit", value=var("else"))]),
        stmt("apply", table="", hit=None),
        stmt("apply", table="table", hit=var("hit")),
        stmt("call_action", action="", args=[]),
        stmt("call_action", action="action", args=args),
        stmt("call_block", block="", args=[]),
        stmt("call_block", block="block", args=list(reversed(args))),
        stmt("call_extern", instance="", method="", args=[], result=None),
        stmt("call_extern", instance="extern", method="method", args=args, result=var("result")),
        stmt("set_valid", header=var("header")),
        second,
        stmt("push", stack=var("stack"), count=0),
        stmt("push", stack=var("stack"), count=2**32 - 1),
        stmt("pop", stack=node("member", base=var("packet"), field="stack"), count=0),
        stmt("pop", stack=var("stack"), count=2**32 - 1),
        stmt("extract", target=node("next", stack=var("stack"))),
        stmt("advance", bits=expressions()[3]),
        stmt("verify", condition=c, error=""),
        stmt("verify", condition=node("binary", op="BINARY_OP_NE", left=x, right=y), error="Fault"),
        stmt("emit", value=node("member", base=var("packet"), field="header")),
        stmt("apply", table='quoted"\\\n名字', hit=var("")),
        stmt("call_extern", instance="e", method="", args=[], result=node("next", stack=var(""))),
        stmt("assign", target=node("index", base=x, index=expressions()[9]), value=c),
    ]
    result += [
        conditional(
            var("outer"),
            [conditional(c, [first], [second]), result[11]],
            [conditional(var("inner"), [result[18], result[21]], []), result[15], result[17]],
        ),
        conditional(c, [conditional(c, [], [])], [conditional(c, [], [])]),
    ]
    return result


def malformed() -> list[tuple[object, str]]:
    c = {"var": "condition"}
    emit = {"emit": {"value": {"var": "v"}}}
    return [
        (None, "leaf: expected an object"),
        ([], "leaf: expected an object"),
        ({}, "leaf: no kind set"),
        ({"annotation": {}}, "leaf: no kind set"),
        ({"conditional": None}, "leaf: no kind set"),
        ({"emit": {}, "assign": {}}, "leaf: more than one kind set: [assign, emit]"),
        (
            {"set_invalid": {}, "set_valid": {}},
            "leaf: more than one kind set: [set_valid, set_invalid]",
        ),
        ({"conditional": False}, "leaf.conditional: expected an object"),
        ({"conditional": {}}, "leaf.conditional.condition: no kind set"),
        (
            {"conditional": {"condition": None, "then": False}},
            "leaf.conditional.condition: no kind set",
        ),
        ({"conditional": {"condition": c, "then": {}}}, "leaf.conditional.then: expected an array"),
        (
            {"conditional": {"condition": c, "otherwise": False}},
            "leaf.conditional.otherwise: expected an array",
        ),
        (
            {"conditional": {"condition": c, "then": [None]}},
            "leaf.conditional.then[0]: expected an object",
        ),
        (
            {"conditional": {"condition": c, "then": [{}, None], "otherwise": [None]}},
            "leaf.conditional.then[0]: no kind set",
        ),
        (
            {"conditional": {"condition": c, "then": [emit, {}], "otherwise": False}},
            "leaf.conditional.then[1]: no kind set",
        ),
        (
            {"conditional": {"condition": c, "then": [], "otherwise": [emit, None]}},
            "leaf.conditional.otherwise[1]: expected an object",
        ),
        (
            {
                "conditional": {
                    "condition": c,
                    "then": [{"conditional": {"condition": c, "otherwise": [{}]}}],
                }
            },
            "leaf.conditional.then[0].conditional.otherwise[0]: no kind set",
        ),
        ({"assign": {}}, "leaf.assign.target: no kind set"),
        ({"assign": {"target": None, "value": {}}}, "leaf.assign.target: no kind set"),
        ({"assign": {"target": {"var": "x"}}}, "leaf.assign.value: no kind set"),
        ({"apply": {"table": 0, "hit": {}}}, "leaf.apply.table: expected a string"),
        ({"apply": {"hit": {}}}, "leaf.apply.hit: no kind set"),
        (
            {"call_action": {"action": False, "args": [{}]}},
            "leaf.call_action.action: expected a string",
        ),
        ({"call_action": {"args": False}}, "leaf.call_action.args: expected an array"),
        ({"call_block": {"block": 0, "args": [{}]}}, "leaf.call_block.block: expected a string"),
        (
            {"call_block": {"args": [{"expr": {"var": "x"}}, {}]}},
            "leaf.call_block.args[1]: no kind set",
        ),
        (
            {"call_extern": {"instance": 1, "method": 2, "args": False, "result": {}}},
            "leaf.call_extern.instance: expected a string",
        ),
        (
            {"call_extern": {"method": 2, "args": False, "result": {}}},
            "leaf.call_extern.method: expected a string",
        ),
        (
            {"call_extern": {"args": [{}, None], "result": {}}},
            "leaf.call_extern.args[0]: no kind set",
        ),
        ({"call_extern": {"result": {}}}, "leaf.call_extern.result: no kind set"),
        ({"set_valid": {}}, "leaf.set_valid.header: no kind set"),
        ({"set_invalid": {"header": False}}, "leaf.set_invalid.header: expected an object"),
        ({"push": {"stack": {}, "count": -1}}, "leaf.push.stack: no kind set"),
        (
            {"push": {"stack": {"var": "s"}, "count": -1}},
            "leaf.push.count: expected a non-negative integer",
        ),
        ({"pop": {"stack": {"var": "s"}, "count": False}}, "leaf.pop.count: expected a number"),
        (
            {"push": {"stack": {"var": "s"}, "count": 2**32}},
            "leaf.push.count: 4294967296 does not fit in uint32",
        ),
        (
            {"pop": {"stack": {"var": "s"}, "count": 2**32}},
            "leaf.pop.count: 4294967296 does not fit in uint32",
        ),
        ({"extract": {}}, "leaf.extract.target: no kind set"),
        (
            {"advance": {"bits": {"lookahead": {"type": {"bits": 2**32}}}}},
            "leaf.advance.bits.lookahead.type.bits: 4294967296 does not fit in uint32",
        ),
        ({"verify": {"condition": {}, "error": 3}}, "leaf.verify.condition: no kind set"),
        ({"verify": {"condition": c, "error": 3}}, "leaf.verify.error: expected a string"),
        (
            {"emit": {"value": {"literal": {"bits": {}}}}},
            "leaf.emit.value.literal.bits.value: expected a decimal number, got an empty string",
        ),
    ]


def normalized() -> list[tuple[object, Expression]]:
    c = var("condition")
    return [
        ({"conditional": {"condition": c.wire}}, conditional(c, [], [])),
        (
            {"conditional": {"condition": c.wire, "then": None, "otherwise": None}},
            conditional(c, [], []),
        ),
        (
            {"conditional": {"condition": c.wire, "then": [], "otherwise": []}},
            conditional(c, [], []),
        ),
        ({"apply": {"table": None, "hit": None}}, stmt("apply", table="", hit=None)),
        (
            {"call_extern": {"instance": None, "method": None, "args": None, "result": None}},
            stmt("call_extern", instance="", method="", args=[], result=None),
        ),
        ({"push": {"stack": {"var": "s"}, "count": None}}, stmt("push", stack=var("s"), count=0)),
        ({"pop": {"stack": {"var": "s"}, "count": "0007"}}, stmt("pop", stack=var("s"), count=7)),
        (
            {"set_valid": {"header": {"var": "h"}}, "set_invalid": None, "annotation": False},
            stmt("set_valid", header=var("h")),
        ),
        ({"verify": {"condition": c.wire, "error": None}}, stmt("verify", condition=c, error="")),
    ]


def requests() -> list[tuple[dict[str, object], dict[str, object]]]:
    """The complete ordered source of original transcripts and raw replays."""
    result: list[tuple[dict[str, object], dict[str, object]]] = []
    for case in cases():
        result.append(
            ({"kind": "stmt", "wire": case.wire}, {"value": case.value, "encoded": case.wire})
        )
    for wire, message in malformed():
        result.append(({"kind": "stmt", "wire": wire}, {"error": message}))
    for wire, case in normalized():
        result.append(({"kind": "stmt", "wire": wire}, {"value": case.value, "encoded": case.wire}))
    return result


def protobuf_value(wire: dict[str, object]) -> tuple[pb.Stmt, object]:
    value = json_format.ParseDict(wire, pb.Stmt())
    program = apb.BlockAssembly()
    program.blocks.add().body.add().CopyFrom(value)
    recovered = wire.load_json(wire.dump_json(program)).blocks[0].body[0]
    assert recovered == value
    return recovered, json_format.MessageToDict(value, preserving_proto_field_name=True)


@pytest.mark.parametrize("case", cases())
def test_stmt_protobuf_known_answers(case: Expression) -> None:
    _, encoded = protobuf_value(case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_stmt_known_answers(lean_binary: Path, case: Expression) -> None:
    actual = assert_leaf(
        lean_binary, "stmt", case.wire, {"value": case.value, "encoded": case.wire}
    )
    actual_wire = actual["encoded"]
    assert isinstance(actual_wire, dict)
    actual_value, encoded = protobuf_value(actual_wire)
    expected_value, _ = protobuf_value(case.wire)
    assert actual_value == expected_value and same_json(encoded, case.wire)


@pytest.mark.parametrize("wire,message", malformed())
def test_lean_agrees_stmt_exact_errors(lean_binary: Path, wire: object, message: str) -> None:
    assert_leaf(lean_binary, "stmt", wire, {"error": message})


@pytest.mark.parametrize("wire,expected", normalized())
def test_lean_agrees_stmt_normalization(
    lean_binary: Path, wire: object, expected: Expression
) -> None:
    assert_leaf(lean_binary, "stmt", wire, {"value": expected.value, "encoded": expected.wire})
