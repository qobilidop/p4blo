"""Actual guarded call prefix, observed before suffix and finally-copyback."""

from __future__ import annotations

import itertools
import json
import subprocess
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from google.protobuf import json_format

from p4blo.arch.externs.register import Register
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_lean_call_body_entry import assert_selected_body
from tests.test_lean_call_entry import independent_values, shared_snapshot, value_json
from tests.test_lean_edsl_fields import target
from tests.test_lean_edsl_guarded_forwarding import (
    INPUTS,
    PAYLOAD,
    expected_packet,
    exported_programs,
)
from tests.test_lean_edsl_guarded_forwarding import (
    test_lean_agrees_on_guarded_forwarding as check_packet,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = list(itertools.product(INPUTS, [False, True]))


def source_values(name: str, prior_drop: bool) -> dict[str, Value]:
    ev, iv, hit, ttl = INPUTS[name]
    return {
        "hdr": Struct(
            "Headers",
            [
                Header(
                    "Ethernet",
                    ev,
                    [Bits(48, 0x112233445566), Bits(48, 0x778899AABBCC), Bits(16, 0x86DD)],
                ),
                Header("IPv4", iv, [Bits(8, ttl), Bits(8, 17), Bits(16, 0xFEDC)]),
            ],
        ),
        "meta": Struct("Metadata", [Bits(9, 509), prior_drop, Bits(16, 0x9876)]),
        "route": Struct(
            "Route", [hit, Bits(48, 0x123456789ABC), Bits(48, 0xCBA987654321), Bits(9, 511)]
        ),
        "observer": independent_values(ev, iv)["observer"],
        "scratch": Bits(8, 0),
        "unrelated": Bits(8, 0),
    }


def expected_values(name: str, prior_drop: bool) -> dict[str, Value]:
    values = source_values(name, prior_drop)
    ev, iv, hit, ttl = INPUTS[name]
    answer = {(True, True, True, 2): 1, (True, True, True, 255): 254}.get((ev, iv, hit, ttl))
    metadata = values["meta"]
    headers = values["hdr"]
    assert isinstance(metadata, Struct) and isinstance(headers, Struct)
    metadata.fields[1] = True
    if answer is not None:
        ethernet, ipv4 = headers.fields
        assert isinstance(ethernet, Header) and isinstance(ipv4, Header)
        ethernet.fields[:2] = [Bits(48, 0x123456789ABC), Bits(48, 0xCBA987654321)]
        ipv4.fields[0] = Bits(8, answer)
        metadata.fields[:2] = [Bits(9, 511), False]
    values["scratch"], values["unrelated"] = Bits(8, 19), Bits(8, 165)
    return values


def normalized(values: dict[str, Value]) -> dict[str, Any]:
    return {key: value_json(value) for key, value in values.items()}


def strict_equal(found: Any, expected: Any) -> bool:
    return json.dumps(found, sort_keys=True) == json.dumps(expected, sort_keys=True)


def strict_snapshot_equal(found: Any, expected: Any) -> bool:
    """Immutable snapshot tuples keep exact scalar/container types, including bytes."""
    if type(found) is not type(expected):
        return False
    if isinstance(expected, tuple):
        return len(found) == len(expected) and all(
            strict_snapshot_equal(left, right) for left, right in zip(found, expected, strict=True)
        )
    return found == expected


def expected_count(name: str) -> int:
    ev, iv, hit, ttl = INPUTS[name]
    if not ev:
        return 11
    if not iv:
        return 14
    if not hit:
        return 17
    return {0: 20, 1: 23, 2: 31, 255: 31}[ttl]


@pytest.fixture(scope="module")
def prefix_export(lean_binary: Path) -> dict[str, Any]:
    assert lean_binary.is_file()
    return json.loads(
        subprocess.run(
            [str(ROOT / "lean/.lake/build/bin/guardedCallPrefix")],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    )


def test_guarded_call_prefix_is_default() -> None:
    package = tomllib.loads((ROOT / "lean/lakefile.toml").read_text())
    assert {"guardedCallPrefix", "UserProofAudit"} <= set(package["defaultTargets"])


def checked_snapshots(export: dict[str, Any]) -> dict[tuple[str, bool], dict[str, Any]]:
    program, call = assert_selected_body(export)
    block = next(b for b in program.blocks if b.name == "RewriteBody")
    snapshots = export["snapshots"]
    assert isinstance(snapshots, list) and len(snapshots) == 64, "snapshot count"
    found: dict[tuple[str, bool], dict[str, Any]] = {}
    for snapshot in snapshots:
        assert set(snapshot) == {
            "name",
            "priorDrop",
            "steps",
            "faultNone",
            "vars",
            "scopeBlock",
            "queue",
            "packet",
            "emitter",
        }
        name, prior_drop = snapshot["name"], snapshot["priorDrop"]
        assert type(name) is str and name in INPUTS
        assert type(prior_drop) is bool and (name, prior_drop) not in found, "snapshot key"
        assert type(snapshot["faultNone"]) is bool and snapshot["faultNone"], "snapshot fault"
        assert type(snapshot["steps"]) is int and snapshot["steps"] == expected_count(name)
        assert strict_equal(
            snapshot["vars"], normalized(expected_values(name, prior_drop)) | {"caller_only": None}
        ), "prefix values"
        assert json_format.ParseDict(snapshot["scopeBlock"], pb.Block()) == block
        queue = snapshot["queue"]
        assert set(queue) == {"suffix", "params", "args", "caller"}
        assert [json_format.ParseDict(s, pb.Stmt()) for s in queue["suffix"]] == list(
            block.body[3:]
        )
        assert [json_format.ParseDict(p, pb.Param()) for p in queue["params"]] == list(block.params)
        assert [json_format.ParseDict(a, pb.Arg()) for a in queue["args"]] == list(call.args)
        values = source_values(name, prior_drop)
        caller = {
            "source_hdr": values["hdr"],
            "source_meta": values["meta"],
            "source_route": values["route"],
            "hdr": values["observer"],
            "caller_only": Bits(9, 301),
        }
        assert strict_equal(queue["caller"], normalized(caller)), "captured caller changed"
        assert strict_equal(snapshot["packet"], [[222, 173, 190, 239], 0xDEADBEEF, 3])
        assert strict_equal(snapshot["emitter"], [5, 3])
        found[name, prior_drop] = snapshot
    assert set(found) == set(CASES)
    return found


class PrefixStopped(Exception):
    """Test-only stop after snapshot; call_block still runs its finally."""


def observe_python_prefix(
    export: dict[str, Any],
    name: str,
    prior_drop: bool,
    monkeypatch: pytest.MonkeyPatch,
    *,
    early_observer: bool = False,
) -> None:
    program, call = assert_selected_body(export)
    block = next(b for b in program.blocks if b.name == "RewriteBody")
    first_observer = block.body[3]
    assert sum(s == first_observer for s in block.body) == 1
    values = source_values(name, prior_drop)
    expected = normalized(expected_values(name, prior_drop))
    index = Index.build(program)
    packet = Packet(PAYLOAD)
    packet.cursor = 3
    emitter = Emitter()
    emitter.write(3, 5)
    entries = InstalledEntries(index)
    entries.entries[("untouched", "table")] = [
        pb.Entry(action=pb.ActionCall(action="sentinelEntry"), priority=7)
    ]
    entries.default_actions[("untouched", "table")] = pb.ActionCall(action="sentinelAction")
    register = Register(3, 8)
    register.cells = [Bits(8, 3), Bits(8, 9), Bits(8, 27)]
    caller = Env.for_block(
        index,
        program.blocks[1],
        {"sentinel": register},
        entries=entries,
        packet=packet,
        emitter=emitter,
    )
    caller.vars = {
        "source_hdr": values["hdr"],
        "source_meta": values["meta"],
        "source_route": values["route"],
        "hdr": values["observer"],
        "caller_only": Bits(9, 301),
    }
    caller.visits[("parser", "state")] = 13
    caller.visits[("sentinel", "one")] = 1
    frozen_caller = deepcopy(normalized(caller.vars))
    frozen_scope = deepcopy(caller.scope)
    frozen_layers = deepcopy((caller.action, caller.action_vars))
    frozen_index = deepcopy(index)
    frozen_shared = shared_snapshot(caller)
    original = stmt.execute_one
    hits = 0

    def stop_at_observer(statement: pb.Stmt, callee: Env) -> None:
        nonlocal hits
        if callee.block.name == "RewriteBody" and statement == first_observer:
            hits += 1
            if early_observer:
                original(statement, callee)
            # Every assertion occurs HERE, before the finally-copyback runs.
            assert strict_equal(normalized(callee.vars), expected), "prefix values"
            assert strict_equal(normalized(caller.vars), frozen_caller), "prefix caller"
            assert (
                caller.scope == frozen_scope
                and (caller.action, caller.action_vars) == frozen_layers
            )
            assert callee.action is None and callee.action_vars is None
            assert callee.scope == frozen_index.scopes[call.block]
            assert callee.index == frozen_index and callee.entries is not None
            assert callee.entries.index == frozen_index
            assert strict_snapshot_equal(shared_snapshot(callee), frozen_shared), (
                "prefix shared state"
            )
            raise PrefixStopped
        original(statement, callee)

    monkeypatch.setattr(stmt, "execute_one", stop_at_observer)
    with pytest.raises(PrefixStopped):
        stmt.call_block(call, caller)
    assert hits == 1
    # No assertion describes this now-copied-back caller as the prefix state.


@pytest.mark.parametrize("name,prior_drop", CASES)
def test_lean_agrees_on_guarded_call_prefix(
    prefix_export: dict[str, Any], name: str, prior_drop: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (name, prior_drop) in checked_snapshots(prefix_export)
    observe_python_prefix(prefix_export, name, prior_drop, monkeypatch)


def test_prefix_observer_rejects_premature_execution(
    prefix_export: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(AssertionError, match="prefix values"):
        observe_python_prefix(
            prefix_export, "guard-true-true-true-2", False, monkeypatch, early_observer=True
        )


@pytest.mark.parametrize(
    "fault", ["cursor-float", "visit-bool", "packet-bytearray", "empty-entries"]
)
def test_prefix_observer_rejects_shared_corruption(
    prefix_export: dict[str, Any], monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    original = Env.enter_block
    hits = 0

    def corrupt(caller: Env, block: pb.Block) -> Env:
        nonlocal hits
        callee = original(caller, block)
        if block.name == "RewriteBody":
            hits += 1
            assert callee.packet is not None and callee.entries is not None
            before = shared_snapshot(callee)
            if fault == "cursor-float":
                callee.packet.cursor = float(callee.packet.cursor)  # pyright: ignore[reportAttributeAccessIssue]
            elif fault == "visit-bool":
                callee.visits[("sentinel", "one")] = True
            elif fault == "packet-bytearray":
                callee.packet.data = bytearray(callee.packet.data)  # pyright: ignore[reportAttributeAccessIssue]
            else:
                callee.entries.entries.clear()
            if fault != "empty-entries":
                assert shared_snapshot(callee) == before, (
                    "weak numeric/container comparison control"
                )
        return callee

    monkeypatch.setattr(Env, "enter_block", corrupt)
    with pytest.raises(AssertionError, match="prefix shared state"):
        observe_python_prefix(prefix_export, "guard-true-true-true-2", False, monkeypatch)
    assert hits == 1


@pytest.mark.parametrize(
    "fault",
    ["bool-int", "zero-bool", "observer", "missing-return", "suffix", "duplicate", "missing"],
)
def test_prefix_snapshot_rejects_corruption(prefix_export: dict[str, Any], fault: str) -> None:
    export = deepcopy(prefix_export)
    snapshot = export["snapshots"][0]
    if fault == "bool-int":
        snapshot["priorDrop"] = 0
    elif fault == "zero-bool":
        snapshot["vars"]["meta"][2][1] = 1
    elif fault == "observer":
        snapshot["vars"]["observer"] = None
    elif fault == "missing-return":
        del snapshot["queue"]["caller"]
    elif fault == "suffix":
        snapshot["queue"]["suffix"].pop()
    elif fault == "duplicate":
        export["snapshots"][1] = deepcopy(snapshot)
    else:
        export["snapshots"].pop()
    with pytest.raises(AssertionError):
        checked_snapshots(export)


def test_lean_agrees_after_prefix_local_fault(
    prefix_export: dict[str, Any],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Same actual local fault: prefix known-answer plus complete packet replay."""
    original = expr.write_lvalue
    hits = 0

    def wrong_local(place: pb.LValue, value: Value, env: Env) -> None:
        nonlocal hits
        if env.block.name == "RewriteBody" and place == target("scratch") and value == Bits(8, 19):
            hits += 1
            value = Bits(8, 20)
        original(place, value, env)

    name = "guard-false-false-true-2"
    programs = exported_programs(ROOT / "lean/.lake/build/bin/guardedForward")
    bundle = tmp_path / f"lean-{name}.json"
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    with monkeypatch.context() as fault:
        fault.setattr(stmt, "write_lvalue", wrong_local)
        with pytest.raises(AssertionError, match="prefix values"):
            with monkeypatch.context() as hook:
                observe_python_prefix(prefix_export, name, False, hook)
        assert hits == 1
        hits = 0
        with pytest.raises(pytest.fail.Exception, match="replay"):
            check_packet(name, programs, lean_binary)
        assert hits == 1
        program, cases, ports, seed = replay.load(bundle)
        assert (
            program == programs[name]
            and cases == [Case(pb.Entries(), 0, PAYLOAD)]
            and (ports, seed) == (4, 0)
        )
        hits = 0
        live = replay.replay(bundle, [lean_binary])
        assert hits == 1 and live.agreed == 0 and len(live.divergences) == 1
        assert live.protocol_error is None and live.both_errored == 0
        divergence = live.divergences[0]
        wrong = bytearray(expected_packet(name))
        wrong[40] = 20
        assert divergence.python.outputs == ((0, bytes(wrong)),)
        assert divergence.lean.outputs == ((0, expected_packet(name)),)
        for outcome in [divergence.python, divergence.lean]:
            assert outcome.error is None and outcome.diagnostic is None and outcome.state == ()
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
