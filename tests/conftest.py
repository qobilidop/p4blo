"""Shared executable gate for all Lean conformance suites, and the oracle marker.

Modules that drive an external oracle (the P4-SpecTec simulator, its
coverage probe, the IL export, or BMv2) are marked `oracle` here by name,
so that `scripts/check.sh` can deselect them with `-m "not oracle"`. They
take a quarter of an hour once the oracle is built locally, and CI runs
them in their own workflows. `P4BLO_ALL_TESTS=1 scripts/check.sh` runs
everything.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from p4blo import ir
from p4blo.drt.run import LeanRunner, default_lean_binary


@pytest.fixture(scope="session")
def lean_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    binary = default_lean_binary()
    if not binary.exists():
        if os.environ.get("P4BLO_REQUIRE_LEAN") == "1":
            pytest.fail(f"required Lean executable is missing: {binary}")
        pytest.skip(f"{binary} is not built (run scripts/check-lean.sh)")
    root = Path(__file__).resolve().parents[1]
    program = ir.load_text(root / "tests/corpus/forwarder/forwarder.txtpb")
    program_json = tmp_path_factory.mktemp("lean") / "forwarder.json"
    program_json.write_text(ir.dump_json(program))
    reason = LeanRunner.probe([binary], program_json, 4)
    if reason is not None:
        pytest.fail(f"p4blo-lean has no working `run` mode: {reason}")
    return binary


ORACLE_MODULES = {
    "test_oracle",
    "test_oracle_generated",
    "test_oracle_block",
    "test_oracle_bmv2",
    "test_bmv2_readback",
    "test_frontend_spectec",
    "test_spectec_coverage",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.stem in ORACLE_MODULES:
            item.add_marker(pytest.mark.oracle)
