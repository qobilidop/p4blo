"""The const-entry priority program, authored in the eDSL: p4c's
`table-entries-priority-bmv2.p4`.

`build()` returns the same `pb.Program` that priority.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl import (
    Control,
    Deparser,
    Header,
    In,
    InOut,
    Out,
    Parser,
    Program,
    Struct,
    Table,
    Transition,
    action,
    bit8,
    bit9,
    bit16,
    entry,
    masked,
    state,
    ternary,
)
from p4blo.v0 import p4blo_pb2 as pb


class hdr(Header):
    e: bit8
    t: bit16
    l: bit8  # noqa: E741
    r: bit8
    v: bit8


class Header_t(Struct):
    h: hdr


# The source's `Meta_t` is empty; egress_port is `standard_meta.egress_spec`.
class Meta_t(Struct):
    egress_port: bit9


class p(Parser[Header_t, Meta_t]):
    h: Out[Header_t]
    meta: InOut[Meta_t]

    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.h.h)
        return self.accept


class ingress(Control[Header_t, Meta_t]):
    h: InOut[Header_t]
    meta: InOut[Meta_t]

    @action
    def a(self) -> None:
        self.assign(self.meta.egress_port, 0)

    @action
    def a_with_control_params(self, x: bit9) -> None:
        self.assign(self.meta.egress_port, x)

    # The source's entries, in its order, with p4c's priorities 3, 2, 1
    # (smaller wins) mapped to the IR's 1, 2, 3 (larger wins); see the
    # README.
    t_ternary = Table(
        keys=(ternary(Header_t.h.t),),
        actions=[a, a_with_control_params],
        default=a(),
        entries=[
            entry(masked(0x1111 & 0xF, 0xF), a_with_control_params(bit9(1)), priority=1),
            entry(0x1181, a_with_control_params(bit9(2)), priority=2),
            entry(masked(0x1181 & 0xF00F, 0xF00F), a_with_control_params(bit9(3)), priority=3),
        ],
    )

    def apply(self) -> None:
        self.apply_table(self.t_ternary)


class deparser(Deparser[Header_t]):
    h: In[Header_t]

    def apply(self) -> None:
        self.emit(self.h.h)


def build() -> pb.Program:
    return Program(
        "priority",
        headers=Header_t,
        metadata=Meta_t,
        parser=p,
        control=ingress,
        deparser=deparser,
    ).build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
