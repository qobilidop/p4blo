# expect: reportArgumentType line 35
"""An rvalue passed to an `Out` extern parameter: `read`'s `result` is a
`Var`, and `ttl + 1` is only a `Bits`."""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Header, Struct, bit8, bit9, bit16, bit32
from p4blo.edsl.externs import Register


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
    idx: bit32


r = Register[bit8]("r", size=256)


class MyIngress(Control[headers, metadata]):
    def apply(self) -> None:
        self.assign(self.meta.idx, self.hdr.ipv4.ttl.cast(bit32))
        r.read(self.hdr.ipv4.ttl, self.meta.idx)
        r.read(self.hdr.ipv4.ttl + 1, self.meta.idx)  # error: result is an rvalue
