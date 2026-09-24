"""Typed bounded stateful IR contexts, executed by the ordinary interpreters.

Programs read one register cell, compute an update from packet data, optionally
write it, and count requests. Output exposes either the old cell or a read after
the writes; differential comparison also observes every extern cell. This module
constructs syntax and packets only, never computes expected state transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from p4blo.drt.programs import binary, bits, boolean, scalar_program
from p4blo.v0 import p4blo_pb2 as pb

WIDTHS = (8, 16, 32, 64)
UPDATE_OPS = (
    pb.BINARY_OP_ADD,
    pb.BINARY_OP_SUB,
    pb.BINARY_OP_ADD_SAT,
    pb.BINARY_OP_SUB_SAT,
    pb.BINARY_OP_BIT_XOR,
)
Condition = Literal["always", "nonzero", "old_lt_data"]
WriteOrder = Literal["computed", "computed_then_data", "data_then_computed"]


@dataclass(frozen=True)
class StatefulSpec:
    width: int
    register_size: int
    counter_size: int
    op: pb.BinaryOp
    condition: Condition = "always"
    write_order: WriteOrder = "computed"
    read_after_write: bool = True
    count_updates: bool = False

    def __post_init__(self) -> None:
        if self.width not in WIDTHS:
            raise ValueError("stateful widths must be 8, 16, 32, or 64")
        if not 1 <= self.register_size <= 4 or not 1 <= self.counter_size <= 4:
            raise ValueError("register and counter sizes must be between 1 and 4")
        if self.op not in UPDATE_OPS:
            raise ValueError("unsupported stateful update operator")
        if self.condition not in ("always", "nonzero", "old_lt_data"):
            raise ValueError("unsupported stateful condition")
        if self.write_order not in ("computed", "computed_then_data", "data_then_computed"):
            raise ValueError("unsupported stateful write order")


def _param(name: str, width: int, direction: pb.Direction) -> pb.Param:
    return pb.Param(name=name, type=pb.Type(bits=width), direction=direction)


def _header() -> pb.Expr:
    return pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field="result"))


def _field(name: str) -> pb.Expr:
    return pb.Expr(member=pb.Member(base=_header(), field=name))


def _header_target() -> pb.LValue:
    return pb.LValue(member=pb.LMember(base=pb.LValue(var="hdr"), field="result"))


def stateful_program(spec: StatefulSpec) -> pb.Program:
    """A full switch program, with all type/width choices explicit in `spec`."""
    program = scalar_program(bits(spec.width, 0), spec.width)
    program.name = "generated-stateful"
    header = program.header_types[0]
    header.ClearField("fields")
    for name, width in (("index", 8), ("data", spec.width), ("value", spec.width)):
        header.fields.add(name=name, type=pb.Type(bits=width))
    program.blocks[0].states[0].body.add(extract=pb.Extract(target=_header_target()))
    register = program.extern_types.add(
        name="register", constructor_params=[_param("size", 32, pb.DIRECTION_IN)]
    )
    register.methods.add(
        name="read",
        params=[
            _param("result", spec.width, pb.DIRECTION_OUT),
            _param("index", 32, pb.DIRECTION_IN),
        ],
    )
    register.methods.add(
        name="write",
        params=[_param("index", 32, pb.DIRECTION_IN), _param("value", spec.width, pb.DIRECTION_IN)],
    )
    counter = program.extern_types.add(
        name="counter", constructor_params=[_param("size", 32, pb.DIRECTION_IN)]
    )
    counter.methods.add(name="count", params=[_param("index", 32, pb.DIRECTION_IN)])
    for name, kind, size in (
        ("reg", "register", spec.register_size),
        ("ctr", "counter", spec.counter_size),
    ):
        program.extern_instances.add(
            name=name,
            extern_type=kind,
            args=[pb.Literal(bits=pb.BitsLiteral(width=32, value=str(size)))],
        )
    control = program.blocks[1]
    control.ClearField("body")
    for name in ("old", "updated"):
        control.locals.add(name=name, type=pb.Type(bits=spec.width))
    index = pb.Expr(cast=pb.Cast(to=pb.Type(bits=32), operand=_field("index")))
    old = pb.Expr(var="old")
    updated = pb.Expr(var="updated")

    def read(target: pb.LValue) -> pb.Stmt:
        return pb.Stmt(
            call_extern=pb.CallExtern(
                instance="reg", method="read", args=[pb.Arg(lvalue=target), pb.Arg(expr=index)]
            )
        )

    def write(value: pb.Expr) -> pb.Stmt:
        return pb.Stmt(
            call_extern=pb.CallExtern(
                instance="reg", method="write", args=[pb.Arg(expr=index), pb.Arg(expr=value)]
            )
        )

    count = pb.Stmt(
        call_extern=pb.CallExtern(instance="ctr", method="count", args=[pb.Arg(expr=index)])
    )
    control.body.extend(
        [
            read(pb.LValue(var="old")),
            pb.Stmt(
                assign=pb.Assign(
                    target=pb.LValue(var="updated"), value=binary(spec.op, old, _field("data"))
                )
            ),
            count,
        ]
    )
    condition = boolean(True)
    if spec.condition == "nonzero":
        condition = binary(pb.BINARY_OP_NE, _field("data"), bits(spec.width, 0))
    elif spec.condition == "old_lt_data":
        condition = binary(pb.BINARY_OP_LT, old, _field("data"))
    writes = [write(updated)]
    if spec.write_order == "computed_then_data":
        writes.append(write(_field("data")))
    elif spec.write_order == "data_then_computed":
        writes.insert(0, write(_field("data")))
    if spec.count_updates:
        writes.append(count)
    control.body.add(conditional=pb.If(condition=condition, **{"then": writes}))
    target = pb.LValue(member=pb.LMember(base=_header_target(), field="value"))
    control.body.append(
        read(target)
        if spec.read_after_write
        else pb.Stmt(assign=pb.Assign(target=target, value=old))
    )
    return program


def packet(spec: StatefulSpec, index: int, data: int) -> bytes:
    """Encode a complete parser header with an initially zero result field."""
    if not 0 <= index < 256 or not 0 <= data < 1 << spec.width:
        raise ValueError("packet fields must fit their declared widths")
    size = spec.width // 8
    return bytes([index]) + data.to_bytes(size, "big") + bytes(size)
