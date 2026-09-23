# expect: reportArgumentType line 31
"""A `concat` result assigned to a typed field without `as_`: the type
system has no width arithmetic, so `concat` cannot type as `Bits[L[16]]`
and the assignment needs `.as_(bit16)` to assert the width."""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Header, Struct, bit8, bit9, bit16, bit32, concat


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
        data = concat(self.hdr.ipv4.ttl, self.hdr.ipv4.protocol)
        self.assign(self.hdr.ipv4.hdrChecksum, data.as_(bit16))
        self.assign(self.hdr.ipv4.hdrChecksum, data)  # error: no width asserted
