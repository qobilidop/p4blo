"""Validity-guarded body; caller/initialization/observer remain test scaffolding."""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo import arch
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, boolean
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_lean_edsl_field_commands import PAYLOAD, field_command_program
from tests.test_lean_edsl_fields import member, target

INPUTS = {
    f"guard-{str(ev).lower()}-{str(iv).lower()}-{str(hit).lower()}-{ttl}": (ev, iv, hit, ttl)
    for ev, iv, hit, ttl in itertools.product(
        [False, True], [False, True], [False, True], [0, 1, 2, 255]
    )
}


def expected_packet(name: str) -> bytes:
    """Independent finite answer table, including all stored fields and inputs."""
    ev, iv, hit, ttl = INPUTS[name]
    forwarded_ttl = {(True, True, True, 2): 1, (True, True, True, 255): 254}.get((ev, iv, hit, ttl))
    if forwarded_ttl is None:
        dst, src, port, drop = 0x111213141516, 0x212223242526, 3, True
    else:
        dst, src, port, drop = 0xAABBCCDDEEFF, 0x102030405060, 7, False
        ttl = forwarded_ttl
    return (
        dst.to_bytes(6, "big")
        + src.to_bytes(6, "big")
        + bytes.fromhex("0800")
        + bytes([ev, ttl, 6])
        + bytes.fromhex("abcd")
        + bytes([iv])
        + port.to_bytes(2, "big")
        + bytes([drop])
        + bytes.fromhex("1234")
        + bytes([hit])
        + bytes.fromhex("aabbccddeeff1020304050600007")
        + bytes([19, 165])
        + PAYLOAD
    )


def guarded_program(name: str, body: list[pb.Stmt]) -> pb.Program:
    """Reuse declaration/observer layout, not prior policy or expected answers.

    Actual authored callee has hdr/meta inout, route in and scratch local.
    Replace every varying initializer explicitly; do not modify shared helpers.
    """
    ev, iv, hit, ttl = INPUTS[name]
    program = field_command_program("forward-two", body)
    program.name = f"lean-{name}"
    caller = program.blocks[1]
    replacements = {
        ("source_hdr", "ipv4", "ttl"): bits(8, ttl),
        ("source_route", "hit"): boolean(hit),
        ("source_meta", "drop"): boolean(False),
    }
    for path, value in replacements.items():
        matches = [
            s for s in caller.body if s.HasField("assign") and s.assign.target == target(*path)
        ]
        assert len(matches) == 1
        matches[0].assign.value.CopyFrom(value)
    # The shared base has both headers valid. Reconstruct only these two
    # validity initializers while retaining all other wrapper statements.
    body_copy = list(caller.body)
    del caller.body[:]
    seen: set[str] = set()
    for statement in body_copy:
        if statement.HasField("set_valid"):
            for header, valid in [("ethernet", ev), ("ipv4", iv)]:
                if statement.set_valid.header == target("source_hdr", header):
                    assert header not in seen
                    seen.add(header)
                    if valid:
                        caller.body.append(statement)
                    break
            else:
                caller.body.append(statement)
        else:
            caller.body.append(statement)
    assert seen == {"ethernet", "ipv4"}
    # Keep observer validity reads distinguishable from authored guard reads.
    # This identity mux is test-only instrumentation, not a normalization.
    callee = next(block for block in program.blocks if block.name == "RewriteBody")
    for statement in callee.body:
        if statement.HasField("assign"):
            value = statement.assign.value
            if value.HasField("cast") and value.cast.operand.HasField("cast"):
                observed = value.cast.operand.cast.operand
                if observed.HasField("is_valid"):
                    header = pb.Expr()
                    header.CopyFrom(observed.is_valid.header)
                    observed.is_valid.header.CopyFrom(
                        pb.Expr(
                            mux=pb.Mux(
                                **{"condition": boolean(True), "then": header, "otherwise": header}
                            )
                        )
                    )
    return program


def exported_programs(exporter: Path) -> dict[str, pb.Program]:
    completed = subprocess.run(
        [str(exporter)], capture_output=True, text=True, check=True, timeout=30
    )
    programs: dict[str, pb.Program] = {}
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name in INPUTS and name not in programs
        ev, iv, hit, ttl = INPUTS[name]
        assert set(record) == {"name", "ttl", "ethernetValid", "ipv4Valid", "hit", "body"}
        assert type(record["ttl"]) is int and record["ttl"] == ttl
        assert record["ethernetValid"] is ev and record["ipv4Valid"] is iv and record["hit"] is hit
        body = [json_format.ParseDict(statement, pb.Stmt()) for statement in record["body"]]
        programs[name] = guarded_program(name, body)
    assert programs.keys() == INPUTS.keys()
    return programs


@pytest.fixture(scope="module")
def guarded_programs(lean_binary: Path) -> dict[str, pb.Program]:
    root = Path(__file__).resolve().parents[1]
    return exported_programs(root / "impl/lean/.lake/build/bin/guardedForward")


def test_guarded_forward_exporter_is_a_default_target() -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "impl/lean/lakefile.toml").read_text())
    assert "guardedForward" in package["defaultTargets"]


@pytest.mark.parametrize("name", INPUTS)
def test_lean_agrees_on_guarded_forwarding(
    name: str, guarded_programs: dict[str, pb.Program], lean_binary: Path
) -> None:
    program = guarded_programs[name]
    case = Case(pb.Entries(), 0, PAYLOAD)
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        bundle = directory / f"lean-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    assert report.agreed == 1
    assert run_python(arch.load(program), case, 4) == [(0, expected_packet(name))]


def test_lean_agrees_after_retained_guard_fault(
    guarded_programs: dict[str, pb.Program],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A real evaluator fault bypasses both guards; full stored state exposes it."""
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    original = expr.evaluate

    def wrong_guard(value: pb.Expr, env: Env) -> Value:
        if env.block.name == "RewriteBody" and value.HasField("is_valid"):
            if value.is_valid.header in [member("hdr", "ethernet"), member("hdr", "ipv4")]:
                return True
        return original(value, env)

    name = "guard-false-false-true-2"
    bundle = tmp_path / f"lean-{name}.json"
    with monkeypatch.context() as fault:
        fault.setattr(expr, "evaluate", wrong_guard)
        fault.setattr(stmt, "evaluate", wrong_guard)
        with pytest.raises(pytest.fail.Exception, match="replay"):
            test_lean_agrees_on_guarded_forwarding(name, guarded_programs, lean_binary)
        program, cases, ports, seed = replay.load(bundle)
        assert program == guarded_programs[name]
        assert cases == [Case(pb.Entries(), 0, PAYLOAD)] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert live.protocol_error is None and live.both_errored == 0
        assert live.agreed == 0 and len(live.divergences) == 1
        assert live.divergences[0].lean.outputs == ((0, expected_packet(name)),)
        wrong = bytearray(expected_packet("guard-true-true-true-2"))
        # The independent observer retains both actual invalidity bits.
        wrong[14] = 0
        wrong[19] = 0
        assert live.divergences[0].python.outputs == ((0, bytes(wrong)),)
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
