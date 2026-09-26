"""Host-entry wire observations, separate from installation and packet execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from google.protobuf import json_format

from p4blo import arch
from p4blo.arch import entry, v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.externs import Registry
from p4blo.arch.externs.counter import Counter
from p4blo.drt._json import loads
from p4blo.drt.state import encode, snapshot
from p4blo.interp.tables import InstallError
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.codec_entries import (
    KINDS,
    EntriesCase,
    HostRejection,
    cases,
    expected_host_state,
    host_program,
    host_rejections,
    host_wire,
    malformed,
    normalized,
    observe_rejected_host,
    protobuf_value,
    requests,
)
from tests.support.codec_leaves import EntriesCodecKind, assert_leaf, same_json


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
@pytest.mark.lean
def test_lean_agrees_entries_answers(lean_binary: Path, case: EntriesCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    _, canonical = protobuf_value(case.kind, wire)
    assert same_json(canonical, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
@pytest.mark.lean
def test_lean_agrees_entries_errors(
    lean_binary: Path, kind: EntriesCodecKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
@pytest.mark.lean
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
@pytest.mark.lean
def test_lean_agrees_host_rejection_state(
    lean_binary: Path, tmp_path: Path, case: HostRejection
) -> None:
    program = host_program()
    source = tmp_path / "host-program.json"
    source.write_text(arch_wire.dump_json(program))
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
    assert all(isinstance(r, dict) and isinstance(r.pop("coverage"), list) for r in replies)
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
    wire = json.loads(arch_wire.dump_json(program))
    if kind == "json-type":
        wire["blocks"] = False
    with (
        patch.object(Registry, "bind", side_effect=AssertionError("binding reached")) as binding,
        patch.object(entry, "run_parser", side_effect=AssertionError("packet reached")) as packet,
    ):
        with pytest.raises(
            json_format.ParseError if kind == "json-type" else validator.ValidationError
        ):
            v1model.load(arch_wire.load_json(json.dumps(wire)))
        assert binding.call_count == packet.call_count == 0


@pytest.mark.parametrize(
    "kind,error",
    [
        ("json-type", "blocks: expected an array"),
        ("duplicate-block", "'C' declared twice in program"),
        ("empty-name", "empty name in program"),
    ],
)
@pytest.mark.lean
def test_lean_agrees_program_startup_rejection(
    lean_binary: Path, tmp_path: Path, kind: str, error: str
) -> None:
    program = host_program()
    if kind == "duplicate-block":
        program.blocks.add().CopyFrom(program.blocks[1])
    elif kind == "empty-name":
        program.blocks[1].name = ""
    wire = json.loads(arch_wire.dump_json(program))
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
