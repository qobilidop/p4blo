#!/usr/bin/env python3
"""Reject tracked files above 5 MiB in either the index or working tree.

Adapted from p4-spectec-lean's repository-size guard. Untracked artifacts
are outside this check; stage new deliverables before running the gate.
"""

import os
import subprocess
import sys
from pathlib import Path

LIMIT = 5 * 1024 * 1024


def oversized(root: Path, limit: int = LIMIT) -> list[tuple[str, int]]:
    """Check staged blobs even if their working copies are smaller or deleted."""
    entries = subprocess.check_output(["git", "-C", str(root), "ls-files", "--stage", "-z"]).split(
        b"\0"
    )
    files: list[tuple[bytes, str]] = []
    for entry in entries:
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, oid, _stage = metadata.split()
        if mode != b"160000":  # A submodule's contents belong to its own repository.
            files.append((oid, os.fsdecode(name)))
    sizes = subprocess.check_output(
        ["git", "-C", str(root), "cat-file", "--batch-check=%(objectsize)"],
        input=b"".join(oid + b"\n" for oid, _ in files),
    ).splitlines()
    failures: list[tuple[str, int]] = []
    for (_, name), stored in zip(files, sizes, strict=True):
        try:
            working = (root / name).lstat().st_size
        except FileNotFoundError:
            working = 0
        size = max(int(stored), working)
        if size > limit:
            failures.append((name, size))
    return failures


def main() -> int:
    failures = oversized(Path(__file__).resolve().parents[1])
    for name, size in failures:
        print(
            f"[file-size] {name!r}: {size} bytes exceeds {LIMIT}; "
            "use reproducible generation, a small compressed snapshot, "
            "or a checksum-pinned external artifact"
        )
    if not failures:
        print("[file-size] all tracked files are at most 5 MiB")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
