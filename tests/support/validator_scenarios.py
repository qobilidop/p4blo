"""Reusable valid and malformed validator inputs, with an explicit scenario catalog.

Builders only construct programs. Python tests retain their code/path/message
assertions; Lean conformance consumes these same programs without invoking or
patching collected test functions.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from google.protobuf import text_format

from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
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
  # 6-9: stack push, indexed write, indexed read, setValid
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
    value { cast { to { bits: 32 } operand { member {
      base { index {
        base { member { base { var: "hdr" } field: "vlan" } }
        index { literal { bits { width: 32 value: "1" } } }
      } }
      field: "vid"
    } } } }
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


def valid() -> apb.BlockAssembly:
    return arch_wire.load_text(VALID)


# Text-format builders keep malformed statements concise.
def stmt(text: str) -> pb.Stmt:
    return text_format.Parse(text, pb.Stmt())


def expr(text: str) -> pb.Expr:
    return text_format.Parse(text, pb.Expr())


def add_stmt(program: apb.BlockAssembly, block: int, text: str) -> apb.BlockAssembly:
    """Append a statement to a control or deparser body."""
    program.blocks[block].body.add().CopyFrom(stmt(text))
    return program


def add_parser_stmt(program: apb.BlockAssembly, state: int, text: str) -> apb.BlockAssembly:
    """Append a statement to a parser state's body."""
    program.blocks[PRS].states[state].body.add().CopyFrom(stmt(text))
    return program


def mutated(mutate: Callable[[apb.BlockAssembly], object]) -> apb.BlockAssembly:
    program = valid()
    mutate(program)
    return program


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


VLAN_LAST_INDEX = f"last_index {{ stack {{ {HDR_VLAN} }} }}"


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


def swap_errors(p: apb.BlockAssembly) -> None:
    p.errors[1], p.errors[2] = p.errors[2], p.errors[1]


def shift_amount(p: apb.BlockAssembly) -> pb.BitsLiteral:
    return p.blocks[ING].body[12].assign.value.binary.right.literal.bits


VLAN_NEXT = f"next {{ stack {{ {HDR_VLAN} }} }}"


def with_helper(program: apb.BlockAssembly, kind: int) -> apb.BlockAssembly:
    """Add an unexported block `fix` of `kind` taking `(in H)`."""
    helper = program.blocks.add(name="fix", kind=kind)
    helper.params.add(name="h", type=pb.Type(struct="H"), direction=pb.DIRECTION_IN)
    return program


def read_bits16(program: apb.BlockAssembly) -> None:
    """Make Counter.read take and return bit<16>, so header fields fit."""
    program.extern_types[0].methods[1].params[0].type.bits = 16
    program.extern_types[0].methods[1].params[1].type.bits = 16
    del program.blocks[ING].body[4]


VLAN_TYPE_AT_IDX = member(index(HDR_VLAN, IDX), "type")


VLAN_TYPE_AT_0 = member(index(HDR_VLAN, lit(32, "0")), "type")


VLAN_TYPE_AT_1 = member(index(HDR_VLAN, lit(32, "1")), "type")


def with_two(program: apb.BlockAssembly) -> apb.BlockAssembly:
    """Add an action `two(inout bit<16> a, inout bit<16> b)` to `ing`, and
    make Counter.read take bit<16>, so header fields fit both."""
    action = program.blocks[ING].actions.add(name="two")
    action.params.add(name="a", type=pb.Type(bits=16), direction=pb.DIRECTION_INOUT)
    action.params.add(name="b", type=pb.Type(bits=16), direction=pb.DIRECTION_INOUT)
    read_bits16(program)
    return program


def start_select(p: apb.BlockAssembly) -> pb.Select:
    return p.blocks[PRS].states[START].transition.select


def route(p: apb.BlockAssembly) -> pb.Table:
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


def with_acl(entries: str) -> apb.BlockAssembly:
    program = valid()
    program.blocks[ING].tables.add().CopyFrom(acl_table(entries))
    add_stmt(program, ING, 'apply { table: "acl" }')
    return program


def no_action(p: apb.BlockAssembly) -> pb.Action:
    return p.blocks[ING].actions.add(name="NoAction")


CORPUS = Path(__file__).resolve().parents[2] / "tests/programs/corpus"


NAME_DUPLICATE_PARAMETERS_0 = [
    lambda p: p.struct_types.add(name="H"),
    lambda p: p.blocks[ING].locals.add(name="hit", type=pb.Type(bits=1)),
    lambda p: (
        p.blocks[ING]
        .actions[1]
        .params.add(name="idx", type=pb.Type(bits=1), direction=pb.DIRECTION_NONE)
    ),
    lambda p: p.errors.append("NoError"),
    lambda p: p.header_types[0].fields.add(name="dst", type=pb.Type(bits=1)),
    lambda p: p.enum_types[0].members.append("RED"),
    lambda p: p.extern_types[0].methods.add(name="count"),
    lambda p: (
        p.extern_types[0]
        .methods[1]
        .params.add(name="idx", type=pb.Type(bits=1), direction=pb.DIRECTION_IN)
    ),
]


NAME_EMPTY_PARAMETERS_0 = [
    lambda p: setattr(p.blocks[PRS], "name", ""),
    lambda p: setattr(p.header_types[0].fields[0], "name", ""),
    lambda p: p.enum_types[0].members.append(""),
    lambda p: setattr(p.extern_types[0].methods[0], "name", ""),
]


ERROR_LIST_PARAMETERS_0 = [
    lambda p: p.errors.__delitem__(0),
    swap_errors,
    lambda p: p.errors.insert(0, "Mine"),
]


REF_UNRESOLVED_PARAMETERS_0 = [
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
    lambda p: setattr(p.blocks[PRS].states[START].transition.select.cases[0].target, "state", "x"),
    lambda p: setattr(p.blocks[ING].body[0].conditional.then[0].apply, "table", "nope"),
    lambda p: setattr(p.blocks[ING].body[0].conditional.otherwise[0].call_action, "action", "nope"),
    lambda p: setattr(p.blocks[ING].tables[0].default_action, "action", "nope"),
    lambda p: p.blocks[ING].tables[0].actions.append("nope"),
    lambda p: add_stmt(p, DEP, 'emit { value { literal { error: "nope" } } }'),
]


REF_KIND_PARAMETERS_0 = [
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
]


SCOPE_VAR_PARAMETERS_0 = [
    lambda p: add_stmt(p, SUB, assign(HDR, IDX)),
    lambda p: add_stmt(p, ING, assign(IDX, var("port"))),
    lambda p: p.blocks[ING].actions[0].body.add().CopyFrom(stmt(assign(IDX, var("dec")))),
]


SCOPE_DECL_PARAMETERS_0 = [
    lambda p: add_stmt(p, SUB, 'apply { table: "route" }'),
    lambda p: add_stmt(p, SUB, call_action("drop")),
]


EXPORT_SIGNATURE_PARAMETERS_0 = [
    lambda p: setattr(p.blocks[PRS].params[0], "direction", pb.DIRECTION_INOUT),
    lambda p: setattr(p.blocks[ING].params[0], "direction", pb.DIRECTION_IN),
    lambda p: setattr(p.blocks[DEP].params[0], "direction", pb.DIRECTION_INOUT),
    lambda p: p.blocks[DEP].params.add(
        name="m", type=pb.Type(struct="M"), direction=pb.DIRECTION_IN
    ),
    lambda p: setattr(p.blocks[ING].params[1].type, "struct", "H"),
    lambda p: p.blocks[PRS].params.__delitem__(1),
]


TYPE_INVALID_PARAMETERS_0 = [
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
]


LITERAL_FORMAT_PARAMETERS_0 = [
    lambda p: setattr(shift_amount(p), "value", "abc"),
    lambda p: setattr(shift_amount(p), "value", "-1"),
    lambda p: setattr(shift_amount(p), "value", " 1"),
    lambda p: setattr(shift_amount(p), "value", "0x1"),
    lambda p: setattr(shift_amount(p), "value", ""),
    lambda p: p.blocks[ING].body[12].assign.value.binary.right.literal.Clear(),
]


LITERAL_RANGE_PARAMETERS_0 = [
    lambda p: setattr(shift_amount(p), "value", "256"),
    lambda p: setattr(shift_amount(p), "width", 0),
    lambda p: setattr(p.blocks[ING].tables[0].const_entries[0].action.args[0].bits, "value", "512"),
    lambda p: setattr(
        p.blocks[PRS].states[START].transition.select.cases[0].sets[0].exact.bits, "value", "65536"
    ),
]


BLOCK_KIND_SHAPE_PARAMETERS_0 = [
    lambda p: setattr(p.blocks[ING], "kind", pb.BLOCK_KIND_UNSPECIFIED),
    lambda p: add_stmt(p, PRS, f"advance {{ bits {{ {B8} }} }}"),
    lambda p: p.blocks[PRS].ClearField("states"),
    lambda p: p.blocks[PRS].actions.add(name="a"),
    lambda p: p.blocks[PRS].tables.add(name="t", actions=["a"]),
    lambda p: p.blocks[ING].states.add(name="s"),
    lambda p: setattr(p.blocks[ING], "start_state", "s"),
    lambda p: setattr(p.blocks[DEP], "start_state", "s"),
]


PARSER_START_STATE_PARAMETERS_0 = ["nope", "", "tmp"]


BLOCK_KIND_STMT_IN_CONTROL_OR_DEPARSER_PARAMETERS_0 = [
    (ING, f"emit {{ value {{ {HDR_IPV4} }} }}"),
    (ING, f"extract {{ target {{ {HDR_IPV4} }} }}"),
    (ING, f"advance {{ bits {{ {IDX} }} }}"),
    (ING, f'verify {{ condition {{ {HIT} }} error: "NoMatch" }}'),
    (DEP, call_action("x")),
    (DEP, 'apply { table: "x" }'),
]


BLOCK_KIND_STMT_IN_PARSER_PARAMETERS_0 = [
    'apply { table: "x" }',
    call_action("x"),
    f"emit {{ value {{ {HDR_IPV4} }} }}",
]


BLOCK_KIND_STMT_IN_ACTION_PARAMETERS_0 = [
    f"emit {{ value {{ {HDR_IPV4} }} }}",
    'apply { table: "route" }',
    call_block("sub", arg_out(HDR), arg_out(META)),
]


PARSER_ONLY_PARAMETERS_0 = [
    (ING, assign(T16, "lookahead { type { bits: 16 } }")),
    (DEP, 'emit { value { lookahead { type { header: "eth" } } } }'),
    (ING, assign(IDX, VLAN_LAST_INDEX)),
    (SUB, f"set_valid {{ header {{ {index(HDR_VLAN, VLAN_LAST_INDEX)} }} }}"),
]


NEXT_ONLY_EXTRACT_IN_A_PARSER_PARAMETERS_0 = [
    assign(VLAN_NEXT, index(HDR_VLAN, lit(32, "0"))),
    f"set_valid {{ header {{ {VLAN_NEXT} }} }}",
    assign(member(VLAN_NEXT, "vid"), lit(12, "1")),
    call_extern("read", arg_in(lit(32, "1")), arg_out(VLAN_NEXT)),
]


PARAM_DIRECTION_PARAMETERS_0 = [
    lambda p: setattr(p.blocks[SUB].params[0], "direction", pb.DIRECTION_NONE),
    lambda p: setattr(p.blocks[SUB].params[0], "direction", pb.DIRECTION_UNSPECIFIED),
    lambda p: setattr(p.blocks[ING].actions[1].params[0], "direction", pb.DIRECTION_UNSPECIFIED),
    lambda p: setattr(p.blocks[ING].actions[1].params[0], "direction", pb.DIRECTION_IN),
    lambda p: setattr(p.extern_types[0].constructor_params[0], "direction", pb.DIRECTION_OUT),
    lambda p: setattr(p.extern_types[0].constructor_params[0], "direction", pb.DIRECTION_NONE),
    lambda p: setattr(p.extern_types[0].methods[0].params[0], "direction", pb.DIRECTION_NONE),
]


EXPR_INVALID_PARAMETERS_0 = [
    assign(IDX, ""),
    assign("", IDX),
    assign(HIT, unary("UNSPECIFIED", HIT)),
    assign(IDX, binary("UNSPECIFIED", IDX, IDX)),
]


TYPE_MISMATCH_IN_CONTROL_PARAMETERS_0 = [
    assign(IDX, B8),
    assign(HIT, B8),
    assign(HDR_IPV4, HDR_ETH),
    f"conditional {{ condition {{ {B8} }} }}",
    assign(HIT, unary("NOT", B8)),
    assign(HIT, unary("COMPLEMENT", TRUE)),
    assign(HIT, unary("NEGATE", TRUE)),
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
    assign(T16, mux(B8, B16, B16)),
    assign(T16, mux(TRUE, B16, B8)),
    assign(IDX, member(IDX, "x")),
    assign(IDX, member(index(HDR_IPV4, IDX), "ttl")),
    assign(IDX, member(index(HDR_VLAN, HIT), "vid")),
    assign(IDX, f"last_index {{ stack {{ {HDR_IPV4} }} }}"),
    assign(HIT, f"is_valid {{ header {{ {HDR} }} }}"),
    f"set_valid {{ header {{ {TTL} }} }}",
    f"set_invalid {{ header {{ {META} }} }}",
    f"push {{ stack {{ {HDR_IPV4} }} count: 1 }}",
    f"pop {{ stack {{ {META_DROP} }} count: 1 }}",
    f'apply {{ table: "route" hit {{ {IDX} }} }}',
    assign(HIT, f"slice {{ operand {{ {TRUE} }} hi: 0 lo: 0 }}"),
    f"set_valid {{ header {{ {index(HDR_VLAN, HIT)} }} }}",
    f"set_valid {{ header {{ {index(HDR_IPV4, IDX)} }} }}",
]


TYPE_MISMATCH_IN_PARSER_PARAMETERS_0 = [
    f"extract {{ target {{ {TTL} }} }}",
    f"extract {{ target {{ {HDR} }} }}",
    f"extract {{ target {{ next {{ stack {{ {HDR_IPV4} }} }} }} }}",
    f"advance {{ bits {{ {TRUE} }} }}",
    f"advance {{ bits {{ {B8} }} }}",
    f'verify {{ condition {{ {B8} }} error: "NoMatch" }}',
    assign(TMP, 'lookahead { type { struct: "M" } }'),
    assign(TMP, 'lookahead { type { stack { header: "vlan" size: 2 } } }'),
    assign(TMP, f"lookahead {{ type {{ {BOOL} }} }}"),
]


TYPE_MISMATCH_IN_DEPARSER_PARAMETERS_0 = [
    f"emit {{ value {{ {TTL} }} }}",
    f"emit {{ value {{ {TRUE} }} }}",
]


CAST_INVALID_PARAMETERS_0 = [
    assign(IDX, cast("bits: 32", TRUE)),
    assign(HIT, cast(BOOL, B8)),
    assign(IDX, cast("bits: 32", HDR_IPV4)),
    assign(HIT, cast(BOOL, TRUE)),
    assign(HDR_IPV4, cast('header: "ipv4"', B8)),
]


SLICE_RANGE_PARAMETERS_0 = [(32, 0), (0, 1), (31, 32), (40, 40)]


LVALUE_READONLY_PARAMETERS_0 = [
    lambda p: add_stmt(p, DEP, assign(TTL, B8)),
    lambda p: add_stmt(p, DEP, f"set_invalid {{ header {{ {HDR_ETH} }} }}"),
    lambda p: p.blocks[ING].actions[1].body.add().CopyFrom(stmt(assign(var("dec"), B8))),
    lambda p: add_stmt(p, DEP, call_block("sub", arg_out(HDR), arg_out(HDR))),
]


STACK_COUNT_PARAMETERS_0 = [
    f"push {{ stack {{ {HDR_VLAN} }} count: 0 }}",
    f"pop {{ stack {{ {HDR_VLAN} }} }}",
]


ARG_COUNT_PARAMETERS_0 = [
    call_block("sub", arg_out(HDR)),
    call_action("fwd", arg_in(lit(9, "1"))),
    call_extern("count"),
    call_extern("size", arg_in(IDX), result=VAL),
]


ARG_DIRECTION_PARAMETERS_0 = [
    call_block("sub", arg_in(HDR), arg_out(META)),
    call_extern("count", arg_out(IDX)),
    call_extern("read", arg_in(IDX), arg_in(VAL)),
    call_extern("count", "args {}"),
    call_action("fwd", arg_out(IDX), arg_in(B8)),
]


ARG_TYPE_PARAMETERS_0 = [
    call_block("sub", arg_out(META), arg_out(HDR)),
    call_extern("count", arg_in(T16)),
    call_extern("read", arg_in(IDX), arg_out(T16)),
    call_action("fwd", arg_in(B8), arg_in(B8)),
]


CALL_KIND_PARAMETERS_0 = [
    lambda p: add_stmt(p, ING, call_block("prs", arg_out(HDR), arg_out(META))),
    lambda p: add_stmt(p, DEP, call_block("prs", arg_out(HDR), arg_out(HDR))),
    lambda p: add_parser_stmt(p, PARSE_IPV4, call_block("sub", arg_out(HDR), arg_out(META))),
    lambda p: add_stmt(with_helper(p, pb.BLOCK_KIND_CONTROL), DEP, call_block("fix", arg_in(HDR))),
    lambda p: add_stmt(with_helper(p, pb.BLOCK_KIND_DEPARSER), ING, call_block("fix", arg_in(HDR))),
]


CALL_ALIAS_PARAMETERS_0 = [
    call_block("sub", arg_out(HDR), arg_out(HDR)),
    call_action("two", arg_out(T16), arg_out(T16)),
    call_action("two", arg_out(member(HDR_ETH, "type")), arg_out(member(HDR_ETH, "type"))),
    call_action("two", arg_out(VLAN_TYPE_AT_IDX), arg_out(VLAN_TYPE_AT_1)),
    call_action("two", arg_out(VLAN_TYPE_AT_1), arg_out(VLAN_TYPE_AT_IDX)),
]


NO_ALIAS_PARAMETERS_0 = [
    call_extern("read", arg_in(T16), arg_out(T16)),
    call_extern("read", arg_in(member(HDR_ETH, "type")), arg_out(member(HDR_ETH, "type"))),
    call_extern("read", arg_in(VLAN_TYPE_AT_IDX), arg_out(VLAN_TYPE_AT_1)),
    call_extern("read", arg_in(VLAN_TYPE_AT_1), arg_out(VLAN_TYPE_AT_IDX)),
    call_action("two", arg_out(member(HDR_ETH, "type")), arg_out(VLAN_TYPE_AT_0)),
    call_action("two", arg_out(VLAN_TYPE_AT_0), arg_out(VLAN_TYPE_AT_1)),
]


CALL_CYCLE_PARAMETERS_0 = [
    lambda p: add_stmt(p, SUB, call_block("ing", arg_out(HDR), arg_out(META))),
    lambda p: add_stmt(p, SUB, call_block("sub", arg_out(HDR), arg_out(META))),
]


EXTERN_RESULT_PARAMETERS_0 = [
    call_extern("size"),
    call_extern("count", arg_in(IDX), result=VAL),
    call_extern("size", result=T16),
]


PARSER_TRANSITION_PARAMETERS_0 = [
    lambda p: p.blocks[PRS].states[PARSE_IPV4].ClearField("transition"),
    lambda p: p.blocks[PRS].states[PARSE_IPV4].transition.direct.Clear(),
    lambda p: start_select(p).cases[0].target.Clear(),
]


SELECT_ARITY_PARAMETERS_0 = [
    lambda p: start_select(p).ClearField("keys"),
    lambda p: start_select(p).cases[0].sets.add().dont_care.SetInParent(),
    lambda p: start_select(p).cases[3].ClearField("sets"),
]


SELECT_TYPE_PARAMETERS_0 = [
    lambda p: setattr(start_select(p).cases[0].sets[0].exact.bits, "width", 8),
    lambda p: setattr(start_select(p).cases[1].sets[0].masked.mask.bits, "width", 8),
    lambda p: setattr(start_select(p).cases[2].sets[0].range.hi.bits, "width", 32),
    lambda p: start_select(p).cases[0].sets[0].exact.CopyFrom(pb.Literal(boolean=True)),
    lambda p: start_select(p).cases[0].sets[0].Clear(),
    lambda p: start_select(p).keys[0].CopyFrom(expr(META_DROP)),
    lambda p: start_select(p).keys[0].CopyFrom(expr(META)),
]


KEY_TYPE_PARAMETERS_0 = [
    lambda p: route(p).keys[0].expr.CopyFrom(expr(META_DROP)),
    lambda p: setattr(route(p).keys[0], "match_kind", pb.MATCH_KIND_UNSPECIFIED),
    lambda p: route(p).keys.add(match_kind=pb.MATCH_KIND_EXACT).expr.CopyFrom(expr(HDR_IPV4)),
    lambda p: route(p).keys.add(match_kind=pb.MATCH_KIND_TERNARY).expr.CopyFrom(expr(HIT)),
]


TABLE_ACTIONS_PARAMETERS_0 = [
    lambda p: route(p).ClearField("actions"),
    lambda p: route(p).actions.append("fwd"),
    lambda p: route(p).actions.remove("drop"),
    lambda p: route(p).actions.remove("fwd"),
]


NOACTION_RESERVED_PARAMETERS_0 = [
    lambda p: no_action(p).body.add().CopyFrom(p.blocks[ING].actions[0].body[0]),
    lambda p: no_action(p).params.add(
        name="port", type=pb.Type(bits=9), direction=pb.DIRECTION_NONE
    ),
]


ACTION_ARGS_PARAMETERS_0 = [
    lambda p: setattr(route(p).default_action, "action", "fwd"),
    lambda p: route(p).default_action.args.add(boolean=True),
    lambda p: route(p).const_entries[0].action.args.pop(),
    lambda p: setattr(route(p).const_entries[0].action.args[0].bits, "width", 8),
    lambda p: route(p).const_entries[0].action.args[1].CopyFrom(pb.Literal(boolean=True)),
]


ENTRY_SHAPE_PARAMETERS_0 = [
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
]


ENTRY_SHAPE_TERNARY_AND_EXACT_PARAMETERS_0 = [
    entry("6", "x", "6", 1),
    entry("6", "255", "true", 1),
    entry("6", "255", "", 1),
]


ENTRY_RANGE_PARAMETERS_0 = [
    lambda p: setattr(route(p).const_entries[0].keys[0].lpm, "value", "4294967296"),
    lambda p: setattr(route(p).const_entries[0].keys[0].lpm, "prefix_len", 33),
]


ENTRY_RANGE_TERNARY_AND_EXACT_PARAMETERS_0 = [
    entry("256", "255", "6", 1),
    entry("6", "256", "6", 1),
    entry("6", "255", "256", 1),
]


ENTRY_PRIORITY_OVERLAP_PARAMETERS_0 = [
    entry("6", "255", "6", 1) + entry("6", "255", "6", 1),
    entry("6", "255", "6", 1) + entry("0", "0", "6", 1),
    entry("6", "15", "6", 1) + entry("16", "240", "6", 1),
]


ENTRY_PRIORITY_NO_OVERLAP_PARAMETERS_0 = [
    entry("6", "255", "6", 1) + entry("17", "255", "6", 1),
    entry("0", "0", "6", 1) + entry("0", "0", "17", 1),
    entry("6", "255", "6", 1) + entry("0", "0", "6", 2),
]


TABLE_KEYS_ARE_BITS_ONLY_PARAMETERS_0 = [META_COLOR, META_DROP]


EXTERN_ARGS_PARAMETERS_0 = [
    lambda p: p.extern_instances[0].ClearField("args"),
    lambda p: p.extern_instances[0].args.add(boolean=True),
    lambda p: setattr(p.extern_instances[0].args[0].bits, "width", 8),
    lambda p: p.extern_instances[0].args[0].CopyFrom(pb.Literal(boolean=True)),
]


def valid_program_has_no_diagnostics() -> apb.BlockAssembly:
    return valid()


def check_returns_index() -> apb.BlockAssembly:
    return valid()


def check_raises_with_diagnostics() -> apb.BlockAssembly:
    program = valid()
    program.headers = "nope"
    return program


def diagnostic_paths_are_protobuf_style() -> apb.BlockAssembly:
    program = valid()
    program.blocks[ING].body[2].assign.value.cast.to.bits = 16
    return program


def nested_path() -> apb.BlockAssembly:
    program = valid()
    mask = program.blocks[PRS].states[START].transition.select.cases[1].sets[0].masked.mask
    mask.bits.width, mask.bits.value = (8, "255")
    return program


def name_duplicate(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def name_empty(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def index_failure_stops_validation() -> apb.BlockAssembly:
    program = valid()
    program.struct_types.add(name="H")
    program.blocks[ING].body[2].assign.value.cast.to.bits = 16
    return program


def error_list(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def ref_unresolved(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def ref_kind(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def scope_var(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def scope_decl(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def scope_decl_state_of_another_parser() -> apb.BlockAssembly:
    program = valid()
    other = program.blocks.add()
    other.CopyFrom(program.blocks[PRS])
    other.name = "prs2"
    other.states[START].transition.direct.state = "parse_vlan"
    del other.states[PARSE_VLAN:]
    return program


def export_duplicate() -> apb.BlockAssembly:
    return mutated(lambda p: p.exports.add(role="parser", block="prs"))


def export_signature(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def unexported_block_may_have_any_signature() -> apb.BlockAssembly:
    program = valid()
    del program.blocks[SUB].params[1]
    program.blocks[SUB].ClearField("body")
    del program.blocks[ING].body[13].call_block.args[1]
    return program


def type_invalid(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def struct_cycle_through_another_struct() -> apb.BlockAssembly:
    program = valid()
    program.struct_types.add(name="A").fields.add(name="b", type=pb.Type(struct="B"))
    program.struct_types.add(name="B").fields.add(name="a", type=pb.Type(struct="A"))
    return program


def literal_format(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def literal_range(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def block_kind_shape(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def parser_start_state(start: str) -> apb.BlockAssembly:
    return mutated(lambda p: setattr(p.blocks[PRS], "start_state", start))


def block_kind_stmt_in_control_or_deparser(block: int, text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, block, text))


def block_kind_stmt_in_parser(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_parser_stmt(p, PARSE_IPV4, text))


def block_kind_stmt_in_action(text: str) -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        p.blocks[ING].actions[0].body.add().CopyFrom(stmt(text))

    return mutated(mutate)


def parser_only(block: int, text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, block, text))


def last_index_in_an_action_is_parser_only() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        body = p.blocks[ING].actions[0].body.add()
        body.CopyFrom(stmt(assign(IDX, VLAN_LAST_INDEX)))

    return mutated(mutate)


def last_index_in_a_parser_is_fine() -> apb.BlockAssembly:
    program = valid()
    last = index(HDR_VLAN, VLAN_LAST_INDEX)
    add_parser_stmt(program, PARSE_IPV4, assign(TMP, cast("bits: 16", VLAN_LAST_INDEX)))
    add_parser_stmt(program, PARSE_IPV4, f"set_valid {{ header {{ {last} }} }}")
    return program


def next_only_extract_in_a_parser(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_parser_stmt(p, PARSE_VLAN, text))


def next_only_extract_in_a_control() -> apb.BlockAssembly:
    text = f"set_valid {{ header {{ {VLAN_NEXT} }} }}"
    return mutated(lambda p: add_stmt(p, ING, text))


def param_direction(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def action_with_directed_params_is_fine_when_only_called() -> apb.BlockAssembly:
    program = valid()
    action = program.blocks[ING].actions.add(name="bump")
    action.params.add(name="x", type=pb.Type(bits=32), direction=pb.DIRECTION_INOUT)
    action.body.add().CopyFrom(stmt(assign(var("x"), binary("ADD", var("x"), B32))))
    add_stmt(program, ING, call_action("bump", arg_out(IDX)))
    return program


def expr_invalid(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def stmt_invalid() -> apb.BlockAssembly:
    return mutated(lambda p: p.blocks[ING].body.add())


def type_mismatch_in_control(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def type_mismatch_in_parser(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_parser_stmt(p, PARSE_IPV4, text))


def lookahead_of_bits_boolean_and_header_is_fine() -> apb.BlockAssembly:
    program = valid()
    add_parser_stmt(program, PARSE_IPV4, assign(META_DROP, f"lookahead {{ type {{ {BOOL} }} }}"))
    add_parser_stmt(program, PARSE_IPV4, assign(HDR_ETH, 'lookahead { type { header: "eth" } }'))
    return program


def type_mismatch_in_deparser(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, DEP, text))


def emit_of_struct_with_scalar_field_is_rejected() -> apb.BlockAssembly:
    program = valid()
    program.blocks[DEP].params.add(name="meta", type=pb.Type(struct="M"), direction=pb.DIRECTION_IN)
    del program.exports[2]
    add_stmt(program, DEP, f"emit {{ value {{ {META} }} }}")
    return program


def emit_of_headers_struct_is_fine() -> apb.BlockAssembly:
    return add_stmt(valid(), DEP, f"emit {{ value {{ {HDR} }} }}")


def cast_invalid(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def bit1_and_boolean_casts_are_fine() -> apb.BlockAssembly:
    program = valid()
    add_stmt(program, ING, assign(HIT, cast(BOOL, lit(1, "1"))))
    add_stmt(program, ING, assign(IDX, cast("bits: 32", cast("bits: 1", HIT))))
    return program


def slice_range(hi: int, lo: int) -> apb.BlockAssembly:
    text = assign(IDX, f"slice {{ operand {{ {IDX} }} hi: {hi} lo: {lo} }}")
    return mutated(lambda p: add_stmt(p, ING, text))


def slice_width() -> apb.BlockAssembly:
    text = assign(T16, f"slice {{ operand {{ {IDX} }} hi: 31 lo: 16 }}")
    return add_stmt(valid(), ING, text)


def lvalue_readonly(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def stack_count(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def arg_count(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def arg_direction(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def arg_type(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def call_kind(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def deparser_may_call_a_deparser() -> apb.BlockAssembly:
    program = with_helper(valid(), pb.BLOCK_KIND_DEPARSER)
    add_stmt(program, len(program.blocks) - 1, f"emit {{ value {{ {member(var('h'), 'eth')} }} }}")
    add_stmt(program, DEP, call_block("fix", arg_in(HDR)))
    return program


def call_alias(text: str) -> apb.BlockAssembly:
    program = with_two(valid())
    add_stmt(program, ING, text)
    return program


def no_alias(text: str) -> apb.BlockAssembly:
    program = with_two(valid())
    add_stmt(program, ING, text)
    return program


def call_cycle(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def call_cycle_message_and_path() -> apb.BlockAssembly:
    program = add_stmt(valid(), SUB, call_block("ing", arg_out(HDR), arg_out(META)))
    return program


def action_call_cycle() -> apb.BlockAssembly:

    def recurse(p: apb.BlockAssembly) -> None:
        p.blocks[ING].actions[0].body.add().CopyFrom(stmt(call_action("drop")))

    return mutated(recurse)


def mutual_action_call_cycle_message_and_path() -> apb.BlockAssembly:
    program = valid()
    fwd = call_action("fwd", arg_in(lit(9, "1")), arg_in(B8))
    program.blocks[ING].actions[0].body.add().CopyFrom(stmt(fwd))
    program.blocks[ING].actions[1].body.add().CopyFrom(stmt(call_action("drop")))
    return program


def actions_may_call_actions_without_a_cycle() -> apb.BlockAssembly:
    program = valid()
    fwd = call_action("fwd", arg_in(lit(9, "1")), arg_in(B8))
    program.blocks[ING].actions[0].body.add().CopyFrom(stmt(fwd))
    return program


def extern_result(text: str) -> apb.BlockAssembly:
    return mutated(lambda p: add_stmt(p, ING, text))


def parser_transition(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def select_arity(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def select_type(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def select_on_boolean_and_enum_keys() -> apb.BlockAssembly:
    program = valid()
    select = program.blocks[PRS].states[PARSE_IPV4].transition.select
    select.keys.add().CopyFrom(expr(META_DROP))
    select.keys.add().CopyFrom(expr(META_COLOR))
    case = select.cases.add()
    case.sets.add().exact.boolean = True
    case.sets.add().exact.enum_member.CopyFrom(pb.EnumLiteral(enum_type="Color", member="RED"))
    case.target.accept.SetInParent()
    return program


def ternary_table_is_valid() -> apb.BlockAssembly:
    return with_acl(entry("64", "255", "6", 1) + entry("0", "0", "6", 2))


def key_name() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        key = route(p).keys.add(match_kind=pb.MATCH_KIND_EXACT, name="dst")
        key.expr.CopyFrom(expr(TTL))
        route(p).const_entries[0].keys.add(exact="1")

    return mutated(mutate)


def key_type(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def table_lpm_count() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        route(p).keys.add().CopyFrom(route(p).keys[0])
        route(p).keys[1].name = "dst2"

    return mutated(mutate)


def table_key_mix() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        route(p).keys.add(match_kind=pb.MATCH_KIND_TERNARY).expr.CopyFrom(expr(TTL))

    return mutated(mutate)


def table_actions(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def noaction_reserved(mutate) -> apb.BlockAssembly:
    """A declared NoAction is an ordinary action of the block, so the name
    is reserved for the one core.p4 means: empty and parameterless."""
    return mutated(mutate)


def an_empty_noaction_may_be_declared() -> apb.BlockAssembly:
    return mutated(no_action)


def action_args(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def entry_shape(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def entry_shape_ternary_and_exact(entries: str) -> apb.BlockAssembly:
    return with_acl(entries)


def entry_range(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


def entry_range_ternary_and_exact(entries: str) -> apb.BlockAssembly:
    return with_acl(entries)


def entry_priority_on_non_ternary_table() -> apb.BlockAssembly:
    return mutated(lambda p: setattr(route(p).const_entries[0], "priority", 5))


def entry_priority_overlap(entries: str) -> apb.BlockAssembly:
    return with_acl(entries)


def entry_priority_no_overlap(entries: str) -> apb.BlockAssembly:
    return with_acl(entries)


def entry_duplicate() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        second = route(p).const_entries.add()
        second.CopyFrom(route(p).const_entries[0])
        second.keys[0].lpm.value = "167772160"
        second.keys[0].lpm.prefix_len = 8

    return mutated(mutate)


def lpm_entry_must_be_canonical() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        route(p).const_entries[0].keys[0].lpm.value = "167772161"
        route(p).const_entries[0].keys[0].lpm.prefix_len = 8

    return mutated(mutate)


def ternary_entry_must_be_canonical() -> apb.BlockAssembly:
    return with_acl(entry("22", "240", "6", 1))


def lpm_entries_with_different_prefixes_are_fine() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        second = route(p).const_entries.add()
        second.CopyFrom(route(p).const_entries[0])
        second.keys[0].lpm.prefix_len = 16

    return mutated(mutate)


def table_keys_are_bits_only(key: str) -> apb.BlockAssembly:
    """A boolean or enum key is elaborated by the frontend into a cast."""

    def mutate(p: apb.BlockAssembly) -> None:
        route(p).keys[0].expr.CopyFrom(expr(key))

    return mutated(mutate)


def apply_inside_an_action_is_rejected() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        p.blocks[ING].actions[0].body.add().CopyFrom(stmt('apply { table: "route" }'))

    return mutated(mutate)


def derived_key_names_collide() -> apb.BlockAssembly:

    def mutate(p: apb.BlockAssembly) -> None:
        route(p).keys[0].name = ""
        key = route(p).keys.add(match_kind=pb.MATCH_KIND_EXACT)
        key.expr.CopyFrom(route(p).keys[0].expr)
        route(p).const_entries[0].keys.add(exact="1")

    return mutated(mutate)


def extern_args(mutate) -> apb.BlockAssembly:
    return mutated(mutate)


@dataclass(frozen=True)
class Case:
    name: str
    program: apb.BlockAssembly


# Names and axis order retain the historical conformance case identities.
SCENARIOS: list[tuple[str, Callable[..., apb.BlockAssembly], list[tuple[list[str], Any]]]] = [
    ("test_valid_program_has_no_diagnostics", valid_program_has_no_diagnostics, []),
    ("test_check_returns_index", check_returns_index, []),
    ("test_check_raises_with_diagnostics", check_raises_with_diagnostics, []),
    ("test_diagnostic_paths_are_protobuf_style", diagnostic_paths_are_protobuf_style, []),
    ("test_nested_path", nested_path, []),
    ("test_name_duplicate", name_duplicate, [(["mutate"], NAME_DUPLICATE_PARAMETERS_0)]),
    ("test_name_empty", name_empty, [(["mutate"], NAME_EMPTY_PARAMETERS_0)]),
    ("test_index_failure_stops_validation", index_failure_stops_validation, []),
    ("test_error_list", error_list, [(["mutate"], ERROR_LIST_PARAMETERS_0)]),
    ("test_ref_unresolved", ref_unresolved, [(["mutate"], REF_UNRESOLVED_PARAMETERS_0)]),
    ("test_ref_kind", ref_kind, [(["mutate"], REF_KIND_PARAMETERS_0)]),
    ("test_scope_var", scope_var, [(["mutate"], SCOPE_VAR_PARAMETERS_0)]),
    ("test_scope_decl", scope_decl, [(["mutate"], SCOPE_DECL_PARAMETERS_0)]),
    ("test_scope_decl_state_of_another_parser", scope_decl_state_of_another_parser, []),
    ("test_export_duplicate", export_duplicate, []),
    ("test_export_signature", export_signature, [(["mutate"], EXPORT_SIGNATURE_PARAMETERS_0)]),
    ("test_unexported_block_may_have_any_signature", unexported_block_may_have_any_signature, []),
    ("test_type_invalid", type_invalid, [(["mutate"], TYPE_INVALID_PARAMETERS_0)]),
    ("test_struct_cycle_through_another_struct", struct_cycle_through_another_struct, []),
    ("test_literal_format", literal_format, [(["mutate"], LITERAL_FORMAT_PARAMETERS_0)]),
    ("test_literal_range", literal_range, [(["mutate"], LITERAL_RANGE_PARAMETERS_0)]),
    ("test_block_kind_shape", block_kind_shape, [(["mutate"], BLOCK_KIND_SHAPE_PARAMETERS_0)]),
    ("test_parser_start_state", parser_start_state, [(["start"], PARSER_START_STATE_PARAMETERS_0)]),
    (
        "test_block_kind_stmt_in_control_or_deparser",
        block_kind_stmt_in_control_or_deparser,
        [(["block", "text"], BLOCK_KIND_STMT_IN_CONTROL_OR_DEPARSER_PARAMETERS_0)],
    ),
    (
        "test_block_kind_stmt_in_parser",
        block_kind_stmt_in_parser,
        [(["text"], BLOCK_KIND_STMT_IN_PARSER_PARAMETERS_0)],
    ),
    (
        "test_block_kind_stmt_in_action",
        block_kind_stmt_in_action,
        [(["text"], BLOCK_KIND_STMT_IN_ACTION_PARAMETERS_0)],
    ),
    ("test_parser_only", parser_only, [(["block", "text"], PARSER_ONLY_PARAMETERS_0)]),
    ("test_last_index_in_an_action_is_parser_only", last_index_in_an_action_is_parser_only, []),
    ("test_last_index_in_a_parser_is_fine", last_index_in_a_parser_is_fine, []),
    (
        "test_next_only_extract_in_a_parser",
        next_only_extract_in_a_parser,
        [(["text"], NEXT_ONLY_EXTRACT_IN_A_PARSER_PARAMETERS_0)],
    ),
    ("test_next_only_extract_in_a_control", next_only_extract_in_a_control, []),
    ("test_param_direction", param_direction, [(["mutate"], PARAM_DIRECTION_PARAMETERS_0)]),
    (
        "test_action_with_directed_params_is_fine_when_only_called",
        action_with_directed_params_is_fine_when_only_called,
        [],
    ),
    ("test_expr_invalid", expr_invalid, [(["text"], EXPR_INVALID_PARAMETERS_0)]),
    ("test_stmt_invalid", stmt_invalid, []),
    (
        "test_type_mismatch_in_control",
        type_mismatch_in_control,
        [(["text"], TYPE_MISMATCH_IN_CONTROL_PARAMETERS_0)],
    ),
    (
        "test_type_mismatch_in_parser",
        type_mismatch_in_parser,
        [(["text"], TYPE_MISMATCH_IN_PARSER_PARAMETERS_0)],
    ),
    (
        "test_lookahead_of_bits_boolean_and_header_is_fine",
        lookahead_of_bits_boolean_and_header_is_fine,
        [],
    ),
    (
        "test_type_mismatch_in_deparser",
        type_mismatch_in_deparser,
        [(["text"], TYPE_MISMATCH_IN_DEPARSER_PARAMETERS_0)],
    ),
    (
        "test_emit_of_struct_with_scalar_field_is_rejected",
        emit_of_struct_with_scalar_field_is_rejected,
        [],
    ),
    ("test_emit_of_headers_struct_is_fine", emit_of_headers_struct_is_fine, []),
    ("test_cast_invalid", cast_invalid, [(["text"], CAST_INVALID_PARAMETERS_0)]),
    ("test_bit1_and_boolean_casts_are_fine", bit1_and_boolean_casts_are_fine, []),
    ("test_slice_range", slice_range, [(["hi", "lo"], SLICE_RANGE_PARAMETERS_0)]),
    ("test_slice_width", slice_width, []),
    ("test_lvalue_readonly", lvalue_readonly, [(["mutate"], LVALUE_READONLY_PARAMETERS_0)]),
    ("test_stack_count", stack_count, [(["text"], STACK_COUNT_PARAMETERS_0)]),
    ("test_arg_count", arg_count, [(["text"], ARG_COUNT_PARAMETERS_0)]),
    ("test_arg_direction", arg_direction, [(["text"], ARG_DIRECTION_PARAMETERS_0)]),
    ("test_arg_type", arg_type, [(["text"], ARG_TYPE_PARAMETERS_0)]),
    ("test_call_kind", call_kind, [(["mutate"], CALL_KIND_PARAMETERS_0)]),
    ("test_deparser_may_call_a_deparser", deparser_may_call_a_deparser, []),
    ("test_call_alias", call_alias, [(["text"], CALL_ALIAS_PARAMETERS_0)]),
    ("test_no_alias", no_alias, [(["text"], NO_ALIAS_PARAMETERS_0)]),
    ("test_call_cycle", call_cycle, [(["mutate"], CALL_CYCLE_PARAMETERS_0)]),
    ("test_call_cycle_message_and_path", call_cycle_message_and_path, []),
    ("test_action_call_cycle", action_call_cycle, []),
    (
        "test_mutual_action_call_cycle_message_and_path",
        mutual_action_call_cycle_message_and_path,
        [],
    ),
    ("test_actions_may_call_actions_without_a_cycle", actions_may_call_actions_without_a_cycle, []),
    ("test_extern_result", extern_result, [(["text"], EXTERN_RESULT_PARAMETERS_0)]),
    ("test_parser_transition", parser_transition, [(["mutate"], PARSER_TRANSITION_PARAMETERS_0)]),
    ("test_select_arity", select_arity, [(["mutate"], SELECT_ARITY_PARAMETERS_0)]),
    ("test_select_type", select_type, [(["mutate"], SELECT_TYPE_PARAMETERS_0)]),
    ("test_select_on_boolean_and_enum_keys", select_on_boolean_and_enum_keys, []),
    ("test_ternary_table_is_valid", ternary_table_is_valid, []),
    ("test_key_name", key_name, []),
    ("test_key_type", key_type, [(["mutate"], KEY_TYPE_PARAMETERS_0)]),
    ("test_table_lpm_count", table_lpm_count, []),
    ("test_table_key_mix", table_key_mix, []),
    ("test_table_actions", table_actions, [(["mutate"], TABLE_ACTIONS_PARAMETERS_0)]),
    ("test_noaction_reserved", noaction_reserved, [(["mutate"], NOACTION_RESERVED_PARAMETERS_0)]),
    ("test_an_empty_noaction_may_be_declared", an_empty_noaction_may_be_declared, []),
    ("test_action_args", action_args, [(["mutate"], ACTION_ARGS_PARAMETERS_0)]),
    ("test_entry_shape", entry_shape, [(["mutate"], ENTRY_SHAPE_PARAMETERS_0)]),
    (
        "test_entry_shape_ternary_and_exact",
        entry_shape_ternary_and_exact,
        [(["entries"], ENTRY_SHAPE_TERNARY_AND_EXACT_PARAMETERS_0)],
    ),
    ("test_entry_range", entry_range, [(["mutate"], ENTRY_RANGE_PARAMETERS_0)]),
    (
        "test_entry_range_ternary_and_exact",
        entry_range_ternary_and_exact,
        [(["entries"], ENTRY_RANGE_TERNARY_AND_EXACT_PARAMETERS_0)],
    ),
    ("test_entry_priority_on_non_ternary_table", entry_priority_on_non_ternary_table, []),
    (
        "test_entry_priority_overlap",
        entry_priority_overlap,
        [(["entries"], ENTRY_PRIORITY_OVERLAP_PARAMETERS_0)],
    ),
    (
        "test_entry_priority_no_overlap",
        entry_priority_no_overlap,
        [(["entries"], ENTRY_PRIORITY_NO_OVERLAP_PARAMETERS_0)],
    ),
    ("test_entry_duplicate", entry_duplicate, []),
    ("test_lpm_entry_must_be_canonical", lpm_entry_must_be_canonical, []),
    ("test_ternary_entry_must_be_canonical", ternary_entry_must_be_canonical, []),
    (
        "test_lpm_entries_with_different_prefixes_are_fine",
        lpm_entries_with_different_prefixes_are_fine,
        [],
    ),
    (
        "test_table_keys_are_bits_only",
        table_keys_are_bits_only,
        [(["key"], TABLE_KEYS_ARE_BITS_ONLY_PARAMETERS_0)],
    ),
    ("test_apply_inside_an_action_is_rejected", apply_inside_an_action_is_rejected, []),
    ("test_derived_key_names_collide", derived_key_names_collide, []),
    ("test_extern_args", extern_args, [(["mutate"], EXTERN_ARGS_PARAMETERS_0)]),
]


def cases() -> list[Case]:
    result: list[Case] = []
    parameter_set = type(pytest.param(None))
    for name, build, axes in sorted(SCENARIOS, key=lambda item: item[0]):
        choices: list[list[dict[str, Any]]] = []
        for names, values in axes:
            axis = []
            for raw in values:
                value: Any = raw.values if isinstance(raw, parameter_set) else raw
                if isinstance(raw, parameter_set) and len(names) == 1:
                    value = value[0]
                axis.append(
                    dict(zip(names, value, strict=True)) if len(names) > 1 else {names[0]: value}
                )
            choices.append(axis)
        for i, combination in enumerate(itertools.product(*choices)):
            kwargs = dict(itertools.chain.from_iterable(item.items() for item in combination))
            result.append(Case(f"test_validator/{name}[{i}]#{len(result)}", build(**kwargs)))
    return result
