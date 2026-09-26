"""Actual apply with independent states and key/lookup/action observations.

The 30 by 9 routing inventory cycles the 24 stored-state boundaries. Every
expected stage is frozen before execution; public apply returns normally.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from p4blo.arch import v1model
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import stmt
from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.tables import InstalledEntries, Match, TableRef
from p4blo.interp.values import Bits, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracles.bmv2 import run as bmv2_run
from tests.programs.ir_helpers import target
from tests.support.forwarder import freeze
from tests.support.forwarder_apply import (
    CASES,
    KEY,
    PACKET_PROFILES,
    ROOT,
    application_output,
    application_packet,
    environment,
    evaluator,
    observe,
    profile,
    writer,
)
from tests.support.forwarder_apply import (
    checked as checked,
)
from tests.support.forwarder_tables import (
    REF,
    call,
    expected,
)


@pytest.mark.parametrize("name", CASES)
def test_python_forwarder_apply(
    checked: apb.BlockAssembly,
    name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    program = checked
    observe(program, name, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-key",
        "duplicate-key",
        "key-sibling",
        "key-cursor",
        "lookup-map",
        "skip-default",
        "leak-layer",
        "restore-outer",
    ],
)
def test_python_apply_observer_faults(
    checked: apb.BlockAssembly,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    program = checked
    name = (
        profile("empty/drop/false", 0)
        if fault == "skip-default"
        else profile("network-host/drop/false", 0x0A000202)
    )
    evaluate, apply, lookup, run_action = (
        evaluator(),
        stmt.apply,
        InstalledEntries.lookup,
        stmt.run_action_call,
    )
    hits = 0

    def bad_read(value: pb.Expr, env: Env) -> Value:
        nonlocal hits
        answer = evaluate(value, env)
        if value == KEY:
            hits += 1
            if fault == "wrong-key":
                return Bits(32, 0x0A000101)
            if fault == "key-sibling":
                meta = env.vars["meta"]
                assert isinstance(meta, Struct)
                meta.fields[0] = Bits(9, 7)
            if fault == "key-cursor":
                assert env.packet is not None
                env.packet.cursor = float(env.packet.cursor)  # type: ignore[assignment]
        return answer

    def bad_apply(ap: pb.Apply, env: Env) -> None:
        nonlocal hits
        hits += 1
        evaluator()(KEY, env)
        return apply(ap, env)

    def bad_lookup(self: InstalledEntries, table: TableRef, keys: list[Bits]) -> Match:
        nonlocal hits
        hits += 1
        answer = lookup(self, table, keys)
        self.default_actions[table] = call("noop")
        return answer

    def bad_action(selected: pb.ActionCall, env: Env) -> None:
        nonlocal hits
        if fault == "skip-default":
            assert selected.action == "drop"
            hits += 1
            return None
        before = deepcopy(env.vars)
        run_action(selected, env)
        hits += 1
        if fault == "leak-layer":
            env.action_vars = {"leak": True}
        else:
            env.vars = before

    with monkeypatch.context() as patch:
        if fault in {"wrong-key", "key-sibling", "key-cursor"}:
            patch.setattr(stmt, "evaluate", bad_read)
        elif fault == "duplicate-key":
            patch.setattr(stmt, "apply", bad_apply)
        elif fault == "lookup-map":
            patch.setattr(InstalledEntries, "lookup", bad_lookup)
        else:
            patch.setattr(stmt, "run_action_call", bad_action)
        if fault in {"key-sibling", "key-cursor"}:
            weak = environment(program, name, actual_entries=True)
            before = freeze(weak)
            answer = evaluator()(KEY, weak)
            assert freeze(answer) == freeze(Bits(32, CASES[name][1]))
            assert weak.entries is not None
            chosen = weak.entries.lookup(REF, [Bits(32, CASES[name][1])])
            assert freeze(chosen) == freeze(expected(CASES[name][0], CASES[name][1]))
            assert freeze(weak) != before and hits == 1
        with pytest.raises(AssertionError):
            observe(program, name, monkeypatch)
    assert hits > 0


@pytest.mark.parametrize("name", list(CASES)[:24])
def test_python_apply_hit_and_error_controls(
    checked: apb.BlockAssembly,
    name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Different operational target, not the original body's absent hit field."""
    program = checked
    env = environment(program, name, actual_entries=True)
    env.entries = InstalledEntries.build(env.index)
    # Hit is an ordinary boolean target, separate from v1model's bit<9> fate.
    env.vars["hit"] = True
    pending, after = deepcopy(env), deepcopy(env)
    for state in (pending, after):
        meta = state.vars["meta"]
        assert isinstance(meta, Struct)
        meta.fields[1] = Bits(9, 511)
    after.vars["hit"] = False
    frozen_pending, frozen_after = freeze(pending), freeze(after)
    action_call, write = stmt.run_action_call, writer()
    counts = {"action": 0, "hit": 0}

    def returned(selected: pb.ActionCall, current: Env) -> None:
        assert current is env and selected == call("drop")
        assert action_call(selected, current) is None
        assert freeze(current) == frozen_pending, "drop must precede the hit write"
        counts["action"] += 1

    def hit_write(lvalue: pb.LValue, value: Value, current: Env) -> None:
        if current is env:
            assert counts == {"action": 1, "hit": 0}, "hit timing/count"
            assert lvalue == target("hit") and freeze(value) == freeze(False)
            assert freeze(current) == frozen_pending
            assert write(lvalue, value, current) is None
            assert freeze(current) == frozen_after
            counts["hit"] += 1
        else:
            write(lvalue, value, current)

    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "run_action_call", returned)
        hooks.setattr(stmt, "write_lvalue", hit_write)
        assert stmt.apply(pb.Apply(table="ipv4_lpm", hit=target("hit")), env) is None
    assert counts == {"action": 1, "hit": 1} and freeze(env) == frozen_after

    # These raw operational maps are NOT accepted original-program host configurations.
    absent = environment(program, name, actual_entries=True)
    absent.entries = InstalledEntries(absent.index, {REF: []}, {REF: None})
    absent_before = freeze(absent)
    with monkeypatch.context() as hooks:

        def forbidden(*_: object) -> None:
            pytest.fail("an absent optional action must not invoke an action")

        hooks.setattr(stmt, "run_action_call", forbidden)
        assert stmt.apply(pb.Apply(table="ipv4_lpm"), absent) is None
    assert freeze(absent) == absent_before

    bad = environment(program, name, actual_entries=True)
    bad.entries = InstalledEntries(
        bad.index, {REF: []}, {REF: pb.ActionCall(action="ipv4_forward")}
    )
    bad.vars["hit"] = True
    bad_before = freeze(bad)
    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "write_lvalue", forbidden)
        with pytest.raises(InterpError, match="action 'ipv4_forward' takes 2 arguments"):
            stmt.apply(pb.Apply(table="ipv4_lpm", hit=target("hit")), bad)
    assert freeze(bad) == bad_before


@pytest.mark.parametrize("name", PACKET_PROFILES)
@pytest.mark.lean
def test_lean_agrees_apply_packets(
    checked: apb.BlockAssembly, lean_binary: Path, name: str
) -> None:
    program = checked
    case = application_packet(name)
    bundle = ROOT / ".artifacts/drt" / ("forwarder-apply-" + name.replace("/", "-") + ".json")
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is not None:
            bundle.parent.mkdir(parents=True, exist_ok=True)
            save(error.report, bundle)
        raise
    if not report.passed:
        bundle.parent.mkdir(parents=True, exist_ok=True)
        save(report, bundle)
    assert report.passed and report.agreed == 1
    assert run_python(v1model.load(program), case, 4) == application_output(name)


@pytest.mark.lean
def test_lean_agrees_skip_default_packet_replay(
    checked: apb.BlockAssembly,
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    program = checked
    name = "empty/drop/false"
    case = application_packet(name)
    original = stmt.run_action_call
    hits = 0

    def skip_drop(selected: pb.ActionCall, env: Env) -> None:
        nonlocal hits
        if env.block.name == "MyIngress" and selected.action == "drop":
            hits += 1
            return
        original(selected, env)

    bundle = tmp_path / "skipped-default.json"
    with monkeypatch.context() as fault:
        fault.setattr(stmt, "run_action_call", skip_drop)
        internal_name = next(n for n in CASES if n.startswith(name + "/"))
        with pytest.raises(AssertionError):
            observe(program, internal_name, monkeypatch)
        assert hits == 1
        report = compare_program(program, [case], 4, [lean_binary])
        save(report, bundle)
        assert hits == 2 and report.agreed == 0 and len(report.divergences) == 1
        assert report.protocol_error is None and report.both_errored == 0
        restored_program, cases, ports, seed = replay.load(bundle)
        assert restored_program == program and cases == [case] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert hits == 3 and live.agreed == 0 and len(live.divergences) == 1
        divergence = live.divergences[0]
        assert divergence.lean.outputs == ()
        assert divergence.python.outputs == tuple(application_output("empty/noop/false"))
        for outcome in [divergence.python, divergence.lean]:
            assert outcome.error is None and outcome.diagnostic is None
        assert divergence.python.state == divergence.lean.state
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1 and restored.both_errored == 0


@pytest.mark.bmv2
def test_apply_packets_bmv2(tmp_path: Path) -> None:
    """Independent immutable oracle: both overlap orders and three defaults."""
    image = bmv2_run.default_image()
    reason = bmv2_run.unavailable(image)
    if reason is not None:
        pytest.skip(f"BMv2 application profile unavailable: {reason}")
    vectors: list[Path] = []
    network = (
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:0x222222222222, port:2)"
    )
    host = (
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000202/32 ipv4_forward(dstAddr:0x333333333333, port:3)"
    )
    installations = [
        [network, host],
        [host, network],
        [],
        ["setdefault ipv4_lpm NoAction()"],
        ["setdefault ipv4_lpm ipv4_forward(dstAddr:0x444444444444, port:1)"],
    ]
    for name, commands in zip(PACKET_PROFILES, installations, strict=True):
        case = application_packet(name)
        lines = [*commands, f"packet {case.ingress_port} {case.packet.hex()}"]
        lines.extend(f"expect {port} {packet.hex()}$" for port, packet in application_output(name))
        vector = tmp_path / (name.replace("/", "-") + ".stf")
        vector.write_text("\n".join(lines) + "\n")
        vectors.append(vector)
    verdicts = bmv2_run.run(
        image, ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb", vectors
    )
    assert len(verdicts) == 5 and {v.vector for v in verdicts} == set(vectors)
    assert all(v.status == "pass" for v in verdicts), "\n".join(map(str, verdicts))
