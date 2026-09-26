"""The parser-error program, authored in the eDSL: p4c's `parser_error-bmv2.p4`.

`build()` returns the same `apb.BlockAssembly` that parser_error.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.arch import assemble
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import (
    BlockLibrary,
    Control,
    CoreErrors,
    Deparser,
    Error,
    Header,
    Parser,
    Struct,
    Transition,
    bit9,
    bit16,
    bit48,
    state,
)


class Ethernet(Header):
    src: bit48
    dst: bit48
    type: bit16


class parsed_packet_t(Struct):
    eth: Ethernet


# The source's `local_metadata_t` is empty; the two intrinsic fields the
# program uses join it under the contract's names: parser_error, which
# the architecture provides, and egress_spec, which it consumes.
class local_metadata_t(Struct):
    parser_error: Error
    egress_spec: bit9


class parse(Parser[parsed_packet_t, local_metadata_t]):
    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.eth)
        return self.accept


class ingress(Control[parsed_packet_t, local_metadata_t]):
    def apply(self) -> None:
        with self.if_(self.meta.parser_error == CoreErrors.PacketTooShort):
            self.set_valid(self.hdr.eth)
            self.assign(self.hdr.eth.type, 0)
            self.assign(self.hdr.eth.src, 0)
            self.assign(self.hdr.eth.dst, 0)
        self.assign(self.meta.egress_spec, 0)


class deparser(Deparser[parsed_packet_t]):
    def apply(self) -> None:
        self.emit(self.hdr)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(parse, ingress, deparser),
        name="parser_error",
        headers=parsed_packet_t,
        metadata=local_metadata_t,
        exports={"parser": parse, "ingress": ingress, "deparser": deparser},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
