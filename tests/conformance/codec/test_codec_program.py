"""Finite whole-program wire answers, independent of validation and execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from google.protobuf import json_format

from tests.support.codec_leaves import ProgramCodecKind, assert_leaf, same_json
from tests.support.codec_program import (
    KINDS,
    ProgramCase,
    cases,
    malformed,
    normalized,
    protobuf_value,
    requests,
)


def test_program_inventory() -> None:
    rows = requests()
    assert (len(cases()), len(malformed()), len(normalized()), len(rows)) == (19, 56, 29, 104)
    assert rows and len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)


@pytest.mark.parametrize("case", cases())
def test_program_public_known_answers(case: ProgramCase) -> None:
    _, canonical = protobuf_value(case.kind, case.wire)
    assert same_json(canonical, case.wire)


@pytest.mark.parametrize("case", cases())
@pytest.mark.lean
def test_lean_agrees_program_answers(lean_binary: Path, case: ProgramCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    _, canonical = protobuf_value(case.kind, wire)
    assert same_json(canonical, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
@pytest.mark.lean
def test_lean_agrees_program_errors(
    lean_binary: Path, kind: ProgramCodecKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
@pytest.mark.lean
def test_lean_agrees_program_defaults(
    lean_binary: Path, kind: ProgramCodecKind, wire: object, case: ProgramCase
) -> None:
    assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})


@pytest.mark.parametrize("kind", KINDS)
def test_program_unknown_fields_outside_canonical_domain(kind: ProgramCodecKind) -> None:
    with pytest.raises(json_format.ParseError, match="unknown_field"):
        protobuf_value(kind, {"unknown_field": False})


def test_program_protojson_extensions_are_not_shared_wire_contract() -> None:
    _, alias = protobuf_value("program", {"headerTypes": [{"name": "Alias"}]})
    assert same_json(alias, {"header_types": [{"name": "Alias"}]})
    _, numeric = protobuf_value("program", {"blocks": [{"kind": 1}]})
    assert same_json(numeric, {"blocks": [{"kind": "BLOCK_KIND_PARSER"}]})
