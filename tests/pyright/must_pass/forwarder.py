"""The forwarder, as docs/notes/edsl-v2-design.md writes it.

Must type-check with zero errors: every width, field, state, action and
table reference is resolved statically.
"""

from __future__ import annotations

from enum import IntEnum

from p4blo.edsl import (
    Bits,
    Bool,
    Control,
    Deparser,
    Header,
    L,
    Parser,
    Program,
    Struct,
    Table,
    Transition,
    action,
    bit8,
    bit9,
    bit16,
    bit32,
    bit48,
    concat,
    lpm,
    state,
)
from p4blo.edsl.externs import Checksum16


class ethernet_t(Header):
    dstAddr: bit48
    srcAddr: bit48
    etherType: bit16


class ipv4_t(Header):
    version: Bits[L[4]]
    ihl: Bits[L[4]]
    diffserv: bit8
    totalLen: bit16
    identification: bit16
    flags: Bits[L[3]]
    fragOffset: Bits[L[13]]
    ttl: bit8
    protocol: bit8
    hdrChecksum: bit16
    srcAddr: bit32
    dstAddr: bit32


class headers(Struct):
    ethernet: ethernet_t
    ipv4: ipv4_t


class metadata(Struct):
    ingress_port: bit9
    egress_port: bit9
    drop: Bool


class EtherType(IntEnum):
    IPV4 = 0x800


class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        return self.goto(self.parse_ethernet)

    @state
    def parse_ethernet(self) -> Transition:
        self.extract(self.hdr.ethernet)
        return self.select(
            self.hdr.ethernet.etherType, {EtherType.IPV4: self.parse_ipv4}, default=self.accept
        )

    @state
    def parse_ipv4(self) -> Transition:
        self.extract(self.hdr.ipv4)
        return self.accept


csum = Checksum16[Bits[L[144]]]("csum")


class MyIngress(Control[headers, metadata]):
    @action
    def NoAction(self) -> None:
        pass

    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)

    @action
    def ipv4_forward(self, dstAddr: bit48, port: bit9) -> None:
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ethernet.srcAddr, self.hdr.ethernet.dstAddr)
        self.assign(self.hdr.ethernet.dstAddr, dstAddr)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)

    ipv4_lpm = Table(
        keys=[lpm(headers.ipv4.dstAddr)],
        actions=[ipv4_forward, drop, NoAction],
        default=drop(),
        size=1024,
    )

    def apply(self) -> None:
        with self.if_(self.hdr.ipv4.is_valid()):
            self.apply_table(self.ipv4_lpm)
        with self.if_(self.hdr.ipv4.is_valid()):
            ipv4 = self.hdr.ipv4
            data = concat(
                ipv4.version,
                ipv4.ihl,
                ipv4.diffserv,
                ipv4.totalLen,
                ipv4.identification,
                ipv4.flags,
                ipv4.fragOffset,
                ipv4.ttl,
                ipv4.protocol,
                ipv4.srcAddr,
                ipv4.dstAddr,
            )
            self.assign(ipv4.hdrChecksum, csum.compute(data.as_(Bits[L[144]])))


class MyDeparser(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.ipv4)


program = Program(
    "forwarder",
    headers=headers,
    metadata=metadata,
    parser=MyParser,
    control=MyIngress,
    deparser=MyDeparser,
    externs=[csum],
)
