"""Reusable codec lvalue fixtures and independent expectations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from google.protobuf import json_format

from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.codec_expr import Expression, expressions, node, var

Kind = Literal["lvalue", "arg"]


@dataclass(frozen=True)
class Case:
    kind: Kind
    wire: dict[str, object]
    value: dict[str, object]


def lvalues() -> list[Expression]:
    # The fixture container is shared, not the production Expr/LValue decoder.
    base, index = var("array"), var("index")
    return [
        var(""),
        var('quoted"\\\n名字'),
        node("member", base=var("header"), field=""),
        node("member", base=var("header"), field="field"),
        node("next", stack=var("stack")),
        node("next", stack=node("member", base=var("packet"), field="stack")),
        node("index", base=base, index=index),
        node(
            "index",
            base=base,
            index=Expression(
                {"literal": {"bits": {"value": "0"}}},
                {"tag": "literal", "value": {"tag": "bits", "width": 0, "value": "0"}},
            ),
        ),
        node("index", base=base, index=expressions()[3]),
        node(
            "index",
            base=node("member", base=var("packet"), field="stack"),
            index=node("binary", op="BINARY_OP_SUB", left=var("left"), right=var("right")),
        ),
        node(
            "member",
            base=node("index", base=node("next", stack=var("stack")), index=index),
            field="field",
        ),
        node("index", base=base, index=node("slice", operand=var("bits"), hi=1, lo=2)),
        node(
            "index",
            base=base,
            index=Expression(
                {"lookahead": {"type": {"bits": 2**32 - 1}}},
                {"tag": "lookahead", "type": {"tag": "bits", "width": 2**32 - 1}},
            ),
        ),
        node("next", stack=node("next", stack=var(""))),
        node(
            "index",
            base=node("member", base=var("left"), field="base_field"),
            index=node("member", base=var("right"), field="index_field"),
        ),
        node(
            "member",
            base=node(
                "index", base=base, index=node("unary", op="UNARY_OP_NOT", operand=var("condition"))
            ),
            field="y",
        ),
    ]


def cases() -> list[Case]:
    result = [Case("lvalue", x.wire, x.value) for x in lvalues()]
    result += [
        Case("arg", {"lvalue": x.wire}, {"tag": "lvalue", "value": x.value}) for x in lvalues()
    ]
    expr = expressions()
    result += [
        Case("arg", {"expr": x.wire}, {"tag": "expr", "value": x.value})
        for x in [var("array"), expr[0], expr[2], expr[3], expr[5], expr[12], expr[38]]
    ]
    return result


def malformed() -> list[tuple[Kind, object, str]]:
    return [
        ("lvalue", None, "leaf: expected an object"),
        ("lvalue", [], "leaf: expected an object"),
        ("lvalue", {}, "leaf: no kind set"),
        ("lvalue", {"annotation": {}}, "leaf: no kind set"),
        ("lvalue", {"var": None}, "leaf: no kind set"),
        ("lvalue", {"member": {}, "var": 1}, "leaf: more than one kind set: [var, member]"),
        ("lvalue", {"next": {"stack": {"var": 1}}}, "leaf.next.stack.var: expected a string"),
        ("lvalue", {"next": 1}, "leaf.next: expected an object"),
        ("lvalue", {"next": {}}, "leaf.next.stack: no kind set"),
        ("lvalue", {"next": {"stack": None}}, "leaf.next.stack: no kind set"),
        ("lvalue", {"member": {"base": None, "field": 1}}, "leaf.member.base: no kind set"),
        (
            "lvalue",
            {"member": {"base": {"var": "x"}, "field": 1}},
            "leaf.member.field: expected a string",
        ),
        ("lvalue", {"index": {"base": {}, "index": {}}}, "leaf.index.base: no kind set"),
        ("lvalue", {"index": {"base": {"var": "x"}}}, "leaf.index.index: no kind set"),
        (
            "lvalue",
            {"index": {"base": {"var": "x"}, "index": {"lookahead": {"type": {"bits": 2**32}}}}},
            "leaf.index.index.lookahead.type.bits: 4294967296 does not fit in uint32",
        ),
        (
            "lvalue",
            {"index": {"base": {"var": "x"}, "index": {"literal": {"bits": {}}}}},
            "leaf.index.index.literal.bits.value: expected a decimal number, got an empty string",
        ),
        ("arg", 1, "leaf: expected an object"),
        ("arg", {}, "leaf: no kind set"),
        ("arg", {"expr": None}, "leaf: no kind set"),
        ("arg", {"expr": {}, "lvalue": {}}, "leaf: more than one kind set: [expr, lvalue]"),
        ("arg", {"expr": {}}, "leaf.expr: no kind set"),
        ("arg", {"lvalue": {}}, "leaf.lvalue: no kind set"),
        ("arg", {"lvalue": {"next": {}}}, "leaf.lvalue.next.stack: no kind set"),
        ("arg", {"expr": {"binary": {"left": {}}}}, "leaf.expr.binary.op: unspecified"),
    ]


def normalized() -> list[tuple[Kind, object, Expression]]:
    leaf = var("x")
    return [
        ("lvalue", {"var": "x", "annotation": False}, leaf),
        ("lvalue", {"var": "x", "member": None}, leaf),
        (
            "lvalue",
            {"member": {"base": {"var": "x"}, "field": None}},
            node("member", base=leaf, field=""),
        ),
        (
            "lvalue",
            {
                "index": {
                    "base": {"var": "x"},
                    "index": {"literal": {"bits": {"width": "0008", "value": "0007"}}},
                }
            },
            node(
                "index",
                base=leaf,
                index=Expression(
                    {"literal": {"bits": {"width": 8, "value": "7"}}},
                    {"tag": "literal", "value": {"tag": "bits", "width": 8, "value": "7"}},
                ),
            ),
        ),
        (
            "arg",
            {"expr": None, "lvalue": {"var": "x"}},
            Expression({"lvalue": leaf.wire}, {"tag": "lvalue", "value": leaf.value}),
        ),
        (
            "arg",
            {"lvalue": None, "expr": {"var": "x"}},
            Expression({"expr": leaf.wire}, {"tag": "expr", "value": leaf.value}),
        ),
    ]


def protobuf_value(kind: Kind, wire: dict[str, object]) -> tuple[pb.LValue | pb.Arg, object]:
    """Public Python codec, with no semantic validator rejecting invalid syntax."""
    program = apb.BlockAssembly()
    statement = program.blocks.add().body.add()
    if kind == "lvalue":
        value = json_format.ParseDict(wire, pb.LValue())
        statement.assign.target.CopyFrom(value)
        recovered = (
            arch_wire.load_json(arch_wire.dump_json(program)).blocks[0].body[0].assign.target
        )
    else:
        value = json_format.ParseDict(wire, pb.Arg())
        statement.call_action.args.add().CopyFrom(value)
        recovered = (
            arch_wire.load_json(arch_wire.dump_json(program)).blocks[0].body[0].call_action.args[0]
        )
    assert value == recovered
    return recovered, json_format.MessageToDict(value, preserving_proto_field_name=True)
