# SPDX-FileCopyrightText: 2019 Stephen Ibanez
# SPDX-License-Identifier: Apache-2.0
"""Typed port of p4lang/tutorials' firewall solution (see README).

The eDSL keeps the original actions and branches visible. The architecture
maps standard metadata to ordinary fields; empty stages disappear and
checksum computation follows ingress. No flow logic lives in an extern.
"""

from __future__ import annotations

from p4blo.arch import assemble
from p4blo.arch import wire as arch_wire
from p4blo.arch.externs.declarations import CRC16, CRC32, Checksum16, Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import (
    Bits,
    BlockLibrary,
    Bool,
    Control,
    Deparser,
    Header,
    L,
    Parser,
    Struct,
    Table,
    Transition,
    action,
    bit1,
    bit8,
    bit9,
    bit16,
    bit32,
    bit48,
    concat,
    exact,
    lpm,
    state,
)


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


class tcp_t(Header):
    srcPort: bit16
    dstPort: bit16
    seqNo: bit32
    ackNo: bit32
    dataOffset: Bits[L[4]]
    res: Bits[L[4]]
    cwr: bit1
    ece: bit1
    urg: bit1
    ack: bit1
    psh: bit1
    rst: bit1
    syn: bit1
    fin: bit1
    window: bit16
    checksum: bit16
    urgentPtr: bit16


class headers(Struct):
    ethernet: ethernet_t
    ipv4: ipv4_t
    tcp: tcp_t


class metadata(Struct):
    ingress_port: bit9
    egress_port: bit9
    drop: Bool


class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        return self.goto(self.parse_ethernet)

    @state
    def parse_ethernet(self) -> Transition:
        self.extract(self.hdr.ethernet)
        return self.select(
            self.hdr.ethernet.etherType, {0x800: self.parse_ipv4}, default=self.accept
        )

    @state
    def parse_ipv4(self) -> Transition:
        self.extract(self.hdr.ipv4)
        return self.select(self.hdr.ipv4.protocol, {6: self.tcp}, default=self.accept)

    @state
    def tcp(self) -> Transition:
        self.extract(self.hdr.tcp)
        return self.accept


bloom_filter_1 = Register[bit1]("bloom_filter_1", size=4096)
bloom_filter_2 = Register[bit1]("bloom_filter_2", size=4096)
hash16 = CRC16[Bits[L[104]]]("hash16")
hash32 = CRC32[Bits[L[104]]]("hash32")
csum = Checksum16[Bits[L[144]]]("csum")


class MyIngress(Control[headers, metadata]):
    reg_pos_one: bit32
    reg_pos_two: bit32
    reg_val_one: bit1
    reg_val_two: bit1
    direction: bit1
    crc16_result: bit16
    check_ports_hit: Bool

    @action
    def NoAction(self) -> None:
        pass

    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)
        self.assign(self.meta.egress_port, 511)

    @action
    def compute_hashes(self, ipAddr1: bit32, ipAddr2: bit32, port1: bit16, port2: bit16) -> None:
        data = concat(ipAddr1, ipAddr2, port1, port2, self.hdr.ipv4.protocol).as_(Bits[L[104]])
        self.assign(self.crc16_result, hash16.compute(data))
        self.assign(self.reg_pos_one, (self.crc16_result & 4095).cast(bit32))
        self.assign(self.reg_pos_two, hash32.compute(data))
        self.assign(self.reg_pos_two, self.reg_pos_two & 4095)

    @action
    def ipv4_forward(self, dstAddr: bit48, port: bit9) -> None:
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ethernet.srcAddr, self.hdr.ethernet.dstAddr)
        self.assign(self.hdr.ethernet.dstAddr, dstAddr)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)

    ipv4_lpm = Table(
        keys=(lpm(headers.ipv4.dstAddr),),
        actions=[ipv4_forward, drop, NoAction],
        default=drop(),
        size=1024,
    )

    @action
    def set_direction(self, dir: bit1) -> None:
        self.assign(self.direction, dir)

    check_ports = Table(
        keys=(exact(metadata.ingress_port), exact(metadata.egress_port)),
        actions=[set_direction, NoAction],
        default=NoAction(),
        size=1024,
    )

    def apply(self) -> None:
        ip, tcp = self.hdr.ipv4, self.hdr.tcp
        with self.if_(ip.is_valid()):
            self.apply_table(self.ipv4_lpm)
            with self.if_(tcp.is_valid()):
                self.assign(self.direction, 0)
                self.apply_table(self.check_ports, hit=self.check_ports_hit)
                with self.if_(self.check_ports_hit):
                    with self.if_(self.direction == 0):
                        self.compute_hashes(ip.srcAddr, ip.dstAddr, tcp.srcPort, tcp.dstPort)
                    with self.else_():
                        self.compute_hashes(ip.dstAddr, ip.srcAddr, tcp.dstPort, tcp.srcPort)
                    with self.if_(self.direction == 0):
                        with self.if_(tcp.syn == 1):
                            bloom_filter_1.write(self.reg_pos_one, 1)
                            bloom_filter_2.write(self.reg_pos_two, 1)
                    with self.elif_(self.direction == 1):
                        bloom_filter_1.read(self.reg_val_one, self.reg_pos_one)
                        bloom_filter_2.read(self.reg_val_two, self.reg_pos_two)
                        with self.if_((self.reg_val_one != 1) | (self.reg_val_two != 1)):
                            self.drop()
        with self.if_(ip.is_valid()):
            data = concat(
                ip.version,
                ip.ihl,
                ip.diffserv,
                ip.totalLen,
                ip.identification,
                ip.flags,
                ip.fragOffset,
                ip.ttl,
                ip.protocol,
                ip.srcAddr,
                ip.dstAddr,
            ).as_(Bits[L[144]])
            self.assign(ip.hdrChecksum, csum.compute(data))


class MyDeparser(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.ipv4)
        self.emit(self.hdr.tcp)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(
            MyParser,
            MyIngress,
            MyDeparser,
            externs=[bloom_filter_1, bloom_filter_2, hash16, hash32, csum],
        ),
        name="tutorial_firewall",
        headers=headers,
        metadata=metadata,
        exports={"parser": MyParser, "control": MyIngress, "deparser": MyDeparser},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
