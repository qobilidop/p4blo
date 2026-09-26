"""Transparent TCP filtering with exact, bounded SYN-created pinholes."""

from __future__ import annotations

from p4blo import edsl as p4
from p4blo.arch import v1model
from p4blo.arch.externs.declarations import CRC16, Checksum16, Register
from p4blo.arch.v0 import assembly_pb2 as apb

ChecksumWords = p4.Bits[p4.L[144]]
FlowTuple = p4.Bits[p4.L[96]]
FlowRecord = p4.Var[p4.L[97]]


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


class TCP(p4.Header):
    src: p4.bit16
    dst: p4.bit16
    sequence: p4.bit32
    acknowledgement: p4.bit32
    data_offset: p4.bit4
    reserved: p4.bit4
    flags: p4.bit8
    window: p4.bit16
    checksum: p4.bit16
    urgent: p4.bit16


class Headers(p4.Struct):
    ethernet: Ethernet
    ipv4: IPv4
    tcp: TCP


class Metadata(p4.Struct):
    ingress_port: p4.bit9
    egress_spec: p4.bit9
    client: p4.bit32
    server: p4.bit32
    client_port: p4.bit16
    server_port: p4.bit16
    permitted: p4.Bool


class Parse(p4.Parser[Headers, Metadata]):
    @p4.state(start=True)
    def start(self) -> p4.Transition:
        self.extract(self.hdr.ethernet)
        return self.select(self.hdr.ethernet.ether_type, {0x0800: self.ipv4}, default=self.accept)

    @p4.state
    def ipv4(self) -> p4.Transition:
        self.extract(self.hdr.ipv4)
        return self.select(self.hdr.ipv4.protocol, {6: self.tcp}, default=self.accept)

    @p4.state
    def tcp(self) -> p4.Transition:
        self.extract(self.hdr.tcp)
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
flow_hash = CRC16[FlowTuple]("flow_hash")
# The top bit distinguishes an occupied record from an empty all-zero cell.
flows = Register[FlowRecord]("flows", size=16)


class Filter(p4.Control[Headers, Metadata]):
    destination: p4.bit9
    expected_checksum: p4.bit16
    tuple_bits: p4.Var[p4.L[96]]
    record: FlowRecord
    resident: FlowRecord
    digest: p4.bit16
    slot: p4.bit32

    @p4.action
    def allow(self) -> None:
        self.assign(self.meta.permitted, True)

    @p4.action
    def deny(self) -> None:
        self.assign(self.meta.permitted, False)

    services = p4.Table(
        keys=(p4.lpm(Metadata.server), p4.exact(Metadata.server_port)),
        actions=[allow, deny],
        default=deny(),
        size=256,
    )

    @p4.action
    def inspect_flow(self) -> None:
        self.assign(
            self.tuple_bits,
            p4.concat(
                self.meta.client, self.meta.server, self.meta.client_port, self.meta.server_port
            ).as_(FlowTuple),
        )
        self.assign(self.digest, flow_hash.compute(self.tuple_bits))
        self.assign(self.slot, (self.digest & 15).cast(p4.bit32))
        self.assign(self.record, p4.concat(p4.bit1(1), self.tuple_bits).as_(FlowRecord))
        flows.read(self.resident, self.slot)
        # Only an inside SYN without ACK/FIN/RST can create a new pinhole.
        new_outbound_syn = (
            (self.meta.ingress_port == 1)
            & ((self.hdr.tcp.flags & 0x17) == 0x02)
            & (self.resident == 0)
        )
        with self.if_(self.resident == self.record):
            self.assign(self.meta.egress_spec, self.destination)
        with self.elif_(new_outbound_syn):
            flows.write(self.slot, self.record)
            self.assign(self.meta.egress_spec, self.destination)

    def orient_flow(self) -> None:
        """Build the branches that give both directions one client/server tuple."""
        ip, tcp = self.hdr.ipv4, self.hdr.tcp
        with self.if_(self.meta.ingress_port == 1):
            self.assign(self.meta.client, ip.src)
            self.assign(self.meta.server, ip.dst)
            self.assign(self.meta.client_port, tcp.src)
            self.assign(self.meta.server_port, tcp.dst)
            self.assign(self.destination, 2)
        with self.else_():
            self.assign(self.meta.client, ip.dst)
            self.assign(self.meta.server, ip.src)
            self.assign(self.meta.client_port, tcp.dst)
            self.assign(self.meta.server_port, tcp.src)
            self.assign(self.destination, 1)

    def apply(self) -> None:
        self.assign(self.meta.egress_spec, 511)
        ip, tcp = self.hdr.ipv4, self.hdr.tcp
        supported_packet = (
            ip.is_valid()
            & tcp.is_valid()
            & (ip.version == 4)
            & (ip.ihl == 5)
            & (ip.total_length >= 40)
            & ((ip.flags & 5) == 0)
            & (ip.fragment_offset == 0)
            & (tcp.data_offset == 5)
            & ((self.meta.ingress_port == 1) | (self.meta.ingress_port == 2))
        )
        with self.if_(supported_packet):
            self.assign(self.expected_checksum, checksum.compute(checksum_data(ip)))
            with self.if_(ip.checksum == self.expected_checksum):
                self.orient_flow()
                self.apply_table(self.services)
                with self.if_(self.meta.permitted):
                    self.inspect_flow()


class Emit(p4.Deparser[Headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.ipv4)
        self.emit(self.hdr.tcp)


blocks = p4.BlockLibrary(Parse, Filter, Emit, externs=[checksum, flow_hash, flows])


def build() -> apb.BlockAssembly:
    """Bind the core blocks to the scoped v1model metadata contract."""
    return v1model.assemble(
        blocks,
        name="example_firewall",
        headers=Headers,
        metadata=Metadata,
        parser=Parse,
        ingress=Filter,
        deparser=Emit,
    )


if __name__ == "__main__":
    from p4blo.arch import wire

    print(wire.dump_text(build()), end="")
