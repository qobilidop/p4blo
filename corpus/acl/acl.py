"""The ACL, authored in the eDSL: p4c's `ternary2-bmv2.p4`.

`build()` returns the same `pb.Program` that acl.txtpb encodes; the test
suite checks the two are equal. Run as a script to print the text format.
"""

from __future__ import annotations

from p4blo.edsl.core import Program, bit, masked, ternary
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("acl")

    data_h = p.header("data_h", f1=bit(32), f2=bit(32), h1=bit(16), b1=bit(8), b2=bit(8))
    extra_h = p.header("extra_h", h=bit(16), b1=bit(8), b2=bit(8))
    packet_t = p.struct("packet_t", data=data_h, extra=extra_h[4])
    # The source's `Meta` is empty; egress_port is `standard_metadata.egress_spec`,
    # the one intrinsic field the program writes, as the contract names it.
    meta_t = p.struct("Meta", egress_port=bit(9))
    p.headers = packet_t
    p.metadata = meta_t

    with p.parser("p", params=[("hdrs", "out", packet_t), ("meta", "inout", meta_t)]) as ps:
        hdrs = ps.hdrs
        with ps.state("start") as s:
            s.extract(hdrs.data)
            s.transition("extra")
        with ps.state("extra") as s:
            s.extract(hdrs.extra.next)
            # `hdrs.extra.last.b2` is `hdrs.extra[hdrs.extra.lastIndex].b2`.
            s.select(
                hdrs.extra[hdrs.extra.last_index].b2,
                {masked(0x80, 0x80): "extra"},
                default=ps.accept,
            )

    with p.control("ingress", params=[("hdrs", "inout", packet_t), ("meta", "inout", meta_t)]) as c:
        hdrs, meta = c.hdrs, c.meta
        # Which of ex1's actions ran: 0 for noop, the default; 1, 2, 3 for
        # act1, act2, act3; 4 for setbyte. This is `ex1.apply().action_run`.
        ex1_run = c.local("ex1_run", bit(8))

        with c.action("setb1", port=bit(9), val=bit(8)) as a:
            a.assign(hdrs.data.b1, a.val)
            a.assign(meta.egress_port, a.port)
        c.action("noop")
        # `setbyte(out bit<8> reg, bit<8> val)` bound to a different `reg` in
        # each table's action list, as one action per table, named as p4c's
        # frontend names them.
        with c.action("setbyte", val=bit(8)) as a:
            a.assign(hdrs.extra[0].b1, a.val)
            a.assign(ex1_run, 4)
        with c.action("setbyte_1", val=bit(8)) as a:
            a.assign(hdrs.data.b2, a.val)
        with c.action("setbyte_2", val=bit(8)) as a:
            a.assign(hdrs.extra[1].b1, a.val)
        with c.action("setbyte_3", val=bit(8)) as a:
            a.assign(hdrs.extra[2].b2, a.val)
        with c.action("act1", val=bit(8)) as a:
            a.assign(hdrs.extra[0].b1, a.val)
            a.assign(ex1_run, 1)
        with c.action("act2", val=bit(8)) as a:
            a.assign(hdrs.extra[0].b1, a.val)
            a.assign(ex1_run, 2)
        with c.action("act3", val=bit(8)) as a:
            a.assign(hdrs.extra[0].b1, a.val)
            a.assign(ex1_run, 3)

        # Key names are the ones p4c's STF uses, so the vectors read unchanged.
        test1 = c.table(
            "test1",
            keys=[ternary(hdrs.data.f1, name="data.f1")],
            actions=["setb1", "noop"],
            default="noop",
        )
        ex1 = c.table(
            "ex1",
            keys=[ternary(hdrs.extra[0].h, name="extra[0].h")],
            actions=["setbyte", "act1", "act2", "act3", "noop"],
            default="noop",
        )
        tbl1 = c.table(
            "tbl1",
            keys=[ternary(hdrs.data.f2, name="data.f2")],
            actions=["setbyte_1", "noop"],
            default="noop",
        )
        tbl2 = c.table(
            "tbl2",
            keys=[ternary(hdrs.data.f2, name="data.f2")],
            actions=["setbyte_2", "noop"],
            default="noop",
        )
        tbl3 = c.table(
            "tbl3",
            keys=[ternary(hdrs.data.f2, name="data.f2")],
            actions=["setbyte_3", "noop"],
            default="noop",
        )

        with c.body() as b:
            b.apply(test1)
            b.assign(ex1_run, 0)
            b.apply(ex1)
            with b.if_(ex1_run == 1):
                b.apply(tbl1)
            with b.else_():
                with b.if_(ex1_run == 2):
                    b.apply(tbl2)
                with b.else_():
                    with b.if_(ex1_run == 3):
                        b.apply(tbl3)

    with p.deparser("deparser", params=[("hdrs", "in", packet_t)]) as d:
        with d.body() as b:
            b.emit(d.hdrs.data)
            b.emit(d.hdrs.extra)

    p.export("parser", "p")
    p.export("control", "ingress")
    p.export("deparser", "deparser")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
