# expect: reportArgumentType line 29
"""A cast to the wrong width: `cast(Bits[L[16]])` types as `Bits[L[16]]`,
which no 8-bit target accepts."""

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
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.hdrChecksum.cast(bit8))
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.dstAddr.cast(bit16))  # error: cast to 16 bits
