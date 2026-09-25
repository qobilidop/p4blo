"""A UDP service dispatcher: select a service, hash a flow, select a backend."""

from __future__ import annotations

from p4blo import edsl as p4
from p4blo.arch import reference
from p4blo.arch.externs.declarations import CRC16, Checksum16
from p4blo.v0 import p4blo_pb2 as pb

ChecksumWords = p4.Bits[p4.L[144]]
FlowTuple = p4.Bits[p4.L[96]]


class Ethernet(p4.Header):
    dst: p4.bit48
    src: p4.bit48
    ether_type: p4.bit16


class IPv4(p4.Header):
    version: p4.bit4
    ihl: p4.bit4
    dscp_ecn: p4.bit8
    total_length: p4.bit16
    identification: p4.bit16
    flags: p4.bit3
    fragment_offset: p4.bit13
    ttl: p4.bit8
    protocol: p4.bit8
    checksum: p4.bit16
    src: p4.bit32
    dst: p4.bit32


class UDP(p4.Header):
    src_port: p4.bit16
    dst_port: p4.bit16
    length: p4.bit16
    checksum: p4.bit16


class Headers(p4.Struct):
    ethernet: Ethernet
    ipv4: IPv4
    udp: UDP


class Metadata(p4.Struct):
    ingress_port: p4.bit9
    egress_port: p4.bit9
    drop: p4.Bool
    expected_checksum: p4.bit16
    group: p4.bit8
    service_found: p4.Bool
    flow_hash: p4.bit16
    bucket: p4.bit2


class Parse(p4.Parser[Headers, Metadata]):
    @p4.state(start=True)
    def start(self) -> p4.Transition:
        self.extract(self.hdr.ethernet)
        return self.select(self.hdr.ethernet.ether_type, {0x0800: self.ipv4}, default=self.accept)

    @p4.state
    def ipv4(self) -> p4.Transition:
        self.extract(self.hdr.ipv4)
        return self.select(self.hdr.ipv4.protocol, {17: self.udp}, default=self.accept)

    @p4.state
    def udp(self) -> p4.Transition:
        self.extract(self.hdr.udp)
        return self.accept


def checksum_data(ip: IPv4) -> ChecksumWords:
    """IPv4 header words with the checksum word omitted (equivalent to zero)."""
    return p4.concat(
        ip.version,
        ip.ihl,
        ip.dscp_ecn,
        ip.total_length,
        ip.identification,
        ip.flags,
        ip.fragment_offset,
        ip.ttl,
        ip.protocol,
        ip.src,
        ip.dst,
    ).as_(ChecksumWords)


def flow_key(ip: IPv4, udp: UDP) -> FlowTuple:
    """Build the network-order tuple expression; payload is not part of affinity."""
    return p4.concat(ip.src, ip.dst, udp.src_port, udp.dst_port).as_(FlowTuple)


checksum = Checksum16[ChecksumWords]("checksum")
flow_hash = CRC16[FlowTuple]("flow_hash")


class Balance(p4.Control[Headers, Metadata]):
    @p4.action
    def deny(self) -> None:
        self.assign(self.meta.drop, True)

    @p4.action
    def select_group(self, group: p4.bit8) -> None:
        self.assign(self.meta.group, group)
        self.assign(self.meta.service_found, True)

    @p4.action
    def deliver(self, src_mac: p4.bit48, dst_mac: p4.bit48, port: p4.bit9) -> None:
        self.assign(self.hdr.ethernet.src, src_mac)
        self.assign(self.hdr.ethernet.dst, dst_mac)
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)
        self.assign(self.hdr.ipv4.checksum, checksum.compute(checksum_data(self.hdr.ipv4)))
        self.assign(self.meta.drop, False)

    services = p4.Table(
        keys=(p4.exact(Headers.ipv4.dst), p4.exact(Headers.udp.dst_port)),
        actions=[select_group, deny],
        default=deny(),
        size=256,
    )
    backends = p4.Table(
        keys=(p4.exact(Metadata.group), p4.exact(Metadata.bucket)),
        actions=[deliver, deny],
        default=deny(),
        size=1024,
    )

    def apply(self) -> None:
        self.assign(self.meta.drop, True)
        self.assign(self.meta.service_found, False)
        ip, udp = self.hdr.ipv4, self.hdr.udp
        supported_packet = (
            ip.is_valid()
            & udp.is_valid()
            & (ip.version == 4)
            & (ip.ihl == 5)
            & (ip.total_length >= 28)
            & (ip.ttl > 1)
            & ((ip.flags & 5) == 0)
            & (ip.fragment_offset == 0)
            & (udp.length >= 8)
        )
        with self.if_(supported_packet):
            self.assign(self.meta.expected_checksum, checksum.compute(checksum_data(ip)))
            with self.if_(ip.checksum == self.meta.expected_checksum):
                self.apply_table(self.services)
                with self.if_(self.meta.service_found):
                    self.assign(
                        self.meta.flow_hash,
                        flow_hash.compute(flow_key(ip, udp)),
                    )
                    self.assign(self.meta.bucket, self.meta.flow_hash.cast(p4.bit2))
                    self.apply_table(self.backends)


class Emit(p4.Deparser[Headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.ipv4)
        self.emit(self.hdr.udp)


blocks = p4.BlockLibrary(Parse, Balance, Emit, externs=[checksum, flow_hash])


def build() -> pb.Program:
    """Assemble the blocks for the supplied switch and its metadata contract."""
    return reference.assemble(
        blocks,
        name="example_load_balancer",
        headers=Headers,
        metadata=Metadata,
        parser=Parse,
        control=Balance,
        deparser=Emit,
    )


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
