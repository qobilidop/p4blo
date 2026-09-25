"""A sub-parser extracting into a header stack, authored in the eDSL.

p4c's `subparser-with-header-stack-bmv2.p4`: the first h2 header is
extracted by a sub-parser into `hdr.h2.next`, the rest by the top-level
parser, and the control records which slots ended up valid. `build()`
returns the same `apb.BlockAssembly` that subparser_stack.txtpb encodes; the test
suite checks the two are equal. Run as a script to print the text format.
"""

from __future__ import annotations

from enum import IntEnum

from p4blo.arch import assemble
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import (
    BlockLibrary,
    Control,
    Deparser,
    Error,
    Errors,
    Header,
    InOut,
    L,
    Out,
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
    the switch then delivers every packet to port 0, as the vector expects."""


class errors(Errors):
    BadHeaderType: Error


class HdrType(IntEnum):
    """The `hdr_type` byte of each header."""

    H1 = 1
    H2 = 2
    H3 = 3


class subParserImpl(Parser):
    """The sub-parser: one h2 header into the stack's next slot, and its
    next_hdr_type out to the caller. Its parameters are these two, not H
    and M."""

    hdr: InOut[headers]
    ret_next_hdr_type: Out[bit8]

    @state
    def start(self) -> Transition:
        self.extract(self.hdr.h2.next)
        last = self.hdr.h2.last
        self.verify(last.hdr_type == HdrType.H2, errors.BadHeaderType)
        self.assign(self.ret_next_hdr_type, last.next_hdr_type)
        return self.accept


class parserI(Parser[headers, metadata]):
    # The parser-scoped local, declared in the parser body as the source
    # declares it: a block local, zero once per parse. Declared inside a
    # state with `self.local`, it would be re-zeroed at every entry of
    # that state instead, as a P4 state-local is.
    my_next_hdr_type: bit8

    @state
    def start(self) -> Transition:
        self.extract(self.hdr.h1)
        self.verify(self.hdr.h1.hdr_type == HdrType.H1, errors.BadHeaderType)
        return self.select(
            self.hdr.h1.next_hdr_type,
            {HdrType.H2: self.parse_first_h2, HdrType.H3: self.parse_h3},
            default=self.accept,
        )

    @state
    def parse_first_h2(self) -> Transition:
        self.call(subParserImpl, self.hdr, self.my_next_hdr_type)
        return self.select(
            self.my_next_hdr_type,
            {HdrType.H2: self.parse_other_h2, HdrType.H3: self.parse_h3},
            default=self.accept,
        )

    @state
    def parse_other_h2(self) -> Transition:
        self.extract(self.hdr.h2.next)
        # `hdr.h2.last` is `hdr.h2[hdr.h2.lastIndex]`, which the eDSL writes.
        last = self.hdr.h2.last
        self.verify(last.hdr_type == HdrType.H2, errors.BadHeaderType)
        return self.select(
            last.next_hdr_type,
            {HdrType.H2: self.parse_other_h2, HdrType.H3: self.parse_h3},
            default=self.accept,
        )

    @state
    def parse_h3(self) -> Transition:
        self.extract(self.hdr.h3)
        self.verify(self.hdr.h3.hdr_type == HdrType.H3, errors.BadHeaderType)
        return self.accept


class cIngress(Control[headers, metadata]):
    def apply(self) -> None:
        hdr = self.hdr
        # Record the valid bits of every h2 slot in h1.h2_valid_bits, so
        # that the vector can check them.
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
        name="subparser_stack",
        headers=headers,
        metadata=metadata,
        exports={"parser": parserI, "control": cIngress, "deparser": DeparserI},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
