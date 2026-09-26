"""Real Lean execution conformance."""

from pathlib import Path

import pytest

from p4blo.drt.case import Case
from p4blo.drt.run import compare_program
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.extern_families import family_program


@pytest.mark.parametrize("suffix", ["", ".8", ".multiple.dots"])
def test_lean_agrees_on_existing_extern_families(suffix: str, lean_binary: Path) -> None:
    report = compare_program(family_program(suffix), [Case(pb.Entries(), 0, b"")], 4, [lean_binary])
    assert report.passed, (report.summary(), report.divergences)
