"""Independent parser-syntax codec answers, without parser validity premises."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo.arch.v0 import assembly_pb2 as apb
from tests.codec import test_codec_expr as expr
from tests.codec import test_codec_stmt as statement
from tests.codec.test_codec_expr import Expression
from tests.codec.test_codec_leaves import ParserKind, assert_leaf, leaves, same_json


@dataclass(frozen=True)
class ParserCase(Expression):
    kind: ParserKind


KINDS: list[ParserKind] = ["target", "key_set", "select_case", "transition", "state"]


def target(tag: str, name: str = "") -> ParserCase:
    if tag == "state":
        return ParserCase({"state": name}, {"tag": "state", "name": name}, "target")
    assert tag in {"accept", "reject"}
    return ParserCase({tag: {}}, {"tag": tag}, "target")


def record(kind: ParserKind, **fields: Expression | list[Expression] | str) -> ParserCase:
    wire: dict[str, object] = {}
    value: dict[str, object] = {}
    for key, child in fields.items():
        if isinstance(child, Expression):
            wire[key], value[key] = child.wire, child.value
        elif isinstance(child, list):
            value[key] = [x.value for x in child]
            if child:
                wire[key] = [x.wire for x in child]
        else:
            value[key] = child
            if child:
                wire[key] = child
    return ParserCase(wire, value, kind)


def key_set(tag: str, **fields: Expression) -> ParserCase:
    if tag == "exact":
        value = fields["value"]
        return ParserCase({tag: value.wire}, {"tag": tag, "value": value.value}, "key_set")
    value = record("key_set", **fields)
    return ParserCase({tag: value.wire}, {"tag": tag, **value.value}, "key_set")


def select_case(sets: Sequence[Expression], destination: Expression) -> ParserCase:
    return record("select_case", sets=list(sets), target=destination)


def direct(destination: Expression) -> ParserCase:
    return ParserCase(
        {"direct": destination.wire}, {"tag": "direct", "target": destination.value}, "transition"
    )


def select(keys: Sequence[Expression], cases: Sequence[Expression]) -> ParserCase:
    value = record("transition", keys=list(keys), cases=list(cases))
    return ParserCase({"select": value.wire}, {"tag": "select", **value.value}, "transition")


def state(name: str, body: list[Expression], transition: Expression) -> ParserCase:
    return record("state", name=name, body=body, transition=transition)


def cases() -> list[ParserCase]:
    targets = [target("state", s) for s in ["", "Missing", 'quoted"\\\n名字']]
    targets += [target("accept"), target("reject")]
    literals = [Expression(x.wire, x.value) for x in leaves() if x.kind == "literal"]
    false = Expression({"boolean": False}, {"tag": "boolean", "value": False})
    error = Expression({"error": "mask"}, {"tag": "error", "name": "mask"})
    large = Expression(
        {"bits": {"value": str(10**100 + 7)}},
        {"tag": "bits", "width": 0, "value": str(10**100 + 7)},
    )
    two = Expression({"bits": {"value": "2"}}, {"tag": "bits", "width": 0, "value": "2"})
    sets = [key_set("exact", value=x) for x in literals]
    sets += [
        key_set("masked", value=large, mask=two),
        key_set("masked", value=false, mask=error),
        key_set("masked", value=literals[-1], mask=literals[0]),
        key_set("range", lo=large, hi=two),
        key_set("range", lo=false, hi=error),
        key_set("range", lo=literals[-1], hi=literals[0]),
        key_set("dont_care"),
    ]
    select_cases = [
        select_case([], targets[3]),
        select_case([sets[0], sets[-1], sets[-3]], targets[0]),
        select_case([sets[-5]], targets[4]),
        select_case(sets, targets[1]),
    ]
    transitions = [direct(t) for t in targets]
    transitions += [
        select([], []),
        select([], select_cases[:3]),
        select(expr.expressions(), select_cases),
        select([expr.var("same"), expr.var("same")], []),
    ]
    states = [
        state("", [], transitions[3]),
        state("", [], transitions[5]),
        state("Missing", statement.cases(), transitions[-2]),
        state('quoted"\\\n名字', list(reversed(statement.cases()[:3])), transitions[4]),
        state(
            "cycle",
            [statement.stmt("call_block", block="cycle", args=[])],
            direct(target("state", "cycle")),
        ),
    ]
    return targets + sets + select_cases + transitions + states


def malformed() -> list[tuple[ParserKind, object, str]]:
    result: list[tuple[ParserKind, object, str]] = []
    for kind in KINDS:
        for wire in [None, [], False, 0, "object"]:
            result.append((kind, wire, "leaf: expected an object"))
    oneofs: list[tuple[ParserKind, list[str]]] = [
        ("target", ["state", "accept", "reject"]),
        ("key_set", ["exact", "masked", "range", "dont_care"]),
        ("transition", ["direct", "select"]),
    ]
    for kind, alternatives in oneofs:
        for wire in [{}, {"annotation": True}, *[{k: None} for k in alternatives]]:
            result.append((kind, wire, "leaf: no kind set"))
    result += [
        (
            "target",
            {"reject": False, "state": False},
            "leaf: more than one kind set: [state, reject]",
        ),
        ("target", {"reject": {}, "accept": {}}, "leaf: more than one kind set: [accept, reject]"),
        ("target", {"state": False}, "leaf.state: expected a string"),
        ("target", {"accept": False}, "leaf.accept: expected an object"),
        ("target", {"reject": []}, "leaf.reject: expected an object"),
        ("key_set", {"range": {}, "exact": {}}, "leaf: more than one kind set: [exact, range]"),
        ("key_set", {"dont_care": 0}, "leaf.dont_care: expected an object"),
        ("key_set", {"exact": {}}, "leaf.exact: no kind set"),
        (
            "key_set",
            {"exact": {"bits": {}}},
            "leaf.exact.bits.value: expected a decimal number, got an empty string",
        ),
        ("key_set", {"masked": False}, "leaf.masked: expected an object"),
        ("key_set", {"masked": {"mask": False}}, "leaf.masked.value: no kind set"),
        ("key_set", {"range": {"hi": False}}, "leaf.range.lo: no kind set"),
        (
            "key_set",
            {"masked": {"value": {"error": ""}, "mask": {}}},
            "leaf.masked.mask: no kind set",
        ),
        (
            "key_set",
            {"range": {"lo": {"error": ""}, "hi": False}},
            "leaf.range.hi: expected an object",
        ),
        (
            "transition",
            {"select": {}, "direct": False},
            "leaf: more than one kind set: [direct, select]",
        ),
        ("transition", {"direct": False}, "leaf.direct: expected an object"),
        ("transition", {"direct": {}}, "leaf.direct: no kind set"),
        ("transition", {"select": False}, "leaf.select: expected an object"),
        ("select_case", {"sets": False, "target": False}, "leaf.sets: expected an array"),
        ("select_case", {"sets": [{}], "target": False}, "leaf.sets[0]: no kind set"),
        (
            "transition",
            {"select": {"keys": False, "cases": False}},
            "leaf.select.keys: expected an array",
        ),
        (
            "transition",
            {"select": {"keys": [{}], "cases": False}},
            "leaf.select.keys[0]: no kind set",
        ),
        ("transition", {"select": {"cases": False}}, "leaf.select.cases: expected an array"),
        ("transition", {"select": {"cases": [{}]}}, "leaf.select.cases[0].target: no kind set"),
        (
            "state",
            {"name": False, "body": False, "transition": False},
            "leaf.name: expected a string",
        ),
        ("state", {"body": False, "transition": False}, "leaf.body: expected an array"),
        ("state", {"body": [{}], "transition": False}, "leaf.body[0]: no kind set"),
    ]
    required: list[tuple[ParserKind, str]] = [("select_case", "target"), ("state", "transition")]
    for kind, field in required:
        for wire in [{}, {field: None}, {field: {}}, {field: False}]:
            message = "expected an object" if wire.get(field) is False else "no kind set"
            result.append((kind, wire, f"leaf.{field}: {message}"))
    result += [
        ("transition", {"select": {"cases": [None]}}, "leaf.select.cases[0]: expected an object"),
        (
            "transition",
            {"select": {"cases": [{"target": {"accept": {}}}, None]}},
            "leaf.select.cases[1]: expected an object",
        ),
        ("key_set", {"masked": {"value": None, "mask": False}}, "leaf.masked.value: no kind set"),
        (
            "key_set",
            {"masked": {"value": {"error": ""}, "mask": None}},
            "leaf.masked.mask: no kind set",
        ),
        ("key_set", {"range": {"lo": {"error": ""}, "hi": None}}, "leaf.range.hi: no kind set"),
    ]
    good = {"boolean": False}
    overflow = {"bits": {"width": 2**32, "value": "0"}}
    for tag, fields in [
        ("exact", ["value"]),
        ("masked", ["value", "mask"]),
        ("range", ["lo", "hi"]),
    ]:
        for field in fields:
            payload: object = (
                overflow
                if tag == "exact"
                else {f: overflow if f == field else good for f in fields}
            )
            suffix = "" if tag == "exact" else f".{field}"
            result.append(
                (
                    "key_set",
                    {tag: payload},
                    f"leaf.{tag}{suffix}.bits.width: 4294967296 does not fit in uint32",
                )
            )
    # Reuse independently authored malformed member answers, at a new later index.
    for wire, message in expr.malformed():
        assert message.startswith("leaf")
        result.append(
            (
                "transition",
                {"select": {"keys": [{"var": "first"}, wire]}},
                "leaf.select.keys[1]" + message[4:],
            )
        )
    for wire, suffix in [
        ({"literal": {"bits": {"width": 2**32, "value": "0"}}}, "literal.bits.width"),
        ({"lookahead": {"type": {"bits": 2**32}}}, "lookahead.type.bits"),
        ({"lookahead": {"type": {"stack": {"size": 2**32}}}}, "lookahead.type.stack.size"),
        ({"slice": {"operand": {"var": "x"}, "lo": 2**32}}, "slice.lo"),
    ]:
        result.append(
            (
                "transition",
                {"select": {"keys": [wire]}},
                f"leaf.select.keys[0].{suffix}: 4294967296 does not fit in uint32",
            )
        )
    for wire, message in statement.malformed():
        assert message.startswith("leaf")
        result.append(
            (
                "state",
                {"body": [{"call_action": {}}, wire], "transition": {"select": {}}},
                "leaf.body[1]" + message[4:],
            )
        )
    for bad, suffix in [(None, "expected an object"), ({}, "no kind set")]:
        result.append(
            (
                "select_case",
                {"sets": [{"dont_care": {}}, bad], "target": {"accept": {}}},
                f"leaf.sets[1]: {suffix}",
            )
        )
        result.append(
            (
                "transition",
                {"select": {"cases": [{"target": {"accept": {}}}, {"sets": [{"exact": bad}]}]}},
                f"leaf.select.cases[1].sets[0]{'' if bad is None else '.exact'}: no kind set",
            )
        )
    return result


def normalized() -> list[tuple[ParserKind, object, ParserCase]]:
    accept, reject = target("accept"), target("reject")
    result: list[tuple[ParserKind, object, ParserCase]] = [
        ("target", {"accept": {"annotation": False}, "state": None}, accept),
        ("target", {"accept": None, "reject": {}}, reject),
        ("target", {"state": "", "annotation": False}, target("state", "")),
        ("key_set", {"dont_care": {"annotation": True}}, key_set("dont_care")),
        (
            "key_set",
            {"exact": {"bits": {"width": "0008", "value": "0007"}}},
            key_set(
                "exact",
                value=Expression(
                    {"bits": {"width": 8, "value": "7"}}, {"tag": "bits", "width": 8, "value": "7"}
                ),
            ),
        ),
    ]
    for empty in [None, []]:
        result += [
            ("select_case", {"sets": empty, "target": {"accept": {}}}, select_case([], accept)),
            ("transition", {"select": {"keys": empty, "cases": empty}}, select([], [])),
            (
                "state",
                {"name": None, "body": empty, "transition": {"select": {}}},
                state("", [], select([], [])),
            ),
        ]
    for wire, value in expr.normalized():
        result.append(("transition", {"select": {"keys": [wire]}}, select([value], [])))
    for wire, value in statement.normalized():
        result.append(
            (
                "state",
                {"body": [wire], "transition": {"direct": {"reject": {}}}},
                state("", [value], direct(reject)),
            )
        )
    return result


def requests() -> list[tuple[dict[str, object], dict[str, object]]]:
    result: list[tuple[dict[str, object], dict[str, object]]] = []
    for case in cases():
        result.append(
            ({"kind": case.kind, "wire": case.wire}, {"value": case.value, "encoded": case.wire})
        )
    for kind, wire, error in malformed():
        result.append(({"kind": kind, "wire": wire}, {"error": error}))
    for kind, wire, case in normalized():
        result.append(({"kind": kind, "wire": wire}, {"value": case.value, "encoded": case.wire}))
    return result


def protobuf_value(kind: ParserKind, wire: dict[str, object]) -> tuple[Message, object]:
    program = apb.BlockAssembly()
    state_message = program.blocks.add().states.add()
    match kind:
        case "target":
            value = state_message.transition.direct
        case "key_set":
            value = state_message.transition.select.cases.add().sets.add()
        case "select_case":
            value = state_message.transition.select.cases.add()
        case "transition":
            value = state_message.transition
        case "state":
            value = state_message
    value.SetInParent()
    json_format.ParseDict(wire, value)
    recovered_state = wire.load_json(wire.dump_json(program)).blocks[0].states[0]
    match kind:
        case "target":
            recovered = recovered_state.transition.direct
        case "key_set":
            recovered = recovered_state.transition.select.cases[0].sets[0]
        case "select_case":
            recovered = recovered_state.transition.select.cases[0]
        case "transition":
            recovered = recovered_state.transition
        case "state":
            recovered = recovered_state
    assert recovered == value
    return recovered, json_format.MessageToDict(recovered, preserving_proto_field_name=True)


def test_parser_baseline_contract() -> None:
    rows = requests()
    assert (len(cases()), len(malformed()), len(normalized()), len(rows)) == (51, 155, 25, 231)
    assert len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)
    assert {c.value["tag"] for c in cases() if c.kind == "target"} == {"state", "accept", "reject"}
    assert {c.value["tag"] for c in cases() if c.kind == "key_set"} == {
        "exact",
        "masked",
        "range",
        "dont_care",
    }


@pytest.mark.parametrize("case", cases())
def test_parser_protobuf_known_answers(case: ParserCase) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_parser_known_answers(lean_binary: Path, case: ParserCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    recovered, encoded = protobuf_value(case.kind, wire)
    expected, _ = protobuf_value(case.kind, case.wire)
    assert recovered == expected and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_parser_exact_errors(
    lean_binary: Path, kind: ParserKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_parser_normalization(
    lean_binary: Path, kind: ParserKind, wire: object, case: ParserCase
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    encoded = actual["encoded"]
    assert isinstance(encoded, dict)
    _, canonical = protobuf_value(kind, encoded)
    assert same_json(canonical, case.wire)
