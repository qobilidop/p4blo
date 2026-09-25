#!/usr/bin/env python3
"""Compare fresh protobuf generation with the index and working tree.

Buf's --output prefixes every plugin output directory, so the configured
generator can run in an empty temporary tree without overwriting local edits.
Both inventory and bytes must match: git diff alone misses untracked outputs
and in-place generation can leave obsolete outputs behind.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path("impl/python")


def is_generated(path: str) -> bool:
    return path.endswith(("_pb2.py", "_pb2.pyi"))


def working_files(root: Path) -> dict[str, bytes]:
    """Read all generated outputs, including untracked and ignored files."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted((root / OUTPUT).rglob("*"))
        if is_generated(path.name) and path.is_file()
    }


def indexed_files(root: Path) -> dict[str, bytes]:
    """Read the proposed commit's copies; an unresolved index is an error."""
    entries = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z", "--", str(OUTPUT)],
        check=True,
        capture_output=True,
    ).stdout
    files: dict[str, bytes] = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if not is_generated(path):
            continue
        mode, oid, stage = metadata.split()
        if stage != b"0" or mode not in (b"100644", b"100755"):
            raise ValueError(f"generated output is not a resolved regular file: {path}")
        files[path] = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", oid.decode("ascii")],
            check=True,
            capture_output=True,
        ).stdout
    return files


def differences(expected: dict[str, bytes], actual: dict[str, bytes], label: str) -> list[str]:
    failures = [f"{label}: missing {path}" for path in sorted(expected.keys() - actual.keys())]
    failures.extend(f"{label}: obsolete {path}" for path in sorted(actual.keys() - expected.keys()))
    failures.extend(
        f"{label}: content differs for {path}"
        for path in sorted(expected.keys() & actual.keys())
        if expected[path] != actual[path]
    )
    return failures


def check(root: Path, *, generator: tuple[str, ...] = ("buf",)) -> list[str]:
    """Generate without mutation, then check both local and staged artifacts."""
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="p4blo-generated-") as directory:
        output = Path(directory).resolve()
        subprocess.run([*generator, "generate", "--output", str(output)], cwd=root, check=True)
        expected = working_files(output)
    if not expected:
        return ["generator produced no *_pb2.py or *_pb2.pyi files under impl/python"]
    return differences(expected, indexed_files(root), "index") + differences(
        expected, working_files(root), "working tree"
    )


def main() -> int:
    try:
        failures = check(Path(__file__).resolve().parents[1])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"generated-code check failed: {error}", file=sys.stderr)
        return 1
    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(
            "Run buf generate, remove obsolete outputs, and stage generated changes.",
            file=sys.stderr,
        )
        return 1
    print("generated protobuf outputs match the index and working tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
