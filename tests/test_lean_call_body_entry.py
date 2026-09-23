"""Actual body-bearing call entry, before any initializer/body/observer runs."""

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

from p4blo.v0 import p4blo_pb2 as pb
from tests.test_lean_call_entry import independent_values, observe_python_entry, value_json
from tests.test_lean_edsl_guarded_forwarding import exported_programs

ROOT = Path(__file__).resolve().parents[1]
PAIRS = list(itertools.product([False, True], repeat=2))


def test_body_entry_exporter_is_default() -> None:
    package = tomllib.loads((ROOT / "lean/lakefile.toml").read_text())
    assert {"UserProofAudit", "callEntry", "callBodyEntry"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def body_entry_export(lean_binary: Path) -> dict[str, Any]:
    assert lean_binary.is_file()
    return json.loads(
        subprocess.run(
            [str(ROOT / "lean/.lake/build/bin/callBodyEntry")],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )


def actual_wrapper() -> pb.Program:
    # Independent tracked Python wrapper; the second authored exporter pins
    # the command insertion separately from the complete body-entry exporter.
    return exported_programs(ROOT / "lean/.lake/build/bin/guardedForward")[
        "guard-false-false-true-2"
    ]


def assert_selected_body(export: dict[str, Any]) -> tuple[pb.Program, pb.CallBlock]:
    assert set(export) == {"program", "args", "snapshots"}
    program = actual_wrapper()
    actual = next(block for block in program.blocks if block.name == "RewriteBody")
    selected = json_format.ParseDict(export["program"], pb.Program())
    assert len(selected.blocks) == 1
    # Deliberately do not erase body: this is the full initializer, guarded
    # command and observer list, with exact order/casts/member spellings.
    assert selected.blocks[0] == actual, "complete selected body differs"
    assert len(actual.body) == 20  # two assignments, one guarded if, 17 observations
    for field, names in [
        ("header_types", {"Ethernet", "IPv4", "Result"}),
        ("struct_types", {"Headers", "Metadata", "Route", "H"}),
    ]:
        expected = {d.name: d for d in getattr(program, field) if d.name in names}
        found = {d.name: d for d in getattr(selected, field)}
        assert len(getattr(selected, field)) == len(found)
        assert set(found) == names and found == expected
    call = program.blocks[1].body[-1].call_block
    assert call.block == "RewriteBody"
    assert [json_format.ParseDict(a, pb.Arg()) for a in export["args"]] == list(call.args)
    return program, call


def assert_snapshots(export: dict[str, Any]) -> None:
    program, call = assert_selected_body(export)
    actual = next(block for block in program.blocks if block.name == "RewriteBody")
    profiles = {
        "empty": [],
        "guarded-wrapper": list(actual.body),
        "faulting": [
            pb.Stmt(
                verify=pb.Verify(
                    condition=pb.Expr(literal=pb.Literal(boolean=False)), error="body-must-not-run"
                )
            )
        ],
    }
    snapshots = export["snapshots"]
    assert isinstance(snapshots, list) and len(snapshots) == 12, "snapshot count"
    seen: set[tuple[str, bool, bool]] = set()
    for snapshot in snapshots:
        assert set(snapshot) == {"name", "ev", "iv", "faultNone", "scopeBlock", "vars", "queue"}
        name, ev, iv = snapshot["name"], snapshot["ev"], snapshot["iv"]
        assert type(name) is str and name in profiles
        assert type(ev) is bool and type(iv) is bool, "snapshot Boolean input"
        assert type(snapshot["faultNone"]) is bool and snapshot["faultNone"], "snapshot fault"
        key = (name, ev, iv)
        assert key not in seen, "duplicate snapshot"
        seen.add(key)
        expected_block = pb.Block()
        expected_block.CopyFrom(actual)
        del expected_block.body[:]
        expected_block.body.extend(profiles[name])
        assert json_format.ParseDict(snapshot["scopeBlock"], pb.Block()) == expected_block
        queue = snapshot["queue"]
        assert set(queue) == {"block", "params", "args", "caller"}
        assert json_format.ParseDict(queue["block"], pb.Block()) == expected_block
        assert [json_format.ParseDict(p, pb.Param()) for p in queue["params"]] == list(
            actual.params
        )
        assert [json_format.ParseDict(a, pb.Arg()) for a in queue["args"]] == list(call.args)
        values = independent_values(ev, iv)
        expected_vars = {name: value_json(value) for name, value in values.items()} | {
            "caller_only": None
        }
        # Exact JSON types matter: Python equality otherwise identifies 0/False.
        assert json.dumps(snapshot["vars"], sort_keys=True) == json.dumps(
            expected_vars, sort_keys=True
        ), "snapshot values"
        expected_caller = {
            "source_hdr": value_json(values["hdr"]),
            "source_meta": value_json(values["meta"]),
            "source_route": value_json(values["route"]),
            "hdr": value_json(values["observer"]),
            "caller_only": ["bits", 9, 301],
        }
        assert json.dumps(queue["caller"], sort_keys=True) == json.dumps(
            expected_caller, sort_keys=True
        )
    assert seen == {(name, ev, iv) for name in profiles for ev, iv in PAIRS}


def test_lean_agrees_on_complete_call_body(body_entry_export: dict[str, Any]) -> None:
    assert_snapshots(body_entry_export)


@pytest.mark.parametrize("ev,iv", PAIRS)
def test_lean_agrees_on_body_bearing_entry(
    body_entry_export: dict[str, Any], ev: bool, iv: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    program, call = assert_selected_body(body_entry_export)
    # Reuse the reviewed immutable shared/caller observer at actual run_block
    # entry. It sees the full body but must not execute it or its initializers.
    observe_python_entry(program, call, ev, iv, monkeypatch)


@pytest.mark.parametrize(
    "fault",
    ["empty", "skip-local", "wrong-local", "skip-observer", "wrong-observer", "observer-order"],
)
def test_complete_body_anchor_rejects_wrong_syntax(
    body_entry_export: dict[str, Any], fault: str
) -> None:
    corrupted = deepcopy(body_entry_export)
    selected = json_format.ParseDict(corrupted["program"], pb.Program())
    body = selected.blocks[0].body
    if fault == "empty":
        del body[:]
    elif fault == "skip-local":
        del body[0]
    elif fault == "wrong-local":
        body[0].assign.value.literal.bits.value = "20"
    elif fault == "skip-observer":
        del body[-1]
    elif fault == "wrong-observer":
        body[3].assign.value.cast.operand.member.field = "src"
    else:
        first = pb.Stmt()
        first.CopyFrom(body[3])
        body[3].CopyFrom(body[4])
        body[4].CopyFrom(first)
    corrupted["program"] = json_format.MessageToDict(selected)
    with pytest.raises(AssertionError, match="complete selected body"):
        assert_selected_body(corrupted)


@pytest.mark.parametrize(
    "fault", ["bool-int", "zero-bool", "observer", "duplicate", "missing", "empty-queue-body"]
)
def test_entry_snapshot_anchor_rejects_corruption(
    body_entry_export: dict[str, Any], fault: str
) -> None:
    corrupted = deepcopy(body_entry_export)
    snapshot = corrupted["snapshots"][4]  # actual guarded-body, both invalid
    if fault == "bool-int":
        snapshot["ev"] = 0
    elif fault == "zero-bool":
        snapshot["vars"]["scratch"][2] = False
    elif fault == "observer":
        snapshot["vars"]["observer"] = None
    elif fault == "duplicate":
        corrupted["snapshots"][5] = deepcopy(snapshot)
    elif fault == "missing":
        corrupted["snapshots"].pop()
    else:
        snapshot["queue"]["block"]["body"] = []
    with pytest.raises(AssertionError):
        assert_snapshots(corrupted)
