"""Real Lean execution conformance."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo.arch import v1model
from p4blo.drt.case import Case
from p4blo.drt.replay import load
from p4blo.drt.run import compare_program, run_python
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Header, Value
from p4blo.interp.values import copy as copy_value
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.copyback import copyback_program, expected_copyback
from tests.support.drt_call_copy import CallKind, call_program, check_call


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


@settings(max_examples=40, deadline=None, derandomize=True)
@given(
    kind=st.sampled_from(["action", "block"]),
    first=st.integers(0, 3),
    second=st.integers(0, 3),
    overlap=st.booleans(),
    packet=st.binary(min_size=2, max_size=4),
)
def test_lean_agrees_call_copy_computed_index_generated(
    lean_binary: Path, kind: CallKind, first: int, second: int, overlap: bool, packet: bytes
) -> None:
    """An `inout` argument `hdr.hs[t]` whose callee moves `t`: copy-back
    writes the element `t` named at copy-in (docs/ir-semantics.md,
    "Copy-back target"), including past the end, where it writes nothing."""
    program = copyback_program(kind, first, second, overlap)
    case = Case(pb.Entries(), 0, packet)
    report = compare_program(program, [case], 4, [lean_binary])
    assert report.passed, report.summary()
    assert run_python(v1model.load(program), case, 4) == [
        (0, expected_copyback(first, packet, overlap))
    ]


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
