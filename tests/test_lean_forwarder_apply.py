"""Actual apply: independent full states and once-only key/lookup/action hooks.

The 30×9 routing inventory cycles the 24 stored-state boundaries, not their
full Cartesian product. The Lean theorem separately quantifies every store.
Every expected stage is frozen before execution; public apply returns normally.
"""

from __future__ import annotations

import itertools
import subprocess
import tomllib
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from google.protobuf import json_format

from p4blo import arch
from p4blo.drt import replay
from p4blo.drt._json import loads as strict_loads
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import stmt
from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.tables import InstalledEntries, Match, TableRef
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracle.bmv2 import run as bmv2_run
from tests.test_codec_leaves import same_json
from tests.test_lean_edsl_fields import target
from tests.test_lean_forwarder import assert_program_identity, freeze
from tests.test_lean_forwarder_action import environment as action_environment
from tests.test_lean_forwarder_action import run_json, selected_action
from tests.test_lean_forwarder_tables import (
    ADDRESSES,
    REF,
    SHAPES,
    call,
    encode,
    entry,
    expected,
    inputs,
    packet_case,
)
from tests.test_lean_forwarder_tables import PROFILES as ROUTES

ROOT = Path(__file__).resolve().parents[1]
STATES = list(itertools.product([False, True], [False, True], [False, True], [0, 1, 255]))
CASES = {
    f"{route}/{address}/{ordinal % 24}": (route, address, STATES[ordinal % 24])
    for ordinal, (route, address) in enumerate(itertools.product(ROUTES, ADDRESSES))
}
KEY = pb.Expr(
    member=pb.Member(
        base=pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field="ipv4")), field="dstAddr"
    )
)


def evaluator() -> Callable[[pb.Expr, Env], Value]:
    # Observe the actual binding used by apply/execute, including live faults;
    # importing expr.evaluate directly would bypass a replaced stmt binding.
    return stmt.evaluate  # pyright: ignore[reportPrivateImportUsage]


def writer() -> Callable[[pb.LValue, Value, Env], None]:
    return stmt.write_lvalue  # pyright: ignore[reportPrivateImportUsage]


def action(name: str) -> pb.ActionCall:
    route, address, _ = CASES[name]
    result = expected(route, address)
    assert result.action is not None
    return result.action


def environment(program: pb.Program, name: str, *, actual_entries: bool) -> Env:
    route, address, state = CASES[name]
    state_name = "-".join(str(v).lower() for v in (*state, False))
    env = action_environment(program, state_name)
    header = env.vars["hdr"]
    assert isinstance(header, Struct) and isinstance(header.fields[1], Header)
    header.fields[1].fields[11] = Bits(32, address)
    if actual_entries:
        env.entries = InstalledEntries.build(env.index, inputs(route))
    else:
        shape, mode, high = ROUTES[route]
        env.entries = InstalledEntries(
            env.index,
            {REF: [entry(which, high) for which in SHAPES[shape]]},
            {REF: call(mode, high)},
        )
    return env


def expected_runs(program: pb.Program, name: str) -> dict[str, Env]:
    before = environment(program, name, actual_entries=False)
    after = environment(program, name, actual_entries=False)
    selected = action(name)
    params: dict[str, Value] = {}
    meta = after.vars["meta"]
    header = after.vars["hdr"]
    assert isinstance(meta, Struct) and isinstance(header, Struct)
    ether, ipv4 = header.fields
    assert isinstance(ether, Header) and isinstance(ipv4, Header)
    if selected.action == "ipv4_forward":
        dst, port = (int(arg.bits.value) for arg in selected.args)
        params = {"dstAddr": Bits(48, dst), "port": Bits(9, port)}
        # Complete initial fields come from independent literal constructors;
        # these answers do not use authored Ref paths or the source policy.
        ether.fields[0] = Bits(48, dst)
        ether.fields[1] = Bits(48, 0x010203040506)
        ttl = CASES[name][2][3]
        ipv4.fields[7] = Bits(8, {0: 255, 1: 0, 255: 254}[ttl])
        meta.fields[1] = Bits(9, port)
    elif selected.action == "drop":
        meta.fields[2] = True
    else:
        assert selected.action == "NoAction"
    return {
        "before": before,
        "entered": replace(before, action=selected.action, action_vars=params),
        "activeEnd": replace(after, action=selected.action, action_vars=dict(params)),
        "after": after,
    }


def count(name: str) -> int:
    return {"ipv4_forward": 13, "drop": 7, "NoAction": 5}[action(name).action]


def body(program: pb.Program, name: str) -> list[pb.Stmt]:
    wanted = action(name).action
    declarations = next(block for block in program.blocks if block.name == "MyIngress")
    actual = next(a for a in declarations.actions if a.name == wanted)
    if wanted == "ipv4_forward":
        assert actual == selected_action(program)
    elif wanted == "drop":
        assert actual == pb.Action(
            name="drop",
            body=[
                pb.Stmt(
                    assign=pb.Assign(
                        target=target("meta", "drop"),
                        value=pb.Expr(literal=pb.Literal(boolean=True)),
                    )
                )
            ],
        )
    else:
        assert actual == pb.Action(name="NoAction")
    return list(actual.body)


def checked_snapshots(raw: Any) -> tuple[pb.Program, dict[str, Any]]:
    assert type(raw) is dict and set(raw) == {"program", "snapshots"}
    program = json_format.ParseDict(raw["program"], pb.Program())
    assert_program_identity(program)
    table = next(b for b in program.blocks if b.name == "MyIngress").tables[0]
    assert list(table.keys) == [pb.Key(expr=KEY, match_kind=pb.MATCH_KIND_LPM)]
    assert len(CASES) == 270 and len({state for _, _, state in CASES.values()}) == 24
    assert type(raw["snapshots"]) is list and len(raw["snapshots"]) == 270
    found: dict[str, Any] = {}
    for record in raw["snapshots"]:
        assert type(record) is dict and set(record) == {
            "name",
            "input",
            "call",
            "hit",
            "before",
            "entered",
            "activeEnd",
            "after",
            "steps",
        }
        name = record["name"]
        assert type(name) is str and name in CASES and name not in found
        route, address, _ = CASES[name]
        assert same_json(record["input"], encode(inputs(route))), "installed input identity"
        assert same_json(record["call"], encode(action(name))), "selected call identity"
        assert same_json(record["hit"], expected(route, address).hit), "selected hit"
        assert type(record["steps"]) is int and record["steps"] == count(name), "literal count"
        for phase, env in expected_runs(program, name).items():
            assert same_json(record[phase], run_json(env)), f"complete {phase}: {name}"
        found[name] = record
    assert set(found) == set(CASES)
    return program, found


@pytest.fixture(scope="module")
def export(lean_binary: Path) -> Any:
    assert lean_binary.is_file()
    process = subprocess.run(
        [str(ROOT / "lean/.lake/build/bin/forwarderApply")],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert process.stderr == "", "exporter stderr"
    return strict_loads(process.stdout)


@pytest.fixture(scope="module")
def checked(export: Any) -> tuple[pb.Program, dict[str, Any]]:
    return checked_snapshots(export)


def observe(program: pb.Program, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    outer = environment(program, name, actual_entries=True)
    frozen = {phase: freeze(env) for phase, env in expected_runs(program, name).items()}
    assert freeze(outer) == frozen["before"], "actual installer/initial state"
    route, address, _ = CASES[name]
    evaluate, lookup, run_action, execute = (
        evaluator(),
        InstalledEntries.lookup,
        stmt.run_action_call,
        stmt.execute,
    )
    counts = {"key": 0, "lookup": 0, "call": 0, "body": 0}
    retained: list[Env] = []

    def read_key(value: pb.Expr, env: Env) -> Value:
        if env is not outer or value != KEY:
            return evaluate(value, env)
        counts["key"] += 1
        assert freeze(env) == frozen["before"], "pre-key state"
        result = evaluate(value, env)
        assert freeze(result) == freeze(Bits(32, address)), "independent key answer"
        assert freeze(env) == frozen["before"], "key read changed state"
        return result

    def find(self: InstalledEntries, ref: TableRef, keys: list[Bits]) -> Match:
        counts["lookup"] += 1
        assert self is outer.entries and ref == REF
        assert freeze(keys) == freeze([Bits(32, address)]), "lookup key identity"
        result = lookup(self, ref, keys)
        assert freeze(keys) == freeze([Bits(32, address)]), "lookup changed key"
        assert freeze(result) == freeze(expected(route, address)), "independent selected match"
        assert freeze(outer) == frozen["before"], "lookup changed complete state"
        return result

    def selected(selected_call: pb.ActionCall, env: Env) -> None:
        counts["call"] += 1
        assert env is outer and selected_call == action(name), "actual selected call"
        assert freeze(env) == frozen["before"], "pre-action state"
        assert run_action(selected_call, env) is None
        assert freeze(env) == frozen["after"], "post-action state"

    def action_body(statements: Iterable[pb.Stmt], inner: Env) -> None:
        counts["body"] += 1
        retained.append(inner)
        assert list(statements) == body(program, name), "actual action body"
        assert freeze(inner) == frozen["entered"], "active entry state"
        assert execute(statements, inner) is None
        assert freeze(inner) == frozen["activeEnd"], "active completed state"

    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "evaluate", read_key)
        hooks.setattr(InstalledEntries, "lookup", find)
        hooks.setattr(stmt, "run_action_call", selected)
        hooks.setattr(stmt, "execute", action_body)
        assert stmt.apply(pb.Apply(table="ipv4_lpm"), outer) is None
    assert counts == {"key": 1, "lookup": 1, "call": 1, "body": 1}, "actual operation counts"
    assert freeze(outer) == frozen["after"], "normal application result"
    assert retained[0] is not outer and retained[0].vars is outer.vars
    assert outer.action is None and outer.action_vars is None


@pytest.mark.parametrize("name", CASES)
def test_lean_agrees_forwarder_apply(
    checked: tuple[pb.Program, dict[str, Any]],
    name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    program, snapshots = checked
    assert name in snapshots
    observe(program, name, monkeypatch)


def test_forwarder_apply_default_targets() -> None:
    package = tomllib.loads((ROOT / "lean/lakefile.toml").read_text())
    assert {"forwarderApply", "UserProofAudit"} <= set(package["defaultTargets"])


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "count",
        "hit-int",
        "wrong-call",
        "cursor",
        "entries",
        "scope",
        "layer",
        "paired-query",
    ],
)
def test_lean_agrees_apply_snapshot_negatives(export: Any, fault: str) -> None:
    bad = deepcopy(export)
    record = bad["snapshots"][0]
    if fault == "missing":
        bad["snapshots"].pop()
    elif fault == "duplicate":
        bad["snapshots"][1] = record
    elif fault == "count":
        record["steps"] -= 1
    elif fault == "hit-int":
        record["hit"] = 0
    elif fault == "wrong-call":
        record["call"] = encode(call("noop"))
    elif fault == "cursor":
        record["after"]["packet"][2] = 3.0
    elif fault == "entries":
        record["after"]["entries"]["entries"].clear()
    elif fault == "scope":
        record["entered"]["frame"]["scope"]["actions"].clear()
    elif fault == "layer":
        record["after"]["frame"]["action"] = "drop"
    else:
        for phase in ["before", "entered", "activeEnd", "after"]:
            record[phase]["frame"]["vars"]["hdr"][2][1][3][11][2] = 1
    with pytest.raises(AssertionError):
        checked_snapshots(bad)


def profile(route: str, address: int) -> str:
    return next(name for name, (r, q, _) in CASES.items() if r == route and q == address)


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
def test_lean_agrees_apply_observer_faults(
    checked: tuple[pb.Program, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    program, _ = checked
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
def test_lean_agrees_apply_hit_and_error_controls(
    checked: tuple[pb.Program, dict[str, Any]],
    name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Different operational target, not the original body's absent hit field."""
    program, _ = checked
    env = environment(program, name, actual_entries=True)
    env.entries = InstalledEntries.build(env.index)
    pending, after = deepcopy(env), deepcopy(env)
    for state, value in [(pending, True), (after, False)]:
        meta = state.vars["meta"]
        assert isinstance(meta, Struct)
        meta.fields[2] = value
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
            assert lvalue == target("meta", "drop") and freeze(value) == freeze(False)
            assert freeze(current) == frozen_pending
            assert write(lvalue, value, current) is None
            assert freeze(current) == frozen_after
            counts["hit"] += 1
        else:
            write(lvalue, value, current)

    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "run_action_call", returned)
        hooks.setattr(stmt, "write_lvalue", hit_write)
        assert stmt.apply(pb.Apply(table="ipv4_lpm", hit=target("meta", "drop")), env) is None
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
    bad_before = freeze(bad)
    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "write_lvalue", forbidden)
        with pytest.raises(InterpError, match="action 'ipv4_forward' takes 2 arguments"):
            stmt.apply(pb.Apply(table="ipv4_lpm", hit=target("meta", "drop")), bad)
    assert freeze(bad) == bad_before


PACKET_PROFILES = [
    "network-host/drop/false",
    "host-network/drop/false",
    "empty/drop/false",
    "empty/noop/false",
    "empty/forward/false",
]


def application_packet(name: str) -> Case:
    return replace(packet_case(), entries=inputs(name))


def application_output(name: str) -> list[tuple[int, bytes]]:
    """Literal whole-packet anchors; checksum execution is tested, not proved here."""
    if name == "empty/drop/false":
        return []
    if name == "empty/noop/false":
        return [
            (
                0,
                bytes.fromhex(
                    "00000000010100000000000108004500001a000100000011a3d00a0001010a000202deadbeefcafe"
                ),
            )
        ]
    port, destination = (
        (1, "444444444444") if name == "empty/forward/false" else (3, "333333333333")
    )
    return [
        (
            port,
            bytes.fromhex(
                destination + "00000000010108004500001a00010000ff11a4cf0a0001010a000202deadbeefcafe"
            ),
        )
    ]


@pytest.mark.parametrize("name", PACKET_PROFILES)
def test_lean_agrees_apply_packets(
    checked: tuple[pb.Program, dict[str, Any]], lean_binary: Path, name: str
) -> None:
    program, _ = checked
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
    assert run_python(arch.load(program), case, 4) == application_output(name)


def test_lean_agrees_skip_default_packet_replay(
    checked: tuple[pb.Program, dict[str, Any]],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    program, _ = checked
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
    verdicts = bmv2_run.run(image, ROOT / "tests/corpus/forwarder/forwarder.txtpb", vectors)
    assert len(verdicts) == 5 and {v.vector for v in verdicts} == set(vectors)
    assert all(v.status == "pass" for v in verdicts), "\n".join(map(str, verdicts))
