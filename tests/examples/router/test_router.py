"""Independent wire answers for route selection and the router's guarded profile."""

from pathlib import Path

from examples.router.program import build
from p4blo import stf
from p4blo.arch.bindings import BoundIndex
from p4blo.drt.case import Case
from p4blo.drt.run import Outcome
from p4blo.drt.state import Observation
from p4blo.v0 import p4blo_pb2 as pb
from tests.examples.packets import internet_checksum, ipv4_frame
from tests.examples.support import check_lean, check_python

POLICY = (
    "add routes hdr.ipv4.dst:0x0a000000/8 forward(src_mac:0x100, dst_mac:0x101, port:1)\n"
    "add routes hdr.ipv4.dst:0x0a000200/24 forward(src_mac:0x200, dst_mac:0x202, port:2)\n"
)


def policy(text: str = POLICY) -> pb.Entries:
    return stf.to_entries(BoundIndex.build(build()), stf.parse(text))


def sequence() -> tuple[list[Case], list[Outcome]]:
    cases: list[Case] = []
    answers: list[Outcome] = []

    def add(
        packet: bytes,
        answer: bytes | None = None,
        port: int = 2,
        entries: pb.Entries | None = None,
        diagnostic: str | None = None,
    ) -> None:
        cases.append(Case(policy() if entries is None else entries, 0, packet))
        answers.append(
            Outcome(
                outputs=() if answer is None else ((port, answer),),
                diagnostic=diagnostic,
                state=(Observation("checksum", "checksum16"),),
            )
        )

    incoming = ipv4_frame()
    outgoing = ipv4_frame(ttl=63, src_mac=0x200, dst_mac=0x202)
    add(incoming, outgoing)
    add(incoming, outgoing, entries=policy("\n".join(reversed(POLICY.splitlines()))))
    add(
        ipv4_frame(dst=0x0A030001),
        ipv4_frame(dst=0x0A030001, ttl=63, src_mac=0x100, dst_mac=0x101),
        1,
    )
    add(ipv4_frame(dst=0xC0000201))
    add(incoming, entries=pb.Entries())
    for ttl in (0, 1):
        add(ipv4_frame(ttl=ttl))
    for ttl in (2, 255):
        add(ipv4_frame(ttl=ttl), ipv4_frame(ttl=ttl - 1, src_mac=0x200, dst_mac=0x202))
    for flags in (0x2000, 0x8000, 1, 0x4001):
        add(ipv4_frame(flags_fragment=flags))
    for version in (0x44, 0x46, 0x65):
        add(ipv4_frame(version_ihl=version))
    add(ipv4_frame(total_length=19))
    add(incoming[:24] + bytes([incoming[24] ^ 1]) + incoming[25:])
    add(incoming[:12] + b"\x86\xdd" + incoming[14:])
    for size in range(34):
        add(incoming[:size])
    for payload in (b"", bytes(range(256))):
        add(
            ipv4_frame(payload=payload),
            ipv4_frame(payload=payload, ttl=63, src_mac=0x200, dst_mac=0x202),
        )
    # The contract deliberately leaves payload-length reconciliation to the host.
    add(
        ipv4_frame(total_length=999),
        ipv4_frame(total_length=999, ttl=63, src_mac=0x200, dst_mac=0x202),
    )
    for port in (0, 3):
        add(
            incoming,
            ipv4_frame(ttl=63, src_mac=0x100, dst_mac=0x101),
            port,
            policy(
                f"add routes hdr.ipv4.dst:0/0 forward(src_mac:0x100, dst_mac:0x101, port:{port})"
            ),
        )
    add(
        incoming,
        entries=policy("add routes hdr.ipv4.dst:0/0 forward(src_mac:1, dst_mac:2, port:4)"),
        diagnostic="egress_spec 4 is not a configured v1model port",
    )
    add(incoming, entries=policy(POLICY + "add routes hdr.ipv4.dst:0x0a000201/32 deny()"))
    return cases, answers


def test_router_independent_packets() -> None:
    cases, expected = sequence()
    check_python(build(), cases, expected)


def test_lean_agrees_router_independent_packets(lean_binary: Path, tmp_path: Path) -> None:
    cases, expected = sequence()
    check_lean(build(), cases, expected, lean_binary, tmp_path)


def test_checksum_fixture_known_answer() -> None:
    # RFC-style fixed bytes anchor the independently implemented checksum helper.
    header = bytes.fromhex("450000730000400040110000c0a80001c0a800c7")
    assert internet_checksum(header) == 0xB861
