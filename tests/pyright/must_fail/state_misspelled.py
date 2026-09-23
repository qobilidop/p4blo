# expect: reportAttributeAccessIssue line 45
"""A misspelled state in a `select` target: `self.parse_ipv5` is not a method."""

from __future__ import annotations

from enum import IntEnum

from p4blo.edsl import Bool, Header, Parser, Struct, Transition, bit9, bit16, bit32, bit48, state


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


class EtherType(IntEnum):
    IPV4 = 0x800


class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        return self.goto(self.parse_ethernet)

    @state
    def parse_ethernet(self) -> Transition:
        self.extract(self.hdr.ethernet)
        return self.select(
            self.hdr.ethernet.etherType,
            {EtherType.IPV4: self.parse_ipv5},  # error: no state parse_ipv5
            default=self.accept,
        )

    @state
    def parse_ipv4(self) -> Transition:
        self.extract(self.hdr.ipv4)
        return self.accept
