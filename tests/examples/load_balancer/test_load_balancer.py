"""Independent exact wire answers, CRC buckets and configuration boundaries."""

from pathlib import Path
from struct import pack

from examples.load_balancer.program import build
from p4blo import stf
from p4blo.arch.bindings import BoundIndex
from p4blo.drt.case import Case
from p4blo.drt.run import Outcome
from p4blo.drt.state import Observation
from p4blo.v0 import p4blo_pb2 as pb
from tests.examples.packets import ipv4_frame
from tests.examples.support import check_lean, check_python

VIP = 0x0A000064
CLIENT = 0xC0000201
SERVICE = "add services hdr.ipv4.dst:0x0a000064 hdr.udp.dst_port:8080 select_group(group:1)"
BUCKETS = "\n".join(
    f"add backends meta.group:1 meta.bucket:{bucket} "
    f"deliver(src_mac:0x{port}00, dst_mac:0x{port}0{port}, port:{port})"
    for bucket, port in enumerate((1, 1, 2, 2))
)
POLICY = SERVICE + "\n" + BUCKETS


def crc16(data: bytes) -> int:
    """Bitwise CRC-16/ARC reference: reflected 0x8005, initial/final zero."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def bucket(src: int, dst: int, sport: int, dport: int) -> int:
    return crc16(pack("!IIHH", src, dst, sport, dport)) & 3


def frame(
    *,
    sport: int = 10000,
    dport: int = 8080,
    payload: bytes = b"ping",
    udp_length: int | None = None,
    udp_checksum: int = 0,
    src: int = CLIENT,
    dst: int = VIP,
    ttl: int = 64,
    flags_fragment: int = 0x4000,
    version_ihl: int = 0x45,
    protocol: int = 17,
    total_length: int | None = None,
    src_mac: int = 1,
    dst_mac: int = 2,
) -> bytes:
    udp = pack(
        "!HHHH", sport, dport, 8 + len(payload) if udp_length is None else udp_length, udp_checksum
    )
    return ipv4_frame(
        src=src,
        dst=dst,
        ttl=ttl,
        protocol=protocol,
        payload=udp + payload,
        flags_fragment=flags_fragment,
        version_ihl=version_ihl,
        total_length=total_length,
        src_mac=src_mac,
        dst_mac=dst_mac,
    )


def policy(text: str = POLICY) -> pb.Entries:
    return stf.to_entries(BoundIndex.build(build()), stf.parse(text))


def sequence() -> tuple[list[Case], list[Outcome]]:
    cases: list[Case] = []
    answers: list[Outcome] = []

    def add(
        packet: bytes,
        answer: bytes | None = None,
        port: int = 1,
        entries: pb.Entries | None = None,
        diagnostic: str | None = None,
    ) -> None:
        cases.append(Case(policy() if entries is None else entries, 0, packet))
        answers.append(
            Outcome(
                outputs=() if answer is None else ((port, answer),),
                diagnostic=diagnostic,
                state=(Observation("checksum", "checksum16"), Observation("flow_hash", "crc16")),
            )
        )

    # Four known flow tuples cover every bucket, including both backends.
    ports = (10001, 10000, 10241, 10240)
    assert [bucket(CLIENT, VIP, sport, 8080) for sport in ports] == [0, 1, 2, 3]
    for sport in ports:
        port = 1 if bucket(CLIENT, VIP, sport, 8080) < 2 else 2
        for payload in (b"", b"ping", b"different application data", bytes(range(256))):
            add(
                frame(sport=sport, payload=payload),
                frame(
                    sport=sport, payload=payload, ttl=63, src_mac=port * 0x100, dst_mac=port * 0x101
                ),
                port,
            )
    # Vary every hash component and both port-width boundaries independently.
    for src, dst, sport, dport in (
        (CLIENT + 1, VIP, 10000, 8080),
        (CLIENT + 256, VIP, 10000, 8080),
        (CLIENT, VIP + 1, 10000, 8080),
        (CLIENT, VIP + 256, 10000, 8080),
        (CLIENT, VIP, 0, 8080),
        (CLIENT, VIP, 65535, 8080),
        (CLIENT, VIP, 10000, 0),
        (CLIENT, VIP, 10000, 65535),
    ):
        port = 1 if bucket(src, dst, sport, dport) < 2 else 2
        configured = policy(
            f"add services hdr.ipv4.dst:{dst} hdr.udp.dst_port:{dport} select_group(group:1)\n"
            + BUCKETS
        )
        add(
            frame(src=src, dst=dst, sport=sport, dport=dport),
            frame(
                src=src,
                dst=dst,
                sport=sport,
                dport=dport,
                ttl=63,
                src_mac=port * 0x100,
                dst_mac=port * 0x101,
            ),
            port,
            configured,
        )
    incoming = frame()
    outgoing = frame(ttl=63, src_mac=0x100, dst_mac=0x101)
    add(incoming, outgoing, entries=policy("\n".join(reversed(POLICY.splitlines()))))
    add(incoming, entries=pb.Entries())
    for group in (0, 255):
        add(incoming, outgoing, entries=policy(POLICY.replace("group:1", f"group:{group}")))
    add(incoming, entries=policy(SERVICE))
    add(incoming, entries=policy(BUCKETS))
    # A service miss must not admit through the default metadata group zero.
    add(incoming, entries=policy(BUCKETS.replace("group:1", "group:0")))
    add(frame(dst=VIP + 1))
    add(frame(dport=8081))
    # Same bucket in a different group must not borrow group 1's backend.
    other_service = SERVICE.replace("group:1", "group:2")
    add(incoming, entries=policy(other_service + "\n" + BUCKETS))
    group2 = "add backends meta.group:2 meta.bucket:1 deliver(src_mac:0x300, dst_mac:0x303, port:3)"
    add(
        incoming,
        frame(ttl=63, src_mac=0x300, dst_mac=0x303),
        3,
        policy(other_service + "\n" + BUCKETS + "\n" + group2),
    )
    # Affinity is conditional on unchanged configuration: remapping moves this flow.
    remapped = POLICY.replace(
        "meta.bucket:1 deliver(src_mac:0x100, dst_mac:0x101, port:1)",
        "meta.bucket:1 deliver(src_mac:0x200, dst_mac:0x202, port:2)",
    )
    add(incoming, frame(ttl=63, src_mac=0x200, dst_mac=0x202), 2, policy(remapped))
    add(incoming, outgoing)
    for ttl in (0, 1):
        add(frame(ttl=ttl))
    for ttl in (2, 255):
        add(frame(ttl=ttl), frame(ttl=ttl - 1, src_mac=0x100, dst_mac=0x101))
    for flags in (0x2000, 0x8000, 1, 0x4001, 0x6000):
        add(frame(flags_fragment=flags))
    add(frame(flags_fragment=0), frame(flags_fragment=0, ttl=63, src_mac=0x100, dst_mac=0x101))
    for version in (0x44, 0x46, 0x65):
        add(frame(version_ihl=version))
    for length in (0, 7):
        add(frame(udp_length=length))
    for length in (0, 20, 27):
        add(frame(total_length=length))
    for protocol in (1, 6, 255):
        add(frame(protocol=protocol))
    add(incoming[:24] + bytes([incoming[24] ^ 1]) + incoming[25:])
    for ether_type in (b"\x81\x00", b"\x86\xdd"):
        add(incoming[:12] + ether_type + incoming[14:])
    for size in range(42):
        add(incoming[:size])
    # Explicitly unsupported validation: envelopes and UDP checksum remain opaque.
    add(
        frame(total_length=65535, udp_length=65535, udp_checksum=0x1234),
        frame(
            total_length=65535,
            udp_length=65535,
            udp_checksum=0x1234,
            ttl=63,
            src_mac=0x100,
            dst_mac=0x101,
        ),
    )
    add(
        frame(total_length=28, udp_length=8),
        frame(total_length=28, udp_length=8, ttl=63, src_mac=0x100, dst_mac=0x101),
    )
    for port in (0, 3, 4, 511):
        configured = policy(
            SERVICE
            + "\n"
            + "add backends meta.group:1 meta.bucket:1 "
            + f"deliver(src_mac:0x100, dst_mac:0x101, port:{port})"
        )
        add(
            incoming,
            outgoing if port < 4 else None,
            port,
            configured,
            None if port < 4 else f"egress_port {port} is not a port of this switch",
        )
    add(incoming, entries=policy(SERVICE + "\nadd backends meta.group:1 meta.bucket:1 deny()"))
    add(
        incoming,
        entries=policy(
            "add services hdr.ipv4.dst:0x0a000064 hdr.udp.dst_port:8080 deny()\n" + BUCKETS
        ),
    )
    return cases, answers


def test_load_balancer_independent_packets() -> None:
    cases, expected = sequence()
    check_python(build(), cases, expected)


def test_lean_agrees_load_balancer_independent_packets(lean_binary: Path, tmp_path: Path) -> None:
    cases, expected = sequence()
    check_lean(build(), cases, expected, lean_binary, tmp_path)


def test_crc16_reference_known_answer() -> None:
    assert crc16(b"123456789") == 0xBB3D
