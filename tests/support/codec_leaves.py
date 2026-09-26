"""Reusable codec leaves fixtures and independent expectations."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from google.protobuf import json_format

from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt._json import loads
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]


LeafKind = Literal["literal", "type", "key"]


DeclarationKind = Literal[
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


TableKind = Literal["table_key", "action_call", "entry", "table"]


ParserKind = Literal["target", "key_set", "select_case", "transition", "state"]


BlockCodecKind = Literal["action", "block"]


ProgramCodecKind = Literal["export", "program"]


EntriesCodecKind = Literal["table_entries", "entries"]


CodecKind = (
    LeafKind
    | DeclarationKind
    | TableKind
    | ParserKind
    | BlockCodecKind
    | ProgramCodecKind
    | EntriesCodecKind
    | Literal["expr", "lvalue", "arg", "stmt"]
)


@dataclass(frozen=True)
class Leaf:
    kind: LeafKind
    wire: dict[str, object]
    value: dict[str, object]


def leaves() -> list[Leaf]:
    result = [
        Leaf("literal", {"bits": {"value": str(n)}}, {"tag": "bits", "width": 0, "value": str(n)})
        for n in [0, 1, 9, 10, 99, 100, 2**32 - 1, 2**32, 10**100 + 7]
    ]
    for width in [1, 8, 2**32 - 1]:
        result.append(
            Leaf(
                "literal",
                {"bits": {"width": width, "value": "0"}},
                {"tag": "bits", "width": width, "value": "0"},
            )
        )
    for b in [False, True]:
        result.append(Leaf("literal", {"boolean": b}, {"tag": "boolean", "value": b}))
    for name in ["", "NoError", 'quoted"\\\n名字']:
        result.extend(
            [
                Leaf("literal", {"error": name}, {"tag": "error", "name": name}),
                Leaf("type", {"header": name}, {"tag": "header", "name": name}),
                Leaf("type", {"struct": name}, {"tag": "struct", "name": name}),
                Leaf("type", {"enum_type": name}, {"tag": "enum_type", "name": name}),
            ]
        )
    for enum_type, member in [("", ""), ("E", ""), ("", "m"), ("E", "m")]:
        fields = {k: v for k, v in [("enum_type", enum_type), ("member", member)] if v}
        result.append(
            Leaf(
                "literal",
                {"enum_member": fields},
                {"tag": "enum_member", "enum_type": enum_type, "member": member},
            )
        )
    result.extend(
        [
            Leaf("type", {"bits": width}, {"tag": "bits", "width": width})
            for width in [0, 1, 2**32 - 1]
        ]
    )
    result.extend([Leaf("type", {tag: {}}, {"tag": tag}) for tag in ["boolean", "error"]])
    for header, size in [("", 0), ("H", 0), ("", 1), ("H", 2**32 - 1)]:
        fields: dict[str, object] = {}
        if header:
            fields["header"] = header
        if size:
            fields["size"] = size
        result.append(
            Leaf("type", {"stack": fields}, {"tag": "stack", "header": header, "size": size})
        )
    return result


def protobuf_value(kind: LeafKind, wire: dict[str, object]) -> tuple[dict[str, object], dict]:
    """The production protobuf adapter, with no semantic validator in between."""
    program = apb.BlockAssembly()
    observed: dict[str, object]
    if kind == "literal":
        value = json_format.ParseDict(wire, pb.Literal())
        program.extern_instances.add().args.add().CopyFrom(value)
        recovered = arch_wire.load_json(arch_wire.dump_json(program)).extern_instances[0].args[0]
        assert recovered == value
        encoded = json.loads(arch_wire.dump_json(program))["extern_instances"][0]["args"][0]
        match value.WhichOneof("value"):
            case "bits":
                observed = {"tag": "bits", "width": value.bits.width, "value": value.bits.value}
            case "boolean":
                observed = {"tag": "boolean", "value": value.boolean}
            case "enum_member":
                observed = {
                    "tag": "enum_member",
                    "enum_type": value.enum_member.enum_type,
                    "member": value.enum_member.member,
                }
            case "error":
                observed = {"tag": "error", "name": value.error}
            case _:
                raise AssertionError("test requires a set literal oneof")
    elif kind == "type":
        value = json_format.ParseDict(wire, pb.Type())
        program.struct_types.add().fields.add().type.CopyFrom(value)
        recovered = arch_wire.load_json(arch_wire.dump_json(program)).struct_types[0].fields[0].type
        assert recovered == value
        encoded = json.loads(arch_wire.dump_json(program))["struct_types"][0]["fields"][0]["type"]
        match value.WhichOneof("kind"):
            case "bits":
                observed = {"tag": "bits", "width": value.bits}
            case "boolean" | "error" as tag:
                observed = {"tag": tag}
            case "header" | "struct" | "enum_type" as tag:
                observed = {"tag": tag, "name": getattr(value, tag)}
            case "stack":
                observed = {"tag": "stack", "header": value.stack.header, "size": value.stack.size}
            case _:
                raise AssertionError("test requires a set type oneof")
    else:
        value = json_format.ParseDict(wire, pb.KeyValue())
        program.blocks.add().tables.add().const_entries.add().keys.add().CopyFrom(value)
        recovered = (
            arch_wire.load_json(arch_wire.dump_json(program))
            .blocks[0]
            .tables[0]
            .const_entries[0]
            .keys[0]
        )
        assert recovered == value
        encoded = json.loads(arch_wire.dump_json(program))["blocks"][0]["tables"][0][
            "const_entries"
        ][0]["keys"][0]
        match value.WhichOneof("kind"):
            case "exact":
                observed = {"tag": "exact", "value": value.exact}
            case "lpm":
                observed = {
                    "tag": "lpm",
                    "value": value.lpm.value,
                    "prefix_len": value.lpm.prefix_len,
                }
            case "ternary":
                observed = {
                    "tag": "ternary",
                    "value": value.ternary.value,
                    "mask": value.ternary.mask,
                }
            case _:
                raise AssertionError("test requires a set key oneof")
    return observed, encoded


def assert_leaf(
    lean_binary: Path, kind: CodecKind, wire: object, expected: dict[str, object]
) -> dict[str, object]:
    """Retain raw leaf JSON before an independent known answer can fail."""
    # A sibling of the given endpoint when there is one (the observer tests
    # hand in a fake); otherwise the architecture package's endpoint,
    # which delegates core kinds and also handles assembly/export leaves.
    binary = lean_binary.with_name("codec-leaves")
    if not binary.exists():
        binary = ROOT / "spec/arch/.lake/build/bin/codec-leaves"
    assert binary.is_file(), f"missing test endpoint: {binary} (build spec/arch/ default targets)"
    request = {"kind": kind, "wire": wire}
    command = [str(binary)]
    failure: str | None = None
    returncode: int | None = None
    stderr = ""
    try:
        result = subprocess.run(
            command, input=json.dumps(request) + "\n", text=True, capture_output=True, timeout=10
        )
        returncode, stderr = result.returncode, result.stderr
        try:
            actual = loads(result.stdout)
        except ValueError:
            actual = {"malformed_stdout": result.stdout}
    except (subprocess.TimeoutExpired, OSError, UnicodeError) as error:
        failure = type(error).__name__
        actual = {"process_error": failure, "detail": str(error)}
        if isinstance(error, subprocess.TimeoutExpired):
            actual["stdout"] = process_text(error.stdout)
            stderr = process_text(error.stderr)
        elif isinstance(error, UnicodeDecodeError):
            actual["raw_bytes_hex"] = error.object.hex()
    if failure is not None or returncode != 0 or stderr or not same_json(actual, expected):
        artifact = {
            "format": "p4blo.codec-leaf.v0",
            "request": request,
            "expected": expected,
            "actual": actual,
            "returncode": returncode,
            "stderr": stderr,
            "command": command,
            "timeout_seconds": 10,
        }
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:24]
        folder = Path(os.environ.get("P4BLO_CODEC_FAILURE_DIR", ROOT / ".artifacts/codec"))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"leaf-{digest}.json").write_text(json.dumps(artifact, indent=2) + "\n")
    assert failure is None, actual
    assert returncode == 0, stderr
    assert stderr == ""
    assert same_json(actual, expected), (actual, expected)
    assert isinstance(actual, dict)
    return dict(actual)


def process_text(value: str | bytes | None) -> str:
    """TimeoutExpired can contain bytes even when the child was run in text mode."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def same_json(left: object, right: object) -> bool:
    """Canonical rendering compares JSON structure without bool/int/float equality."""
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def key_leaves() -> list[tuple[str, Leaf]]:
    result = [
        (f"exact-{n}", Leaf("key", {"exact": str(n)}, {"tag": "exact", "value": str(n)}))
        for n in [0, 1, 9, 10, 2**32, 10**100 + 7]
    ]
    for value in [0, 1, 10**100 + 7]:
        for prefix in [0, 1, 2**32 - 1]:
            fields: dict[str, object] = {"value": str(value)}
            if prefix:
                fields["prefix_len"] = prefix
            result.append(
                (
                    f"lpm-{value}-{prefix}",
                    Leaf(
                        "key",
                        {"lpm": fields},
                        {"tag": "lpm", "value": str(value), "prefix_len": prefix},
                    ),
                )
            )
    for value, mask in [
        (0, 0),
        (0, 1),
        (1, 0),
        (3, 12),
        (12, 3),
        (2**32 - 1, 2**32 - 1),
        (10**100 + 7, 2**32),
        (2**32, 10**100 + 7),
    ]:
        fields = {"value": str(value), "mask": str(mask)}
        result.append(
            (
                f"ternary-{value}-{mask}",
                Leaf("key", {"ternary": fields}, {"tag": "ternary", **fields}),
            )
        )
    return result
