"""Header stack operations, authored in the eDSL.

p4c's `header-stack-ops-bmv2.p4`: every packet carries three op bytes,
and each op pushes, pops, fills or invalidates a slot of a five-deep
stack. `build()` returns the same `pb.Program` that stacks.txtpb encodes;
the test suite checks the two are equal. Run as a script to print the
text format.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

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


def if_ladder(b: Stmts, arms: Sequence[tuple[Expr, Callable[[], None]]]) -> None:
    """`if (c0) s0 else if (c1) s1 ...`, as the nested if/else it is."""
    (cond, body), *rest = arms
    with b.if_(cond):
        body()
    if rest:
        with b.else_():
            if_ladder(b, rest)


def build() -> pb.Program:
    p = Program("stacks")

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
    # the switch then delivers every packet to port 0, as the vectors expect.
    metadata = p.struct("metadata")
    p.headers = headers
    p.metadata = metadata

    BadHeaderType = p.error("BadHeaderType")

    with p.parser("parserI") as ps:
        hdr = ps.hdr
        # `hdr.h2.last` is `hdr.h2[hdr.h2.lastIndex]`.
        last = hdr.h2[hdr.h2.last_index]
        with ps.state("start") as s:
            s.extract(hdr.h1)
            s.verify(hdr.h1.hdr_type == 1, BadHeaderType)
            s.select(hdr.h1.next_hdr_type, {2: "parse_h2", 3: "parse_h3"}, default=ps.accept)
        with ps.state("parse_h2") as s:
            s.extract(hdr.h2.next)
            s.verify(last.hdr_type == 2, BadHeaderType)
            s.select(last.next_hdr_type, {2: "parse_h2", 3: "parse_h3"}, default=ps.accept)
        with ps.state("parse_h3") as s:
            s.extract(hdr.h3)
            s.verify(hdr.h3.hdr_type == 3, BadHeaderType)
            s.accept()

    # The sub-control: the op's high nibble picks the operation and the low
    # nibble its count or slot.
    with p.control("cDoOneOp", params=[("hdr", "inout", headers), ("op", "in", bit(8))]) as c:
        hdr, op = c.hdr, c.op
        with c.body() as b:

            def push(n: int) -> Callable[[], None]:
                return lambda: b.push(hdr.h2, n)

            def pop(n: int) -> Callable[[], None]:
                return lambda: b.pop(hdr.h2, n)

            def fill(i: int) -> Callable[[], None]:
                def body() -> None:
                    b.set_valid(hdr.h2[i])
                    b.assign(hdr.h2[i].hdr_type, 2)
                    b.assign(hdr.h2[i].f1, 0xA0 + i)
                    b.assign(hdr.h2[i].f2, (i << 4) + 0x0A)
                    b.assign(hdr.h2[i].next_hdr_type, 9)

                return body

            def invalidate(i: int) -> Callable[[], None]:
                return lambda: b.set_invalid(hdr.h2[i])

            def nop() -> None:
                pass

            if_ladder(
                b,
                [
                    (op == 0x00, nop),
                    (
                        op[7:4] == 1,
                        lambda: if_ladder(b, [(op[3:0] == n, push(n)) for n in range(1, 7)]),
                    ),
                    (
                        op[7:4] == 2,
                        lambda: if_ladder(b, [(op[3:0] == n, pop(n)) for n in range(1, 7)]),
                    ),
                    (
                        op[7:4] == 3,
                        lambda: if_ladder(b, [(op[3:0] == i, fill(i)) for i in range(5)]),
                    ),
                    (
                        op[7:4] == 4,
                        lambda: if_ladder(b, [(op[3:0] == i, invalidate(i)) for i in range(5)]),
                    ),
                ],
            )

    with p.control("cIngress") as c:
        hdr = c.hdr
        with c.body() as b:
            # `do_one_op.apply(hdr, hdr.h1.op1)`: the op is read into a local
            # first, because the validator refuses an argument that may alias
            # an inout one, and the copy is what `in` means anyway.
            for name in ("op1", "op2", "op3"):
                op = b.local(name, bit(8))
                b.assign(op, getattr(hdr.h1, name))
                b.call_block("cDoOneOp", hdr, op)
            # Record the valid bits of every h2 slot in h1.h2_valid_bits, so
            # that the vectors can check them.
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
