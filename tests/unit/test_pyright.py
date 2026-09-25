"""The eDSL's static guarantees, tested through pyright.

docs/design.md ("Python eDSL") promises that pyright rejects a mistyped
width, field, state, action, table or extern call. This suite makes that a
tested property rather than a claim: every file under
tests/pyright/must_pass must type-check with zero errors, and every file
under tests/pyright/must_fail must fail for exactly the reasons its header
names, one `# expect: <rule> [line N]` comment per expected diagnostic.
The directory is excluded from the project-wide pyright run
(pyproject.toml) and checked here under its own tests/pyright/pyrightconfig.json,
so the must_fail files are seen only by this suite.

A must_pass file is also a program: it is imported, built and validated
here. Type-checking it alone would leave the one construct the design
puts at run time by accepted deviation -- a sub-block call's arguments --
checked nowhere.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from p4blo import validator
from p4blo.edsl import EdslError, Program, bit8

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "tests" / "pyright"
CONFIG = SUITE / "pyrightconfig.json"
MUST_PASS = sorted((SUITE / "must_pass").glob("*.py"))
MUST_FAIL = sorted((SUITE / "must_fail").glob("*.py"))
EXPECT = re.compile(r"^#\s*expect:\s*(?P<rule>\w+)(?:\s+line\s+(?P<line>\d+))?\s*$")


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    severity: str
    line: int
    """1-based; pyright's JSON is 0-based."""
    message: str

    def __str__(self) -> str:
        return f"{self.rule} line {self.line}: {self.message.splitlines()[0]}"


@dataclass(frozen=True)
class Expectation:
    rule: str
    line: int | None

    def matches(self, diagnostic: Diagnostic) -> bool:
        return diagnostic.rule == self.rule and self.line in (None, diagnostic.line)

    def __str__(self) -> str:
        return self.rule if self.line is None else f"{self.rule} line {self.line}"


def pyright_command() -> list[str] | None:
    """How to run pyright: the `pyright` package of this interpreter's
    environment, else one on the path, else nothing."""
    if importlib.util.find_spec("pyright") is not None:
        return [sys.executable, "-m", "pyright"]
    found = shutil.which("pyright")
    return [found] if found else None


@pytest.fixture(scope="module")
def diagnostics() -> dict[Path, list[Diagnostic]]:
    """Everything pyright reports on the suite, by file, from one run over
    all of it. The run uses the suite's own config, because pyproject.toml
    excludes the suite and pyright skips an excluded file even when it is
    named on the command line; it resolves imports against this
    interpreter, so it sees the same `p4blo` the tests do."""
    command = pyright_command()
    if command is None:
        pytest.skip("pyright is not installed")
    files = MUST_PASS + MUST_FAIL
    options = ["--outputjson", "--project", str(CONFIG), "--pythonpath", sys.executable]
    try:
        run = subprocess.run(
            [*command, *options, *map(str, files)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as e:
        pytest.skip(f"pyright is not runnable: {e}")
    start = run.stdout.find("{")
    if start < 0:
        pytest.skip(f"pyright produced no JSON: {run.stderr.strip() or run.stdout.strip()}")
    report = json.loads(run.stdout[start:])
    by_file: dict[Path, list[Diagnostic]] = {file: [] for file in files}
    for d in report["generalDiagnostics"]:
        file = Path(d["file"]).resolve()
        if file in by_file:
            by_file[file].append(
                Diagnostic(
                    d.get("rule") or "<no rule>",
                    d["severity"],
                    d["range"]["start"]["line"] + 1,
                    d["message"],
                )
            )
    return by_file


def errors_of(file: Path, diagnostics: dict[Path, list[Diagnostic]]) -> list[Diagnostic]:
    """The errors pyright reports on `file`."""
    return [d for d in diagnostics[file] if d.severity == "error"]


def import_fixture(file: Path) -> ModuleType:
    """A fixture module, executed: its `program` is what it declares."""
    spec = importlib.util.spec_from_file_location(f"pyright_fixture_{file.stem}", file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expectations(file: Path) -> list[Expectation]:
    found = []
    for line in file.read_text().splitlines():
        m = EXPECT.match(line)
        if m:
            found.append(Expectation(m["rule"], int(m["line"]) if m["line"] else None))
    return found


@pytest.mark.parametrize("file", MUST_PASS, ids=lambda f: f.stem)
def test_must_pass_has_no_errors(file: Path, diagnostics: dict[Path, list[Diagnostic]]) -> None:
    errors = errors_of(file, diagnostics)
    assert not errors, "\n".join(map(str, errors))


@pytest.mark.parametrize("file", MUST_PASS, ids=lambda f: f.stem)
def test_must_pass_builds_and_validates(file: Path) -> None:
    """Every must_pass file declares a `program` that builds into IR the
    validator accepts. Pyright never runs a file; this does."""
    program = import_fixture(file).program
    assert isinstance(program, Program)
    assert validator.validate(program.build()) == []


@pytest.mark.parametrize("file", MUST_FAIL, ids=lambda f: f.stem)
def test_must_fail_fails_for_the_named_reasons(
    file: Path, diagnostics: dict[Path, list[Diagnostic]]
) -> None:
    expected = expectations(file)
    assert expected, f"{file.name} names no `# expect:` diagnostic"
    errors = errors_of(file, diagnostics)
    missing = [e for e in expected if not any(e.matches(d) for d in errors)]
    unexpected = [d for d in errors if not any(e.matches(d) for e in expected)]
    report = [
        *(f"missing: {e}" for e in missing),
        *(f"unexpected: {d}" for d in unexpected),
        *(f"reported: {d}" for d in errors),
    ]
    assert not missing and not unexpected, "\n".join(report)


def test_the_project_wide_run_does_not_see_the_suite() -> None:
    """A must_fail file must never fail `uv run pyright` or `ruff check`."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        tool = tomllib.load(f)["tool"]
    assert "tests/pyright" in tool["pyright"]["exclude"]
    assert "tests/pyright" in tool["ruff"]["extend-exclude"]


def test_an_expression_has_no_truth_value() -> None:
    """`if hdr.ipv4.ttl == 1:` is the one mistake pyright cannot see: a
    comparison is a `Bool` expression, and Python asks it for a truth value.
    The design's answer is a `__bool__` that raises and names the cause."""
    ttl = bit8(1)
    with pytest.raises(EdslError):
        if ttl == 1:
            pass
    with pytest.raises(EdslError):
        bool(ttl)
