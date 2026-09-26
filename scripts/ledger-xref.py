"""Write the ledger's cross-reference table, docs/ledger-xref.md.

    uv run python scripts/ledger-xref.py [--check]

Every entry of the deviation ledger in docs/ir-semantics.md cites the P4
section, the P4-SpecTec rules, the Lean definitions, the Python functions
and the tests of one behavior. This script lays those citations out as
one table, a row per entry in the ledger's order, so that a reader can
go from a behavior to each of the five in one hop. SpecTec names link to
their line in the pinned P4-SpecTec source, found through the committed
rule inventory tests/oracles/spectec-rules.json; tests link to their
files. `--check` compares instead of writing and exits non-zero on
drift, which is how tests/repository/test_ledger_xref.py keeps the table
true.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "ir-semantics.md"
TABLE = ROOT / "docs" / "ledger-xref.md"
INVENTORY = ROOT / "tests/oracles/spectec-rules.json"
SPECTEC_REPO = "https://github.com/kaist-plrg/p4-spectec"

FIELDS = ("P4", "SpecTec", "Lean", "Python", "Test", "Class")
CLASSES = ("same", "refines undefined", "deviates", "not representable")
# Sections of the ledger that hold no entries, as tests/repository/test_ledger.py
# has them.
NON_ENTRY_SECTIONS = frozenset({"How to read an entry", "Decimal values at the JSON boundary"})
# When one name is several kinds of SpecTec item, link the most specific.
KIND_ORDER = ("rule", "rulegroup", "relation", "dec", "syntax")

HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.*?)\s*$")
TOP_BULLET = re.compile(r"^- \*\*(?P<name>.+?)\*\*")
SUB_ITEM = re.compile(r"^  - (?P<key>[A-Za-z0-9]+):\s*(?P<value>.*)$")
BACKTICKED = re.compile(r"`([^`]+)`")


@dataclass
class Entry:
    name: str
    section: str
    fields: dict[str, str] = field(default_factory=dict)


def entries(text: str) -> list[Entry]:
    """The ledger's entries in order, parsed as tests/repository/test_ledger.py does."""
    found: list[Entry] = []
    section = ""
    current: Entry | None = None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            current = None
            if len(heading.group(1)) == 2:
                section = heading.group("title")
            continue
        if section == "" or section in NON_ENTRY_SECTIONS:
            continue
        bullet = TOP_BULLET.match(line)
        if bullet:
            current = Entry(bullet.group("name"), section)
            found.append(current)
            continue
        sub = SUB_ITEM.match(line)
        if sub and current is not None:
            current.fields[sub.group("key")] = sub.group("value").strip()
        elif line and not line.startswith(" "):
            current = None
    for entry in found:
        if tuple(entry.fields) != FIELDS:
            raise SystemExit(f"ledger entry {entry.name!r} has lines {list(entry.fields)}")
    return found


def anchor(title: str) -> str:
    """GitHub's anchor for a heading."""
    return re.sub(r"[^a-z0-9 _-]", "", title.lower()).replace(" ", "-")


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def spectec_links(inventory: dict[str, object]) -> dict[str, str]:
    commit = inventory["commit"]
    items = inventory["items"]
    assert isinstance(commit, str) and isinstance(items, list)
    best: dict[str, tuple[int, str]] = {}
    for item in items:
        rank = KIND_ORDER.index(item["kind"])
        url = f"{SPECTEC_REPO}/blob/{commit}/spec/{item['file']}#L{item['line']}"
        if item["name"] not in best or rank < best[item["name"]][0]:
            best[item["name"]] = (rank, url)
    return {name: url for name, (_, url) in best.items()}


def names(value: str) -> str:
    """The backticked names of a line as code, or the line itself when it
    names none (`none` and its reason)."""
    found = BACKTICKED.findall(value)
    if not found:
        return cell(value)
    return ", ".join(f"`{cell(n)}`" for n in found)


def spectec(value: str, links: dict[str, str]) -> str:
    found = BACKTICKED.findall(value)
    if not found:
        return cell(value)
    return ", ".join(f"[`{cell(n)}`]({links[n]})" if n in links else f"`{cell(n)}`" for n in found)


def tests(value: str) -> str:
    """Test references grouped by file, each file a link relative to docs/."""
    groups: dict[str, list[str]] = {}
    for reference in BACKTICKED.findall(value):
        path, _, function = reference.partition("::")
        groups.setdefault(path, [])
        if function:
            groups[path].append(function)
    parts: list[str] = []
    for path, functions in groups.items():
        label = path.removeprefix("tests/")
        link = f"[{cell(label)}](../{path})"
        if functions:
            link += " " + ", ".join(f"`{cell(f)}`" for f in functions)
        parts.append(link)
    return "<br>".join(parts)


def render(ledger: list[Entry], links: dict[str, str]) -> str:
    lines = [
        "# Ledger cross-reference",
        "",
        "Every entry of the deviation ledger in [ir-semantics.md](ir-semantics.md),",
        "in the ledger's order, with the five places it is decided, implemented",
        "and checked: the P4-16 specification section, the P4-SpecTec rules (each",
        "linked to its line at the pinned commit), the Lean definitions under",
        "`spec/ir/P4bloIR/`, the Python functions in `p4blo`, and the tests. The",
        "entry's name links to its section of the ledger, which holds the",
        "choice, the reason and the class sentence.",
        "",
        "This page is generated by `uv run python scripts/ledger-xref.py` from the",
        "ledger; do not edit it by hand. `tests/repository/test_ledger_xref.py`",
        "fails when it differs from what the script writes.",
        "",
        "| Entry | Class | P4 | SpecTec | Lean | Python | Tests |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in ledger:
        f = entry.fields
        kind = next(c for c in CLASSES if f["Class"].startswith(c))
        name = entry.name.rstrip(".")
        row = [
            f"[{cell(name)}](ir-semantics.md#{anchor(entry.section)})",
            kind,
            cell(f["P4"]),
            spectec(f["SpecTec"], links),
            names(f["Lean"]),
            names(f["Python"]),
            tests(f["Test"]),
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def generate() -> str:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return render(entries(LEDGER.read_text(encoding="utf-8")), spectec_links(inventory))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check", action="store_true", help="compare with the committed table instead"
    )
    args = parser.parse_args(argv)
    text = generate()
    if args.check:
        current = TABLE.read_text(encoding="utf-8") if TABLE.is_file() else ""
        if current != text:
            print(
                f"{TABLE.relative_to(ROOT)} is stale; rerun scripts/ledger-xref.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TABLE.relative_to(ROOT)} matches the ledger")
        return 0
    TABLE.write_text(text, encoding="utf-8")
    print(f"wrote {TABLE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
