"""Reusable forwarder actions fixtures and independent expectations."""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import pytest

from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.corpus.forwarder.forwarder import build
from tests.programs.ir_helpers import target
from tests.support.forwarder import assert_program_identity, freeze

ROOT = Path(__file__).resolve().parents[2]


PROFILES = {
    "-".join(str(v).lower() for v in values): values
    for values in itertools.product(
        [False, True], [False, True], [False, True], [0, 1, 255], [False, True]
    )
}


def destinations(name: str) -> tuple[int, int]:
    return (0xFFFFFFFFFFFE, 511) if PROFILES[name][4] else (0x020202020202, 2)


def values(name: str, *, final: bool = False) -> dict[str, Value]:
    ev, iv, sentinel, ttl, _ = PROFILES[name]
    dst, port = destinations(name)
    return {
        "hdr": Struct(
            "headers",
            [
                Header(
                    "ethernet_t",
                    ev,
                    [
                        Bits(48, dst if final else 0x010203040506),
                        Bits(48, 0x010203040506 if final else 0x111213141516),
                        Bits(16, 0x0800),
                    ],
                ),
                Header(
                    "ipv4_t",
                    iv,
                    [
                        Bits(4, 4),
                        Bits(4, 5),
                        Bits(8, 17),
                        Bits(16, 26),
                        Bits(16, 37),
                        Bits(3, 5),
                        Bits(13, 47),
                        Bits(8, ({0: 255, 1: 0, 255: 254}[ttl] if final else ttl)),
                        Bits(8, 17),
                        Bits(16, 0x9876),
                        Bits(32, 0x0A000101),
                        Bits(32, 0x0A000202),
                    ],
                ),
            ],
        ),
        "meta": Struct("metadata", [Bits(9, 3), Bits(9, port if final else 7)]),
        "untouched_flag": sentinel,
        "untouched": Bits(8, 165),
        "dstAddr": Bits(48, 99),
        "port": Bits(9, 77),
    }


def action_call(name: str) -> pb.ActionCall:
    dst, port = destinations(name)
    return pb.ActionCall(
        action="ipv4_forward",
        args=[
            pb.Literal(bits=pb.BitsLiteral(width=48, value=str(dst))),
            pb.Literal(bits=pb.BitsLiteral(width=9, value=str(port))),
        ],
    )


def parameters(name: str) -> dict[str, Value]:
    dst, port = destinations(name)
    return {"dstAddr": Bits(48, dst), "port": Bits(9, port)}


def environment(program: apb.BlockAssembly, name: str) -> Env:
    index = BoundIndex.build(program)
    entries = InstalledEntries(index)
    entries.entries[("MyIngress", "ipv4_lpm")] = [
        pb.Entry(
            keys=[pb.KeyValue(lpm=pb.LpmValue(value="167772672", prefix_len=24))],
            action=pb.ActionCall(action="drop"),
            priority=7,
        )
    ]
    entries.default_actions[("MyIngress", "ipv4_lpm")] = pb.ActionCall(action="NoAction")
    register = Register(3, 8)
    register.cells[:] = [Bits(8, n) for n in [3, 9, 27]]
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.write(3, 5)
    env = Env.for_block(
        index,
        index.blocks["MyIngress"],
        {"sentinel": register},
        entries=entries,
        packet=packet,
        emitter=emitter,
        visits={("parser", "state"): 13, ("sentinel", "one"): 1},
    )
    env.vars.update(values(name))
    return env


def expected_runs(program: apb.BlockAssembly, name: str) -> dict[str, Env]:
    before = environment(program, name)
    after = environment(program, name)
    after.vars.update(values(name, final=True))
    return {
        "before": before,
        "after": after,
        "entered": replace(before, action="ipv4_forward", action_vars=parameters(name)),
        "pending": replace(after, action="ipv4_forward", action_vars=parameters(name)),
    }


def selected_action(program: apb.BlockAssembly) -> pb.Action:
    action = next(
        a
        for b in program.blocks
        if b.name == "MyIngress"
        for a in b.actions
        if a.name == "ipv4_forward"
    )

    # The complete literal four-statement anchor is independent of candidate
    # policy, lowered Ref paths and any projection of its own body.
    def member(*path: str) -> pb.Expr:
        result = pb.Expr(var=path[0])
        for field in path[1:]:
            result = pb.Expr(member=pb.Member(base=result, field=field))
        return result

    def assign(path: tuple[str, ...], value: pb.Expr) -> pb.Stmt:
        return pb.Stmt(assign=pb.Assign(target=target(*path), value=value))

    expected = pb.Action(
        name="ipv4_forward",
        params=[
            pb.Param(name="dstAddr", type=pb.Type(bits=48), direction=pb.DIRECTION_NONE),
            pb.Param(name="port", type=pb.Type(bits=9), direction=pb.DIRECTION_NONE),
        ],
        body=[
            assign(("meta", "egress_spec"), pb.Expr(var="port")),
            assign(("hdr", "ethernet", "srcAddr"), member("hdr", "ethernet", "dstAddr")),
            assign(("hdr", "ethernet", "dstAddr"), pb.Expr(var="dstAddr")),
            assign(
                ("hdr", "ipv4", "ttl"),
                pb.Expr(
                    binary=pb.Binary(
                        op=pb.BINARY_OP_SUB,
                        left=member("hdr", "ipv4", "ttl"),
                        right=pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=8, value="1"))),
                    )
                ),
            ),
        ],
    )
    assert action == expected, "actual parameter/body identity"
    return action


def observe_action(program: apb.BlockAssembly, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    outer = environment(program, name)
    expectations = expected_runs(program, name)
    frozen = {phase: freeze(env) for phase, env in expectations.items()}
    probe = replace(expectations["pending"], action_vars=parameters(name))
    assert probe.action_vars is not None
    probe.action_vars["port"] = Bits(9, 1)
    expected_first_write = freeze(probe)
    probe.action_vars["dstAddr"] = Bits(48, 23)
    expected_second_write = freeze(probe)
    original = stmt.execute
    observed: list[Env] = []

    def observe(body: Iterable[pb.Stmt], inner: Env) -> None:
        observed.append(inner)
        assert list(body) == list(selected_action(program).body), "selected body identity"
        assert freeze(inner) == frozen["entered"], "active entry state"
        assert {key: freeze(inner.read(key)) for key in parameters(name)} == {
            key: freeze(value) for key, value in parameters(name).items()
        }, "parameter precedence"
        assert original(body, inner) is None
        assert freeze(inner) == frozen["pending"], "active completed state"

    with monkeypatch.context() as spy:
        spy.setattr(stmt, "execute", observe)
        assert stmt.run_action_call(action_call(name), outer) is None
    assert len(observed) == 1, "actual table-action execution hook"
    assert freeze(outer) == frozen["after"], "normal returned state"
    inner = observed[0]
    assert inner is not outer and inner.vars is outer.vars, "shared block store"
    assert inner.action_vars is not outer.action_vars and outer.action_vars is None
    assert outer.read("dstAddr") == Bits(48, 99) and outer.read("port") == Bits(9, 77)
    # Post-observation writes exercise the actual action-hit write branch.
    # They must not overwrite the same-named operational block decoys.
    inner.write("port", Bits(9, 1))
    assert freeze(inner) == expected_first_write, "first parameter write damaged active state"
    assert freeze(outer) == frozen["after"], "first parameter write leaked into block state"
    inner.write("dstAddr", Bits(48, 23))
    assert freeze(inner) == expected_second_write, "second parameter write damaged active state"
    assert freeze(outer) == frozen["after"], "parameter writes leaked into the block layer"


@pytest.fixture(scope="module")
def checked() -> apb.BlockAssembly:
    program = build()
    assert_program_identity(program)
    return program
