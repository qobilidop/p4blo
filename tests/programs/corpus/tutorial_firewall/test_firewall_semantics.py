"""Persistent execution of the Python-authored tutorial firewall.

The generic Lean endpoint checks serialized programs and request sequences
against Python and independent packet/state expectations.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from hypothesis import given, settings

from p4blo import arch, stf
from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import (
    ProtocolError,
    compare_program,
    python_outcome,
    request_json,
)
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.corpus.forwarder.test_forwarder_semantics import freeze
from tests.programs.corpus.tutorial_firewall.test_firewall import (
    Step,
    bypass,
    collision,
    connection,
    edges,
    shapes,
)
from tests.programs.corpus.tutorial_firewall.test_firewall_boundaries import persistence, truncated
from tests.programs.corpus.tutorial_firewall.test_firewall_generated import (
    Event,
    campaigns,
    model,
    targeted,
)
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build

ROOT = Path(__file__).resolve().parents[4]
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


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_lean_agrees_firewall_stf(
    firewall: apb.BlockAssembly, lean_binary: Path, vector: Path
) -> None:
    statements = stf.parse(vector.read_text())
    index = BoundIndex.build(firewall)
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    stf.replay(index, statements, collect)
    assert cases
    compare_and_save(firewall, cases, lean_binary)
    stf.assert_replay(
        index, statements, arch.stf_driver(v1model.V1Model(ports=4), v1model.load(firewall))
    )


@pytest.mark.parametrize(
    "sequence",
    [connection(), collision(), collision(reverse=True), shapes(), bypass(), edges()],
    ids=["connection", "collision", "reverse-collision", "shapes", "bypass", "edges"],
)
def test_lean_agrees_firewall_known_sequences(
    firewall: apb.BlockAssembly, lean_binary: Path, sequence: list[Step]
) -> None:
    check_sequence(firewall, sequence, lean_binary)


@pytest.mark.parametrize("length", range(55))
def test_lean_agrees_firewall_packet_boundaries(
    firewall: apb.BlockAssembly, lean_binary: Path, length: int
) -> None:
    check_sequence(firewall, [truncated(length)], lean_binary)


@pytest.mark.parametrize("length", range(54))
def test_lean_agrees_firewall_persistent_boundaries(
    firewall: apb.BlockAssembly, lean_binary: Path, length: int
) -> None:
    check_sequence(firewall, persistence(length), lean_binary)


@pytest.mark.parametrize("events", targeted().values(), ids=targeted().keys())
def test_lean_agrees_firewall_host_policy(
    firewall: apb.BlockAssembly, lean_binary: Path, events: list[Event]
) -> None:
    check_sequence(firewall, model(events), lean_binary)


@settings(max_examples=40, derandomize=True, deadline=None)
@given(events=campaigns())
def test_lean_agrees_firewall_generated(
    firewall: apb.BlockAssembly, lean_binary: Path, events: list[Event]
) -> None:
    check_sequence(firewall, model(events), lean_binary)


@pytest.fixture(scope="module")
def firewall() -> apb.BlockAssembly:
    assert {"connection.stf", "collisions.stf"} <= {p.name for p in VECTORS}
    program = build()
    assert_program_identity(program)
    return program
