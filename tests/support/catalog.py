"""Shared corpus and oracle input inventories, independent of pytest collection."""

from pathlib import Path

from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests/programs/corpus"
PROGRAMS = sorted(p for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())
VECTORS = sorted(v for p in PROGRAMS for v in p.glob("*.stf"))
ORACLE_VECTORS = sorted([*VECTORS, *(ROOT / "tests/programs/examples").glob("*/*.stf")])


def program_of(vector: Path) -> Path:
    """The unique IR text file accompanying a vector."""
    programs = sorted(vector.parent.glob("*.txtpb"))
    assert len(programs) == 1, f"{vector.parent} should hold exactly one .txtpb"
    return programs[0]


def golden(program_dir: Path) -> apb.BlockAssembly:
    return arch_wire.load_text(program_dir / f"{program_dir.name}.txtpb")
