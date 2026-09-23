"""The Python eDSL: a builder for p4blo programs.

Plain constructors declare types, externs and blocks; operator overloading
builds expressions; control flow is explicit. The builder does the
elaboration the IR refuses to do, giving integer literals a width from
context and resolving field access to typed paths, and inserts nothing else:
every cast in the IR is one the user wrote.

    from p4blo.edsl.core import Program, bit, boolean, lpm

    p = Program("forwarder")
    ethernet_t = p.header("ethernet_t", dstAddr=bit(48), srcAddr=bit(48), etherType=bit(16))
    headers = p.struct("headers", ethernet=ethernet_t)
    metadata = p.struct("metadata", egress_port=bit(9), drop=boolean)
    p.headers, p.metadata = headers, metadata

    with p.parser("MyParser") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.ethernet)
            s.accept()

    with p.control("MyIngress") as c:
        with c.action("drop") as a:
            a.assign(c.meta.drop, True)
        t = c.table("t", keys=[lpm(c.hdr.ethernet.dstAddr)], actions=["drop"])
        with c.body() as b:
            with b.if_(c.hdr.ethernet.is_valid()):
                b.apply(t)

    program = p.build()  # a pb.Program
"""

from p4blo.edsl.core.blocks import (
    ACCEPT,
    REJECT,
    ActionBody,
    Block,
    Control,
    ControlBody,
    Deparser,
    DeparserBody,
    Entry,
    Key,
    Parser,
    StateBody,
    Stmts,
    Table,
    dont_care,
    entry,
    exact,
    lpm,
    masked,
    prefix,
    range_,
    ternary,
)
from p4blo.edsl.core.expr import EnumType, Errors, Expr, concat, mux
from p4blo.edsl.core.program import Program
from p4blo.edsl.core.types import (
    EdslError,
    ExternInstance,
    ExternType,
    HeaderType,
    StructType,
    bit,
    boolean,
    error_t,
    method,
)

__all__ = [
    "ACCEPT",
    "REJECT",
    "ActionBody",
    "Block",
    "Control",
    "ControlBody",
    "Deparser",
    "DeparserBody",
    "EdslError",
    "Entry",
    "EnumType",
    "Errors",
    "Expr",
    "ExternInstance",
    "ExternType",
    "HeaderType",
    "Key",
    "Parser",
    "Program",
    "StateBody",
    "Stmts",
    "StructType",
    "Table",
    "bit",
    "boolean",
    "concat",
    "dont_care",
    "entry",
    "error_t",
    "exact",
    "lpm",
    "masked",
    "method",
    "mux",
    "prefix",
    "range_",
    "ternary",
]
