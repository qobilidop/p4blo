# expect: reportArgumentType line 28
"""A 16-bit value assigned to an 8-bit field: `assign(Var[W], Bits[W] | int)`."""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Header, Struct, bit8, bit9, bit16, bit32


class ipv4_t(Header):
    ttl: bit8
    protocol: bit8
    hdrChecksum: bit16
    dstAddr: bit32


class headers(Struct):
    ipv4: ipv4_t


class metadata(Struct):
    egress_port: bit9
    drop: Bool


class MyIngress(Control[headers, metadata]):
    def apply(self) -> None:
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.protocol)
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.hdrChecksum)  # error: 16 bits into 8
