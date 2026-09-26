"""Reusable forwarder apply fixtures and independent expectations."""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path

import pytest

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.tables import InstalledEntries, Match, TableRef
from p4blo.interp.values import Bits, Header, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.corpus.forwarder.forwarder import build
from tests.programs.ir_helpers import target
from tests.support.forwarder import assert_program_identity, freeze
from tests.support.forwarder_actions import environment as action_environment
from tests.support.forwarder_actions import selected_action
from tests.support.forwarder_tables import (
    ADDRESSES,
    REF,
    SHAPES,
    call,
    entry,
    expected,
    inputs,
    packet_case,
)
from tests.support.forwarder_tables import PROFILES as ROUTES

ROOT = Path(__file__).resolve().parents[2]


STATES = list(itertools.product([False, True], [False, True], [False, True], [0, 1, 255]))


CASES = {
    f"{route}/{address}/{ordinal % 24}": (route, address, STATES[ordinal % 24])
    for ordinal, (route, address) in enumerate(itertools.product(ROUTES, ADDRESSES))
}


KEY = pb.Expr(
    member=pb.Member(
        base=pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field="ipv4")), field="dstAddr"
    )
)


def evaluator() -> Callable[[pb.Expr, Env], Value]:
    # Observe the actual binding used by apply/execute, including live faults;
    # importing expr.evaluate directly would bypass a replaced stmt binding.
    return stmt.evaluate  # pyright: ignore[reportPrivateImportUsage]


def writer() -> Callable[[pb.LValue, Value, Env], None]:
    return stmt.write_lvalue  # pyright: ignore[reportPrivateImportUsage]


def action(name: str) -> pb.ActionCall:
    route, address, _ = CASES[name]
    result = expected(route, address)
    assert result.action is not None
    return result.action


def environment(program: apb.BlockAssembly, name: str, *, actual_entries: bool) -> Env:
    route, address, state = CASES[name]
    state_name = "-".join(str(v).lower() for v in (*state, False))
    env = action_environment(program, state_name)
    header = env.vars["hdr"]
    assert isinstance(header, Struct) and isinstance(header.fields[1], Header)
    header.fields[1].fields[11] = Bits(32, address)
    if actual_entries:
        env.entries = InstalledEntries.build(env.index, inputs(route))
    else:
        shape, mode, high = ROUTES[route]
        env.entries = InstalledEntries(
            env.index,
            {REF: [entry(which, high) for which in SHAPES[shape]]},
            {REF: call(mode, high)},
        )
    return env


def expected_runs(program: apb.BlockAssembly, name: str) -> dict[str, Env]:
    before = environment(program, name, actual_entries=False)
    after = environment(program, name, actual_entries=False)
    selected = action(name)
    params: dict[str, Value] = {}
    meta = after.vars["meta"]
    header = after.vars["hdr"]
    assert isinstance(meta, Struct) and isinstance(header, Struct)
    ether, ipv4 = header.fields
    assert isinstance(ether, Header) and isinstance(ipv4, Header)
    if selected.action == "ipv4_forward":
        dst, port = (int(arg.bits.value) for arg in selected.args)
        params = {"dstAddr": Bits(48, dst), "port": Bits(9, port)}
        # Complete initial fields come from independent literal constructors;
        # these literal answers do not use the runtime field helpers.
        ether.fields[0] = Bits(48, dst)
        ether.fields[1] = Bits(48, 0x010203040506)
        ttl = CASES[name][2][3]
        ipv4.fields[7] = Bits(8, {0: 255, 1: 0, 255: 254}[ttl])
        meta.fields[1] = Bits(9, port)
    elif selected.action == "drop":
        meta.fields[1] = Bits(9, 511)
    else:
        assert selected.action == "NoAction"
    return {
        "before": before,
        "entered": replace(before, action=selected.action, action_vars=params),
        "activeEnd": replace(after, action=selected.action, action_vars=dict(params)),
        "after": after,
    }


def body(program: apb.BlockAssembly, name: str) -> list[pb.Stmt]:
    wanted = action(name).action
    declarations = next(block for block in program.blocks if block.name == "MyIngress")
    actual = next(a for a in declarations.actions if a.name == wanted)
    if wanted == "ipv4_forward":
        assert actual == selected_action(program)
    elif wanted == "drop":
        assert actual == pb.Action(
            name="drop",
            body=[
                pb.Stmt(
                    assign=pb.Assign(
                        target=target("meta", "egress_spec"),
                        value=pb.Expr(
                            literal=pb.Literal(bits=pb.BitsLiteral(width=9, value="511"))
                        ),
                    )
                )
            ],
        )
    else:
        assert actual == pb.Action(name="NoAction")
    return list(actual.body)


def observe(program: apb.BlockAssembly, name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    outer = environment(program, name, actual_entries=True)
    frozen = {phase: freeze(env) for phase, env in expected_runs(program, name).items()}
    assert freeze(outer) == frozen["before"], "actual installer/initial state"
    route, address, _ = CASES[name]
    evaluate, lookup, run_action, execute = (
        evaluator(),
        InstalledEntries.lookup,
        stmt.run_action_call,
        stmt.execute,
    )
    counts = {"key": 0, "lookup": 0, "call": 0, "body": 0}
    retained: list[Env] = []

    def read_key(value: pb.Expr, env: Env) -> Value:
        if env is not outer or value != KEY:
            return evaluate(value, env)
        counts["key"] += 1
        assert freeze(env) == frozen["before"], "pre-key state"
        result = evaluate(value, env)
        assert freeze(result) == freeze(Bits(32, address)), "independent key answer"
        assert freeze(env) == frozen["before"], "key read changed state"
        return result

    def find(self: InstalledEntries, ref: TableRef, keys: list[Bits]) -> Match:
        counts["lookup"] += 1
        assert self is outer.entries and ref == REF
        assert freeze(keys) == freeze([Bits(32, address)]), "lookup key identity"
        result = lookup(self, ref, keys)
        assert freeze(keys) == freeze([Bits(32, address)]), "lookup changed key"
        assert freeze(result) == freeze(expected(route, address)), "independent selected match"
        assert freeze(outer) == frozen["before"], "lookup changed complete state"
        return result

    def selected(selected_call: pb.ActionCall, env: Env) -> None:
        counts["call"] += 1
        assert env is outer and selected_call == action(name), "actual selected call"
        assert freeze(env) == frozen["before"], "pre-action state"
        assert run_action(selected_call, env) is None
        assert freeze(env) == frozen["after"], "post-action state"

    def action_body(statements: Iterable[pb.Stmt], inner: Env) -> None:
        counts["body"] += 1
        retained.append(inner)
        assert list(statements) == body(program, name), "actual action body"
        assert freeze(inner) == frozen["entered"], "active entry state"
        assert execute(statements, inner) is None
        assert freeze(inner) == frozen["activeEnd"], "active completed state"

    with monkeypatch.context() as hooks:
        hooks.setattr(stmt, "evaluate", read_key)
        hooks.setattr(InstalledEntries, "lookup", find)
        hooks.setattr(stmt, "run_action_call", selected)
        hooks.setattr(stmt, "execute", action_body)
        assert stmt.apply(pb.Apply(table="ipv4_lpm"), outer) is None
    assert counts == {"key": 1, "lookup": 1, "call": 1, "body": 1}, "actual operation counts"
    assert freeze(outer) == frozen["after"], "normal application result"
    assert retained[0] is not outer and retained[0].vars is outer.vars
    assert outer.action is None and outer.action_vars is None


def profile(route: str, address: int) -> str:
    return next(name for name, (r, q, _) in CASES.items() if r == route and q == address)


PACKET_PROFILES = [
    "network-host/drop/false",
    "host-network/drop/false",
    "empty/drop/false",
    "empty/noop/false",
    "empty/forward/false",
]


def application_packet(name: str) -> Case:
    return replace(packet_case(), entries=inputs(name))


def application_output(name: str) -> list[tuple[int, bytes]]:
    """Literal whole-packet anchors; checksum execution is tested, not proved here."""
    if name == "empty/drop/false":
        return []
    if name == "empty/noop/false":
        return [
            (
                0,
                bytes.fromhex(
                    "00000000010100000000000108004500001a000100000011a3d00a0001010a000202deadbeefcafe"
                ),
            )
        ]
    port, destination = (
        (1, "444444444444") if name == "empty/forward/false" else (3, "333333333333")
    )
    return [
        (
            port,
            bytes.fromhex(
                destination + "00000000010108004500001a00010000ff11a4cf0a0001010a000202deadbeefcafe"
            ),
        )
    ]


@pytest.fixture(scope="module")
def checked() -> apb.BlockAssembly:
    program = build()
    assert_program_identity(program)
    return program
