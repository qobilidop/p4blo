"""Actual register reads: observe complete state after output copy-back."""

from __future__ import annotations

import copy
import itertools
from collections.abc import Sequence

import pytest

from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_lean_firewall import firewall as firewall
from tests.test_lean_firewall_bloom import ARRAYS, POSITIONS, initial as insertion_initial
from tests.test_lean_forwarder import freeze

PROFILES = list(itertools.product(range(len(ARRAYS)), POSITIONS, [False, True], [False, True], [False, True]))


def readback_body(program: pb.Program) -> list[pb.Stmt]:
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    filtering = ingress.body[0].conditional.then[1].conditional.then[2].conditional.then
    body = list(filtering[1].conditional.else_[0].conditional.then)
    expected_reads = [
        pb.Stmt(call_extern=pb.CallExtern(
            instance=name, method="read", args=[
                pb.Arg(lvalue=pb.LValue(var=target)), pb.Arg(expr=pb.Expr(var=position)),
            ],
        ))
        for name, target, position in [
            ("bloom_filter_1", "reg_val_one", "reg_pos_one"),
            ("bloom_filter_2", "reg_val_two", "reg_pos_two"),
        ]
    ]
    assert len(body) == 3 and body[:2] == expected_reads, "actual readback syntax changed"
    assert body[2].WhichOneof("stmt") == "conditional"
    assert list(body[2].conditional.then) == [pb.Stmt(call_action=pb.CallAction(action="drop"))]
    assert not body[2].conditional.else_
    return body[:2]


def initial(program: pb.Program, shape: int, positions: tuple[int, int], overlay: bool,
            layers: tuple[bool, bool]) -> Env:
    env = insertion_initial(program, shape, *positions, overlay)
    env.vars.update(reg_val_one=False, reg_val_two=Bits(17, 23))
    env.action = "readback-overlay"
    if env.action_vars is None:
        env.action_vars = {"sibling": Bits(13, 99)}
    if layers[0]:
        env.action_vars["reg_val_one"] = True
    if layers[1]:
        env.action_vars["reg_val_two"] = Bits(17, 42)
    return env


def observe_reads(env: Env, body: Sequence[pb.Stmt], shape: int,
                  positions: tuple[int, int], layers: tuple[bool, bool],
                  monkeypatch: pytest.MonkeyPatch) -> None:
    expected = copy.deepcopy(env)
    expected_trace: list[tuple[str, object]] = []
    for name, target, cells, position, action in zip(
        ["bloom_filter_1", "bloom_filter_2"], ["reg_val_one", "reg_val_two"],
        ARRAYS[shape], positions, layers, strict=True,
    ):
        value = Bits(1, cells[position] if position < len(cells) else 0)
        if action:
            assert expected.action_vars is not None
            expected.action_vars[target] = value
        else:
            expected.vars[target] = value
        expected_trace.append((name, freeze(expected)))
    original = stmt.call_extern
    observed: list[tuple[str, object]] = []

    def trace(call: pb.CallExtern, current: Env) -> None:
        assert current is env and call.method == "read", "unexpected readback call"
        original(call, current)
        observed.append((call.instance, freeze(current)))

    with monkeypatch.context() as patch:
        patch.setattr(stmt, "call_extern", trace)
        stmt.execute(body, env)
    assert observed == expected_trace, "readback copy-back state or call order changed"
    assert freeze(env) == freeze(expected), "readback final complete Env changed"


def test_readback_inventory() -> None:
    assert len(PROFILES) == 280
    assert set((first, second) for _, _, _, first, second in PROFILES) == set(itertools.product([False, True], repeat=2))


@pytest.mark.parametrize("shape,positions,overlay,first,second", PROFILES)
def test_lean_agrees_readback(firewall: pb.Program, monkeypatch: pytest.MonkeyPatch,
                            shape: int, positions: tuple[int, int], overlay: bool,
                            first: bool, second: bool) -> None:
    layers = (first, second)
    observe_reads(initial(firewall, shape, positions, overlay, layers),
                  readback_body(firewall), shape, positions, layers, monkeypatch)


def test_lean_agrees_readback_no_action(firewall: pb.Program, monkeypatch: pytest.MonkeyPatch) -> None:
    env = initial(firewall, 3, (1, 2), False, (False, False))
    env.action = None
    env.action_vars = None
    observe_reads(env, readback_body(firewall), 3, (1, 2), (False, False), monkeypatch)
