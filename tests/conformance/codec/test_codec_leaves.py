"""Actual leaf wire laws: independent payloads, not just self round-trips."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.support.codec_leaves import (
    Leaf,
    LeafKind,
    assert_leaf,
    key_leaves,
    leaves,
    protobuf_value,
    same_json,
)


@pytest.mark.parametrize("leaf", leaves())
def test_leaf_protobuf_known_answers(leaf: Leaf) -> None:
    value, encoded = protobuf_value(leaf.kind, leaf.wire)
    assert same_json(value, leaf.value)
    assert same_json(encoded, leaf.wire)


@pytest.mark.parametrize("leaf", leaves())
@pytest.mark.lean
def test_lean_agrees_leaf_known_answers(lean_binary: Path, leaf: Leaf) -> None:
    actual = assert_leaf(
        lean_binary, leaf.kind, leaf.wire, {"value": leaf.value, "encoded": leaf.wire}
    )
    actual_encoded = actual["encoded"]
    assert isinstance(actual_encoded, dict)
    value, encoded = protobuf_value(leaf.kind, actual_encoded)
    assert same_json(value, leaf.value) and same_json(encoded, leaf.wire)


@pytest.mark.parametrize("wrong", [0, 0.0, 1, 1.0])
def test_leaf_observer_retains_type_confusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wrong: object
) -> None:
    (tmp_path / "codec-leaves").touch()
    monkeypatch.setenv("P4BLO_CODEC_FAILURE_DIR", str(tmp_path / "failures"))
    expected = {"value": {"tag": "boolean", "value": False}, "encoded": {"boolean": False}}
    bad = {"value": {"tag": "boolean", "value": wrong}, "encoded": {"boolean": wrong}}

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["fake"], 0, json.dumps(bad), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(AssertionError):
        assert_leaf(tmp_path / "p4blo-lean", "literal", {"boolean": False}, expected)
    bundles = list((tmp_path / "failures").glob("*.json"))
    assert len(bundles) == 1
    saved = json.loads(bundles[0].read_text())
    assert same_json(saved["actual"], bad) and same_json(saved["expected"], expected)


@pytest.mark.parametrize("left, right", [(False, 0), (True, 1), (8, 8.0)])
def test_leaf_observer_requires_exact_json_types(left: object, right: object) -> None:
    assert left == right
    assert not same_json({"nested": [left]}, {"nested": [right]})


@pytest.mark.parametrize(
    "mode",
    ["timeout-bytes", "timeout-text", "oserror", "crash", "empty", "malformed", "invalid-utf8"],
)
def test_leaf_observer_retains_process_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    (tmp_path / "codec-leaves").touch()
    monkeypatch.setenv("P4BLO_CODEC_FAILURE_DIR", str(tmp_path / "failures"))
    wire = {"index": {"base": {"var": "x"}, "index": {"var": "i"}}}
    expected: dict[str, object] = {"encoded": wire}

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if mode.startswith("timeout"):
            output = b"partial\xff" if mode == "timeout-bytes" else "partial"
            raise subprocess.TimeoutExpired(["fake"], 10, output=output, stderr=b"timeout")
        if mode == "oserror":
            raise OSError("cannot launch")
        if mode == "invalid-utf8":
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        return subprocess.CompletedProcess(
            ["fake"],
            -11 if mode == "crash" else 0,
            "{" if mode == "malformed" else "",
            "crashed" if mode == "crash" else "",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(AssertionError):
        assert_leaf(tmp_path / "p4blo-lean", "expr", wire, expected)
    bundles = list((tmp_path / "failures").glob("*.json"))
    assert len(bundles) == 1
    saved = json.loads(bundles[0].read_text())
    assert same_json(saved["request"], {"kind": "expr", "wire": wire})
    assert same_json(saved["expected"], expected)
    assert saved["command"] == [str(tmp_path / "codec-leaves")]
    assert saved["timeout_seconds"] == 10
    if mode.startswith("timeout"):
        assert saved["actual"]["process_error"] == "TimeoutExpired"
        assert saved["actual"]["stdout"] == ("partial�" if mode == "timeout-bytes" else "partial")
        assert saved["stderr"] == "timeout" and saved["returncode"] is None
    elif mode == "oserror":
        assert saved["actual"]["process_error"] == "OSError"
    elif mode == "crash":
        assert saved["returncode"] == -11 and saved["stderr"] == "crashed"
    elif mode == "invalid-utf8":
        assert saved["actual"]["process_error"] == "UnicodeDecodeError"
        assert saved["actual"]["raw_bytes_hex"] == "ff"
    else:
        assert saved["actual"] == {"malformed_stdout": "{" if mode == "malformed" else ""}


@pytest.mark.parametrize(
    "kind, wire, message",
    [
        (
            "literal",
            {"bits": {}},
            "leaf.bits.value: expected a decimal number, got an empty string",
        ),
        (
            "literal",
            {"bits": {"value": None}},
            "leaf.bits.value: expected a decimal number, got an empty string",
        ),
        ("literal", {"bits": {"value": 0}}, "leaf.bits.value: expected a string"),
        ("type", {}, "leaf: no kind set"),
        ("literal", {"boolean": None}, "leaf: no kind set"),
        ("type", {"bits": 2**32}, "leaf.bits: 4294967296 does not fit in uint32"),
        ("type", {"stack": {"size": 2**32}}, "leaf.stack.size: 4294967296 does not fit in uint32"),
        (
            "literal",
            {"bits": {"width": 2**32, "value": "0"}},
            "leaf.bits.width: 4294967296 does not fit in uint32",
        ),
    ],
)
@pytest.mark.lean
def test_lean_agrees_leaf_rejection_profile(
    lean_binary: Path, kind: LeafKind, wire: dict[str, object], message: str
) -> None:
    # Deliberately not a full ProtoJSON acceptance-parity assertion: protobuf
    # permits empty messages and missing strings before semantic validation.
    assert_leaf(lean_binary, kind, wire, {"error": message})


@pytest.mark.lean
def test_lean_agrees_leaf_decimal_canonicalization(lean_binary: Path) -> None:
    assert_leaf(
        lean_binary,
        "literal",
        {"bits": {"width": "0008", "value": "0007"}},
        {
            "value": {"tag": "bits", "width": 8, "value": "7"},
            "encoded": {"bits": {"width": 8, "value": "7"}},
        },
    )


@pytest.mark.parametrize(
    "leaf", [leaf for _, leaf in key_leaves()], ids=[name for name, _ in key_leaves()]
)
def test_key_protobuf_known_answers(leaf: Leaf) -> None:
    value, encoded = protobuf_value(leaf.kind, leaf.wire)
    assert same_json(value, leaf.value) and same_json(encoded, leaf.wire)


@pytest.mark.parametrize(
    "leaf", [leaf for _, leaf in key_leaves()], ids=[name for name, _ in key_leaves()]
)
@pytest.mark.lean
def test_lean_agrees_key_known_answers(lean_binary: Path, leaf: Leaf) -> None:
    actual = assert_leaf(lean_binary, "key", leaf.wire, {"value": leaf.value, "encoded": leaf.wire})
    encoded = actual["encoded"]
    assert isinstance(encoded, dict)
    value, canonical = protobuf_value("key", encoded)
    assert same_json(value, leaf.value) and same_json(canonical, leaf.wire)


@pytest.mark.parametrize(
    "wire, message",
    [
        ({}, "leaf: no kind set"),
        ({"exact": None}, "leaf: no kind set"),
        ({"exact": ""}, "leaf.exact: expected a decimal number, got an empty string"),
        ({"exact": 0}, "leaf.exact: expected a string"),
        ({"lpm": {}}, "leaf.lpm.value: expected a decimal number, got an empty string"),
        (
            {"lpm": {"value": None}},
            "leaf.lpm.value: expected a decimal number, got an empty string",
        ),
        (
            {"lpm": {"value": "0", "prefix_len": 2**32}},
            "leaf.lpm.prefix_len: 4294967296 does not fit in uint32",
        ),
        (
            {"lpm": {"value": "0", "prefix_len": -1}},
            "leaf.lpm.prefix_len: expected a non-negative integer",
        ),
        ({"lpm": {"value": "0", "prefix_len": True}}, "leaf.lpm.prefix_len: expected a number"),
        (
            {"ternary": {"value": "0"}},
            "leaf.ternary.mask: expected a decimal number, got an empty string",
        ),
        (
            {"ternary": {"mask": "0"}},
            "leaf.ternary.value: expected a decimal number, got an empty string",
        ),
        (
            {"ternary": {"value": "0", "mask": None}},
            "leaf.ternary.mask: expected a decimal number, got an empty string",
        ),
        (
            {"ternary": {"value": None, "mask": "0"}},
            "leaf.ternary.value: expected a decimal number, got an empty string",
        ),
        ({"ternary": {"value": "0", "mask": 0}}, "leaf.ternary.mask: expected a string"),
    ],
)
@pytest.mark.lean
def test_lean_agrees_key_rejection_profile(
    lean_binary: Path, wire: dict[str, object], message: str
) -> None:
    assert_leaf(lean_binary, "key", wire, {"error": message})


@pytest.mark.parametrize(
    "wire, value, encoded",
    [
        ({"exact": "0007"}, {"tag": "exact", "value": "7"}, {"exact": "7"}),
        (
            {"lpm": {"value": "0007", "prefix_len": None}},
            {"tag": "lpm", "value": "7", "prefix_len": 0},
            {"lpm": {"value": "7"}},
        ),
        (
            {"lpm": {"value": "0007", "prefix_len": "0032"}},
            {"tag": "lpm", "value": "7", "prefix_len": 32},
            {"lpm": {"value": "7", "prefix_len": 32}},
        ),
        (
            {"ternary": {"value": "0003", "mask": "0012"}},
            {"tag": "ternary", "value": "3", "mask": "12"},
            {"ternary": {"value": "3", "mask": "12"}},
        ),
    ],
)
@pytest.mark.lean
def test_lean_agrees_key_normalization(
    lean_binary: Path, wire: dict[str, object], value: dict[str, object], encoded: dict[str, object]
) -> None:
    actual = assert_leaf(lean_binary, "key", wire, {"value": value, "encoded": encoded})
    actual_encoded = actual["encoded"]
    assert isinstance(actual_encoded, dict)
    observed, canonical = protobuf_value("key", actual_encoded)
    assert same_json(observed, value) and same_json(canonical, encoded)


@pytest.mark.parametrize("position", ["exact", "lpm.value", "ternary.value", "ternary.mask"])
@pytest.mark.parametrize("spelling", ["-1", "0x1", "١"])
@pytest.mark.lean
def test_lean_agrees_key_rejects_nondecimal_spelling(
    lean_binary: Path, position: str, spelling: str
) -> None:
    wire: dict[str, object]
    if position == "exact":
        wire = {"exact": spelling}
    elif position == "lpm.value":
        wire = {"lpm": {"value": spelling}}
    else:
        field = position.split(".")[1]
        fields = {"value": "0", "mask": "0", field: spelling}
        wire = {"ternary": fields}
    assert_leaf(
        lean_binary,
        "key",
        wire,
        {"error": f'leaf.{position}: expected a decimal number, got "{spelling}"'},
    )
