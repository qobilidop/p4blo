"""Independent packets, CRC arithmetic and complete pinhole-state expectations."""

import struct
from pathlib import Path

from examples.firewall.program import build
from p4blo import ir, stf
from p4blo.drt.case import Case
from p4blo.drt.run import Outcome
from p4blo.drt.state import Observation
from p4blo.v0 import p4blo_pb2 as pb
from tests.examples.packets import ipv4_frame
from tests.examples.support import check_lean, check_python

type Flow = tuple[int, int, int, int]
FLOW: Flow = (0x0A000001, 0xC0000201, 40000, 443)
POLICY = "add services meta.server:0xc0000200/24 meta.server_port:443 allow()"


def crc16(data: bytes) -> int:
    """CRC-16/ARC, reflected polynomial, initial value zero; no lookup table."""
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value


def record(flow: Flow) -> tuple[int, int]:
    encoded = struct.pack("!IIHH", *flow)
    return crc16(encoded) % 16, (1 << 96) + int.from_bytes(encoded, "big")


def packet(
    flow: Flow = FLOW,
    *,
    inbound: bool = False,
    flags: int = 2,
    offset: int = 5,
    version_ihl: int = 0x45,
    flags_fragment: int = 0x4000,
    total_length: int | None = None,
    protocol: int = 6,
    payload: bytes = b"",
    ttl: int = 64,
) -> bytes:
    client, server, client_port, server_port = flow
    source, dest = (server, client) if inbound else (client, server)
    sport, dport = (server_port, client_port) if inbound else (client_port, server_port)
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, offset << 4, flags, 8192, 0, 0)
    return ipv4_frame(
        src=source,
        dst=dest,
        protocol=protocol,
        payload=tcp + payload,
        version_ihl=version_ihl,
        flags_fragment=flags_fragment,
        total_length=total_length,
        ttl=ttl,
    )


def policy(text: str = POLICY) -> pb.Entries:
    return stf.to_entries(ir.Index.build(build()), stf.parse(text))


def sequence() -> tuple[list[Case], list[Outcome]]:
    cases: list[Case] = []
    answers: list[Outcome] = []
    cells = [0] * 16
    permitted = policy()

    def add(
        data: bytes,
        ingress: int = 1,
        *,
        passed: bool = False,
        opened: Flow | None = None,
        entries: pb.Entries | None = None,
    ) -> None:
        if opened is not None:
            slot, value = record(opened)
            assert cells[slot] in (0, value), "expected record must not evict another flow"
            cells[slot] = value
        cases.append(Case(permitted if entries is None else entries, ingress, data))
        answers.append(
            Outcome(
                outputs=((3 - ingress, data),) if passed else (),
                state=(
                    Observation("checksum", "checksum16"),
                    Observation("flow_hash", "crc16"),
                    Observation("flows", "register", 97, tuple(cells)),
                ),
            )
        )

    # No packet except an inside SYN without ACK/FIN/RST creates state.
    add(packet(inbound=True, flags=0x12), 2)
    add(packet(inbound=True), 2)
    for flags in range(256):
        if flags & 0x17 != 2:
            add(packet(flags=flags))
    add(packet(), entries=pb.Entries())
    add(packet(), 0)
    add(packet(), 3)
    add(packet(), passed=True, opened=FLOW)
    add(packet(inbound=True, flags=0x12), 2, passed=True)
    # Once open, even FIN/RST are admitted without deleting the record.
    for flags in range(256):
        add(packet(flags=flags), passed=True)
        add(packet(inbound=True, flags=flags), 2, passed=True)

    # Removing policy closes access immediately, retaining the exact record.
    add(packet(), entries=pb.Entries())
    add(packet(inbound=True, flags=0x10), 2, entries=pb.Entries())
    add(packet(inbound=True, flags=0x10), 2, passed=True)
    denied = policy(POLICY + "\nadd services meta.server:0xc0000201/32 meta.server_port:443 deny()")
    add(packet(), entries=denied)
    add(packet(inbound=True), 2, entries=denied)
    add(packet(), passed=True)

    # Changing any tuple component cannot borrow the existing permission.
    for flow in (
        (FLOW[0] + 1, FLOW[1], FLOW[2], FLOW[3]),
        (FLOW[0], FLOW[1] + 1, FLOW[2], FLOW[3]),
        (FLOW[0], FLOW[1], FLOW[2] + 1, FLOW[3]),
        (FLOW[0], FLOW[1], FLOW[2], FLOW[3] + 1),
    ):
        add(packet(flow, flags=0x10))
        add(packet(flow, inbound=True, flags=0x10), 2)
    add(packet((FLOW[0], 0xC0000301, FLOW[2], 443)))
    add(packet((FLOW[0], FLOW[1], FLOW[2], 80)))

    # Every truncated fixed header is rejected, with all existing state intact.
    for length in range(54):
        add(packet()[:length])
    for version in (0x44, 0x46, 0x65):
        add(packet(version_ihl=version))
    for fragment in (0x2000, 0x8000, 1, 0x4001):
        add(packet(flags_fragment=fragment))
    for offset in (0, 4, 6, 15):
        add(packet(offset=offset))
    for length in (0, 20, 39):
        add(packet(total_length=length))
    add(packet(protocol=17))
    data = packet()
    add(data[:24] + bytes([data[24] ^ 1]) + data[25:])
    add(data[:12] + b"\x81\x00" + data[14:])
    add(data, 0)
    add(data, 3)
    for ttl in (0, 1, 255):
        add(packet(ttl=ttl), passed=True)
    # Payload length and TCP checksum are deliberately outside validation.
    add(packet(total_length=999, payload=b"payload"), passed=True)
    add(packet(payload=bytes(range(256))), passed=True)
    add(data[:50] + b"\x12\x34" + data[52:], passed=True)

    # A colliding tuple is rejected even with fifteen other slots free.
    resident_slot, _ = record(FLOW)
    collision = next(
        (FLOW[0], FLOW[1], port, 443)
        for port in range(40001, 65536)
        if record((FLOW[0], FLOW[1], port, 443))[0] == resident_slot
    )
    add(packet(collision))
    add(packet(collision, inbound=True), 2)
    add(packet(inbound=True), 2, passed=True)
    # An all-zero tuple still needs the occupancy bit; zero is not an open flow.
    zero: Flow = (0, 0, 0, 0)
    zero_policy = policy("add services meta.server:0/0 meta.server_port:0 allow()")
    add(packet(zero, inbound=True), 2, entries=zero_policy)
    add(packet(zero), passed=True, opened=zero, entries=zero_policy)
    add(packet(zero, inbound=True), 2, passed=True, entries=zero_policy)
    # Fill each remaining slot; ECN bits do not prevent a SYN from opening it.
    for slot in range(16):
        if cells[slot]:
            continue
        flow = next(
            (FLOW[0], FLOW[1], port, 443)
            for port in range(1, 65536)
            if record((FLOW[0], FLOW[1], port, 443))[0] == slot
        )
        add(packet(flow, flags=0xC2), passed=True, opened=flow)
        add(packet(flow, inbound=True, flags=0x10), 2, passed=True)
    add(packet(collision))
    add(packet(), passed=True)
    assert all(cells)
    return cases, answers


def test_firewall_independent_packets() -> None:
    cases, expected = sequence()
    check_python(build(), cases, expected)
    # A new load forgets every pinhole: replay the same sequence from zero.
    check_python(build(), cases, expected)


def test_lean_agrees_firewall_independent_packets(lean_binary: Path, tmp_path: Path) -> None:
    cases, expected = sequence()
    check_lean(build(), cases, expected, lean_binary, tmp_path)
    check_lean(build(), cases[:2], expected[:2], lean_binary, tmp_path)


def test_crc_known_answer() -> None:
    assert crc16(b"123456789") == 0xBB3D
