"""The csum16 program, authored in the eDSL.

`build()` returns the same `pb.Program` that csum16.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl.core import Program, bit
from p4blo.edsl.core.externs import checksum16
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("csum16")

    H = p.header("H", d=bit(16), c=bit(16))
    p.headers = p.struct("Parsed_packet", h=H)
    # The donor's `Metadata` is empty: no contract field, so every packet
    # leaves on port 0 undropped, as the vectors expect.
    p.metadata = p.struct("Metadata")

    # v1model's `update_checksum(true, { hdr.h.d }, hdr.h.c, HashAlgorithm.
    # csum16)` is a checksum16 instance over the 16 bits of the field list,
    # called at the end of the control.
    csum = p.extern_instance("csum", checksum16(p, bit(16)))

    with p.parser("parserI") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.h)
            s.accept()

    # The donor's `cIngress`, then its `uc` (the update-checksum control);
    # `cEgress` is empty and `vc` (verify_checksum) is deferred.
    with p.control("cIngress") as c:
        hdr = c.hdr
        with c.body() as b:
            b.assign(hdr.h.d, hdr.h.d + 1)
            b.call(csum, "compute", hdr.h.d, result=hdr.h.c)

    with p.deparser("DeparserI") as d:
        with d.body() as b:
            b.emit(d.hdr.h)

    p.export("parser", "parserI")
    p.export("control", "cIngress")
    p.export("deparser", "DeparserI")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
