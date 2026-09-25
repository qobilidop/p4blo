"""Authored field reads with an independent full aggregate-state observer.

The wrapper exposes stored fields even when their header is invalid. It is
unverified test scaffolding, not a parser or a whole-program Lean compiler.
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
from p4blo.interp import expr
from p4blo.interp.values import Bits, Header, Value
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb

# Width, initial header validity, independently expected expression bytes.
EXPECTED: dict[str, tuple[int | None, bool, bytes]] = {
    "field-add-valid": (8, True, b"\x00"),
    "field-add-invalid": (8, False, b"\x00"),
    "field-right": (9, False, b"\x01\x01"),
    "field-port": (9, True, b"\x00\x08"),
    "field-mux": (9, False, b"\x01\x01"),
    "field-equal": (None, True, b"\x01"),
    "field-no": (9, False, b"\x01\xff"),
}


def member(*names: str) -> pb.Expr:
    value = pb.Expr(var=names[0])
    for name in names[1:]:
        value = pb.Expr(member=pb.Member(base=value, field=name))
    return value


def target(*names: str) -> pb.LValue:
    value = pb.LValue(var=names[0])
    for name in names[1:]:
        value = pb.LValue(member=pb.LMember(base=value, field=name))
    return value


def field_program(name: str, expression: pb.Expr, width: int | None, valid: bool) -> pb.Program:
    program = scalar_program(bits(8, 0), 8)
    program.name = f"lean-fields-{name}"
    # Reserve H for the source header. Architecture scaffolding is separate.
    program.struct_types[0].name = "ObserverHeaders"
    program.headers = "ObserverHeaders"
    for block in program.blocks:
        block.params[0].type.struct = "ObserverHeaders"
    program.header_types.add(
        name="H",
        fields=[
            pb.Field(name="left", type=pb.Type(bits=8)),
            pb.Field(name="right", type=pb.Type(bits=9)),
        ],
    )
    program.struct_types.add(
        name="Packet",
        fields=[
            pb.Field(name="header", type=pb.Type(header="H")),
            pb.Field(name="sibling", type=pb.Type(bits=16)),
        ],
    )
    program.struct_types[1].fields.extend(
        [
            pb.Field(name="port", type=pb.Type(bits=9)),
            pb.Field(name="flag", type=pb.Type(boolean=pb.BoolType())),
        ]
    )
    control = program.blocks[1]
    control.params[0].name = "observer"
    control.locals.add(name="hdr", type=pb.Type(struct="Packet"))
    control.locals.add(name="unrelated", type=pb.Type(bits=8))
    del control.body[:]
    control.body.add(set_valid=pb.SetValid(header=target("observer", "result")))
    for path, value in [
        (("hdr", "header", "left"), bits(8, 171)),
        (("hdr", "header", "right"), bits(9, 257)),
        (("hdr", "sibling"), bits(16, 4660)),
        (("meta", "port"), bits(9, 3)),
        (("meta", "flag"), boolean(True)),
        (("unrelated",), bits(8, 165)),
    ]:
        control.body.add(assign=pb.Assign(target=target(*path), value=value))
    if valid:
        control.body.add(set_valid=pb.SetValid(header=target("hdr", "header")))
    observations = [
        ("left", 8, member("hdr", "header", "left")),
        ("right", 16, member("hdr", "header", "right")),
        ("sibling", 16, member("hdr", "sibling")),
        ("port", 16, member("meta", "port")),
        ("flag", 8, pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=member("meta", "flag")))),
        (
            "valid",
            8,
            pb.Expr(
                cast=pb.Cast(
                    to=pb.Type(bits=1),
                    operand=pb.Expr(is_valid=pb.IsValid(header=member("hdr", "header"))),
                )
            ),
        ),
        ("unrelated", 8, member("unrelated")),
        (
            "result",
            16 if width == 9 else 8,
            expression
            if width is not None
            else pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=expression)),
        ),
    ]
    del program.header_types[0].fields[:]
    for field, output_width, _ in observations:
        program.header_types[0].fields.add(name=field, type=pb.Type(bits=output_width))
    # Evaluate once before observing the source store. A returned scalar can
    # remain correct while a faulty read mutates a sibling or validity bit.
    for field, output_width, value in [observations[-1], *observations[:-1]]:
        control.body.add(
            assign=pb.Assign(
                target=target("observer", "result", field),
                value=pb.Expr(cast=pb.Cast(to=pb.Type(bits=output_width), operand=value)),
            )
        )
    return program


def test_field_exporter_is_a_default_target() -> None:
    root = Path(__file__).resolve().parents[2]
    package = tomllib.loads((root / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def authored_field_programs(lean_binary: Path) -> dict[str, pb.Program]:
    assert lean_binary.is_file()
    root = Path(__file__).resolve().parents[2]
    exporter = root / "impl/lean/.lake/build/bin/p4blo"
    assert exporter.is_file(), f"build {root}/scripts/check-lean.sh first"
    result: dict[str, pb.Program] = {}
    completed = subprocess.run(
        [str(exporter), "fieldExpressions"], capture_output=True, text=True, check=True, timeout=30
    )
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name in EXPECTED and name not in result
        width, valid, _ = EXPECTED[name]
        assert record["width"] == width and record["valid"] is valid
        expression = json_format.ParseDict(record["expression"], pb.Expr())
        result[name] = field_program(name, expression, width, valid)
    assert result.keys() == EXPECTED.keys()
    return result


@pytest.mark.parametrize("name", EXPECTED)
def test_lean_agrees_on_authored_field_known_answers(
    name: str, authored_field_programs: dict[str, pb.Program], lean_binary: Path
) -> None:
    program = authored_field_programs[name]
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
        bundle = directory / f"lean-fields-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    _, valid, answer = EXPECTED[name]
    # Every source field, the stored validity bit, and an unrelated root.
    expected = b"\xab\x01\x01\x12\x34\x00\x03\x01" + bytes([valid, 165]) + answer
    assert run_python(arch.reference.load(program), case, 4) == [(0, expected)]


def test_lean_agrees_after_retained_field_read_side_effect(
    authored_field_programs: dict[str, pb.Program],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A correct scalar result must not conceal a mutated source sibling."""
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    original = expr.field_of

    def wrong_read(container: Value, field: str, index: Index) -> Value:
        result = original(container, field, index)
        if isinstance(container, Header) and container.type_name == "H" and field == "right":
            container.fields[0] = Bits(8, 0)
        return result

    program = authored_field_programs["field-right"]
    # Retain the weaker observer as an explicit adversarial control: it reads
    # left before right corrupts it, and evaluates the expression last.
    weak = pb.Program()
    weak.CopyFrom(program)
    body = list(weak.blocks[1].body)
    selected = next(
        stmt for stmt in body if stmt.assign.target == target("observer", "result", "result")
    )
    del weak.blocks[1].body[:]
    weak.blocks[1].body.extend([stmt for stmt in body if stmt != selected] + [selected])
    bundle = tmp_path / "lean-fields-field-right.json"
    with monkeypatch.context() as fault:
        fault.setattr(expr, "field_of", wrong_read)
        assert compare_program(weak, [Case(pb.Entries(), 0, b"")], 4, [lean_binary]).passed
        with pytest.raises(pytest.fail.Exception, match="replay"):
            test_lean_agrees_on_authored_field_known_answers(
                "field-right", authored_field_programs, lean_binary
            )
        saved_program, cases, ports, seed = replay.load(bundle)
        assert saved_program == program and cases == [Case(pb.Entries(), 0, b"")]
        assert (ports, seed) == (4, 0)
        report = replay.replay(bundle, [lean_binary])
        assert report.protocol_error is None and report.both_errored == 0
        assert report.agreed == 0 and len(report.divergences) == 1
        mismatch = report.divergences[0]
        assert mismatch.python.outputs == ((0, bytes.fromhex("000101123400030100a50101")),)
        assert mismatch.lean.outputs == ((0, bytes.fromhex("ab0101123400030100a50101")),)
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
