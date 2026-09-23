"""Every construct the design note names, once, in one program.

A sub-parser call with an `Out` argument; a header stack (`.next`, `.last`,
indexing, push and pop, set_valid and set_invalid); a cast; a slice narrowed
with `as_`; `mux`; an if/elif/else ladder; a ternary table with typed const
entries over two keys; a direct action call; the three extern families
(`Register`, `Counter`, `Checksum16`) with `Out` arguments; `IntEnum` select
keys; `concat` asserted to a width with `as_`. Must type-check with zero
errors.
"""

from __future__ import annotations

from enum import IntEnum

from p4blo.edsl import (
    Bits,
    Bool,
    Control,
    Deparser,
    Header,
    L,
    InOut,
    Out,
    Parser,
    Program,
    Stack,
    Struct,
    Table,
    Transition,
    Var,
    action,
    bit8,
    bit9,
    bit16,
    bit32,
    concat,
    entry,
    exact,
    mux,
    state,
    ternary,
)
from p4blo.edsl.externs import Checksum16, Counter, Register

MAX_H2 = 5


class h1_t(Header):
    hdr_type: bit8
    op1: bit8
    op2: bit8
    h2_valid_bits: bit8
    next_hdr_type: bit8
    csum: bit16


class h2_t(Header):
    hdr_type: bit8
    f1: bit8
    f2: bit8
    next_hdr_type: bit8


class headers(Struct):
    h1: h1_t
    h2: Stack[h2_t, L[5]]


class metadata(Struct):
    egress_port: bit9
    drop: Bool
    next_type: bit8
    nibble: Var[L[4]]
    idx: bit32
    value: bit8


class HdrType(IntEnum):
    H1 = 1
    H2 = 2


class Op(IntEnum):
    NOP = 0
    PUSH = 1
    POP = 2


class SubParser(Parser[headers, metadata]):
    """One h2 header into the stack's next slot, its next_hdr_type out."""

    hdr: InOut[headers]
    ret_next_hdr_type: Out[bit8]

    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.h2.next)
        self.assign(self.ret_next_hdr_type, self.hdr.h2.last.next_hdr_type)
        return self.accept


class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.h1)
        return self.select(
            self.hdr.h1.next_hdr_type, {HdrType.H2: self.parse_first_h2}, default=self.accept
        )

    @state
    def parse_first_h2(self) -> Transition:
        self.call(SubParser, self.meta.next_type)
        return self.select(
            self.meta.next_type, {HdrType.H2: self.parse_other_h2}, default=self.accept
        )

    @state
    def parse_other_h2(self) -> Transition:
        self.extract(self.hdr.h2.next)
        return self.select(
            self.hdr.h2.last.next_hdr_type,
            {HdrType.H2: self.parse_other_h2},
            default=self.accept,
        )


r = Register[bit8]("r", size=256)
pkts = Counter("pkts", size=256)
csum = Checksum16[Bits[L[24]]]("csum")


def bump(c: Control[headers, metadata], field: Var[L[8]]) -> None:
    """A helper typed on `Var`: it needs a place to write, not just a value."""
    c.assign(field, field + 1)


class MyIngress(Control[headers, metadata]):
    @action
    def NoAction(self) -> None:
        pass

    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)

    @action
    def set_port(self, port: bit9) -> None:
        self.assign(self.meta.egress_port, port)

    @action
    def fill(self, f1: bit8, f2: bit8) -> None:
        self.set_valid(self.hdr.h2[0])
        self.assign(self.hdr.h2[0].f1, f1)
        self.assign(self.hdr.h2[0].f2, f2)

    ops = Table(
        keys=[ternary(headers.h1.op1), exact(headers.h1.hdr_type)],
        actions=[set_port, fill, drop, NoAction],
        default=NoAction(),
        entries=[
            entry((bit8(0x10), bit8(HdrType.H1)), set_port(port=bit9(1)), priority=1),
            entry((bit8(0x20), bit8(HdrType.H1)), fill(f1=bit8(0xA0), f2=bit8(0x0A)), priority=2),
        ],
        size=16,
    )

    def apply(self) -> None:
        op = self.hdr.h1.op1
        # A cast, then the three extern families: a counter, a register read
        # into an `Out` argument and written back, a checksum in expression
        # position further down.
        self.assign(self.meta.idx, self.hdr.h1.hdr_type.cast(bit32))
        pkts.count(self.meta.idx)
        r.read(self.meta.value, self.meta.idx)
        self.assign(self.meta.value, self.meta.value + self.hdr.h1.op2)
        r.write(self.meta.idx, self.meta.value)
        bump(self, self.hdr.h1.op2)
        # A slice narrowed with `as_`; `mux` for a conditional value.
        self.assign(self.meta.nibble, op[3:0].as_(Bits[L[4]]))
        self.assign(self.meta.egress_port, mux(self.hdr.h2[0].is_valid(), bit9(1), bit9(2)))
        # Stack operations behind an if/elif/else ladder.
        with self.if_(op[7:4] == Op.PUSH):
            self.push(self.hdr.h2, 1)
        with self.elif_(op[7:4] == Op.POP):
            self.pop(self.hdr.h2, 1)
        with self.else_():
            self.set_invalid(self.hdr.h2[MAX_H2 - 1])
        self.apply_table(self.ops)
        self.set_port(port=bit9(3))
        # `concat` in expression position, asserted to the checksum's width.
        with self.if_(self.hdr.h1.is_valid()):
            data = concat(self.hdr.h1.hdr_type, self.hdr.h1.op1, self.hdr.h1.op2)
            self.assign(self.hdr.h1.csum, csum.compute(data.as_(Bits[L[24]])))


class MyDeparser(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.h1)
        self.emit(self.hdr.h2)


program = Program(
    "constructs",
    headers=headers,
    metadata=metadata,
    parser=MyParser,
    control=MyIngress,
    deparser=MyDeparser,
    externs=[r, pkts, csum],
)
