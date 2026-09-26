"""Real Lean execution conformance."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo.drt.case import Case
from p4blo.drt.replay import load
from p4blo.drt.run import compare_program
from p4blo.interp import expr
from p4blo.interp.values import Header, Struct, Value
from p4blo.interp.values import copy as copy_value
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt_aggregate_copy import WIDTHS, CopyKind, check_copy, copy_program


@pytest.mark.parametrize("kind", ["header", "struct"])
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("valid", [False, True])
@pytest.mark.lean
def test_lean_agrees_aggregate_copy_boundaries(
    lean_binary: Path, kind: CopyKind, width: int, valid: bool
) -> None:
    program, expected = copy_program(kind, width, valid, (1 << width) - 1, 1, 0, 2)
    check_copy(program, expected, lean_binary)


@settings(max_examples=40, deadline=None, derandomize=True)
@given(
    kind=st.sampled_from(["header", "struct"]),
    width=st.sampled_from(WIDTHS),
    valid=st.booleans(),
    data=st.data(),
)
@pytest.mark.lean
def test_lean_agrees_aggregate_copy_generated(
    lean_binary: Path, kind: CopyKind, width: int, valid: bool, data: st.DataObject
) -> None:
    values = data.draw(st.lists(st.integers(0, (1 << width) - 1), min_size=4, max_size=4))
    program, expected = copy_program(kind, width, valid, *values)
    check_copy(program, expected, lean_binary)


@pytest.mark.parametrize("kind", ["header", "struct"])
@pytest.mark.lean
def test_lean_agrees_copy_observer_kills_aliasing(
    lean_binary: Path, kind: CopyKind, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    program, expected = copy_program(kind, 9, False, 257, 19, 3, 7)

    def aliased(value: Value) -> Value:
        if isinstance(value, Header if kind == "header" else Struct):
            return value
        return copy_value(value)

    with monkeypatch.context() as mutation:
        mutation.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
        mutation.setattr(expr, "copy", aliased)
        with pytest.raises(pytest.fail.Exception, match="replay"):
            check_copy(program, expected, lean_binary)
        bundles = list(tmp_path.glob("*.json"))
        assert len(bundles) == 1
        restored_program, cases, ports, seed = load(bundles[0])
        assert restored_program == program
        assert cases == [Case(pb.Entries(), 0, b"")] and (ports, seed) == (4, 0)
        live = compare_program(restored_program, cases, ports, [lean_binary])
        assert len(live.divergences) == 1 and not live.passed
        difference = live.divergences[0]
        assert difference.python.error is None and difference.lean.error is None
        assert difference.python.diagnostic is None and difference.lean.diagnostic is None
        assert difference.python.outputs != difference.lean.outputs
    restored = compare_program(restored_program, cases, ports, [lean_binary])
    assert restored.passed
    check_copy(program, expected, lean_binary)
