"""Observe actual four-argument entry, before body, observer and copyback.

This deliberately does not claim that either caller construction or the
whole packet wrapper has been proved. Python's existing run_block boundary
is intercepted after its actual call_block binder, without reimplementing it.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
from google.protobuf import json_format

from p4blo.arch.externs.register import Register
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb
from tests.codec.test_codec_leaves import same_json
from tests.lean.test_lean_edsl_field_commands import field_command_program

ROOT = Path(__file__).resolve().parents[2]


def test_call_entry_exporter_is_a_default_target() -> None:
    package = tomllib.loads((ROOT / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def entry_export(lean_binary: Path) -> dict[str, Any]:
    assert lean_binary.is_file()
    exporter = ROOT / "impl/lean/.lake/build/bin/p4blo"
    assert exporter.is_file(), f"build {ROOT}/scripts/check-lean.sh first"
    return json.loads(
        subprocess.run(
            [str(exporter), "callEntry"], check=True, capture_output=True, text=True, timeout=30
        ).stdout
    )


def declarations(export: dict[str, Any]) -> tuple[pb.Program, pb.CallBlock]:
    program = field_command_program("forward-hit", [])
    selected = json_format.ParseDict(export["program"], pb.Program())
    actual = next(block for block in program.blocks if block.name == "RewriteBody")
    assert len(selected.blocks) == 1
    projected = pb.Block()
    projected.CopyFrom(actual)
    del projected.body[:]
    assert selected.blocks[0] == projected
    # Order across nominal declarations is immaterial; field order is not.
    for field, names in [
        ("header_types", {"Ethernet", "IPv4", "Result"}),
        ("struct_types", {"Headers", "Metadata", "Route", "H"}),
    ]:
        expected = {decl.name: decl for decl in getattr(program, field) if decl.name in names}
        obtained = {decl.name: decl for decl in getattr(selected, field)}
        assert len(getattr(selected, field)) == len(obtained)
        assert set(obtained) == names
        assert obtained == expected
    call = program.blocks[1].body[-1].call_block
    assert call.block == "RewriteBody"
    arguments = [json_format.ParseDict(arg, pb.Arg()) for arg in export["args"]]
    assert arguments == list(call.args)
    return program, call


def test_lean_agrees_on_call_entry_declarations(entry_export: dict[str, Any]) -> None:
    declarations(entry_export)


def test_call_entry_anchor_rejects_paired_equal_width_remapping(
    entry_export: dict[str, Any],
) -> None:
    """A layout and initializer can agree on the same wrong field order."""
    corrupted = deepcopy(entry_export)
    selected = json_format.ParseDict(corrupted["program"], pb.Program())
    result = next(header for header in selected.header_types if header.name == "Result")
    assert result.fields[0].type == result.fields[1].type == pb.Type(bits=48)
    result.fields[0].name, result.fields[1].name = result.fields[1].name, result.fields[0].name
    corrupted["program"] = json_format.MessageToDict(selected)
    with pytest.raises(AssertionError):
        declarations(corrupted)


def independent_values(ev: bool, iv: bool) -> dict[str, Value]:
    observer = Struct(
        "H",
        [
            Header(
                "Result",
                True,
                [
                    Bits(w, v)
                    for w, v in [
                        (48, 101),
                        (48, 202),
                        (16, 303),
                        (8, 4),
                        (8, 5),
                        (8, 6),
                        (16, 707),
                        (8, 8),
                        (16, 909),
                        (8, 10),
                        (16, 1111),
                        (8, 12),
                        (48, 1313),
                        (48, 1414),
                        (16, 1515),
                        (8, 16),
                        (8, 17),
                    ]
                ],
            )
        ],
    )
    return {
        "hdr": Struct(
            "Headers",
            [
                Header(
                    "Ethernet",
                    ev,
                    [Bits(48, 0x111213141516), Bits(48, 0x212223242526), Bits(16, 0x0800)],
                ),
                Header("IPv4", iv, [Bits(8, 64), Bits(8, 6), Bits(16, 0xABCD)]),
            ],
        ),
        "meta": Struct("Metadata", [Bits(9, 3), True, Bits(16, 0x1234)]),
        "route": Struct(
            "Route", [True, Bits(48, 0xAABBCCDDEEFF), Bits(48, 0x102030405060), Bits(9, 7)]
        ),
        "observer": observer,
        "scratch": Bits(8, 0),
        "unrelated": Bits(8, 0),
    }


def value_json(value: Value) -> Any:
    match value:
        case Bits(width, number):
            return ["bits", width, number]
        case bool():
            return value
        case Header(name, valid, fields):
            return ["header", name, valid, [value_json(v) for v in fields]]
        case Struct(name, fields):
            return ["struct", name, [value_json(v) for v in fields]]
        case _:
            raise AssertionError(f"unexpected entry value {value!r}")


@pytest.mark.parametrize("ev,iv", [(False, False), (False, True), (True, False), (True, True)])
def test_lean_agrees_on_call_entry(
    entry_export: dict[str, Any], ev: bool, iv: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    program, call = assert_native_snapshot(entry_export, ev, iv)
    observe_python_entry(program, call, ev, iv, monkeypatch)


def assert_native_snapshot(
    entry_export: dict[str, Any],
    ev: bool,
    iv: bool,
) -> tuple[pb.Program, pb.CallBlock]:
    program, call = declarations(entry_export)
    expected = independent_values(ev, iv)
    expected_json = {name: value_json(value) for name, value in expected.items()}
    snapshots = entry_export["snapshots"]
    assert isinstance(snapshots, list) and len(snapshots) == 4, "snapshot cases"
    assert all(type(s["ev"]) is bool and type(s["iv"]) is bool for s in snapshots), "snapshot cases"
    assert {(s["ev"], s["iv"]) for s in snapshots} == {
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    }, "snapshot cases"
    snapshot = next(s for s in snapshots if (s["ev"], s["iv"]) == (ev, iv))
    caller_values = {
        "source_hdr": expected["hdr"],
        "source_meta": expected["meta"],
        "source_route": expected["route"],
        "hdr": expected["observer"],
        "caller_only": Bits(9, 301),
    }
    expected_snapshot = {
        "ev": ev,
        "iv": iv,
        "faultNone": True,
        "scope": "RewriteBody",
        "size": 6,
        "actionNone": True,
        "vars": expected_json | {"caller_only": None},
        "queue": {
            "block": "RewriteBody",
            "params": [json_format.MessageToDict(p) for p in program.blocks[-1].params],
            "args": [json_format.MessageToDict(a) for a in call.args],
            "caller": {name: value_json(v) for name, v in caller_values.items()},
            "callerScope": "Caller",
            "callerSize": 5,
            "callerActionNone": True,
        },
        "index": "plain-call-entry-declarations",
        "packet": [[222, 173, 190, 239], 0xDEADBEEF, 3],
        "emitter": [5, 3],
        "extern": [8, [3, 9, 27]],
        "externSize": 1,
        "visit": 13,
        "visitSize": 1,
        "entries": {
            "index": "plain-call-entry-declarations",
            "size": 0,
            "defaultsSize": 1,
            "default": {"action": "sentinelAction"},
        },
    }
    assert same_json(snapshot, expected_snapshot), "entry snapshot contents or JSON types changed"
    return program, call


@pytest.mark.parametrize(
    "fault",
    ["stored-validity", "fault-flag", "zero-bit", "case-bool", "duplicate", "missing", "extra"],
)
def test_call_entry_snapshot_rejects_malformed_exports(
    entry_export: dict[str, Any],
    fault: str,
) -> None:
    corrupted = deepcopy(entry_export)
    snapshots = corrupted["snapshots"]
    snapshot = next(s for s in snapshots if s["ev"] is False and s["iv"] is False)
    if fault == "stored-validity":
        snapshot["vars"]["hdr"][2][0][2] = 0
    elif fault == "fault-flag":
        snapshot["faultNone"] = 1
    elif fault == "zero-bit":
        snapshot["vars"]["scratch"][2] = False
    elif fault == "case-bool":
        snapshot["ev"] = 0
    elif fault == "duplicate":
        snapshots[1] = deepcopy(snapshot)
    elif fault == "missing":
        snapshots.pop()
    else:
        snapshots.append(deepcopy(snapshot))
    with pytest.raises(AssertionError, match="snapshot"):
        assert_native_snapshot(corrupted, False, False)


def shared_snapshot(env: Env) -> tuple[Any, ...]:
    """Immutable contents, not references to mutable runtime objects."""
    assert env.packet is not None and env.emitter is not None and env.entries is not None
    externs: list[tuple[str, int, tuple[tuple[int, int], ...]]] = []
    for name, binding in env.externs.items():
        assert isinstance(binding, Register)
        externs.append(
            (name, binding.width, tuple((cell.width, cell.value) for cell in binding.cells))
        )
    return (
        env.index.program.SerializeToString(deterministic=True),
        env.packet.data,
        env.packet._value,
        env.packet.cursor,
        env.emitter.value,
        env.emitter.width,
        env.entries.index.program.SerializeToString(deterministic=True),
        tuple(
            sorted(
                (key, tuple(v.SerializeToString(deterministic=True) for v in values))
                for key, values in env.entries.entries.items()
            )
        ),
        tuple(
            sorted(
                (key, None if value is None else value.SerializeToString(deterministic=True))
                for key, value in env.entries.default_actions.items()
            )
        ),
        tuple(sorted(externs)),
        tuple(sorted(env.visits.items())),
    )


def observe_python_entry(
    program: pb.Program,
    call: pb.CallBlock,
    ev: bool,
    iv: bool,
    monkeypatch: pytest.MonkeyPatch,
    *,
    weak_only: bool = False,
) -> None:
    expected = independent_values(ev, iv)
    expected_json = {name: value_json(value) for name, value in expected.items()}
    caller_values = {
        "source_hdr": expected["hdr"],
        "source_meta": expected["meta"],
        "source_route": expected["route"],
        "hdr": expected["observer"],
        "caller_only": Bits(9, 301),
    }
    # Freeze before call: later mutations of the actual values cannot rewrite the oracle.
    frozen_caller = json.dumps(
        {name: value_json(v) for name, v in caller_values.items()}, sort_keys=True
    )
    index = Index.build(program)
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.write(3, 5)
    entries = InstalledEntries(index)
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
    caller.vars = caller_values
    caller.visits[("parser", "state")] = 13
    frozen_shared = shared_snapshot(caller)
    frozen_index = deepcopy(index)
    frozen_scope = deepcopy(caller.scope)
    frozen_layers = deepcopy((caller.action, caller.action_vars))
    observed: list[dict[str, Any]] = []

    def observe_entry(block: pb.Block, callee: Env) -> None:
        assert block.name == "RewriteBody"
        assert callee.action is None and callee.action_vars is None
        assert callee.index is caller.index and callee.entries is caller.entries
        assert callee.packet is caller.packet and callee.emitter is caller.emitter
        assert callee.externs is caller.externs and callee.visits is caller.visits
        assert caller.vars == caller_values
        if not weak_only:
            assert callee.index == frozen_index, "entry index changed"
            assert callee.entries is not None and callee.entries.index == frozen_index, (
                "entry installed index changed"
            )
            assert caller.scope == frozen_scope, "entry caller scope changed"
            assert (caller.action, caller.action_vars) == frozen_layers, (
                "entry caller layers changed"
            )
            assert callee.scope == frozen_index.scopes[call.block], "entry callee scope changed"
            assert (
                json.dumps({name: value_json(v) for name, v in caller.vars.items()}, sort_keys=True)
                == frozen_caller
            ), "entry caller changed"
            assert shared_snapshot(callee) == frozen_shared, "entry shared state changed"
        observed.append({name: value_json(v) for name, v in callee.vars.items()})

    monkeypatch.setattr(stmt, "run_block", observe_entry)
    stmt.call_block(call, caller)
    assert same_json(observed, [expected_json]), "entry Python value JSON types changed"


def test_call_entry_python_observer_rejects_boolean_integer_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = stmt.argument_value

    def malformed_argument(param: pb.Param, arg: pb.Arg, env: Env) -> Value:
        value = original(param, arg, env)
        if param.name == "hdr":
            assert isinstance(value, Struct)
            ethernet = value.fields[0]
            assert isinstance(ethernet, Header)
            # Deliberately violate this copied runtime header's annotation.
            # The original caller remains untouched, so only output checking sees it.
            ethernet.valid = cast(bool, 0)
            expected = value_json(independent_values(False, True)["hdr"])
            assert value_json(value) == expected  # the former check survives
            assert not same_json(value_json(value), expected)
        return value

    monkeypatch.setattr(stmt, "argument_value", malformed_argument)
    program = field_command_program("forward-hit", [])
    call = program.blocks[1].body[-1].call_block
    with pytest.raises(AssertionError, match="entry Python value JSON types changed"):
        observe_python_entry(program, call, False, True, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    ["cursor", "caller", "extern", "visits", "entries", "emitter", "index", "caller_action"],
)
def test_call_entry_observer_rejects_shared_state_faults(
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained entry-level reproduction, not whole-program DRT replay.

    The original identity/aliased checks survive each mutation. The frozen
    content observer must reject it at the exact real binder/body boundary.
    """
    original = Env.enter_block

    def faulty_entry(caller: Env, block: pb.Block) -> Env:
        callee = original(caller, block)
        if fault == "cursor":
            assert caller.packet is not None
            caller.packet.cursor += 1
        elif fault == "caller":
            caller.vars["caller_only"] = Bits(9, 302)
        elif fault == "extern":
            binding = caller.externs["sentinel"]
            assert isinstance(binding, Register)
            binding.cells[1] = Bits(8, 10)
        elif fault == "visits":
            caller.visits[("parser", "state")] = 14
        elif fault == "entries":
            assert caller.entries is not None
            caller.entries.default_actions.clear()
        elif fault == "emitter":
            assert caller.emitter is not None
            caller.emitter.value = 6
        elif fault == "index":
            caller.index.blocks.clear()
        else:
            caller.action = "unexpected"
        return callee

    monkeypatch.setattr(Env, "enter_block", faulty_entry)
    program = field_command_program("forward-hit", [])
    call = program.blocks[1].body[-1].call_block
    observe_python_entry(program, call, False, True, monkeypatch, weak_only=True)
    with pytest.raises(AssertionError, match="entry .*changed"):
        observe_python_entry(program, call, False, True, monkeypatch)
