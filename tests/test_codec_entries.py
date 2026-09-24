"""Host-entry wire observations, separate from installation and packet execution."""

from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest
from google.protobuf import json_format
from google.protobuf.message import Message

from p4blo import arch, interp, ir, validator
from p4blo.arch.externs import Registry
from p4blo.arch.externs.counter import Counter
from p4blo.drt._json import loads
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, scalar_program
from p4blo.drt.run import run_python
from p4blo.drt.state import encode, snapshot
from p4blo.interp.tables import InstallError
from p4blo.v0 import p4blo_pb2 as pb
from tests import test_codec_tables as table
from tests.test_codec_expr import Expression
from tests.test_codec_leaves import EntriesCodecKind, assert_leaf, key_leaves, leaves, same_json
from tests.test_lean_forwarder import freeze


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


# These are public-pipeline rejection checks, not runtime-error rollback tests.
def host_program() -> pb.Program:
    program = scalar_program(bits(8, 42), 8)
    program.name = "interchange-rejection"
    control = program.blocks[1]
    control.actions.add(name="NoAction")
    action = control.actions.add(name="Set")
    action.params.add(name="arg", type=pb.Type(bits=8), direction=pb.DIRECTION_NONE)
    for name, kind in [
        ("exact", pb.MATCH_KIND_EXACT),
        ("lpm", pb.MATCH_KIND_LPM),
        ("ternary", pb.MATCH_KIND_TERNARY),
        ("fixed", pb.MATCH_KIND_EXACT),
    ]:
        declaration = control.tables.add(name=name, actions=["NoAction", "Set"], size=8)
        declaration.keys.add(name="key", expr=bits(8, 7), match_kind=kind)
        declaration.default_action.action = "NoAction"
        declaration.const_default_action = name == "fixed"
    control.body.add().apply.table = "exact"
    counter = program.extern_types.add(name="counter")
    counter.constructor_params.add(name="size", type=pb.Type(bits=32), direction=pb.DIRECTION_IN)
    counter.methods.add(name="count").params.add(
        name="index", type=pb.Type(bits=32), direction=pb.DIRECTION_IN
    )
    for name, size, index in [("ticks", 3, 0), ("guard", 4, 2)]:
        program.extern_instances.add(
            name=name, extern_type="counter", args=[bits(32, size).literal]
        )
        call = control.body.add().call_extern
        call.instance, call.method = name, "count"
        call.args.add(expr=bits(32, index))
    assert validator.validate(program) == []
    return program


def host_wire(
    *,
    target: str = "exact",
    key: object = None,
    action: object = None,
    priority: int = 0,
    default: object = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "keys": [{"exact": "7"} if key is None else key],
        "action": {"action": "NoAction"} if action is None else action,
    }
    if priority:
        entry["priority"] = priority
    item: dict[str, object] = {"block": "C", "table": target, "entries": [entry]}
    if default is not None:
        item["default_action"] = default
    return {"tables": [item]}


@dataclass(frozen=True)
class HostRejection:
    name: str
    wire: dict[str, object]
    python_error: str
    lean_error: str
    decode: bool = False


def host_rejections() -> list[HostRejection]:
    # Diagnostics are literal intended answers, not copied from either runtime.
    result = [
        HostRejection(
            "array", {"tables": False}, "must be in []", "entries.tables: expected an array", True
        ),
        HostRejection(
            "uint32",
            {"tables": [{"entries": [{"priority": 2**32}]}]},
            "Value out of range",
            "entries.tables[0].entries[0].priority: 4294967296 does not fit in uint32",
            True,
        ),
        HostRejection(
            "target",
            host_wire(target="Missing"),
            "no table 'Missing' in block 'C'",
            "no table 'Missing' in block 'C'",
        ),
        HostRejection(
            "kind",
            host_wire(key={"lpm": {"value": "0"}}),
            "key 'key' wants a exact value",
            "key 'key' wants a exact value",
        ),
        HostRejection(
            "width",
            host_wire(key={"exact": "256"}),
            "exact value '256' does not fit in 8 bits",
            "exact value '256' does not fit in 8 bits",
        ),
        HostRejection(
            "prefix",
            host_wire(target="lpm", key={"lpm": {"value": "0", "prefix_len": 9}}),
            "prefix length 9 exceeds width 8",
            "prefix length 9 exceeds width 8",
        ),
        HostRejection(
            "mask",
            host_wire(target="ternary", key={"ternary": {"value": "2", "mask": "1"}}),
            "ternary value '2' has bits outside its mask",
            "ternary value '2' has bits outside its mask",
        ),
        HostRejection(
            "priority",
            host_wire(priority=7),
            "table 'exact' has no ternary key; priority must be 0",
            "table 'exact' has no ternary key; priority must be 0",
        ),
        HostRejection(
            "action",
            host_wire(action={"action": "Missing"}),
            "table 'exact' has no action 'Missing'",
            "table 'exact' has no action 'Missing'",
        ),
        HostRejection(
            "argument",
            host_wire(action={"action": "Set", "args": [{"bits": {"width": 9, "value": "1"}}]}),
            "argument for Set.arg is bit<9>, not bit<8>",
            "argument for Set.arg is bit<9>, not bit<8>",
        ),
        HostRejection(
            "empty-default",
            host_wire(default={}),
            "table 'exact' has no action ''",
            "table 'exact' has no action ''",
        ),
        HostRejection(
            "const-default",
            host_wire(target="fixed", default={"action": "NoAction"}),
            "table 'fixed' has a const default action",
            "table 'fixed' has a const default action",
        ),
    ]
    duplicate = host_wire()
    tables = duplicate["tables"]
    assert isinstance(tables, list)
    tables.append(deepcopy(tables[0]))
    result.append(
        HostRejection(
            "duplicate",
            duplicate,
            "table 'exact': duplicate entry",
            "table 'exact': duplicate entry",
        )
    )
    late = host_wire()
    tables = late["tables"]
    assert isinstance(tables, list)
    tables.append({"block": "C", "table": "Missing", "default_action": {"action": "NoAction"}})
    result.append(
        HostRejection(
            "later-table",
            late,
            "no table 'Missing' in block 'C'",
            "no table 'Missing' in block 'C'",
        )
    )
    return result


def expected_host_state(count: int) -> dict[str, object]:
    return {
        "guard": {"kind": "counter", "values": ["0x0", "0x0", hex(count), "0x0"]},
        "ticks": {"kind": "counter", "values": [hex(count), "0x0", "0x0"]},
    }


def observe_rejected_host(case: HostRejection) -> None:
    loaded = arch.load(host_program())
    valid = json_format.ParseDict(host_wire(), pb.Entries())
    request = Case(valid, 0, b"\xab\xcd")
    assert run_python(loaded, request, 4) == [(0, b"\x2a\xab\xcd")]
    assert same_json(encode(snapshot(loaded)), expected_host_state(1))
    # Detached structural snapshots cover lookup maps, not just program bytes.
    frozen_index = freeze(loaded.index)
    frozen_externs = freeze(loaded.externs)
    frozen_meta = freeze(loaded.metadata)
    frozen_roles = freeze(dict(loaded.blocks))
    installed = loaded.entries(valid)
    frozen_installed = freeze(installed)
    frozen_wire = deepcopy(case.wire)
    frozen_valid = valid.SerializeToString(deterministic=True)
    with (
        patch.object(interp, "run_parser", wraps=interp.run_parser) as parser_call,
        patch.object(interp, "run_control", wraps=interp.run_control) as control_call,
        patch.object(interp, "run_deparser", wraps=interp.run_deparser) as deparser_call,
    ):
        expected_exception = json_format.ParseError if case.decode else InstallError
        with pytest.raises(expected_exception, match=re.escape(case.python_error)):
            rejected = json_format.ParseDict(deepcopy(case.wire), pb.Entries())
            run_python(loaded, Case(rejected, 0, b"\xab\xcd"), 4)
        assert (parser_call.call_count, control_call.call_count, deparser_call.call_count) == (
            0,
            0,
            0,
        )
    assert same_json(encode(snapshot(loaded)), expected_host_state(1)), (
        "rejected host changed persistent state"
    )
    assert freeze(loaded.externs) == frozen_externs, "rejected host changed raw extern state"
    assert freeze(loaded.index) == frozen_index, "rejected host changed index configuration"
    assert freeze(loaded.metadata) == frozen_meta, "rejected host changed metadata configuration"
    assert freeze(dict(loaded.blocks)) == frozen_roles, "rejected host changed roles"
    assert freeze(installed) == frozen_installed, "rejected host changed installed configuration"
    assert (
        same_json(case.wire, frozen_wire)
        and valid.SerializeToString(deterministic=True) == frozen_valid
    )
    assert run_python(loaded, request, 4) == [(0, b"\x2a\xab\xcd")]
    assert same_json(encode(snapshot(loaded)), expected_host_state(2))


@pytest.mark.parametrize("case", host_rejections(), ids=lambda c: c.name)
def test_host_rejection_does_not_execute_or_change_state(case: HostRejection) -> None:
    observe_rejected_host(case)


def test_host_observer_rejects_boolean_count_hidden_by_hex() -> None:
    original = arch.Loaded.entries
    hits: list[str] = []

    def corrupt_after_rejection(loaded: arch.Loaded, host: pb.Entries | None = None):
        try:
            return original(loaded, host)
        except InstallError:
            counter = loaded.externs["ticks"]
            assert isinstance(counter, Counter)
            assert type(counter.counts[0]) is int and counter.counts[0] == 1
            counter.counts[0] = True
            # The logical hex observer alone really survives this corruption.
            assert same_json(encode(snapshot(loaded)), expected_host_state(1))
            hits.append("delegated rejection")
            raise

    case = next(c for c in host_rejections() if c.name == "target")
    with patch.object(arch.Loaded, "entries", corrupt_after_rejection):
        with pytest.raises(AssertionError, match="raw extern state"):
            observe_rejected_host(case)
    assert hits == ["delegated rejection"]


def test_host_observer_rejects_metadata_boolean_integer_alias() -> None:
    original = arch.Loaded.entries
    hits: list[str] = []
    restorations: list[tuple[object, bool]] = []

    def corrupt_after_rejection(loaded: arch.Loaded, host: pb.Entries | None = None):
        try:
            return original(loaded, host)
        except InstallError:
            field = loaded.metadata.contract.fields[0]
            assert field.provided is True
            restorations.append((field, field.provided))
            object.__setattr__(field, "provided", 1)
            hits.append("delegated rejection")
            raise

    case = next(c for c in host_rejections() if c.name == "target")
    try:
        with patch.object(arch.Loaded, "entries", corrupt_after_rejection):
            with pytest.raises(AssertionError, match="metadata configuration"):
                observe_rejected_host(case)
        assert hits == ["delegated rejection"]
    finally:
        for field, original_value in restorations:
            object.__setattr__(field, "provided", original_value)


@pytest.mark.parametrize("case", host_rejections(), ids=lambda c: c.name)
def test_lean_agrees_host_rejection_state(
    lean_binary: Path, tmp_path: Path, case: HostRejection
) -> None:
    program = host_program()
    source = tmp_path / "host-program.json"
    source.write_text(ir.dump_json(program))
    requests = [host_wire(), case.wire, host_wire()]
    stdin = "".join(
        json.dumps({"entries": value, "ingress_port": 0, "packet": "abcd"}) + "\n"
        for value in requests
    )
    result = subprocess.run(
        [str(lean_binary), "run", str(source)],
        input=stdin,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0 and result.stderr == "", (result.returncode, result.stderr)
    replies = [loads(line) for line in result.stdout.splitlines()]
    # Every reply also carries its rule coverage; the exact comparison is about the rest.
    assert all(isinstance(r.pop("coverage"), list) for r in replies)
    expected = [
        {"outputs": [[0, "2aabcd"]], "state": expected_host_state(1)},
        {"error": case.lean_error, "state": expected_host_state(1)},
        {"outputs": [[0, "2aabcd"]], "state": expected_host_state(2)},
    ]
    assert same_json(replies, expected)


@pytest.mark.parametrize("kind", ["json-type", "duplicate-block", "empty-name"])
def test_program_startup_rejection_before_binding(kind: str) -> None:
    program = host_program()
    if kind == "duplicate-block":
        program.blocks.add().CopyFrom(program.blocks[1])
    elif kind == "empty-name":
        program.blocks[1].name = ""
    wire = json.loads(ir.dump_json(program))
    if kind == "json-type":
        wire["blocks"] = False
    with (
        patch.object(Registry, "bind", side_effect=AssertionError("binding reached")) as binding,
        patch.object(interp, "run_parser", side_effect=AssertionError("packet reached")) as packet,
    ):
        with pytest.raises(
            json_format.ParseError if kind == "json-type" else validator.ValidationError
        ):
            arch.load(ir.load_json(json.dumps(wire)))
        assert binding.call_count == packet.call_count == 0


@pytest.mark.parametrize(
    "kind,error",
    [
        ("json-type", "blocks: expected an array"),
        ("duplicate-block", "'C' declared twice in program"),
        ("empty-name", "empty name in program"),
    ],
)
def test_lean_agrees_program_startup_rejection(
    lean_binary: Path, tmp_path: Path, kind: str, error: str
) -> None:
    program = host_program()
    if kind == "duplicate-block":
        program.blocks.add().CopyFrom(program.blocks[1])
    elif kind == "empty-name":
        program.blocks[1].name = ""
    wire = json.loads(ir.dump_json(program))
    if kind == "json-type":
        wire["blocks"] = False
    source = tmp_path / "rejected-program.json"
    source.write_text(json.dumps(wire))
    result = subprocess.run(
        [str(lean_binary), "run", str(source)],
        input=json.dumps({"entries": host_wire(), "packet": "abcd"}) + "\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1 and result.stdout == ""
    assert result.stderr == f"error: {error}\n"
