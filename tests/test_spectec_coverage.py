"""Every in-scope P4-SpecTec rule is exercised by p4blo's inputs or excluded with a reason.

tests/oracle/spectec-coverage.json is the measurement tests/oracle/coverage.py
makes on the pinned simulator: which items of the rule inventory
(tests/oracle/spectec-rules.json) fire when the corpus and examples run.
tests/oracle/spectec-coverage-exclusions.json is written by hand: every
in-scope item that does not fire, with a category and a reason. In scope are
the rules of 8-dynamic and the functions of 3-operations.

Without any OCaml toolchain this checks that both fixtures name the pinned
commit, that the report joins the inventory, that every in-scope item is hit
or excluded, and that no exclusion is stale. With the oracle and the coverage
probe built at the pin, the report is also regenerated and compared, which
takes about fifteen seconds and runs in the oracle CI job; elsewhere that test
skips and says why.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "tests" / "oracle" / "spectec-coverage.json"
EXCLUSIONS = ROOT / "tests" / "oracle" / "spectec-coverage-exclusions.json"
INVENTORY = ROOT / "tests" / "oracle" / "spectec-rules.json"
SCRIPT = ROOT / "tests" / "oracle" / "coverage.py"
COVERAGE_DOC = ROOT / "docs" / "coverage.md"

sys.path.insert(0, str(ROOT))
from tests.oracle import coverage  # noqa: E402

CATEGORIES = {"architecture", "excluded-construct", "not-representable", "unhit"}
Key = tuple[str, str, str, int]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def key(item: dict[str, Any]) -> Key:
    return (str(item["kind"]), str(item["name"]), str(item["file"]), int(item["line"]))


def in_scope(item: dict[str, Any]) -> bool:
    """The rules of 8-dynamic and the functions of 3-operations."""
    return (item["kind"], item["section"]) in {("rule", "8-dynamic"), ("dec", "3-operations")}


def coverage_rows() -> set[str]:
    """The first cells of docs/coverage.md's construct tables, backticks removed."""
    rows: set[str] = set()
    for line in COVERAGE_DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith(("| IL construct", "| Status")):
            rows.add(line.split("|")[1].strip().replace("`", ""))
    return rows


def test_fixtures_name_the_pinned_commit() -> None:
    pin = coverage.pinned_commit()
    assert load(REPORT)["commit"] == pin
    assert load(EXCLUSIONS)["commit"] == pin
    assert load(INVENTORY)["commit"] == pin


def test_report_joins_the_inventory() -> None:
    inventory = {key(i) for i in load(INVENTORY)["items"] if i["kind"] in coverage.KINDS}
    reported = [key(i) for i in load(REPORT)["items"]]
    assert len(reported) == len(set(reported)), "an item is reported twice"
    assert set(reported) == inventory, "the report and the inventory list different items"


def test_every_in_scope_item_is_hit_or_excluded() -> None:
    excluded = {key(e) for e in load(EXCLUSIONS)["exclusions"]}
    missing = [
        f"{i['file']}:{i['line']}: {i['kind']} {i['name']}"
        for i in load(REPORT)["items"]
        if in_scope(i) and not i["hit"] and key(i) not in excluded
    ]
    assert not missing, "in scope, not hit and not excluded:\n" + "\n".join(missing)


def test_no_exclusion_is_stale() -> None:
    hit = {key(i) for i in load(REPORT)["items"] if i["hit"]}
    stale = [
        f"{e['file']}:{e['line']}: {e['name']}"
        for e in load(EXCLUSIONS)["exclusions"]
        if key(e) in hit
    ]
    assert not stale, "excluded but hit; remove the exclusion:\n" + "\n".join(stale)


def test_exclusions_are_well_formed() -> None:
    inventory = {key(i): i for i in load(INVENTORY)["items"]}
    rows = coverage_rows()
    fixture = load(EXCLUSIONS)
    assert set(fixture["categories"]) == CATEGORIES
    seen: set[Key] = set()
    problems: list[str] = []
    for entry in fixture["exclusions"]:
        where = f"{entry.get('file')}:{entry.get('line')}: {entry.get('name')}"
        k = key(entry)
        if k in seen:
            problems.append(f"{where}: listed twice")
        seen.add(k)
        item = inventory.get(k)
        if item is None:
            problems.append(f"{where}: names nothing in the inventory")
        elif not in_scope(item):
            problems.append(f"{where}: is not in scope, so needs no exclusion")
        category = entry.get("category")
        if category not in CATEGORIES:
            problems.append(f"{where}: unknown category {category!r}")
        if not str(entry.get("reason", "")).strip():
            problems.append(f"{where}: no reason")
        if category == "excluded-construct" and entry.get("row") not in rows:
            problems.append(f"{where}: row {entry.get('row')!r} is not a docs/coverage.md row")
        if category == "unhit" and not str(entry.get("reach", "")).strip():
            problems.append(f"{where}: an unhit item says which input would reach it")
    assert not problems, "\n".join(problems)


def test_report_matches_a_fresh_measurement() -> None:
    root = coverage.oracle_root()
    for problem in (coverage.checkout_problem(root), coverage.probe_problem(root)):
        if problem is not None:
            pytest.skip(problem)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        check=False,
        timeout=coverage.TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, result.stdout + result.stderr
