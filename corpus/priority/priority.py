"""The const-entry priority program, authored in the eDSL: p4c's
`table-entries-priority-bmv2.p4`.

`build()` returns the same `pb.Program` that priority.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl import Program, bit, entry, masked, ternary
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("priority")

    hdr = p.header("hdr", e=bit(8), t=bit(16), l=bit(8), r=bit(8), v=bit(8))
    header_t = p.struct("Header_t", h=hdr)
    # The source's `Meta_t` is empty; egress_port is `standard_meta.egress_spec`.
    meta_t = p.struct("Meta_t", egress_port=bit(9))
    p.headers = header_t
    p.metadata = meta_t

    with p.parser("p", params=[("h", "out", header_t), ("meta", "inout", meta_t)]) as ps:
        with ps.state("start") as s:
            s.extract(ps.h.h)
            s.accept()

    with p.control("ingress", params=[("h", "inout", header_t), ("meta", "inout", meta_t)]) as c:
        h, meta = c.h, c.meta
        with c.action("a") as a:
            a.assign(meta.egress_port, 0)
        with c.action("a_with_control_params", x=bit(9)) as a:
            a.assign(meta.egress_port, a.x)
        # The source's entries, in its order, with p4c's priorities 3, 2, 1
        # (smaller wins) mapped to the IR's 1, 2, 3 (larger wins); see the
        # README.
        t_ternary = c.table(
            "t_ternary",
            keys=[ternary(h.h.t)],
            actions=["a", "a_with_control_params"],
            default="a",
            const_entries=[
                entry(masked(0x1111 & 0xF, 0xF), ("a_with_control_params", 1), priority=1),
                entry(0x1181, ("a_with_control_params", 2), priority=2),
                entry(masked(0x1181 & 0xF00F, 0xF00F), ("a_with_control_params", 3), priority=3),
            ],
        )
        with c.body() as b:
            b.apply(t_ternary)

    with p.deparser("deparser", params=[("h", "in", header_t)]) as d:
        with d.body() as b:
            b.emit(d.h.h)

    p.export("parser", "p")
    p.export("control", "ingress")
    p.export("deparser", "deparser")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
