"""Reusable forwarder tables fixtures and independent expectations."""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.interp.tables import InstalledEntries, Match
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.corpus.forwarder.forwarder import build
from tests.support.forwarder import assert_program_identity, freeze

ROOT = Path(__file__).resolve().parents[2]


REF = ("MyIngress", "ipv4_lpm")


SHAPES = {
    "empty": [],
    "network": ["network"],
    "host": ["host"],
    "network-host": ["network", "host"],
    "host-network": ["host", "network"],
}


PROFILES = {
    f"{shape}/{mode}/{str(high).lower()}": (shape, mode, high)
    for shape, mode, high in itertools.product(SHAPES, ["drop", "noop", "forward"], [False, True])
}


ADDRESSES = [
    0,
    0x0A0001FF,
    0x0A000200,
    0x0A000201,
    0x0A000202,
    0x0A000203,
    0x0A0002FF,
    0x0A000300,
    0xFFFFFFFF,
]


NETWORK_ANSWERS = {0x0A000200, 0x0A000201, 0x0A000202, 0x0A000203, 0x0A0002FF}


def call(which: str, high: bool = False) -> pb.ActionCall:
    if which in {"drop", "noop"}:
        return pb.ActionCall(action={"drop": "drop", "noop": "NoAction"}[which])
    mac, port = {
        ("network", False): (0x222222222222, 2),
        ("network", True): (0xFFFFFFFFFFFF, 511),
        ("host", False): (0x333333333333, 3),
        ("host", True): (0xFFFFFFFFFFFE, 510),
        ("forward", False): (0x444444444444, 1),
        ("forward", True): (0, 0),
    }[which, high]
    return pb.ActionCall(
        action="ipv4_forward",
        args=[
            pb.Literal(bits=pb.BitsLiteral(width=48, value=str(mac))),
            pb.Literal(bits=pb.BitsLiteral(width=9, value=str(port))),
        ],
    )


def entry(which: str, high: bool = False) -> pb.Entry:
    value, prefix = {"network": (0x0A000200, 24), "host": (0x0A000202, 32)}[which]
    return pb.Entry(
        keys=[pb.KeyValue(lpm=pb.LpmValue(value=str(value), prefix_len=prefix))],
        action=call(which, high),
    )


def inputs(name: str) -> pb.Entries:
    shape, mode, high = PROFILES[name]
    table = pb.TableEntries(
        block=REF[0], table=REF[1], entries=[entry(which, high) for which in SHAPES[shape]]
    )
    if mode != "drop":
        table.default_action.CopyFrom(call(mode, high))
    return pb.Entries(tables=[table])


def expected(name: str, address: int) -> Match:
    shape, mode, high = PROFILES[name]
    if "host" in SHAPES[shape] and address == 0x0A000202:
        return Match(call("host", high), True)
    if "network" in SHAPES[shape] and address in NETWORK_ANSWERS:
        return Match(call("network", high), True)
    return Match(call(mode, high), False)


def observe(program: apb.BlockAssembly, name: str) -> None:
    index = BoundIndex.build(program)
    original_index = freeze(index)
    installed = InstalledEntries.build(index, inputs(name))
    assert freeze(index) == original_index, "installer changed source index"
    shape, mode, high = PROFILES[name]
    independent = InstalledEntries(
        index, {REF: [entry(w, high) for w in SHAPES[shape]]}, {REF: call(mode, high)}
    )
    assert freeze(installed) == freeze(independent), "whole installed state"
    frozen = freeze(installed)
    for address in ADDRESSES:
        keys = [Bits(32, address)]
        frozen_keys = freeze(keys)
        result = installed.lookup(REF, keys)
        assert freeze(installed) == frozen, "lookup changed installed state"
        assert freeze(keys) == frozen_keys, "lookup changed query"
        assert freeze(result) == freeze(expected(name, address)), "independent selection"
    installed.set_default(REF, None)
    independent.default_actions[REF] = call("drop")
    assert freeze(installed) == freeze(independent), "restored declaration default"


def packet_case() -> Case:
    return Case(
        inputs("network-host/drop/false"),
        0,
        bytes.fromhex(
            "00000000010100000000000108004500001a00010000001100000a0001010a000202deadbeefcafe"
        ),
    )


def packet_expected(host: bool = True) -> list[tuple[int, bytes]]:
    return [
        (
            3 if host else 2,
            bytes.fromhex(
                ("333333333333" if host else "222222222222")
                + "00000000010108004500001a00010000ff11a4cf0a0001010a000202deadbeefcafe"
            ),
        )
    ]


@pytest.fixture(scope="module")
def validated() -> apb.BlockAssembly:
    program = build()
    assert_program_identity(program)
    return program
