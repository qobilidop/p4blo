# expect: reportCallIssue line 43
"""A direct action call missing an argument: `self.ipv4_forward(port=...)`
without `dstAddr`."""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Header, Struct, action, bit9, bit16, bit32, bit48


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

    def apply(self) -> None:
        self.drop()
        self.ipv4_forward(self.hdr.ethernet.srcAddr, bit9(1))
        self.ipv4_forward(port=bit9(1))  # error: dstAddr is missing
