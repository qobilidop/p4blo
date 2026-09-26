"""Check repository size and the staged/working-tree cases a disk scan misses."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_file_sizes", ROOT / "scripts/check-file-sizes.py"
)
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.STDOUT)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    git(tmp_path, "init", "--quiet")
    return tmp_path


def test_repository_files_fit_limit() -> None:
    assert CHECK.oversized(ROOT) == []


def test_empty_index_and_untracked_files(repository: Path) -> None:
    (repository / "scratch").write_bytes(b"x" * 65)
    assert CHECK.oversized(repository, limit=64) == []


@pytest.mark.parametrize("name", ["plain", "with spaces", "with\na newline", "with\ta tab"])
def test_staged_oversize_survives_working_copy_shrink(repository: Path, name: str) -> None:
    path = repository / name
    path.write_bytes(b"x" * 65)
    git(repository, "add", "--", name)
    path.write_bytes(b"x")
    assert CHECK.oversized(repository, limit=64) == [(name, 65)]
    path.unlink()
    assert not path.exists()
    assert CHECK.oversized(repository, limit=64) == [(name, 65)]


def test_exact_limit_and_unstaged_growth(repository: Path) -> None:
    path = repository / "snapshot"
    path.write_bytes(b"x" * 64)
    git(repository, "add", "--", path.name)
    assert CHECK.oversized(repository, limit=64) == []
    path.write_bytes(b"x" * 65)
    assert CHECK.oversized(repository, limit=64) == [(path.name, 65)]


def test_symlink_is_measured_without_following_target(repository: Path) -> None:
    (repository / "scratch").write_bytes(b"x" * 65)
    (repository / "link").symlink_to("scratch")
    (repository / "dangling").symlink_to("absent")
    git(repository, "add", "--", "link", "dangling")
    assert CHECK.oversized(repository, limit=64) == []
