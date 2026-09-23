"""Retained actual local-write fault; complete packet input survives for replay."""

from pathlib import Path

import pytest

from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_lean_edsl_field_commands import (
    PAYLOAD,
    expected_packet,
)
from tests.test_lean_edsl_field_commands import (
    authored_field_commands as authored_field_commands,
)
from tests.test_lean_edsl_field_commands import (
    test_lean_agrees_on_authored_field_commands as check_authored_case,
)


def test_lean_agrees_after_retained_initializer_write_fault(
    authored_field_commands: dict[str, pb.Program],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fault only the scratch initializer; forwarding itself leaves it alone."""
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    original = expr.write_lvalue
    hits = 0

    def wrong_write(lv: pb.LValue, value: Value, env: Env) -> None:
        nonlocal hits
        if (
            env.block.name == "RewriteBody"
            and lv == pb.LValue(var="scratch")
            and isinstance(value, Bits)
            and (value.width, value.value) == (8, 19)
        ):
            hits += 1
            value = Bits(8, 20)
        original(lv, value, env)

    name = "forward-hit"
    bundle = tmp_path / f"lean-field-commands-{name}.json"
    with monkeypatch.context() as fault:
        fault.setattr(stmt, "write_lvalue", wrong_write)
        with pytest.raises(pytest.fail.Exception, match="replay"):
            check_authored_case(name, authored_field_commands, lean_binary)
        assert hits == 1
        program, cases, ports, seed = replay.load(bundle)
        assert program == authored_field_commands[name]
        assert cases == [Case(pb.Entries(), 0, PAYLOAD)] and (ports, seed) == (4, 0)
        live = replay.replay(bundle, [lean_binary])
        assert hits == 2
        assert live.protocol_error is None and live.both_errored == 0
        assert live.agreed == 0 and len(live.divergences) == 1
        expected = expected_packet(name)
        corrupted = bytearray(expected)
        corrupted[-6] = 20  # scratch, unrelated, then the four payload bytes
        mismatch = live.divergences[0]
        assert mismatch.python.error is None and mismatch.lean.error is None
        assert mismatch.python.diagnostic is None and mismatch.lean.diagnostic is None
        assert mismatch.python.state == mismatch.lean.state == ()
        assert mismatch.python.outputs == ((0, bytes(corrupted)),)
        assert mismatch.lean.outputs == ((0, expected),)
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1
