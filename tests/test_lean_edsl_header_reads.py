"""Authored validity reads with a complete post-read observer inside the callee.

Inputs really are read-only parameters. Snapshot before returning so copying
an input parameter cannot conceal a read-side effect on its callee-local value.
Initializers, caller copying and the observer remain unverified scaffolding.
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
# Explicit expected answers, independent of exported source syntax/denotation.
# a,b; first,second,direct,empty,mixed expression results; command result,flag.
ANSWERS = {
    "00": (False, False, (0, 0, 1, 0, 204), (19, False)),
    "01": (False, True, (0, 1, 1, 1, 204), (19, True)),
    "10": (True, False, (1, 0, 0, 0, 0), (205, False)),
    "11": (True, True, (1, 1, 0, 1, 0), (205, True)),
}
KINDS = ("first", "second", "direct", "empty", "mixed", "command")
NAMES = [f"{kind}-{suffix}" for suffix in ANSWERS for kind in KINDS]


def bool_byte(value: pb.Expr) -> pb.Expr:
    return pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=value))


def validity(*path: str) -> pb.Expr:
    # The identity mux distinguishes observer reads from the authored operand
    # in scoped mutations. Otherwise an observer fault can conceal a weak
    # pre-expression snapshot order by corrupting state a second time.
    header = pb.Expr(
        mux=pb.Mux(
            **{"condition": boolean(True), "then": member(*path), "otherwise": member(*path)}
        )
    )
    return bool_byte(pb.Expr(is_valid=pb.IsValid(header=header)))


def expected_packet(name: str) -> bytes:
    kind, suffix = name.split("-")
    a, b, values, (result, flag) = ANSWERS[suffix]
    answer = 0 if kind == "command" else values[KINDS.index(kind)]
    if kind != "command":
        result, flag = 0, False
    return bytes([171, a, 57, b, 0x12, 0x34, 204, not a, b, flag, result, answer, 165]) + PAYLOAD


def header_read_program(name: str, body: list[pb.Stmt]) -> pb.Program:
    _, suffix = name.split("-")
    a, b, _, _ = ANSWERS[suffix]
    program = scalar_program(bits(8, 0), 8)
    program.name = f"lean-header-reads-{name}"
    program.header_types.add(
        name="ReadHeader", fields=[pb.Field(name="byte", type=pb.Type(bits=8))]
    )
    program.header_types.add(name="ReadEmpty")
    program.struct_types.add(
        name="ReadPacket",
        fields=[
            pb.Field(name="first", type=pb.Type(header="ReadHeader")),
            pb.Field(name="second", type=pb.Type(header="ReadHeader")),
            pb.Field(name="sentinel", type=pb.Type(bits=16)),
        ],
    )
    caller = program.blocks[1]
    del caller.body[1:]
    root_types = [
        ("packet", pb.Type(struct="ReadPacket"), pb.DIRECTION_IN),
        ("direct", pb.Type(header="ReadHeader"), pb.DIRECTION_IN),
        ("empty", pb.Type(header="ReadEmpty"), pb.DIRECTION_IN),
        ("result", pb.Type(bits=8), pb.DIRECTION_OUT),
        ("flag", pb.Type(boolean=pb.BoolType()), pb.DIRECTION_OUT),
    ]
    for root, ty, _ in root_types:
        caller.locals.add(name=f"source_{root}", type=ty)
    for path, width, value in [
        (("source_packet", "first", "byte"), 8, 171),
        (("source_packet", "second", "byte"), 8, 57),
        (("source_packet", "sentinel"), 16, 4660),
        (("source_direct", "byte"), 8, 204),
    ]:
        caller.body.add(assign=pb.Assign(target=target(*path), value=bits(width, value)))
    for path, valid in [
        (("source_packet", "first"), a),
        (("source_packet", "second"), b),
        (("source_direct",), not a),
        (("source_empty",), b),
    ]:
        if valid:
            caller.body.add(set_valid=pb.SetValid(header=target(*path)))
    callee = program.blocks.add(name="HeaderReadBody", kind=pb.BLOCK_KIND_CONTROL)
    for root, ty, direction in root_types:
        callee.params.add(name=root, type=ty, direction=direction)
    callee.params.add(name="observer", type=pb.Type(struct="H"), direction=pb.DIRECTION_INOUT)
    callee.locals.add(name="unrelated", type=pb.Type(bits=8))
    callee.locals.add(name="answer", type=pb.Type(bits=8))
    callee.body.add(assign=pb.Assign(target=target("unrelated"), value=bits(8, 165)))
    # Imported authored expression/body executes once, before every snapshot.
    callee.body.extend(body)
    observations = [
        ("firstByte", 8, member("packet", "first", "byte")),
        ("firstValid", 8, validity("packet", "first")),
        ("secondByte", 8, member("packet", "second", "byte")),
        ("secondValid", 8, validity("packet", "second")),
        ("sentinel", 16, member("packet", "sentinel")),
        ("directByte", 8, member("direct", "byte")),
        ("directValid", 8, validity("direct")),
        ("emptyValid", 8, validity("empty")),
        ("flag", 8, bool_byte(member("flag"))),
        ("result", 8, member("result")),
        ("answer", 8, member("answer")),
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
            block=callee.name,
            args=[
                pb.Arg(expr=member(f"source_{root}"))
                if direction == pb.DIRECTION_IN
                else pb.Arg(lvalue=target(f"source_{root}"))
                for root, _, direction in root_types
            ]
            + [pb.Arg(lvalue=target("hdr"))],
        )
    )
    return program


def exported_programs(exporter: Path) -> dict[str, pb.Program]:
    completed = subprocess.run(
        [str(exporter), "headerReads"], capture_output=True, text=True, check=True, timeout=30
    )
    programs: dict[str, pb.Program] = {}
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name in NAMES and name not in programs
        kind, suffix = name.split("-")
        a, b, _, _ = ANSWERS[suffix]
        assert record["a"] is a and record["b"] is b
        if kind == "command":
            assert record.keys() == {"name", "a", "b", "body"}
            body = [json_format.ParseDict(item, pb.Stmt()) for item in record["body"]]
        else:
            assert record.keys() == {"name", "a", "b", "width", "expression"}
            if kind == "mixed":
                assert type(record["width"]) is int and record["width"] == 8
            else:
                assert record["width"] is None
            expression = json_format.ParseDict(record["expression"], pb.Expr())
            if kind != "mixed":
                expression = pb.Expr(
                    cast=pb.Cast(to=pb.Type(bits=8), operand=bool_byte(expression))
                )
            body = [pb.Stmt(assign=pb.Assign(target=target("answer"), value=expression))]
        programs[name] = header_read_program(name, body)
    assert programs.keys() == set(NAMES)
    return programs


def pre_read_observer(program: pb.Program) -> pb.Program:
    """Deliberately weaker observer used only as an adversarial control."""
    weak = pb.Program()
    weak.CopyFrom(program)
    callee = weak.blocks[-1]
    statements = list(callee.body)
    authored = statements[1]
    assert authored.assign.target == target("answer")
    del callee.body[:]
    callee.body.extend([statements[0], *statements[2:], authored])
    return weak


def test_header_read_exporter_is_a_default_target() -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def authored_header_reads(lean_binary: Path) -> dict[str, pb.Program]:
    assert lean_binary.is_file()
    root = Path(__file__).resolve().parents[1]
    exporter = root / "impl/lean/.lake/build/bin/p4blo"
    assert exporter.is_file(), f"build {root}/scripts/check-lean.sh first"
    return exported_programs(exporter)


@pytest.mark.parametrize("name", NAMES)
def test_lean_agrees_on_authored_header_reads(
    name: str, authored_header_reads: dict[str, pb.Program], lean_binary: Path
) -> None:
    program = authored_header_reads[name]
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
        bundle = directory / f"lean-header-reads-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    assert run_python(arch.load(program), case, 4) == [(0, expected_packet(name))]


@pytest.mark.parametrize("fault_kind", ["return", "side-effect"])
def test_lean_agrees_after_retained_validity_read_fault(
    fault_kind: str,
    authored_header_reads: dict[str, pb.Program],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fault an actual evaluator read; preserve and replay its complete input."""
    original = expr.evaluate
    hits = 0

    def wrong_read(value: pb.Expr, env: Env) -> Value:
        nonlocal hits
        result = original(value, env)
        if env.block.name == "HeaderReadBody" and value == pb.Expr(
            is_valid=pb.IsValid(header=member("packet", "first"))
        ):
            hits += 1
            if fault_kind == "return":
                assert type(result) is bool
                return not result
            sibling = original(member("packet", "second"), env)
            assert isinstance(sibling, Header)
            sibling.fields[0] = Bits(8, 0)
        return result

    name = "first-01"
    bundle = tmp_path / f"lean-header-reads-{name}.json"
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    with monkeypatch.context() as fault:
        fault.setattr(expr, "evaluate", wrong_read)
        fault.setattr(stmt, "evaluate", wrong_read)
        if fault_kind == "side-effect":
            weak = pre_read_observer(authored_header_reads[name])
            case = Case(pb.Entries(), 0, PAYLOAD)
            weak_report = compare_program(weak, [case], 4, [lean_binary])
            assert weak_report.passed and weak_report.agreed == 1 and hits == 1
            assert run_python(arch.load(weak), case, 4) == [(0, expected_packet(name))]
        with pytest.raises(pytest.fail.Exception, match="replay"):
            test_lean_agrees_on_authored_header_reads(name, authored_header_reads, lean_binary)
        program, cases, ports, seed = replay.load(bundle)
        assert program == authored_header_reads[name]
        assert cases == [Case(pb.Entries(), 0, PAYLOAD)] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert live.protocol_error is None and live.both_errored == 0
        assert live.agreed == 0 and len(live.divergences) == 1
        expected = expected_packet(name)
        wrong = bytearray(expected)
        if fault_kind == "return":
            wrong[11] = 1
        else:
            wrong[2] = 0  # Correct returned Bool, corrupted sibling stored byte.
        mismatch = live.divergences[0]
        assert mismatch.python.outputs == ((0, bytes(wrong)),)
        assert mismatch.lean.outputs == ((0, expected),)
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
