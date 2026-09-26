"""Small six-stage IR fixture shared by unit and program checks."""

from p4blo import ir
from p4blo.arch import v1model
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb


def bits(width: int, value: int) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=width, value=str(value))))


def path(root: str, *fields: str) -> pb.LValue:
    result = pb.LValue(var=root)
    for name in fields:
        result = pb.LValue(member=pb.LMember(base=result, field=name))
    return result


def read(root: str, *fields: str) -> pb.Expr:
    result = pb.Expr(var=root)
    for name in fields:
        result = pb.Expr(member=pb.Member(base=result, field=name))
    return result


def assign(target: pb.LValue, value: pb.Expr) -> pb.Stmt:
    return pb.Stmt(assign=pb.Assign(target=target, value=value))


def program() -> apb.BlockAssembly:
    p = apb.BlockAssembly(name="stages", headers="H", metadata="M", errors=ir.CORE_ERRORS)
    p.header_types.add(name="Byte", fields=[pb.Field(name="value", type=pb.Type(bits=8))])
    p.struct_types.add(name="H", fields=[pb.Field(name="h", type=pb.Type(header="Byte"))])
    p.struct_types.add(
        name="M",
        fields=[
            pb.Field(name="ingress_port", type=pb.Type(bits=9)),
            pb.Field(name="parser_error", type=pb.Type(error=pb.ErrorType())),
            pb.Field(name="egress_spec", type=pb.Type(bits=9)),
            pb.Field(name="egress_port", type=pb.Type(bits=9)),
            pb.Field(name="scratch", type=pb.Type(bits=9)),
        ],
    )
    for role, kind in v1model.ROLE_KINDS.items():
        block = p.blocks.add(name=role.title().replace("_", ""), kind=kind)
        block.params.add(
            name="hdr",
            type=pb.Type(struct="H"),
            direction=(
                pb.DIRECTION_OUT
                if role == "parser"
                else pb.DIRECTION_IN
                if role == "deparser"
                else pb.DIRECTION_INOUT
            ),
        )
        if role != "deparser":
            block.params.add(name="meta", type=pb.Type(struct="M"), direction=pb.DIRECTION_INOUT)
        if role == "parser":
            block.start_state = "start"
            block.states.add(
                name="start",
                body=[pb.Stmt(extract=pb.Extract(target=path("hdr", "h")))],
                transition=pb.Transition(direct=pb.Target(accept=pb.Accept())),
            )
        elif role == "deparser":
            block.body.add(emit=pb.Emit(value=read("hdr", "h")))
        elif role == "ingress":
            block.body.append(assign(path("meta", "egress_spec"), bits(9, 1)))
        p.exports.add(role=role, block=block.name)
    return p


def block(p: apb.BlockAssembly, role: str) -> pb.Block:
    name = next(e.block for e in p.exports if e.role == role)
    return next(b for b in p.blocks if b.name == name)


def run(p: apb.BlockAssembly) -> list[tuple[int, bytes]]:
    loaded = v1model.load(p)
    return v1model.V1Model(ports=4).run(loaded, loaded.entries(), 0, b"\x01payload")
