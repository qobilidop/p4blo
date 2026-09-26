"""Whole invalid-body Python state, separate from packet/extern observations."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any, cast

import pytest

from p4blo.arch import v1model
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.run import compare_program
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.firewall_body import (
    expected_vars,
    invalid_env,
    observe_body,
)
from tests.support.firewall_semantics import firewall as firewall
from tests.support.forwarder import freeze


def test_python_firewall_actual_initialization(firewall: apb.BlockAssembly) -> None:
    loaded = v1model.load(firewall)
    frame = Env.for_block(loaded.index, loaded.index.blocks["MyIngress"], loaded.externs)
    assert freeze(frame.vars) == freeze(expected_vars())
    assert frame.action is None and frame.action_vars is None
    assert frame.scope is loaded.index.scopes["MyIngress"]


@pytest.mark.parametrize(
    "ev,sentinel,overlay,dirty,tcp_shape",
    list(itertools.product([False, True], [False, True], [False, True], [False, True], range(3))),
)
def test_python_firewall_invalid_body(
    firewall: apb.BlockAssembly,
    ev: bool,
    sentinel: bool,
    overlay: bool,
    dirty: bool,
    tcp_shape: int,
) -> None:
    observe_body(invalid_env(firewall, ev, sentinel, overlay, dirty, tcp_shape))


@pytest.mark.parametrize(
    "fault", ["local", "tcp", "bloom", "index", "scope", "entries", "cursor-type", "overlay"]
)
def test_python_firewall_invalid_observer_rejects_effects(
    firewall: apb.BlockAssembly, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    original = stmt.execute_one
    hits = 0

    def corrupt(statement: pb.Stmt, env: Env) -> None:
        nonlocal hits
        original(statement, env)
        if not statement.HasField("conditional") or not statement.conditional.then[0].HasField(
            "apply"
        ):
            return
        hits += 1
        if fault == "local":
            env.vars["reg_pos_two"] = Bits(32, 17)
        elif fault == "tcp":
            expr.expect_struct(env.read("hdr")).fields[2] = Bits(7, 17)
        elif fault == "bloom":
            register = env.externs["bloom_filter_1"]
            assert isinstance(register, Register)
            register.cells[0] = Bits(1, 0)
        elif fault == "index":
            env.index.errors["NoError"] = 99
        elif fault == "scope":
            env.scope.actions.pop("NoAction")
        elif fault == "entries":
            assert env.entries is not None
            env.entries.entries.clear()
        elif fault == "cursor-type":
            assert env.packet is not None
            cast(Any, env.packet).cursor = float(env.packet.cursor)
        else:
            assert env.action_vars is not None
            env.action_vars["shadow"] = Bits(17, 0)

    with monkeypatch.context() as patch:
        patch.setattr(stmt, "execute_one", corrupt)
        with pytest.raises(AssertionError, match="complete firewall Env"):
            observe_body(invalid_env(firewall, True, False, True, True, 2))
    assert hits == 1


def test_lean_agrees_firewall_packet_observer_misses_local_effect(
    firewall: apb.BlockAssembly, lean_binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = stmt.execute_one
    hits = 0

    def corrupt(statement: pb.Stmt, env: Env) -> None:
        nonlocal hits
        original(statement, env)
        if env.block.name == "MyIngress" and statement.HasField("conditional"):
            if statement.conditional.then[0].HasField("apply"):
                headers = expr.expect_struct(env.read("hdr"))
                if not expr.expect_header(headers.fields[1]).valid:
                    env.vars["reg_pos_two"] = Bits(32, 17)
                    hits += 1

    packet = bytes.fromhex(
        "ffffffffffff000000000001080600010800060400010000000000010a0001010000000000000a000202"
    )
    with monkeypatch.context() as patch:
        patch.setattr(stmt, "execute_one", corrupt)
        report = compare_program(firewall, [Case(pb.Entries(), 0, packet)], 4, [lean_binary])
        assert report.passed and report.agreed == 1 and hits == 1
        with pytest.raises(AssertionError, match="complete firewall Env"):
            observe_body(invalid_env(firewall, True, False, False, True, 2))
        assert hits == 2
