"""The stateful program, authored in the eDSL.

`build()` returns the same `pb.Program` that stateful.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from enum import IntEnum

from p4blo.arch import assemble
from p4blo.arch.externs.declarations import Counter, Register
from p4blo.edsl import (
    BlockLibrary,
    Control,
    Deparser,
    Header,
    Parser,
    Struct,
    Transition,
    bit8,
    bit32,
    state,
)
from p4blo.v0 import p4blo_pb2 as pb


class myhdr_t(Header):
    reg_idx_to_update: bit8
    value_to_add: bit8
    debug_last_reg_value_written: bit8


class Headers(Struct):
    myhdr: myhdr_t


class Meta(Struct):
    """The donor's `Meta` is empty. It declares no contract field, so the
    switch reads egress_port as 0 and drop as false: every packet leaves
    on port 0, as the vectors expect."""


class Seed(IntEnum):
    """What the donor writes to the cell, `0x2a`."""

    VALUE = 0x2A


# register<bit<8>>(256) r; the one instance both halves of the pipeline
# use. `counter(256, CounterType.packets) pkts` is our addition, counted
# once per packet at the register's index; STF cannot observe it.
r = Register[bit8]("r", size=256)
pkts = Counter("pkts", size=256)


class p(Parser[Headers, Meta]):
    @state
    def start(self) -> Transition:
        self.extract(self.hdr.myhdr)
        return self.accept


class pipeline(Control[Headers, Meta]):
    """The donor's `ingress` followed by its `egress`, as one control: the
    architecture runs one control, and nothing happens between the two."""

    def apply(self) -> None:
        hdr = self.hdr
        idx = hdr.myhdr.reg_idx_to_update.cast(bit32)
        # -- ingress --
        pkts.count(idx)
        x = self.local("x", bit8)
        r.read(x, idx)
        # The donor writes 0x2a unconditionally and discards `x`. Seeding
        # only an untouched cell keeps its vectors and lets ours see the
        # value the previous packet left behind (README, "Added").
        with self.if_(x == 0):
            r.write(idx, Seed.VALUE)
        # -- egress --
        tmp = self.local("tmp", bit8)
        r.read(tmp, idx)
        self.assign(tmp, tmp + hdr.myhdr.value_to_add)
        r.write(idx, tmp)
        self.assign(hdr.myhdr.debug_last_reg_value_written, tmp)


class deparser(Deparser[Headers]):
    def apply(self) -> None:
        self.emit(self.hdr.myhdr)


def build() -> pb.Program:
    return assemble(
        BlockLibrary(p, pipeline, deparser, externs=[r, pkts]),
        name="stateful",
        headers=Headers,
        metadata=Meta,
        exports={"parser": p, "control": pipeline, "deparser": deparser},
    )


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
