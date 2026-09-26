"""Regression for dispatching monomorphic extern names by their first segment."""

from pathlib import Path

import pytest

from p4blo.arch import v1model
from p4blo.arch.builder import AssemblyBuilder
from p4blo.arch.externs import declarations as externs
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, scalar_program
from p4blo.drt.run import compare_program
from p4blo.edsl import core
from p4blo.v0 import p4blo_pb2 as pb


def family_program(suffix: str) -> apb.BlockAssembly:
    p = scalar_program(bits(8, 42), 8)
    declarations = AssemblyBuilder("declarations")
    register = externs.register(declarations, core.bit(8), f"register{suffix}")
    counter = externs.counter(declarations, f"counter{suffix}")
    checksum = externs.checksum16(declarations, core.bit(16), f"checksum16{suffix}")
    instances = [
        declarations.extern_instance("r", register, 2),
        declarations.extern_instance("c", counter, 2),
        declarations.extern_instance("s", checksum),
    ]
    p.extern_types.extend(t.build() for t in (register, counter, checksum))
    p.extern_instances.extend(i.build() for i in instances)
    return p


@pytest.mark.parametrize("suffix", ["", ".8", ".multiple.dots"])
def test_python_dispatches_existing_families(suffix: str) -> None:
    assert set(v1model.load(family_program(suffix)).externs) == {"r", "c", "s"}


@pytest.mark.parametrize("suffix", ["", ".8", ".multiple.dots"])
def test_lean_agrees_on_existing_extern_families(suffix: str, lean_binary: Path) -> None:
    report = compare_program(family_program(suffix), [Case(pb.Entries(), 0, b"")], 4, [lean_binary])
    assert report.passed, (report.summary(), report.divergences)
