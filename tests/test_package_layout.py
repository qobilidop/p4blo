"""Guard the ownership split without depending on cached build outputs."""

import tomllib
from pathlib import Path

from p4blo.drt.run import default_lean_binary
from p4blo.v0 import p4blo_pb2 as pb
from tests import test_corpus, test_oracle, test_oracle_bmv2

ROOT = Path(__file__).resolve().parents[1]


def test_specification_executable_location() -> None:
    assert default_lean_binary().parent == ROOT / "spec/ir/.lake/build/bin"
    assert not (ROOT / "proto").exists()


def test_lean_package_dependency_is_one_way() -> None:
    spec = tomllib.loads((ROOT / "spec/ir/lakefile.toml").read_text())
    library = tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())
    assert spec["name"] == "p4blo-ir"
    assert library["name"] == "p4blo"
    assert not spec.get("require")
    assert library["require"] == [{"name": "p4blo-ir", "path": "../../spec/ir"}]
    assert "P4bloIR" in {lib["name"] for lib in spec["lean_lib"]}
    assert "P4blo" in {lib["name"] for lib in library["lean_lib"]}
    assert "P4bloIR" in spec["defaultTargets"]
    assert "P4blo" in library["defaultTargets"]
    assert (ROOT / "spec/ir/P4bloIR.lean").is_file()
    assert (ROOT / "spec/ir/P4bloIR/IR.lean").is_file()
    assert (ROOT / "impl/lean/P4blo.lean").is_file()
    assert (ROOT / "impl/lean/P4blo/Scalar.lean").is_file()
    for old in (
        "spec/ir/P4blo",
        "spec/ir/P4blo.lean",
        "impl/lean/P4bloLean",
        "impl/lean/P4bloLean.lean",
    ):
        assert not (ROOT / old).exists()
    assert {"ProofAudit", "CodecProofAudit", "codec-leaves"} <= set(spec["defaultTargets"])
    assert "CodecProofAudit" in {lib["name"] for lib in spec["lean_lib"]}
    assert {exe["name"]: exe["root"] for exe in spec["lean_exe"]}["codec-leaves"] == (
        "Tests.CodecLeaves"
    )
    assert spec["testDriver"]
    assert library["testDriver"]
    assert (ROOT / "spec/ir/lean-toolchain").read_bytes() == (
        ROOT / "impl/lean/lean-toolchain"
    ).read_bytes()


def test_schema_descriptor_identity_survives_move() -> None:
    assert pb.DESCRIPTOR.name == "p4blo/v0/p4blo.proto"
    assert (ROOT / "spec/ir/proto" / pb.DESCRIPTOR.name).is_file()


def test_shared_corpus_discovery_is_not_empty() -> None:
    corpus = ROOT / "tests/corpus"
    programs = sorted(corpus.glob("*/*.txtpb"))
    vectors = sorted(corpus.glob("*/*.stf"))
    assert len(programs) >= 10
    assert len(vectors) >= 15
    assert all(p.with_suffix(".py").is_file() for p in programs)
    assert test_corpus.PROGRAMS == sorted(p.parent for p in programs)
    assert test_corpus.VECTORS == vectors
    example_vectors = sorted((ROOT / "tests/examples").glob("*/*.stf"))
    assert example_vectors, "public application vectors must reach both oracles"
    assert test_oracle.VECTORS == sorted(vectors + example_vectors)
    assert test_oracle_bmv2.VECTORS == sorted(vectors + example_vectors)
    assert "register_bounds/bounds.stf" in test_oracle_bmv2.KNOWN_DIVERGENCES
    assert not (ROOT / "corpus").exists()
    assert not (ROOT / "oracle").exists()
