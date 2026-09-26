"""Skip heavy CI only for a known, nonempty diff of narrative Markdown.

Python/schema checks still run for every change. A missing event, unavailable
history or any path outside this narrow allowlist requests the full CI scope.
Run from the checkout root after checkout with fetch-depth: 0.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

# These Markdown files are inputs to Lean or oracle tests, not just prose.
CHECKED_DOCS = {"docs/quickstart.md", "docs/ir-semantics.md", "docs/p4-spec-coverage.md"}
NARRATIVE_FILES = {
    "README.md",
    "AGENTS.md",
    ".agents/status.md",
    ".agents/decisions.md",
    ".agents/roadmap.md",
}


def narrative_path(name: str) -> bool:
    """Accept only the documented locations, not arbitrary Markdown files."""
    if name in NARRATIVE_FILES:
        return True
    path = PurePosixPath(name)
    if path.suffix != ".md" or name in CHECKED_DOCS:
        return False
    if len(path.parts) == 2 and path.parts[0] == "docs":
        return True
    return len(path.parts) >= 3 and path.parts[:2] in {
        (".agents", "notes"),
        (".agents", "reviews"),
    }


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def commit_id(value: object, root: Path) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", value
    ):
        raise ValueError("event has no full hexadecimal commit ID")
    # Require an actual locally available commit; zero IDs and blobs fail closed.
    return git(root, "rev-parse", "--verify", f"{value}^{{commit}}").decode("ascii").strip()


def full_scope(root: Path, event_path: Path | None, event_name: str) -> tuple[bool, str]:
    """Return the safe default on uncertainty, with a short diagnostic reason."""
    if event_name not in {"pull_request", "push"} or event_path is None:
        return True, "unknown or missing event"
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
        if event_name == "pull_request":
            pr = event.get("pull_request")
            if not isinstance(pr, dict):
                raise ValueError("missing pull request")
            base, head = pr.get("base"), pr.get("head")
            if not isinstance(base, dict) or not isinstance(head, dict):
                raise ValueError("missing pull request base or head")
            before = commit_id(base.get("sha"), root)
            after = commit_id(head.get("sha"), root)
            before = git(root, "merge-base", before, after).decode("ascii").strip()
        else:
            before = commit_id(event.get("before"), root)
            after = commit_id(event.get("after"), root)
        # Disable rename detection so deleting code and adding docs retains BOTH
        # paths. NUL separation also preserves whitespace/newlines in filenames.
        raw = git(
            root,
            "diff",
            "--no-ext-diff",
            "--ignore-submodules=none",
            "--no-renames",
            "--raw",
            "-z",
            before,
            after,
            "--",
        )
        if not raw:
            return True, "empty diff"
        if not raw.endswith(b"\0"):
            raise ValueError("unexpected diff output")
        records = raw[:-1].decode("utf-8").split("\0")
        if len(records) % 2:
            raise ValueError("unexpected diff records")
        for metadata, name in zip(records[::2], records[1::2], strict=True):
            fields = metadata.split()
            if len(fields) != 5 or not fields[0].startswith(":"):
                raise ValueError("unexpected diff metadata")
            old_mode, new_mode = fields[0][1:], fields[1]
            # Only regular, non-executable Markdown blobs qualify. Additions
            # and deletions use mode 000000 for the absent side. Symlinks,
            # executable files, submodules and type/mode changes run full CI.
            if (old_mode, new_mode) not in {
                ("100644", "100644"),
                ("000000", "100644"),
                ("100644", "000000"),
            } or fields[4] not in {"A", "D", "M"}:
                return True, "diff includes a non-regular file or mode change"
            if not narrative_path(name):
                return True, "diff includes a path outside narrative Markdown"
        return False, "all changed paths are narrative Markdown"
    except (OSError, ValueError, subprocess.SubprocessError):
        # Do not print event values or subprocess diagnostics: paths and commit
        # fields are untrusted, and outputs must contain constant booleans only.
        return True, "event or commit history unavailable or invalid"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-path", type=Path)
    parser.add_argument("--event-name", default="")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    full, reason = full_scope(Path.cwd(), args.event_path, args.event_name)
    output = "full=true\n" if full else "full=false\n"
    print(f"CI scope: {reason}", file=sys.stderr)
    if args.github_output is not None:
        # A failed output write fails this step, never silently requests a skip.
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
