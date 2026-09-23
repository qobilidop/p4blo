# expect: reportOperatorIssue line 27
"""An 8-bit plus a 16-bit operand: `+` is typed `(Bits[W], Bits[W] | int)`."""

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
        bad = self.hdr.ipv4.ttl + self.hdr.ipv4.hdrChecksum  # error: 8-bit plus 16-bit
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl + self.hdr.ipv4.protocol)
