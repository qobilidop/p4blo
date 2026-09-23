# expect: reportArgumentType line 41
"""An action argument of the wrong width: an 8-bit literal for a 9-bit port."""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Header, Struct, action, bit8, bit9, bit16, bit32, bit48


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
        self.ipv4_forward(dstAddr=self.hdr.ethernet.srcAddr, port=bit9(1))
        self.ipv4_forward(dstAddr=self.hdr.ethernet.srcAddr, port=bit8(1))  # error: port is 9 bits
