"""The const-entry priority program, authored in the eDSL: p4c's
`table-entries-priority-bmv2.p4`.

`build()` returns the same `apb.BlockAssembly` that priority.txtpb encodes; the
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
    Deparser,
    Header,
    In,
    InOut,
    Out,
    Parser,
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


class hdr(Header):
    e: bit8
    t: bit16
    l: bit8  # noqa: E741
    r: bit8
    v: bit8


class Header_t(Struct):
    h: hdr


# The source's `Meta_t` is empty; egress_spec is `standard_meta.egress_spec`.
class Meta_t(Struct):
    egress_spec: bit9


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
        self.assign(self.meta.egress_spec, 0)

    @action
    def a_with_control_params(self, x: bit9) -> None:
        self.assign(self.meta.egress_spec, x)

    # The source's entries, in its order, with the priorities the language
    # specification gives them (larger wins). `@priority` is p4c's
    # annotation, not the language's `priority =`, so no entry has one and
    # the three are numbered by position, 3, 2, 1; see the README.
    t_ternary = Table(
        keys=(ternary(Header_t.h.t),),
        actions=[a, a_with_control_params],
        default=a(),
        entries=[
            entry(masked(0x1111 & 0xF, 0xF), a_with_control_params(bit9(1)), priority=3),
            entry(0x1181, a_with_control_params(bit9(2)), priority=2),
            entry(masked(0x1181 & 0xF00F, 0xF00F), a_with_control_params(bit9(3)), priority=1),
        ],
    )

    def apply(self) -> None:
        self.apply_table(self.t_ternary)


class deparser(Deparser[Header_t]):
    h: In[Header_t]

    def apply(self) -> None:
        self.emit(self.h.h)


def build() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(p, ingress, deparser),
        name="priority",
        headers=Header_t,
        metadata=Meta_t,
        exports={"parser": p, "ingress": ingress, "deparser": deparser},
    )


if __name__ == "__main__":
    print(arch_wire.dump_text(build()), end="")
