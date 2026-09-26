"""Independent known answers for v1model stage boundaries and profile checks."""

from __future__ import annotations

import pytest

from p4blo.arch import v1model
from p4blo.arch.externs.counter import Counter
from p4blo.arch.loader import LoadError
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.program_v1model import assign, bits, block, path, program, read, run


def test_all_six_stages_preserve_order_and_payload() -> None:
    p = program()
    for number, role in enumerate(("verify_checksum", "ingress", "egress", "compute_checksum"), 1):
        doubled = pb.Expr(
            binary=pb.Binary(op=pb.BINARY_OP_MUL, left=read("hdr", "h", "value"), right=bits(8, 2))
        )
        block(p, role).body.append(
            assign(
                path("hdr", "h", "value"),
                pb.Expr(binary=pb.Binary(op=pb.BINARY_OP_ADD, left=doubled, right=bits(8, number))),
            )
        )
    assert run(p) == [(1, b"\x2apayload")]
    printed = v1model.print_program(p)
    assert (
        "V1Switch(Parser(), VerifyChecksum(), Ingress(), Egress(), ComputeChecksum(), Deparser())"
        in printed
    )


def test_later_ingress_assignment_undoes_drop() -> None:
    p = program()
    block(p, "ingress").body.insert(0, assign(path("meta", "egress_spec"), bits(9, 511)))
    assert run(p) == [(1, b"\x01payload")]


def test_egress_spec_cannot_redirect_selected_port() -> None:
    p = program()
    block(p, "egress").body.append(assign(path("meta", "egress_spec"), bits(9, 2)))
    block(p, "compute_checksum").body.append(
        assign(
            path("hdr", "h", "value"),
            pb.Expr(cast=pb.Cast(to=pb.Type(bits=8), operand=read("meta", "egress_port"))),
        )
    )
    assert run(p) == [(1, b"\x01payload")]


@pytest.mark.parametrize("role", ["ingress", "egress"])
def test_drop_suppresses_downstream_extern_effects(role: str) -> None:
    p = program()
    p.extern_types.add(
        name="counter",
        constructor_params=[
            pb.Param(name="size", type=pb.Type(bits=32), direction=pb.DIRECTION_IN)
        ],
        methods=[
            pb.Method(
                name="count",
                params=[pb.Param(name="index", type=pb.Type(bits=32), direction=pb.DIRECTION_IN)],
            )
        ],
    )
    p.extern_instances.add(
        name="observed",
        extern_type="counter",
        args=[pb.Literal(bits=pb.BitsLiteral(width=32, value="1"))],
    )
    block(p, role).body.append(assign(path("meta", "egress_spec"), bits(9, 511)))
    for downstream in ("egress", "compute_checksum", "deparser"):
        if downstream == role:
            continue
        block(p, downstream).body.append(
            pb.Stmt(
                call_extern=pb.CallExtern(
                    instance="observed", method="count", args=[pb.Arg(expr=bits(32, 0))]
                )
            )
        )
    loaded = v1model.load(p)
    assert v1model.V1Model(4).run(loaded, loaded.entries(), 0, b"\x01") == []
    counter = loaded.externs["observed"]
    assert isinstance(counter, Counter)
    assert counter.counts == [0]


@pytest.mark.parametrize(
    "role,field",
    [("parser", "parser_error"), ("verify_checksum", "ingress_port"), ("ingress", "egress_port")],
)
def test_unavailable_standard_metadata_reads_are_rejected(role: str, field: str) -> None:
    p = program()
    b = block(p, role)
    body = b.states[0].body if role == "parser" else b.body
    if field == "parser_error":
        value = pb.Expr(
            binary=pb.Binary(
                op=pb.BINARY_OP_EQ,
                left=read("meta", field),
                right=pb.Expr(literal=pb.Literal(error="NoError")),
            )
        )
        body.append(pb.Stmt(conditional=pb.If(condition=value)))
    else:
        body.append(assign(path("meta", "scratch"), read("meta", field)))
    with pytest.raises(LoadError, match="unavailable"):
        v1model.load(p)


@pytest.mark.parametrize(
    "role,field",
    [
        ("parser", "egress_spec"),
        ("verify_checksum", "egress_spec"),
        ("ingress", "ingress_port"),
        ("egress", "egress_port"),
        ("compute_checksum", "egress_spec"),
    ],
)
def test_protected_writes_are_rejected(role: str, field: str) -> None:
    p = program()
    b = block(p, role)
    body = b.states[0].body if role == "parser" else b.body
    body.append(assign(path("meta", field), bits(9, 1)))
    with pytest.raises(LoadError, match="read-only"):
        v1model.load(p)


@pytest.mark.parametrize("field", ["drop", "flood", "mcast_grp", "checksum_error"])
def test_unsupported_fields_are_rejected(field: str) -> None:
    p = program()
    p.struct_types[1].fields.add(name=field, type=pb.Type(bits=9))
    with pytest.raises(LoadError, match="unsupported v1model metadata"):
        v1model.load(p)


def test_nested_control_cannot_write_readonly_metadata() -> None:
    p = program()
    child = p.blocks.add(name="Child", kind=pb.BLOCK_KIND_CONTROL)
    child.params.add(name="m", type=pb.Type(struct="M"), direction=pb.DIRECTION_INOUT)
    child.body.append(assign(path("m", "egress_port"), bits(9, 2)))
    block(p, "ingress").body.append(
        pb.Stmt(call_block=pb.CallBlock(block="Child", args=[pb.Arg(lvalue=path("meta"))]))
    )
    with pytest.raises(LoadError, match="read-only"):
        v1model.load(p)
    child.body[0].assign.target.CopyFrom(path("m", "egress_spec"))
    assert run(p) == [(2, b"\x01payload")]


def test_whole_metadata_replacement_is_rejected() -> None:
    p = program()
    ingress = block(p, "ingress")
    ingress.locals.add(name="replacement", type=pb.Type(struct="M"))
    ingress.body.append(assign(path("meta"), read("replacement")))
    with pytest.raises(LoadError, match="whole metadata writes"):
        v1model.load(p)


def test_optional_egress_still_supplies_actual_port_to_compute() -> None:
    p = program()
    egress_export = next(e for e in p.exports if e.role == "egress")
    p.exports.remove(egress_export)
    block(p, "compute_checksum").body.append(
        assign(
            path("hdr", "h", "value"),
            pb.Expr(cast=pb.Cast(to=pb.Type(bits=8), operand=read("meta", "egress_port"))),
        )
    )
    assert run(p) == [(1, b"\x01payload")]
    printed = v1model.print_program(p)
    assert "control MyEgress" in printed
    assert "meta.egress_port = standard_metadata.egress_port;" in printed


def test_table_key_cannot_read_egress_port_before_selection() -> None:
    p = program()
    b = block(p, "ingress")
    b.actions.add(name="NoAction")
    b.tables.add(
        name="lookup",
        keys=[pb.Key(expr=read("meta", "egress_port"), match_kind=pb.MATCH_KIND_EXACT)],
        actions=["NoAction"],
        default_action=pb.ActionCall(action="NoAction"),
    )
    b.body.add(apply=pb.Apply(table="lookup"))
    with pytest.raises(LoadError, match="unavailable"):
        v1model.load(p)


def test_action_alias_cannot_overwrite_actual_port() -> None:
    p = program()
    b = block(p, "ingress")
    b.actions.add(
        name="overwrite",
        params=[pb.Param(name="port", type=pb.Type(bits=9), direction=pb.DIRECTION_INOUT)],
        body=[assign(path("port"), bits(9, 2))],
    )
    b.body.add(
        call_action=pb.CallAction(
            action="overwrite", args=[pb.Arg(lvalue=path("meta", "egress_port"))]
        )
    )
    with pytest.raises(LoadError, match="read-only"):
        v1model.load(p)
    b.body[-1].call_action.args[0].lvalue.CopyFrom(path("meta", "egress_spec"))
    assert run(p) == [(2, b"\x01payload")]


def test_one_block_cannot_supply_multiple_native_stage_interfaces() -> None:
    p = program()
    next(e for e in p.exports if e.role == "verify_checksum").block = block(
        p, "compute_checksum"
    ).name
    with pytest.raises(LoadError, match="distinct block"):
        v1model.load(p)


@pytest.mark.parametrize("kind", ["block", "action"])
def test_call_argument_index_cannot_read_unavailable_metadata(kind: str) -> None:
    p = program()
    p.struct_types[0].fields.add(
        name="stack", type=pb.Type(stack=pb.StackType(header="Byte", size=2))
    )
    param = pb.Param(name="h", type=pb.Type(header="Byte"), direction=pb.DIRECTION_INOUT)
    body = [assign(path("h", "value"), bits(8, 9))]
    arg = pb.Arg(
        lvalue=pb.LValue(
            index=pb.LIndex(base=path("hdr", "stack"), index=read("meta", "egress_port"))
        )
    )
    ingress = block(p, "ingress")
    if kind == "block":
        p.blocks.add(name="Child", kind=pb.BLOCK_KIND_CONTROL, params=[param], body=body)
        call = ingress.body.add(call_block=pb.CallBlock(block="Child", args=[arg])).call_block
    else:
        ingress.actions.add(name="child", params=[param], body=body)
        call = ingress.body.add(call_action=pb.CallAction(action="child", args=[arg])).call_action
    with pytest.raises(LoadError, match="unavailable"):
        v1model.load(p)
    call.args[0].lvalue.index.index.CopyFrom(read("meta", "ingress_port"))
    assert run(p) == [(1, b"\x01payload")]
