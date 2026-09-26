"""Shared printer fixtures."""

from __future__ import annotations

import os
import re
from pathlib import Path

from google.protobuf import text_format

from p4blo import ir
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "impl/python/tests/printer/golden"

CORPUS = Path(__file__).resolve().parents[2] / "tests/programs/corpus"

# ---------------------------------------------------------------------------
# IR text with two shorthands
# ---------------------------------------------------------------------------


def ir_text(template: str) -> str:
    """Expand two shorthands inside protobuf text format.

    `<hdr.eth.dst>` is the dotted path as nested `member`/`var` messages,
    which read the same as an Expr and as an LValue; `<16w2048>` is a bits
    literal as an Expr, and `[16w2048]` the bare Literal message for action
    arguments, select cases and extern constructor arguments.
    """

    def bits(width: str, value: str) -> str:
        return f'bits {{ width: {width} value: "{value}" }}'

    def path(match: re.Match[str]) -> str:
        head, *rest = match.group(1).split(".")
        text = f'var: "{head}"'
        for f in rest:
            text = f'member {{ base {{ {text} }} field: "{f}" }}'
        return text

    template = re.sub(r"\[(\d+)w(\d+)\]", lambda m: bits(m.group(1), m.group(2)), template)
    template = re.sub(
        r"<(\d+)w(\d+)>", lambda m: f"literal {{ {bits(m.group(1), m.group(2))} }}", template
    )
    return re.sub(r"<([A-Za-z_][\w.]*)>", path, template)


def program(text: str) -> apb.BlockAssembly:
    return arch_wire.load_text(ir_text(text))


def stmt(text: str) -> pb.Stmt:
    return text_format.Parse(ir_text(text), pb.Stmt())


def expr(text: str) -> pb.Expr:
    return text_format.Parse(ir_text(text), pb.Expr())


CORE_ERRORS = "\n".join(f'errors: "{e}"' for e in ir.CORE_ERRORS)

ETHERNET = """
header_types {
  name: "ethernet_t"
  fields { name: "dst" type { bits: 48 } }
  fields { name: "src" type { bits: 48 } }
  fields { name: "type" type { bits: 16 } }
}
"""

# ---------------------------------------------------------------------------
# Golden programs
# ---------------------------------------------------------------------------

# Every parser construct: a sub-parser, a start state not named start, a
# local, extract into a stack, lookahead, advance, verify, lastIndex, an if
# in a state, select over tuples with masks, ranges and don't-cares, reject,
# a program error, and the parser_error contract field.
PARSER_FEATURES = f"""
name: "parser_features"
{CORE_ERRORS}
errors: "BadVersion"
{ETHERNET}
header_types {{
  name: "vlan_t"
  fields {{ name: "pcp" type {{ bits: 3 }} }}
  fields {{ name: "cfi" type {{ bits: 1 }} }}
  fields {{ name: "vid" type {{ bits: 12 }} }}
  fields {{ name: "type" type {{ bits: 16 }} }}
}}
header_types {{
  name: "ipv4_t"
  fields {{ name: "version" type {{ bits: 4 }} }}
  fields {{ name: "ihl" type {{ bits: 4 }} }}
  fields {{ name: "ttl" type {{ bits: 8 }} }}
  fields {{ name: "flag" type {{ boolean {{}} }} }}
}}
struct_types {{
  name: "headers"
  fields {{ name: "eth" type {{ header: "ethernet_t" }} }}
  fields {{ name: "vlans" type {{ stack {{ header: "vlan_t" size: 2 }} }} }}
  fields {{ name: "ipv4" type {{ header: "ipv4_t" }} }}
}}
struct_types {{
  name: "metadata"
  fields {{ name: "ingress_port" type {{ bits: 9 }} }}
  fields {{ name: "parser_error" type {{ error {{}} }} }}
  fields {{ name: "note" type {{ bits: 8 }} }}
}}
headers: "headers"
metadata: "metadata"

blocks {{
  name: "TopParser"
  kind: BLOCK_KIND_PARSER
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_OUT }}
  params {{ name: "meta" type {{ struct: "metadata" }} direction: DIRECTION_INOUT }}
  locals {{ name: "peek" type {{ bits: 16 }} }}
  start_state: "begin"
  states {{
    name: "begin"
    body {{ extract {{ target {{ <hdr.eth> }} }} }}
    body {{ assign {{ target {{ var: "peek" }} value {{ lookahead {{ type {{ bits: 16 }} }} }} }} }}
    transition {{
      select {{
        keys {{ <hdr.eth.type> }}
        keys {{ slice {{ operand {{ <hdr.eth.dst> }} hi: 47 lo: 40 }} }}
        cases {{
          sets {{ exact {{ [16w33024] }} }}
          sets {{ dont_care {{}} }}
          target {{ state: "vlan" }}
        }}
        cases {{
          sets {{ range {{ lo {{ [16w2048] }} hi {{ [16w2049] }} }} }}
          sets {{ masked {{ value {{ [8w1] }} mask {{ [8w255] }} }} }}
          target {{ state: "ipv4" }}
        }}
        cases {{
          sets {{ exact {{ [16w34525] }} }}
          sets {{ exact {{ [8w0] }} }}
          target {{ state: "skip" }}
        }}
        cases {{
          sets {{ dont_care {{}} }}
          sets {{ dont_care {{}} }}
          target {{ accept {{}} }}
        }}
      }}
    }}
  }}
  states {{
    name: "vlan"
    body {{ extract {{ target {{ next {{ stack {{ <hdr.vlans> }} }} }} }} }}
    body {{
      assign {{
        target {{ <meta.note> }}
        value {{
          cast {{ to {{ bits: 8 }} operand {{ last_index {{ stack {{ <hdr.vlans> }} }} }} }}
        }}
      }}
    }}
    transition {{
      select {{
        keys {{
          member {{
            base {{ index {{ base {{ <hdr.vlans> }} index {{ <32w0> }} }} }}
            field: "type"
          }}
        }}
        cases {{ sets {{ exact {{ [16w33024] }} }} target {{ state: "vlan" }} }}
        cases {{ sets {{ exact {{ [16w2048] }} }} target {{ state: "ipv4" }} }}
        cases {{ sets {{ dont_care {{}} }} target {{ accept {{}} }} }}
      }}
    }}
  }}
  states {{
    name: "ipv4"
    body {{
      call_block {{
        block: "Ipv4Parser"
        args {{ lvalue {{ <hdr.ipv4> }} }}
        args {{ lvalue {{ <meta.note> }} }}
      }}
    }}
    body {{
      advance {{
        bits {{
          binary {{
            op: BINARY_OP_MUL
            left {{
              binary {{
                op: BINARY_OP_SUB
                left {{ cast {{ to {{ bits: 32 }} operand {{ <hdr.ipv4.ihl> }} }} }}
                right {{ <32w5> }}
              }}
            }}
            right {{ <32w32> }}
          }}
        }}
      }}
    }}
    body {{
      conditional {{
        condition {{ binary {{ op: BINARY_OP_EQ left {{ <hdr.ipv4.ttl> }} right {{ <8w0> }} }} }}
        then {{ assign {{ target {{ <meta.note> }} value {{ <8w255> }} }} }}
      }}
    }}
    transition {{
      select {{
        keys {{ <meta.note> }}
        cases {{ sets {{ exact {{ [8w255] }} }} target {{ reject {{}} }} }}
        cases {{ sets {{ dont_care {{}} }} target {{ accept {{}} }} }}
      }}
    }}
  }}
  states {{
    name: "skip"
    body {{ advance {{ bits {{ <32w16> }} }} }}
    transition {{ direct {{ reject {{}} }} }}
  }}
}}

blocks {{
  name: "Ipv4Parser"
  kind: BLOCK_KIND_PARSER
  params {{ name: "ip" type {{ header: "ipv4_t" }} direction: DIRECTION_OUT }}
  params {{ name: "note" type {{ bits: 8 }} direction: DIRECTION_INOUT }}
  start_state: "start"
  states {{
    name: "start"
    body {{ extract {{ target {{ var: "ip" }} }} }}
    body {{
      verify {{
        condition {{ binary {{ op: BINARY_OP_EQ left {{ <ip.version> }} right {{ <4w4> }} }} }}
        error: "BadVersion"
      }}
    }}
    body {{ assign {{ target {{ var: "note" }} value {{ <ip.ttl> }} }} }}
    transition {{ direct {{ accept {{}} }} }}
  }}
}}

blocks {{
  name: "TopIngress"
  kind: BLOCK_KIND_CONTROL
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_INOUT }}
  params {{ name: "meta" type {{ struct: "metadata" }} direction: DIRECTION_INOUT }}
  body {{
    conditional {{
      condition {{
        binary {{
          op: BINARY_OP_NE
          left {{ <meta.parser_error> }}
          right {{ literal {{ error: "NoError" }} }}
        }}
      }}
      then {{ assign {{ target {{ <meta.note> }} value {{ <8w1> }} }} }}
    }}
  }}
}}

blocks {{
  name: "TopDeparser"
  kind: BLOCK_KIND_DEPARSER
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_IN }}
  body {{ emit {{ value {{ <hdr.eth> }} }} }}
  body {{ emit {{ value {{ <hdr.vlans> }} }} }}
  body {{ emit {{ value {{ <hdr.ipv4> }} }} }}
}}

exports {{ role: "parser" block: "TopParser" }}
exports {{ role: "ingress" block: "TopIngress" }}
exports {{ role: "deparser" block: "TopDeparser" }}
"""

# Every control construct: sub-controls called from a control and from a
# deparser, locals of every
# scalar type, actions with data and with an in parameter, an lpm table
# with const entries and a key name, a ternary table with priorities and a
# const default, an enum key, hit, push, pop, setValid, setInvalid, every
# operator, both casts, the mux, and all four contract fields.
CONTROL_FEATURES = f"""
name: "control_features"
{CORE_ERRORS}
{ETHERNET}
header_types {{
  name: "ipv4_t"
  fields {{ name: "ttl" type {{ bits: 8 }} }}
  fields {{ name: "src" type {{ bits: 32 }} }}
  fields {{ name: "dst" type {{ bits: 32 }} }}
}}
header_types {{
  name: "tag_t"
  fields {{ name: "v" type {{ bits: 8 }} }}
}}
struct_types {{
  name: "headers"
  fields {{ name: "eth" type {{ header: "ethernet_t" }} }}
  fields {{ name: "ipv4" type {{ header: "ipv4_t" }} }}
  fields {{ name: "tags" type {{ stack {{ header: "tag_t" size: 3 }} }} }}
}}
struct_types {{
  name: "metadata"
  fields {{ name: "ingress_port" type {{ bits: 9 }} }}
  fields {{ name: "parser_error" type {{ error {{}} }} }}
  fields {{ name: "egress_spec" type {{ bits: 9 }} }}
  fields {{ name: "color" type {{ enum_type: "Color" }} }}
  fields {{ name: "flag" type {{ boolean {{}} }} }}
  fields {{ name: "scratch" type {{ bits: 32 }} }}
}}
enum_types {{ name: "Color" members: "RED" members: "GREEN" members: "BLUE" }}
headers: "headers"
metadata: "metadata"

blocks {{
  name: "EthParser"
  kind: BLOCK_KIND_PARSER
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_OUT }}
  params {{ name: "meta" type {{ struct: "metadata" }} direction: DIRECTION_INOUT }}
  start_state: "start"
  states {{
    name: "start"
    body {{ extract {{ target {{ <hdr.eth> }} }} }}
    body {{ extract {{ target {{ <hdr.ipv4> }} }} }}
    transition {{ direct {{ accept {{}} }} }}
  }}
}}

blocks {{
  name: "MainIngress"
  kind: BLOCK_KIND_CONTROL
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_INOUT }}
  params {{ name: "meta" type {{ struct: "metadata" }} direction: DIRECTION_INOUT }}
  locals {{ name: "tmp" type {{ bits: 16 }} }}
  locals {{ name: "matched" type {{ boolean {{}} }} }}
  locals {{ name: "c" type {{ enum_type: "Color" }} }}
  locals {{ name: "e" type {{ error {{}} }} }}
  locals {{ name: "spare" type {{ header: "tag_t" }} }}
  actions {{ name: "NoAction" }}
  actions {{
    name: "drop"
    body {{ assign {{ target {{ <meta.egress_spec> }} value {{ <9w511> }} }} }}
  }}
  actions {{
    name: "forward"
    params {{ name: "dst" type {{ bits: 48 }} direction: DIRECTION_NONE }}
    params {{ name: "port" type {{ bits: 9 }} direction: DIRECTION_NONE }}
    body {{ assign {{ target {{ <meta.egress_spec> }} value {{ var: "port" }} }} }}
    body {{ assign {{ target {{ <hdr.eth.dst> }} value {{ var: "dst" }} }} }}
  }}
  actions {{
    name: "set_ttl"
    params {{ name: "ttl" type {{ bits: 8 }} direction: DIRECTION_IN }}
    body {{ assign {{ target {{ <hdr.ipv4.ttl> }} value {{ var: "ttl" }} }} }}
  }}
  tables {{
    name: "ipv4_lpm"
    keys {{ expr {{ <hdr.ipv4.dst> }} match_kind: MATCH_KIND_LPM name: "dst" }}
    keys {{ expr {{ <hdr.eth.type> }} match_kind: MATCH_KIND_EXACT name: "hdr.eth.type" }}
    actions: "forward"
    actions: "drop"
    actions: "NoAction"
    default_action {{ action: "drop" }}
    const_entries {{
      keys {{ lpm {{ value: "167772160" prefix_len: 8 }} }}
      keys {{ exact: "2048" }}
      action {{ action: "forward" args {{ [48w1] }} args {{ [9w1] }} }}
    }}
    const_entries {{
      keys {{ lpm {{ value: "0" prefix_len: 0 }} }}
      keys {{ exact: "2048" }}
      action {{ action: "drop" }}
    }}
    size: 1024
  }}
  tables {{
    name: "acl"
    keys {{ expr {{ <hdr.ipv4.src> }} match_kind: MATCH_KIND_TERNARY }}
    keys {{ expr {{ <meta.ingress_port> }} match_kind: MATCH_KIND_EXACT }}
    actions: "drop"
    actions: "NoAction"
    const_default_action: true
    const_entries {{
      keys {{ ternary {{ value: "167772160" mask: "4278190080" }} }}
      keys {{ exact: "1" }}
      action {{ action: "drop" }}
      priority: 10
    }}
    const_entries {{
      keys {{ ternary {{ value: "167772161" mask: "4294967295" }} }}
      keys {{ exact: "1" }}
      action {{ action: "NoAction" }}
      priority: 20
    }}
  }}
  tables {{
    name: "by_port"
    keys {{ expr {{ <meta.ingress_port> }} match_kind: MATCH_KIND_EXACT name: "port" }}
    actions: "drop"
  }}
  body {{ apply {{ table: "ipv4_lpm" hit {{ var: "matched" }} }} }}
  body {{
    conditional {{
      condition {{ var: "matched" }}
      then {{ apply {{ table: "acl" }} }}
      otherwise {{ call_action {{ action: "drop" }} }}
    }}
  }}
  body {{ apply {{ table: "by_port" }} }}
  body {{ call_action {{ action: "set_ttl" args {{ expr {{ <8w64> }} }} }} }}
  body {{
    call_block {{
      block: "Rewrite"
      args {{ lvalue {{ <hdr.eth> }} }}
      args {{ expr {{ <48w1> }} }}
    }}
  }}
  body {{ push {{ stack {{ <hdr.tags> }} count: 1 }} }}
  body {{ pop {{ stack {{ <hdr.tags> }} count: 2 }} }}
  body {{ set_valid {{ header {{ index {{ base {{ <hdr.tags> }} index {{ <32w0> }} }} }} }} }}
  body {{ set_invalid {{ header {{ index {{ base {{ <hdr.tags> }} index {{ <32w1> }} }} }} }} }}
  body {{ set_valid {{ header {{ var: "spare" }} }} }}
  body {{
    assign {{
      target {{ index {{ base {{ <hdr.tags> }} index {{ <32w2> }} }} }}
      value {{ var: "spare" }}
    }}
  }}
  body {{
    assign {{
      target {{ <meta.scratch> }}
      value {{
        binary {{
          op: BINARY_OP_MUL
          left {{
            binary {{
              op: BINARY_OP_ADD
              left {{ cast {{ to {{ bits: 32 }} operand {{ <hdr.ipv4.ttl> }} }} }}
              right {{ <32w1> }}
            }}
          }}
          right {{ binary {{ op: BINARY_OP_ADD_SAT left {{ <32w2> }} right {{ <32w3> }} }} }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ var: "tmp" }}
      value {{
        binary {{
          op: BINARY_OP_CONCAT
          left {{ slice {{ operand {{ <hdr.eth.type> }} hi: 7 lo: 0 }} }}
          right {{ slice {{ operand {{ <hdr.eth.type> }} hi: 15 lo: 8 }} }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ var: "tmp" }}
      value {{
        binary {{
          op: BINARY_OP_SHR
          left {{ binary {{ op: BINARY_OP_SHL left {{ var: "tmp" }} right {{ <8w2> }} }} }}
          right {{ <8w1> }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ var: "tmp" }}
      value {{
        binary {{
          op: BINARY_OP_BIT_OR
          left {{
            unary {{
              op: UNARY_OP_COMPLEMENT
              operand {{
                binary {{ op: BINARY_OP_BIT_AND left {{ var: "tmp" }} right {{ <16w255> }} }}
              }}
            }}
          }}
          right {{ binary {{ op: BINARY_OP_BIT_XOR left {{ var: "tmp" }} right {{ <16w1> }} }} }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ var: "tmp" }}
      value {{
        binary {{
          op: BINARY_OP_SUB_SAT
          left {{ unary {{ op: UNARY_OP_NEGATE operand {{ var: "tmp" }} }} }}
          right {{ binary {{ op: BINARY_OP_SUB left {{ var: "tmp" }} right {{ <16w1> }} }} }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ <meta.flag> }}
      value {{
        binary {{
          op: BINARY_OP_AND
          left {{
            binary {{
              op: BINARY_OP_OR
              left {{ binary {{ op: BINARY_OP_LT left {{ var: "tmp" }} right {{ <16w5> }} }} }}
              right {{ binary {{ op: BINARY_OP_GE left {{ var: "tmp" }} right {{ <16w9> }} }} }}
            }}
          }}
          right {{
            binary {{
              op: BINARY_OP_AND
              left {{
                unary {{
                  op: UNARY_OP_NOT
                  operand {{
                    binary {{ op: BINARY_OP_EQ left {{ var: "tmp" }} right {{ <16w0> }} }}
                  }}
                }}
              }}
              right {{
                binary {{
                  op: BINARY_OP_AND
                  left {{ binary {{ op: BINARY_OP_NE left {{ var: "tmp" }} right {{ <16w1> }} }} }}
                  right {{
                    binary {{
                      op: BINARY_OP_AND
                      left {{
                        binary {{ op: BINARY_OP_LE left {{ var: "tmp" }} right {{ <16w7> }} }}
                      }}
                      right {{
                        binary {{ op: BINARY_OP_GT left {{ var: "tmp" }} right {{ <16w2> }} }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ <meta.color> }}
      value {{
        mux {{
          condition {{ <meta.flag> }}
          then {{ literal {{ enum_member {{ enum_type: "Color" member: "GREEN" }} }} }}
          otherwise {{ literal {{ enum_member {{ enum_type: "Color" member: "BLUE" }} }} }}
        }}
      }}
    }}
  }}
  body {{ assign {{ target {{ var: "c" }} value {{ <meta.color> }} }} }}
  body {{ assign {{ target {{ var: "e" }} value {{ <meta.parser_error> }} }} }}
  body {{
    assign {{
      target {{ <meta.scratch> }}
      value {{
        cast {{
          to {{ bits: 32 }}
          operand {{ cast {{ to {{ bits: 1 }} operand {{ <meta.flag> }} }} }}
        }}
      }}
    }}
  }}
  body {{
    assign {{
      target {{ <meta.flag> }}
      value {{
        cast {{
          to {{ boolean {{}} }}
          operand {{ slice {{ operand {{ <meta.scratch> }} hi: 0 lo: 0 }} }}
        }}
      }}
    }}
  }}
  body {{
    conditional {{
      condition {{
        binary {{
          op: BINARY_OP_AND
          left {{ is_valid {{ header {{ <hdr.ipv4> }} }} }}
          right {{
            binary {{
              op: BINARY_OP_EQ
              left {{ var: "c" }}
              right {{ literal {{ enum_member {{ enum_type: "Color" member: "RED" }} }} }}
            }}
          }}
        }}
      }}
      then {{
        call_action {{ action: "forward" args {{ expr {{ <48w2> }} }} args {{ expr {{ <9w2> }} }} }}
      }}
    }}
  }}
}}

blocks {{
  name: "Rewrite"
  kind: BLOCK_KIND_CONTROL
  params {{ name: "eth" type {{ header: "ethernet_t" }} direction: DIRECTION_INOUT }}
  params {{ name: "dst" type {{ bits: 48 }} direction: DIRECTION_IN }}
  body {{ assign {{ target {{ <eth.src> }} value {{ <eth.dst> }} }} }}
  body {{ assign {{ target {{ <eth.dst> }} value {{ var: "dst" }} }} }}
}}

blocks {{
  name: "MainDeparser"
  kind: BLOCK_KIND_DEPARSER
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_IN }}
  locals {{ name: "first" type {{ bits: 8 }} }}
  body {{ emit {{ value {{ <hdr.eth> }} }} }}
  body {{
    call_block {{
      block: "Summarize"
      args {{ expr {{ <hdr.tags> }} }}
      args {{ lvalue {{ var: "first" }} }}
    }}
  }}
  body {{ emit {{ value {{ <hdr.tags> }} }} }}
  body {{
    conditional {{
      condition {{ binary {{ op: BINARY_OP_NE left {{ var: "first" }} right {{ <8w0> }} }} }}
      then {{ emit {{ value {{ <hdr.ipv4> }} }} }}
    }}
  }}
}}

blocks {{
  name: "Summarize"
  kind: BLOCK_KIND_DEPARSER
  params {{ name: "tags" type {{ stack {{ header: "tag_t" size: 3 }} }} direction: DIRECTION_IN }}
  params {{ name: "first" type {{ bits: 8 }} direction: DIRECTION_OUT }}
  body {{
    assign {{
      target {{ var: "first" }}
      value {{
        member {{ base {{ index {{ base {{ var: "tags" }} index {{ <32w0> }} }} }} field: "v" }}
      }}
    }}
  }}
}}

exports {{ role: "parser" block: "EthParser" }}
exports {{ role: "ingress" block: "MainIngress" }}
exports {{ role: "deparser" block: "MainDeparser" }}
"""

# The three extern families: a register used by one exported block, printed
# inside it; a counter shared with a sub-control, printed at top level; and
# checksum16, which has no v1model instance and prints as hash().
EXTERNS = f"""
name: "externs"
{CORE_ERRORS}
{ETHERNET}
struct_types {{
  name: "headers"
  fields {{ name: "eth" type {{ header: "ethernet_t" }} }}
}}
struct_types {{
  name: "metadata"
  fields {{ name: "egress_spec" type {{ bits: 9 }} }}
  fields {{ name: "idx" type {{ bits: 32 }} }}
  fields {{ name: "sum" type {{ bits: 16 }} }}
}}
headers: "headers"
metadata: "metadata"

extern_types {{
  name: "register"
  constructor_params {{ name: "size" type {{ bits: 32 }} direction: DIRECTION_IN }}
  methods {{
    name: "read"
    params {{ name: "result" type {{ bits: 16 }} direction: DIRECTION_OUT }}
    params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
  }}
  methods {{
    name: "write"
    params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
    params {{ name: "value" type {{ bits: 16 }} direction: DIRECTION_IN }}
  }}
}}
extern_types {{
  name: "counter"
  constructor_params {{ name: "size" type {{ bits: 32 }} direction: DIRECTION_IN }}
  methods {{
    name: "count"
    params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
  }}
}}
extern_types {{
  name: "checksum16"
  methods {{
    name: "compute"
    params {{ name: "data" type {{ bits: 96 }} direction: DIRECTION_IN }}
    returns {{ bits: 16 }}
  }}
}}
extern_instances {{ name: "last_seen" extern_type: "register" args {{ [32w16] }} }}
extern_instances {{ name: "pkts" extern_type: "counter" args {{ [32w4] }} }}
extern_instances {{ name: "csum" extern_type: "checksum16" }}

blocks {{
  name: "EthParser"
  kind: BLOCK_KIND_PARSER
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_OUT }}
  params {{ name: "meta" type {{ struct: "metadata" }} direction: DIRECTION_INOUT }}
  start_state: "start"
  states {{
    name: "start"
    body {{ extract {{ target {{ <hdr.eth> }} }} }}
    transition {{ direct {{ accept {{}} }} }}
  }}
}}

blocks {{
  name: "Count"
  kind: BLOCK_KIND_CONTROL
  params {{ name: "i" type {{ bits: 32 }} direction: DIRECTION_IN }}
  body {{ call_extern {{ instance: "pkts" method: "count" args {{ expr {{ var: "i" }} }} }} }}
}}

blocks {{
  name: "MainIngress"
  kind: BLOCK_KIND_CONTROL
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_INOUT }}
  params {{ name: "meta" type {{ struct: "metadata" }} direction: DIRECTION_INOUT }}
  body {{
    call_extern {{
      instance: "last_seen" method: "read"
      args {{ lvalue {{ <meta.sum> }} }}
      args {{ expr {{ <meta.idx> }} }}
    }}
  }}
  body {{
    assign {{
      target {{ <meta.sum> }}
      value {{ binary {{ op: BINARY_OP_ADD left {{ <meta.sum> }} right {{ <16w1> }} }} }}
    }}
  }}
  body {{
    call_extern {{
      instance: "last_seen" method: "write"
      args {{ expr {{ <meta.idx> }} }}
      args {{ expr {{ <meta.sum> }} }}
    }}
  }}
  body {{ call_extern {{ instance: "pkts" method: "count" args {{ expr {{ <32w0> }} }} }} }}
  body {{ call_block {{ block: "Count" args {{ expr {{ <meta.idx> }} }} }} }}
  body {{
    call_extern {{
      instance: "csum" method: "compute"
      args {{
        expr {{
          binary {{ op: BINARY_OP_CONCAT left {{ <hdr.eth.dst> }} right {{ <hdr.eth.src> }} }}
        }}
      }}
      result {{ <meta.sum> }}
    }}
  }}
  body {{ assign {{ target {{ <meta.egress_spec> }} value {{ <9w1> }} }} }}
}}

blocks {{
  name: "MainDeparser"
  kind: BLOCK_KIND_DEPARSER
  params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_IN }}
  body {{ emit {{ value {{ <hdr.eth> }} }} }}
}}

exports {{ role: "parser" block: "EthParser" }}
exports {{ role: "ingress" block: "MainIngress" }}
exports {{ role: "deparser" block: "MainDeparser" }}
"""

# Only a parser exported: the shim supplies the other two roles, and the
# metadata struct has no contract field at all.
BARE = f"""
name: "bare"
{CORE_ERRORS}
struct_types {{ name: "H" }}
struct_types {{ name: "M" fields {{ name: "seen" type {{ boolean {{}} }} }} }}
headers: "H"
metadata: "M"
blocks {{
  name: "P"
  kind: BLOCK_KIND_PARSER
  params {{ name: "h" type {{ struct: "H" }} direction: DIRECTION_OUT }}
  params {{ name: "m" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
  start_state: "start"
  states {{
    name: "start"
    body {{ assign {{ target {{ <m.seen> }} value {{ literal {{ boolean: true }} }} }} }}
    transition {{ direct {{ accept {{}} }} }}
  }}
}}
exports {{ role: "parser" block: "P" }}
"""

GOLDENS: dict[str, str] = {
    "parser_features": PARSER_FEATURES,
    "control_features": CONTROL_FEATURES,
    "externs": EXTERNS,
    "bare": BARE,
}


def golden_program(name: str) -> apb.BlockAssembly:
    if name == "forwarder":
        return arch_wire.load_text(CORPUS / "forwarder" / "forwarder.txtpb")
    if name == "port_parser":
        return program(PORT_PARSER % ("start", "start"))
    return program(GOLDENS[name])


def check_golden(name: str, text: str) -> Path:
    path = GOLDEN_DIR / f"{name}.p4"
    if os.environ.get("P4BLO_UPDATE_GOLDENS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    assert path.exists(), f"no golden {path}; run with P4BLO_UPDATE_GOLDENS=1"
    assert text == path.read_text(), f"{path} differs; P4BLO_UPDATE_GOLDENS=1 regenerates it"
    return path


# A parser that decides on `meta.ingress_port`: packets from port 1
# request a drop through ordinary user metadata, which ingress applies.
# v1model provides the port before the parser runs, so its printer must too.
PORT_PARSER = """
name: "port_parser"
errors: "NoError" errors: "PacketTooShort" errors: "NoMatch" errors: "StackOutOfBounds"
errors: "HeaderTooShort" errors: "ParserTimeout" errors: "ParserInvalidArgument"
header_types { name: "h_t" fields { name: "f" type { bits: 8 } } }
struct_types { name: "H" fields { name: "h" type { header: "h_t" } } }
struct_types {
  name: "M"
  fields { name: "ingress_port" type { bits: 9 } }
  fields { name: "egress_spec" type { bits: 9 } }
  fields { name: "drop_requested" type { boolean {} } }
}
headers: "H"
metadata: "M"
blocks {
  name: "P" kind: BLOCK_KIND_PARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  start_state: "%s"
  states {
    name: "%s"
    body { extract { target { <hdr.h> } } }
    transition { select {
      keys { <meta.ingress_port> }
      cases { sets { exact { [9w1] } } target { state: "from_one" } }
      cases { sets { dont_care {} } target { accept {} } }
    } }
  }
  states {
    name: "from_one"
    body { assign { target { <meta.drop_requested> } value { literal { boolean: true } } } }
    transition { direct { accept {} } }
  }
}
blocks {
  name: "C" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  body { assign { target { <meta.egress_spec> } value { <9w2> } } }
  body { conditional {
    condition { <meta.drop_requested> }
    then { assign { target { <meta.egress_spec> } value { <9w511> } } }
  } }
}
blocks {
  name: "D" kind: BLOCK_KIND_DEPARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
  body { emit { value { <hdr.h> } } }
}
exports { role: "parser" block: "P" }
exports { role: "ingress" block: "C" }
exports { role: "deparser" block: "D" }
"""
