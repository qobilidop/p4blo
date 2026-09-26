"""Whole-packet anchors and complete-state observations for the Python forwarder.

The generic Lean endpoint checks serialized programs against Python; known
answers and injected faults independently test the observable behavior.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any, cast

import pytest

from p4blo import arch, stf
from p4blo.arch import v1model
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.forwarder import (
    VECTORS,
    compare_and_save,
    edge_case,
    invalid_env,
    observe_invalid_control,
)
from tests.support.forwarder import (
    forwarder as forwarder,
)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_lean_agrees_forwarder_stf(
    forwarder: apb.BlockAssembly, lean_binary: Path, vector: Path
) -> None:
    statements = stf.parse(vector.read_text())
    index = BoundIndex.build(forwarder)
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    # Public STF replay does installation/grouping. This pass collects input,
    # deliberately ignoring its expected-output failures; the next passes assert.
    stf.replay(index, statements, collect)
    assert cases, f"forwarder vector has no packet requests: {vector.name}"
    compare_and_save(forwarder, cases, lean_binary, vector.stem)
    loaded = v1model.load(forwarder)
    stf.assert_replay(index, statements, arch.stf_driver(v1model.V1Model(ports=4), loaded))


@pytest.mark.parametrize("ttl", [0, 1])
def test_lean_agrees_forwarder_wrapping_ttl(
    forwarder: apb.BlockAssembly, lean_binary: Path, ttl: int
) -> None:
    case, expected = edge_case(ttl)
    compare_and_save(forwarder, [case], lean_binary, f"ttl-{ttl}")
    assert run_python(v1model.load(forwarder), case, 4) == expected


def test_lean_agrees_forwarder_detects_saturating_python_subtraction(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A real evaluator fault: save before checking output; replay live/restored."""
    original = expr.bits_binary
    hits = 0

    def saturating(op: int, left: Bits, right: Bits) -> Value:
        nonlocal hits
        if op == pb.BINARY_OP_SUB and left.width == 8 and left.value == 0 and right.value == 1:
            hits += 1
            return Bits(8, 0)
        return original(op, left, right)

    case, expected = edge_case(0)
    bundle = tmp_path / "forwarder-saturating-subtraction.json"
    with monkeypatch.context() as fault:
        fault.setattr(expr, "bits_binary", saturating)
        report = compare_program(forwarder, [case], 4, [lean_binary])
        save(report, bundle)
        assert hits == 1 and report.agreed == 0 and len(report.divergences) == 1
        assert report.protocol_error is None and report.both_errored == 0
        program, cases, ports, seed = replay.load(bundle)
        assert program == forwarder and cases == [case] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert hits == 2 and live.agreed == 0 and len(live.divergences) == 1
        divergence = live.divergences[0]
        assert divergence.lean.outputs == tuple(expected)
        assert divergence.python.outputs == tuple(edge_case(1)[1])
        for outcome in [divergence.python, divergence.lean]:
            assert outcome.error is None and outcome.diagnostic is None
        assert divergence.python.state == divergence.lean.state
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1 and restored.both_errored == 0


def test_lean_agrees_forwarder_checksum_after_drop(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dropped packet cannot reveal this stateless checksum call in its output.

    Retain a scoped execution observation, separately from packet agreement.
    """
    original = stmt.call_extern
    observed: list[tuple[int, int]] = []

    def observe(call: pb.CallExtern, env: Env) -> None:
        original(call, env)
        if env.block.name == "MyIngress" and call.instance == "csum":
            metadata = expr.expect_struct(env.read("meta"))
            headers = expr.expect_struct(env.read("hdr"))
            ipv4 = expr.expect_header(headers.fields[1])
            observed.append(
                (expr.expect_bits(metadata.fields[1]).value, expr.expect_bits(ipv4.fields[9]).value)
            )

    case, _ = edge_case(0)
    case = Case(pb.Entries(), case.ingress_port, case.packet)
    with monkeypatch.context() as spy:
        spy.setattr(stmt, "call_extern", observe)
        compare_and_save(forwarder, [case], lean_binary, "drop-checksum")
    assert observed == [(511, 0xA3D0)]


@pytest.mark.parametrize(
    "valid,sentinel,port,ttl",
    list(itertools.product([False, True], [False, True], [0, 3], [0, 1, 255])),
)
def test_python_forwarder_invalid_python_state(
    forwarder: apb.BlockAssembly, valid: bool, sentinel: bool, port: int, ttl: int
) -> None:
    """Complete-state known answers for invalid IPv4 profiles."""
    observe_invalid_control(invalid_env(forwarder, valid, sentinel, port, ttl))


@pytest.mark.parametrize("fault", ["ingress", "cursor-type", "entries", "index", "scope", "extern"])
def test_lean_agrees_forwarder_invalid_observer_kills_hidden_effect(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    original = stmt.execute_one
    hits = 0

    def corrupt(statement: pb.Stmt, env: Env) -> None:
        nonlocal hits
        original(statement, env)
        if env.block.name != "MyIngress" or not statement.HasField("conditional"):
            return
        if not statement.conditional.then[0].HasField("apply"):
            return
        headers = expr.expect_struct(env.read("hdr"))
        if expr.expect_header(headers.fields[1]).valid:
            return
        hits += 1
        if fault == "ingress":
            expr.expect_struct(env.read("meta")).fields[0] = Bits(9, 7)
        elif fault == "cursor-type":
            assert env.packet is not None
            cast(Any, env.packet).cursor = float(env.packet.cursor)
        elif fault == "entries":
            assert env.entries is not None
            env.entries.entries.clear()
        elif fault == "index":
            env.index.errors["NoError"] = 99
        elif fault == "scope":
            env.scope.actions.pop("NoAction")
        else:
            register = env.externs["sentinel"]
            assert isinstance(register, Register)
            register.cells[0] = Bits(8, 8)

    with monkeypatch.context() as patch:
        patch.setattr(stmt, "execute_one", corrupt)
        if fault == "ingress":
            # Confirm the actual reviewer-found survivor at the weaker public
            # packet boundary: it executes once and still emits exact ARP bytes.
            arp = bytes.fromhex(
                "ffffffffffff000000000001080600010800060400010000000000010a0001010000000000000a000202"
            )
            case = Case(pb.Entries(), 0, arp)
            report = compare_program(forwarder, [case], 4, [lean_binary])
            assert hits == 1 and report.passed and report.agreed == 1
            assert run_python(v1model.load(forwarder), case, 4) == [(0, arp)] and hits == 2
        prior = hits
        with pytest.raises(AssertionError, match="complete Python control state"):
            observe_invalid_control(invalid_env(forwarder, True, False, 3, 0))
        assert hits == prior + 1


def test_lean_agrees_forwarder_protocol_error_retains_inputs(
    forwarder: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Transport-error handling unit test, not a semantic fault/Lean simulation."""
    case, _ = edge_case(0)
    report = compare_program(forwarder, [case], 4, [lean_binary])
    assert report.passed
    report.protocol_error = "injected transport failure after the actual request"

    def failed(*_args: object, **_kwargs: object) -> None:
        raise ProtocolError(report.protocol_error or "transport failure", report)

    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    monkeypatch.setattr("tests.support.forwarder.compare_program", failed)
    with pytest.raises(pytest.fail.Exception, match="complete mismatch saved"):
        compare_and_save(forwarder, [case], lean_binary, "transport")
    program, cases, ports, seed = replay.load(tmp_path / "lean-forwarder-transport.json")
    assert program == forwarder and cases == [case] and (ports, seed) == (4, 0)
