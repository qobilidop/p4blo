"""Lean-authored scalar IR against independent answers and both interpreters.

The exporter emits syntax only. Expected bytes below do not call the Lean
source denotation or mirror its lowering. Thus a bad notation expansion can
fail even when the core lowering theorem remains true.
"""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo import arch
from p4blo.drt.case import Case
from p4blo.drt.programs import scalar_program
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.v0 import p4blo_pb2 as pb

# Width is independently specified, including bool (None) and non-byte bits.
EXPECTED: dict[str, tuple[int | None, bytes]] = {
    "zero": (8, b"\x00"),
    "maximum": (8, b"\xff"),
    "add": (8, b"\x1a"),
    "wrap": (8, b"\x00"),
    "one-bit-wrap": (1, b"\x00"),
    "wide": (65, b"\x00\x00\x00\x00\x00\x00\x00\x00\x80"),
    "equal": (None, b"\x80"),
    "unequal": (None, b"\x00"),
    "yes": (8, b"\x13"),
    "no": (8, b"\x07"),
    "bool-yes": (None, b"\x00"),
    "bool-no": (None, b"\x80"),
    "nested": (8, b"\x2e"),
}


def test_user_proof_audit_and_exporter_are_default_targets() -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "lean/lakefile.toml").read_text())
    assert {"UserProofAudit", "scalarExamples"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def authored_expressions(lean_binary: Path) -> dict[str, pb.Expr]:
    # lean_binary enforces the shared absent-vs-broken/required gate policy.
    assert lean_binary.is_file()
    root = Path(__file__).resolve().parents[1]
    exporter = root / "lean/.lake/build/bin/scalarExamples"
    assert exporter.is_file(), f"missing Lean eDSL exporter: run {root}/scripts/check-lean.sh"
    completed = subprocess.run(
        [str(exporter)], capture_output=True, text=True, check=True, timeout=30
    )
    result: dict[str, pb.Expr] = {}
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name not in result, f"duplicate exported example: {name}"
        assert name in EXPECTED, f"unexpected exported example: {name}"
        assert record["width"] == EXPECTED[name][0]
        result[name] = json_format.ParseDict(record["expression"], pb.Expr())
    assert result.keys() == EXPECTED.keys(), "export must include every authored example"
    return result


@pytest.mark.parametrize("name", EXPECTED)
def test_lean_agrees_on_authored_scalar_known_answers(
    name: str, authored_expressions: dict[str, pb.Expr], lean_binary: Path
) -> None:
    width, expected = EXPECTED[name]
    program = scalar_program(authored_expressions[name], width)
    case = Case(pb.Entries(), 0, b"")
    # Known-answer check independently catches shared mistakes, including a
    # source macro that builds a valid but unintended expression.
    assert run_python(arch.load(program), case, 4) == [(0, expected)]
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        target = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        target.mkdir(parents=True, exist_ok=True)
        bundle = target / f"lean-edsl-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
