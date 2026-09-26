"""Real Git/event regressions for conservative heavy-CI selection."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ci-scope.py"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def write(root: Path, name: str, content: str = "new content\n") -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def commit(root: Path) -> str:
    git(root, "add", "--", ".")
    git(
        root,
        "-c",
        "user.name=CI scope fixture",
        "-c",
        "user.email=ci-scope@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-qm",
        "CI scope fixture",
    )
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repository with spaces"
    root.mkdir()
    git(root, "init", "-q")
    write(root, "README.md", "initial prose\n")
    write(root, "impl/python/core.py", "initial code\n")
    return root, commit(root)


def classify(
    root: Path,
    tmp_path: Path,
    event: object,
    event_name: str = "push",
) -> bool:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event))
    output = tmp_path / "github-output"
    output.write_text("other=value\n")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--event-path",
            str(event_path),
            "--event-name",
            event_name,
            "--github-output",
            str(output),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout in {"full=true\n", "full=false\n"}
    assert output.read_text() == "other=value\n" + result.stdout
    assert result.stderr.startswith("CI scope: ")
    return result.stdout == "full=true\n"


@pytest.mark.parametrize(
    "name",
    [
        "README.md",
        "AGENTS.md",
        "docs/design.md",
        ".agents/status.md",
        ".agents/decisions.md",
        ".agents/roadmap.md",
        ".agents/notes/plan.md",
        ".agents/reviews/nested/review.md",
        ".agents/notes/spaces and\nnewlines.md",
    ],
)
def test_narrative_only_push_skips_heavy_jobs(
    repository: tuple[Path, str], tmp_path: Path, name: str
) -> None:
    root, before = repository
    write(root, name)
    assert not classify(root, tmp_path, {"before": before, "after": commit(root)})


@pytest.mark.parametrize(
    "name",
    [
        "impl/python/core.py",
        "spec/ir/proto/p4blo/v0/p4blo.proto",
        ".github/workflows/ci.yml",
        "uv.lock",
        "docs/quickstart.md",
        "docs/ir-semantics.md",
        "docs/p4-spec-coverage.md",
        "docs/nested/unknown.md",
        "docs/code.py",
        "docs/design.md.py",
        "tests/README.md",
        "tests/conformance/mutants.py",
        "docs/UPPER.MD",
        ".agents/skills/example/SKILL.md",
        ".agents/notes/mutation.py",
        ".agents/unknown.md",
        ".agents/notes.md",
        "website/index.html",
    ],
)
def test_non_narrative_or_test_input_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path, name: str
) -> None:
    root, before = repository
    write(root, "README.md")
    write(root, name)
    assert classify(root, tmp_path, {"before": before, "after": commit(root)})


@pytest.mark.parametrize("rename", [False, True])
def test_deleted_code_or_code_renamed_to_docs_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path, rename: bool
) -> None:
    root, before = repository
    source = root / "impl/python/core.py"
    if rename:
        (root / "docs").mkdir()
        source.rename(root / "docs/retired.md")
    else:
        source.unlink()
    assert not source.exists()
    assert classify(root, tmp_path, {"before": before, "after": commit(root)})


def test_deleted_narrative_is_still_narrative(repository: tuple[Path, str], tmp_path: Path) -> None:
    root, before = repository
    (root / "README.md").unlink()
    assert not classify(root, tmp_path, {"before": before, "after": commit(root)})


@pytest.mark.parametrize("symlink", [False, True])
def test_markdown_mode_or_type_change_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path, symlink: bool
) -> None:
    root, before = repository
    path = root / "README.md"
    if symlink:
        path.unlink()
        path.symlink_to(root / "impl/python/core.py")
    else:
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    assert classify(root, tmp_path, {"before": before, "after": commit(root)})


def test_new_markdown_symlink_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path
) -> None:
    root, before = repository
    (root / "docs").mkdir()
    (root / "docs/design.md").symlink_to(root / "impl/python/core.py")
    assert classify(root, tmp_path, {"before": before, "after": commit(root)})


def test_pull_request_uses_merge_base_not_advanced_base(
    repository: tuple[Path, str], tmp_path: Path
) -> None:
    root, common = repository
    write(root, "README.md")
    head = commit(root)
    git(root, "checkout", "--detach", common)
    write(root, "impl/python/core.py", "advanced base code\n")
    base = commit(root)
    event = {"pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
    assert not classify(root, tmp_path, event, "pull_request")
    # The identical endpoints on a push include the removed base code change.
    assert classify(root, tmp_path, {"before": base, "after": head})


def test_unrelated_pull_request_history_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path
) -> None:
    root, base = repository
    git(root, "checkout", "--orphan", "unrelated")
    write(root, "README.md")
    head = commit(root)
    event = {"pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
    assert classify(root, tmp_path, event, "pull_request")


@pytest.mark.parametrize("event", [None, [], {}, {"pull_request": {}}, {"before": 42}])
@pytest.mark.parametrize("event_name", ["push", "pull_request", "workflow_dispatch", ""])
def test_unknown_or_malformed_events_require_full_scope(
    repository: tuple[Path, str], tmp_path: Path, event: object, event_name: str
) -> None:
    root, _ = repository
    assert classify(root, tmp_path, event, event_name)


@pytest.mark.parametrize("before", ["0" * 40, "f" * 40, "HEAD", "--help", "$(echo unsafe)"])
def test_missing_or_invalid_commits_require_full_scope(
    repository: tuple[Path, str], tmp_path: Path, before: str
) -> None:
    root, _ = repository
    write(root, "README.md")
    assert classify(root, tmp_path, {"before": before, "after": commit(root)})


def test_non_commit_object_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path
) -> None:
    root, head = repository
    blob = git(root, "rev-parse", "HEAD:README.md")
    assert classify(root, tmp_path, {"before": blob, "after": head})


def test_missing_head_requires_full_scope(repository: tuple[Path, str], tmp_path: Path) -> None:
    root, before = repository
    assert classify(root, tmp_path, {"before": before, "after": "0" * 40})


def test_unavailable_checkout_requires_full_scope(tmp_path: Path) -> None:
    assert classify(tmp_path, tmp_path, {"before": "a" * 40, "after": "b" * 40})


def test_empty_diff_requires_full_scope(repository: tuple[Path, str], tmp_path: Path) -> None:
    root, before = repository
    assert classify(root, tmp_path, {"before": before, "after": commit(root)})


@pytest.mark.parametrize("content", [None, "not JSON", "{", b"\xff"])
def test_unreadable_event_requires_full_scope(
    repository: tuple[Path, str], tmp_path: Path, content: str | bytes | None
) -> None:
    root, _ = repository
    event_path = tmp_path / "invalid-event.json"
    if isinstance(content, str):
        event_path.write_text(content)
    elif content is not None:
        event_path.write_bytes(content)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--event-path", str(event_path), "--event-name", "push"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "full=true\n"


def test_missing_arguments_require_full_scope(repository: tuple[Path, str]) -> None:
    root, _ = repository
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=root, check=True, capture_output=True, text=True
    )
    assert result.stdout == "full=true\n"
