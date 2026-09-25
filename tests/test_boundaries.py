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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def test_ir_side_never_imports_architecture_or_harness() -> None:
    assert crossings(modules(*IR_SIDE), ("p4blo.arch", "p4blo.drt")) == []


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
