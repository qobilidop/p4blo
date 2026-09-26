"""Every corpus program: it validates, its eDSL source rebuilds its golden,
and its vectors replay under the v1model architecture.

A corpus program lives in `tests/programs/corpus/<name>/` as `<name>.py` (the eDSL
source), `<name>.txtpb` (the IR golden), a README, and `*.stf` vectors.
Each vector file replays on a freshly loaded program, so extern state does
not leak between files; within a file it persists, as the vectors intend.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from p4blo import arch, stf
from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb

CORPUS = Path(__file__).resolve().parents[2] / "tests/programs/corpus"
PROGRAMS = sorted(p for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())
VECTORS = sorted(v for p in PROGRAMS for v in p.glob("*.stf"))


def golden(program_dir: Path) -> apb.BlockAssembly:
    return arch_wire.load_text(program_dir / f"{program_dir.name}.txtpb")


@pytest.mark.parametrize("program_dir", PROGRAMS, ids=lambda p: p.name)
def test_program_validates(program_dir: Path) -> None:
    assert validator.validate(golden(program_dir)) == []


@pytest.mark.parametrize("program_dir", PROGRAMS, ids=lambda p: p.name)
def test_edsl_source_rebuilds_the_golden(program_dir: Path) -> None:
    source = program_dir / f"{program_dir.name}.py"
    if not source.exists():
        pytest.skip("no eDSL source yet")
    spec = importlib.util.spec_from_file_location(program_dir.name, source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build() == golden(program_dir)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: f"{v.parent.name}/{v.stem}")
def test_vector_replays_under_v1model(vector: Path) -> None:
    loaded = v1model.load(golden(vector.parent))
    statements = stf.parse(vector.read_text())
    stf.assert_replay(loaded.index, statements, arch.stf_driver(v1model.V1Model(ports=4), loaded))
