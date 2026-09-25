"""Whole normal guarded calls, separate from any packet/observer wrapper."""

from __future__ import annotations

import json
import subprocess
import tomllib
from collections.abc import Iterable
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
from p4blo.interp.values import Bits, Struct, Value
from p4blo.ir import BlockScope, Index
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_codec_leaves import same_json
from tests.test_lean_call_entry import shared_snapshot, value_json
from tests.test_lean_call_return import frame_json, mutable_aggregate_ids, run_json
from tests.test_lean_edsl_field_commands import field_command_program
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
from tests.test_lean_guarded_call_prefix import (
    CASES,
    expected_values,
    normalized,
    source_values,
    strict_snapshot_equal,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def call_export(lean_binary: Path) -> dict[str, Any]:
    assert lean_binary.is_file()
    return json.loads(
        subprocess.run(
            [str(ROOT / "impl/lean/.lake/build/bin/p4blo"), "guardedControlCall"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )


@pytest.fixture(scope="module")
def guarded_body(lean_binary: Path) -> list[pb.Stmt]:
    assert lean_binary.is_file()
    records = [
        json.loads(line)
        for line in subprocess.run(
            [str(ROOT / "impl/lean/.lake/build/bin/p4blo"), "guardedForward"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.splitlines()
    ]
    assert len(records) == 32 and {r["name"] for r in records} == set(INPUTS)
    first = records[0]["body"]
    assert all(r["body"] == first for r in records)
    result = [json_format.ParseDict(s, pb.Stmt()) for s in first]
    assert len(result) == 1 and result[0].HasField("conditional")
    return result


def declarations(export: dict[str, Any], guard: list[pb.Stmt]) -> tuple[pb.Program, pb.CallBlock]:
    assert set(export) == {"program", "args", "snapshots"}
    wrapper = field_command_program("forward-hit", [])
    old = next(b for b in wrapper.blocks if b.name == "RewriteBody")
    # Construct all three statements independently, never slice candidate body.
    expected = pb.Block(
        name="RewriteBody",
        kind=pb.BLOCK_KIND_CONTROL,
        params=old.params,
        locals=old.locals,
        body=[
            pb.Stmt(
                assign=pb.Assign(
                    target=target("scratch"),
                    value=pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=8, value="19"))),
                )
            ),
            pb.Stmt(
                assign=pb.Assign(
                    target=target("unrelated"),
                    value=pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=8, value="165"))),
                )
            ),
            *guard,
        ],
    )
    selected = json_format.ParseDict(export["program"], pb.Program())
    assert list(selected.blocks) == [expected], "exact observer-free body"
    assert len(expected.body) == 3
    assert selected.name == "plain-call-entry-declarations"
    for field, names in [
        ("header_types", {"Ethernet", "IPv4", "Result"}),
        ("struct_types", {"Headers", "Metadata", "Route", "H"}),
    ]:
        values = list(getattr(selected, field))
        assert len(values) == len(names)
        assert {d.name: d for d in values} == {
            d.name: d for d in getattr(wrapper, field) if d.name in names
        }
    assert not (
        selected.enum_types or selected.extern_types or selected.extern_instances or selected.errors
    )
    call = wrapper.blocks[1].body[-1].call_block
    assert [json_format.ParseDict(a, pb.Arg()) for a in export["args"]] == list(call.args)
    return selected, call


def caller_env(program: pb.Program, name: str, prior_drop: bool) -> Env:
    values = source_values(name, prior_drop)
    index = Index.build(program)
    entries = InstalledEntries(index)
    entries.entries[("untouched", "table")] = [
        pb.Entry(action=pb.ActionCall(action="sentinelEntry"), priority=7)
    ]
    entries.default_actions[("untouched", "table")] = pb.ActionCall(action="sentinelAction")
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.write(3, 5)
    register = Register(3, 8)
    register.cells[:] = [Bits(8, n) for n in [3, 9, 27]]
    return Env(
        index,
        BlockScope(pb.Block(name="Caller", kind=pb.BLOCK_KIND_CONTROL)),
        {"sentinel": register},
        {
            "source_hdr": values["hdr"],
            "source_meta": values["meta"],
            "source_route": values["route"],
            "hdr": values["observer"],
            "caller_only": Bits(9, 301),
            "scratch": Bits(8, 41),
            "unrelated": Bits(8, 42),
        },
        entries=entries,
        packet=packet,
        emitter=emitter,
        visits={("parser", "state"): 13, ("sentinel", "one"): 1},
    )


def expectations(caller: Env, name: str, prior_drop: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    values = expected_values(name, prior_drop)
    after = run_json(caller)
    after["frame"]["vars"]["source_hdr"] = value_json(values["hdr"])
    after["frame"]["vars"]["source_meta"] = value_json(values["meta"])
    callee = Env(caller.index, caller.index.scopes["RewriteBody"], caller.externs, values)
    return after, frame_json(callee)


def count(name: str) -> int:
    ev, iv, hit, ttl = INPUTS[name]
    if not ev:
        return 13
    if not iv:
        return 16
    if not hit:
        return 19
    return {0: 22, 1: 25, 2: 33, 255: 33}[ttl]


def check_snapshots(
    export: dict[str, Any], guard: list[pb.Stmt]
) -> tuple[pb.Program, pb.CallBlock]:
    program, call = declarations(export, guard)
    snapshots = export["snapshots"]
    assert isinstance(snapshots, list) and len(snapshots) == 64, "snapshot cases"
    seen: set[tuple[str, bool]] = set()
    for snapshot in snapshots:
        name, prior_drop = snapshot["name"], snapshot["priorDrop"]
        assert type(name) is str and name in INPUTS and type(prior_drop) is bool, "snapshot cases"
        assert (name, prior_drop) not in seen, "snapshot duplicate"
        seen.add((name, prior_drop))
        caller = caller_env(program, name, prior_drop)
        after, callee = expectations(caller, name, prior_drop)
        assert same_json(
            snapshot,
            {
                "name": name,
                "priorDrop": prior_drop,
                "steps": count(name),
                "faultNone": True,
                "empty": True,
                "returnPendingOneStepShort": True,
                "run": after,
                "callee": callee,
            },
        ), "complete snapshot"
    assert seen == set(CASES)
    return program, call


@pytest.fixture(scope="module")
def checked_call(
    call_export: dict[str, Any], guarded_body: list[pb.Stmt]
) -> tuple[pb.Program, pb.CallBlock]:
    # Validate every exported profile once, not 64 × 64 repeated validations.
    return check_snapshots(call_export, guarded_body)


def observe_call(
    program: pb.Program,
    call: pb.CallBlock,
    name: str,
    prior_drop: bool,
    monkeypatch: pytest.MonkeyPatch,
    *,
    check_copyback_order: bool = True,
) -> None:
    caller = caller_env(program, name, prior_drop)
    expected, expected_callee = expectations(caller, name, prior_drop)
    frozen_shared = shared_snapshot(caller)
    frozen_index, frozen_scope = deepcopy(caller.index), deepcopy(caller.scope)
    original_inputs = {
        n: caller.vars[n] for n in ["source_hdr", "source_meta", "source_route", "hdr"]
    }
    frozen_inputs = normalized(original_inputs)
    original_ids = set().union(*(mutable_aggregate_ids(v) for v in original_inputs.values()))
    retained: list[Env] = []
    frozen_after_body: list[dict[str, Any]] = []
    writes: list[str] = []
    actual_run, actual_write = stmt.run_block, expr.write_lvalue

    def keep(block: pb.Block, callee: Env) -> None:
        assert block.name == "RewriteBody" and not retained
        retained.append(callee)
        entered_ids = set().union(
            *(mutable_aggregate_ids(callee.vars[n]) for n in ["hdr", "meta", "route", "observer"])
        )
        assert entered_ids.isdisjoint(original_ids), "copy-in mutable alias"
        actual_run(block, callee)
        frozen_after_body.append(run_json(callee))

    def spy(place: pb.LValue, value: Value, env: Env) -> None:
        if env is caller:
            writes.append(place.var)
        actual_write(place, value, env)

    monkeypatch.setattr(stmt, "run_block", keep)
    monkeypatch.setattr(stmt, "write_lvalue", spy)
    # Normal completion: no early-exit exception, fake copyback or body model.
    assert stmt.call_block(call, caller) is None
    assert len(retained) == len(frozen_after_body) == 1, "normal body hook count"
    callee = retained[0]
    if check_copyback_order:
        assert writes == ["source_hdr", "source_meta", "hdr"], "copyback order/targets"
    assert same_json(run_json(caller), expected), "complete caller"
    assert same_json(frame_json(callee), expected_callee), "complete callee"
    assert same_json(run_json(callee), frozen_after_body[0]), "copyback changed callee"
    assert same_json(normalized(original_inputs), frozen_inputs), "copy-in changed old inputs"
    assert caller.index == callee.index == frozen_index and caller.scope == frozen_scope
    assert strict_snapshot_equal(shared_snapshot(caller), frozen_shared), (
        "shared state types/contents"
    )
    assert strict_snapshot_equal(shared_snapshot(callee), frozen_shared), "callee shared state"
    copied_ids = set().union(
        *(
            mutable_aggregate_ids(caller.vars[n])
            for n in ["source_hdr", "source_meta", "source_route", "hdr"]
        )
    )
    callee_ids = set().union(
        *(mutable_aggregate_ids(callee.vars[n]) for n in ["hdr", "meta", "route", "observer"])
    )
    assert copied_ids.isdisjoint(callee_ids), "copy-out mutable alias"
    for root, path, positions, width, number in [
        ("source_hdr", ["ethernet", "dst"], [2, 0, 3, 0], 48, 0x515253545556),
        ("source_hdr", ["ipv4", "ttl"], [2, 1, 3, 0], 8, 23),
        ("source_meta", ["port"], [2, 0], 9, 399),
        ("hdr", ["result", "dst"], [2, 0, 3, 0], 48, 0x616263646566),
        ("source_route", ["port"], [2, 3], 9, 401),
    ]:
        expr.write_lvalue(target(root, *path), Bits(width, number), caller)
        destination = expected["frame"]["vars"][root]
        for position in positions[:-1]:
            destination = destination[position]
        destination[positions[-1]] = ["bits", width, number]
        assert same_json(run_json(caller), expected), "follow-up caller write"
        assert same_json(run_json(callee), frozen_after_body[0]), "follow-up alias changed callee"


def test_control_call_is_default() -> None:
    assert {"P4bloTest", "p4blo"} <= set(
        tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())["defaultTargets"]
    )


@pytest.mark.parametrize("name,prior_drop", CASES)
def test_lean_agrees_on_guarded_control_call(
    checked_call: tuple[pb.Program, pb.CallBlock],
    name: str,
    prior_drop: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observe_call(*checked_call, name, prior_drop, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    [
        "alias-meta",
        "alias-observer",
        "alias-ipv4",
        "alias-fields",
        "reverse",
        "skip",
        "input-copy",
        "local-leak",
        "cursor-float",
        "visit-bool",
        "entries",
        "scratch",
    ],
)
def test_whole_call_observer_rejects_faults(
    checked_call: tuple[pb.Program, pb.CallBlock], fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    actual = stmt.copy_back
    hits = 0

    def wrong(params: Iterable[pb.Param], args: Iterable[pb.Arg], values: Env, caller: Env) -> None:
        nonlocal hits
        hits += 1
        ps, aa = list(params), list(args)
        if fault == "reverse":
            actual(reversed(ps), reversed(aa), values, caller)
        elif fault == "skip":
            actual(ps[:-1], aa[:-1], values, caller)
        else:
            actual(ps, aa, values, caller)
        if fault == "alias-meta":
            caller.vars["source_meta"] = values.vars["meta"]
        elif fault == "alias-observer":
            caller.vars["hdr"] = values.vars["observer"]
        elif fault in {"alias-ipv4", "alias-fields"}:
            copied, original = caller.vars["source_hdr"], values.vars["hdr"]
            assert isinstance(copied, Struct) and isinstance(original, Struct)
            if fault == "alias-ipv4":
                copied.fields[1] = original.fields[1]
            else:
                copied.fields = original.fields
        elif fault == "input-copy":
            stmt.write_lvalue(target("source_route"), values.read("route"), caller)  # pyright: ignore[reportPrivateImportUsage]
        elif fault == "local-leak":
            caller.vars["scratch"] = values.vars["scratch"]
        elif fault == "cursor-float":
            assert caller.packet is not None
            caller.packet.cursor = float(caller.packet.cursor)  # pyright: ignore[reportAttributeAccessIssue]
        elif fault == "visit-bool":
            caller.visits[("sentinel", "one")] = True
        elif fault == "entries":
            assert caller.entries is not None
            caller.entries.entries.clear()
        elif fault == "scratch":
            values.vars["scratch"] = Bits(8, 20)

    monkeypatch.setattr(stmt, "copy_back", wrong)
    if fault in {"skip", "reverse"}:
        with monkeypatch.context() as weak:
            observe_call(
                *checked_call, "guard-true-true-true-2", False, weak, check_copyback_order=False
            )
        assert hits == 1  # Complete value/isolation snapshots alone survive.
        hits = 0
    with pytest.raises(AssertionError):
        observe_call(*checked_call, "guard-true-true-true-2", False, monkeypatch)
    assert hits == 1


@pytest.mark.parametrize(
    "fault", ["bool-int", "count", "pending", "index", "scope", "callee", "missing", "duplicate"]
)
def test_complete_snapshot_rejects_faults(
    call_export: dict[str, Any], guarded_body: list[pb.Stmt], fault: str
) -> None:
    export = deepcopy(call_export)
    s = export["snapshots"][0]
    if fault == "bool-int":
        s["priorDrop"] = 0
    elif fault == "count":
        s["steps"] -= 1
    elif fault == "pending":
        s["returnPendingOneStepShort"] = False
    elif fault == "index":
        s["run"]["entries"]["index"]["blocks"] = {}
    elif fault == "scope":
        s["run"]["frame"]["scope"]["vars"]["extra"] = {}
    elif fault == "callee":
        s["callee"]["vars"]["scratch"] = ["bits", 8, 20]
    elif fault == "missing":
        export["snapshots"].pop()
    else:
        export["snapshots"][1] = deepcopy(s)
    with pytest.raises(AssertionError, match="snapshot"):
        check_snapshots(export, guarded_body)


def test_exact_syntax_rejects_paired_wrong_intent(
    call_export: dict[str, Any], guarded_body: list[pb.Stmt]
) -> None:
    export = deepcopy(call_export)
    program = json_format.ParseDict(export["program"], pb.Program())
    program.blocks[0].body[0].assign.value.literal.bits.value = "20"
    export["program"] = json_format.MessageToDict(program)
    for snapshot in export["snapshots"]:
        snapshot["callee"]["vars"]["scratch"] = ["bits", 8, 20]
    with pytest.raises(AssertionError, match="observer-free body"):
        check_snapshots(export, guarded_body)


@pytest.mark.parametrize("parameter", ["hdr", "meta", "route", "observer"])
def test_normal_call_rejects_copy_in_aliases(
    checked_call: tuple[pb.Program, pb.CallBlock], parameter: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = stmt.argument_value
    hits = 0

    def alias(param: pb.Param, arg: pb.Arg, caller: Env) -> Value:
        nonlocal hits
        if param.name == parameter:
            hits += 1
            return (
                expr.evaluate(arg.expr, caller)
                if arg.HasField("expr")
                else expr.read_lvalue(arg.lvalue, caller)
            )
        return original(param, arg, caller)

    monkeypatch.setattr(stmt, "argument_value", alias)
    with pytest.raises(AssertionError, match="copy-in mutable alias"):
        observe_call(*checked_call, "guard-true-true-true-2", False, monkeypatch)
    assert hits == 1


def test_lean_agrees_after_whole_call_skipped_observer(
    checked_call: tuple[pb.Program, pb.CallBlock],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """One return fault, separately observed as call order and packet mismatch."""
    original = stmt.copy_back
    hits = 0

    def skip(params: Iterable[pb.Param], args: Iterable[pb.Arg], values: Env, caller: Env) -> None:
        nonlocal hits
        pairs = list(zip(params, args, strict=True))
        if values.block.name == "RewriteBody":
            hits += 1
            pairs = [(p, a) for p, a in pairs if p.name != "observer"]
        original([p for p, _ in pairs], [a for _, a in pairs], values, caller)

    name = "guard-false-false-true-2"
    programs = exported_programs([str(ROOT / "impl/lean/.lake/build/bin/p4blo"), "guardedForward"])
    bundle = tmp_path / f"lean-{name}.json"
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    with monkeypatch.context() as fault:
        fault.setattr(stmt, "copy_back", skip)
        with pytest.raises(AssertionError, match="copyback order/targets"):
            with monkeypatch.context() as spies:
                observe_call(*checked_call, name, False, spies)
        assert hits == 1
        hits = 0
        with pytest.raises(pytest.fail.Exception, match="replay"):
            check_packet(name, programs, lean_binary)
        assert hits == 1
        program, cases, ports, seed = replay.load(bundle)
        assert program == programs[name] and cases == [Case(pb.Entries(), 0, PAYLOAD)]
        assert (ports, seed) == (4, 0)
        hits = 0
        live = replay.replay(bundle, [lean_binary])
        assert hits == 1 and live.agreed == 0 and len(live.divergences) == 1
        assert live.protocol_error is None and live.both_errored == 0
        divergence = live.divergences[0]
        # The separate packet wrapper starts its 42-byte Result header valid
        # and zeroed; skipped observer copyback leaves those initial bytes.
        assert divergence.python.outputs == ((0, bytes(42) + PAYLOAD),)
        assert divergence.lean.outputs == ((0, expected_packet(name)),)
        for outcome in [divergence.python, divergence.lean]:
            assert outcome.error is None and outcome.diagnostic is None and outcome.state == ()
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
