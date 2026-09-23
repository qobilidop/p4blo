"""The verify-error program, authored in the eDSL: p4c's `issue1824-bmv2.p4`.

`build()` returns the same `pb.Program` that verify_error.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from enum import IntEnum

from p4blo.edsl import (
    Control,
    CoreErrors,
    Deparser,
    Error,
    Errors,
    Header,
    Parser,
    Program,
    Struct,
    Transition,
    bit4,
    bit48,
    state,
)
from p4blo.v0 import p4blo_pb2 as pb


class test_header(Header):
    dstAddr: bit48
    srcAddr: bit48


class headers(Struct):
    h1: test_header


class mystruct1_t(Struct):
    a: bit4
    b: bit4


# The source's metadata, plus parser_error from standard_metadata under
# the contract's name. The program never sets egress_spec, so no
# egress_port: the architecture sends to port 0.
class metadata(Struct):
    mystruct1: mystruct1_t
    parser_error: Error


# The program's own errors, declared after core.p4's seven.
class errors(Errors):
    IPv4OptionsNotSupported: Error
    IPv4ChecksumError: Error
    IPv4HeaderTooShort: Error
    IPv4BadPacket: Error


class DstAddr(IntEnum):
    """The marker the control writes when the parser rejected."""

    BAD = 0xBAD


class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.h1)
        self.verify(False, errors.IPv4BadPacket)
        self.verify(False, errors.IPv4HeaderTooShort)
        return self.accept


class MyIngress(Control[headers, metadata]):
    def apply(self) -> None:
        with self.if_(self.meta.parser_error != CoreErrors.NoError):
            self.assign(self.hdr.h1.dstAddr, DstAddr.BAD)


class MyDeparser(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.h1)


def build() -> pb.Program:
    return Program(
        "verify_error",
        headers=headers,
        metadata=metadata,
        errors=errors,
        parser=MyParser,
        control=MyIngress,
        deparser=MyDeparser,
    ).build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
