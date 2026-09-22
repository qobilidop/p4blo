"""The forwarder, authored in the eDSL.

`build()` returns the same `pb.Program` that forwarder.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl import Program, bit, boolean, lpm
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("forwarder")

    ethernet_t = p.header("ethernet_t", dstAddr=bit(48), srcAddr=bit(48), etherType=bit(16))
    ipv4_t = p.header(
        "ipv4_t",
        version=bit(4),
        ihl=bit(4),
        diffserv=bit(8),
        totalLen=bit(16),
        identification=bit(16),
        flags=bit(3),
        fragOffset=bit(13),
        ttl=bit(8),
        protocol=bit(8),
        hdrChecksum=bit(16),
        srcAddr=bit(32),
        dstAddr=bit(32),
    )
    headers = p.struct("headers", ethernet=ethernet_t, ipv4=ipv4_t)
    # The metadata contract of the step-1 architecture: ingress_port is
    # provided, egress_port and drop are consumed.
    metadata = p.struct("metadata", ingress_port=bit(9), egress_port=bit(9), drop=boolean)
    p.headers = headers
    p.metadata = metadata

    TYPE_IPV4 = 0x800

    with p.parser("MyParser") as ps:
        hdr = ps.hdr
        with ps.state("start") as s:
            s.transition("parse_ethernet")
        with ps.state("parse_ethernet") as s:
            s.extract(hdr.ethernet)
            s.select(hdr.ethernet.etherType, {TYPE_IPV4: "parse_ipv4"}, default=ps.accept)
        with ps.state("parse_ipv4") as s:
            s.extract(hdr.ipv4)
            s.accept()

    with p.control("MyIngress") as c:
        hdr, meta = c.hdr, c.meta
        c.action("NoAction")
        with c.action("drop") as a:
            a.assign(meta.drop, True)
        with c.action("ipv4_forward", dstAddr=bit(48), port=bit(9)) as a:
            a.assign(meta.egress_port, a.port)
            a.assign(hdr.ethernet.srcAddr, hdr.ethernet.dstAddr)
            a.assign(hdr.ethernet.dstAddr, a.dstAddr)
            a.assign(hdr.ipv4.ttl, hdr.ipv4.ttl - 1)
        ipv4_lpm = c.table(
            "ipv4_lpm",
            keys=[lpm(hdr.ipv4.dstAddr)],
            actions=["ipv4_forward", "drop", "NoAction"],
            default="drop",
            size=1024,
        )
        with c.body() as b:
            with b.if_(hdr.ipv4.is_valid()):
                b.apply(ipv4_lpm)

    with p.deparser("MyDeparser") as d:
        with d.body() as b:
            b.emit(d.hdr.ethernet)
            b.emit(d.hdr.ipv4)

    p.export("parser", "MyParser")
    p.export("control", "MyIngress")
    p.export("deparser", "MyDeparser")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
