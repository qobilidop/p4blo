"""The csum16 program, authored in the eDSL.

`build()` returns the same `apb.BlockAssembly` that csum16.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.arch import assemble
from p4blo.arch import wire as arch_wire
from p4blo.arch.externs.declarations import Checksum16
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import (
    BlockLibrary,
    Control,
    Deparser,
    Header,
    Parser,
    Struct,
    Transition,
    bit16,
    state,
)


class H(Header):
    d: bit16
    c: bit16


class Parsed_packet(Struct):
    h: H


class Metadata(Struct):
    """The donor's `Metadata` is empty: no contract field, so every packet
    leaves on port 0 undropped, as the vectors expect."""


# v1model's `update_checksum(true, { hdr.h.d }, hdr.h.c, HashAlgorithm.
# csum16)` is a checksum16 instance over the 16 bits of the field list,
# called at the end of the control.
csum = Checksum16[bit16]("csum")


class parserI(Parser[Parsed_packet, Metadata]):
    @state
    def start(self) -> Transition:
        self.extract(self.hdr.h)
        return self.accept


class cIngress(Control[Parsed_packet, Metadata]):
    """The donor's `cIngress`, then its `uc` (the update-checksum control);
    `cEgress` is empty and `vc` (verify_checksum) is deferred."""

    def apply(self) -> None:
        hdr = self.hdr
        self.assign(hdr.h.d, hdr.h.d + 1)
        self.assign(hdr.h.c, csum.compute(hdr.h.d))


class DeparserI(Deparser[Parsed_packet]):
    def apply(self) -> None:
        self.emit(self.hdr.h)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(parserI, cIngress, DeparserI, externs=[csum]),
        name="csum16",
        headers=Parsed_packet,
        metadata=Metadata,
        exports={"parser": parserI, "control": cIngress, "deparser": DeparserI},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
