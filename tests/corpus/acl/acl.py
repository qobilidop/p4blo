"""The ACL, authored in the eDSL: p4c's `ternary2-bmv2.p4`.

`build()` returns the same `apb.BlockAssembly` that acl.txtpb encodes; the test
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
    Header,
    In,
    InOut,
    L,
    Out,
    Parser,
    Stack,
    Struct,
    Table,
    Transition,
    action,
    bit8,
    bit9,
    bit16,
    bit32,
    masked,
    state,
    ternary,
)


class data_h(Header):
    f1: bit32
    f2: bit32
    h1: bit16
    b1: bit8
    b2: bit8


class extra_h(Header):
    h: bit16
    b1: bit8
    b2: bit8


class packet_t(Struct):
    data: data_h
    extra: Stack[extra_h, L[4]]


# The source's `Meta` is empty; egress_spec is `standard_metadata.egress_spec`,
# the one intrinsic field the program writes, as the contract names it.
class Meta(Struct):
    egress_spec: bit9


class ExtraB2(IntEnum):
    """The top bit of `extra_h.b2`: set when another `extra_h` follows."""

    MORE = 0x80


class Ex1Run(IntEnum):
    """Which of ex1's actions ran: `ex1.apply().action_run` as a local."""

    NOOP = 0
    ACT1 = 1
    ACT2 = 2
    ACT3 = 3
    SETBYTE = 4


class p(Parser[packet_t, Meta]):
    hdrs: Out[packet_t]
    meta: InOut[Meta]

    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdrs.data)
        return self.goto(self.extra)

    @state
    def extra(self) -> Transition:
        self.extract(self.hdrs.extra.next)
        # `hdrs.extra.last.b2` is `hdrs.extra[hdrs.extra.lastIndex].b2`.
        return self.select(
            self.hdrs.extra.last.b2,
            {masked(ExtraB2.MORE, ExtraB2.MORE): self.extra},
            default=self.accept,
        )


class ingress(Control[packet_t, Meta]):
    hdrs: InOut[packet_t]
    meta: InOut[Meta]
    # Which of ex1's actions ran: 0 for noop, the default; 1, 2, 3 for
    # act1, act2, act3; 4 for setbyte. This is `ex1.apply().action_run`.
    ex1_run: bit8

    @action
    def setb1(self, port: bit9, val: bit8) -> None:
        self.assign(self.hdrs.data.b1, val)
        self.assign(self.meta.egress_spec, port)

    @action
    def noop(self) -> None:
        pass

    # `setbyte(out bit<8> reg, bit<8> val)` bound to a different `reg` in
    # each table's action list, as one action per table, named as p4c's
    # frontend names them.
    @action
    def setbyte(self, val: bit8) -> None:
        self.assign(self.hdrs.extra[0].b1, val)
        self.assign(self.ex1_run, Ex1Run.SETBYTE)

    @action
    def setbyte_1(self, val: bit8) -> None:
        self.assign(self.hdrs.data.b2, val)

    @action
    def setbyte_2(self, val: bit8) -> None:
        self.assign(self.hdrs.extra[1].b1, val)

    @action
    def setbyte_3(self, val: bit8) -> None:
        self.assign(self.hdrs.extra[2].b2, val)

    @action
    def act1(self, val: bit8) -> None:
        self.assign(self.hdrs.extra[0].b1, val)
        self.assign(self.ex1_run, Ex1Run.ACT1)

    @action
    def act2(self, val: bit8) -> None:
        self.assign(self.hdrs.extra[0].b1, val)
        self.assign(self.ex1_run, Ex1Run.ACT2)

    @action
    def act3(self, val: bit8) -> None:
        self.assign(self.hdrs.extra[0].b1, val)
        self.assign(self.ex1_run, Ex1Run.ACT3)

    # Key names are the ones p4c's STF uses, so the vectors read unchanged.
    test1 = Table(
        keys=(ternary(packet_t.data.f1, name="data.f1"),),
        actions=[setb1, noop],
        default=noop(),
    )
    ex1 = Table(
        keys=(ternary(packet_t.extra[0].h, name="extra[0].h"),),
        actions=[setbyte, act1, act2, act3, noop],
        default=noop(),
    )
    tbl1 = Table(
        keys=(ternary(packet_t.data.f2, name="data.f2"),),
        actions=[setbyte_1, noop],
        default=noop(),
    )
    tbl2 = Table(
        keys=(ternary(packet_t.data.f2, name="data.f2"),),
        actions=[setbyte_2, noop],
        default=noop(),
    )
    tbl3 = Table(
        keys=(ternary(packet_t.data.f2, name="data.f2"),),
        actions=[setbyte_3, noop],
        default=noop(),
    )

    def apply(self) -> None:
        self.apply_table(self.test1)
        self.assign(self.ex1_run, Ex1Run.NOOP)
        self.apply_table(self.ex1)
        with self.if_(self.ex1_run == Ex1Run.ACT1):
            self.apply_table(self.tbl1)
        with self.elif_(self.ex1_run == Ex1Run.ACT2):
            self.apply_table(self.tbl2)
        with self.elif_(self.ex1_run == Ex1Run.ACT3):
            self.apply_table(self.tbl3)


class deparser(Deparser[packet_t]):
    hdrs: In[packet_t]

    def apply(self) -> None:
        self.emit(self.hdrs.data)
        self.emit(self.hdrs.extra)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(p, ingress, deparser),
        name="acl",
        headers=packet_t,
        metadata=Meta,
        exports={"parser": p, "ingress": ingress, "deparser": deparser},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
