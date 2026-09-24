"""Independent authoring and persistent execution of the fixed Lean firewall.

These bounded tests do not prove the complete pipeline. The runner accepts
requests, never an exported Program; ordinary DRT separately exercises codecs.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings

from p4blo import arch, ir, stf, validator
from p4blo.drt._json import loads as strict_loads
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import (
    Outcome,
    ProtocolError,
    compare_program,
    parse_reply,
    python_outcome,
    request_json,
)
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.tutorial_firewall.tutorial_firewall import build
from tests.test_firewall import Step, bypass, collision, connection, edges, shapes
from tests.test_firewall_boundaries import persistence, truncated
from tests.test_firewall_generated import Event, campaigns, model, targeted
from tests.test_lean_forwarder import freeze

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests/corpus/tutorial_firewall"
EXPORTER = ROOT / "lean/.lake/build/bin/leanTutorialFirewall"
VECTORS = sorted(CORPUS.glob("*.stf"))


def assert_program_identity(program: pb.Program) -> None:
    assert program == build(), "Lean source differs from independent Python authoring"
    assert program == ir.load_text(CORPUS / "tutorial_firewall.txtpb"), "frozen golden differs"
    assert validator.validate(program) == []


@pytest.fixture(scope="module")
def firewall(lean_binary: Path) -> pb.Program:
    assert lean_binary.is_file()
    assert EXPORTER.is_file(), "build both Lean packages before conformance"
    assert {"connection.stf", "collisions.stf"} <= {p.name for p in VECTORS}
    result = subprocess.run([str(EXPORTER)], check=True, capture_output=True, text=True, timeout=30)
    assert result.stderr == ""
    program = ir.load_json(result.stdout)
    assert_program_identity(program)
    return program


def checked_fixed_reply(line: str) -> Outcome:
    record = strict_loads(line)
    assert type(record) is dict
    assert set(record) in ({"outputs", "state"}, {"outputs", "state", "diagnostic"})
    if "diagnostic" in record:
        assert type(record["diagnostic"]) is str and record["diagnostic"]
    outcome = parse_reply(line)
    assert [(s.name, s.kind) for s in outcome.state] == [
        ("bloom_filter_1", "register"),
        ("bloom_filter_2", "register"),
        ("csum", "checksum16"),
        ("hash16", "crc16"),
        ("hash32", "crc32"),
    ]
    for item in outcome.state[:2]:
        assert type(item.width) is int and item.width == 1
        assert len(item.values) == 4096
        assert all(type(value) is int and value in (0, 1) for value in item.values)
    return outcome


def fixed_run(cases: list[Case]) -> list[Outcome]:
    requests = "\n".join(request_json(case) for case in cases) + "\n"
    process = subprocess.run(
        [str(EXPORTER), "run"],
        input=requests,
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        assert process.returncode == 0 and process.stderr == ""
        replies = process.stdout.splitlines()
        assert len(replies) == len(cases)
        outcomes = [checked_fixed_reply(reply) for reply in replies]
        loaded = arch.load(build())
        for case, actual in zip(cases, outcomes, strict=True):
            expected = python_outcome(loaded, case, 4)
            assert expected.error is None and actual.error is None
            assert actual.diagnostic is expected.diagnostic is None
            assert freeze(actual.outputs) == freeze(expected.outputs)
            assert freeze(actual.state) == freeze(expected.state)
        return outcomes
    except (AssertionError, ProtocolError, ValueError) as error:
        # A fixed-server defect is not necessarily a generic DRT defect. Keep
        # its exact protocol separately, without claiming a generic divergence.
        record = {
            "format": "p4blo.lean-firewall.fixed.v0",
            "program": json.loads(ir.dump_json(build())),
            "ports": 4,
            "stdin": requests,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
        }
        encoded = json.dumps(record, sort_keys=True, indent=2) + "\n"
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ROOT / ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"lean-firewall-fixed-{digest[:24]}.json"
        path.write_text(encoded)
        raise AssertionError(f"fixed runner mismatch saved to {path}") from error


def compare_and_save(program: pb.Program, cases: list[Case], lean_binary: Path) -> None:
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


def check_sequence(program: pb.Program, sequence: list[Step], lean_binary: Path) -> None:
    cases = [item.case for item in sequence]
    # Save real engine inconsistencies before asserting independent policy answers.
    compare_and_save(program, cases, lean_binary)
    loaded = arch.load(program)
    for expected, actual in zip(sequence, fixed_run(cases), strict=True):
        python = python_outcome(loaded, expected.case, 4)
        assert python.error is None and actual.error is None
        assert freeze(actual.outputs) == freeze(expected.outputs) == freeze(python.outputs)
        assert freeze(actual.state) == freeze(expected.state) == freeze(python.state)
        assert actual.diagnostic is python.diagnostic is None


def test_firewall_default_target() -> None:
    config = tomllib.loads((ROOT / "lean/lakefile.toml").read_text())
    assert "leanTutorialFirewall" in config["defaultTargets"]


def test_lean_agrees_firewall_program_identity(firewall: pb.Program) -> None:
    assert_program_identity(firewall)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_lean_agrees_firewall_stf(firewall: pb.Program, lean_binary: Path, vector: Path) -> None:
    statements = stf.parse(vector.read_text())
    index = ir.Index.build(firewall)
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    stf.replay(index, statements, collect)
    assert cases
    compare_and_save(firewall, cases, lean_binary)
    replies = iter(fixed_run(cases))

    def output(_entries: pb.Entries, _port: int, _packet: bytes) -> list[tuple[int, bytes]]:
        reply = next(replies)
        assert reply.outputs is not None and reply.diagnostic is None
        return list(reply.outputs)

    stf.assert_replay(index, statements, output)
    assert next(replies, None) is None
    stf.assert_replay(index, statements, arch.stf_driver(arch.Switch(ports=4), arch.load(firewall)))


@pytest.mark.parametrize(
    "sequence",
    [connection(), collision(), collision(reverse=True), shapes(), bypass(), edges()],
    ids=["connection", "collision", "reverse-collision", "shapes", "bypass", "edges"],
)
def test_lean_agrees_firewall_known_sequences(
    firewall: pb.Program, lean_binary: Path, sequence: list[Step]
) -> None:
    check_sequence(firewall, sequence, lean_binary)


@pytest.mark.parametrize("length", range(55))
def test_lean_agrees_firewall_packet_boundaries(
    firewall: pb.Program, lean_binary: Path, length: int
) -> None:
    check_sequence(firewall, [truncated(length)], lean_binary)


@pytest.mark.parametrize("length", range(54))
def test_lean_agrees_firewall_persistent_boundaries(
    firewall: pb.Program, lean_binary: Path, length: int
) -> None:
    check_sequence(firewall, persistence(length), lean_binary)


@pytest.mark.parametrize("events", targeted().values(), ids=targeted().keys())
def test_lean_agrees_firewall_host_policy(
    firewall: pb.Program, lean_binary: Path, events: list[Event]
) -> None:
    check_sequence(firewall, model(events), lean_binary)


@settings(max_examples=40, derandomize=True, deadline=None)
@given(events=campaigns())
def test_lean_agrees_firewall_generated(
    firewall: pb.Program, lean_binary: Path, events: list[Event]
) -> None:
    check_sequence(firewall, model(events), lean_binary)


@pytest.mark.parametrize("fault", ["array-length", "array-width", "missing-extern", "extra-field"])
def test_fixed_observer_rejects_incomplete_state(fault: str) -> None:
    record = {
        "outputs": [],
        "state": {
            "bloom_filter_1": {"kind": "register", "width": 1, "values": ["0x0"] * 4096},
            "bloom_filter_2": {"kind": "register", "width": 1, "values": ["0x0"] * 4096},
            "csum": {"kind": "checksum16"},
            "hash16": {"kind": "crc16"},
            "hash32": {"kind": "crc32"},
        },
    }
    assert checked_fixed_reply(json.dumps(record)).error is None
    if fault == "array-length":
        record["state"]["bloom_filter_1"]["values"] = ["0x0"] * 4095
    elif fault == "array-width":
        record["state"]["bloom_filter_2"]["width"] = True
    elif fault == "missing-extern":
        del record["state"]["hash32"]
    else:
        record["unexpected"] = True
    with pytest.raises((AssertionError, ProtocolError)):
        checked_fixed_reply(json.dumps(record))


def test_lean_agrees_firewall_fixed_reset_is_retained(
    firewall: pb.Program, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cases = [item.case for item in connection()]
    # Generic execution remains correct: this fault belongs solely to the
    # fixed process's persistence. Never label its artifact a generic mismatch.
    compare_and_save(firewall, cases, lean_binary)
    original = subprocess.run
    hits = 0

    def restart(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal hits
        assert args == [str(EXPORTER), "run"]
        requests = kwargs.pop("input").splitlines()
        replies: list[str] = []
        for request in requests:
            result = original(args, input=request + "\n", **kwargs)
            assert result.returncode == 0 and result.stderr == ""
            replies.append(result.stdout)
            hits += 1
        return subprocess.CompletedProcess(args, 0, "".join(replies), "")

    with monkeypatch.context() as fault:
        fault.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
        fault.setattr(subprocess, "run", restart)
        with pytest.raises(AssertionError, match="fixed runner mismatch saved"):
            fixed_run(cases)
    assert hits == len(cases) == 4
    artifacts = list(tmp_path.glob("lean-firewall-fixed-*.json"))
    assert len(artifacts) == 1
    record = strict_loads(artifacts[0].read_text())
    assert isinstance(record, dict)
    assert record["format"] == "p4blo.lean-firewall.fixed.v0"
    assert ir.load_json(json.dumps(record["program"])) == firewall
    assert record["stdin"] == "\n".join(request_json(case) for case in cases) + "\n"
    assert record["returncode"] == 0 and record["stderr"] == "" and record["ports"] == 4
    broken = [checked_fixed_reply(line) for line in record["stdout"].splitlines()]
    assert len(broken) == 4 and broken[2].outputs == ()
    assert any(broken[1].state[0].values) and not any(broken[2].state[0].values)
    restored = fixed_run(cases)
    for actual, expected in zip(restored, connection(), strict=True):
        assert freeze(actual.outputs) == freeze(expected.outputs)
        assert freeze(actual.state) == freeze(expected.state)
