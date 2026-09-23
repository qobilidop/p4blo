"""The verify-error program, authored in the eDSL: p4c's `issue1824-bmv2.p4`.

`build()` returns the same `pb.Program` that verify_error.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl.core import Program, bit, error_t
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("verify_error")

    test_header = p.header("test_header", dstAddr=bit(48), srcAddr=bit(48))
    headers = p.struct("headers", h1=test_header)
    mystruct1_t = p.struct("mystruct1_t", a=bit(4), b=bit(4))
    # The source's metadata, plus parser_error from standard_metadata under
    # the contract's name. The program never sets egress_spec, so no
    # egress_port: the architecture sends to port 0.
    metadata = p.struct("metadata", mystruct1=mystruct1_t, parser_error=error_t)
    p.headers = headers
    p.metadata = metadata

    # The program's own errors, declared after core.p4's seven.
    p.error("IPv4OptionsNotSupported")
    p.error("IPv4ChecksumError")
    p.error("IPv4HeaderTooShort")
    p.error("IPv4BadPacket")

    with p.parser("MyParser") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.h1)
            s.verify(False, p.errors.IPv4BadPacket)
            s.verify(False, p.errors.IPv4HeaderTooShort)
            s.accept()

    with p.control("MyIngress") as c:
        hdr, meta = c.hdr, c.meta
        with c.body() as b:
            with b.if_(meta.parser_error != p.errors.NoError):
                b.assign(hdr.h1.dstAddr, 0xBAD)

    with p.deparser("MyDeparser") as d:
        with d.body() as b:
            b.emit(d.hdr.h1)

    p.export("parser", "MyParser")
    p.export("control", "MyIngress")
    p.export("deparser", "MyDeparser")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
