"""The parser-error program, authored in the eDSL: p4c's `parser_error-bmv2.p4`.

`build()` returns the same `pb.Program` that parser_error.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl import Expr, Program, bit, error_t
from p4blo.v0 import p4blo_pb2 as pb


def field(base: Expr, name: str) -> Expr:
    """`base.name` for a field whose name an `Expr` attribute shadows.

    `Ethernet.type` is a field of the source program; `Expr.type` is the
    builder's own attribute, so `hdr.eth.type` never reaches the field
    lookup. Calling the lookup directly does.
    """
    return Expr.__getattr__(base, name)


def build() -> pb.Program:
    p = Program("parser_error")

    ethernet = p.header("Ethernet", src=bit(48), dst=bit(48), type=bit(16))
    headers = p.struct("parsed_packet_t", eth=ethernet)
    # The source's `local_metadata_t` is empty; the two intrinsic fields the
    # program uses join it under the contract's names: parser_error, which
    # the architecture provides, and egress_port, which it consumes.
    metadata = p.struct("local_metadata_t", parser_error=error_t, egress_port=bit(9))
    p.headers = headers
    p.metadata = metadata

    with p.parser("parse") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.eth)
            s.accept()

    with p.control("ingress") as c:
        hdr, meta = c.hdr, c.meta
        with c.body() as b:
            with b.if_(meta.parser_error == p.errors.PacketTooShort):
                b.set_valid(hdr.eth)
                b.assign(field(hdr.eth, "type"), 0)
                b.assign(hdr.eth.src, 0)
                b.assign(hdr.eth.dst, 0)
            b.assign(meta.egress_port, 0)

    with p.deparser("deparser") as d:
        with d.body() as b:
            b.emit(d.hdr)

    p.export("parser", "parse")
    p.export("control", "ingress")
    p.export("deparser", "deparser")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
