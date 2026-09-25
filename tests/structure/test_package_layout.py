"""Guard the ownership split without depending on cached build outputs."""

import subprocess
import tomllib
from pathlib import Path

from p4blo.drt.run import default_lean_binary
from p4blo.v0 import p4blo_pb2 as pb
from tests.external import test_oracle, test_oracle_bmv2
from tests.programs import test_corpus

ROOT = Path(__file__).resolve().parents[2]


def test_specification_executable_location() -> None:
    assert default_lean_binary().parent == ROOT / "spec/arch/.lake/build/bin"
    assert not (ROOT / "proto").exists()


def test_lean_package_dependency_is_one_way() -> None:
    spec = tomllib.loads((ROOT / "spec/ir/lakefile.toml").read_text())
    arch = tomllib.loads((ROOT / "spec/arch/lakefile.toml").read_text())
    library = tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())
    assert spec["name"] == "p4blo-ir"
    assert arch["name"] == "p4blo-arch"
    assert library["name"] == "p4blo"
    # The IR spec depends on nothing; the architecture spec on the IR; the
    # user library on both. Nothing architectural lives in the IR spec.
    assert not spec.get("require")
    assert arch["require"] == [{"name": "p4blo-ir", "path": "../ir"}]
    assert library["require"] == [
        {"name": "p4blo-ir", "path": "../../spec/ir"},
        {"name": "p4blo-arch", "path": "../../spec/arch"},
    ]
    assert "P4bloIR" in {lib["name"] for lib in spec["lean_lib"]}
    assert "P4bloArch" in {lib["name"] for lib in arch["lean_lib"]}
    assert "P4blo" in {lib["name"] for lib in library["lean_lib"]}
    assert "P4bloIR" in spec["defaultTargets"]
    assert "P4bloArch" in arch["defaultTargets"]
    assert "P4blo" in library["defaultTargets"]
    assert "p4blo-lean" not in {exe["name"] for exe in spec["lean_exe"]}
    assert {exe["name"]: exe["root"] for exe in arch["lean_exe"]}["p4blo-lean"] == "Main"
    assert not (ROOT / "spec/ir/P4bloIR/Switch.lean").exists()
    assert (ROOT / "spec/arch/P4bloArch/Switch.lean").is_file()
    assert (ROOT / "spec/arch/P4bloArch/Externs.lean").is_file()
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
    assert {"P4bloIRTest", "codec-leaves"} <= set(spec["defaultTargets"])
    assert "P4bloIRTest" in {lib["name"] for lib in spec["lean_lib"]}
    assert {exe["name"]: exe["root"] for exe in spec["lean_exe"]}["codec-leaves"] == (
        "P4bloIRTest.CodecLeaves"
    )
    assert spec["testDriver"]
    assert arch["testDriver"]
    assert library["testDriver"]
    toolchain = (ROOT / "spec/ir/lean-toolchain").read_bytes()
    assert (ROOT / "spec/arch/lean-toolchain").read_bytes() == toolchain
    assert (ROOT / "impl/lean/lean-toolchain").read_bytes() == toolchain


# Each Lean package's root module, and the tracked entries its root may hold
# beyond the layout's own: the IR's wire schema and the user package's
# assurance log.
LEAN_PACKAGES = {
    "spec/ir": ("P4bloIR", {"proto"}),
    "spec/arch": ("P4bloArch", {"proto"}),
    "impl/lean": ("P4blo", {"ASSURANCE.md"}),
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
        "spec/arch/P4bloArchTest/ArchProofAudit.lean",
        "impl/lean/P4bloTest/UserProofAudit.lean",
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


def test_user_executable_is_one_main_with_subcommands() -> None:
    library = tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())
    assert {exe["name"]: exe["root"] for exe in library["lean_exe"]}["p4blo"] == "Main"
    assert "p4blo" in library["defaultTargets"]


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


# The test suites, one directory per question of the testing strategy
# (docs/design.md), and the data and drivers they share; tests/examples
# also keeps each application's tests beside its assets.
TEST_SUITES = ("unit", "codec", "programs", "drt", "lean", "external", "structure")
TEST_DATA = (
    "corpus",
    "examples",
    "oracle",
    "conformance",
    "frontend",
    "assurance",
    "pyright",
    "golden",
    "drt-coverage-parts",
)


def test_tests_are_grouped_by_question() -> None:
    tests = ROOT / "tests"
    assert not sorted(p.name for p in tests.glob("test_*.py")), "no flat test modules"
    for suite in TEST_SUITES:
        directory = tests / suite
        assert (directory / "__init__.py").is_file(), suite
        assert (directory / "README.md").is_file(), suite
        assert sorted(directory.glob("test_*.py")), suite
    for data in TEST_DATA:
        assert (tests / data).is_dir(), data
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "tests"],
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    top = {Path(p.decode()).relative_to("tests").parts[0] for p in tracked if p}
    files = {"__init__.py", "conftest.py", "ledger-classes.json"}
    files |= {"drt-unhit-tags.json", "drt-guided-measurement.json"}
    assert top == set(TEST_SUITES) | set(TEST_DATA) | files
