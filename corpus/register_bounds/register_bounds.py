"""The register_bounds program, authored in the eDSL.

`build()` returns the same `pb.Program` that register_bounds.txtpb encodes;
the test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl import Program, bit
from p4blo.edsl.externs import register
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("register_bounds")

    # idx picks the cell, val is added to it, got reports what the cell
    # holds afterwards; the packet is the whole header.
    h_t = p.header("h_t", idx=bit(8), val=bit(8), got=bit(8))
    p.headers = p.struct("headers", h=h_t)
    # No contract field: every packet leaves on port 0 (README).
    p.metadata = p.struct("metadata")

    # Four cells indexed by an 8-bit field: 252 of the 256 indices a packet
    # can name lie beyond the end.
    r = p.extern_instance("r", register(p, bit(8)), 4)

    with p.parser("P") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.h)
            s.accept()

    with p.control("C") as c:
        hdr = c.hdr
        with c.body() as b:
            i = hdr.h.idx.cast(bit(32))
            x = b.local("x", bit(8))
            b.call(r, "read", x, i)
            b.call(r, "write", i, x + hdr.h.val)
            # Read back what the write left: the sum in range, zero beyond
            # the end, where the write was ignored.
            b.call(r, "read", hdr.h.got, i)

    with p.deparser("D") as d:
        with d.body() as b:
            b.emit(d.hdr.h)

    p.export("parser", "P")
    p.export("control", "C")
    p.export("deparser", "D")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
