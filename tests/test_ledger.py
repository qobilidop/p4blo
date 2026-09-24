"""docs/ir-semantics.md is a checkable deviation ledger.

Every entry of the semantics sections is a top-level bullet whose text
starts with a bold behavior name, followed by exactly six sub-list lines in
a fixed order: `P4:`, `SpecTec:`, `Lean:`, `Python:`, `Test:`, `Class:`.
This module checks that shape and that every name an entry cites exists:

- a `Lean:` name is a declaration (`def`, `theorem`, `structure`,
  `inductive`, `abbrev`, ...) under spec/ir/P4bloIR/, qualified by the
  namespaces it is declared in below `P4bloIR`, so `Installed.lookup`
  resolves only if `lookup` is declared inside `namespace Installed`;
- a `Python:` name is a dotted path that imports and resolves with
  `getattr`;
- a `Test:` reference is a pytest node id whose file and function exist, or
  a file or directory under the repository;
- a `Class:` line starts with one of the four classes and a sentence;
- the class counts in the summary table equal the entries' classes.

SpecTec names are checked against the pinned rule inventory by
tests/test_spectec_rules.py, which reads the same `SpecTec:` lines.
"""

from __future__ import annotations

import ast
import importlib
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "ir-semantics.md"
LEAN_DIR = ROOT / "spec" / "ir" / "P4bloIR"

FIELDS = ("P4", "SpecTec", "Lean", "Python", "Test", "Class")
CLASSES = ("same", "refines undefined", "deviates", "not representable")
# Sections of the page that hold no entries.
NON_ENTRY_SECTIONS = frozenset({"How to read an entry", "Decimal values at the JSON boundary"})

HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.*?)\s*$")
TOP_BULLET = re.compile(r"^- (?P<text>.*)$")
BOLD_START = re.compile(r"^\*\*(?P<name>.+?)\*\*")
SUB_ITEM = re.compile(r"^  - (?P<key>[A-Za-z0-9]+):\s*(?P<value>.*)$")
BACKTICKED = re.compile(r"`([^`]+)`")
CLASS_LINE = re.compile(r"^(?P<cls>" + "|".join(CLASSES) + r")\.\s+\S")
COUNT_ROW = re.compile(r"^\|\s*(?P<cls>[a-z ]+?)\s*\|\s*(?P<n>\d+)\s*\|\s*$")


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


def names_on(entry: Entry, key: str) -> list[str]:
    return BACKTICKED.findall(entry.get(key))


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_the_ledger_has_entries_in_every_semantics_section() -> None:
    found = entries()
    assert len(found) >= 46, f"only {len(found)} entries parsed"
    sections = {e.section for e in found}
    for title in ("Values and operations", "Parsers", "Tables", "Deparsers", "Externs"):
        assert title in sections, f"no entries under '{title}'"


def test_entry_names_are_unique() -> None:
    names = [e.name for e in entries()]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, f"entries named more than once: {duplicates}"


def test_every_entry_has_the_six_lines_in_order() -> None:
    wrong = [
        f"{e.where()}: {[k for k, _ in e.fields]}"
        for e in entries()
        if tuple(k for k, _ in e.fields) != FIELDS
    ]
    assert not wrong, f"entries whose lines are not {list(FIELDS)}:\n" + "\n".join(wrong)


def test_every_line_says_something() -> None:
    empty = [f"{e.where()}: {k}" for e in entries() for k, v in e.fields if not v]
    assert not empty, "empty template lines:\n" + "\n".join(empty)


def test_spectec_lines_cite_names_or_say_none() -> None:
    wrong = [
        e.where()
        for e in entries()
        if not names_on(e, "SpecTec") and not e.get("SpecTec").startswith("none")
    ]
    assert not wrong, "SpecTec lines with neither a name nor 'none':\n" + "\n".join(wrong)


def test_implementation_and_test_lines_cite_names() -> None:
    wrong = [
        f"{e.where()}: {k}"
        for e in entries()
        for k in ("Lean", "Python", "Test")
        if not names_on(e, k)
    ]
    assert not wrong, "lines without a backticked name:\n" + "\n".join(wrong)


def test_every_class_line_starts_with_a_class_and_a_sentence() -> None:
    wrong = [
        f"{e.where()}: {e.get('Class')[:40]!r}"
        for e in entries()
        if not CLASS_LINE.match(e.get("Class"))
    ]
    assert not wrong, f"Class lines must start with one of {CLASSES} and a sentence:\n" + "\n".join(
        wrong
    )


def test_the_summary_table_counts_the_entries() -> None:
    table: dict[str, int] = {}
    for line in ledger_lines():
        row = COUNT_ROW.match(line)
        if row and (row.group("cls") in CLASSES or row.group("cls") == "total"):
            table[row.group("cls")] = int(row.group("n"))
    actual = {cls: 0 for cls in CLASSES}
    for e in entries():
        match = CLASS_LINE.match(e.get("Class"))
        assert match, e.where()
        actual[match.group("cls")] += 1
    assert {k: v for k, v in table.items() if k != "total"} == actual
    assert table.get("total") == len(entries())


# ---------------------------------------------------------------------------
# Lean names
# ---------------------------------------------------------------------------

LEAN_DECL = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?"
    r"(?:(?:private|protected|noncomputable|partial|unsafe|nonrec)\s+)*"
    r"(?:def|theorem|lemma|structure|inductive|abbrev|class|instance|opaque|axiom)\s+"
    r"(?P<name>[^\s:({\[]+)"
)
LEAN_BLOCK_COMMENT = re.compile(r"/-.*?-/", re.S)
LEAN_OPEN = re.compile(r"^\s*(?P<kind>namespace|section)\b\s*(?P<name>\S*)")
LEAN_MUTUAL = re.compile(r"^\s*mutual\s*$")
LEAN_END = re.compile(r"^\s*end\b\s*(?P<name>\S*)\s*$")


@cache
def lean_declarations() -> frozenset[str]:
    """Every declaration under spec/ir/P4bloIR/, qualified by the namespaces
    it is declared in below `P4bloIR`."""
    declared: set[str] = set()
    for path in sorted(LEAN_DIR.rglob("*.lean")):
        text = LEAN_BLOCK_COMMENT.sub("", path.read_text(encoding="utf-8"))
        # Each scope contributes its namespace components, possibly none.
        scopes: list[list[str]] = []
        for raw in text.splitlines():
            line = raw.split("--", 1)[0]
            if not line.strip():
                continue
            opened = LEAN_OPEN.match(line)
            if opened:
                name = opened.group("name")
                parts = name.split(".") if opened.group("kind") == "namespace" and name else []
                scopes.append(parts)
                continue
            if LEAN_MUTUAL.match(line):
                scopes.append([])
                continue
            ended = LEAN_END.match(line)
            if ended:
                if scopes:
                    scopes.pop()
                continue
            decl = LEAN_DECL.match(line)
            if decl:
                namespace = [part for scope in scopes for part in scope]
                if namespace[:1] == ["P4bloIR"]:
                    namespace = namespace[1:]
                declared.add(".".join([*namespace, decl.group("name")]))
    return frozenset(declared)


def test_lean_declarations_are_found() -> None:
    declared = lean_declarations()
    for name in ("evaluate", "Bits.wrap", "Installed.lookup", "Execution.drive", "Value.equal"):
        assert name in declared, f"the scanner lost '{name}'"
    assert "lookup" not in declared, "a namespaced name leaked out of its namespace"


def test_every_lean_name_is_declared() -> None:
    declared = lean_declarations()
    missing = [
        f"{e.where()}: `{name}`"
        for e in entries()
        for name in names_on(e, "Lean")
        if name.removeprefix("P4bloIR.") not in declared
    ]
    assert not missing, "Lean names declared nowhere under spec/ir/P4bloIR/:\n" + "\n".join(missing)


# ---------------------------------------------------------------------------
# Python names
# ---------------------------------------------------------------------------


def resolve_python(dotted: str) -> Any:
    """The object a dotted name denotes: the longest importable module
    prefix, then attributes."""
    parts = dotted.split(".")
    if parts[0] != "p4blo":
        raise LookupError(f"'{dotted}' is not in the p4blo package")
    for split in range(len(parts), 0, -1):
        try:
            obj: Any = importlib.import_module(".".join(parts[:split]))
        except ModuleNotFoundError:
            continue
        for attribute in parts[split:]:
            obj = getattr(obj, attribute)
        return obj
    raise LookupError(dotted)


def test_every_python_name_resolves() -> None:
    missing: list[str] = []
    for e in entries():
        for name in names_on(e, "Python"):
            try:
                resolve_python(name)
            except (LookupError, AttributeError) as error:
                missing.append(f"{e.where()}: `{name}` ({error})")
    assert not missing, "Python names that do not resolve:\n" + "\n".join(missing)


def test_the_python_resolver_is_strict() -> None:
    resolve_python("p4blo.interp.tables.InstalledEntries.lookup")
    with pytest.raises(AttributeError):
        resolve_python("p4blo.interp.tables.InstalledEntries.look_up")


# ---------------------------------------------------------------------------
# Test references
# ---------------------------------------------------------------------------


@cache
def defined_names(path: Path) -> frozenset[str]:
    """`name` and `Class::name` for every function and class of a module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            for member in node.body:
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                    names.add(f"{node.name}::{member.name}")
    return frozenset(names)


def reference_problem(reference: str) -> str | None:
    """Why a `Test:` reference does not exist, or None when it does."""
    path_text, _, rest = reference.partition("::")
    path = ROOT / path_text
    if not path.resolve().is_relative_to(ROOT) or not path.exists():
        return f"no file or directory {path_text}"
    if not rest:
        return None
    if path.suffix != ".py" or not path.is_file():
        return f"{path_text} is not a Python file"
    node = re.sub(r"\[.*\]$", "", rest)
    if node not in defined_names(path):
        return f"{path_text} defines no {node}"
    return None


def test_every_test_reference_exists() -> None:
    missing = [
        f"{e.where()}: `{ref}`: {problem}"
        for e in entries()
        for ref in names_on(e, "Test")
        if (problem := reference_problem(ref)) is not None
    ]
    assert not missing, "Test references that do not exist:\n" + "\n".join(missing)


def test_the_test_resolver_is_strict() -> None:
    assert reference_problem("tests/test_ledger.py::test_the_test_resolver_is_strict") is None
    assert reference_problem("tests/corpus/stacks") is None
    assert reference_problem("tests/test_ledger.py::test_no_such_test") is not None
    assert reference_problem("tests/corpus/no_such_program") is not None
