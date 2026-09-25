"""Lean's validity checker against the Python validator.

`p4blo-lean check` runs `P4bloIR.Validity.check`, whose acceptance the Lean
side proves sound for `Valid` and which progress builds on. This test
requires the two validators to agree on which programs are valid, over
every corpus program, every public example, a sample of generated
programs from the DRT families, and every program `tests/unit/test_validator.py`
hands to `validator.validate`: its base program and each program it breaks
in one place.

On a rejected program the first codes must correspond. The Lean checker
stops at the first problem and uses the Python codes, so the table below
is the identity except where a problem cannot reach it: a oneof with no
kind, an unspecified enum or a non-decimal literal fails Lean's decoder
first, which the command reports as `DECODE`. Decoding precedes checking,
so `DECODE` corresponds to a wire problem anywhere in Python's list.
"""

from __future__ import annotations

import inspect
import itertools
import json
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from p4blo import ir
from p4blo import validator as v
from p4blo.drt.families import FAMILIES, sample
from p4blo.v0 import p4blo_pb2 as pb
from tests.unit import test_validator
from tests.examples import catalog

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "corpus"
# Generated programs per family and profile; the families' own campaigns run
# 200 seeds each against the interpreters, so a sample of their shapes here.
SEEDS = range(40)

DECODE = "DECODE"
# The type of `pytest.param(...)`, which pytest does not export.
PARAM: Any = type(pytest.param(None))

# Python's code to the Lean codes that may name the same first problem.
CODES: dict[str, frozenset[str]] = {
    code: frozenset({code})
    for code in [
        v.NAME_EMPTY,
        v.NAME_DUPLICATE,
        v.ERROR_LIST,
        v.REF_UNRESOLVED,
        v.REF_KIND,
        v.SCOPE_VAR,
        v.SCOPE_DECL,
        v.EXPORT_DUPLICATE,
        v.EXPORT_SIGNATURE,
        v.LITERAL_RANGE,
        v.PARSER_START_STATE,
        v.BLOCK_KIND_STMT,
        v.PARSER_ONLY,
        v.NEXT_ONLY_EXTRACT,
        v.TYPE_MISMATCH,
        v.CAST_INVALID,
        v.SLICE_RANGE,
        v.LVALUE_READONLY,
        v.STACK_COUNT,
        v.ARG_COUNT,
        v.ARG_TYPE,
        v.CALL_KIND,
        v.CALL_ALIAS,
        v.CALL_CYCLE,
        v.EXTERN_RESULT,
        v.SELECT_ARITY,
        v.KEY_NAME,
        v.TABLE_LPM_COUNT,
        v.TABLE_KEY_MIX,
        v.TABLE_ACTIONS,
        v.NOACTION_RESERVED,
        v.ACTION_ARGS,
        v.ENTRY_RANGE,
        v.ENTRY_PRIORITY,
        v.ENTRY_DUPLICATE,
        v.EXTERN_ARGS,
    ]
} | {
    # Wire problems: the proto allows them, the Lean IR cannot hold them.
    v.EXPR_INVALID: frozenset({DECODE}),  # no kind, unspecified operator
    v.STMT_INVALID: frozenset({DECODE}),  # no kind
    v.LITERAL_FORMAT: frozenset({DECODE}),  # no value, not decimal
    v.PARSER_TRANSITION: frozenset({DECODE}),  # no transition, target without kind
    # Codes that name a wire problem as well as a checked one.
    v.TYPE_INVALID: frozenset({v.TYPE_INVALID, DECODE}),  # type with no kind
    v.BLOCK_KIND_SHAPE: frozenset({v.BLOCK_KIND_SHAPE, DECODE}),  # block with no kind
    v.PARAM_DIRECTION: frozenset({v.PARAM_DIRECTION, DECODE}),  # unspecified direction
    v.ARG_DIRECTION: frozenset({v.ARG_DIRECTION, DECODE}),  # argument with no kind
    v.SELECT_TYPE: frozenset({v.SELECT_TYPE, DECODE}),  # key set with no kind
    v.KEY_TYPE: frozenset({v.KEY_TYPE, DECODE}),  # unspecified match kind
    v.ENTRY_SHAPE: frozenset({v.ENTRY_SHAPE, DECODE}),  # no kind, not decimal
}


def test_the_table_covers_every_code() -> None:
    documented = {name for name in dir(v) if name.isupper() and isinstance(getattr(v, name), str)}
    assert set(CODES) == documented


@dataclass(frozen=True)
class Case:
    name: str
    program: pb.Program


def positive_cases() -> Iterator[Case]:
    for path in sorted(CORPUS.glob("*/*.txtpb")):
        yield Case(f"corpus/{path.stem}", ir.load_text(path))
    for name in catalog.NAMES:
        yield Case(f"example/{name}", catalog.build(name))
    for family, profile, seed in itertools.product(FAMILIES, ("lean", "spectec"), SEEDS):
        yield Case(f"drt/{family}/{profile}/{seed}", sample(family, seed, profile).program)


def _parameter_sets(fn: Callable[..., Any]) -> list[dict[str, Any]] | None:
    """Every keyword set pytest would call `fn` with, or None when it needs
    a fixture."""
    marks: list[Any] = [m for m in getattr(fn, "pytestmark", []) if m.name == "parametrize"]
    axes: list[list[dict[str, Any]]] = []
    for mark in marks:
        spec: Any = mark.args[0]
        names: list[str] = (
            [n.strip() for n in spec.split(",")] if isinstance(spec, str) else list(spec)
        )
        values: list[dict[str, Any]] = []
        for raw in mark.args[1]:
            value: Any = raw.values if isinstance(raw, PARAM) else raw
            if isinstance(raw, PARAM) and len(names) == 1:
                value = value[0]
            values.append(
                dict(zip(names, value, strict=True)) if len(names) > 1 else {names[0]: value}
            )
        axes.append(values)
    sets = [
        dict(itertools.chain.from_iterable(d.items() for d in combo))
        for combo in itertools.product(*axes)
    ]
    wanted = set(inspect.signature(fn).parameters)
    if any(set(s) != wanted for s in sets):
        return None
    return sets


def validator_cases() -> list[Case]:
    """Every program `tests/unit/test_validator.py` validates, recorded by
    running its tests with `validator.validate` wrapped."""
    recorded: list[Case] = []
    original = v.validate
    current = ""

    def record(program: pb.Program) -> list[v.Diagnostic]:
        copy = pb.Program()
        copy.CopyFrom(program)
        recorded.append(Case(f"{current}#{len(recorded)}", copy))
        return original(program)

    v.validate = record  # type: ignore[assignment]
    try:
        for name, fn in inspect.getmembers(test_validator, inspect.isfunction):
            if not name.startswith("test_") or name == "test_corpus_programs_validate":
                continue
            sets = _parameter_sets(fn)
            if sets is None:
                continue
            for i, kwargs in enumerate(sets):
                current = f"test_validator/{name}[{i}]"
                fn(**kwargs)
    finally:
        v.validate = original  # type: ignore[assignment]
    return recorded


def lean_verdicts(lean: Path, programs: list[pb.Program], tmp: Path) -> list[str]:
    paths = []
    for i, program in enumerate(programs):
        path = tmp / f"p{i}.json"
        path.write_text(ir.dump_json(program))
        paths.append(str(path))
    lines: list[str] = []
    # A bounded command line: a few hundred paths per call.
    for start in range(0, len(paths), 200):
        chunk = paths[start : start + 200]
        run = subprocess.run([lean, "check", *chunk], capture_output=True, text=True, timeout=600)
        assert run.returncode in (0, 1), run.stderr
        out = run.stdout.splitlines()
        assert len(out) == len(chunk), run.stdout + run.stderr
        lines += out
    return lines


def lean_code(line: str) -> str | None:
    return None if line == "accept" else line.split()[1]


def corresponds(diagnostics: list[v.Diagnostic], code: str | None) -> bool:
    """Lean's first code names Python's first problem. Decoding precedes
    checking, so a wire problem Python lists later is Lean's first, and so
    is one Python never reaches because a failed index stops it."""
    if code == DECODE:
        stopped = diagnostics[0].code in (v.NAME_EMPTY, v.NAME_DUPLICATE)
        return stopped or any(DECODE in CODES[d.code] for d in diagnostics)
    return code in CODES[diagnostics[0].code]


def compare(cases: list[Case], lean: Path, tmp: Path) -> list[str]:
    """Every disagreement, as a sentence."""
    verdicts = lean_verdicts(lean, [c.program for c in cases], tmp)
    problems: list[str] = []
    for case, line in zip(cases, verdicts, strict=True):
        diagnostics = v.validate(case.program)
        code = lean_code(line)
        if not diagnostics and code is not None:
            problems.append(f"{case.name}: Python accepts, Lean says {line}")
        elif diagnostics and code is None:
            problems.append(f"{case.name}: Lean accepts, Python says {diagnostics[0]}")
        elif diagnostics and not corresponds(diagnostics, code):
            problems.append(f"{case.name}: Python's first is {diagnostics[0]}, Lean says {line}")
    return problems


def test_lean_agrees_validity_on_valid_programs(lean_binary: Path, tmp_path: Path) -> None:
    cases = list(positive_cases())
    assert len(cases) > 100
    assert compare(cases, lean_binary, tmp_path) == []


def test_lean_agrees_validity_on_the_validator_tests(lean_binary: Path, tmp_path: Path) -> None:
    cases = validator_cases()
    rejected = [c for c in cases if v.validate(c.program)]
    # The base program, the accepted variants, and one break per rule.
    assert len(rejected) > 150
    assert {d.code for c in rejected for d in v.validate(c.program)} == set(CODES)
    assert compare(cases, lean_binary, tmp_path) == []


def test_lean_agrees_validity_on_the_rule_each_validator_test_targets(
    lean_binary: Path, tmp_path: Path
) -> None:
    """A validator test breaks one rule on a well-formed wire program, so
    Lean reaches that rule instead of stopping in its decoder: `DECODE` is
    accepted only where Python also names a wire problem, never through
    `corresponds`'s allowance for an index failure that hides one."""
    cases = validator_cases()
    verdicts = lean_verdicts(lean_binary, [c.program for c in cases], tmp_path)
    hidden = [
        case.name
        for case, line in zip(cases, verdicts, strict=True)
        if lean_code(line) == DECODE
        and not any(DECODE in CODES[d.code] for d in v.validate(case.program))
    ]
    assert hidden == []


def test_csum16_fixture_is_the_golden() -> None:
    """`spec/arch/P4bloArchTest/NonVacuity.lean` writes csum16 as a Lean term,
    and the Lean tests check that term against this fixture; the fixture
    must be the corpus golden."""
    fixture = ROOT / "spec/arch/P4bloArchTest/fixtures/csum16.json"
    golden = ir.load_text(CORPUS / "csum16" / "csum16.txtpb")
    assert json.loads(fixture.read_text()) == json.loads(ir.dump_json(golden))
