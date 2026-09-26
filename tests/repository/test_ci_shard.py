"""Collect real pytest items to check shard coverage, stability and selection hooks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

CONFTEST = Path(__file__).resolve().parents[2] / "conftest.py"


@pytest.fixture
def suite(tmp_path: Path) -> Path:
    """Use the production hooks with cheap parametrized and oracle-marked items."""
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    oracle: external oracle\n    lean: Lean\n"
        "    spectec: P4-SpecTec\n    bmv2: BMv2\n"
    )
    observer = """
import json

_deselected = []


def _describe(item):
    return {"nodeid": item.nodeid, "oracle": item.get_closest_marker("oracle") is not None}


def pytest_deselected(items):
    _deselected.extend(_describe(item) for item in items)


def pytest_collection_finish(session):
    path = Path(__file__).resolve().parent / "inventory.json"
    path.write_text(json.dumps({
        "selected": [_describe(item) for item in session.items],
        "deselected": _deselected,
    }))
"""
    (tmp_path / "conftest.py").write_text(CONFTEST.read_text() + observer)
    (tmp_path / "test_cases.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.parametrize('value', range(40))\n"
        "@pytest.mark.lean\n"
        "def test_lean_agrees_case(value, lean_binary):\n    pass\n\n"
        "def test_python_case():\n    pass\n\n"
        "@pytest.mark.bmv2\n"
        "def test_bmv2_case():\n    pass\n"
    )
    (tmp_path / "test_oracle.py").write_text(
        "import pytest\n@pytest.mark.spectec\ndef test_spectec_case():\n    pass\n"
    )
    return tmp_path


def run_collection(suite: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTEST_ADDOPTS", None)
    # Hash randomization must not affect cross-process shard membership.
    environment["PYTHONHASHSEED"] = "random"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        cwd=suite,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def collect(suite: Path, *args: str) -> dict[str, Any]:
    result = run_collection(suite, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((suite / "inventory.json").read_text())


def nodeids(inventory: dict[str, Any], group: str = "selected") -> set[str]:
    return {item["nodeid"] for item in inventory[group]}


def test_default_inventory_is_disjoint_union_of_stable_shards(suite: Path) -> None:
    whole = collect(suite)
    first = collect(suite, "--ci-shard", "1/2")
    second = collect(suite, "--ci-shard", "2/2")
    repeated = collect(suite, "--ci-shard", "1/2")
    reversed_files = collect(suite, "--ci-shard", "1/2", "test_oracle.py", "test_cases.py")
    assert len(nodeids(whole)) == 43
    assert not whole["deselected"]
    assert nodeids(first) and nodeids(second)
    assert nodeids(first).isdisjoint(nodeids(second))
    assert nodeids(first) | nodeids(second) == nodeids(whole)
    assert first == repeated
    assert nodeids(first) == nodeids(reversed_files)
    assert nodeids(first, "deselected") == nodeids(second)
    assert nodeids(second, "deselected") == nodeids(first)
    assert nodeids(collect(suite, "--ci-shard", "1/1")) == nodeids(whole)


def test_marker_selection_commutes_with_sharding(suite: Path) -> None:
    matching = nodeids(collect(suite, "-m", "lean"))
    assert len(matching) == 40
    selected: list[set[str]] = []
    for shard in ("1/2", "2/2"):
        unfiltered = nodeids(collect(suite, "--ci-shard", shard))
        filtered = collect(suite, "--ci-shard", shard, "-m", "lean")
        assert nodeids(filtered) == unfiltered & matching
        assert len(filtered["selected"]) + len(filtered["deselected"]) == 43
        selected.append(nodeids(filtered))
    assert selected[0].isdisjoint(selected[1])
    assert selected[0] | selected[1] == matching


def test_oracle_marks_precede_sharding_and_marker_selection(suite: Path) -> None:
    expected = {"test_cases.py::test_bmv2_case", "test_oracle.py::test_spectec_case"}
    whole = collect(suite, "-m", "oracle")
    assert nodeids(whole) == expected
    first = collect(suite, "--ci-shard", "1/2")
    all_items = first["selected"] + first["deselected"]
    assert {item["nodeid"] for item in all_items if item["oracle"]} == expected
    without_oracles = collect(suite, "--ci-shard", "1/2", "-m", "not oracle")
    assert nodeids(without_oracles) == nodeids(first) - expected


@pytest.mark.parametrize(
    "shard", ["", "1", "1/", "/2", "a/2", "1/2/3", "0/2", "1/0", "3/2", "-1/2", "1/ 2"]
)
def test_invalid_shards_are_usage_errors(suite: Path, shard: str) -> None:
    result = run_collection(suite, f"--ci-shard={shard}")
    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert "--ci-shard must be INDEX/COUNT with 1 <= INDEX <= COUNT" in result.stderr
    assert not (suite / "inventory.json").exists()


@pytest.mark.parametrize("marker", ["lean", "oracle"])
def test_bad_dependency_marks_fail_before_deselection(suite: Path, marker: str) -> None:
    (suite / "test_hidden.py").write_text(
        f"import pytest\n@pytest.mark.{marker}\ndef test_hidden():\n    pass\n"
    )
    result = run_collection(suite, "-m", "not lean and not oracle")
    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert "test_hidden.py::test_hidden" in result.stderr
    assert "dependency" in result.stderr


def test_missing_lean_marker_fails_even_in_native_selection(suite: Path) -> None:
    (suite / "test_hidden.py").write_text("def test_hidden(lean_binary):\n    pass\n")
    result = run_collection(suite, "-m", "lean")
    assert result.returncode == pytest.ExitCode.USAGE_ERROR
    assert "lean marker must match lean_binary dependency" in result.stderr
