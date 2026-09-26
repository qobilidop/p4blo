"""Actual Bloom insertion: full arrays, complete Env and first-call order."""

from __future__ import annotations

import copy
import itertools
from collections.abc import Sequence
from typing import Any, cast

import pytest

from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp import ExternResult, stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.corpus.forwarder.test_forwarder_semantics import freeze
from tests.programs.corpus.tutorial_firewall.test_firewall_body_semantics import invalid_env
from tests.programs.corpus.tutorial_firewall.test_firewall_semantics import firewall as firewall

ARRAYS = [([], []), ([0], [0]), ([1], [1]), ([1, 0, 0, 1], [0, 1, 0]), ([0] * 4096, [1] * 4096)]
POSITIONS = [(0, 0), (1, 2), (3, 1), (4095, 4095), (4096, 4096), (0xFFFFFFFF, 0xFFFFFFFF), (1, 1)]
PROFILES = list(itertools.product(range(len(ARRAYS)), POSITIONS, [False, True]))


def insertion_body(program: apb.BlockAssembly) -> list[pb.Stmt]:
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    tcp = ingress.body[0].conditional.then[1].conditional
    filtering = tcp.then[2].conditional.then
    body = list(filtering[1].conditional.then[0].conditional.then)
    expected = [
        pb.Stmt(
            call_extern=pb.CallExtern(
                instance=name,
                method="write",
                args=[
                    pb.Arg(expr=pb.Expr(var=position)),
                    pb.Arg(
                        expr=pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=1, value="1")))
                    ),
                ],
            )
        )
        for name, position in [("bloom_filter_1", "reg_pos_one"), ("bloom_filter_2", "reg_pos_two")]
    ]
    assert body == expected, "actual insertion syntax changed"
    return body


def register(env: Env, name: str) -> Register:
    value = env.externs[name]
    assert isinstance(value, Register)
    return value


def initial(program: apb.BlockAssembly, shape: int, p: int, q: int, overlay: bool) -> Env:
    env = invalid_env(program, True, True, False, True, 2)
    for name, cells in zip(["bloom_filter_1", "bloom_filter_2"], ARRAYS[shape], strict=True):
        register(env, name).cells[:] = [Bits(1, v) for v in cells]
    env.vars.update(reg_pos_one=Bits(32, p), reg_pos_two=Bits(32, q))
    if overlay:
        env.vars.update(reg_pos_one=True, reg_pos_two=False)
        env.action = "position-overlay"
        env.action_vars = {
            "reg_pos_one": Bits(32, p),
            "reg_pos_two": Bits(32, q),
            "sibling": Bits(13, 99),
        }
    return env


def expected_write(env: Env, name: str, position: int) -> None:
    target = register(env, name)
    target.cells[:] = [Bits(1, 1) if i == position else v for i, v in enumerate(target.cells)]


def observe_insertion(
    env: Env, body: Sequence[pb.Stmt], positions: tuple[int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = copy.deepcopy(env)
    expected_trace: list[tuple[str, object, object]] = []
    for name, position in zip(["bloom_filter_1", "bloom_filter_2"], positions, strict=True):
        value = Bits(32, position)
        expected_write(expected, name, position)
        expected_trace.append((name, freeze([value, Bits(1, 1)]), freeze(expected)))
    original = Register.call
    observed: list[tuple[str, object, object]] = []

    def trace(binding: Register, method: str, args: list[Value]) -> ExternResult:
        answer = original(binding, method, args)
        names = [name for name, other in env.externs.items() if other is binding]
        assert len(names) == 1 and method == "write", "unexpected Bloom call"
        observed.append((names[0], freeze(args), freeze(env)))
        return answer

    with monkeypatch.context() as patch:
        patch.setattr(Register, "call", trace)
        stmt.execute(body, env)
    assert observed == expected_trace, "Bloom intermediate complete Env or call order changed"
    assert freeze(env) == freeze(expected), "Bloom final complete Env changed"


def test_bloom_profile_inventory() -> None:
    assert len(PROFILES) == 70
    assert all(v in (0, 1) for pair in ARRAYS for cells in pair for v in cells)


@pytest.mark.parametrize("shape,positions,overlay", PROFILES)
def test_python_bloom_insertion(
    firewall: apb.BlockAssembly,
    monkeypatch: pytest.MonkeyPatch,
    shape: int,
    positions: tuple[int, int],
    overlay: bool,
) -> None:
    observe_insertion(
        initial(firewall, shape, *positions, overlay),
        insertion_body(firewall),
        positions,
        monkeypatch,
    )


@pytest.mark.parametrize(
    "fault", ["other-cell", "other-extern", "local", "overlay", "cursor-type", "repair"]
)
def test_python_bloom_observer_rejects_effects(
    firewall: apb.BlockAssembly, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    env = initial(firewall, 3, 1, 2, True)
    original = Register.call
    hits = 0

    def corrupt(binding: Register, method: str, args: list[Value]) -> ExternResult:
        nonlocal hits
        answer = original(binding, method, args)
        if binding is env.externs["bloom_filter_1"]:
            hits += 1
            if fault == "other-cell":
                binding.cells[0] = Bits(1, 0)
            elif fault == "other-extern":
                register(env, "sentinel").cells[0] = Bits(8, 0)
            elif fault == "local":
                env.vars["crc16_result"] = Bits(16, 17)
            elif fault in ("overlay", "repair"):
                assert env.action_vars is not None
                env.action_vars["sibling"] = Bits(13, 0)
            else:
                assert env.packet is not None
                cast(Any, env.packet).cursor = float(env.packet.cursor)
        elif fault == "repair":
            assert env.action_vars is not None
            env.action_vars["sibling"] = Bits(13, 99)
        return answer

    with monkeypatch.context() as patch:
        patch.setattr(Register, "call", corrupt)
        with pytest.raises(AssertionError, match="Bloom intermediate complete Env"):
            observe_insertion(env, insertion_body(firewall), (1, 2), monkeypatch)
    assert hits == 1


def test_python_bloom_order_survives_final_cells(
    firewall: apb.BlockAssembly, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = insertion_body(firewall)
    env = initial(firewall, 3, 1, 2, False)
    expected = copy.deepcopy(env)
    expected_write(expected, "bloom_filter_1", 1)
    expected_write(expected, "bloom_filter_2", 2)
    stmt.execute(list(reversed(body)), env)
    assert freeze(env) == freeze(expected), "reversal should survive a final-state-only observer"
    with pytest.raises(AssertionError, match="Bloom intermediate complete Env or call order"):
        observe_insertion(
            initial(firewall, 3, 1, 2, False), list(reversed(body)), (1, 2), monkeypatch
        )


def test_python_bloom_read_alias_is_not_expected(
    firewall: apb.BlockAssembly, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = initial(firewall, 3, 1, 2, True)
    original = Env.read
    hits = 0

    def alias(frame: Env, name: str) -> Value:
        nonlocal hits
        if frame is env and name == "reg_pos_one":
            hits += 1
            name = "reg_pos_two"
        return original(frame, name)

    with monkeypatch.context() as patch:
        patch.setattr(Env, "read", alias)
        with pytest.raises(AssertionError, match="Bloom intermediate complete Env"):
            observe_insertion(env, insertion_body(firewall), (1, 2), monkeypatch)
    # The expected model makes no production reads; this is the actual call.
    assert hits == 1
    assert register(env, "bloom_filter_1").cells == [Bits(1, v) for v in [1, 0, 1, 1]]
