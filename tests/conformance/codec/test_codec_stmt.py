"""Independent statement constructor/wire/default/error-order codec anchors."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.codec_expr import Expression
from tests.support.codec_leaves import assert_leaf, same_json
from tests.support.codec_stmt import (
    cases,
    malformed,
    normalized,
    protobuf_value,
)


@pytest.mark.parametrize("case", cases())
def test_stmt_protobuf_known_answers(case: Expression) -> None:
    _, encoded = protobuf_value(case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
@pytest.mark.lean
def test_lean_agrees_stmt_known_answers(lean_binary: Path, case: Expression) -> None:
    actual = assert_leaf(
        lean_binary, "stmt", case.wire, {"value": case.value, "encoded": case.wire}
    )
    actual_wire = actual["encoded"]
    assert isinstance(actual_wire, dict)
    actual_value, encoded = protobuf_value(actual_wire)
    expected_value, _ = protobuf_value(case.wire)
    assert actual_value == expected_value and same_json(encoded, case.wire)


@pytest.mark.parametrize("wire,message", malformed())
@pytest.mark.lean
def test_lean_agrees_stmt_exact_errors(lean_binary: Path, wire: object, message: str) -> None:
    assert_leaf(lean_binary, "stmt", wire, {"error": message})


@pytest.mark.parametrize("wire,expected", normalized())
@pytest.mark.lean
def test_lean_agrees_stmt_normalization(
    lean_binary: Path, wire: object, expected: Expression
) -> None:
    assert_leaf(lean_binary, "stmt", wire, {"value": expected.value, "encoded": expected.wire})
