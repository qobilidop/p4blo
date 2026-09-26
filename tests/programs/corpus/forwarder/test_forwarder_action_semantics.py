"""Complete-state observations of the selected table action.

Python completes normally through run_action_call; an execution hook observes
entry and exit. Operational parameter-name decoys test layer separation.
"""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt.replay import save
from p4blo.drt.run import compare_program
from p4blo.interp import expr, stmt
from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.ir_helpers import target
from tests.support.forwarder import edge_case, freeze
from tests.support.forwarder_actions import (
    PROFILES,
    action_call,
    environment,
    observe_action,
)
from tests.support.forwarder_actions import (
    checked as checked,
)


@pytest.mark.parametrize("name", PROFILES)
def test_python_forwarder_action(
    checked: apb.BlockAssembly, name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    program = checked
    observe_action(program, name, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    [
        "block_first",
        "write_block_first",
        "wrong_binding",
        "probe_port_bool",
        "probe_clobber_dst",
        "detached_block",
        "missing_restore",
        "shadow_hdr",
        "cursor_float",
        "visit_bool",
        "entry_clear",
    ],
)
def test_action_observer_rejects_actual_environment_faults(
    checked: apb.BlockAssembly, fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original, read, write = Env.enter_action, Env.read, Env.write
    hits = 0
    probe_hits = 0

    def enter(env: Env, action: str, params: dict[str, Value]) -> Env:
        nonlocal hits
        hits += 1
        inner = original(env, action, params)
        if fault == "wrong_binding":
            assert inner.action_vars is not None
            inner.action_vars["port"] = Bits(9, 77)
        elif fault == "detached_block":
            inner.vars = deepcopy(inner.vars)
        elif fault == "missing_restore":
            env.action, env.action_vars = inner.action, inner.action_vars
        elif fault == "shadow_hdr":
            assert inner.action_vars is not None
            inner.action_vars["hdr"] = deepcopy(inner.vars["hdr"])
        elif fault == "cursor_float":
            assert inner.packet is not None
            inner.packet.cursor = 3.0  # type: ignore[assignment]
        elif fault == "visit_bool":
            inner.visits[("sentinel", "one")] = True
        elif fault == "entry_clear":
            assert inner.entries is not None
            inner.entries.entries.clear()
        return inner

    def block_first(env: Env, name: str) -> Value:
        return env.vars[name] if name in env.vars else read(env, name)

    def write_block_first(env: Env, name: str, value: Value) -> None:
        if name in env.vars:
            env.vars[name] = value
        else:
            write(env, name, value)

    def damaged_probe(env: Env, name: str, value: Value) -> None:
        nonlocal probe_hits
        write(env, name, value)
        if env.action == "ipv4_forward" and name == "port" and value == Bits(9, 1):
            probe_hits += 1
            assert env.action_vars is not None
            if fault == "probe_port_bool":
                env.action_vars["port"] = Bits(9, True)
            else:
                env.action_vars["dstAddr"] = Bits(48, 0)

    with monkeypatch.context() as mutant:
        mutant.setattr(Env, "enter_action", enter)
        if fault == "block_first":
            mutant.setattr(Env, "read", block_first)
        if fault == "write_block_first":
            mutant.setattr(Env, "write", write_block_first)
        if fault in {"probe_port_bool", "probe_clobber_dst"}:
            mutant.setattr(Env, "write", damaged_probe)
        with pytest.raises(AssertionError):
            observe_action(checked, "false-false-true-0-false", monkeypatch)
    assert hits == 1
    if fault in {"probe_port_bool", "probe_clobber_dst"}:
        assert probe_hits == 1


@pytest.mark.parametrize("fault", ["old_destination_order", "full_outer_restore", "saturating_ttl"])
def test_action_observer_rejects_semantic_faults(
    checked: apb.BlockAssembly, fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    execute, arithmetic = stmt.execute, expr.bits_binary
    hits = 0

    def damaged(body: Iterable[pb.Stmt], env: Env) -> None:
        nonlocal hits
        items = list(body)
        if env.action == "ipv4_forward":
            hits += 1
            if fault == "old_destination_order":
                items[1], items[2] = items[2], items[1]
            old = deepcopy(env.vars)
            execute(items, env)
            if fault == "full_outer_restore":
                env.vars.clear()
                env.vars.update(old)
        else:
            execute(items, env)

    def saturating(op: int, left: Bits, right: Bits) -> Value:
        if op == pb.BINARY_OP_SUB and left.width == 8:
            return Bits(8, max(0, left.value - right.value))
        return arithmetic(op, left, right)

    with monkeypatch.context() as mutant:
        mutant.setattr(stmt, "execute", damaged)
        if fault == "saturating_ttl":
            mutant.setattr(expr, "bits_binary", saturating)
        with pytest.raises(AssertionError, match="active completed state"):
            observe_action(checked, "true-true-false-0-false", monkeypatch)
    assert hits == 1


def test_python_action_wrong_arity(
    checked: apb.BlockAssembly, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = environment(checked, "true-true-false-1-false")
    before = freeze(env)

    def forbidden(*_: Any) -> Env:
        raise AssertionError("bad arity entered action storage")

    with monkeypatch.context() as spy:
        spy.setattr(Env, "enter_action", forbidden)
        bad = action_call("true-true-false-1-false")
        del bad.args[-1]
        with pytest.raises(InterpError, match="takes 2 arguments"):
            stmt.run_action_call(bad, env)
    assert freeze(env) == before


def test_lean_agrees_action_field_fault_replay(
    checked: apb.BlockAssembly,
    lean_binary: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = expr.write_lvalue
    hits = 0

    def omit_destination(lvalue: pb.LValue, value: Value, env: Env) -> None:
        nonlocal hits
        if env.action == "ipv4_forward" and lvalue == target("hdr", "ethernet", "dstAddr"):
            hits += 1
            return
        original(lvalue, value, env)

    program = checked
    case, expected = edge_case(0)
    bundle = tmp_path / "action-missing-destination.json"
    with monkeypatch.context() as mutant:
        mutant.setattr(stmt, "write_lvalue", omit_destination)
        # Retain the genuine mismatch before independent answer assertions.
        report = compare_program(program, [case], 4, [lean_binary])
        save(report, bundle)
        assert report.agreed == 0 and len(report.divergences) == 1 and hits == 1
        assert report.protocol_error is None and report.both_errored == 0
        assert replay.load(bundle) == (program, [case], 4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert live.agreed == 0 and len(live.divergences) == 1 and hits == 2
        mismatch = live.divergences[0]
        assert mismatch.lean.outputs == tuple(expected)
        wrong_packet = bytes.fromhex("000000000101") + expected[0][1][6:]
        assert mismatch.python.outputs == ((2, wrong_packet),)
        for outcome in [mismatch.python, mismatch.lean]:
            assert outcome.error is None and outcome.diagnostic is None
        with pytest.raises(AssertionError, match="active completed state"):
            observe_action(program, "true-true-false-0-false", monkeypatch)
        assert hits == 3
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1 and restored.both_errored == 0
