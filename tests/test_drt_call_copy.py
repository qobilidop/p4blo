"""Bounded call copy-in/out profile; overlapping writable arguments are excluded."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Literal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import arch
from p4blo.drt.case import Case
from p4blo.drt.programs import binary, bits, scalar_program
from p4blo.drt.replay import load, save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Header, Value
from p4blo.interp.values import copy as copy_value
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_drt_aggregate_copy import place, read

CallKind = Literal["action", "block"]


def call_program(
    kind: CallKind, width: int, valid: bool, a: int, b: int, changed: int
) -> tuple[pb.Program, bytes]:
    program = scalar_program(bits(8, 0), 8)
    program.name = f"aggregate-call-{kind}"
    header = program.header_types.add(name="Data")
    for name in ("left", "right"):
        header.fields.add(name=name, type=pb.Type(bits=width))
    control = program.blocks[1]
    del control.body[1:]
    for name, left, right in (("cell", a, b), ("output", 5, 7), ("unrelated", 11, 13)):
        control.locals.add(name=name, type=pb.Type(header="Data"))
        for field, value in (("left", left), ("right", right)):
            control.body.add(assign=pb.Assign(target=place(name, field), value=bits(width, value)))
        if valid or name != "cell":
            control.body.add(set_valid=pb.SetValid(header=place(name)))
    control.locals.add(name="sentinel", type=pb.Type(bits=8))
    control.body.add(assign=pb.Assign(target=place("sentinel"), value=bits(8, 165)))
    callee = (
        control.actions.add(name="rewrite")
        if kind == "action"
        else program.blocks.add(name="Rewrite", kind=pb.BLOCK_KIND_CONTROL)
    )
    for name, direction in (
        ("snapshot", pb.DIRECTION_IN),
        ("working", pb.DIRECTION_INOUT),
        ("result", pb.DIRECTION_OUT),
    ):
        callee.params.add(name=name, type=pb.Type(header="Data"), direction=direction)
    for target, value in (
        (("working", "left"), bits(width, changed)),
        (("working", "right"), read("snapshot", "left")),
        (("result", "left"), read("snapshot", "right")),
        (("result", "right"), binary(pb.BINARY_OP_ADD, read("result", "right"), bits(width, 1))),
    ):
        callee.body.add(assign=pb.Assign(target=place(*target), value=value))
    arguments = [
        pb.Arg(expr=read("cell")),
        pb.Arg(lvalue=place("cell")),
        pb.Arg(lvalue=place("output")),
    ]
    if kind == "action":
        control.body.add(call_action=pb.CallAction(action="rewrite", args=arguments))
    else:
        control.body.add(call_block=pb.CallBlock(block="Rewrite", args=arguments))

    fields = program.header_types[0].fields
    del fields[:]
    expected = bytearray()
    padded = ((width + 7) // 8) * 8
    for name, left, right, is_valid in (
        ("cell", changed, a, valid),
        ("output", b, 1, False),
        ("unrelated", 11, 13, True),
    ):
        for label, value, result_width, number in (
            ("left", read(name, "left"), padded, left),
            ("right", read(name, "right"), padded, right),
            (
                "valid",
                pb.Expr(
                    cast=pb.Cast(
                        to=pb.Type(bits=1),
                        operand=pb.Expr(is_valid=pb.IsValid(header=read(name))),
                    )
                ),
                8,
                int(is_valid),
            ),
        ):
            field = f"{name}_{label}"
            fields.add(name=field, type=pb.Type(bits=result_width))
            control.body.add(
                assign=pb.Assign(
                    target=place("hdr", "result", field),
                    value=pb.Expr(cast=pb.Cast(to=pb.Type(bits=result_width), operand=value)),
                )
            )
            expected.extend(number.to_bytes(result_width // 8, "big"))
    fields.add(name="sentinel", type=pb.Type(bits=8))
    control.body.add(
        assign=pb.Assign(target=place("hdr", "result", "sentinel"), value=read("sentinel"))
    )
    expected.append(165)
    return program, bytes(expected)


def check_call(program: pb.Program, expected: bytes, lean_binary: Path) -> None:
    # Nonempty unconsumed payload must survive both kinds of call.
    case = Case(pb.Entries(), 0, b"\xde\xad")
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        assert error.report is not None
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(program.SerializeToString()).hexdigest()[:24]
        bundle = directory / f"call-copy-{digest}.json"
        save(report, bundle)
        pytest.fail(f"{report.summary()}; replay {bundle}; {report.protocol_error}")
    assert run_python(arch.load(program), case, 4) == [(0, expected + case.packet)]


@pytest.mark.parametrize("kind", ["action", "block"])
@pytest.mark.parametrize("width", [8, 9, 65])
@pytest.mark.parametrize("valid", [False, True])
def test_lean_agrees_call_copy_boundaries(
    lean_binary: Path, kind: CallKind, width: int, valid: bool
) -> None:
    check_call(*call_program(kind, width, valid, (1 << width) - 1, 19, 3), lean_binary)


@settings(max_examples=40, deadline=None, derandomize=True)
@given(
    kind=st.sampled_from(["action", "block"]),
    width=st.sampled_from([8, 9, 65]),
    valid=st.booleans(),
    data=st.data(),
)
def test_lean_agrees_call_copy_generated(
    lean_binary: Path, kind: CallKind, width: int, valid: bool, data: st.DataObject
) -> None:
    values = data.draw(st.lists(st.integers(0, (1 << width) - 1), min_size=3, max_size=3))
    check_call(*call_program(kind, width, valid, *values), lean_binary)


@pytest.mark.parametrize("kind", ["action", "block"])
@pytest.mark.parametrize("fault", ["alias", "out-initial", "skip-copyback"])
def test_lean_agrees_call_copy_mutation_replays(
    lean_binary: Path,
    kind: CallKind,
    fault: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    program, expected = call_program(kind, 9, False, 257, 19, 3)
    argument_value = stmt.argument_value

    def alias(value: Value) -> Value:
        return value if isinstance(value, Header) else copy_value(value)

    def bad_out(param: pb.Param, arg: pb.Arg, env: Env) -> Value:
        if param.direction == pb.DIRECTION_OUT and arg.lvalue.var == "output":
            return copy_value(env.read("output"))
        return argument_value(param, arg, env)

    with monkeypatch.context() as mutation:
        mutation.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
        if fault == "alias":
            mutation.setattr(stmt, "copy", alias)
        elif fault == "out-initial":
            mutation.setattr(stmt, "argument_value", bad_out)
        else:
            mutation.setattr(stmt, "copy_back", lambda *_args: None)
        with pytest.raises(pytest.fail.Exception, match="replay"):
            check_call(program, expected, lean_binary)
        bundles = list(tmp_path.glob("*.json"))
        assert len(bundles) == 1
        restored_program, cases, ports, seed = load(bundles[0])
        assert restored_program == program and cases == [Case(pb.Entries(), 0, b"\xde\xad")]
        assert (ports, seed) == (4, 0)
        live = compare_program(restored_program, cases, ports, [lean_binary])
        assert not live.passed and len(live.divergences) == 1
        difference = live.divergences[0]
        assert difference.python.error is None and difference.lean.error is None
        assert difference.python.diagnostic is None and difference.lean.diagnostic is None
        assert difference.python.outputs != difference.lean.outputs
    assert compare_program(restored_program, cases, ports, [lean_binary]).passed
    check_call(program, expected, lean_binary)
