# expect: reportAttributeAccessIssue line 48
"""A misspelled table: `self.ipv4_lpn` is not an attribute of the control."""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Header, Struct, Table, action, bit9, bit16, bit32, bit48, lpm


class ethernet_t(Header):
    dstAddr: bit48
    srcAddr: bit48
    etherType: bit16


class ipv4_t(Header):
    dstAddr: bit32


class headers(Struct):
    ethernet: ethernet_t
    ipv4: ipv4_t


class metadata(Struct):
    egress_port: bit9
    drop: Bool


class MyIngress(Control[headers, metadata]):
    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)

    @action
    def ipv4_forward(self, dstAddr: bit48, port: bit9) -> None:
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ethernet.dstAddr, dstAddr)

    ipv4_lpm = Table(
        keys=[lpm(headers.ipv4.dstAddr)],
        actions=[ipv4_forward, drop],
        default=drop(),
        size=1024,
    )

    def apply(self) -> None:
        self.apply_table(self.ipv4_lpm)
        self.apply_table(self.ipv4_lpn)  # error: no table ipv4_lpn
