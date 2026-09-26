"""Independent Python authoring of the six-stage native P4 acceptance witness."""

from p4blo import edsl as p4
from p4blo.arch import v1model
from p4blo.arch.externs.declarations import Register
from p4blo.arch.v0 import assembly_pb2 as apb


class Trace(p4.Header):
    trace: p4.bit32
    mode: p4.bit8
    port: p4.bit8
    e: p4.bit8
    c: p4.bit8
    d: p4.bit8


class Trailer(p4.Header):
    value: p4.bit8


class Headers(p4.Struct):
    h: Trace


class Metadata(p4.Struct):
    egress_spec: p4.bit9
    egress_port: p4.bit9


egress_count = Register[p4.bit8]("egress_count", size=1)
compute_count = Register[p4.bit8]("compute_count", size=1)
deparser_count = Register[p4.bit8]("deparser_count", size=1)


class Parse(p4.Parser[Headers, Metadata]):
    @p4.state(start=True)
    def start(self) -> p4.Transition:
        self.extract(self.hdr.h)
        self.assign(self.hdr.h.trace, 1)
        return self.accept


class Verify(p4.Control[Headers, Metadata]):
    def apply(self) -> None:
        self.assign(self.hdr.h.trace, (self.hdr.h.trace << 4) | 2)


class Ingress(p4.Control[Headers, Metadata]):
    def apply(self) -> None:
        self.assign(self.hdr.h.trace, (self.hdr.h.trace << 4) | 3)
        egress_count.read(self.hdr.h.e, 0)
        compute_count.read(self.hdr.h.c, 0)
        deparser_count.read(self.hdr.h.d, 0)
        self.assign(self.meta.egress_spec, 2)
        with self.if_(self.hdr.h.mode == 1):
            self.assign(self.meta.egress_spec, 511)
        with self.if_(self.hdr.h.mode == 3):
            self.assign(self.meta.egress_spec, 511)
            self.assign(self.meta.egress_spec, 2)


class Egress(p4.Control[Headers, Metadata]):
    n: p4.bit8

    def apply(self) -> None:
        self.assign(self.hdr.h.trace, (self.hdr.h.trace << 4) | 4)
        self.assign(self.hdr.h.port, self.meta.egress_port.cast(p4.bit8))
        egress_count.read(self.n, 0)
        egress_count.write(0, self.n + 1)
        with self.if_(self.hdr.h.mode == 2):
            self.assign(self.meta.egress_spec, 511)


class Compute(p4.Control[Headers, Metadata]):
    n: p4.bit8

    def apply(self) -> None:
        self.assign(self.hdr.h.trace, (self.hdr.h.trace << 4) | 5)
        compute_count.read(self.n, 0)
        compute_count.write(0, self.n + 1)


class Emit(p4.Deparser[Headers]):
    n: p4.bit8
    trailer: Trailer

    def apply(self) -> None:
        deparser_count.read(self.n, 0)
        deparser_count.write(0, self.n + 1)
        self.set_valid(self.trailer)
        self.assign(self.trailer.value, 6)
        self.emit(self.hdr)
        self.emit(self.trailer)


def stages() -> apb.BlockAssembly:
    blocks = p4.BlockLibrary(
        Parse,
        Verify,
        Ingress,
        Egress,
        Compute,
        Emit,
        externs=[egress_count, compute_count, deparser_count],
    )
    return v1model.assemble(
        blocks,
        name="v1model_stages",
        headers=Headers,
        metadata=Metadata,
        parser=Parse,
        verify_checksum=Verify,
        ingress=Ingress,
        egress=Egress,
        compute_checksum=Compute,
        deparser=Emit,
    )
