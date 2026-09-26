# expect: reportAttributeAccessIssue line 28
"""A misspelled field: views have no `__getattr__`, so `tt1` is unknown."""

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
        self.assign(self.hdr.ipv4.ttl, 0)
        self.assign(self.hdr.ipv4.tt1, 0)  # error: tt1 is not a field
