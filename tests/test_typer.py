"""One expression typer: the validator's, which everything else calls.

`p4blo.validator.typer` is the only code that computes an expression's
type. The validator types while it checks; the interpreter
(`p4blo.interp.widths.type_of`), the printer and the STF reader type a
checked program through `expr_type`. This test guards that seam: over
every corpus program, every public example and a sample of generated
programs, every expression the validator types, in the scope and action
it stands in, gets the same type from the interpreter's entry point.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from pathlib import Path

import pytest

from p4blo import ir
from p4blo import validator as v
from p4blo.drt.families import FAMILIES, sample
from p4blo.interp.widths import type_of
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.names import Scope
from p4blo.validator.typer import Typer
from tests.examples import catalog

CORPUS = Path(__file__).resolve().parent / "corpus"
SEEDS = range(20)


def programs() -> Iterator[tuple[str, pb.Program]]:
    for path in sorted(CORPUS.glob("*/*.txtpb")):
        yield f"corpus/{path.stem}", ir.load_text(path)
    for name in catalog.NAMES:
        yield f"example/{name}", catalog.build(name)
    for family, profile, seed in itertools.product(FAMILIES, ("lean", "spectec"), SEEDS):
        yield f"drt/{family}/{profile}/{seed}", sample(family, seed, profile).program


PROGRAMS = list(programs())


class _Recorder(v._Validator):  # pyright: ignore[reportPrivateUsage]
    """The validator, keeping every expression it types and the type."""

    def __init__(self, program: pb.Program) -> None:
        super().__init__(program)
        self.typed: list[tuple[pb.Expr, Scope, pb.Type]] = []

    def type_of(self, expr: pb.Expr, scope: Scope, path: str) -> pb.Type | None:
        t = Typer.type_of(self, expr, scope, path)
        if t is not None:
            self.typed.append((expr, scope, t))
        return t


@pytest.mark.parametrize(("name", "program"), PROGRAMS, ids=[n for n, _ in PROGRAMS])
def test_the_validator_and_the_interpreter_type_alike(name: str, program: pb.Program) -> None:
    recorder = _Recorder(program)
    assert recorder.run() == [], name
    assert recorder.typed, name
    index = recorder.idx
    for expr, scope, t in recorder.typed:
        action = scope.action.name if scope.action is not None else None
        assert type_of(expr, index, scope.names, action) == t, (name, str(expr))
