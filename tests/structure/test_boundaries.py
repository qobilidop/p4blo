"""The Python package keeps the IR apart from architecture support.

`p4blo.ir`, `p4blo.validator`, `p4blo.stf`, `p4blo.interp` and `p4blo.edsl`
are the IR side: they define programs, check them, run their blocks as
functions and author them. `p4blo.arch` is architecture support: the
metadata contract, the filter and the switch, the extern families they
supply and the v1model printer. `p4blo.drt` is the harness that drives
both. The IR side never imports the other two, and the architecture never
imports the harness; docs/ir-semantics.md and docs/arch-supports.md
describe the same boundary in prose.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "impl/python/p4blo"
IR_SIDE = ("ir.py", "validator", "printer", "stf.py", "interp", "edsl")


def modules(*parts: str) -> list[Path]:
    found: list[Path] = []
    for part in parts:
        path = PACKAGE / part
        found.extend([path] if path.is_file() else sorted(path.rglob("*.py")))
    assert found, parts
    return found


def imported_modules(path: Path) -> set[str]:
    """Every module a file imports, at any nesting depth."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def crossings(files: list[Path], forbidden: tuple[str, ...]) -> list[str]:
    return [
        f"{path.relative_to(ROOT)} imports {name}"
        for path in files
        for name in sorted(imported_modules(path))
        if any(name == f or name.startswith(f + ".") for f in forbidden)
    ]


# Scripts CI or a container runs with a bare interpreter, before or without
# the p4blo package: the coverage probe's `build`, the BMv2 container's
# driver and the website renderer. Their module-level imports must come from
# the standard library; p4blo imports stay inside the functions that need it.
BARE_INTERPRETER_SCRIPTS = (
    "scripts/ci-scope.py",
    "tests/oracle/coverage.py",
    "tests/oracle/bmv2/driver.py",
    "scripts/render-website-example.py",
)


def top_level_non_stdlib(path: Path) -> list[str]:
    """Modules imported at module level that are not in the standard library."""
    names: list[str] = []
    pending: list[ast.AST] = list(ast.parse(path.read_text(encoding="utf-8"), str(path)).body)
    while pending:
        node = pending.pop()
        # Module-level `if`, `try` and `with` bodies run at import too.
        if isinstance(node, (ast.If, ast.Try, ast.With)):
            pending.extend(ast.iter_child_nodes(node))
        elif isinstance(node, ast.ExceptHandler):
            pending.extend(node.body)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return [
        name
        for name in names
        if name != "__future__" and name.split(".")[0] not in sys.stdlib_module_names
    ]


@pytest.mark.parametrize("script", BARE_INTERPRETER_SCRIPTS)
def test_bare_interpreter_scripts_import_only_stdlib_at_module_level(script: str) -> None:
    assert top_level_non_stdlib(ROOT / script) == []


def test_bare_interpreter_check_detects_a_module_level_package_import(tmp_path: Path) -> None:
    script = tmp_path / "script.py"
    script.write_text(
        "import json\n\nfrom p4blo.arch import wire\n\ntry:\n    import p4blo.ir\n"
        "except ImportError:\n    pass\n\n\ndef f() -> None:\n"
        "    from p4blo import stf\n",
        encoding="utf-8",
    )
    assert sorted(top_level_non_stdlib(script)) == ["p4blo.arch", "p4blo.ir"]


def test_ir_side_never_imports_architecture_or_harness() -> None:
    assert crossings(modules(*IR_SIDE), ("p4blo.arch", "p4blo.drt")) == []


def test_import_boundary_detects_a_concrete_extern_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A convenience re-export must not smuggle a family into the core."""
    candidate = tmp_path / "edsl.py"
    candidate.write_text("from p4blo.arch.externs.declarations import Register\n")
    monkeypatch.setitem(crossings.__globals__, "ROOT", tmp_path)
    assert crossings([candidate], ("p4blo.arch",)) == [
        "edsl.py imports p4blo.arch.externs.declarations",
        "edsl.py imports p4blo.arch.externs.declarations.Register",
    ]


def test_core_edsl_has_no_concrete_extern_families() -> None:
    from p4blo import edsl
    from p4blo.edsl import externs

    for name in ("Register", "Counter", "Checksum16", "CRC16", "CRC32"):
        assert not hasattr(edsl, name), name
        assert not hasattr(externs, name), name
    assert externs.__all__ == ["Extern"]
    assert not (PACKAGE / "edsl/core/externs.py").exists()


def test_architecture_never_imports_harness() -> None:
    assert crossings(modules("arch"), ("p4blo.drt",)) == []


def test_architecture_support_lives_under_arch() -> None:
    assert (PACKAGE / "arch/externs/register.py").is_file()
    assert (PACKAGE / "arch/v1model.py").is_file()
    for old in ("externs", "printer.py"):
        assert not (PACKAGE / old).exists(), old


LEAN_IR_SPEC = ROOT / "spec/ir/P4bloIR"
# Words that name an architecture's decisions or a concrete extern family.
# The IR specification may not mention them; the reference architecture
# package does.
ARCHITECTURAL = (
    "Switch",
    "egress",
    "ingress_port",
    "standard_metadata",
    "P4bloArch",
    '"register"',
    '"counter"',
    '"checksum16"',
    '"crc16"',
    '"crc32"',
)


def test_ir_specification_holds_nothing_architectural() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}: {word}"
        for path in sorted(LEAN_IR_SPEC.rglob("*.lean"))
        for word in ARCHITECTURAL
        if word in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
    for old in ("Switch.lean", "CertificateWire.lean"):
        assert not (LEAN_IR_SPEC / old).exists()
    assert not (ROOT / "spec/ir/Main.lean").exists()


# The gate-only libraries of the three Lean packages.
LEAN_TEST_LIBRARIES = ("P4bloIRTest", "P4bloArchTest", "P4bloTest")


def test_importable_lean_modules_never_import_gate_only_ones() -> None:
    """What a client may import, and each package's executable, stands
    without the tests and audits under `<Root>Test/`."""
    offenders = []
    for package in ("spec/ir", "spec/arch", "impl/lean"):
        for path in sorted((ROOT / package).rglob("*.lean")):
            relative = path.relative_to(ROOT / package)
            if relative.parts[0] in LEAN_TEST_LIBRARIES or ".lake" in relative.parts:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                words = line.split()
                if words[:1] == ["import"] and words[1].split(".")[0] in LEAN_TEST_LIBRARIES:
                    offenders.append(f"{package}/{relative}: {line}")
    assert offenders == []
