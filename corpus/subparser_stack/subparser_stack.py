"""A sub-parser extracting into a header stack, authored in the eDSL.

p4c's `subparser-with-header-stack-bmv2.p4`: the first h2 header is
extracted by a sub-parser into `hdr.h2.next`, the rest by the top-level
parser, and the control records which slots ended up valid. `build()`
returns the same `pb.Program` that subparser_stack.txtpb encodes; the test
suite checks the two are equal. Run as a script to print the text format.
"""

from __future__ import annotations

from p4blo.edsl.core import Expr, Program, Stmts, bit
from p4blo.v0 import p4blo_pb2 as pb

MAX_H2_HEADERS = 5


def set_slice(b: Stmts, field: Expr, hi: int, lo: int, value: int) -> None:
    """`field[hi:lo] = value`, which the IR has no lvalue for, as the
    read-modify-write `field = (field & ~mask) | (value << lo)`, every
    operand at the field's width."""
    width = field.width
    mask = ((1 << (hi - lo + 1)) - 1) << lo
    if not 0 <= value < (1 << (hi - lo + 1)):
        raise ValueError(f"{value} does not fit in [{hi}:{lo}]")
    shifted = b.block.program.literal(value, bit(width)) << lo
    b.assign(field, (field & ~b.block.program.literal(mask, bit(width))) | shifted)


def build() -> pb.Program:
    p = Program("subparser_stack")

    h1_t = p.header(
        "h1_t",
        hdr_type=bit(8),
        op1=bit(8),
        op2=bit(8),
        op3=bit(8),
        h2_valid_bits=bit(8),
        next_hdr_type=bit(8),
    )
    h2_t = p.header("h2_t", hdr_type=bit(8), f1=bit(8), f2=bit(8), next_hdr_type=bit(8))
    h3_t = p.header("h3_t", hdr_type=bit(8), data=bit(8))
    headers = p.struct("headers", h1=h1_t, h2=h2_t[MAX_H2_HEADERS], h3=h3_t)
    # The program reads and writes no intrinsic metadata, so M is empty:
    # the switch then delivers every packet to port 0, as the vector expects.
    metadata = p.struct("metadata")
    p.headers = headers
    p.metadata = metadata

    BadHeaderType = p.error("BadHeaderType")

    # The sub-parser: one h2 header into the stack's next slot, and its
    # next_hdr_type out to the caller.
    sub_params = [("hdr", "inout", headers), ("ret_next_hdr_type", "out", bit(8))]
    with p.parser("subParserImpl", params=sub_params) as sub:
        hdr = sub.hdr
        last = hdr.h2[hdr.h2.last_index]
        with sub.state("start") as s:
            s.extract(hdr.h2.next)
            s.verify(last.hdr_type == 2, BadHeaderType)
            s.assign(sub.ret_next_hdr_type, last.next_hdr_type)
            s.accept()

    with p.parser("parserI") as ps:
        hdr = ps.hdr
        # `hdr.h2.last` is `hdr.h2[hdr.h2.lastIndex]`.
        last = hdr.h2[hdr.h2.last_index]
        # A parser-scoped local, live across states.
        my_next_hdr_type = ps.local("my_next_hdr_type", bit(8))
        with ps.state("start") as s:
            s.extract(hdr.h1)
            s.verify(hdr.h1.hdr_type == 1, BadHeaderType)
            s.select(hdr.h1.next_hdr_type, {2: "parse_first_h2", 3: "parse_h3"}, default=ps.accept)
        with ps.state("parse_first_h2") as s:
            s.call_block("subParserImpl", hdr, my_next_hdr_type)
            s.select(my_next_hdr_type, {2: "parse_other_h2", 3: "parse_h3"}, default=ps.accept)
        with ps.state("parse_other_h2") as s:
            s.extract(hdr.h2.next)
            s.verify(last.hdr_type == 2, BadHeaderType)
            s.select(last.next_hdr_type, {2: "parse_other_h2", 3: "parse_h3"}, default=ps.accept)
        with ps.state("parse_h3") as s:
            s.extract(hdr.h3)
            s.verify(hdr.h3.hdr_type == 3, BadHeaderType)
            s.accept()

    with p.control("cIngress") as c:
        hdr = c.hdr
        with c.body() as b:
            # Record the valid bits of every h2 slot in h1.h2_valid_bits, so
            # that the vector can check them.
            b.assign(hdr.h1.h2_valid_bits, 0)
            for i in range(MAX_H2_HEADERS):
                with b.if_(hdr.h2[i].is_valid()):
                    set_slice(b, hdr.h1.h2_valid_bits, i, i, 1)

    with p.deparser("DeparserI") as d:
        with d.body() as b:
            b.emit(d.hdr.h1)
            b.emit(d.hdr.h2)
            b.emit(d.hdr.h3)

    p.export("parser", "parserI")
    p.export("control", "cIngress")
    p.export("deparser", "DeparserI")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
