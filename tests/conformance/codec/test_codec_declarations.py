"""Independent nine-declaration wire/constructor/default/error-order anchors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.codec_declarations import (
    DIRECTIONS,
    KINDS,
    Declaration,
    cases,
    malformed,
    normalized,
    protobuf_value,
    requests,
)
from tests.support.codec_leaves import DeclarationKind, assert_leaf, same_json


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
