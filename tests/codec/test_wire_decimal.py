"""Decimal wire defaults must not fabricate a valid numeric zero.

Protobuf parsing supplies an empty string for omitted/null string fields;
the Python validator rejects that spelling. Lean's Nat-based IR must reject
at its decoding boundary instead of inventing a value that cannot preserve
the original malformed representation. This is not full ProtoJSON parity.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from google.protobuf import json_format

from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, scalar_program
from p4blo.drt.run import run_python
from p4blo.drt.state import encode, snapshot
from p4blo.interp.tables import InstallError
from p4blo.v0 import p4blo_pb2 as pb


def decimal_program(kind: str) -> apb.BlockAssembly:
    program = scalar_program(bits(8, 0), 8)
    if kind != "literal":
        control = program.blocks[1]
        control.actions.add(name="NoAction")
        table = control.tables.add(name="t", size=1, actions=["NoAction"])
        table.default_action.action = "NoAction"
        match = pb.MATCH_KIND_LPM if kind == "lpm" else pb.MATCH_KIND_TERNARY
        table.keys.add(expr=bits(8, 0), match_kind=match)
        entry = table.const_entries.add(action=pb.ActionCall(action="NoAction"))
        if kind == "lpm":
            entry.keys.add(lpm=pb.LpmValue(value="0", prefix_len=8))
        else:
            entry.priority = 0
            entry.keys.add(ternary=pb.TernaryValue(value="0", mask="255"))
    assert validator.validate(program) == []
    return program


def decimal_field(wire: dict[str, Any], kind: str) -> tuple[dict[str, Any], str, str]:
    if kind == "literal":
        return (
            wire["blocks"][1]["body"][1]["assign"]["value"]["literal"]["bits"],
            "value",
            "bits.value",
        )
    key = wire["blocks"][1]["tables"][0]["const_entries"][0]["keys"][0]
    if kind == "lpm":
        return key["lpm"], "value", "lpm.value"
    field = "mask" if kind == "ternary-mask" else "value"
    return key["ternary"], field, f"ternary.{field}"


@pytest.mark.parametrize("kind", ["literal", "lpm", "ternary-value", "ternary-mask"])
@pytest.mark.parametrize("spelling", ["missing", "null", "empty", "negative", "hex", "number"])
def test_lean_agrees_on_rejected_decimal_spelling(
    kind: str, spelling: str, lean_binary: Path
) -> None:
    wire = json.loads(arch_wire.dump_json(decimal_program(kind)))
    obj, field, path = decimal_field(wire, kind)
    if spelling == "missing":
        del obj[field]
    else:
        obj[field] = {"null": None, "empty": "", "negative": "-1", "hex": "0x0", "number": 0}[
            spelling
        ]
    text = json.dumps(wire)
    try:
        parsed = arch_wire.load_json(text)
    except json_format.ParseError:
        assert spelling == "number"
    else:
        problems = validator.validate(parsed)
        expected_code = validator.LITERAL_FORMAT if kind == "literal" else validator.ENTRY_SHAPE
        assert len(problems) == 1 and problems[0].code == expected_code, problems
        assert "not decimal" in problems[0].message
    result = subprocess.run(
        [str(lean_binary), "-"], input=text, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert path in result.stderr
    assert "expected a " in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("kind", ["literal", "lpm", "ternary-value", "ternary-mask"])
@pytest.mark.parametrize("spelling", ["0", "000", "7"])
def test_lean_agrees_on_explicit_decimal_strings(
    kind: str, spelling: str, lean_binary: Path
) -> None:
    wire = json.loads(arch_wire.dump_json(decimal_program(kind)))
    obj, field, _ = decimal_field(wire, kind)
    obj[field] = spelling
    text = json.dumps(wire)
    assert validator.validate(arch_wire.load_json(text)) == []
    result = subprocess.run(
        [str(lean_binary), "-"], input=text, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("scalar: ")
    assert result.stderr == ""


@pytest.mark.parametrize("kind", ["lpm", "ternary-value", "ternary-mask"])
@pytest.mark.parametrize("spelling", ["missing", "null"])
def test_lean_agrees_on_decimal_request_rejection_without_state_change(
    kind: str, spelling: str, lean_binary: Path, tmp_path: Path
) -> None:
    program = decimal_program(kind)
    control = program.blocks[1]
    table = control.tables[0]
    entries = pb.Entries()
    entries.tables.add(block="C", table="t").entries.extend(table.const_entries)
    table.ClearField("const_entries")
    control.body.add().apply.table = "t"
    counter = program.extern_types.add(name="counter")
    counter.constructor_params.add(name="size", type=pb.Type(bits=32), direction=pb.DIRECTION_IN)
    counter.methods.add(name="count").params.add(
        name="index", type=pb.Type(bits=32), direction=pb.DIRECTION_IN
    )
    program.extern_instances.add(name="ticks", extern_type="counter", args=[bits(32, 1).literal])
    call = control.body.add().call_extern
    call.instance, call.method = "ticks", "count"
    call.args.add(expr=bits(32, 0))
    loaded = v1model.load(program)
    valid = json_format.MessageToDict(entries, preserving_proto_field_name=True)
    malformed = json.loads(json.dumps(valid))
    key = malformed["tables"][0]["entries"][0]["keys"][0]
    obj = key["lpm"] if kind == "lpm" else key["ternary"]
    field = "mask" if kind == "ternary-mask" else "value"
    if spelling == "missing":
        del obj[field]
    else:
        obj[field] = None
    malformed_entries = json_format.ParseDict(malformed, pb.Entries())
    assert run_python(loaded, Case(entries, 0, b""), 4) == [(0, b"\x00")]
    expected_first = {"ticks": {"kind": "counter", "values": ["0x1"]}}
    assert encode(snapshot(loaded)) == expected_first
    with pytest.raises(InstallError, match="not decimal"):
        run_python(loaded, Case(malformed_entries, 0, b""), 4)
    assert encode(snapshot(loaded)) == expected_first
    assert run_python(loaded, Case(entries, 0, b""), 4) == [(0, b"\x00")]
    expected_final = {"ticks": {"kind": "counter", "values": ["0x2"]}}
    assert encode(snapshot(loaded)) == expected_final

    source = tmp_path / "decimal.json"
    source.write_text(arch_wire.dump_json(program))
    requests = "".join(
        json.dumps({"entries": value, "ingress_port": 0, "packet": ""}) + "\n"
        for value in (valid, malformed, valid)
    )
    result = subprocess.run(
        [str(lean_binary), "run", str(source)],
        input=requests,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(replies) == 3
    assert all(isinstance(r.pop("coverage"), list) for r in replies)
    assert replies[0] == {"outputs": [[0, "00"]], "state": expected_first}
    assert set(replies[1]) == {"error", "state"}
    assert f"{field}: expected a decimal number, got an empty string" in replies[1]["error"]
    assert replies[1]["state"] == expected_first
    assert replies[2] == {"outputs": [[0, "00"]], "state": expected_final}
