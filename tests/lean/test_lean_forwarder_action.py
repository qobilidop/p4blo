"""Actual selected table action, not direct calls or the whole pipeline.

Snapshots are validated once per module. Python completes normally through
run_action_call; the execution hook observes entry/exit without throwing a
sentinel or reimplementing the action. Operational parameter-name decoys are
not claimed to be validator-accepted block declarations.
"""

from __future__ import annotations

import itertools
import json
import subprocess
import tomllib
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from google.protobuf import json_format

from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt._json import loads as strict_loads
from p4blo.drt.replay import save
from p4blo.drt.run import compare_program
from p4blo.interp import expr, stmt
from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.codec.test_codec_leaves import same_json
from tests.lean.test_lean_call_return import run_json as return_run_json
from tests.lean.test_lean_edsl_fields import target
from tests.lean.test_lean_forwarder import assert_program_identity, edge_case, freeze

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {
    "-".join(str(v).lower() for v in values): values
    for values in itertools.product(
        [False, True], [False, True], [False, True], [0, 1, 255], [False, True]
    )
}


def destinations(name: str) -> tuple[int, int]:
    return (0xFFFFFFFFFFFE, 511) if PROFILES[name][4] else (0x020202020202, 2)


def values(name: str, *, final: bool = False) -> dict[str, Value]:
    ev, iv, drop, ttl, _ = PROFILES[name]
    dst, port = destinations(name)
    return {
        "hdr": Struct(
            "headers",
            [
                Header(
                    "ethernet_t",
                    ev,
                    [
                        Bits(48, dst if final else 0x010203040506),
                        Bits(48, 0x010203040506 if final else 0x111213141516),
                        Bits(16, 0x0800),
                    ],
                ),
                Header(
                    "ipv4_t",
                    iv,
                    [
                        Bits(4, 4),
                        Bits(4, 5),
                        Bits(8, 17),
                        Bits(16, 26),
                        Bits(16, 37),
                        Bits(3, 5),
                        Bits(13, 47),
                        Bits(8, ({0: 255, 1: 0, 255: 254}[ttl] if final else ttl)),
                        Bits(8, 17),
                        Bits(16, 0x9876),
                        Bits(32, 0x0A000101),
                        Bits(32, 0x0A000202),
                    ],
                ),
            ],
        ),
        "meta": Struct("metadata", [Bits(9, 3), Bits(9, port if final else 7), drop]),
        "untouched": Bits(8, 165),
        "dstAddr": Bits(48, 99),
        "port": Bits(9, 77),
    }


def action_call(name: str) -> pb.ActionCall:
    dst, port = destinations(name)
    return pb.ActionCall(
        action="ipv4_forward",
        args=[
            pb.Literal(bits=pb.BitsLiteral(width=48, value=str(dst))),
            pb.Literal(bits=pb.BitsLiteral(width=9, value=str(port))),
        ],
    )


def parameters(name: str) -> dict[str, Value]:
    dst, port = destinations(name)
    return {"dstAddr": Bits(48, dst), "port": Bits(9, port)}


def environment(program: apb.BlockAssembly, name: str) -> Env:
    index = BoundIndex.build(program)
    entries = InstalledEntries(index)
    entries.entries[("MyIngress", "ipv4_lpm")] = [
        pb.Entry(
            keys=[pb.KeyValue(lpm=pb.LpmValue(value="167772672", prefix_len=24))],
            action=pb.ActionCall(action="drop"),
            priority=7,
        )
    ]
    entries.default_actions[("MyIngress", "ipv4_lpm")] = pb.ActionCall(action="NoAction")
    register = Register(3, 8)
    register.cells[:] = [Bits(8, n) for n in [3, 9, 27]]
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.write(3, 5)
    env = Env.for_block(
        index,
        index.blocks["MyIngress"],
        {"sentinel": register},
        entries=entries,
        packet=packet,
        emitter=emitter,
        visits={("parser", "state"): 13, ("sentinel", "one"): 1},
    )
    env.vars.update(values(name))
    return env


def expected_runs(program: apb.BlockAssembly, name: str) -> dict[str, Env]:
    before = environment(program, name)
    after = environment(program, name)
    after.vars.update(values(name, final=True))
    return {
        "before": before,
        "after": after,
        "entered": replace(before, action="ipv4_forward", action_vars=parameters(name)),
        "pending": replace(after, action="ipv4_forward", action_vars=parameters(name)),
    }


def run_json(env: Env) -> dict[str, Any]:
    result = return_run_json(env)
    assert env.entries is not None
    # The reused return profile had no nested LPM names. Match the public
    # wire spelling here without weakening or changing its shared helper.
    result["entries"]["entries"] = {
        json.dumps(key, separators=(",", ":")): [
            json_format.MessageToDict(entry, preserving_proto_field_name=True) for entry in entries
        ]
        for key, entries in env.entries.entries.items()
    }
    return result


def selected_action(program: apb.BlockAssembly) -> pb.Action:
    action = next(
        a
        for b in program.blocks
        if b.name == "MyIngress"
        for a in b.actions
        if a.name == "ipv4_forward"
    )

    # The complete literal four-statement anchor is independent of candidate
    # policy, lowered Ref paths and any projection of its own body.
    def member(*path: str) -> pb.Expr:
        result = pb.Expr(var=path[0])
        for field in path[1:]:
            result = pb.Expr(member=pb.Member(base=result, field=field))
        return result

    def assign(path: tuple[str, ...], value: pb.Expr) -> pb.Stmt:
        return pb.Stmt(assign=pb.Assign(target=target(*path), value=value))

    expected = pb.Action(
        name="ipv4_forward",
        params=[
            pb.Param(name="dstAddr", type=pb.Type(bits=48), direction=pb.DIRECTION_NONE),
            pb.Param(name="port", type=pb.Type(bits=9), direction=pb.DIRECTION_NONE),
        ],
        body=[
            assign(("meta", "egress_port"), pb.Expr(var="port")),
            assign(("hdr", "ethernet", "srcAddr"), member("hdr", "ethernet", "dstAddr")),
            assign(("hdr", "ethernet", "dstAddr"), pb.Expr(var="dstAddr")),
            assign(
                ("hdr", "ipv4", "ttl"),
                pb.Expr(
                    binary=pb.Binary(
                        op=pb.BINARY_OP_SUB,
                        left=member("hdr", "ipv4", "ttl"),
                        right=pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=8, value="1"))),
                    )
                ),
            ),
        ],
    )
    assert action == expected, "actual parameter/body identity"
    return action


def checked_snapshots(export: Any) -> tuple[apb.BlockAssembly, dict[str, Any]]:
    assert type(export) is dict and set(export) == {"program", "action", "snapshots"}
    program = json_format.ParseDict(export["program"], apb.BlockAssembly())
    assert_program_identity(program)
    assert json_format.ParseDict(export["action"], pb.Action()) == selected_action(program)
    snapshots = export["snapshots"]
    assert type(snapshots) is list and len(snapshots) == 48, "snapshot count"
    found: dict[str, Any] = {}
    for snapshot in snapshots:
        assert type(snapshot) is dict and set(snapshot) == {
            "name",
            "call",
            "before",
            "entered",
            "pending",
            "after",
            "steps",
        }
        name = snapshot["name"]
        assert type(name) is str and name in PROFILES and name not in found, "snapshot identity"
        assert type(snapshot["steps"]) is int and snapshot["steps"] == 11, "literal count"
        assert same_json(snapshot["call"], json_format.MessageToDict(action_call(name))), (
            "literal bindings"
        )
        for phase, expected in expected_runs(program, name).items():
            assert same_json(snapshot[phase], run_json(expected)), f"independent {phase}: {name}"
        found[name] = snapshot
    assert set(found) == set(PROFILES)
    return program, found


@pytest.fixture(scope="module")
def action_export(lean_binary: Path) -> Any:
    assert lean_binary.is_file()
    process = subprocess.run(
        [str(ROOT / "impl/lean/.lake/build/bin/p4blo"), "forwarderAction"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.stderr == "", "action exporter stderr"
    return strict_loads(process.stdout)


@pytest.fixture(scope="module")
def checked(action_export: Any) -> tuple[apb.BlockAssembly, dict[str, Any]]:
    return checked_snapshots(action_export)


def observe_action(program: apb.BlockAssembly, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    outer = environment(program, name)
    expectations = expected_runs(program, name)
    frozen = {phase: freeze(env) for phase, env in expectations.items()}
    probe = replace(expectations["pending"], action_vars=parameters(name))
    assert probe.action_vars is not None
    probe.action_vars["port"] = Bits(9, 1)
    expected_first_write = freeze(probe)
    probe.action_vars["dstAddr"] = Bits(48, 23)
    expected_second_write = freeze(probe)
    original = stmt.execute
    observed: list[Env] = []

    def observe(body: Iterable[pb.Stmt], inner: Env) -> None:
        observed.append(inner)
        assert list(body) == list(selected_action(program).body), "selected body identity"
        assert freeze(inner) == frozen["entered"], "active entry state"
        assert {key: freeze(inner.read(key)) for key in parameters(name)} == {
            key: freeze(value) for key, value in parameters(name).items()
        }, "parameter precedence"
        assert original(body, inner) is None
        assert freeze(inner) == frozen["pending"], "active completed state"

    with monkeypatch.context() as spy:
        spy.setattr(stmt, "execute", observe)
        assert stmt.run_action_call(action_call(name), outer) is None
    assert len(observed) == 1, "actual table-action execution hook"
    assert freeze(outer) == frozen["after"], "normal returned state"
    inner = observed[0]
    assert inner is not outer and inner.vars is outer.vars, "shared block store"
    assert inner.action_vars is not outer.action_vars and outer.action_vars is None
    assert outer.read("dstAddr") == Bits(48, 99) and outer.read("port") == Bits(9, 77)
    # Post-observation writes exercise the actual action-hit write branch.
    # They must not overwrite the same-named operational block decoys.
    inner.write("port", Bits(9, 1))
    assert freeze(inner) == expected_first_write, "first parameter write damaged active state"
    assert freeze(outer) == frozen["after"], "first parameter write leaked into block state"
    inner.write("dstAddr", Bits(48, 23))
    assert freeze(inner) == expected_second_write, "second parameter write damaged active state"
    assert freeze(outer) == frozen["after"], "parameter writes leaked into the block layer"


def test_forwarder_action_default_target() -> None:
    package = tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


@pytest.mark.parametrize("name", PROFILES)
def test_lean_agrees_forwarder_action(
    checked: tuple[apb.BlockAssembly, dict[str, Any]], name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    program, snapshots = checked
    assert name in snapshots
    observe_action(program, name, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "missing",
        "count_bool",
        "count_short",
        "cursor_float",
        "visit_bool",
        "entry_clear",
        "scope_clear",
        "parameter_swap",
        "paired_mac",
        "return_layer",
    ],
)
def test_action_snapshot_observer_rejects_faults(action_export: Any, fault: str) -> None:
    broken = deepcopy(action_export)
    record = broken["snapshots"][0]
    if fault == "duplicate":
        broken["snapshots"][1] = record
    elif fault == "missing":
        broken["snapshots"].pop()
    elif fault == "count_bool":
        record["steps"] = True
    elif fault == "count_short":
        record["steps"] = 10
    elif fault == "cursor_float":
        record["after"]["packet"][2] = 3.0
    elif fault == "visit_bool":
        record["after"]["visits"]['["sentinel","one"]'] = True
    elif fault == "entry_clear":
        record["after"]["entries"]["entries"] = {}
    elif fault == "scope_clear":
        record["after"]["frame"]["scope"]["actions"] = {}
    elif fault == "parameter_swap":
        record["call"]["args"].reverse()
    elif fault == "paired_mac":
        for phase in ["before", "entered", "pending", "after"]:
            fields = record[phase]["frame"]["vars"]["hdr"][2][0][3]
            fields[0], fields[1] = fields[1], fields[0]
    else:
        record["after"]["frame"]["action"] = "ipv4_forward"
    with pytest.raises(AssertionError):
        checked_snapshots(broken)


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
    checked: tuple[apb.BlockAssembly, dict[str, Any]], fault: str, monkeypatch: pytest.MonkeyPatch
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
            observe_action(checked[0], "false-false-true-0-false", monkeypatch)
    assert hits == 1
    if fault in {"probe_port_bool", "probe_clobber_dst"}:
        assert probe_hits == 1


@pytest.mark.parametrize("fault", ["old_destination_order", "full_outer_restore", "saturating_ttl"])
def test_action_observer_rejects_semantic_faults(
    checked: tuple[apb.BlockAssembly, dict[str, Any]], fault: str, monkeypatch: pytest.MonkeyPatch
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
            observe_action(checked[0], "true-true-false-0-false", monkeypatch)
    assert hits == 1


def test_lean_agrees_action_wrong_arity(
    checked: tuple[apb.BlockAssembly, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    env = environment(checked[0], "true-true-false-1-false")
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
    checked: tuple[apb.BlockAssembly, dict[str, Any]],
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

    program = checked[0]
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
