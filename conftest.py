"""Shared Lean fixture, explicit dependency categories and deterministic CI shards.

Specialist tests declare lean, spectec, bmv2 or p4c markers at their definitions.
The oracle category is the union of the three external P4 dependencies.
--ci-shard INDEX/COUNT composes with pytest marker selection.
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
    # Derive only a category union; filenames and function names imply nothing.
    for item in items:
        if any(item.get_closest_marker(name) for name in ("spectec", "bmv2", "p4c")):
            item.add_marker(pytest.mark.oracle)
        markers = {mark.name for mark in item.iter_markers()}
        fixtures = set(getattr(item, "fixturenames", ()))
        if ("lean" in markers) != ("lean_binary" in fixtures):
            raise pytest.UsageError(f"{item.nodeid}: lean marker must match lean_binary dependency")
        if "oracle" in markers and not markers.intersection({"spectec", "bmv2", "p4c"}):
            raise pytest.UsageError(f"{item.nodeid}: oracle requires a specific dependency marker")
        package_tests = Path(__file__).resolve().parent / "impl/python/tests"
        if item.path.is_relative_to(package_tests) and markers.intersection({"lean", "oracle"}):
            raise pytest.UsageError(f"{item.nodeid}: package tests must require no native tools")
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
