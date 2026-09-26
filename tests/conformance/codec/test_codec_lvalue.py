"""Independent LValue/Arg wire and semantic observations, without validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.codec_expr import Expression
from tests.support.codec_leaves import assert_leaf, same_json
from tests.support.codec_lvalue import (
    Case,
    Kind,
    cases,
    malformed,
    normalized,
    protobuf_value,
)


@pytest.mark.parametrize("case", cases())
def test_lvalue_arg_protobuf_known_answers(case: Case) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
@pytest.mark.lean
def test_lean_agrees_lvalue_arg_known_answers(lean_binary: Path, case: Case) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    actual_wire = actual["encoded"]
    assert isinstance(actual_wire, dict)
    actual_value, encoded = protobuf_value(case.kind, actual_wire)
    expected_value, _ = protobuf_value(case.kind, case.wire)
    assert actual_value == expected_value and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,message", malformed())
@pytest.mark.lean
def test_lean_agrees_lvalue_arg_exact_errors(
    lean_binary: Path, kind: Kind, wire: object, message: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": message})


@pytest.mark.parametrize("kind,wire,expected", normalized())
@pytest.mark.lean
def test_lean_agrees_lvalue_arg_normalization(
    lean_binary: Path, kind: Kind, wire: object, expected: Expression
) -> None:
    assert_leaf(lean_binary, kind, wire, {"value": expected.value, "encoded": expected.wire})
