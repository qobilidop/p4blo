"""Generated-artifact checks fail closed without needing Buf or network access."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check-generated.py"
PYTHON = "impl/python/p4blo/v0/example_pb2.py"
STUB = "impl/python/p4blo/v0/example_pb2.pyi"
EXPECTED = {PYTHON: b"generated python\n", STUB: b"generated stub\n"}


@pytest.fixture
def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_generated", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(root: Path, files: dict[str, bytes]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def stage(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "add", "--", "."], check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository with spaces"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
    write(root, EXPECTED)
    stage(root)
    return root


def fake_generator(tmp_path: Path, files: dict[str, bytes], exit_code: int = 0) -> tuple[str, ...]:
    script = tmp_path / "fake_buf.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "assert sys.argv[1:3] == ['generate', '--output']\n"
        "output = Path(sys.argv[3])\n"
        "assert output.is_absolute() and output != Path.cwd()\n"
        "assert not list(output.iterdir())\n"
        f"for name, content in {files!r}.items():\n"
        "    path = output / name\n"
        "    path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    path.write_bytes(content)\n"
        f"raise SystemExit({exit_code})\n"
    )
    return (sys.executable, str(script))


def test_fresh_generation_matches_both_copies(
    checker: ModuleType, repository: Path, tmp_path: Path
) -> None:
    # Unrelated hand-written package files are outside the generated inventory.
    write(repository, {"impl/python/p4blo/__init__.py": b"hand-written\n"})
    assert checker.check(repository, generator=fake_generator(tmp_path, EXPECTED)) == []
    assert (repository / "impl/python/p4blo/__init__.py").read_bytes() == b"hand-written\n"


@pytest.mark.parametrize("missing", [PYTHON, STUB])
def test_missing_generated_file_is_rejected(
    checker: ModuleType, repository: Path, tmp_path: Path, missing: str
) -> None:
    (repository / missing).unlink()
    stage(repository)
    failures = checker.check(repository, generator=fake_generator(tmp_path, EXPECTED))
    assert failures == [f"index: missing {missing}", f"working tree: missing {missing}"]
    assert not (repository / missing).exists(), "the check must not regenerate in place"


def test_untracked_new_generated_file_is_rejected(
    checker: ModuleType, repository: Path, tmp_path: Path
) -> None:
    new_file = "impl/python/another_package/new_pb2.py"
    expected = EXPECTED | {new_file: b"new output\n"}
    write(repository, expected)
    assert checker.check(repository, generator=fake_generator(tmp_path, expected)) == [
        f"index: missing {new_file}"
    ]


def test_staged_drift_cannot_hide_behind_matching_worktree(
    checker: ModuleType, repository: Path, tmp_path: Path
) -> None:
    write(repository, {STUB: b"wrong staged output\n"})
    stage(repository)
    write(repository, EXPECTED)
    assert checker.check(repository, generator=fake_generator(tmp_path, EXPECTED)) == [
        f"index: content differs for {STUB}"
    ]


def test_local_edits_are_rejected_and_preserved(
    checker: ModuleType, repository: Path, tmp_path: Path
) -> None:
    write(repository, {PYTHON: b"local edit\n"})
    assert checker.check(repository, generator=fake_generator(tmp_path, EXPECTED)) == [
        f"working tree: content differs for {PYTHON}"
    ]
    assert (repository / PYTHON).read_bytes() == b"local edit\n"


@pytest.mark.parametrize("tracked", [False, True])
def test_obsolete_generated_output_is_rejected(
    checker: ModuleType, repository: Path, tmp_path: Path, tracked: bool
) -> None:
    old = "impl/python/retired/old_pb2.pyi"
    write(repository, {old: b"obsolete\n"})
    if tracked:
        stage(repository)
    expected = ([f"index: obsolete {old}"] if tracked else []) + [f"working tree: obsolete {old}"]
    assert checker.check(repository, generator=fake_generator(tmp_path, EXPECTED)) == expected


def test_empty_generation_is_not_success(
    checker: ModuleType, repository: Path, tmp_path: Path
) -> None:
    assert checker.check(repository, generator=fake_generator(tmp_path, {})) == [
        "generator produced no *_pb2.py or *_pb2.pyi files under impl/python"
    ]


def test_generator_failure_is_not_a_comparison_pass(
    checker: ModuleType, repository: Path, tmp_path: Path
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as failure:
        checker.check(repository, generator=fake_generator(tmp_path, EXPECTED, exit_code=9))
    assert failure.value.returncode == 9
