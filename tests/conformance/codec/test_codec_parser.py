"""Independent parser-syntax codec answers, without parser validity premises."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.codec_leaves import ParserKind, assert_leaf, same_json
from tests.support.codec_parser import (
    KINDS,
    ParserCase,
    cases,
    malformed,
    normalized,
    protobuf_value,
    requests,
)


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
@pytest.mark.lean
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
@pytest.mark.lean
def test_lean_agrees_parser_exact_errors(
    lean_binary: Path, kind: ParserKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
@pytest.mark.lean
def test_lean_agrees_parser_normalization(
    lean_binary: Path, kind: ParserKind, wire: object, case: ParserCase
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    encoded = actual["encoded"]
    assert isinstance(encoded, dict)
    _, canonical = protobuf_value(kind, encoded)
    assert same_json(canonical, case.wire)
