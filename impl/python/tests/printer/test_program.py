"""Printer output and golden equality without native tools.

Regenerate with P4BLO_UPDATE_GOLDENS=1 pytest impl/python/tests/printer/test_program.py.
"""

from __future__ import annotations

import pytest
from google.protobuf import text_format

from p4blo.arch import v1model, validator
from p4blo.arch.bindings import BoundIndex
from p4blo.printer import PrintError, print_expr, print_lvalue, print_stmt, print_type
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.printer import (
    GOLDENS,
    PORT_PARSER,
    check_golden,
    expr,
    golden_program,
    ir_text,
    program,
    stmt,
)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", [*GOLDENS, "forwarder", "port_parser"])
def test_golden_program_is_valid(name: str) -> None:
    assert validator.validate(golden_program(name)) == []


@pytest.mark.parametrize("name", [*GOLDENS, "forwarder", "port_parser"])
def test_golden(name: str) -> None:
    text = v1model.print_program(golden_program(name))
    check_golden(name, text)


def test_print_type() -> None:
    assert print_type(pb.Type(bits=9)) == "bit<9>"
    assert print_type(pb.Type(boolean=pb.BoolType())) == "bool"
    assert print_type(pb.Type(header="ethernet_t")) == "ethernet_t"
    assert print_type(pb.Type(struct="headers")) == "headers"
    assert print_type(pb.Type(enum_type="Color")) == "Color"
    assert print_type(pb.Type(error=pb.ErrorType())) == "error"
    assert print_type(pb.Type(stack=pb.StackType(header="tag_t", size=4))) == "tag_t[4]"
    with pytest.raises(PrintError):
        print_type(pb.Type())


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<8w255>", "8w255"),
        ("literal { boolean: true }", "true"),
        ('literal { error: "PacketTooShort" }', "error.PacketTooShort"),
        ('literal { enum_member { enum_type: "Color" member: "RED" } }', "Color.RED"),
        ("<hdr.eth.dst>", "hdr.eth.dst"),
        ("index { base { <hdr.tags> } index { <32w1> } }", "hdr.tags[32w1]"),
        ("last_index { stack { <hdr.tags> } }", "hdr.tags.lastIndex"),
        ("is_valid { header { <hdr.eth> } }", "hdr.eth.isValid()"),
        ('lookahead { type { header: "ethernet_t" } }', "packet.lookahead<ethernet_t>()"),
        ('slice { operand { var: "x" } hi: 7 lo: 4 }', "x[7:4]"),
        ('cast { to { bits: 16 } operand { var: "x" } }', "(bit<16>) x"),
        ('unary { op: UNARY_OP_NOT operand { var: "b" } }', "!b"),
        (
            "unary { op: UNARY_OP_NEGATE "
            'operand { unary { op: UNARY_OP_COMPLEMENT operand { var: "x" } } } }',
            "-(~x)",
        ),
        (
            'binary { op: BINARY_OP_ADD_SAT left { var: "a" } right { var: "b" } }',
            "a |+| b",
        ),
        (
            'mux { condition { var: "c" } then { var: "a" } otherwise { var: "b" } }',
            "c ? a : b",
        ),
    ],
)
def test_print_expr_leaves_and_operators(text: str, expected: str) -> None:
    assert print_expr(expr(text)) == expected


def test_print_expr_parenthesizes_every_compound_operand() -> None:
    # (a + b) * c == d ? x[3:0] : (bit<4>) (y << 8w1)
    e = expr(
        """
        mux {
          condition {
            binary {
              op: BINARY_OP_EQ
              left {
                binary {
                  op: BINARY_OP_MUL
                  left { binary { op: BINARY_OP_ADD left { var: "a" } right { var: "b" } } }
                  right { var: "c" }
                }
              }
              right { var: "d" }
            }
          }
          then { slice { operand { var: "x" } hi: 3 lo: 0 } }
          otherwise {
            cast {
              to { bits: 4 }
              operand { binary { op: BINARY_OP_SHL left { var: "y" } right { <8w1> } } }
            }
          }
        }
        """
    )
    assert print_expr(e) == "(((a + b) * c) == d) ? (x[3:0]) : ((bit<4>) (y << 8w1))"


def test_print_lvalue() -> None:
    lv = text_format.Parse(ir_text("next { stack { <hdr.tags> } }"), pb.LValue())
    assert print_lvalue(lv) == "hdr.tags.next"
    lv = text_format.Parse(ir_text("index { base { <hdr.tags> } index { <meta.i> } }"), pb.LValue())
    assert print_lvalue(lv) == "hdr.tags[meta.i]"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("assign { target { <meta.x> } value { <8w1> } }", "meta.x = 8w1;"),
        ('apply { table: "t" }', "t.apply();"),
        ('apply { table: "t" hit { var: "h" } }', "h = t.apply().hit;"),
        ('call_action { action: "a" args { expr { <8w1> } } }', "a(8w1);"),
        (
            'call_extern { instance: "r" method: "read" '
            'args { lvalue { var: "v" } } args { expr { <32w0> } } }',
            "r.read(v, 32w0);",
        ),
        (
            'call_extern { instance: "c" method: "compute" '
            'args { expr { var: "d" } } result { var: "v" } }',
            "v = c.compute(d);",
        ),
        ("set_valid { header { <hdr.eth> } }", "hdr.eth.setValid();"),
        ("set_invalid { header { <hdr.eth> } }", "hdr.eth.setInvalid();"),
        ("push { stack { <hdr.tags> } count: 2 }", "hdr.tags.push_front(2);"),
        ("pop { stack { <hdr.tags> } count: 1 }", "hdr.tags.pop_front(1);"),
        ("extract { target { next { stack { <hdr.tags> } } } }", "packet.extract(hdr.tags.next);"),
        ("advance { bits { <32w8> } }", "packet.advance(32w8);"),
        (
            'verify { condition { var: "ok" } error: "PacketTooShort" }',
            "verify(ok, error.PacketTooShort);",
        ),
        ("emit { value { <hdr.eth> } }", "packet.emit(hdr.eth);"),
        ('call_block { block: "Sub" args { lvalue { <hdr.eth> } } }', "Sub_inst.apply(hdr.eth);"),
    ],
)
def test_print_stmt(text: str, expected: str) -> None:
    assert print_stmt(stmt(text)) == expected


def test_print_stmt_conditional_nests_and_indents() -> None:
    s = stmt(
        """
        conditional {
          condition { var: "c" }
          then { assign { target { var: "x" } value { <8w1> } } }
          otherwise {
            conditional {
              condition { var: "d" }
              then { assign { target { var: "x" } value { <8w2> } } }
            }
          }
        }
        """
    )
    assert print_stmt(s, depth=1) == "\n".join(
        [
            "    if (c) {",
            "        x = 8w1;",
            "    } else {",
            "        if (d) {",
            "            x = 8w2;",
            "        }",
            "    }",
        ]
    )


def test_standard_metadata_binding_is_by_name() -> None:
    index = BoundIndex.build(golden_program("control_features"))
    prologue, epilogue = v1model.standard_metadata_binding(index, "m")
    assert prologue == [
        "m.ingress_port = standard_metadata.ingress_port;",
        "m.parser_error = standard_metadata.parser_error;",
        "m.egress_spec = standard_metadata.egress_spec;",
    ]
    assert epilogue == [
        "standard_metadata.egress_spec = m.egress_spec;",
    ]
    # The parser gets the field the architectures write before it runs, and
    # only that one: parser_error is set after the parser, and nothing is
    # consumed there.
    assert v1model.standard_metadata_binding(index, "m", "parser") == (
        ["m.ingress_port = standard_metadata.ingress_port;"],
        [],
    )
    index = BoundIndex.build(golden_program("bare"))
    assert v1model.standard_metadata_binding(index, "m") == ([], [])
    assert v1model.standard_metadata_binding(index, "m", "parser") == ([], [])
    assert v1model.standard_metadata_binding(index, "m", "deparser") == ([], [])
    with pytest.raises(PrintError, match="unknown"):
        v1model.standard_metadata_binding(index, "m", "unknown")


@pytest.mark.parametrize("start", ["start", "first"])
def test_the_parser_is_provided_ingress_port_before_it_runs(start: str) -> None:
    """The `start` variant is also the golden `port_parser`, which p4test
    typechecks; the `first` one checks the synthesized start state."""
    p = program(PORT_PARSER % (start, start))
    assert validator.validate(p) == []
    text = v1model.print_program(p)
    parser_text = text[text.index("parser P(") : text.index("control C(")]
    control_text = text[text.index("control C(") : text.index("control D(")]
    copy = "meta.ingress_port = standard_metadata.ingress_port;"
    # In the parser the copy is the first statement of `start`, so a
    # select on the port in the start state already sees it; the control
    # keeps its own copy, which reads the same value.
    assert f"state start {{\n        {copy}\n" in parser_text
    assert parser_text.count(copy) == 1
    assert "transition select(meta.ingress_port)" in parser_text
    assert control_text.count(copy) == 1
    assert "parser_error" not in parser_text
    loaded = v1model.load(p)
    pipeline = v1model.V1Model(ports=4)
    assert pipeline.run(loaded, loaded.entries(), 1, b"\x2apayload") == []
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x2apayload") == [(2, b"\x2apayload")]


def test_contract_field_with_the_wrong_type_is_refused() -> None:
    p = golden_program("control_features")
    egress_spec = next(f for f in p.struct_types[1].fields if f.name == "egress_spec")
    egress_spec.type.CopyFrom(pb.Type(bits=1))
    with pytest.raises(PrintError, match="egress_spec"):
        v1model.print_program(p)


def test_unknown_extern_family_is_refused() -> None:
    p = golden_program("externs")
    p.extern_types[0].name = "mystery"
    p.extern_instances[0].extern_type = "mystery"
    with pytest.raises(PrintError, match="mystery"):
        v1model.print_program(p)


def test_a_noaction_with_a_body_is_refused() -> None:
    """A declared NoAction runs its body on a miss in the IR; core.p4's is
    empty, so the shim can only elide the empty, parameterless one."""
    p = golden_program("control_features")
    control = p.blocks[1]
    no_action = next(a for a in control.actions if a.name == "NoAction")
    assert "action NoAction" not in v1model.print_program(p)
    no_action.body.add().CopyFrom(control.actions[1].body[0])  # meta.egress_spec = 511
    with pytest.raises(PrintError, match="NoAction with a body"):
        v1model.print_program(p)
    del no_action.body[:]
    no_action.params.add(name="port", type=pb.Type(bits=9))
    with pytest.raises(PrintError, match="NoAction with a body"):
        v1model.print_program(p)


def test_start_state_clash_is_refused() -> None:
    p = golden_program("parser_features")
    p.blocks[0].states[1].name = "start"
    with pytest.raises(PrintError, match="start"):
        v1model.print_program(p)


def test_extern_placement() -> None:
    text = v1model.print_program(golden_program("externs"))
    lines = text.splitlines()
    # Shared with a sub-control: top level. Used by one exported block: inside it.
    assert "counter(32w4, CounterType.packets) pkts;" in lines
    assert "    register<bit<16>>(32w16) last_seen;" in lines
    assert "checksum16" not in text
    assert (
        "        hash(meta.sum, HashAlgorithm.csum16, 16w0, "
        "{ hdr.eth.dst ++ hdr.eth.src }, 32w65536);" in lines
    )


def test_ternary_entries_print_by_descending_priority() -> None:
    text = v1model.print_program(golden_program("control_features"))
    twenty = text.index("priority = 20:")
    ten = text.index("priority = 10:")
    assert twenty < ten
    assert "largest_priority_wins = true;" in text
    assert "const entries" in text  # the lpm table keeps the const form


def test_missing_roles_get_empty_blocks() -> None:
    text = v1model.print_program(golden_program("bare"))
    assert "control MyIngress(inout H hdr, inout M meta, inout standard_metadata_t" in text
    assert "control MyDeparser(packet_out packet, in H hdr)" in text
    assert text.rstrip().endswith(
        "V1Switch(P(), MyVerifyChecksum(), MyIngress(), MyEgress(), "
        "MyComputeChecksum(), MyDeparser()) main;"
    )
