"""Reusable codec program fixtures and independent expectations."""

from __future__ import annotations

import json
from dataclasses import dataclass

from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo.arch import wire as arch_wire
from tests.support import codec_blocks as block
from tests.support import codec_declarations as declaration
from tests.support import codec_stmt as statement
from tests.support import codec_tables as table
from tests.support.codec_expr import Expression
from tests.support.codec_leaves import ProgramCodecKind


@dataclass(frozen=True)
class ProgramCase(Expression):
    kind: ProgramCodecKind


KINDS: list[ProgramCodecKind] = ["export", "program"]


LISTS = [
    "errors",
    "header_types",
    "struct_types",
    "enum_types",
    "extern_types",
    "extern_instances",
    "blocks",
    "exports",
]


STRINGS = ["name", "headers", "metadata"]


ORDER = ["name", *LISTS[:-1], "headers", "metadata", "exports"]


def export(role: str = "", target: str = "") -> ProgramCase:
    wire: dict[str, object] = {k: v for k, v in [("role", role), ("block", target)] if v}
    return ProgramCase(wire, {"role": role, "block": target}, "export")


def program(**fields: str | list[str] | list[Expression]) -> ProgramCase:
    wire: dict[str, object] = {}
    value: dict[str, object] = {}
    assert set(fields) <= set(ORDER)
    for field in ORDER:
        child = fields.get(field, "" if field in STRINGS else [])
        if isinstance(child, str):
            value[field] = child
            if child:
                wire[field] = child
        else:
            value[field] = [x.value if isinstance(x, Expression) else x for x in child]
            if child:
                wire[field] = [x.wire if isinstance(x, Expression) else x for x in child]
    return ProgramCase(wire, value, "program")


def cases() -> list[ProgramCase]:
    declarations = declaration.cases()
    members: dict[str, list[Expression]] = {
        plural: [x for x in declarations if x.kind == singular]
        for plural, singular in [
            ("header_types", "header_type"),
            ("struct_types", "struct_type"),
            ("enum_types", "enum_type"),
            ("extern_types", "extern_type"),
            ("extern_instances", "extern_instance"),
        ]
    }
    exports: list[Expression] = [export(), export("same", "Missing"), export("same", "Other")]
    blocks: list[Expression] = [
        block.block(k, name=n, start="Unresolved")
        for k, n in zip(block.BLOCK_KINDS, ["", "same", "same"], strict=True)
    ]
    fields: dict[str, str | list[str] | list[Expression]] = {
        "name": 'quoted"\\\n名字',
        "errors": ["", "same", "same"],
        **members,
        "blocks": blocks,
        "headers": "HdrOnly",
        "metadata": "MetaOnly",
        "exports": exports,
    }
    result = [
        export(),
        export("", "OnlyBlock"),
        export("OnlyRole", ""),
        export("role-left", "block-right"),
        program(),
        program(**fields),
    ]
    result.append(program(**{k: v[::-1] if isinstance(v, list) else v for k, v in fields.items()}))
    result += [program(**{field: fields[field]}) for field in ORDER]
    # Propagate the existing independent maximum-width/count/slice/table fixtures.
    result.append(
        program(
            blocks=[
                block.block(
                    body=statement.cases()[14:20],
                    tables=[x for x in table.cases() if x.kind == "table"],
                )
            ]
        )
    )
    return result


def malformed() -> list[tuple[ProgramCodecKind, object, str]]:
    result: list[tuple[ProgramCodecKind, object, str]] = []
    for kind in KINDS:
        for wire in (None, [], False, 0, "object"):
            result.append((kind, wire, "leaf: expected an object"))
    string_fields: list[tuple[ProgramCodecKind, list[str]]] = [
        ("export", ["role", "block"]),
        ("program", STRINGS),
    ]
    for kind, fields in string_fields:
        for field in fields:
            result.append((kind, {field: False}, f"leaf.{field}: expected a string"))
    for field in LISTS:
        result.append(("program", {field: False}, f"leaf.{field}: expected an array"))
        empty: object = (
            "" if field == "errors" else {"kind": "BLOCK_KIND_CONTROL"} if field == "blocks" else {}
        )
        what = "a string" if field == "errors" else "an object"
        result.append(("program", {field: [empty, None]}, f"leaf.{field}[1]: expected {what}"))
    result.append(("export", {"role": False, "block": False}, "leaf.role: expected a string"))
    for first, second in zip(ORDER, ORDER[1:], strict=False):
        what = "a string" if first in STRINGS else "an array"
        result.append(("program", {first: False, second: False}, f"leaf.{first}: expected {what}"))
    # Selected inherited bounds: each declaration family plus every numeric family in Block.
    bound = 2**32
    nested: list[tuple[str, dict[str, object], str]] = [
        ("header_types", {"fields": [{"type": {"bits": bound}}]}, "fields[0].type.bits"),
        (
            "struct_types",
            {"fields": [{"type": {"stack": {"size": bound}}}]},
            "fields[0].type.stack.size",
        ),
        (
            "extern_types",
            {"constructor_params": [{"type": {"bits": bound}, "direction": "DIRECTION_NONE"}]},
            "constructor_params[0].type.bits",
        ),
        ("extern_types", {"methods": [{"returns": {"bits": bound}}]}, "methods[0].returns.bits"),
        (
            "extern_instances",
            {"args": [{"bits": {"width": bound, "value": "0"}}]},
            "args[0].bits.width",
        ),
    ]
    block_bad: list[tuple[dict[str, object], str]] = [
        ({"params": [{"type": {"bits": bound}}]}, "params[0].type.bits"),
        ({"locals": [{"type": {"stack": {"size": bound}}}]}, "locals[0].type.stack.size"),
        ({"body": [{"push": {"stack": {"var": "x"}, "count": bound}}]}, "body[0].push.count"),
        ({"tables": [{"size": bound}]}, "tables[0].size"),
        (
            {"tables": [{"const_entries": [{"priority": bound}]}]},
            "tables[0].const_entries[0].priority",
        ),
        (
            {
                "tables": [
                    {"const_entries": [{"keys": [{"lpm": {"value": "0", "prefix_len": bound}}]}]}
                ]
            },
            "tables[0].const_entries[0].keys[0].lpm.prefix_len",
        ),
        (
            {"body": [{"advance": {"bits": {"slice": {"operand": {"var": "x"}, "hi": bound}}}}]},
            "body[0].advance.bits.slice.hi",
        ),
    ]
    nested += [("blocks", {"kind": "BLOCK_KIND_CONTROL", **wire}, path) for wire, path in block_bad]
    for field, wire, path in nested:
        result.append(
            ("program", {field: [wire]}, f"leaf.{field}[0].{path}: {bound} does not fit in uint32")
        )
    result.append(("program", {"blocks": [{}]}, "leaf.blocks[0].kind: unspecified"))
    result.append(("program", {"blocks": [{"kind": 1}]}, "leaf.blocks[0].kind: expected a string"))
    return result


def normalized() -> list[tuple[ProgramCodecKind, object, ProgramCase]]:
    result: list[tuple[ProgramCodecKind, object, ProgramCase]] = []
    shapes: list[tuple[ProgramCodecKind, ProgramCase, list[str]]] = [
        ("export", export(), ["role", "block"]),
        ("program", program(), ORDER),
    ]
    for kind, empty, fields in shapes:
        result.append((kind, {"unknown_field": False}, empty))
        for field in fields:
            for value in (None, [] if field in LISTS else ""):
                result.append((kind, {field: value}, empty))
    result.append(("program", {"headerTypes": [{"name": "Alias"}]}, program()))
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


def protobuf_value(kind: ProgramCodecKind, wire: dict[str, object]) -> tuple[Message, object]:
    wrapper = wire if kind == "program" else {"exports": [wire]}
    parsed = arch_wire.load_json(json.dumps(wrapper))
    recovered = arch_wire.load_json(arch_wire.dump_json(parsed))
    assert recovered == parsed
    message = recovered if kind == "program" else recovered.exports[0]
    return message, json_format.MessageToDict(message, preserving_proto_field_name=True)
