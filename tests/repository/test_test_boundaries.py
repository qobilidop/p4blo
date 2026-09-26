"""Keep test discovery and shared support independent of test-module imports."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def imported_tests(source: str) -> list[str]:
    """Find imported test modules, including imports inside helper functions."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules = [name.name for name in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [f"{node.module or ''}.{name.name}" for name in node.names]
        else:
            continue
        found.extend(
            name for name in modules if any(p.startswith("test_") for p in name.split("."))
        )
    return found


def test_no_test_module_is_another_suites_dependency() -> None:
    paths = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "tests", "impl/python/tests"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\0")
    wrong = {
        path: imports
        for path in paths
        if path.endswith(".py") and (imports := imported_tests((ROOT / path).read_text()))
    }
    assert not wrong


def test_import_guard_rejects_nested_and_aliased_dependencies() -> None:
    assert imported_tests("from tests.support import packets") == []
    assert imported_tests("from tests.programs import test_corpus as corpus")
    assert imported_tests("def helper():\n    import tests.codec.test_leaves as leaves")
