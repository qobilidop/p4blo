"""The register_bounds program, authored in the eDSL.

`build()` returns the same `apb.BlockAssembly` that register_bounds.txtpb encodes;
the test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.arch import assemble
from p4blo.arch import wire as arch_wire
from p4blo.arch.externs.declarations import Register
from p4blo.arch.v0 import assembly_pb2 as apb
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


# idx picks the cell, val is added to it, got reports what the cell
# holds afterwards; the packet is the whole header.
class h_t(Header):
    idx: bit8
    val: bit8
    got: bit8


class headers(Struct):
    h: h_t


# No contract field: every packet leaves on port 0 (README).
class metadata(Struct):
    pass


# Four cells indexed by an 8-bit field: 252 of the 256 indices a packet
# can name lie beyond the end.
r = Register[bit8]("r", size=4)


class P(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.h)
        return self.accept


class C(Control[headers, metadata]):
    x: bit8

    def apply(self) -> None:
        i = self.hdr.h.idx.cast(bit32)
        r.read(self.x, i)
        r.write(i, self.x + self.hdr.h.val)
        # Read back what the write left: the sum in range, zero beyond
        # the end, where the write was ignored.
        r.read(self.hdr.h.got, i)


class D(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.h)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(P, C, D, externs=[r]),
        name="register_bounds",
        headers=headers,
        metadata=metadata,
        exports={"parser": P, "ingress": C, "deparser": D},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
