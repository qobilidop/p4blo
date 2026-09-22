"""One valid program, then one malformed program per rule.

`VALID` exercises every construct the validator knows; each test below takes
a fresh copy, breaks one thing, and asserts the code that names the break.
The corpus programs must validate too.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from google.protobuf import text_format

from p4blo import ir
from p4blo import validator as v
from p4blo.v0 import p4blo_pb2 as pb

# Block indices in VALID.
PRS, ING, SUB, DEP = 0, 1, 2, 3
# State indices in the parser.
START, PARSE_VLAN, PARSE_IPV4 = 0, 1, 2

VALID = """
name: "valid"
errors: "NoError"
errors: "PacketTooShort"
errors: "NoMatch"
errors: "StackOutOfBounds"
errors: "HeaderTooShort"
errors: "ParserTimeout"
errors: "ParserInvalidArgument"
errors: "BadVersion"

header_types {
  name: "eth"
  fields { name: "dst" type { bits: 48 } }
  fields { name: "src" type { bits: 48 } }
  fields { name: "type" type { bits: 16 } }
}
header_types {
  name: "ipv4"
  fields { name: "ver" type { bits: 4 } }
  fields { name: "ttl" type { bits: 8 } }
  fields { name: "proto" type { bits: 8 } }
  fields { name: "src" type { bits: 32 } }
  fields { name: "dst" type { bits: 32 } }
}
header_types {
  name: "vlan"
  fields { name: "pcp" type { bits: 3 } }
  fields { name: "cfi" type { boolean {} } }
  fields { name: "vid" type { bits: 12 } }
  fields { name: "type" type { bits: 16 } }
}
struct_types {
  name: "H"
  fields { name: "eth" type { header: "eth" } }
  fields { name: "vlan" type { stack { header: "vlan" size: 2 } } }
  fields { name: "ipv4" type { header: "ipv4" } }
}
struct_types {
  name: "M"
  fields { name: "port" type { bits: 9 } }
  fields { name: "drop" type { boolean {} } }
  fields { name: "color" type { enum_type: "Color" } }
}
enum_types { name: "Color" members: "RED" members: "GREEN" }

extern_types {
  name: "Counter"
  constructor_params { name: "size" type { bits: 32 } direction: DIRECTION_IN }
  methods {
    name: "count"
    params { name: "idx" type { bits: 32 } direction: DIRECTION_IN }
  }
  methods {
    name: "read"
    params { name: "idx" type { bits: 32 } direction: DIRECTION_IN }
    params { name: "value" type { bits: 32 } direction: DIRECTION_OUT }
  }
  methods { name: "size" returns { bits: 32 } }
}
extern_instances {
  name: "ctr" extern_type: "Counter" args { bits { width: 32 value: "1024" } }
}

headers: "H"
metadata: "M"

blocks {
  name: "prs" kind: BLOCK_KIND_PARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  locals { name: "tmp" type { bits: 16 } }
  start_state: "start"
  states {
    name: "start"
    body { extract { target { member { base { var: "hdr" } field: "eth" } } } }
    transition { select {
      keys { member { base { member { base { var: "hdr" } field: "eth" } } field: "type" } }
      cases {
        sets { exact { bits { width: 16 value: "2048" } } }
        target { state: "parse_ipv4" }
      }
      cases {
        sets { masked {
          value { bits { width: 16 value: "33024" } }
          mask { bits { width: 16 value: "65535" } }
        } }
        target { state: "parse_vlan" }
      }
      cases {
        sets { range {
          lo { bits { width: 16 value: "36864" } }
          hi { bits { width: 16 value: "40959" } }
        } }
        target { accept {} }
      }
      cases { sets { dont_care {} } target { accept {} } }
    } }
  }
  states {
    name: "parse_vlan"
    body { extract { target { next { stack { member { base { var: "hdr" } field: "vlan" } } } } } }
    body { assign { target { var: "tmp" } value { lookahead { type { bits: 16 } } } } }
    body { advance { bits { literal { bits { width: 32 value: "0" } } } } }
    transition { select {
      keys { var: "tmp" }
      cases { sets { exact { bits { width: 16 value: "33024" } } } target { state: "parse_vlan" } }
      cases { sets { exact { bits { width: 16 value: "2048" } } } target { state: "parse_ipv4" } }
      cases { sets { dont_care {} } target { reject {} } }
    } }
  }
  states {
    name: "parse_ipv4"
    body { extract { target { member { base { var: "hdr" } field: "ipv4" } } } }
    body { verify {
      condition { binary {
        op: BINARY_OP_EQ
        left { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "ver" } }
        right { literal { bits { width: 4 value: "4" } } }
      } }
      error: "BadVersion"
    } }
    transition { direct { accept {} } }
  }
}

blocks {
  name: "ing" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  locals { name: "hit" type { boolean {} } }
  locals { name: "idx" type { bits: 32 } }
  locals { name: "val" type { bits: 32 } }
  locals { name: "t16" type { bits: 16 } }
  actions {
    name: "drop"
    body { assign {
      target { member { base { var: "meta" } field: "drop" } }
      value { literal { boolean: true } }
    } }
  }
  actions {
    name: "fwd"
    params { name: "port" type { bits: 9 } direction: DIRECTION_NONE }
    params { name: "dec" type { bits: 8 } direction: DIRECTION_NONE }
    body { assign {
      target { member { base { var: "meta" } field: "port" } } value { var: "port" }
    } }
    body { assign {
      target { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "ttl" } }
      value { binary {
        op: BINARY_OP_SUB
        left { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "ttl" } }
        right { var: "dec" }
      } }
    } }
  }
  tables {
    name: "route"
    keys {
      expr { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "dst" } }
      match_kind: MATCH_KIND_LPM
      name: "dst"
    }
    actions: "drop"
    actions: "fwd"
    default_action { action: "drop" }
    const_entries {
      keys { lpm { value: "167772160" prefix_len: 8 } }
      action {
        action: "fwd"
        args { bits { width: 9 value: "1" } }
        args { bits { width: 8 value: "1" } }
      }
    }
    size: 1024
  }
  # 0: if with apply and call_action
  body { conditional {
    condition { is_valid { header { member { base { var: "hdr" } field: "ipv4" } } } }
    then { apply { table: "route" hit { var: "hit" } } }
    otherwise { call_action { action: "drop" } }
  } }
  # 1: mux over enum literals
  body { assign {
    target { member { base { var: "meta" } field: "color" } }
    value { mux {
      condition { var: "hit" }
      then { literal { enum_member { enum_type: "Color" member: "RED" } } }
      otherwise { literal { enum_member { enum_type: "Color" member: "GREEN" } } }
    } }
  } }
  # 2: cast of a slice
  body { assign {
    target { var: "idx" }
    value { cast {
      to { bits: 32 }
      operand { slice {
        operand { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "dst" } }
        hi: 7 lo: 0
      } }
    } }
  } }
  # 3-5: extern calls: in arg, out arg, result
  body { call_extern { instance: "ctr" method: "count" args { expr { var: "idx" } } } }
  body { call_extern {
    instance: "ctr" method: "read" args { expr { var: "idx" } } args { lvalue { var: "val" } }
  } }
  body { call_extern { instance: "ctr" method: "size" result { var: "val" } } }
  # 6-9: stack push, indexed write, lastIndex, setValid
  body { push { stack { member { base { var: "hdr" } field: "vlan" } } count: 1 } }
  body { assign {
    target { member {
      base { index {
        base { member { base { var: "hdr" } field: "vlan" } }
        index { literal { bits { width: 32 value: "0" } } }
      } }
      field: "vid"
    } }
    value { cast { to { bits: 12 } operand { var: "idx" } } }
  } }
  body { assign {
    target { var: "idx" }
    value { last_index { stack { member { base { var: "hdr" } field: "vlan" } } } }
  } }
  body { set_valid { header { index {
    base { member { base { var: "hdr" } field: "vlan" } } index { var: "idx" }
  } } } }
  # 10-12: concat, boolean logic, shift
  body { assign {
    target { var: "t16" }
    value { binary {
      op: BINARY_OP_CONCAT
      left { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "ttl" } }
      right { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "proto" } }
    } }
  } }
  body { assign {
    target { member { base { var: "meta" } field: "drop" } }
    value { binary {
      op: BINARY_OP_AND
      left { unary { op: UNARY_OP_NOT operand { member { base { var: "meta" } field: "drop" } } } }
      right { binary {
        op: BINARY_OP_LT
        left { member { base { member { base { var: "hdr" } field: "ipv4" } } field: "ttl" } }
        right { literal { bits { width: 8 value: "1" } } }
      } }
    } }
  } }
  body { assign {
    target { var: "idx" }
    value { binary {
      op: BINARY_OP_SHL left { var: "idx" } right { literal { bits { width: 8 value: "2" } } }
    } }
  } }
  # 13-14: sub-control call, pop
  body { call_block {
    block: "sub" args { lvalue { var: "hdr" } } args { lvalue { var: "meta" } }
  } }
  body { pop { stack { member { base { var: "hdr" } field: "vlan" } } count: 1 } }
}

blocks {
  name: "sub" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  body { assign {
    target { member { base { var: "meta" } field: "port" } }
    value { binary {
      op: BINARY_OP_ADD
      left { member { base { var: "meta" } field: "port" } }
      right { literal { bits { width: 9 value: "1" } } }
    } }
  } }
}

blocks {
  name: "dep" kind: BLOCK_KIND_DEPARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
  body { emit { value { member { base { var: "hdr" } field: "eth" } } } }
  body { emit { value { member { base { var: "hdr" } field: "vlan" } } } }
  body { emit { value { member { base { var: "hdr" } field: "ipv4" } } } }
}

exports { role: "parser" block: "prs" }
exports { role: "ingress" block: "ing" }
exports { role: "deparser" block: "dep" }
"""


# -- helpers --------------------------------------------------------------------


def valid() -> pb.Program:
    return ir.load_text(VALID)


def codes(program: pb.Program) -> list[str]:
    return [d.code for d in v.validate(program)]


def stmt(text: str) -> pb.Stmt:
    return text_format.Parse(text, pb.Stmt())


def expr(text: str) -> pb.Expr:
    return text_format.Parse(text, pb.Expr())


def add_stmt(program: pb.Program, block: int, text: str) -> pb.Program:
    """Append a statement to a control or deparser body."""
    program.blocks[block].body.add().CopyFrom(stmt(text))
    return program


def add_parser_stmt(program: pb.Program, state: int, text: str) -> pb.Program:
    """Append a statement to a parser state's body."""
    program.blocks[PRS].states[state].body.add().CopyFrom(stmt(text))
    return program


def broken(mutate: Callable[[pb.Program], object]) -> list[str]:
    program = valid()
    mutate(program)
    return codes(program)


# Text-format builders, so that a malformed statement fits on one line.


def var(name: str) -> str:
    return f'var: "{name}"'


def member(base: str, field: str) -> str:
    return f'member {{ base {{ {base} }} field: "{field}" }}'


def index(base: str, idx: str) -> str:
    return f"index {{ base {{ {base} }} index {{ {idx} }} }}"


def lit(width: int, value: str) -> str:
    return f'literal {{ bits {{ width: {width} value: "{value}" }} }}'


def assign(target: str, value: str) -> str:
    return f"assign {{ target {{ {target} }} value {{ {value} }} }}"


def unary(op: str, operand: str) -> str:
    return f"unary {{ op: UNARY_OP_{op} operand {{ {operand} }} }}"


def binary(op: str, left: str, right: str) -> str:
    return f"binary {{ op: BINARY_OP_{op} left {{ {left} }} right {{ {right} }} }}"


def mux(condition: str, then: str, otherwise: str) -> str:
    return f"mux {{ condition {{ {condition} }} then {{ {then} }} otherwise {{ {otherwise} }} }}"


def cast(to: str, operand: str) -> str:
    return f"cast {{ to {{ {to} }} operand {{ {operand} }} }}"


def arg_in(text: str) -> str:
    return f"args {{ expr {{ {text} }} }}"


def arg_out(text: str) -> str:
    return f"args {{ lvalue {{ {text} }} }}"


def call_block(block: str, *args: str) -> str:
    return f'call_block {{ block: "{block}" {" ".join(args)} }}'


def call_action(action: str, *args: str) -> str:
    return f'call_action {{ action: "{action}" {" ".join(args)} }}'


def call_extern(method: str, *args: str, result: str | None = None) -> str:
    tail = f" result {{ {result} }}" if result else ""
    return f'call_extern {{ instance: "ctr" method: "{method}" {" ".join(args)}{tail} }}'


HDR, META, IDX, HIT, VAL, T16, TMP = (
    var("hdr"),
    var("meta"),
    var("idx"),
    var("hit"),
    var("val"),
    var("t16"),
    var("tmp"),
)
HDR_IPV4 = member(HDR, "ipv4")
HDR_VLAN = member(HDR, "vlan")
HDR_ETH = member(HDR, "eth")
TTL = member(HDR_IPV4, "ttl")
PROTO = member(HDR_IPV4, "proto")
META_DROP = member(META, "drop")
META_COLOR = member(META, "color")
B8 = lit(8, "1")
B16 = lit(16, "1")
B32 = lit(32, "1")
TRUE = "literal { boolean: true }"
BOOL = "boolean {}"


# -- the valid program ---------------------------------------------------------


def test_valid_program_has_no_diagnostics() -> None:
    assert v.validate(valid()) == []


def test_check_returns_index() -> None:
    index = v.check(valid())
    assert set(index.blocks) == {"prs", "ing", "sub", "dep"}


def test_check_raises_with_diagnostics() -> None:
    program = valid()
    program.headers = "nope"
    with pytest.raises(v.ValidationError) as info:
        v.check(program)
    assert [d.code for d in info.value.diagnostics] == [v.REF_UNRESOLVED]
    assert "headers" in str(info.value)


def test_diagnostic_paths_are_protobuf_style() -> None:
    program = valid()
    program.blocks[ING].body[2].assign.value.cast.to.bits = 16
    (diag,) = v.validate(program)
    assert diag.code == v.TYPE_MISMATCH
    assert diag.path == "blocks[1].body[2].assign"
    assert str(diag).startswith("blocks[1].body[2].assign: TYPE_MISMATCH: ")


def test_nested_path() -> None:
    program = valid()
    mask = program.blocks[PRS].states[START].transition.select.cases[1].sets[0].masked.mask
    mask.bits.width, mask.bits.value = 8, "255"
    (diag,) = v.validate(program)
    assert diag.code == v.SELECT_TYPE
    assert diag.path == "blocks[0].states[0].transition.select.cases[1].sets[0].masked.mask"


# -- structure and names ---------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.struct_types.add(name="H"),
        lambda p: p.blocks[ING].locals.add(name="hit", type=pb.Type(bits=1)),
        lambda p: p.blocks[ING].actions[1].params.add(name="idx", type=pb.Type(bits=1)),
        lambda p: p.errors.append("NoError"),
        lambda p: p.header_types[0].fields.add(name="dst", type=pb.Type(bits=1)),
        lambda p: p.enum_types[0].members.append("RED"),
        lambda p: p.extern_types[0].methods.add(name="count"),
        lambda p: p.extern_types[0].methods[1].params.add(name="idx", type=pb.Type(bits=1)),
    ],
)
def test_name_duplicate(mutate) -> None:
    assert v.NAME_DUPLICATE in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p.blocks[PRS], "name", ""),
        lambda p: setattr(p.header_types[0].fields[0], "name", ""),
        lambda p: p.enum_types[0].members.append(""),
        lambda p: setattr(p.extern_types[0].methods[0], "name", ""),
    ],
)
def test_name_empty(mutate) -> None:
    assert v.NAME_EMPTY in broken(mutate)


def test_index_failure_stops_validation() -> None:
    program = valid()
    program.struct_types.add(name="H")
    program.blocks[ING].body[2].assign.value.cast.to.bits = 16
    assert codes(program) == [v.NAME_DUPLICATE]


def swap_errors(p: pb.Program) -> None:
    p.errors[1], p.errors[2] = p.errors[2], p.errors[1]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.errors.__delitem__(0),
        swap_errors,
        lambda p: p.errors.insert(0, "Mine"),
    ],
)
def test_error_list(mutate) -> None:
    assert v.ERROR_LIST in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p, "headers", "nope"),
        lambda p: setattr(p, "metadata", ""),
        lambda p: setattr(p.struct_types[0].fields[0].type, "header", "nope"),
        lambda p: setattr(p.struct_types[0].fields[1].type.stack, "header", "nope"),
        lambda p: setattr(p.struct_types[1].fields[2].type, "enum_type", "nope"),
        lambda p: setattr(p.extern_instances[0], "extern_type", "nope"),
        lambda p: setattr(p.exports[0], "block", "nope"),
        lambda p: setattr(p.blocks[ING].body[13].call_block, "block", "nope"),
        lambda p: setattr(p.blocks[ING].body[3].call_extern, "instance", "nope"),
        lambda p: setattr(p.blocks[ING].body[3].call_extern, "method", "nope"),
        lambda p: setattr(p.blocks[ING].body[2].assign.target, "var", "nope"),
        lambda p: setattr(p.blocks[ING].body[3].call_extern.args[0].expr, "var", "nope"),
        lambda p: setattr(p.blocks[ING].body[10].assign.value.binary.left.member, "field", "x"),
        lambda p: setattr(p.blocks[ING].body[1].assign.target.member, "field", "nope"),
        lambda p: setattr(
            p.blocks[ING].body[1].assign.value.mux.then.literal.enum_member, "member", "x"
        ),
        lambda p: setattr(p.blocks[PRS].states[PARSE_IPV4].body[1].verify, "error", "nope"),
        lambda p: setattr(
            p.blocks[PRS].states[START].transition.select.cases[0].target, "state", "x"
        ),
        lambda p: setattr(p.blocks[ING].body[0].conditional.then[0].apply, "table", "nope"),
        lambda p: setattr(
            p.blocks[ING].body[0].conditional.otherwise[0].call_action, "action", "nope"
        ),
        lambda p: setattr(p.blocks[ING].tables[0].default_action, "action", "nope"),
        lambda p: p.blocks[ING].tables[0].actions.append("nope"),
        lambda p: add_stmt(p, DEP, 'emit { value { literal { error: "nope" } } }'),
    ],
)
def test_ref_unresolved(mutate) -> None:
    assert v.REF_UNRESOLVED in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p, "headers", "eth"),
        lambda p: setattr(p.struct_types[0].fields[0].type, "header", "H"),
        lambda p: setattr(p.struct_types[0].fields[2].type, "struct", "ipv4"),
        lambda p: setattr(p.struct_types[1].fields[2].type, "enum_type", "eth"),
        lambda p: setattr(p.extern_instances[0], "extern_type", "ctr"),
        lambda p: setattr(p.exports[0], "block", "H"),
        lambda p: setattr(p.blocks[ING].body[13].call_block, "block", "Counter"),
        lambda p: setattr(p.blocks[ING].body[3].call_extern, "instance", "Counter"),
        lambda p: setattr(p.blocks[ING].body[2].assign.target, "var", "route"),
        lambda p: setattr(p.blocks[ING].body[3].call_extern.args[0].expr, "var", "drop"),
        lambda p: setattr(p.blocks[ING].body[0].conditional.then[0].apply, "table", "drop"),
        lambda p: setattr(
            p.blocks[ING].body[0].conditional.otherwise[0].call_action, "action", "route"
        ),
        lambda p: setattr(
            p.blocks[PRS].states[START].transition.select.cases[0].target, "state", "tmp"
        ),
    ],
)
def test_ref_kind(mutate) -> None:
    assert v.REF_KIND in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        # sub reads ing's local
        lambda p: add_stmt(p, SUB, assign(HDR, IDX)),
        # the block body reads an action's param
        lambda p: add_stmt(p, ING, assign(IDX, var("port"))),
        # one action reads another's param
        lambda p: p.blocks[ING].actions[0].body.add().CopyFrom(stmt(assign(IDX, var("dec")))),
    ],
)
def test_scope_var(mutate) -> None:
    assert v.SCOPE_VAR in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: add_stmt(p, SUB, 'apply { table: "route" }'),
        lambda p: add_stmt(p, SUB, call_action("drop")),
    ],
)
def test_scope_decl(mutate) -> None:
    assert v.SCOPE_DECL in broken(mutate)


def test_scope_decl_state_of_another_parser() -> None:
    program = valid()
    other = program.blocks.add()
    other.CopyFrom(program.blocks[PRS])
    other.name = "prs2"
    other.states[START].transition.direct.state = "parse_vlan"
    del other.states[PARSE_VLAN:]
    assert v.SCOPE_DECL in codes(program)


def test_export_duplicate() -> None:
    assert v.EXPORT_DUPLICATE in broken(lambda p: p.exports.add(role="parser", block="prs"))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p.blocks[PRS].params[0], "direction", pb.DIRECTION_INOUT),
        lambda p: setattr(p.blocks[ING].params[0], "direction", pb.DIRECTION_IN),
        lambda p: setattr(p.blocks[DEP].params[0], "direction", pb.DIRECTION_INOUT),
        lambda p: p.blocks[DEP].params.add(
            name="m", type=pb.Type(struct="M"), direction=pb.DIRECTION_IN
        ),
        lambda p: setattr(p.blocks[ING].params[1].type, "struct", "H"),
        lambda p: p.blocks[PRS].params.__delitem__(1),
    ],
)
def test_export_signature(mutate) -> None:
    assert v.EXPORT_SIGNATURE in broken(mutate)


def test_unexported_block_may_have_any_signature() -> None:
    program = valid()
    del program.blocks[SUB].params[1]
    program.blocks[SUB].ClearField("body")
    del program.blocks[ING].body[13].call_block.args[1]
    assert codes(program) == []


# -- types and literals ----------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p.blocks[ING].locals[1].type, "bits", 0),
        lambda p: setattr(p.struct_types[0].fields[1].type.stack, "size", 0),
        lambda p: p.header_types[0].fields[0].type.CopyFrom(pb.Type(struct="M")),
        lambda p: (
            p.header_types[0]
            .fields[0]
            .type.CopyFrom(pb.Type(stack=pb.StackType(header="vlan", size=1)))
        ),
        lambda p: p.blocks[ING].locals[1].type.Clear(),
        lambda p: p.extern_types[0].methods[2].returns.Clear(),
        lambda p: p.blocks[ING].actions[1].params[0].type.Clear(),
        lambda p: p.extern_types[0].constructor_params[0].type.Clear(),
        lambda p: p.enum_types[0].ClearField("members"),
        lambda p: p.struct_types[1].fields.add(name="self", type=pb.Type(struct="M")),
        lambda p: add_stmt(p, ING, assign(IDX, cast("", IDX))),
    ],
)
def test_type_invalid(mutate) -> None:
    assert v.TYPE_INVALID in broken(mutate)


def test_struct_cycle_through_another_struct() -> None:
    program = valid()
    program.struct_types.add(name="A").fields.add(name="b", type=pb.Type(struct="B"))
    program.struct_types.add(name="B").fields.add(name="a", type=pb.Type(struct="A"))
    (diag,) = v.validate(program)
    assert diag.code == v.TYPE_INVALID
    assert "A -> B -> A" in diag.message


def shift_amount(p: pb.Program) -> pb.BitsLiteral:
    return p.blocks[ING].body[12].assign.value.binary.right.literal.bits


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(shift_amount(p), "value", "abc"),
        lambda p: setattr(shift_amount(p), "value", "-1"),
        lambda p: setattr(shift_amount(p), "value", " 1"),
        lambda p: setattr(shift_amount(p), "value", "0x1"),
        lambda p: setattr(shift_amount(p), "value", ""),
        lambda p: p.blocks[ING].body[12].assign.value.binary.right.literal.Clear(),
    ],
)
def test_literal_format(mutate) -> None:
    assert v.LITERAL_FORMAT in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(shift_amount(p), "value", "256"),
        lambda p: setattr(shift_amount(p), "width", 0),
        lambda p: setattr(
            p.blocks[ING].tables[0].const_entries[0].action.args[0].bits, "value", "512"
        ),
        lambda p: setattr(
            p.blocks[PRS].states[START].transition.select.cases[0].sets[0].exact.bits,
            "value",
            "65536",
        ),
    ],
)
def test_literal_range(mutate) -> None:
    assert v.LITERAL_RANGE in broken(mutate)


# -- blocks ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p.blocks[ING], "kind", pb.BLOCK_KIND_UNSPECIFIED),
        lambda p: add_stmt(p, PRS, f"advance {{ bits {{ {B8} }} }}"),
        lambda p: p.blocks[PRS].ClearField("states"),
        lambda p: p.blocks[PRS].actions.add(name="a"),
        lambda p: p.blocks[PRS].tables.add(name="t", actions=["a"]),
        lambda p: p.blocks[ING].states.add(name="s"),
        lambda p: setattr(p.blocks[ING], "start_state", "s"),
        lambda p: setattr(p.blocks[DEP], "start_state", "s"),
    ],
)
def test_block_kind_shape(mutate) -> None:
    assert v.BLOCK_KIND_SHAPE in broken(mutate)


@pytest.mark.parametrize("start", ["nope", "", "tmp"])
def test_parser_start_state(start: str) -> None:
    assert v.PARSER_START_STATE in broken(lambda p: setattr(p.blocks[PRS], "start_state", start))


@pytest.mark.parametrize(
    "block, text",
    [
        (ING, f"emit {{ value {{ {HDR_IPV4} }} }}"),
        (ING, f"extract {{ target {{ {HDR_IPV4} }} }}"),
        (ING, f"advance {{ bits {{ {IDX} }} }}"),
        (ING, f'verify {{ condition {{ {HIT} }} error: "NoMatch" }}'),
        (DEP, call_action("x")),
        (DEP, 'apply { table: "x" }'),
    ],
)
def test_block_kind_stmt_in_control_or_deparser(block: int, text: str) -> None:
    assert v.BLOCK_KIND_STMT in broken(lambda p: add_stmt(p, block, text))


@pytest.mark.parametrize(
    "text",
    ['apply { table: "x" }', call_action("x"), f"emit {{ value {{ {HDR_IPV4} }} }}"],
)
def test_block_kind_stmt_in_parser(text: str) -> None:
    assert v.BLOCK_KIND_STMT in broken(lambda p: add_parser_stmt(p, PARSE_IPV4, text))


def test_block_kind_stmt_in_action() -> None:
    def mutate(p: pb.Program) -> None:
        p.blocks[ING].actions[0].body.add().CopyFrom(stmt(f"emit {{ value {{ {HDR_IPV4} }} }}"))

    assert v.BLOCK_KIND_STMT in broken(mutate)


@pytest.mark.parametrize(
    "block, text",
    [
        (ING, assign(T16, "lookahead { type { bits: 16 } }")),
        (ING, f"set_valid {{ header {{ next {{ stack {{ {HDR_VLAN} }} }} }} }}"),
        (DEP, 'emit { value { lookahead { type { header: "eth" } } } }'),
    ],
)
def test_parser_only(block: int, text: str) -> None:
    assert v.PARSER_ONLY in broken(lambda p: add_stmt(p, block, text))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(p.blocks[SUB].params[0], "direction", pb.DIRECTION_NONE),
        lambda p: setattr(p.blocks[SUB].params[0], "direction", pb.DIRECTION_UNSPECIFIED),
        lambda p: setattr(
            p.blocks[ING].actions[1].params[0], "direction", pb.DIRECTION_UNSPECIFIED
        ),
        # an action a table invokes has only directionless params
        lambda p: setattr(p.blocks[ING].actions[1].params[0], "direction", pb.DIRECTION_IN),
        lambda p: setattr(p.extern_types[0].constructor_params[0], "direction", pb.DIRECTION_OUT),
        lambda p: setattr(p.extern_types[0].constructor_params[0], "direction", pb.DIRECTION_NONE),
        lambda p: setattr(p.extern_types[0].methods[0].params[0], "direction", pb.DIRECTION_NONE),
    ],
)
def test_param_direction(mutate) -> None:
    assert v.PARAM_DIRECTION in broken(mutate)


def test_action_with_directed_params_is_fine_when_only_called() -> None:
    program = valid()
    action = program.blocks[ING].actions.add(name="bump")
    action.params.add(name="x", type=pb.Type(bits=32), direction=pb.DIRECTION_INOUT)
    action.body.add().CopyFrom(stmt(assign(var("x"), binary("ADD", var("x"), B32))))
    add_stmt(program, ING, call_action("bump", arg_out(IDX)))
    assert codes(program) == []


# -- expressions, lvalues and statements -----------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        assign(IDX, ""),
        assign("", IDX),
        assign(HIT, unary("UNSPECIFIED", HIT)),
        assign(IDX, binary("UNSPECIFIED", IDX, IDX)),
    ],
)
def test_expr_invalid(text: str) -> None:
    assert v.EXPR_INVALID in broken(lambda p: add_stmt(p, ING, text))


def test_stmt_invalid() -> None:
    assert v.STMT_INVALID in broken(lambda p: p.blocks[ING].body.add())


@pytest.mark.parametrize(
    "text",
    [
        # assign: types differ
        assign(IDX, B8),
        assign(HIT, B8),
        assign(HDR_IPV4, HDR_ETH),
        # if: condition not boolean
        f"conditional {{ condition {{ {B8} }} }}",
        # unary
        assign(HIT, unary("NOT", B8)),
        assign(HIT, unary("COMPLEMENT", TRUE)),
        assign(HIT, unary("NEGATE", TRUE)),
        # binary: widths, kinds
        assign(T16, binary("ADD", B8, B16)),
        assign(T16, binary("SUB_SAT", B16, B8)),
        assign(T16, binary("BIT_XOR", B16, TRUE)),
        assign(T16, binary("SHL", B16, TRUE)),
        assign(T16, binary("SHR", TRUE, B8)),
        assign(T16, binary("CONCAT", B8, TRUE)),
        assign(HIT, binary("EQ", B8, B16)),
        assign(HIT, binary("NE", B8, TRUE)),
        assign(HIT, binary("LT", B8, B16)),
        assign(HIT, binary("GE", TRUE, TRUE)),
        assign(HIT, binary("AND", B8, TRUE)),
        assign(HIT, binary("OR", TRUE, B8)),
        # mux
        assign(T16, mux(B8, B16, B16)),
        assign(T16, mux(TRUE, B16, B8)),
        # member on a scalar, index on a header, index by a boolean, lastIndex of a header
        assign(IDX, member(IDX, "x")),
        assign(IDX, member(index(HDR_IPV4, IDX), "ttl")),
        assign(IDX, member(index(HDR_VLAN, HIT), "vid")),
        assign(IDX, f"last_index {{ stack {{ {HDR_IPV4} }} }}"),
        # isValid on a struct; setValid on a field; push on a header; apply hit not boolean
        assign(HIT, f"is_valid {{ header {{ {HDR} }} }}"),
        f"set_valid {{ header {{ {TTL} }} }}",
        f"set_invalid {{ header {{ {META} }} }}",
        f"push {{ stack {{ {HDR_IPV4} }} count: 1 }}",
        f"pop {{ stack {{ {META_DROP} }} count: 1 }}",
        f'apply {{ table: "route" hit {{ {IDX} }} }}',
        # slice of a boolean
        assign(HIT, f"slice {{ operand {{ {TRUE} }} hi: 0 lo: 0 }}"),
        # index lvalue by boolean, of a header
        f"set_valid {{ header {{ {index(HDR_VLAN, HIT)} }} }}",
        f"set_valid {{ header {{ {index(HDR_IPV4, IDX)} }} }}",
    ],
)
def test_type_mismatch_in_control(text: str) -> None:
    assert v.TYPE_MISMATCH in broken(lambda p: add_stmt(p, ING, text))


@pytest.mark.parametrize(
    "text",
    [
        f"extract {{ target {{ {TTL} }} }}",
        f"extract {{ target {{ {HDR} }} }}",
        f"extract {{ target {{ next {{ stack {{ {HDR_IPV4} }} }} }} }}",
        f"advance {{ bits {{ {TRUE} }} }}",
        f'verify {{ condition {{ {B8} }} error: "NoMatch" }}',
        assign(TMP, 'lookahead { type { struct: "M" } }'),
        assign(TMP, f"lookahead {{ type {{ {BOOL} }} }}"),
    ],
)
def test_type_mismatch_in_parser(text: str) -> None:
    assert v.TYPE_MISMATCH in broken(lambda p: add_parser_stmt(p, PARSE_IPV4, text))


@pytest.mark.parametrize(
    "text",
    [f"emit {{ value {{ {TTL} }} }}", f"emit {{ value {{ {TRUE} }} }}"],
)
def test_type_mismatch_in_deparser(text: str) -> None:
    assert v.TYPE_MISMATCH in broken(lambda p: add_stmt(p, DEP, text))


def test_emit_of_struct_with_scalar_field_is_rejected() -> None:
    program = valid()
    program.blocks[DEP].params.add(name="meta", type=pb.Type(struct="M"), direction=pb.DIRECTION_IN)
    del program.exports[2]
    add_stmt(program, DEP, f"emit {{ value {{ {META} }} }}")
    assert codes(program) == [v.TYPE_MISMATCH]


def test_emit_of_headers_struct_is_fine() -> None:
    assert codes(add_stmt(valid(), DEP, f"emit {{ value {{ {HDR} }} }}")) == []


@pytest.mark.parametrize(
    "text",
    [
        assign(IDX, cast("bits: 32", TRUE)),
        assign(HIT, cast(BOOL, B8)),
        assign(IDX, cast("bits: 32", HDR_IPV4)),
        assign(HIT, cast(BOOL, TRUE)),
        assign(HDR_IPV4, cast('header: "ipv4"', B8)),
    ],
)
def test_cast_invalid(text: str) -> None:
    assert v.CAST_INVALID in broken(lambda p: add_stmt(p, ING, text))


def test_bit1_and_boolean_casts_are_fine() -> None:
    program = valid()
    add_stmt(program, ING, assign(HIT, cast(BOOL, lit(1, "1"))))
    add_stmt(program, ING, assign(IDX, cast("bits: 32", cast("bits: 1", HIT))))
    assert codes(program) == []


@pytest.mark.parametrize("hi, lo", [(32, 0), (0, 1), (31, 32), (40, 40)])
def test_slice_range(hi: int, lo: int) -> None:
    text = assign(IDX, f"slice {{ operand {{ {IDX} }} hi: {hi} lo: {lo} }}")
    assert v.SLICE_RANGE in broken(lambda p: add_stmt(p, ING, text))


def test_slice_width() -> None:
    text = assign(T16, f"slice {{ operand {{ {IDX} }} hi: 31 lo: 16 }}")
    assert codes(add_stmt(valid(), ING, text)) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: add_stmt(p, DEP, assign(TTL, B8)),
        lambda p: add_stmt(p, DEP, f"set_invalid {{ header {{ {HDR_ETH} }} }}"),
        lambda p: p.blocks[ING].actions[1].body.add().CopyFrom(stmt(assign(var("dec"), B8))),
        lambda p: add_stmt(p, DEP, call_block("sub", arg_out(HDR), arg_out(HDR))),
    ],
)
def test_lvalue_readonly(mutate) -> None:
    assert v.LVALUE_READONLY in broken(mutate)


@pytest.mark.parametrize(
    "text",
    [f"push {{ stack {{ {HDR_VLAN} }} count: 0 }}", f"pop {{ stack {{ {HDR_VLAN} }} }}"],
)
def test_stack_count(text: str) -> None:
    assert v.STACK_COUNT in broken(lambda p: add_stmt(p, ING, text))


@pytest.mark.parametrize(
    "text",
    [
        call_block("sub", arg_out(HDR)),
        call_action("fwd", arg_in(lit(9, "1"))),
        call_extern("count"),
        call_extern("size", arg_in(IDX), result=VAL),
    ],
)
def test_arg_count(text: str) -> None:
    assert v.ARG_COUNT in broken(lambda p: add_stmt(p, ING, text))


@pytest.mark.parametrize(
    "text",
    [
        call_block("sub", arg_in(HDR), arg_out(META)),
        call_extern("count", arg_out(IDX)),
        call_extern("read", arg_in(IDX), arg_in(VAL)),
        call_extern("count", "args {}"),
        call_action("fwd", arg_out(IDX), arg_in(B8)),
    ],
)
def test_arg_direction(text: str) -> None:
    assert v.ARG_DIRECTION in broken(lambda p: add_stmt(p, ING, text))


@pytest.mark.parametrize(
    "text",
    [
        call_block("sub", arg_out(META), arg_out(HDR)),
        call_extern("count", arg_in(T16)),
        call_extern("read", arg_in(IDX), arg_out(T16)),
        call_action("fwd", arg_in(B8), arg_in(B8)),
    ],
)
def test_arg_type(text: str) -> None:
    assert v.ARG_TYPE in broken(lambda p: add_stmt(p, ING, text))


@pytest.mark.parametrize(
    "mutate",
    [
        # a control calling a parser
        lambda p: add_stmt(p, ING, call_block("prs", arg_out(HDR), arg_out(META))),
        # a deparser calling a parser
        lambda p: add_stmt(p, DEP, call_block("prs", arg_out(HDR), arg_out(HDR))),
        # a parser calling a control
        lambda p: add_parser_stmt(p, PARSE_IPV4, call_block("sub", arg_out(HDR), arg_out(META))),
    ],
)
def test_call_kind(mutate) -> None:
    assert v.CALL_KIND in broken(mutate)


def test_deparser_may_call_a_control() -> None:
    program = valid()
    helper = program.blocks.add(name="fix", kind=pb.BLOCK_KIND_CONTROL)
    helper.params.add(name="h", type=pb.Type(struct="H"), direction=pb.DIRECTION_IN)
    add_stmt(program, DEP, call_block("fix", arg_in(HDR)))
    assert codes(program) == []


def read_bits16(program: pb.Program) -> None:
    """Make Counter.read take and return bit<16>, so header fields fit."""
    program.extern_types[0].methods[1].params[0].type.bits = 16
    program.extern_types[0].methods[1].params[1].type.bits = 16
    del program.blocks[ING].body[4]


VLAN_TYPE_AT_IDX = member(index(HDR_VLAN, IDX), "type")
VLAN_TYPE_AT_0 = member(index(HDR_VLAN, lit(32, "0")), "type")
VLAN_TYPE_AT_1 = member(index(HDR_VLAN, lit(32, "1")), "type")


@pytest.mark.parametrize(
    "text",
    [
        call_block("sub", arg_out(HDR), arg_out(HDR)),
        call_extern("read", arg_in(T16), arg_out(T16)),
        # the whole header and one of its fields
        call_extern("read", arg_in(member(HDR_ETH, "type")), arg_out(member(HDR_ETH, "type"))),
        # the same stack element, once by computed index and once by literal
        call_extern("read", arg_in(VLAN_TYPE_AT_IDX), arg_out(VLAN_TYPE_AT_1)),
        call_extern("read", arg_in(VLAN_TYPE_AT_1), arg_out(VLAN_TYPE_AT_IDX)),
    ],
)
def test_call_alias(text: str) -> None:
    program = valid()
    read_bits16(program)
    add_stmt(program, ING, text)
    assert v.CALL_ALIAS in codes(program)


@pytest.mark.parametrize(
    "text",
    [
        # sibling fields of one header
        call_extern("read", arg_in(member(HDR_ETH, "type")), arg_out(VLAN_TYPE_AT_0)),
        # different stack elements by literal index
        call_extern("read", arg_in(VLAN_TYPE_AT_0), arg_out(VLAN_TYPE_AT_1)),
        # a computed value cannot alias
        call_extern("read", arg_in(binary("ADD", VLAN_TYPE_AT_1, B16)), arg_out(VLAN_TYPE_AT_1)),
    ],
)
def test_no_alias(text: str) -> None:
    program = valid()
    read_bits16(program)
    add_stmt(program, ING, text)
    assert codes(program) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: add_stmt(p, SUB, call_block("ing", arg_out(HDR), arg_out(META))),
        lambda p: add_stmt(p, SUB, call_block("sub", arg_out(HDR), arg_out(META))),
    ],
)
def test_call_cycle(mutate) -> None:
    assert v.CALL_CYCLE in broken(mutate)


def test_call_cycle_message_and_path() -> None:
    program = add_stmt(valid(), SUB, call_block("ing", arg_out(HDR), arg_out(META)))
    (diag,) = v.validate(program)
    assert diag.code == v.CALL_CYCLE
    assert "ing -> sub -> ing" in diag.message
    assert diag.path == "blocks[2].body[1].call_block"


@pytest.mark.parametrize(
    "text",
    [
        call_extern("size"),
        call_extern("count", arg_in(IDX), result=VAL),
        call_extern("size", result=T16),
    ],
)
def test_extern_result(text: str) -> None:
    assert v.EXTERN_RESULT in broken(lambda p: add_stmt(p, ING, text))


# -- parsers -----------------------------------------------------------------------


def start_select(p: pb.Program) -> pb.Select:
    return p.blocks[PRS].states[START].transition.select


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.blocks[PRS].states[PARSE_IPV4].ClearField("transition"),
        lambda p: p.blocks[PRS].states[PARSE_IPV4].transition.direct.Clear(),
        lambda p: start_select(p).cases[0].target.Clear(),
    ],
)
def test_parser_transition(mutate) -> None:
    assert v.PARSER_TRANSITION in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: start_select(p).ClearField("keys"),
        lambda p: start_select(p).cases[0].sets.add().dont_care.SetInParent(),
        lambda p: start_select(p).cases[3].ClearField("sets"),
    ],
)
def test_select_arity(mutate) -> None:
    assert v.SELECT_ARITY in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(start_select(p).cases[0].sets[0].exact.bits, "width", 8),
        lambda p: setattr(start_select(p).cases[1].sets[0].masked.mask.bits, "width", 8),
        lambda p: setattr(start_select(p).cases[2].sets[0].range.hi.bits, "width", 32),
        lambda p: start_select(p).cases[0].sets[0].exact.CopyFrom(pb.Literal(boolean=True)),
        lambda p: start_select(p).cases[0].sets[0].Clear(),
        # masked and range need a bits key
        lambda p: start_select(p).keys[0].CopyFrom(expr(META_DROP)),
        # a struct is not a select key
        lambda p: start_select(p).keys[0].CopyFrom(expr(META)),
    ],
)
def test_select_type(mutate) -> None:
    assert v.SELECT_TYPE in broken(mutate)


def test_select_on_boolean_and_enum_keys() -> None:
    program = valid()
    select = program.blocks[PRS].states[PARSE_IPV4].transition.select
    select.keys.add().CopyFrom(expr(META_DROP))
    select.keys.add().CopyFrom(expr(META_COLOR))
    case = select.cases.add()
    case.sets.add().exact.boolean = True
    case.sets.add().exact.enum_member.CopyFrom(pb.EnumLiteral(enum_type="Color", member="RED"))
    case.target.accept.SetInParent()
    assert codes(program) == []


# -- tables ------------------------------------------------------------------------


def route(p: pb.Program) -> pb.Table:
    return p.blocks[ING].tables[0]


def acl_table(entries: str) -> pb.Table:
    return text_format.Parse(
        f"""
        name: "acl"
        keys {{ expr {{ {TTL} }} match_kind: MATCH_KIND_TERNARY }}
        keys {{ expr {{ {PROTO} }} match_kind: MATCH_KIND_EXACT }}
        actions: "drop"
        {entries}
        """,
        pb.Table(),
    )


def entry(ttl: str, mask: str, proto: str, priority: int) -> str:
    return (
        f'const_entries {{ keys {{ ternary {{ value: "{ttl}" mask: "{mask}" }} }} '
        f'keys {{ exact: "{proto}" }} action {{ action: "drop" }} priority: {priority} }}'
    )


def with_acl(entries: str) -> pb.Program:
    program = valid()
    program.blocks[ING].tables.add().CopyFrom(acl_table(entries))
    add_stmt(program, ING, 'apply { table: "acl" }')
    return program


def test_ternary_table_is_valid() -> None:
    assert codes(with_acl(entry("64", "255", "6", 1) + entry("0", "0", "6", 2))) == []


def test_key_name() -> None:
    def mutate(p: pb.Program) -> None:
        key = route(p).keys.add(match_kind=pb.MATCH_KIND_EXACT, name="dst")
        key.expr.CopyFrom(expr(TTL))
        route(p).const_entries[0].keys.add(exact="1")

    assert v.KEY_NAME in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: route(p).keys[0].expr.CopyFrom(expr(META_DROP)),
        lambda p: setattr(route(p).keys[0], "match_kind", pb.MATCH_KIND_UNSPECIFIED),
        lambda p: route(p).keys.add(match_kind=pb.MATCH_KIND_EXACT).expr.CopyFrom(expr(HDR_IPV4)),
        lambda p: route(p).keys.add(match_kind=pb.MATCH_KIND_TERNARY).expr.CopyFrom(expr(HIT)),
    ],
)
def test_key_type(mutate) -> None:
    assert v.KEY_TYPE in broken(mutate)


def test_table_lpm_count() -> None:
    def mutate(p: pb.Program) -> None:
        route(p).keys.add().CopyFrom(route(p).keys[0])
        route(p).keys[1].name = "dst2"

    assert v.TABLE_LPM_COUNT in broken(mutate)


def test_table_key_mix() -> None:
    def mutate(p: pb.Program) -> None:
        route(p).keys.add(match_kind=pb.MATCH_KIND_TERNARY).expr.CopyFrom(expr(TTL))

    assert v.TABLE_KEY_MIX in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: route(p).ClearField("actions"),
        lambda p: route(p).actions.append("fwd"),
        lambda p: route(p).actions.remove("drop"),
        lambda p: route(p).actions.remove("fwd"),
    ],
)
def test_table_actions(mutate) -> None:
    assert v.TABLE_ACTIONS in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(route(p).default_action, "action", "fwd"),
        lambda p: route(p).default_action.args.add(boolean=True),
        lambda p: route(p).const_entries[0].action.args.pop(),
        lambda p: setattr(route(p).const_entries[0].action.args[0].bits, "width", 8),
        lambda p: route(p).const_entries[0].action.args[1].CopyFrom(pb.Literal(boolean=True)),
    ],
)
def test_action_args(mutate) -> None:
    assert v.ACTION_ARGS in broken(mutate)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: route(p).const_entries[0].keys[0].CopyFrom(pb.KeyValue(exact="1")),
        lambda p: route(p).const_entries[0].keys[0].Clear(),
        lambda p: route(p).const_entries[0].keys.add(exact="1"),
        lambda p: route(p).const_entries[0].ClearField("keys"),
        lambda p: setattr(route(p).const_entries[0].keys[0].lpm, "value", "10.0.0.0"),
        lambda p: (
            route(p)
            .const_entries[0]
            .keys[0]
            .CopyFrom(pb.KeyValue(ternary=pb.TernaryValue(value="1", mask="1")))
        ),
    ],
)
def test_entry_shape(mutate) -> None:
    assert v.ENTRY_SHAPE in broken(mutate)


@pytest.mark.parametrize(
    "entries",
    [entry("6", "x", "6", 1), entry("6", "255", "true", 1), entry("6", "255", "", 1)],
)
def test_entry_shape_ternary_and_exact(entries: str) -> None:
    assert v.ENTRY_SHAPE in codes(with_acl(entries))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: setattr(route(p).const_entries[0].keys[0].lpm, "value", "4294967296"),
        lambda p: setattr(route(p).const_entries[0].keys[0].lpm, "prefix_len", 33),
    ],
)
def test_entry_range(mutate) -> None:
    assert v.ENTRY_RANGE in broken(mutate)


@pytest.mark.parametrize(
    "entries",
    [entry("256", "255", "6", 1), entry("6", "256", "6", 1), entry("6", "255", "256", 1)],
)
def test_entry_range_ternary_and_exact(entries: str) -> None:
    assert v.ENTRY_RANGE in codes(with_acl(entries))


def test_entry_priority_on_non_ternary_table() -> None:
    assert v.ENTRY_PRIORITY in broken(lambda p: setattr(route(p).const_entries[0], "priority", 5))


@pytest.mark.parametrize(
    "entries",
    [
        # identical
        entry("6", "255", "6", 1) + entry("6", "255", "6", 1),
        # one covers the other
        entry("6", "255", "6", 1) + entry("0", "0", "6", 1),
        # partial masks that agree where both care
        entry("6", "15", "6", 1) + entry("16", "240", "6", 1),
    ],
)
def test_entry_priority_overlap(entries: str) -> None:
    assert codes(with_acl(entries)) == [v.ENTRY_PRIORITY]


@pytest.mark.parametrize(
    "entries",
    [
        # disjoint ternary values
        entry("6", "255", "6", 1) + entry("17", "255", "6", 1),
        # disjoint exact values
        entry("0", "0", "6", 1) + entry("0", "0", "17", 1),
        # overlapping but different priorities
        entry("6", "255", "6", 1) + entry("0", "0", "6", 2),
    ],
)
def test_entry_priority_no_overlap(entries: str) -> None:
    assert codes(with_acl(entries)) == []


def test_entry_duplicate() -> None:
    def mutate(p: pb.Program) -> None:
        second = route(p).const_entries.add()
        second.CopyFrom(route(p).const_entries[0])
        second.keys[0].lpm.value = "167772160"
        second.keys[0].lpm.prefix_len = 8

    assert v.ENTRY_DUPLICATE in broken(mutate)


def test_lpm_entry_must_be_canonical() -> None:
    def mutate(p: pb.Program) -> None:
        # 10.0.0.1/8: a set bit below the prefix
        route(p).const_entries[0].keys[0].lpm.value = "167772161"
        route(p).const_entries[0].keys[0].lpm.prefix_len = 8

    assert v.ENTRY_RANGE in broken(mutate)


def test_ternary_entry_must_be_canonical() -> None:
    assert v.ENTRY_RANGE in codes(with_acl(entry("22", "240", "6", 1)))


def test_lpm_entries_with_different_prefixes_are_fine() -> None:
    def mutate(p: pb.Program) -> None:
        second = route(p).const_entries.add()
        second.CopyFrom(route(p).const_entries[0])
        second.keys[0].lpm.prefix_len = 16

    assert broken(mutate) == []


@pytest.mark.parametrize("key", [META_COLOR, META_DROP])
def test_table_keys_are_bits_only(key: str) -> None:
    """A boolean or enum key is elaborated by the frontend into a cast."""

    def mutate(p: pb.Program) -> None:
        route(p).keys[0].expr.CopyFrom(expr(key))

    assert v.KEY_TYPE in broken(mutate)


def test_apply_inside_an_action_is_rejected() -> None:
    def mutate(p: pb.Program) -> None:
        p.blocks[ING].actions[0].body.add().CopyFrom(stmt('apply { table: "route" }'))

    assert v.BLOCK_KIND_STMT in broken(mutate)


def test_derived_key_names_collide() -> None:
    def mutate(p: pb.Program) -> None:
        route(p).keys[0].name = ""  # both keys now derive hdr.ipv4.dst
        key = route(p).keys.add(match_kind=pb.MATCH_KIND_EXACT)
        key.expr.CopyFrom(route(p).keys[0].expr)
        route(p).const_entries[0].keys.add(exact="1")

    assert v.KEY_NAME in broken(mutate)


# -- externs -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.extern_instances[0].ClearField("args"),
        lambda p: p.extern_instances[0].args.add(boolean=True),
        lambda p: setattr(p.extern_instances[0].args[0].bits, "width", 8),
        lambda p: p.extern_instances[0].args[0].CopyFrom(pb.Literal(boolean=True)),
    ],
)
def test_extern_args(mutate) -> None:
    assert v.EXTERN_ARGS in broken(mutate)


# -- the corpus ------------------------------------------------------------------


CORPUS = Path(__file__).parent.parent / "corpus"


@pytest.mark.parametrize("program", sorted(CORPUS.glob("*/*.txtpb")), ids=lambda p: p.stem)
def test_corpus_programs_validate(program: Path) -> None:
    assert v.validate(ir.load_text(program)) == []
