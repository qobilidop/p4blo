"""Reusable firewall fixtures and independent expectations."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from p4blo import stf
from p4blo.arch import validator
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.state import Observation, Snapshot
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracles import firewall as original
from tests.oracles.bmv2 import run as bmv2
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build

CORPUS = Path(__file__).resolve().parents[2] / "tests/programs/corpus/tutorial_firewall"


CONFIGURATION = (
    "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000001/32 ipv4_forward(dstAddr:17, port:1)",
    "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000002/32 ipv4_forward(dstAddr:34, port:2)",
    "add check_ports meta.ingress_port:1 meta.egress_spec:2 set_direction(dir:0)",
    "add check_ports meta.ingress_port:2 meta.egress_spec:1 set_direction(dir:1)",
)


# Independently calculated using reflected polynomial 0xA001 and zlib CRC32,
# then checked against the original BMv2 register arrays, not our interpreter.
# port -> (CRC16 % 4096, CRC32 % 4096) for 10.0.0.1:port -> 10.0.0.2:80 TCP.
INDICES = {12345: (1990, 1987), 12346: (966, 2093), 749: (966, 747), 13602: (780, 2093)}


def checksum(data: bytes) -> bytes:
    """Independent test-only Internet checksum over an even-length header."""
    assert len(data) % 2 == 0
    total = sum(int.from_bytes(data[i : i + 2], "big") for i in range(0, len(data), 2))
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return (total ^ 65535).to_bytes(2, "big")


def packet(
    port: int = 12345,
    *,
    inbound: bool = False,
    flags: int = 0x10,
    seq: int = 1,
    ttl: int = 64,
    protocol: int = 6,
    shape: int = 0x45,
    offset: int = 0x50,
    payload: bytes = b"",
) -> bytes:
    src, dst = (2, 1) if inbound else (1, 2)
    sport, dport = (80, port) if inbound else (port, 80)
    tcp = (
        sport.to_bytes(2, "big")
        + dport.to_bytes(2, "big")
        + seq.to_bytes(4, "big")
        + bytes(4)
        + bytes([offset, flags])
        + bytes.fromhex("200000000000")
    )
    body = tcp + payload
    ip = (
        bytes([shape, 0])
        + (20 + len(body)).to_bytes(2, "big")
        + bytes(4)
        + bytes([ttl, protocol])
        + bytes(2)
        + bytes([10, 0, 0, src, 10, 0, 0, dst])
    )
    ip = ip[:10] + checksum(ip) + ip[12:]
    return bytes.fromhex("0000000000010000000000aa0800") + ip + body


def forwarded(data: bytes, egress: int) -> bytes:
    """Expected routing transformation; never calls p4blo evaluation."""
    result = bytearray(data)
    result[:6] = (17 if egress == 1 else 34).to_bytes(6, "big")
    result[6:12] = data[:6]
    result[22] = (data[22] - 1) % 256
    result[24:26] = bytes(2)
    result[24:26] = checksum(bytes(result[14:34]))
    return bytes(result)


def expected_state(ports: set[int]) -> Snapshot:
    ones = [{INDICES[p][i] for p in ports} for i in range(2)]
    return (
        Observation("bloom_filter_1", "register", 1, tuple(int(i in ones[0]) for i in range(4096))),
        Observation("bloom_filter_2", "register", 1, tuple(int(i in ones[1]) for i in range(4096))),
        Observation("csum", "checksum16"),
        Observation("hash16", "crc16"),
        Observation("hash32", "crc32"),
    )


@dataclass(frozen=True)
class Step:
    case: Case
    outputs: tuple[tuple[int, bytes], ...]
    state: Snapshot


def step(
    data: bytes, ingress: int, egress: int | None, inserted: set[int], *, directions: bool = True
) -> Step:
    rules = CONFIGURATION if directions else CONFIGURATION[:2]
    entries = stf.to_entries(BoundIndex.build(build()), stf.parse("\n".join(rules)))
    outputs = () if egress is None else ((egress, forwarded(data, egress)),)
    return Step(Case(entries, ingress, data), outputs, expected_state(inserted))


def connection() -> list[Step]:
    return [
        step(packet(inbound=True, seq=1), 2, None, set()),
        step(packet(flags=2, seq=2), 1, 2, {12345}),
        step(packet(inbound=True, seq=3), 2, 1, {12345}),
        step(packet(12346, inbound=True, seq=4), 2, None, {12345}),
    ]


def collision(*, reverse: bool = False) -> list[Step]:
    a, b = (13602, 749) if reverse else (749, 13602)
    return [
        step(packet(12346, inbound=True, seq=10), 2, None, set()),
        step(packet(a, flags=2, seq=11), 1, 2, {a}),
        step(packet(12346, inbound=True, seq=12), 2, None, {a}),
        step(packet(b, flags=2, seq=13), 1, 2, {a, b}),
        step(packet(12346, inbound=True, seq=14), 2, 1, {a, b}),
        # FIN is not deletion, and outbound ACK is not insertion.
        step(packet(12346, inbound=True, flags=1, seq=15), 2, 1, {a, b}),
        step(packet(12346, flags=0x10, seq=16), 1, 2, {a, b}),
    ]


def shapes() -> list[Step]:
    return [
        step(packet(flags=0x10, seq=20), 1, 2, set()),
        step(packet(inbound=True, flags=2, seq=21), 2, None, set()),
        step(packet(flags=3, seq=22), 1, 2, {12345}),
        step(packet(inbound=True, flags=4, seq=23), 2, 1, {12345}),
        step(packet(inbound=True, protocol=17, ttl=0, seq=24), 2, 1, {12345}),
        step(packet(shape=0x46, offset=0x60, flags=2, seq=25, payload=b"options?"), 1, 2, {12345}),
        step(packet(12346, inbound=True, seq=26), 2, 1, {12345}, directions=False),
        step(packet(12346, flags=2, seq=27), 1, 2, {12345}, directions=False),
    ]


def bypass() -> list[Step]:
    return [
        step(packet(12346, inbound=True, seq=30), 2, 1, set(), directions=False),
        step(packet(12346, flags=2, seq=31), 1, 2, set(), directions=False),
    ]


def edges() -> list[Step]:
    miss = bytearray(packet(flags=2, seq=40))
    miss[30:34] = bytes([10, 0, 0, 3])
    miss[24:26] = bytes(2)
    miss[24:26] = checksum(bytes(miss[14:34]))
    non_ipv4 = bytearray(packet(seq=41))
    non_ipv4[12:14] = bytes.fromhex("86dd")
    rules = stf.to_entries(BoundIndex.build(build()), stf.parse("\n".join(CONFIGURATION)))
    bad_checksum = bytearray(packet(flags=2, seq=43))
    bad_checksum[24:26] = bytes(2)
    return [
        step(bytes(miss), 1, None, set()),
        Step(Case(rules, 1, bytes(non_ipv4)), ((0, bytes(non_ipv4)),), expected_state(set())),
        step(packet(seq=42)[:43], 1, 2, set()),
        step(bytes(bad_checksum), 1, 2, {12345}),
    ]


def vector(steps: list[Step]) -> str:
    """Fixed-profile STF; packet expectations come from the Step, not execution."""
    lines: list[str] = list(CONFIGURATION)
    for item in steps:
        lines.append(f"packet {item.case.ingress_port} {item.case.packet.hex()}")
        lines.extend(f"expect {port} {data.hex()}$" for port, data in item.outputs)
    return "\n".join(lines) + "\n"


SENTINEL = packet(protocol=17, seq=0x7FFFFFF0, payload=b"p4blo-state-barrier")


SENTINEL_OUTPUT = forwarded(SENTINEL, 2)


def observation_plan(sequence: list[Step], *, directions: bool = True) -> bmv2.Plan:
    """Fresh-switch prefixes observe every boundary, never resetting within one prefix."""
    phases = []
    for length in range(1, len(sequence) + 1):
        prefix = sequence[:length]
        assert all(item.case.packet != SENTINEL for item in prefix)
        assert all(data != SENTINEL_OUTPUT for item in prefix for _, data in item.outputs)
        phases.append(
            bmv2.Phase(
                commands=list(original.COMMANDS if directions else original.COMMANDS[:2]),
                packets=[stf.Packet(0, item.case.ingress_port, item.case.packet) for item in prefix]
                + [stf.Packet(0, 1, SENTINEL)],
                expects=[
                    stf.Expect(0, port, data, bytes([255]) * len(data), True)
                    for item in prefix
                    for port, data in item.outputs
                ]
                + [stf.Expect(0, 2, SENTINEL_OUTPUT, bytes([255]) * len(SENTINEL_OUTPUT), True)],
            )
        )
    return bmv2.Plan(phases, [0, 1, 2], [])


def assert_original_observations(sequence: list[Step], plan: bmv2.Plan, reply: dict) -> None:
    assert len(reply["phases"]) == len(sequence)
    for item, phase in zip(sequence, reply["phases"], strict=True):
        assert phase["error"] is None, phase
        expected = {
            "MyIngress." + obs.name: list(obs.values)
            for obs in item.state
            if obs.kind == "register"
        }
        assert phase["registers"] == expected
    assert bmv2.judge(plan, reply) == ("pass", "")


@pytest.fixture(scope="module")
def original_bmv2() -> tuple[str, bmv2.Compiled]:
    image = bmv2.default_image()
    unavailable = bmv2.unavailable(image)
    if unavailable:
        pytest.skip(unavailable)
    return image, bmv2.compile_program(image, original.source())


class KnownSpecTecTableMaskDisagreement(Exception):
    """Only the pinned route-mask mismatch, not an arbitrary oracle error."""


def walk(statements: Sequence[pb.Stmt]) -> Iterator[pb.Stmt]:
    for statement in statements:
        yield statement
        if statement.WhichOneof("kind") == "conditional":
            yield from walk(statement.conditional.then)
            yield from walk(statement.conditional.otherwise)


MUTATIONS = ["accept-one-filter", "insert-without-syn", "ignore-direction-hit", "unreversed-ports"]


def mutant(name: str) -> tuple[apb.BlockAssembly, list[Step]]:
    program = build()
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    statements = list(walk(ingress.body))
    if name == "accept-one-filter":
        (target,) = [
            s.conditional.condition
            for s in statements
            if s.conditional.condition.binary.op == pb.BINARY_OP_OR
        ]
        target.binary.op = pb.BINARY_OP_AND
        sequence = collision()
    elif name == "insert-without-syn":
        (target,) = [
            s.conditional.condition
            for s in statements
            if s.conditional.condition.binary.left.member.field == "syn"
        ]
        target.CopyFrom(pb.Expr(literal=pb.Literal(boolean=True)))
        sequence = shapes()
    elif name == "ignore-direction-hit":
        (target,) = [
            s.conditional.condition
            for s in statements
            if s.conditional.condition.var == "check_ports_hit"
        ]
        target.CopyFrom(pb.Expr(literal=pb.Literal(boolean=True)))
        sequence = shapes()
    else:
        calls = [s.call_action for s in statements if s.call_action.action == "compute_hashes"]
        assert len(calls) == 2
        for index in [2, 3]:
            calls[1].args[index].CopyFrom(calls[0].args[index])
        sequence = connection()
    assert validator.validate(program) == []
    return program, sequence
