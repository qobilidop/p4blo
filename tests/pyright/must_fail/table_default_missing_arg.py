# expect: reportCallIssue line 43
"""A table default missing an action argument: `ipv4_forward(port=...)`
without `dstAddr` is an `Action[P]` call with a parameter left out."""

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
        default=ipv4_forward(port=bit9(1)),  # error: dstAddr is missing
        size=1024,
    )

    def apply(self) -> None:
        self.apply_table(self.ipv4_lpm)
