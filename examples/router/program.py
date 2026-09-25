"""A fixed-header IPv4 router: validate, select a route, rewrite, emit."""

from __future__ import annotations

from p4blo import edsl as p4
from p4blo.arch import reference
from p4blo.arch.externs.declarations import Checksum16
from p4blo.v0 import p4blo_pb2 as pb

ChecksumWords = p4.Bits[p4.L[144]]


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


class Headers(p4.Struct):
    ethernet: Ethernet
    ipv4: IPv4


class Metadata(p4.Struct):
    ingress_port: p4.bit9
    egress_port: p4.bit9
    drop: p4.Bool
    expected_checksum: p4.bit16


class Parse(p4.Parser[Headers, Metadata]):
    @p4.state(start=True)
    def start(self) -> p4.Transition:
        self.extract(self.hdr.ethernet)
        return self.select(self.hdr.ethernet.ether_type, {0x0800: self.ipv4}, default=self.accept)

    @p4.state
    def ipv4(self) -> p4.Transition:
        self.extract(self.hdr.ipv4)
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


checksum = Checksum16[ChecksumWords]("checksum")


class Route(p4.Control[Headers, Metadata]):
    @p4.action
    def deny(self) -> None:
        self.assign(self.meta.drop, True)

    @p4.action
    def forward(self, src_mac: p4.bit48, dst_mac: p4.bit48, port: p4.bit9) -> None:
        self.assign(self.hdr.ethernet.src, src_mac)
        self.assign(self.hdr.ethernet.dst, dst_mac)
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)
        self.assign(self.hdr.ipv4.checksum, checksum.compute(checksum_data(self.hdr.ipv4)))
        self.assign(self.meta.drop, False)

    routes = p4.Table(
        keys=(p4.lpm(Headers.ipv4.dst),),
        actions=[forward, deny],
        default=deny(),
        size=1024,
    )

    def apply(self) -> None:
        # Controls also run after parser failure: begin with a closed gate.
        self.assign(self.meta.drop, True)
        ip = self.hdr.ipv4
        supported_packet = (
            ip.is_valid()
            & (ip.version == 4)
            & (ip.ihl == 5)
            & (ip.total_length >= 20)
            & (ip.ttl > 1)
            & ((ip.flags & 5) == 0)
            & (ip.fragment_offset == 0)
        )
        with self.if_(supported_packet):
            self.assign(self.meta.expected_checksum, checksum.compute(checksum_data(ip)))
            with self.if_(ip.checksum == self.meta.expected_checksum):
                self.apply_table(self.routes)


class Emit(p4.Deparser[Headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.ipv4)


blocks = p4.BlockLibrary(Parse, Route, Emit, externs=[checksum])


def build() -> pb.Program:
    """Assemble the blocks for the supplied switch and its metadata contract."""
    return reference.assemble(
        blocks,
        name="example_router",
        headers=Headers,
        metadata=Metadata,
        parser=Parse,
        control=Route,
        deparser=Emit,
    )


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
