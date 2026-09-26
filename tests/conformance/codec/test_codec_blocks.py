"""Action/Block wire-only answers, independent of production codecs/validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.codec_blocks import (
    BLOCK_KINDS,
    KINDS,
    BlockCase,
    cases,
    malformed,
    normalized,
    protobuf_value,
    requests,
)
from tests.support.codec_leaves import BlockCodecKind, assert_leaf, same_json


def test_block_baseline_contract() -> None:
    rows = requests()
    assert (len(cases()), len(malformed()), len(normalized()), len(rows)) == (19, 384, 95, 498)
    assert rows and len({json.dumps(r, sort_keys=True) for r, _ in rows}) == len(rows)
    assert {r["kind"] for r, _ in rows} == set(KINDS)
    assert {c.value["kind"] for c in cases() if c.kind == "block"} == set(BLOCK_KINDS)


@pytest.mark.parametrize("case", cases())
def test_block_protobuf_known_answers(case: BlockCase) -> None:
    _, encoded = protobuf_value(case.kind, case.wire)
    assert same_json(encoded, case.wire)


@pytest.mark.parametrize("case", cases())
def test_lean_agrees_block_known_answers(lean_binary: Path, case: BlockCase) -> None:
    actual = assert_leaf(
        lean_binary, case.kind, case.wire, {"value": case.value, "encoded": case.wire}
    )
    wire = actual["encoded"]
    assert isinstance(wire, dict)
    recovered, encoded = protobuf_value(case.kind, wire)
    expected, _ = protobuf_value(case.kind, case.wire)
    assert recovered == expected and same_json(encoded, case.wire)


@pytest.mark.parametrize("kind,wire,error", malformed())
def test_lean_agrees_block_exact_errors(
    lean_binary: Path, kind: BlockCodecKind, wire: object, error: str
) -> None:
    assert_leaf(lean_binary, kind, wire, {"error": error})


@pytest.mark.parametrize("kind,wire,case", normalized())
def test_lean_agrees_block_normalization(
    lean_binary: Path, kind: BlockCodecKind, wire: object, case: BlockCase
) -> None:
    actual = assert_leaf(lean_binary, kind, wire, {"value": case.value, "encoded": case.wire})
    encoded = actual["encoded"]
    assert isinstance(encoded, dict)
    _, canonical = protobuf_value(kind, encoded)
    assert same_json(canonical, case.wire)
