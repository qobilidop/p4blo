"""Whole invalid-body Python state, separate from packet/extern observations."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any, cast

import pytest

from p4blo import arch
from p4blo.arch.externs.register import Register
from p4blo.drt.case import Case
from p4blo.drt.run import compare_program
from p4blo.interp import expr, stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.lean.test_lean_firewall import firewall as firewall
from tests.lean.test_lean_forwarder import freeze
from tests.programs.test_firewall import connection


def expected_vars() -> dict[str, Value]:
    return {
        "hdr": Struct(
            "headers",
            [
                Header("ethernet_t", False, [Bits(48, 0), Bits(48, 0), Bits(16, 0)]),
                Header(
                    "ipv4_t",
                    False,
                    [Bits(w, 0) for w in [4, 4, 8, 16, 16, 3, 13, 8, 8, 16, 32, 32]],
                ),
                Header(
                    "tcp_t",
                    False,
                    [
                        Bits(w, 0)
                        for w in [16, 16, 32, 32, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 16, 16, 16]
                    ],
                ),
            ],
        ),
        "meta": Struct("metadata", [Bits(9, 0), Bits(9, 0), False]),
        "reg_pos_one": Bits(32, 0),
        "reg_pos_two": Bits(32, 0),
        "reg_val_one": Bits(1, 0),
        "reg_val_two": Bits(1, 0),
        "direction": Bits(1, 0),
        "crc16_result": Bits(16, 0),
        "check_ports_hit": False,
    }


def invalid_env(
    program: pb.Program, ev: bool, drop: bool, overlay: bool, dirty: bool, tcp_shape: int
) -> Env:
    loaded = arch.load(program)
    installed = loaded.entries(connection()[0].case.entries)
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.value, emitter.width = 0x1234, 13
    # Deliberately arbitrary state rather than a claim of fresh initialization.
    for name, values in [("bloom_filter_1", [1, 0, 1]), ("bloom_filter_2", [0, 1])]:
        register = loaded.externs[name]
        assert isinstance(register, Register)
        register.cells[:] = [Bits(1, v) for v in values]
    sentinel = Register(2, 8)
    sentinel.cells[:] = [Bits(8, 7), Bits(8, 9)]
    loaded.externs["sentinel"] = sentinel
    env = Env.for_block(
        loaded.index,
        loaded.index.blocks["MyIngress"],
        loaded.externs,
        entries=installed,
        packet=packet,
        emitter=emitter,
        visits={("sentinel", "state"): 13},
    )
    tcp: Value = [
        Header("tcp_t", False, []),
        Header("tcp_t", True, [Bits(7, 83)]),
        Struct("UnusedUnknown", [True, Bits(65, 0x12345)]),
    ][tcp_shape]
    headers = Struct(
        "headers",
        [
            Header("ethernet_t", ev, [Bits(48, 0x101), Bits(48, 0x202), Bits(16, 0x0800)]),
            Header("ipv4_t", False, [True, Bits(9, 511)] if dirty else []),
            tcp,
        ],
    )
    env.vars["hdr"] = headers
    env.vars["meta"] = Struct("metadata", [Bits(9, 3), Bits(9, 511), drop])
    if dirty:
        env.vars.update(
            reg_pos_one=Bits(32, 0xFFFFFFFF),
            reg_pos_two=Bits(32, 211),
            reg_val_one=Bits(1, 1),
            reg_val_two=Bits(1, 1),
            direction=Bits(1, 1),
            crc16_result=Bits(16, 0xFFFF),
            check_ports_hit=True,
        )
    env.vars["untouched"] = Struct("Unrelated", [Bits(5, 17), True])
    if overlay:
        env.vars["hdr"] = True
        env.action = "operational-overlay"
        env.action_vars = {"hdr": headers, "reg_pos_one": True, "shadow": Bits(17, 0x12345)}
    return env


def observe_body(env: Env) -> None:
    before = freeze(env)
    stmt.execute(env.block.body, env)
    assert freeze(env) == before, "invalid IPv4 changed complete firewall Env"


def test_lean_agrees_firewall_actual_initialization(firewall: pb.Program) -> None:
    loaded = arch.load(firewall)
    frame = Env.for_block(loaded.index, loaded.index.blocks["MyIngress"], loaded.externs)
    assert freeze(frame.vars) == freeze(expected_vars())
    assert frame.action is None and frame.action_vars is None
    assert frame.scope is loaded.index.scopes["MyIngress"]


@pytest.mark.parametrize(
    "ev,drop,overlay,dirty,tcp_shape",
    list(itertools.product([False, True], [False, True], [False, True], [False, True], range(3))),
)
def test_lean_agrees_firewall_invalid_body(
    firewall: pb.Program, ev: bool, drop: bool, overlay: bool, dirty: bool, tcp_shape: int
) -> None:
    observe_body(invalid_env(firewall, ev, drop, overlay, dirty, tcp_shape))


@pytest.mark.parametrize(
    "fault", ["local", "tcp", "bloom", "index", "scope", "entries", "cursor-type", "overlay"]
)
def test_lean_agrees_firewall_invalid_observer_rejects_effects(
    firewall: pb.Program, monkeypatch: pytest.MonkeyPatch, fault: str
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
    firewall: pb.Program, lean_binary: Path, monkeypatch: pytest.MonkeyPatch
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
