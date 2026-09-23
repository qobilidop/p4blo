"""The stateful program, authored in the eDSL.

`build()` returns the same `pb.Program` that stateful.txtpb encodes; the
test suite checks the two are equal. Run as a script to print the text
format.
"""

from __future__ import annotations

from p4blo.edsl.core import Program, bit
from p4blo.edsl.core.externs import counter, register
from p4blo.v0 import p4blo_pb2 as pb


def build() -> pb.Program:
    p = Program("stateful")

    myhdr_t = p.header(
        "myhdr_t",
        reg_idx_to_update=bit(8),
        value_to_add=bit(8),
        debug_last_reg_value_written=bit(8),
    )
    p.headers = p.struct("Headers", myhdr=myhdr_t)
    # The donor's `Meta` is empty. It declares no contract field, so the
    # switch reads egress_port as 0 and drop as false: every packet leaves
    # on port 0, as the vectors expect.
    p.metadata = p.struct("Meta")

    # register<bit<8>>(256) r; the one instance both halves of the pipeline
    # use. `counter(256, CounterType.packets) pkts` is our addition, counted
    # once per packet at the register's index; STF cannot observe it.
    r = p.extern_instance("r", register(p, bit(8)), 256)
    pkts = p.extern_instance("pkts", counter(p), 256)

    with p.parser("p") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.myhdr)
            s.accept()

    # The donor's `ingress` followed by its `egress`, as one control: the
    # architecture runs one control, and nothing happens between the two.
    with p.control("pipeline") as c:
        hdr = c.hdr
        with c.body() as b:
            idx = hdr.myhdr.reg_idx_to_update.cast(bit(32))
            # -- ingress --
            b.call(pkts, "count", idx)
            x = b.local("x", bit(8))
            b.call(r, "read", x, idx)
            # The donor writes 0x2a unconditionally and discards `x`. Seeding
            # only an untouched cell keeps its vectors and lets ours see the
            # value the previous packet left behind (README, "Added").
            with b.if_(x == 0):
                b.call(r, "write", idx, 0x2A)
            # -- egress --
            tmp = b.local("tmp", bit(8))
            b.call(r, "read", tmp, idx)
            b.assign(tmp, tmp + hdr.myhdr.value_to_add)
            b.call(r, "write", idx, tmp)
            b.assign(hdr.myhdr.debug_last_reg_value_written, tmp)

    with p.deparser("deparser") as d:
        with d.body() as b:
            b.emit(d.hdr.myhdr)

    p.export("parser", "p")
    p.export("control", "pipeline")
    p.export("deparser", "deparser")
    return p.build()


if __name__ == "__main__":
    from p4blo import ir

    print(ir.dump_text(build()), end="")
