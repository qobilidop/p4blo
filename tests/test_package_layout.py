"""Guard the ownership split without depending on cached build outputs."""

import tomllib
from pathlib import Path

from p4blo.drt.run import default_lean_binary
from p4blo.v0 import p4blo_pb2 as pb
from tests import test_corpus, test_oracle, test_oracle_bmv2

ROOT = Path(__file__).resolve().parents[1]


def test_specification_executable_location() -> None:
    assert default_lean_binary().parent == ROOT / "ir/.lake/build/bin"
    assert not (ROOT / "proto").exists()


def test_lean_package_dependency_is_one_way() -> None:
    spec = tomllib.loads((ROOT / "ir/lakefile.toml").read_text())
    library = tomllib.loads((ROOT / "lean/lakefile.toml").read_text())
    assert spec["name"] == "p4blo-ir"
    assert not spec.get("require")
    assert library["require"] == [{"name": "p4blo-ir", "path": "../ir"}]
    assert "ProofAudit" in spec["defaultTargets"]
    assert spec["testDriver"]
    assert library["testDriver"]
    assert (ROOT / "ir/lean-toolchain").read_bytes() == (ROOT / "lean/lean-toolchain").read_bytes()


def test_schema_descriptor_identity_survives_move() -> None:
    assert pb.DESCRIPTOR.name == "p4blo/v0/p4blo.proto"
    assert (ROOT / "ir/proto" / pb.DESCRIPTOR.name).is_file()


def test_shared_corpus_discovery_is_not_empty() -> None:
    corpus = ROOT / "tests/corpus"
    programs = sorted(corpus.glob("*/*.txtpb"))
    vectors = sorted(corpus.glob("*/*.stf"))
    assert len(programs) >= 10
    assert len(vectors) >= 15
    assert all(p.with_suffix(".py").is_file() for p in programs)
    assert test_corpus.PROGRAMS == sorted(p.parent for p in programs)
    assert test_corpus.VECTORS == vectors
    assert test_oracle.VECTORS == vectors
    assert test_oracle_bmv2.VECTORS == vectors
    assert "register_bounds/bounds.stf" in test_oracle_bmv2.KNOWN_DIVERGENCES
    assert not (ROOT / "corpus").exists()
    assert not (ROOT / "oracle").exists()
