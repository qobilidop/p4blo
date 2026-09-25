"""Normal return snapshots, not packet DRT or a proof of caller construction.

Observe the actual Python copy_back with a delegating write spy; compare the
actual Lean blockReturn against independently built whole-state known answers.
The callee includes operational decoys, not a globally typed-frame claim.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from collections.abc import Iterable
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import Any, cast

import pytest
from google.protobuf import json_format

from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.ir import BlockScope, Index
from p4blo.v0 import p4blo_pb2 as pb
from tests.codec.test_codec_leaves import same_json
from tests.lean.test_lean_call_entry import declarations, independent_values, value_json

ROOT = Path(__file__).resolve().parents[2]
CASES = [(False, False), (False, True), (True, False), (True, True)]


@pytest.fixture(scope="module")
def return_export(lean_binary: Path) -> dict[str, Any]:
    assert lean_binary.is_file()
    exporter = ROOT / "impl/lean/.lake/build/bin/p4blo"
    assert exporter.is_file(), f"build {ROOT}/scripts/check-lean.sh first"
    return json.loads(
        subprocess.run(
            [str(exporter), "callReturn"], check=True, capture_output=True, text=True, timeout=30
        ).stdout
    )


def test_call_return_exporter_is_a_default_target() -> None:
    package = tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


def checked_declarations(export: dict[str, Any]) -> tuple[Index, list[pb.Param], list[pb.Arg]]:
    program, call = declarations(export)
    params = [json_format.ParseDict(p, pb.Param()) for p in export["params"]]
    actual = next(block for block in program.blocks if block.name == "RewriteBody")
    assert params == list(actual.params)
    # Literal anchors remain independent of both exported and Python fixtures.
    assert [(p.name, p.direction) for p in params] == [
        ("hdr", pb.DIRECTION_INOUT),
        ("meta", pb.DIRECTION_INOUT),
        ("route", pb.DIRECTION_IN),
        ("observer", pb.DIRECTION_INOUT),
    ]
    assert [
        (a.WhichOneof("kind"), a.lvalue.var if a.HasField("lvalue") else a.expr.var)
        for a in call.args
    ] == [
        ("lvalue", "source_hdr"),
        ("lvalue", "source_meta"),
        ("expr", "source_route"),
        ("lvalue", "hdr"),
    ]
    selected = json_format.ParseDict(export["program"], apb.BlockAssembly())
    return BoundIndex.build(selected), params, list(call.args)


def new_values(ev: bool, iv: bool) -> dict[str, Value]:
    return {
        "hdr": Struct(
            "Headers",
            [
                Header(
                    "Ethernet",
                    ev,
                    [Bits(48, 0x313233343536), Bits(48, 0x414243444546), Bits(16, 0x86DD)],
                ),
                Header("IPv4", iv, [Bits(8, 17), Bits(8, 29), Bits(16, 0x1357)]),
            ],
        ),
        "meta": Struct("Metadata", [Bits(9, 257), False, Bits(16, 0x5678)]),
        "observer": Struct(
            "H",
            [
                Header(
                    "Result",
                    False,
                    [
                        Bits(w, v)
                        for w, v in [
                            (48, 1001),
                            (48, 2002),
                            (16, 3003),
                            (8, 40),
                            (8, 50),
                            (8, 60),
                            (16, 7007),
                            (8, 80),
                            (16, 9009),
                            (8, 100),
                            (16, 11011),
                            (8, 120),
                            (48, 13013),
                            (48, 14014),
                            (16, 15015),
                            (8, 160),
                            (8, 170),
                        ]
                    ],
                )
            ],
        ),
        "route": Struct(
            "Route", [False, Bits(48, 0x999999999999), Bits(48, 0x888888888888), Bits(9, 511)]
        ),
    }


def environments(index: Index, ev: bool, iv: bool) -> tuple[Env, Env]:
    old, new = independent_values(ev, iv), new_values(ev, iv)
    register = Register(3, 8)
    register.cells[:] = [Bits(8, v) for v in [31, 19, 7]]
    entries = InstalledEntries(index)
    entries.entries[("untouched", "table")] = [
        pb.Entry(action=pb.ActionCall(action="currentEntry"), priority=37)
    ]
    entries.default_actions[("untouched", "table")] = pb.ActionCall(action="currentAction")
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 11
    emitter = Emitter()
    emitter.write(5, 19)
    caller = Env(
        index,
        BlockScope(pb.Block(name="Caller", kind=pb.BLOCK_KIND_CONTROL)),
        {"sentinel": register},
        {
            "source_hdr": old["hdr"],
            "source_meta": old["meta"],
            "source_route": old["route"],
            "hdr": old["observer"],
            "caller_only": Bits(9, 301),
            "scratch": Bits(8, 41),
            "unrelated": Bits(8, 42),
        },
        entries=entries,
        packet=packet,
        emitter=emitter,
        visits={("parser", "state"): 29},
    )
    callee = Env(
        index,
        index.scopes["RewriteBody"],
        caller.externs,
        {
            "hdr": new["hdr"],
            "meta": new["meta"],
            "observer": new["observer"],
            "scratch": Bits(8, 91),
            "unrelated": Bits(8, 92),
            "source_hdr": Bits(8, 93),
            "source_meta": Bits(8, 94),
            "callee_only": True,
        }
        | ({"route": new["route"]} if ev else {}),
        entries=entries,
        packet=packet,
        emitter=emitter,
        visits=caller.visits,
    )
    return caller, callee


def scope_json(scope: BlockScope) -> dict[str, Any]:
    encode = partial(json_format.MessageToDict, preserving_proto_field_name=True)
    return {
        "block": encode(scope.block),
        "vars": {
            k: {"param" if isinstance(v, pb.Param) else "var": encode(v)}
            for k, v in scope.vars.items()
        },
        "actions": {k: encode(v) for k, v in scope.actions.items()},
        "actionParams": {
            k: {n: encode(v) for n, v in ps.items()} for k, ps in scope.action_params.items()
        },
        "tables": {k: encode(v) for k, v in scope.tables.items()},
        "states": {k: encode(v) for k, v in scope.states.items()},
    }


def index_json(index: Index) -> dict[str, Any]:
    encode = partial(json_format.MessageToDict, preserving_proto_field_name=True)
    result: dict[str, Any] = {
        "program": encode(index.program),
        "scopes": {k: scope_json(s) for k, s in index.scopes.items()},
        "programNames": dict.fromkeys(index.program_names, True),
        "errors": dict(index.errors),
    }
    for label, table in [
        ("headerTypes", index.header_types),
        ("structTypes", index.struct_types),
        ("enumTypes", index.enum_types),
        ("externTypes", index.extern_types),
        ("externInstances", index.extern_instances),
        ("blocks", index.blocks),
    ]:
        result[label] = {k: encode(v) for k, v in table.items()}
    return result


def frame_json(env: Env) -> dict[str, Any]:
    return {
        "scope": scope_json(env.scope),
        "vars": {k: value_json(v) for k, v in env.vars.items()},
        "action": env.action,
        "actionVars": None
        if env.action_vars is None
        else {k: value_json(v) for k, v in env.action_vars.items()},
    }


def pair_key(key: tuple[str, str]) -> str:
    return json.dumps(key, separators=(",", ":"))


def run_json(env: Env) -> dict[str, Any]:
    assert env.entries is not None and env.packet is not None and env.emitter is not None
    externs: dict[str, Any] = {}
    for name, binding in env.externs.items():
        assert isinstance(binding, Register)
        # Width is part of both the register and every cell's representation.
        assert all(cell.width == binding.width for cell in binding.cells)
        externs[name] = {"register": [binding.width, [cell.value for cell in binding.cells]]}
    return {
        "index": index_json(env.index),
        "frame": frame_json(env),
        "entries": {
            "index": index_json(env.entries.index),
            "entries": {
                pair_key(k): [json_format.MessageToDict(v) for v in vs]
                for k, vs in env.entries.entries.items()
            },
            "defaults": {
                pair_key(k): None if v is None else json_format.MessageToDict(v)
                for k, v in env.entries.default_actions.items()
            },
        },
        "externs": externs,
        "packet": [list(env.packet.data), env.packet._value, env.packet.cursor],
        "emitter": [env.emitter.value, env.emitter.width],
        "visits": {pair_key(k): v for k, v in env.visits.items()},
    }


def expected_after(caller: Env, ev: bool, iv: bool) -> dict[str, Any]:
    expected = run_json(caller)  # Detached JSON, never passed to the runtime.
    new = new_values(ev, iv)
    expected["frame"]["vars"].update(
        {
            "source_hdr": value_json(new["hdr"]),
            "source_meta": value_json(new["meta"]),
            "hdr": value_json(new["observer"]),
        }
    )
    return expected


def mutable_aggregate_ids(value: Value) -> set[int]:
    """All mutable containers in this fixture's Struct/Header trees."""
    if isinstance(value, (Struct, Header)):
        result = {id(value), id(value.fields)}
        for field in value.fields:
            result.update(mutable_aggregate_ids(field))
        return result
    return set()


def assert_native_snapshot(export: dict[str, Any], ev: bool, iv: bool) -> None:
    index, _, _ = checked_declarations(export)
    caller, callee = environments(index, ev, iv)
    snapshots = export["snapshots"]
    assert isinstance(snapshots, list) and len(snapshots) == 4, "snapshot cases"
    assert all(type(s["ev"]) is bool and type(s["iv"]) is bool for s in snapshots), "snapshot cases"
    assert {(s["ev"], s["iv"]) for s in snapshots} == set(CASES), "snapshot cases"
    snapshot = next(s for s in snapshots if (s["ev"], s["iv"]) == (ev, iv))
    expected = {
        "ev": ev,
        "iv": iv,
        "faultNone": True,
        "pending": True,
        "run": expected_after(caller, ev, iv),
        "callee": frame_json(callee),
    }
    assert same_json(snapshot, expected), "return snapshot contents or JSON types changed"


def observe_python_return(
    export: dict[str, Any], ev: bool, iv: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    index, params, args = checked_declarations(export)
    caller, callee = environments(index, ev, iv)
    expected, frozen_callee = expected_after(caller, ev, iv), run_json(callee)
    frozen_index, caller_scope, callee_scope = (
        deepcopy(index),
        deepcopy(caller.scope),
        deepcopy(callee.scope),
    )
    references = {
        name: getattr(caller, name)
        for name in ["index", "entries", "externs", "packet", "emitter", "visits"]
    }
    writes: list[str] = []
    actual_write = expr.write_lvalue

    def spy(target: pb.LValue, value: Value, env: Env) -> None:
        writes.append(target.var)
        actual_write(target, value, env)

    monkeypatch.setattr(stmt, "write_lvalue", spy)
    stmt.copy_back(params, args, callee, caller)
    assert writes == ["source_hdr", "source_meta", "hdr"], "copy-back order"
    assert same_json(run_json(caller), expected), "caller or shared contents changed"
    assert same_json(run_json(callee), frozen_callee), "callee or shared contents changed"
    assert caller.index == callee.index == frozen_index
    assert caller.scope == caller_scope and callee.scope == callee_scope
    assert caller.action is callee.action is caller.action_vars is callee.action_vars is None
    for name, reference in references.items():
        assert getattr(caller, name) is getattr(callee, name) is reference
    # Include every mutable object AND field list, not only equal contents.
    copied_ids = set().union(
        *(mutable_aggregate_ids(caller.vars[n]) for n in ["source_hdr", "source_meta", "hdr"])
    )
    original_ids = set().union(
        *(mutable_aggregate_ids(callee.vars[n]) for n in ["hdr", "meta", "observer"])
    )
    assert copied_ids.isdisjoint(original_ids), "copied aggregate containers alias callee"
    # Real writes in every aggregate branch must leave the retained callee alone.
    for root, path, positions, width, number in [
        ("source_hdr", ["ethernet", "dst"], [2, 0, 3, 0], 48, 0x515253545556),
        ("source_hdr", ["ipv4", "ttl"], [2, 1, 3, 0], 8, 23),
        ("source_meta", ["port"], [2, 0], 9, 399),
        ("hdr", ["result", "dst"], [2, 0, 3, 0], 48, 0x616263646566),
    ]:
        target = pb.LValue(var=root)
        for field in path:
            target = pb.LValue(member=pb.LMember(base=target, field=field))
        expr.write_lvalue(target, Bits(width, number), caller)
        destination = expected["frame"]["vars"][root]
        for position in positions[:-1]:
            destination = destination[position]
        destination[positions[-1]] = ["bits", width, number]
        assert same_json(run_json(caller), expected), "follow-up member write"
        assert same_json(run_json(callee), frozen_callee), "copied aggregate aliases callee"


def test_lean_agrees_on_call_return_declarations(return_export: dict[str, Any]) -> None:
    checked_declarations(return_export)


@pytest.mark.parametrize("ev,iv", CASES)
def test_lean_agrees_on_call_return(
    return_export: dict[str, Any], ev: bool, iv: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert_native_snapshot(return_export, ev, iv)
    observe_python_return(return_export, ev, iv, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    [
        "validity",
        "flag",
        "case",
        "duplicate",
        "missing",
        "extra",
        "caller",
        "index",
        "packet",
        "scope",
        "callee",
    ],
)
def test_return_snapshot_rejects_corruption(return_export: dict[str, Any], fault: str) -> None:
    corrupted = deepcopy(return_export)
    snapshots = corrupted["snapshots"]
    s = next(s for s in snapshots if s["ev"] is False and s["iv"] is False)
    if fault == "validity":
        s["run"]["frame"]["vars"]["source_hdr"][2][0][2] = 0
    elif fault == "flag":
        s["faultNone"] = 1
    elif fault == "case":
        s["ev"] = 0
    elif fault == "duplicate":
        snapshots[1] = deepcopy(s)
    elif fault == "missing":
        snapshots.pop()
    elif fault == "extra":
        snapshots.append(deepcopy(s))
    elif fault == "caller":
        s["run"]["frame"]["vars"]["caller_only"] = ["bits", 9, 302]
    elif fault == "index":
        s["run"]["index"]["blocks"] = {}
    elif fault == "packet":
        s["run"]["packet"][2] += 1
    elif fault == "scope":
        s["run"]["frame"]["action"] = "unexpected"
    else:
        s["callee"]["vars"]["scratch"] = ["bits", 8, 0]
    with pytest.raises(AssertionError, match="snapshot"):
        assert_native_snapshot(corrupted, False, False)


@pytest.mark.parametrize(
    "fault",
    [
        "cursor",
        "index",
        "entries",
        "emitter",
        "extern",
        "visits",
        "caller-scope",
        "callee-scope",
        "caller-action",
        "callee-action",
        "caller-value",
        "callee-value",
        "alias",
        "alias-meta",
        "alias-observer",
        "alias-ipv4",
        "alias-fields",
        "bool-alias",
        "input",
        "skip",
        "wrong-root",
        "wrong-frame",
        "reverse",
    ],
)
def test_return_observer_rejects_actual_boundary_faults(
    return_export: dict[str, Any], fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retained observer challenges delegate to actual copy_back, never a model.

    Final-value-only checking would miss reversed independent writes and
    aggregate aliasing; identity-only checking would miss shared mutations.
    These are boundary known-answer checks, not packet differential replay.
    """
    actual = stmt.copy_back

    def faulty(params: Iterable[pb.Param], args: Iterable[pb.Arg], values: Env, env: Env) -> None:
        ps, arguments = list(params), deepcopy(list(args))
        if fault == "skip":
            actual(ps[:-1], arguments[:-1], values, env)
        elif fault == "wrong-root":
            arguments[0].lvalue.var = "source_meta"
            actual(ps, arguments, values, env)
        elif fault == "wrong-frame":
            actual(ps, arguments, values, values)
        elif fault == "reverse":
            actual(reversed(ps), reversed(arguments), values, env)
        else:
            actual(ps, arguments, values, env)
        if fault == "cursor":
            assert env.packet is not None
            env.packet.cursor += 1
        elif fault == "index":
            env.index.blocks.clear()
        elif fault == "entries":
            assert env.entries is not None
            env.entries.entries.clear()
        elif fault == "emitter":
            assert env.emitter is not None
            env.emitter.value = 0
        elif fault == "extern":
            cast(dict[str, Register], env.externs).clear()
        elif fault == "visits":
            env.visits.clear()
        elif fault == "caller-scope":
            env.scope.block.name = "wrongCaller"
        elif fault == "callee-scope":
            values.scope.block.name = "wrongCallee"
        elif fault == "caller-action":
            env.action = "unexpected"
        elif fault == "callee-action":
            values.action_vars = {}
        elif fault == "caller-value":
            env.vars["caller_only"] = Bits(9, 302)
        elif fault == "callee-value":
            values.vars["scratch"] = Bits(8, 0)
        elif fault == "alias":
            env.vars["source_hdr"] = values.vars["hdr"]
        elif fault == "alias-meta":
            env.vars["source_meta"] = values.vars["meta"]
        elif fault == "alias-observer":
            env.vars["hdr"] = values.vars["observer"]
        elif fault in ("alias-ipv4", "alias-fields"):
            copied, original = env.vars["source_hdr"], values.vars["hdr"]
            assert isinstance(copied, Struct) and isinstance(original, Struct)
            if fault == "alias-ipv4":
                copied.fields[1] = original.fields[1]
            else:
                copied.fields = original.fields
        elif fault == "bool-alias":
            aggregate = env.vars["source_hdr"]
            assert isinstance(aggregate, Struct) and isinstance(aggregate.fields[0], Header)
            # Simulate an untyped foreign boundary; Python equality aliases it.
            cast(Any, aggregate.fields[0]).valid = 1
        elif fault == "input":
            expr.write_lvalue(pb.LValue(var="source_route"), values.read("route"), env)

    monkeypatch.setattr(stmt, "copy_back", faulty)
    with pytest.raises(AssertionError):
        observe_python_return(return_export, True, False, monkeypatch)


def test_return_anchor_rejects_paired_destination_remapping(return_export: dict[str, Any]) -> None:
    """A result model can agree with the same wrong argument mapping."""
    corrupted = deepcopy(return_export)
    corrupted["args"][0], corrupted["args"][1] = corrupted["args"][1], corrupted["args"][0]
    for s in corrupted["snapshots"]:
        values = s["run"]["frame"]["vars"]
        values["source_hdr"], values["source_meta"] = values["source_meta"], values["source_hdr"]
    with pytest.raises(AssertionError):
        checked_declarations(corrupted)
