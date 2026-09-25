"""A single-tag VLAN access gateway, built with the typed Python eDSL."""

from __future__ import annotations

from p4blo import edsl as p4
from p4blo.arch import assemble
from p4blo.arch.externs.declarations import Counter
from p4blo.v0 import p4blo_pb2 as pb


class Ethernet(p4.Header):
    dst: p4.bit48
    src: p4.bit48
    ether_type: p4.bit16


class Vlan(p4.Header):
    pcp: p4.bit3
    dei: p4.bit1
    vid: p4.bit12
    ether_type: p4.bit16


class Headers(p4.Struct):
    ethernet: Ethernet
    vlan: Vlan


class Metadata(p4.Struct):
    ingress_port: p4.bit9
    egress_port: p4.bit9
    drop: p4.Bool


class Parse(p4.Parser[Headers, Metadata]):
    @p4.state(start=True)
    def start(self) -> p4.Transition:
        self.extract(self.hdr.ethernet)
        return self.select(
            self.hdr.ethernet.ether_type,
            {0x8100: self.tagged},
            default=self.accept,
        )

    @p4.state
    def tagged(self) -> p4.Transition:
        self.extract(self.hdr.vlan)
        return self.accept


admissions = Counter("admissions", size=512)


class Gateway(p4.Control[Headers, Metadata]):
    @p4.action
    def deny(self) -> None:
        self.assign(self.meta.drop, True)

    @p4.action
    def deliver(self, port: p4.bit9) -> None:
        self.assign(self.meta.egress_port, port)
        self.assign(self.hdr.ethernet.ether_type, self.hdr.vlan.ether_type)
        self.set_invalid(self.hdr.vlan)
        admissions.count(port.cast(p4.bit32))
        self.assign(self.meta.drop, False)

    access = p4.Table(
        keys=(
            p4.exact(Metadata.ingress_port),
            p4.exact(Headers.vlan.vid),
            p4.exact(Headers.ethernet.dst),
        ),
        actions=[deliver, deny],
        default=deny(),
        size=1024,
    )

    def apply(self) -> None:
        self.assign(self.meta.drop, True)
        vlan = self.hdr.vlan
        with self.if_(
            vlan.is_valid()
            & (vlan.vid > 0)
            & (vlan.vid < 4095)
            & (vlan.ether_type != 0x8100)
            & (vlan.ether_type != 0x88A8)
        ):
            self.apply_table(self.access)


class Emit(p4.Deparser[Headers]):
    def apply(self) -> None:
        self.emit(self.hdr.ethernet)
        self.emit(self.hdr.vlan)


def build() -> pb.Program:
    return assemble(
        p4.BlockLibrary(Parse, Gateway, Emit, externs=[admissions]),
        name="vlan_gateway",
        headers=Headers,
        metadata=Metadata,
        exports={"parser": Parse, "control": Gateway, "deparser": Emit},
    )


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
