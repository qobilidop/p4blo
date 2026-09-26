"""Guard the ownership split without depending on cached build outputs."""

import subprocess
import tomllib
from pathlib import Path

from p4blo.drt.run import default_lean_binary
from p4blo.v0 import p4blo_pb2 as pb
from tests.support import catalog

ROOT = Path(__file__).resolve().parents[2]


def test_specification_executable_location() -> None:
    assert default_lean_binary().parent == ROOT / "spec/arch/.lake/build/bin"
    assert not (ROOT / "proto").exists()


def test_lean_package_dependency_is_one_way() -> None:
    spec = tomllib.loads((ROOT / "spec/ir/lakefile.toml").read_text())
    arch = tomllib.loads((ROOT / "spec/arch/lakefile.toml").read_text())
    assert spec["name"] == "p4blo-ir"
    assert arch["name"] == "p4blo-arch"
    # The IR spec depends on nothing; the executable architecture adapter
    # depends on the IR. Nothing architectural lives in the IR spec.
    assert not spec.get("require")
    assert arch["require"] == [{"name": "p4blo-ir", "path": "../ir"}]
    assert "P4bloIR" in {lib["name"] for lib in spec["lean_lib"]}
    assert "P4bloArch" in {lib["name"] for lib in arch["lean_lib"]}
    assert "P4bloIR" in spec["defaultTargets"]
    assert "P4bloArch" in arch["defaultTargets"]
    assert "p4blo-lean" not in {exe["name"] for exe in spec["lean_exe"]}
    assert {exe["name"]: exe["root"] for exe in arch["lean_exe"]}["p4blo-lean"] == "Main"
    assert not (ROOT / "spec/ir/P4bloIR/Switch.lean").exists()
    assert not (ROOT / "spec/ir/P4bloIR/V1Model.lean").exists()
    assert not (ROOT / "spec/arch/P4bloArch/Switch.lean").exists()
    assert (ROOT / "spec/arch/P4bloArch/V1Model.lean").is_file()
    assert (ROOT / "spec/arch/P4bloArch/Externs.lean").is_file()
    assert (ROOT / "spec/ir/P4bloIR.lean").is_file()
    assert (ROOT / "spec/ir/P4bloIR/IR.lean").is_file()
    for old in (
        "impl/lean",
        "spec/ir/P4blo",
        "spec/ir/P4blo.lean",
        "impl/lean/P4bloLean",
        "impl/lean/P4bloLean.lean",
    ):
        assert not (ROOT / old).exists()
    assert {"P4bloIRTest", "codec-leaves"} <= set(spec["defaultTargets"])
    assert "P4bloIRTest" in {lib["name"] for lib in spec["lean_lib"]}
    assert {exe["name"]: exe["root"] for exe in spec["lean_exe"]}["codec-leaves"] == (
        "P4bloIRTest.CodecLeaves"
    )
    assert spec["testDriver"]
    assert arch["testDriver"]
    toolchain = (ROOT / "spec/ir/lean-toolchain").read_bytes()
    assert (ROOT / "spec/arch/lean-toolchain").read_bytes() == toolchain


# Each Lean package's root module, and the tracked entries its root may hold
# beyond the layout's own: each package's wire schema.
LEAN_PACKAGES = {
    "spec/ir": ("P4bloIR", {"proto"}),
    "spec/arch": ("P4bloArch", {"proto"}),
}


def test_lean_package_roots_follow_the_layout() -> None:
    """Importable modules under `<Root>/`, gate-only ones under `<Root>Test/`
    as one default-target library, and at the root only what Lake needs."""
    for package, (root, extra) in LEAN_PACKAGES.items():
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", package],
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
        top = {Path(p.decode()).relative_to(package).parts[0] for p in tracked if p}
        required = {
            f"{root}.lean",
            root,
            f"{root}Test",
            "lakefile.toml",
            "lean-toolchain",
            "lake-manifest.json",
            "README.md",
        }
        assert required <= top, package
        assert top - required <= {"Main.lean"} | extra, package
        config = tomllib.loads((ROOT / package / "lakefile.toml").read_text())
        libraries = {lib["name"]: lib for lib in config["lean_lib"]}
        assert set(libraries) == {root, f"{root}Test"}, package
        assert libraries[f"{root}Test"]["globs"] == [f"{root}Test.+"], package
        assert {root, f"{root}Test"} <= set(config["defaultTargets"]), package
        executables = {exe["name"]: exe["root"] for exe in config["lean_exe"]}
        assert executables[config["testDriver"]] == f"{root}Test.Main", package
        outside = [r for r in executables.values() if not r.startswith(f"{root}Test.")]
        assert outside == (["Main"] if "Main.lean" in top else []), package
    for audit in (
        "spec/ir/P4bloIRTest/ProofAudit.lean",
        "spec/ir/P4bloIRTest/CodecProofAudit.lean",
    ):
        assert (ROOT / audit).is_file(), audit
    for old in (
        "spec/ir/Tests",
        "spec/ir/ProofAudit.lean",
        "spec/ir/CodecProofAudit.lean",
        "spec/arch/ArchTests",
        "spec/arch/ArchProofAudit.lean",
        "impl/lean/P4bloTests.lean",
        "impl/lean/UserProofAudit.lean",
        "impl/lean/ForwarderMain.lean",
    ):
        assert not (ROOT / old).exists(), old


def test_schema_descriptor_identity_survives_move() -> None:
    assert pb.DESCRIPTOR.name == "p4blo/v0/p4blo.proto"
    assert (ROOT / "spec/ir/proto" / pb.DESCRIPTOR.name).is_file()


def test_shared_corpus_discovery_is_not_empty() -> None:
    corpus = ROOT / "tests/programs/corpus"
    programs = sorted(corpus.glob("*/*.txtpb"))
    vectors = sorted(corpus.glob("*/*.stf"))
    assert len(programs) >= 10
    assert len(vectors) >= 15
    assert all(p.with_suffix(".py").is_file() for p in programs)
    assert catalog.PROGRAMS == sorted(p.parent for p in programs)
    assert catalog.VECTORS == vectors
    example_vectors = sorted((ROOT / "tests/programs/examples").glob("*/*.stf"))
    assert example_vectors, "public application vectors must reach both oracles"
    assert catalog.ORACLE_VECTORS == sorted(vectors + example_vectors)
    assert not (ROOT / "corpus").exists()
    assert not (ROOT / "oracle").exists()


def _undiscovered(paths: list[str], roots: list[str]) -> list[str]:
    return [
        path
        for path in paths
        if Path(path).name.startswith("test_")
        and path.endswith(".py")
        and not any(Path(path).is_relative_to(root) for root in roots)
    ]


def test_tests_are_grouped_by_question() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert "--import-mode=importlib" in config["addopts"]
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "tests", "impl/python/tests"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    assert not _undiscovered(tracked, config["testpaths"])
    # A removed package root must expose the tests that default discovery loses.
    assert _undiscovered(["impl/python/tests/test_ir.py"], ["tests"]) == [
        "impl/python/tests/test_ir.py"
    ]
