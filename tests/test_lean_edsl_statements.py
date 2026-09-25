"""Lean-authored command bodies: independent whole-local-state answers.

The packet wrapper is intentionally unverified scaffolding. It initializes
inputs, executes exported syntax, and exposes every source binding plus an
unrelated sentinel. Differential failures are saved before answer assertions.
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
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, boolean, scalar_program
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.v0 import p4blo_pb2 as pb

# Inputs and complete final values, independently written; never obtained from
# source denotation, lowering, or the exporter. The fourth byte is unrelated.
EXPECTED: dict[str, tuple[tuple[int, int, bool], bytes]] = {
    "update-wrap": ((255, 7, False), b"\x00\x07\x01\xa5"),
    "update-dependent": ((3, 7, True), b"\x04\x0b\x00\xa5"),
    "update-y-wrap": ((254, 2, True), b"\xff\x01\x00\xa5"),
    "update-zero": ((0, 0, False), b"\x01\x01\x00\xa5"),
    "choose-yes": ((3, 7, True), b"\x0a\x11\x01\xa5"),
    "choose-no": ((3, 7, False), b"\x0c\x13\x00\xa5"),
    "choose-wrap": ((250, 255, True), b"\x01\x00\x01\xa5"),
    "skip": ((19, 7, True), b"\x13\x07\x01\xa5"),
    "boolean": ((19, 7, True), b"\x13\x07\x00\xa5"),
}


def test_statement_exporter_is_a_default_target() -> None:
    root = Path(__file__).resolve().parents[1]
    package = tomllib.loads((root / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


def statement_program(name: str, body: list[pb.Stmt], inputs: tuple[int, int, bool]) -> pb.Program:
    """Independent valid wrapper exposing all final local values as bytes."""
    program = scalar_program(bits(8, 0), 8)
    program.name = f"lean-statements-{name}"
    fields = program.header_types[0].fields
    del fields[:]
    for key in ("x", "y", "flag", "unrelated"):
        fields.add(name=key, type=pb.Type(bits=8))
    control = program.blocks[1]
    # Preserve only the already validated setValid statement from the context.
    del control.body[1:]
    values = {
        "x": bits(8, inputs[0]),
        "y": bits(8, inputs[1]),
        "flag": boolean(inputs[2]),
        "unrelated": bits(8, 165),
    }
    for key, value in values.items():
        ty = pb.Type(boolean=pb.BoolType()) if key == "flag" else pb.Type(bits=8)
        control.locals.add(name=key, type=ty)
        control.body.add(assign=pb.Assign(target=pb.LValue(var=key), value=value))
    control.body.extend(body)
    for key in values:
        value = pb.Expr(var=key)
        if key == "flag":
            value = pb.Expr(
                cast=pb.Cast(
                    to=pb.Type(bits=8),
                    operand=pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=value)),
                )
            )
        target = pb.LValue()
        target.member.base.member.base.var = "hdr"
        target.member.base.member.field = "result"
        target.member.field = key
        control.body.add(assign=pb.Assign(target=target, value=value))
    return program


@pytest.fixture(scope="module")
def authored_programs(lean_binary: Path) -> dict[str, pb.Program]:
    assert lean_binary.is_file()
    root = Path(__file__).resolve().parents[1]
    exporter = root / "impl/lean/.lake/build/bin/p4blo"
    assert exporter.is_file(), f"missing statement exporter: run {root}/scripts/check-lean.sh"
    completed = subprocess.run(
        [str(exporter), "scalarCommands"], capture_output=True, text=True, check=True, timeout=30
    )
    programs: dict[str, pb.Program] = {}
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name not in programs and name in EXPECTED, name
        inputs = record["inputs"]
        expected, _ = EXPECTED[name]
        assert inputs == dict(zip(("x", "y", "flag"), expected, strict=True)), name
        assert type(inputs["x"]) is int and type(inputs["y"]) is int
        assert type(inputs["flag"]) is bool
        body = [json_format.ParseDict(stmt, pb.Stmt()) for stmt in record["body"]]
        programs[name] = statement_program(name, body, expected)
    assert programs.keys() == EXPECTED.keys()
    return programs


@pytest.mark.parametrize("name", EXPECTED)
def test_lean_agrees_on_authored_statement_known_answers(
    name: str, authored_programs: dict[str, pb.Program], lean_binary: Path
) -> None:
    program = authored_programs[name]
    case = Case(pb.Entries(), 0, b"")
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        bundle = directory / f"lean-statements-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    # Both interpreters can agree on an unintended but well-typed source
    # command; independent expected bytes are a different essential oracle.
    assert run_python(arch.load(program), case, 4) == [(0, EXPECTED[name][1])]
