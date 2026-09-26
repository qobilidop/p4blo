"""Every public application is typed, validated, reconstructed and executed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from p4blo import arch, stf
from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.drt import generate
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from tests.programs.examples.catalog import DATA, NAMES, ROOT, build


def test_discovery_is_nonempty_and_assets_are_complete() -> None:
    assert {"router", "firewall", "load_balancer"} <= set(NAMES)
    for name in NAMES:
        assert (ROOT / f"examples/{name}/README.md").is_file()
        assert (ROOT / f"examples/{name}/demo.py").is_file()
        assert (DATA / name / "program.txtpb").is_file()
        assert list((DATA / name).glob("*.stf"))


@pytest.mark.parametrize("name", NAMES)
def test_source_rebuilds_valid_golden(name: str) -> None:
    program = build(name)
    assert validator.validate(program) == []
    assert arch_wire.dump_text(program) == (DATA / name / "program.txtpb").read_text()


@pytest.mark.parametrize("name", NAMES)
def test_vectors(name: str) -> None:
    for vector in sorted((DATA / name).glob("*.stf")):
        program = build(name)
        statements = stf.parse(vector.read_text())
        loaded = v1model.load(program)
        stf.assert_replay(loaded.index, statements, arch.stf_driver(v1model.V1Model(4), loaded))
        for statement in statements:
            if isinstance(statement, stf.Expect):
                assert statement.exact, f"{vector}: public examples require exact output lengths"


@pytest.mark.parametrize("name", NAMES)
def test_lean_agrees_generated_application(name: str, lean_binary: Path) -> None:
    program = build(name)
    cases = generate(BoundIndex.build(program), seed=73, count=80, ports=4)
    artifacts = ROOT / ".artifacts/drt/examples"
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        report = compare_program(program, cases, 4, [lean_binary], seed=73)
    except ProtocolError as error:
        if error.report is not None:
            save(error.report, artifacts / f"{name}-generated-protocol.json")
        raise
    if not report.passed:
        save(report, artifacts / f"{name}-generated.json")
    assert report.passed, report.divergences
    assert report.both_errored == 0


@pytest.mark.parametrize("name", NAMES)
def test_documented_demo(name: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", f"examples.{name}.demo"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    readme = (ROOT / f"examples/{name}/README.md").read_text()
    assert f"```text\n{result.stdout}```" in readme
