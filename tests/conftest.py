"""Shared executable gate for all Lean conformance suites."""

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
