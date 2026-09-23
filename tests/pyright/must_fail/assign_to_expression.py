# expect: reportArgumentType line 29
# expect: reportCallIssue line 29
"""Assigning to an expression: `ttl - 1` is a `Bits`, and `assign` wants a `Var`."""

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
        self.assign(self.hdr.ipv4.ttl, self.hdr.ipv4.ttl - 1)
        self.assign(self.hdr.ipv4.ttl - 1, self.hdr.ipv4.ttl)  # error: target is not a Var
