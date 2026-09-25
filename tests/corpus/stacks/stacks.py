"""Header stack operations, authored in the eDSL.

p4c's `header-stack-ops-bmv2.p4`: every packet carries three op bytes,
and each op pushes, pops, fills or invalidates a slot of a five-deep
stack. `build()` returns the same `apb.BlockAssembly` that stacks.txtpb encodes;
the test suite checks the two are equal. Run as a script to print the
text format.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import IntEnum
from typing import Any

from p4blo.arch import assemble
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import (
    BlockLibrary,
    Bool,
    Control,
    Deparser,
    Error,
    Errors,
    Header,
    In,
    InOut,
    L,
    Parser,
    Stack,
    Struct,
    Transition,
    bit8,
    state,
)

# `#define MAX_H2_HEADERS 5`: the loop bound below, and the stack's depth,
# which a `Literal` width must spell as the number itself.
MAX_H2_HEADERS = 5


class h1_t(Header):
    hdr_type: bit8
    op1: bit8
    op2: bit8
    op3: bit8
    h2_valid_bits: bit8
    next_hdr_type: bit8


class h2_t(Header):
    hdr_type: bit8
    f1: bit8
    f2: bit8
    next_hdr_type: bit8


class h3_t(Header):
    hdr_type: bit8
    data: bit8


class headers(Struct):
    h1: h1_t
    h2: Stack[h2_t, L[5]]
    h3: h3_t


class metadata(Struct):
    """The program reads and writes no intrinsic metadata, so M is empty:
    the switch then delivers every packet to port 0, as the vectors expect."""


class errors(Errors):
    BadHeaderType: Error


class HdrType(IntEnum):
    """The `hdr_type` byte of each header, and `next_hdr_type`'s "none"."""

    H1 = 1
    H2 = 2
    H3 = 3
    NONE = 9


class Op(IntEnum):
    """An op byte: `NOP` is the whole byte, the rest are its high nibble;
    the low nibble is a count or a slot."""

    NOP = 0x00
    PUSH = 1
    POP = 2
    FILL = 3
    INVALIDATE = 4


class Fill(IntEnum):
    """What a fill writes into slot i: `f1 = 0xA0 + i`, `f2 = (i << 4) + 0x0A`."""

    F1_BASE = 0xA0
    F2_LOW = 0x0A


def if_ladder(c: Control[Any, Any], arms: Sequence[tuple[Bool, Callable[[], None]]]) -> None:
    """`if (c0) s0 else if (c1) s1 ...`, as the nested if/else it is."""
    (cond, body), *rest = arms
    with c.if_(cond):
        body()
    if rest:
        with c.else_():
            if_ladder(c, rest)


class parserI(Parser[headers, metadata]):
    @state
    def start(self) -> Transition:
        self.extract(self.hdr.h1)
        self.verify(self.hdr.h1.hdr_type == HdrType.H1, errors.BadHeaderType)
        return self.select(
            self.hdr.h1.next_hdr_type,
            {HdrType.H2: self.parse_h2, HdrType.H3: self.parse_h3},
            default=self.accept,
        )

    @state
    def parse_h2(self) -> Transition:
        self.extract(self.hdr.h2.next)
        # `hdr.h2.last` is `hdr.h2[hdr.h2.lastIndex]`, which the eDSL writes.
        last = self.hdr.h2.last
        self.verify(last.hdr_type == HdrType.H2, errors.BadHeaderType)
        return self.select(
            last.next_hdr_type,
            {HdrType.H2: self.parse_h2, HdrType.H3: self.parse_h3},
            default=self.accept,
        )

    @state
    def parse_h3(self) -> Transition:
        self.extract(self.hdr.h3)
        self.verify(self.hdr.h3.hdr_type == HdrType.H3, errors.BadHeaderType)
        return self.accept


class cDoOneOp(Control):
    """The sub-control: the op's high nibble picks the operation and the low
    nibble its count or slot. Its parameters are these two, not H and M."""

    hdr: InOut[headers]
    op: In[bit8]

    def apply(self) -> None:
        hdr, op = self.hdr, self.op

        def push(n: int) -> Callable[[], None]:
            return lambda: self.push(hdr.h2, n)

        def pop(n: int) -> Callable[[], None]:
            return lambda: self.pop(hdr.h2, n)

        def fill(i: int) -> Callable[[], None]:
            def body() -> None:
                self.set_valid(hdr.h2[i])
                self.assign(hdr.h2[i].hdr_type, HdrType.H2)
                self.assign(hdr.h2[i].f1, Fill.F1_BASE + i)
                self.assign(hdr.h2[i].f2, (i << 4) + Fill.F2_LOW)
                self.assign(hdr.h2[i].next_hdr_type, HdrType.NONE)

            return body

        def invalidate(i: int) -> Callable[[], None]:
            return lambda: self.set_invalid(hdr.h2[i])

        def nop() -> None:
            pass

        if_ladder(
            self,
            [
                (op == Op.NOP, nop),
                (
                    op[7:4] == Op.PUSH,
                    lambda: if_ladder(self, [(op[3:0] == n, push(n)) for n in range(1, 7)]),
                ),
                (
                    op[7:4] == Op.POP,
                    lambda: if_ladder(self, [(op[3:0] == n, pop(n)) for n in range(1, 7)]),
                ),
                (
                    op[7:4] == Op.FILL,
                    lambda: if_ladder(self, [(op[3:0] == i, fill(i)) for i in range(5)]),
                ),
                (
                    op[7:4] == Op.INVALIDATE,
                    lambda: if_ladder(self, [(op[3:0] == i, invalidate(i)) for i in range(5)]),
                ),
            ],
        )


class cIngress(Control[headers, metadata]):
    def apply(self) -> None:
        hdr = self.hdr
        # `do_one_op.apply(hdr, hdr.h1.op1)`: the op is read into a local
        # first, because the validator refuses an argument that may alias
        # an inout one, and the copy is what `in` means anyway.
        for name, field in (("op1", hdr.h1.op1), ("op2", hdr.h1.op2), ("op3", hdr.h1.op3)):
            op = self.local(name, bit8)
            self.assign(op, field)
            self.call(cDoOneOp, hdr, op)
        # Record the valid bits of every h2 slot in h1.h2_valid_bits, so
        # that the vectors can check them.
        self.assign(hdr.h1.h2_valid_bits, 0)
        for i in range(MAX_H2_HEADERS):
            with self.if_(hdr.h2[i].is_valid()):
                self.assign_slice(hdr.h1.h2_valid_bits, i, i, 1)


class DeparserI(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.h1)
        self.emit(self.hdr.h2)
        self.emit(self.hdr.h3)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(parserI, cIngress, DeparserI, errors=errors),
        name="stacks",
        headers=headers,
        metadata=metadata,
        exports={"parser": parserI, "control": cIngress, "deparser": DeparserI},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
