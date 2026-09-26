"""Reusable firewall semantics fixtures and independent expectations."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import (
    ProtocolError,
    compare_program,
    python_outcome,
    request_json,
)
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build
from tests.support.firewall import Step
from tests.support.forwarder import freeze

ROOT = Path(__file__).resolve().parents[2]


CORPUS = ROOT / "tests/programs/corpus/tutorial_firewall"


VECTORS = sorted(CORPUS.glob("*.stf"))


def assert_program_identity(program: apb.BlockAssembly) -> None:
    assert program == build(), "program differs from Python authoring"
    assert program == arch_wire.load_text(CORPUS / "tutorial_firewall.txtpb"), (
        "frozen golden differs"
    )
    assert validator.validate(program) == []


def compare_and_save(program: apb.BlockAssembly, cases: list[Case], lean_binary: Path) -> None:
    try:
        report = compare_program(program, cases, 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        digest = hashlib.sha256(program.SerializeToString(deterministic=True))
        for case in cases:
            digest.update(request_json(case).encode())
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ROOT / ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"lean-firewall-{digest.hexdigest()[:24]}.json"
        save(report, path)
        pytest.fail(f"complete mismatch saved to {path}: {report}")
    assert report.agreed == len(cases)


def check_sequence(program: apb.BlockAssembly, sequence: list[Step], lean_binary: Path) -> None:
    cases = [item.case for item in sequence]
    # Save real engine inconsistencies before asserting independent policy answers.
    compare_and_save(program, cases, lean_binary)
    loaded = v1model.load(program)
    for expected in sequence:
        python = python_outcome(loaded, expected.case, 4)
        assert python.error is None
        assert freeze(expected.outputs) == freeze(python.outputs)
        assert freeze(expected.state) == freeze(python.state)
        assert python.diagnostic is None


@pytest.fixture(scope="module")
def firewall() -> apb.BlockAssembly:
    assert {"connection.stf", "collisions.stf"} <= {p.name for p in VECTORS}
    program = build()
    assert_program_identity(program)
    return program
