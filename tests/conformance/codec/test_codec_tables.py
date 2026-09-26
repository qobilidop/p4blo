"""Independent table declaration observations: no validation or table execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.codec_leaves import TableKind, assert_leaf, same_json
from tests.support.codec_tables import (
    KINDS,
    MATCH_KINDS,
    TableCase,
    cases,
    malformed,
    normalized,
    protobuf_value,
    requests,
)


def test_table_baseline_contract() -> None:
    rows = requests()
    assert len(rows) == 181
    assert len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)
    assert "key" not in KINDS  # Existing leaf kind continues to mean KeyValue.
    assert {c.value["match_kind"] for c in cases() if c.kind == "table_key"} == set(MATCH_KINDS)


@pytest.mark.parametrize("case", cases())
def test_table_protobuf_known_answers(case: TableCase) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_table_known_answers(lean_binary: Path, case: TableCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    actual_value, encoded = protobuf_value(case.kind, wire)
    expected_value, _ = protobuf_value(case.kind, case.wire)
    assert actual_value == expected_value and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_table_exact_errors(
    lean_binary: Path, kind: TableKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_table_normalization(
    lean_binary: Path, kind: TableKind, wire: object, case: TableCase
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    _, canonical = protobuf_value(kind, wire)
    assert same_json(canonical, case.wire)
