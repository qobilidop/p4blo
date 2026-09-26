"""Shared test inputs and checks; no test-module dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LEDGER = ROOT / "docs" / "ir-semantics.md"

FIELDS = ("P4", "SpecTec", "Lean", "Python", "Test", "Class")

CLASSES = ("same", "refines undefined", "deviates", "not representable")

NON_ENTRY_SECTIONS = frozenset({"How to read an entry", "Decimal values at the JSON boundary"})

HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.*?)\s*$")

TOP_BULLET = re.compile(r"^- (?P<text>.*)$")

BOLD_START = re.compile(r"^\*\*(?P<name>.+?)\*\*")

SUB_ITEM = re.compile(r"^  - (?P<key>[A-Za-z0-9]+):\s*(?P<value>.*)$")

BACKTICKED = re.compile(r"`([^`]+)`")


@dataclass
class Entry:
    name: str
    line: int
    section: str
    fields: list[tuple[str, str]] = field(default_factory=list)

    def get(self, key: str) -> str:
        for k, v in self.fields:
            if k == key:
                return v
        raise KeyError(key)

    def where(self) -> str:
        return f"docs/ir-semantics.md:{self.line} ({self.name})"


@cache
def ledger_lines() -> tuple[str, ...]:
    return tuple(LEDGER.read_text(encoding="utf-8").splitlines())


@cache
def entries() -> tuple[Entry, ...]:
    """Every entry of the semantics sections, with its sub-list lines."""
    found: list[Entry] = []
    section = ""
    current: Entry | None = None
    stray: list[str] = []
    for number, line in enumerate(ledger_lines(), start=1):
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
            bold = BOLD_START.match(bullet.group("text"))
            if bold is None:
                stray.append(f"docs/ir-semantics.md:{number}: a bullet without a bold name")
                current = None
                continue
            current = Entry(bold.group("name"), number, section)
            found.append(current)
            continue
        sub = SUB_ITEM.match(line)
        if sub and current is not None:
            current.fields.append((sub.group("key"), sub.group("value").strip()))
        elif line.startswith("  - ") and current is not None:
            stray.append(f"docs/ir-semantics.md:{number}: a sub-list line without a field name")
        elif line and not line.startswith(" ") and current is not None:
            # Unindented text ends the entry.
            current = None
    assert not stray, "\n".join(stray)
    return tuple(found)
