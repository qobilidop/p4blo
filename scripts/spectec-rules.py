"""Extract P4-SpecTec's rule inventory into a tracked fixture.

    uv run python scripts/spectec-rules.py [--check]

The deviation ledger in docs/ir-semantics.md cites P4-SpecTec by the names
of its relations, rules, functions and syntax productions. Those citations
must resolve at the pinned commit, and the test that checks them must run
without an OCaml toolchain, so the inventory is a committed JSON file,
tests/oracle/spectec-rules.json, regenerated from the pinned checkout by
this script. `--check` compares instead of writing and exits non-zero on
drift, which is how tests/test_spectec_rules.py uses it when a checkout at
the pin is available.

Only the architecture-free sections are inventoried: everything under
spec/ except 9-arch. The kinds and their spellings in the watsup sources:

    syntax NAME            a syntax production (`syntax typeIR = ...`)
    relation NAME          a relation declaration
    rule REL/NAME          one inference rule, possibly inside a rulegroup
    rulegroup REL/NAME     a named group of rules for one construct
    dec $NAME              a function declaration (definitions follow as `def`)

Each item records its section (the directory), file and line. Names are
the identifiers only; a rule's name includes its relation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "oracle" / "spectec-rules.json"
BUILD_SCRIPT = ROOT / "tests" / "oracle" / "build.sh"
DEFAULT_ORACLE_DIR = Path.home() / ".cache" / "p4blo" / "p4-spectec"
EXCLUDED_SECTIONS = {"9-arch"}

ITEM = re.compile(
    r"^\s*(?P<kind>syntax|relation|rule|rulegroup|dec)\s+"
    r"(?P<name>\$?[A-Za-z_][A-Za-z0-9_'-]*(?:/[A-Za-z0-9_'-]+)?)"
)


def pinned_commit() -> str:
    """The commit tests/oracle/build.sh pins, the single source of the pin."""
    for line in BUILD_SCRIPT.read_text(encoding="utf-8").splitlines():
        if line.startswith("P4_SPECTEC_COMMIT="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{BUILD_SCRIPT} has no P4_SPECTEC_COMMIT line")


def inventory(spec: Path) -> list[dict[str, Any]]:
    """Every declaration in the architecture-free sections, sorted."""
    items: list[dict[str, Any]] = []
    for path in sorted(spec.rglob("*.watsup")):
        section = path.relative_to(spec).parts[0]
        if section in EXCLUDED_SECTIONS:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = ITEM.match(line)
            if match is None:
                continue
            kind, name = match.group("kind"), match.group("name")
            if kind == "dec" and not name.startswith("$"):
                continue
            items.append(
                {
                    "kind": kind,
                    "name": name,
                    "section": section,
                    "file": path.relative_to(spec).as_posix(),
                    "line": number,
                }
            )
    items.sort(
        key=lambda item: (
            str(item["kind"]),
            str(item["name"]),
            str(item["file"]),
            int(item["line"]),
        )
    )
    return items


def render(commit: str, items: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in items:
        counts[str(item["kind"])] = counts.get(str(item["kind"]), 0) + 1
    head = {
        "commit": commit,
        "sections_excluded": sorted(EXCLUDED_SECTIONS),
        "counts": dict(sorted(counts.items())),
    }
    # One item per line: a diff at a pin bump reads as added and removed names.
    lines = [json.dumps(item, separators=(",", ":")) for item in items]
    return json.dumps(head)[:-1] + ', "items": [\n' + ",\n".join(lines) + "\n]}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--oracle-dir",
        type=Path,
        default=None,
        help="the P4-SpecTec checkout (default: build.sh's)",
    )
    parser.add_argument(
        "--check", action="store_true", help="compare with the fixture instead of writing it"
    )
    args = parser.parse_args(argv)

    root = args.oracle_dir or Path(os.environ.get("P4BLO_ORACLE_DIR") or DEFAULT_ORACLE_DIR)
    root = root.expanduser().resolve()
    commit = pinned_commit()
    head = (
        (root / ".p4blo-built").read_text(encoding="utf-8").strip()
        if (root / ".p4blo-built").is_file()
        else ""
    )
    if head != commit:
        print(
            f"{root} is not built at the pinned commit {commit} (stamp: {head or 'none'})",
            file=sys.stderr,
        )
        return 2
    text = render(commit, inventory(root / "spec"))
    if args.check:
        if not FIXTURE.is_file() or FIXTURE.read_text(encoding="utf-8") != text:
            print(
                f"{FIXTURE} differs from the inventory of {root}; rerun without --check",
                file=sys.stderr,
            )
            return 1
        print(f"{FIXTURE} matches {root} at {commit}")
        return 0
    FIXTURE.write_text(text, encoding="utf-8")
    print(f"wrote {FIXTURE} from {root} at {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
