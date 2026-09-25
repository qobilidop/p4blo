"""Every corpus program: it validates, its eDSL source rebuilds its golden,
and its vectors replay under the switch architecture.

A corpus program lives in `tests/corpus/<name>/` as `<name>.py` (the eDSL
source), `<name>.txtpb` (the IR golden), a README, and `*.stf` vectors.
Each vector file replays on a freshly loaded program, so extern state does
not leak between files; within a file it persists, as the vectors intend.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from p4blo import arch, ir, stf, validator
from p4blo.v0 import p4blo_pb2 as pb

CORPUS = Path(__file__).resolve().parents[2] / "tests" / "corpus"
PROGRAMS = sorted(p for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())
VECTORS = sorted(v for p in PROGRAMS for v in p.glob("*.stf"))


def golden(program_dir: Path) -> pb.Program:
    return ir.load_text(program_dir / f"{program_dir.name}.txtpb")


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
def test_vector_replays_under_the_switch(vector: Path) -> None:
    loaded = arch.reference.load(golden(vector.parent))
    statements = stf.parse(vector.read_text())
    stf.assert_replay(loaded.index, statements, arch.stf_driver(arch.Switch(ports=4), loaded))


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: f"{v.parent.name}/{v.stem}")
def test_the_filter_makes_the_same_fate_decisions(vector: Path) -> None:
    """Claim 3: every program runs under both architectures unchanged.

    The filter has no deparser, so its bytes differ from the switch's, but
    the fate is the control's decision and must agree: dropped by one is
    dropped by the other, and a forwarded packet leaves on the same port.
    Entries accumulate as the vector installs them, as in a replay.
    """
    program = golden(vector.parent)
    statements = stf.parse(vector.read_text())
    switch = arch.stf_driver(arch.Switch(ports=4), arch.reference.load(program))
    filter_ = arch.stf_driver(arch.Filter(), arch.reference.load(program))
    installed: list[stf.Statement] = []
    packets = 0
    for statement in statements:
        if isinstance(statement, stf.Add | stf.SetDefault):
            installed.append(statement)
        elif isinstance(statement, stf.Packet):
            entries = stf.to_entries(ir.Index.build(program), installed)
            by_switch = switch(entries, statement.port, statement.data)
            by_filter = filter_(entries, statement.port, statement.data)
            assert [port for port, _ in by_filter] == [port for port, _ in by_switch]
            packets += 1
    assert packets > 0
