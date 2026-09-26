"""Shared executable gate for all Lean conformance suites, and the oracle marker.

Modules that drive an external oracle (the P4-SpecTec simulator, its
coverage probe, the IL export, or BMv2) are marked `oracle` here by name,
so that `scripts/check.sh` can deselect them with `-m "not oracle"`. They
take a quarter of an hour once the oracle is built locally, and CI runs
them in their own workflows. `P4BLO_ALL_TESTS=1 scripts/check.sh` runs
everything.

The optional --ci-shard INDEX/COUNT selects a deterministic partition by test
node ID. It composes with -k and -m; without it the inventory is unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path

import pytest

from p4blo.arch import wire as arch_wire
from p4blo.drt.run import LeanRunner, default_lean_binary


@pytest.fixture(scope="session")
def lean_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    binary = default_lean_binary()
    if not binary.exists():
        if os.environ.get("P4BLO_REQUIRE_LEAN") == "1":
            pytest.fail(f"required Lean executable is missing: {binary}")
        pytest.skip(f"{binary} is not built (run scripts/check-lean.sh)")
    root = Path(__file__).resolve().parent
    program = arch_wire.load_text(root / "tests/programs/corpus/forwarder/forwarder.txtpb")
    program_json = tmp_path_factory.mktemp("lean") / "forwarder.json"
    program_json.write_text(arch_wire.dump_json(program))
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


def ci_shard(value: str) -> tuple[int, int]:
    """Parse a one-based shard index and a positive shard count."""
    message = "--ci-shard must be INDEX/COUNT with 1 <= INDEX <= COUNT"
    if re.fullmatch(r"[0-9]+/[0-9]+", value) is None:
        raise argparse.ArgumentTypeError(message)
    try:
        index, count = map(int, value.split("/"))
    except ValueError as error:
        raise argparse.ArgumentTypeError(message) from error
    if not 1 <= index <= count:
        raise argparse.ArgumentTypeError(message)
    return index, count


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--ci-shard",
        type=ci_shard,
        default=None,
        metavar="INDEX/COUNT",
        help="Select a stable SHA256(nodeid) shard (one-based); default: all tests",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # Mark before either our shard selection or pytest's -m/-k selection so
    # every deselection observer sees the same oracle classification.
    for item in items:
        # BMv2 tests also live in mixed modules; the BMv2 workflow selects
        # them by name (`-k bmv2`), so the name is the rule here too.
        if item.path.stem in ORACLE_MODULES or "bmv2" in item.name:
            item.add_marker(pytest.mark.oracle)
    shard: tuple[int, int] | None = config.getoption("ci_shard")
    if shard is None:
        return
    index, count = shard
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        slot = int.from_bytes(hashlib.sha256(item.nodeid.encode("utf-8")).digest(), "big") % count
        (selected if slot == index - 1 else deselected).append(item)
    items[:] = selected
    if deselected:
        config.hook.pytest_deselected(items=deselected)
