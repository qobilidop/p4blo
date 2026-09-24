"""Typed field bodies with actual root directions and full post-body state.

The caller, initializers, observer, subcontrol copying and architecture are
unverified scaffolding. The authored subcontrol body sees hdr/meta inout,
route input-only and scratch local, matching its Lean declaration premise.
"""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo import arch
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, boolean, scalar_program
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Bits, Header, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_lean_edsl_fields import member, target

PAYLOAD = bytes.fromhex("deadbeef")
# Inputs: ttl, Ethernet validity, IPv4 validity, route hit. Complete changed
# values: dst/src MAC, ttl, protocol, port, drop, scratch. Independent constants,
# not exported source denotations or outputs obtained from either interpreter.
EXPECTED = {
    "dependent-wrap-valid": (
        (255, True, True, True),
        (0x111213141516, 0x212223242526, 0, 6, 7, True, 0),
    ),
    "dependent-wrap-invalid": (
        (255, False, False, True),
        (0x111213141516, 0x212223242526, 0, 6, 7, True, 0),
    ),
    "dependent-next": (
        (3, True, False, True),
        (0x111213141516, 0x212223242526, 4, 10, 4, False, 4),
    ),
    "dependent-protocol-wrap": (
        (249, False, True, False),
        (0x111213141516, 0x212223242526, 250, 0, 4, False, 250),
    ),
    "forward-hit": ((64, True, True, True), (0xAABBCCDDEEFF, 0x102030405060, 63, 6, 7, False, 19)),
    "forward-two": ((2, True, True, True), (0xAABBCCDDEEFF, 0x102030405060, 1, 6, 7, False, 19)),
    "forward-max": (
        (255, True, True, True),
        (0xAABBCCDDEEFF, 0x102030405060, 254, 6, 7, False, 19),
    ),
    "forward-zero": ((0, True, True, True), (0x111213141516, 0x212223242526, 0, 6, 3, True, 19)),
    "forward-one": ((1, True, True, True), (0x111213141516, 0x212223242526, 1, 6, 3, True, 19)),
    "forward-miss": ((64, True, True, False), (0x111213141516, 0x212223242526, 64, 6, 3, True, 19)),
}


def expected_packet(name: str) -> bytes:
    (_, ethernet_valid, ipv4_valid, hit), (dst, src, ttl, protocol, port, drop, scratch) = EXPECTED[
        name
    ]
    return (
        dst.to_bytes(6, "big")
        + src.to_bytes(6, "big")
        + bytes.fromhex("0800")
        + bytes([ethernet_valid, ttl, protocol])
        + bytes.fromhex("abcd")
        + bytes([ipv4_valid])
        + port.to_bytes(2, "big")
        + bytes([drop])
        + bytes.fromhex("1234")
        + bytes([hit])
        + bytes.fromhex("aabbccddeeff1020304050600007")
        + bytes([scratch, 165])
        + PAYLOAD
    )


def bool_byte(value: pb.Expr) -> pb.Expr:
    return pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=value))


def field_command_program(name: str, body: list[pb.Stmt]) -> pb.Program:
    ttl, ethernet_valid, ipv4_valid, hit = EXPECTED[name][0]
    program = scalar_program(bits(8, 0), 8)
    program.name = f"lean-field-commands-{name}"
    for header, fields in [
        ("Ethernet", [("dst", 48), ("src", 48), ("etherType", 16)]),
        ("IPv4", [("ttl", 8), ("protocol", 8), ("checksum", 16)]),
    ]:
        program.header_types.add(
            name=header, fields=[pb.Field(name=n, type=pb.Type(bits=w)) for n, w in fields]
        )
    program.struct_types.add(
        name="Headers",
        fields=[
            pb.Field(name="ethernet", type=pb.Type(header="Ethernet")),
            pb.Field(name="ipv4", type=pb.Type(header="IPv4")),
        ],
    )
    for struct_name, fields in [
        ("Metadata", [("port", 9), ("drop", None), ("sentinel", 16)]),
        ("Route", [("hit", None), ("dst", 48), ("src", 48), ("port", 9)]),
    ]:
        program.struct_types.add(
            name=struct_name,
            fields=[
                pb.Field(
                    name=n, type=pb.Type(boolean=pb.BoolType()) if w is None else pb.Type(bits=w)
                )
                for n, w in fields
            ],
        )
    caller = program.blocks[1]
    del caller.body[1:]
    for root, struct_name in [
        ("source_hdr", "Headers"),
        ("source_meta", "Metadata"),
        ("source_route", "Route"),
    ]:
        caller.locals.add(name=root, type=pb.Type(struct=struct_name))
    initializers = [
        (("source_hdr", "ethernet", "dst"), bits(48, 0x111213141516)),
        (("source_hdr", "ethernet", "src"), bits(48, 0x212223242526)),
        (("source_hdr", "ethernet", "etherType"), bits(16, 0x0800)),
        (("source_hdr", "ipv4", "ttl"), bits(8, ttl)),
        (("source_hdr", "ipv4", "protocol"), bits(8, 6)),
        (("source_hdr", "ipv4", "checksum"), bits(16, 0xABCD)),
        (("source_meta", "port"), bits(9, 3)),
        (("source_meta", "drop"), boolean(True)),
        (("source_meta", "sentinel"), bits(16, 0x1234)),
        (("source_route", "hit"), boolean(hit)),
        (("source_route", "dst"), bits(48, 0xAABBCCDDEEFF)),
        (("source_route", "src"), bits(48, 0x102030405060)),
        (("source_route", "port"), bits(9, 7)),
    ]
    for path, value in initializers:
        caller.body.add(assign=pb.Assign(target=target(*path), value=value))
    for header, valid in [("ethernet", ethernet_valid), ("ipv4", ipv4_valid)]:
        if valid:
            caller.body.add(set_valid=pb.SetValid(header=target("source_hdr", header)))
    callee = program.blocks.add(name="RewriteBody", kind=pb.BLOCK_KIND_CONTROL)
    for root, struct_name, direction in [
        ("hdr", "Headers", pb.DIRECTION_INOUT),
        ("meta", "Metadata", pb.DIRECTION_INOUT),
        ("route", "Route", pb.DIRECTION_IN),
        ("observer", "H", pb.DIRECTION_INOUT),
    ]:
        callee.params.add(name=root, type=pb.Type(struct=struct_name), direction=direction)
    for root, value in [("scratch", 19), ("unrelated", 165)]:
        callee.locals.add(name=root, type=pb.Type(bits=8))
        callee.body.add(assign=pb.Assign(target=target(root), value=bits(8, value)))
    # Execute the authored body exactly once before taking any observation.
    callee.body.extend(body)
    observations = [
        ("dst", 48, member("hdr", "ethernet", "dst")),
        ("src", 48, member("hdr", "ethernet", "src")),
        ("etherType", 16, member("hdr", "ethernet", "etherType")),
        (
            "ethernetValid",
            8,
            bool_byte(pb.Expr(is_valid=pb.IsValid(header=member("hdr", "ethernet")))),
        ),
        ("ttl", 8, member("hdr", "ipv4", "ttl")),
        ("protocol", 8, member("hdr", "ipv4", "protocol")),
        ("checksum", 16, member("hdr", "ipv4", "checksum")),
        ("ipv4Valid", 8, bool_byte(pb.Expr(is_valid=pb.IsValid(header=member("hdr", "ipv4"))))),
        ("port", 16, member("meta", "port")),
        ("drop", 8, bool_byte(member("meta", "drop"))),
        ("sentinel", 16, member("meta", "sentinel")),
        ("routeHit", 8, bool_byte(member("route", "hit"))),
        ("routeDst", 48, member("route", "dst")),
        ("routeSrc", 48, member("route", "src")),
        ("routePort", 16, member("route", "port")),
        ("scratch", 8, member("scratch")),
        ("unrelated", 8, member("unrelated")),
    ]
    del program.header_types[0].fields[:]
    for field, width, value in observations:
        program.header_types[0].fields.add(name=field, type=pb.Type(bits=width))
        callee.body.add(
            assign=pb.Assign(
                target=target("observer", "result", field),
                value=pb.Expr(cast=pb.Cast(to=pb.Type(bits=width), operand=value)),
            )
        )
    caller.body.add(
        call_block=pb.CallBlock(
            block="RewriteBody",
            args=[
                pb.Arg(lvalue=target("source_hdr")),
                pb.Arg(lvalue=target("source_meta")),
                pb.Arg(expr=member("source_route")),
                pb.Arg(lvalue=target("hdr")),
            ],
        )
    )
    return program


def test_field_command_exporter_is_a_default_target() -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "impl/lean/lakefile.toml").read_text())
    assert {"UserProofAudit", "fieldCommands"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def authored_field_commands(lean_binary: Path) -> dict[str, pb.Program]:
    assert lean_binary.is_file()
    root = Path(__file__).resolve().parents[1]
    exporter = root / "impl/lean/.lake/build/bin/fieldCommands"
    assert exporter.is_file(), f"build {root}/scripts/check-lean.sh first"
    completed = subprocess.run(
        [str(exporter)], capture_output=True, text=True, check=True, timeout=30
    )
    programs: dict[str, pb.Program] = {}
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name in EXPECTED and name not in programs
        ttl, ethernet_valid, ipv4_valid, hit = EXPECTED[name][0]
        assert type(record["ttl"]) is int and record["ttl"] == ttl
        assert record["ethernetValid"] is ethernet_valid and record["ipv4Valid"] is ipv4_valid
        assert record["hit"] is hit
        body = [json_format.ParseDict(statement, pb.Stmt()) for statement in record["body"]]
        programs[name] = field_command_program(name, body)
    assert programs.keys() == EXPECTED.keys()
    return programs


@pytest.mark.parametrize("name", EXPECTED)
def test_lean_agrees_on_authored_field_commands(
    name: str, authored_field_commands: dict[str, pb.Program], lean_binary: Path
) -> None:
    program = authored_field_commands[name]
    case = Case(pb.Entries(), 0, PAYLOAD)
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        bundle = directory / f"lean-field-commands-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    assert run_python(arch.load(program), case, 4) == [(0, expected_packet(name))]


@pytest.mark.parametrize("fault_kind", ["validity", "sibling"])
def test_lean_agrees_after_retained_authored_field_write_fault(
    fault_kind: str,
    authored_field_commands: dict[str, pb.Program],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fault only the authored TTL write, not any wrapper initializer."""
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    original = expr.write_lvalue

    def wrong_write(lv: pb.LValue, value: Value, env: Env) -> None:
        original(lv, value, env)
        if env.block.name == "RewriteBody" and lv == target("hdr", "ipv4", "ttl"):
            container = expr.read_lvalue(lv.member.base, env)
            assert isinstance(container, Header) and container.type_name == "IPv4"
            if fault_kind == "validity":
                container.valid = True
            else:
                container.fields[2] = Bits(16, 0)

    name = "dependent-wrap-invalid"
    bundle = tmp_path / f"lean-field-commands-{name}.json"
    with monkeypatch.context() as fault:
        fault.setattr(stmt, "write_lvalue", wrong_write)
        with pytest.raises(pytest.fail.Exception, match="replay"):
            test_lean_agrees_on_authored_field_commands(name, authored_field_commands, lean_binary)
        saved_program, cases, ports, seed = replay.load(bundle)
        assert saved_program == authored_field_commands[name]
        assert cases == [Case(pb.Entries(), 0, PAYLOAD)] and (ports, seed) == (4, 0)
        report = replay.replay(bundle, [lean_binary])
        assert report.protocol_error is None and report.both_errored == 0
        assert report.agreed == 0 and len(report.divergences) == 1
        expected = expected_packet(name)
        corrupted = bytearray(expected)
        if fault_kind == "validity":
            corrupted[19] = 1
        else:
            corrupted[17:19] = b"\x00\x00"
        mismatch = report.divergences[0]
        assert mismatch.python.outputs == ((0, bytes(corrupted)),)
        assert mismatch.lean.outputs == ((0, expected),)
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
