"""The eDSL builds the IR it says it does.

Every test compares a built message with a hand-written text-format
expectation. The forwarder test is the acceptance test: the eDSL program
under corpus/forwarder must equal the golden txtpb beside it.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from functools import reduce
from pathlib import Path
from types import ModuleType

import pytest
from google.protobuf import text_format

from p4blo import arch, ir, validator
from p4blo.edsl.core import (
    EdslError,
    Program,
    bit,
    boolean,
    concat,
    dont_care,
    entry,
    error_t,
    exact,
    lpm,
    masked,
    method,
    mux,
    prefix,
    range_,
    ternary,
)
from p4blo.edsl.core import externs as edsl_externs
from p4blo.v0 import p4blo_pb2 as pb

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def corpus_module(name: str) -> ModuleType:
    """The eDSL source of corpus program `name`, imported."""
    spec = importlib.util.spec_from_file_location(name, CORPUS / name / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def block(text: str) -> pb.Block:
    return text_format.Parse(text, pb.Block())


# Text-format fragments for the paths the tests keep writing. An Expr and
# the LValue naming the same place print identically for var, member and
# index, so one helper serves both.


def var(name: str) -> str:
    return f'var: "{name}"'


def member(base: str, field: str) -> str:
    return f'member {{ base {{ {base} }} field: "{field}" }}'


def bits(width: int, value: int) -> str:
    return f'literal {{ bits {{ width: {width} value: "{value}" }} }}'


HDR_H = member(var("hdr"), "h")
HDR_H_F = member(HDR_H, "f")
HDR_H_G = member(HDR_H, "g")
HDR_STACK = member(var("hdr"), "stack")
META_X = member(var("meta"), "x")
META_OK = member(var("meta"), "ok")


def base() -> Program:
    """A program with a header, a stack and a metadata struct to build on."""
    p = Program("t")
    h = p.header("h", f=bit(8), g=bit(16))
    v = p.header("v", tag=bit(4), bos=bit(1))
    p.headers = p.struct("H", h=h, stack=v[2])
    p.metadata = p.struct("M", x=bit(8), ok=boolean, err=error_t)
    return p


# ---------------------------------------------------------------------------
# The acceptance test
# ---------------------------------------------------------------------------


def test_forwarder_equals_the_golden() -> None:
    golden = ir.load_text(CORPUS / "forwarder" / "forwarder.txtpb")
    assert corpus_module("forwarder").build() == golden


# ---------------------------------------------------------------------------
# Program-level declarations
# ---------------------------------------------------------------------------


def test_declarations_in_order() -> None:
    p = base()
    color = p.enum("color", "RED", "GREEN")
    custom = p.error("Custom")
    reg = edsl_externs.register(p, bit(8))
    r = p.extern_instance("r", reg, 4)
    ck = p.extern_type(
        "checksum16", methods={"compute": method([("data", "in", bit(16))], returns=bit(16))}
    )
    p.extern_instance("c16", ck)
    assert color.RED.pb == text_format.Parse(
        'literal { enum_member { enum_type: "color" member: "RED" } }', pb.Expr()
    )
    assert custom.pb == text_format.Parse('literal { error: "Custom" }', pb.Expr())
    assert r.name == "r"
    expected = ir.load_text(
        """
        name: "t"
        errors: "NoError"
        errors: "PacketTooShort"
        errors: "NoMatch"
        errors: "StackOutOfBounds"
        errors: "HeaderTooShort"
        errors: "ParserTimeout"
        errors: "ParserInvalidArgument"
        errors: "Custom"
        header_types {
          name: "h"
          fields { name: "f" type { bits: 8 } }
          fields { name: "g" type { bits: 16 } }
        }
        header_types {
          name: "v"
          fields { name: "tag" type { bits: 4 } }
          fields { name: "bos" type { bits: 1 } }
        }
        struct_types {
          name: "H"
          fields { name: "h" type { header: "h" } }
          fields { name: "stack" type { stack { header: "v" size: 2 } } }
        }
        struct_types {
          name: "M"
          fields { name: "x" type { bits: 8 } }
          fields { name: "ok" type { boolean {} } }
          fields { name: "err" type { error {} } }
        }
        enum_types { name: "color" members: "RED" members: "GREEN" }
        extern_types {
          name: "register"
          constructor_params { name: "size" type { bits: 32 } direction: DIRECTION_IN }
          methods {
            name: "read"
            params { name: "result" type { bits: 8 } direction: DIRECTION_OUT }
            params { name: "index" type { bits: 32 } direction: DIRECTION_IN }
          }
          methods {
            name: "write"
            params { name: "index" type { bits: 32 } direction: DIRECTION_IN }
            params { name: "value" type { bits: 8 } direction: DIRECTION_IN }
          }
        }
        extern_types {
          name: "checksum16"
          methods {
            name: "compute"
            params { name: "data" type { bits: 16 } direction: DIRECTION_IN }
            returns { bits: 16 }
          }
        }
        extern_instances {
          name: "r" extern_type: "register" args { bits { width: 32 value: "4" } }
        }
        extern_instances { name: "c16" extern_type: "checksum16" }
        headers: "H"
        metadata: "M"
        """
    )
    assert p.build() == expected


def test_exports_and_default_signatures() -> None:
    p = base()
    p.parser("P").state("start").accept()
    p.control("C")
    p.deparser("D")
    p.export("parser", "P")
    p.export("control", "C")
    p.export("deparser", "D")
    program = p.build()
    assert [(e.role, e.block) for e in program.exports] == [
        ("parser", "P"),
        ("control", "C"),
        ("deparser", "D"),
    ]
    assert program.blocks[0] == block(
        """
        name: "P" kind: BLOCK_KIND_PARSER
        params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
        params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
        states { name: "start" transition { direct { accept {} } } }
        start_state: "start"
        """
    )
    assert program.blocks[1] == block(
        """
        name: "C" kind: BLOCK_KIND_CONTROL
        params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
        params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
        """
    )
    assert program.blocks[2] == block(
        """
        name: "D" kind: BLOCK_KIND_DEPARSER
        params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
        """
    )


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def test_parser() -> None:
    p = base()
    h = p.types.headers["h"]
    with p.parser("sub", params=[("x", "out", h)]) as sub:
        with sub.state("start") as s:
            s.extract(sub.x)
            s.accept()
    with p.parser("main") as ps:
        hdr, meta = ps.hdr, ps.meta
        with ps.state("start", start=True) as s:
            s.call_block(sub, hdr.h)
            s.verify(hdr.h.f != 0, "PacketTooShort")
            s.select(
                (hdr.h.f, hdr.h.g),
                {
                    (1, dont_care): "tags",
                    (masked(2, 0xF0), range_(10, 20)): ps.reject,
                },
                default=ps.accept,
            )
        with ps.state("tags") as s:
            s.extract(hdr.stack.next)
            s.advance(8)
            s.assign(meta.x, s.lookahead(bit(8)))
            s.verify(meta.x == 0, p.errors.ParserInvalidArgument)
            s.select(hdr.stack[0].bos, {1: ps.accept}, default="tags")
    program = p.build()
    assert program.blocks[0] == block(
        f"""
        name: "sub" kind: BLOCK_KIND_PARSER
        params {{ name: "x" type {{ header: "h" }} direction: DIRECTION_OUT }}
        states {{
          name: "start"
          body {{ extract {{ target {{ {var("x")} }} }} }}
          transition {{ direct {{ accept {{}} }} }}
        }}
        start_state: "start"
        """
    )
    assert program.blocks[1] == block(
        f"""
        name: "main" kind: BLOCK_KIND_PARSER
        params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_OUT }}
        params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
        states {{
          name: "start"
          body {{ call_block {{ block: "sub" args {{ lvalue {{ {HDR_H} }} }} }} }}
          body {{
            verify {{
              condition {{
                binary {{ op: BINARY_OP_NE left {{ {HDR_H_F} }} right {{ {bits(8, 0)} }} }}
              }}
              error: "PacketTooShort"
            }}
          }}
          transition {{
            select {{
              keys {{ {HDR_H_F} }}
              keys {{ {HDR_H_G} }}
              cases {{
                sets {{ exact {{ bits {{ width: 8 value: "1" }} }} }}
                sets {{ dont_care {{}} }}
                target {{ state: "tags" }}
              }}
              cases {{
                sets {{
                  masked {{
                    value {{ bits {{ width: 8 value: "2" }} }}
                    mask {{ bits {{ width: 8 value: "240" }} }}
                  }}
                }}
                sets {{
                  range {{
                    lo {{ bits {{ width: 16 value: "10" }} }}
                    hi {{ bits {{ width: 16 value: "20" }} }}
                  }}
                }}
                target {{ reject {{}} }}
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
          name: "tags"
          body {{ extract {{ target {{ next {{ stack {{ {HDR_STACK} }} }} }} }} }}
          body {{ advance {{ bits {{ {bits(32, 8)} }} }} }}
          body {{
            assign {{ target {{ {META_X} }} value {{ lookahead {{ type {{ bits: 8 }} }} }} }}
          }}
          body {{
            verify {{
              condition {{
                binary {{ op: BINARY_OP_EQ left {{ {META_X} }} right {{ {bits(8, 0)} }} }}
              }}
              error: "ParserInvalidArgument"
            }}
          }}
          transition {{
            select {{
              keys {{
                member {{
                  base {{ index {{ base {{ {HDR_STACK} }} index {{ {bits(32, 0)} }} }} }}
                  field: "bos"
                }}
              }}
              cases {{
                sets {{ exact {{ bits {{ width: 1 value: "1" }} }} }}
                target {{ accept {{}} }}
              }}
              cases {{ sets {{ dont_care {{}} }} target {{ state: "tags" }} }}
            }}
          }}
        }}
        start_state: "start"
        """
    )


def test_parser_start_state_is_the_one_named_start_by_default() -> None:
    p = base()
    with p.parser("P") as ps:
        with ps.state("other") as s:
            s.accept()
        with ps.state("start") as s:
            s.transition("other")
    assert p.build().blocks[0].start_state == "start"


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_control() -> None:
    p = base()
    reg = edsl_externs.register(p, bit(8))
    r = p.extern_instance("r", reg, 4)
    ck = edsl_externs.checksum16(p, bit(16))
    c16 = p.extern_instance("c16", ck)
    with p.control("sub", params=[("y", "inout", bit(8))]) as sub:
        with sub.body() as b:
            b.assign(sub.y, sub.y + 1)
    with p.control("main") as c:
        hdr, meta = c.hdr, c.meta
        c.action("NoAction")
        with c.action("set", val=bit(8)) as a:
            a.assign(meta.x, a.val)
        t = c.table(
            "t",
            keys=[ternary(hdr.h.f), exact(hdr.h.g, name="g")],
            actions=["set", "NoAction"],
            default=("set", 7),
            const_default=True,
            const_entries=[
                entry((masked(1, 0xFF), 2), ("set", 3), priority=10),
                entry((dont_care, 4), "NoAction", priority=1),
            ],
            size=16,
        )
        with c.body() as b:
            hit = b.local("hit", boolean)
            b.apply(t, hit=hit)
            with b.if_(hit & (meta.x < 5)):
                b.assign(meta.x, mux(meta.ok, meta.x.add_sat(1), meta.x.sub_sat(1)))
            with b.else_():
                tmp = b.local("tmp", bit(16))
                b.assign(tmp, concat(meta.x, hdr.h.f))
                b.assign(hdr.h.g, tmp[15:8].cast(bit(16)) ^ (hdr.h.g >> 2))
            b.call(r, "read", meta.x, 0)
            b.call(r, "write", 1, meta.x)
            b.call(c16, "compute", hdr.h.g, result=tmp)
            b.call_block(sub, meta.x)
            b.call_action("set", 9)
            b.set_valid(hdr.h)
            b.set_invalid(hdr.h)
            b.push(hdr.stack, 1)
            b.pop(hdr.stack, 1)
            b.assign(meta.ok, hdr.stack.last_index == 1)
            b.assign(meta.ok, ~meta.ok | meta.ok.cast(bit(1)).cast(boolean))
            b.assign(meta.x, -hdr.h.f)
    program = p.build()
    assert program.blocks[0] == block(
        f"""
        name: "sub" kind: BLOCK_KIND_CONTROL
        params {{ name: "y" type {{ bits: 8 }} direction: DIRECTION_INOUT }}
        body {{
          assign {{
            target {{ {var("y")} }}
            value {{
              binary {{ op: BINARY_OP_ADD left {{ {var("y")} }} right {{ {bits(8, 1)} }} }}
            }}
          }}
        }}
        """
    )
    assert program.blocks[1] == block(
        f"""
        name: "main" kind: BLOCK_KIND_CONTROL
        params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_INOUT }}
        params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
        locals {{ name: "hit" type {{ boolean {{}} }} }}
        locals {{ name: "tmp" type {{ bits: 16 }} }}
        actions {{ name: "NoAction" }}
        actions {{
          name: "set"
          params {{ name: "val" type {{ bits: 8 }} direction: DIRECTION_NONE }}
          body {{ assign {{ target {{ {META_X} }} value {{ {var("val")} }} }} }}
        }}
        tables {{
          name: "t"
          keys {{ expr {{ {HDR_H_F} }} match_kind: MATCH_KIND_TERNARY }}
          keys {{ expr {{ {HDR_H_G} }} match_kind: MATCH_KIND_EXACT name: "g" }}
          actions: "set"
          actions: "NoAction"
          default_action {{ action: "set" args {{ bits {{ width: 8 value: "7" }} }} }}
          const_default_action: true
          const_entries {{
            keys {{ ternary {{ value: "1" mask: "255" }} }}
            keys {{ exact: "2" }}
            action {{ action: "set" args {{ bits {{ width: 8 value: "3" }} }} }}
            priority: 10
          }}
          const_entries {{
            keys {{ ternary {{ value: "0" mask: "0" }} }}
            keys {{ exact: "4" }}
            action {{ action: "NoAction" }}
            priority: 1
          }}
          size: 16
        }}
        body {{ apply {{ table: "t" hit {{ {var("hit")} }} }} }}
        body {{
          conditional {{
            condition {{
              binary {{
                op: BINARY_OP_AND
                left {{ {var("hit")} }}
                right {{
                  binary {{ op: BINARY_OP_LT left {{ {META_X} }} right {{ {bits(8, 5)} }} }}
                }}
              }}
            }}
            then {{
              assign {{
                target {{ {META_X} }}
                value {{
                  mux {{
                    condition {{ {META_OK} }}
                    then {{
                      binary {{
                        op: BINARY_OP_ADD_SAT left {{ {META_X} }} right {{ {bits(8, 1)} }}
                      }}
                    }}
                    otherwise {{
                      binary {{
                        op: BINARY_OP_SUB_SAT left {{ {META_X} }} right {{ {bits(8, 1)} }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            otherwise {{
              assign {{
                target {{ {var("tmp")} }}
                value {{
                  binary {{ op: BINARY_OP_CONCAT left {{ {META_X} }} right {{ {HDR_H_F} }} }}
                }}
              }}
            }}
            otherwise {{
              assign {{
                target {{ {HDR_H_G} }}
                value {{
                  binary {{
                    op: BINARY_OP_BIT_XOR
                    left {{
                      cast {{
                        to {{ bits: 16 }}
                        operand {{ slice {{ operand {{ {var("tmp")} }} hi: 15 lo: 8 }} }}
                      }}
                    }}
                    right {{
                      binary {{ op: BINARY_OP_SHR left {{ {HDR_H_G} }} right {{ {bits(16, 2)} }} }}
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        body {{
          call_extern {{
            instance: "r" method: "read"
            args {{ lvalue {{ {META_X} }} }}
            args {{ expr {{ {bits(32, 0)} }} }}
          }}
        }}
        body {{
          call_extern {{
            instance: "r" method: "write"
            args {{ expr {{ {bits(32, 1)} }} }}
            args {{ expr {{ {META_X} }} }}
          }}
        }}
        body {{
          call_extern {{
            instance: "c16" method: "compute"
            args {{ expr {{ {HDR_H_G} }} }}
            result {{ {var("tmp")} }}
          }}
        }}
        body {{ call_block {{ block: "sub" args {{ lvalue {{ {META_X} }} }} }} }}
        body {{ call_action {{ action: "set" args {{ expr {{ {bits(8, 9)} }} }} }} }}
        body {{ set_valid {{ header {{ {HDR_H} }} }} }}
        body {{ set_invalid {{ header {{ {HDR_H} }} }} }}
        body {{ push {{ stack {{ {HDR_STACK} }} count: 1 }} }}
        body {{ pop {{ stack {{ {HDR_STACK} }} count: 1 }} }}
        body {{
          assign {{
            target {{ {META_OK} }}
            value {{
              binary {{
                op: BINARY_OP_EQ
                left {{ last_index {{ stack {{ {HDR_STACK} }} }} }}
                right {{ {bits(32, 1)} }}
              }}
            }}
          }}
        }}
        body {{
          assign {{
            target {{ {META_OK} }}
            value {{
              binary {{
                op: BINARY_OP_OR
                left {{ unary {{ op: UNARY_OP_NOT operand {{ {META_OK} }} }} }}
                right {{
                  cast {{
                    to {{ boolean {{}} }}
                    operand {{ cast {{ to {{ bits: 1 }} operand {{ {META_OK} }} }} }}
                  }}
                }}
              }}
            }}
          }}
        }}
        body {{
          assign {{
            target {{ {META_X} }}
            value {{ unary {{ op: UNARY_OP_NEGATE operand {{ {HDR_H_F} }} }} }}
          }}
        }}
        """
    )


def test_lpm_entries_and_reflected_operators() -> None:
    p = base()
    with p.control("C") as c:
        hdr = c.hdr
        with c.action("a") as a:
            a.assign(hdr.h.f, 1 + hdr.h.f)
            a.assign(hdr.h.f, 3 - hdr.h.f)
            a.assign(hdr.h.f, ~hdr.h.f & 15)
            a.assign(hdr.h.f, hdr.h.f << p.literal(9, bit(4)))
        c.table(
            "t",
            keys=[lpm(hdr.h.g)],
            actions=["a"],
            const_entries=[entry(prefix(0xFF00, 8), "a")],
        )
    built = p.build().blocks[0]
    assert built.actions[0] == text_format.Parse(
        f"""
        name: "a"
        body {{
          assign {{
            target {{ {HDR_H_F} }}
            value {{ binary {{ op: BINARY_OP_ADD left {{ {bits(8, 1)} }} right {{ {HDR_H_F} }} }} }}
          }}
        }}
        body {{
          assign {{
            target {{ {HDR_H_F} }}
            value {{ binary {{ op: BINARY_OP_SUB left {{ {bits(8, 3)} }} right {{ {HDR_H_F} }} }} }}
          }}
        }}
        body {{
          assign {{
            target {{ {HDR_H_F} }}
            value {{
              binary {{
                op: BINARY_OP_BIT_AND
                left {{ unary {{ op: UNARY_OP_COMPLEMENT operand {{ {HDR_H_F} }} }} }}
                right {{ {bits(8, 15)} }}
              }}
            }}
          }}
        }}
        body {{
          assign {{
            target {{ {HDR_H_F} }}
            value {{ binary {{ op: BINARY_OP_SHL left {{ {HDR_H_F} }} right {{ {bits(4, 9)} }} }} }}
          }}
        }}
        """,
        pb.Action(),
    )
    assert built.tables[0] == text_format.Parse(
        f"""
        name: "t"
        keys {{ expr {{ {HDR_H_G} }} match_kind: MATCH_KIND_LPM }}
        actions: "a"
        const_entries {{
          keys {{ lpm {{ value: "65280" prefix_len: 8 }} }}
          action {{ action: "a" }}
        }}
        """,
        pb.Table(),
    )


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------


def stmt(text: str) -> pb.Stmt:
    return text_format.Parse(text, pb.Stmt())


def cond(value: int) -> str:
    return f"binary {{ op: BINARY_OP_EQ left {{ {META_X} }} right {{ {bits(8, value)} }} }}"


def set_x(value: int) -> str:
    return f"assign {{ target {{ {META_X} }} value {{ {bits(8, value)} }} }}"


def test_else_follows_its_own_if_in_both_branches() -> None:
    p = base()
    with p.control("C") as c:
        x = c.meta.x
        with c.body() as b:
            with b.if_(x == 1):
                with b.if_(x == 2):
                    b.assign(x, 20)
                with b.else_():
                    b.assign(x, 21)
            with b.else_():
                with b.if_(x == 3):
                    b.assign(x, 30)
                with b.else_():
                    b.assign(x, 31)
            with b.if_(x == 4):
                b.assign(x, 40)
    body = p.build().blocks[0].body
    assert len(body) == 2
    assert body[0] == stmt(
        f"""
        conditional {{
          condition {{ {cond(1)} }}
          then {{
            conditional {{
              condition {{ {cond(2)} }}
              then {{ {set_x(20)} }}
              otherwise {{ {set_x(21)} }}
            }}
          }}
          otherwise {{
            conditional {{
              condition {{ {cond(3)} }}
              then {{ {set_x(30)} }}
              otherwise {{ {set_x(31)} }}
            }}
          }}
        }}
        """
    )
    assert body[1] == stmt(f"conditional {{ condition {{ {cond(4)} }} then {{ {set_x(40)} }} }}")


def test_elif_nests_as_the_else_if_ladder() -> None:
    p = base()
    with p.control("C") as c:
        x = c.meta.x
        with c.body() as b:
            with b.if_(x == 1):
                b.assign(x, 10)
            with b.elif_(x == 2):
                # An if_ inside an arm does not capture the ladder's next arm.
                with b.if_(x == 5):
                    b.assign(x, 50)
            with b.elif_(x == 3):
                b.assign(x, 30)
            with b.else_():
                b.assign(x, 40)
            with pytest.raises(EdslError, match="elif_ must follow an if_"):
                with b.elif_(x == 6):
                    pass
    body = p.build().blocks[0].body
    assert len(body) == 1
    assert body[0] == stmt(
        f"""
        conditional {{
          condition {{ {cond(1)} }}
          then {{ {set_x(10)} }}
          otherwise {{
            conditional {{
              condition {{ {cond(2)} }}
              then {{ conditional {{ condition {{ {cond(5)} }} then {{ {set_x(50)} }} }} }}
              otherwise {{
                conditional {{
                  condition {{ {cond(3)} }}
                  then {{ {set_x(30)} }}
                  otherwise {{ {set_x(40)} }}
                }}
              }}
            }}
          }}
        }}
        """
    )


def test_else_after_a_closed_else_is_refused() -> None:
    # The inner if_ is the last statement of the else; closing the else
    # must not leave it open for a stray else_ at the outer level.
    p = base()
    with p.control("C") as c:
        x = c.meta.x
        with c.body() as b:
            with b.if_(x == 1):
                b.assign(x, 10)
            with b.else_():
                with b.if_(x == 2):
                    b.assign(x, 20)
            with pytest.raises(EdslError, match="else_ must follow an if_"):
                with b.else_():
                    b.assign(x, 30)
    assert p.build().blocks[0].body[0] == stmt(
        f"""
        conditional {{
          condition {{ {cond(1)} }}
          then {{ {set_x(10)} }}
          otherwise {{ conditional {{ condition {{ {cond(2)} }} then {{ {set_x(20)} }} }} }}
        }}
        """
    )


def test_else_at_the_start_of_a_branch_is_refused() -> None:
    # A sibling if_ outside the branch is not the one just closed inside it.
    p = base()
    with p.control("C") as c:
        x = c.meta.x
        with c.body() as b:
            with b.if_(x == 1):
                b.assign(x, 10)
            with b.if_(x == 2):
                with pytest.raises(EdslError, match="else_ must follow an if_"):
                    with b.else_():
                        b.assign(x, 20)
                b.assign(x, 21)
    assert p.build().blocks[0].body[1] == stmt(
        f"conditional {{ condition {{ {cond(2)} }} then {{ {set_x(21)} }} }}"
    )


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


def test_stack_last_is_the_element_at_last_index() -> None:
    p = base()
    c = p.control("C")
    last = c.hdr.stack.last
    spelled = c.hdr.stack[c.hdr.stack.last_index]
    assert last.type == spelled.type == pb.Type(header="v")
    assert last.pb == spelled.pb
    assert last.lval == spelled.lval
    assert last.tag.pb == text_format.Parse(
        f"""
        member {{
          base {{
            index {{ base {{ {HDR_STACK} }} index {{ last_index {{ stack {{ {HDR_STACK} }} }} }} }}
          }}
          field: "tag"
        }}
        """,
        pb.Expr(),
    )
    with pytest.raises(EdslError, match="needs a stack"):
        _ = c.hdr.h.last


def test_field_reaches_a_field_an_attribute_shadows() -> None:
    p = Program("t")
    eth = p.header("eth", type=bit(16), next=bit(8), src=bit(48))
    p.headers = p.struct("H", eth=eth)
    p.metadata = p.struct("M")
    c = p.control("C")
    # The wart: the builder's own attribute wins over the field.
    assert c.hdr.eth.type == pb.Type(header="eth")
    with pytest.raises(EdslError, match="needs a stack"):
        _ = c.hdr.eth.next
    # field() always means the IR field, and is what the attribute means otherwise.
    for name in ("type", "next", "src"):
        f = c.hdr.eth.field(name)
        assert f.type == eth.fields[name]
        assert f.pb == text_format.Parse(member(member(var("hdr"), "eth"), name), pb.Expr())
        assert f.lval == text_format.Parse(member(member(var("hdr"), "eth"), name), pb.LValue())
    assert c.hdr.eth.field("src").pb == c.hdr.eth.src.pb
    with pytest.raises(EdslError, match="no field 'nope'"):
        c.hdr.eth.field("nope")
    with pytest.raises(EdslError, match="has no fields"):
        c.hdr.eth.src.field("type")
    # A key built on the shadowed attribute fails where it is written, in
    # the eDSL's words, not two calls later with an AttributeError.
    c.action("nop")
    for key in (exact, lpm, ternary):
        with pytest.raises(EdslError, match=r"(?s)a key is an Expr, got .*\.field\(name\)"):
            key(c.hdr.eth.type)  # pyright: ignore[reportArgumentType]
    with pytest.raises(EdslError, match="a key is an Expr, got 3"):
        exact(3)  # pyright: ignore[reportArgumentType]
    c.table("t", keys=[exact(c.hdr.eth.field("type"))], actions=["nop"])


def test_concat_chains_from_the_left() -> None:
    p = base()
    c = p.control("C")
    f, g, tag = c.hdr.h.f, c.hdr.h.g, c.hdr.stack[0].tag
    three = concat(f, g, tag)
    assert three.type == bit(28)
    assert three.pb == concat(concat(f, g), tag).pb
    assert three.pb == reduce(concat, [f, g, tag]).pb
    with pytest.raises(EdslError, match="needs Exprs"):
        concat(f, 1, g)  # pyright: ignore[reportArgumentType]


def test_assign_slice_is_the_read_modify_write() -> None:
    # The shape the stacks corpus writes by hand: every literal at the
    # target's width, the shift kept even when `lo` is 0.
    p = base()
    with p.control("C") as c:
        f = c.hdr.h.f
        with c.body() as b:
            b.assign_slice(f, 5, 3, 0b101)
            b.assign_slice(f, 0, 0, 1)
    body = p.build().blocks[0].body
    assert body[0] == stmt(
        f"""
        assign {{
          target {{ {HDR_H_F} }}
          value {{
            binary {{
              op: BINARY_OP_BIT_OR
              left {{
                binary {{
                  op: BINARY_OP_BIT_AND
                  left {{ {HDR_H_F} }}
                  right {{ unary {{ op: UNARY_OP_COMPLEMENT operand {{ {bits(8, 0b111000)} }} }} }}
                }}
              }}
              right {{
                binary {{ op: BINARY_OP_SHL left {{ {bits(8, 0b101)} }} right {{ {bits(8, 3)} }} }}
              }}
            }}
          }}
        }}
        """
    )
    assert body[1] == stmt(
        f"""
        assign {{
          target {{ {HDR_H_F} }}
          value {{
            binary {{
              op: BINARY_OP_BIT_OR
              left {{
                binary {{
                  op: BINARY_OP_BIT_AND
                  left {{ {HDR_H_F} }}
                  right {{ unary {{ op: UNARY_OP_COMPLEMENT operand {{ {bits(8, 1)} }} }} }}
                }}
              }}
              right {{
                binary {{ op: BINARY_OP_SHL left {{ {bits(8, 1)} }} right {{ {bits(8, 0)} }} }}
              }}
            }}
          }}
        }}
        """
    )
    with pytest.raises(EdslError, match="out of range"):
        b.assign_slice(f, 8, 0, 1)
    with pytest.raises(EdslError, match="does not fit"):
        b.assign_slice(f, 2, 1, 4)
    with pytest.raises(EdslError, match="lvalue"):
        b.assign_slice(f + 1, 2, 1, 1)


# ---------------------------------------------------------------------------
# Deparsers, enums and errors
# ---------------------------------------------------------------------------


def test_deparser_emits() -> None:
    p = base()
    with p.deparser("D") as d:
        with d.body() as b:
            b.emit(d.hdr.h)
            b.emit(d.hdr.stack)
            b.emit(d.hdr)
    assert p.build().blocks[0] == block(
        f"""
        name: "D" kind: BLOCK_KIND_DEPARSER
        params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_IN }}
        body {{ emit {{ value {{ {HDR_H} }} }} }}
        body {{ emit {{ value {{ {HDR_STACK} }} }} }}
        body {{ emit {{ value {{ {var("hdr")} }} }} }}
        """
    )


def test_enum_and_error_literals() -> None:
    p = Program("e")
    color = p.enum("color", "RED", "GREEN")
    custom = p.error("Custom")
    p.headers = p.struct("H")
    p.metadata = p.struct("M", c=color, err=error_t)
    with p.control("C") as c:
        meta = c.meta
        with c.body() as b:
            with b.if_((meta.c == color.GREEN) | (meta.err != p.errors.NoMatch)):
                b.assign(meta.c, color.RED)
                b.assign(meta.err, custom)
    with p.parser("P") as ps:
        with ps.state("start") as s:
            s.select(ps.meta.c, {color.RED: ps.accept, color.GREEN: ps.reject})
    program = p.build()
    assert program.errors[-1] == "Custom"
    assert program.blocks[0].body[0] == text_format.Parse(
        """
        conditional {
          condition {
            binary {
              op: BINARY_OP_OR
              left {
                binary {
                  op: BINARY_OP_EQ
                  left { member { base { var: "meta" } field: "c" } }
                  right { literal { enum_member { enum_type: "color" member: "GREEN" } } }
                }
              }
              right {
                binary {
                  op: BINARY_OP_NE
                  left { member { base { var: "meta" } field: "err" } }
                  right { literal { error: "NoMatch" } }
                }
              }
            }
          }
          then {
            assign {
              target { member { base { var: "meta" } field: "c" } }
              value { literal { enum_member { enum_type: "color" member: "RED" } } }
            }
          }
          then {
            assign {
              target { member { base { var: "meta" } field: "err" } }
              value { literal { error: "Custom" } }
            }
          }
        }
        """,
        pb.Stmt(),
    )
    assert program.blocks[1].states[0].transition == text_format.Parse(
        """
        select {
          keys { member { base { var: "meta" } field: "c" } }
          cases {
            sets { exact { enum_member { enum_type: "color" member: "RED" } } }
            target { accept {} }
          }
          cases {
            sets { exact { enum_member { enum_type: "color" member: "GREEN" } } }
            target { reject {} }
          }
        }
        """,
        pb.Transition(),
    )


# ---------------------------------------------------------------------------
# Mistakes the builder catches
# ---------------------------------------------------------------------------


def _width_mismatch(p: Program) -> None:
    c = p.control("C")
    _ = c.hdr.h.f + c.hdr.h.g


def _literal_does_not_fit(p: Program) -> None:
    c = p.control("C")
    _ = c.hdr.h.f + 256


def _int_needs_context(p: Program) -> None:
    c = p.control("C")
    mux(c.meta.ok, 1, 2)


def _bool_where_bits(p: Program) -> None:
    c = p.control("C")
    c.body().assign(c.meta.x, True)


def _unknown_field(p: Program) -> None:
    c = p.control("C")
    _ = c.hdr.h.nope


def _no_fields(p: Program) -> None:
    c = p.control("C")
    _ = c.hdr.h.f.bit


def _unknown_var(p: Program) -> None:
    c = p.control("C")
    _ = c.nope


def _missing_start_state(p: Program) -> None:
    ps = p.parser("P")
    ps.state("s").accept()
    p.build()


def _unknown_transition_target(p: Program) -> None:
    ps = p.parser("P")
    ps.state("start").transition("nowhere")
    p.build()


def _state_without_transition(p: Program) -> None:
    p.parser("P").state("start")
    p.build()


def _unknown_action_in_table(p: Program) -> None:
    c = p.control("C")
    c.table("t", keys=[exact(c.hdr.h.f)], actions=["missing"])


def _default_not_among_actions(p: Program) -> None:
    c = p.control("C")
    c.action("a")
    c.action("b")
    c.table("t", actions=["a"], default="b")


def _no_actions(p: Program) -> None:
    c = p.control("C")
    c.table("t", keys=[exact(c.hdr.h.f)], actions=[])


def _priority_without_a_ternary_key(p: Program) -> None:
    c = p.control("C")
    c.action("a")
    c.table("t", keys=[exact(c.hdr.h.f)], actions=["a"], const_entries=[entry(1, "a", priority=3)])


def _entry_arity(p: Program) -> None:
    c = p.control("C")
    c.action("a")
    c.table("t", keys=[exact(c.hdr.h.f)], actions=["a"], const_entries=[entry((1, 2), "a")])


def _select_arity(p: Program) -> None:
    ps = p.parser("P")
    ps.state("start").select((ps.hdr.h.f, ps.hdr.h.g), {1: ps.accept})


def _else_without_if(p: Program) -> None:
    b = p.control("C").body()
    with b.else_():
        pass


def _assign_to_rvalue(p: Program) -> None:
    c = p.control("C")
    c.body().assign(c.hdr.h.f + 1, 0)


def _out_arg_not_lvalue(p: Program) -> None:
    reg = edsl_externs.register(p, bit(8))
    r = p.extern_instance("r", reg, 1)
    c = p.control("C")
    c.body().call(r, "read", c.meta.x + 1, 0)


def _out_arg_wrong_width(p: Program) -> None:
    reg = edsl_externs.register(p, bit(16))
    r = p.extern_instance("r", reg, 1)
    c = p.control("C")
    c.body().call(r, "read", c.meta.x, 0)


def _result_for_void_method(p: Program) -> None:
    reg = edsl_externs.register(p, bit(8))
    r = p.extern_instance("r", reg, 1)
    c = p.control("C")
    c.body().call(r, "write", 0, 0, result=c.meta.x)


def _bad_cast(p: Program) -> None:
    p.control("C").meta.ok.cast(bit(8))


def _slice_out_of_range(p: Program) -> None:
    p.control("C").hdr.h.f[8:0]


def _truth_value(p: Program) -> None:
    c = p.control("C")
    if c.meta.ok:
        pass


def _read_next(p: Program) -> None:
    c = p.control("C")
    c.body().assign(c.meta.x, c.hdr.stack.next.tag)


def _duplicate_name(p: Program) -> None:
    c = p.control("C")
    c.action("a")
    c.local("a", bit(8))


def _local_reuses_program_name(p: Program) -> None:
    p.control("C").local("h", bit(8))


def _unknown_error(p: Program) -> None:
    _ = p.errors.Nope


def _unknown_enum_member(p: Program) -> None:
    _ = p.enum("color", "RED").BLUE


@pytest.mark.parametrize(
    "mistake",
    [
        _width_mismatch,
        _literal_does_not_fit,
        _int_needs_context,
        _bool_where_bits,
        _unknown_field,
        _no_fields,
        _unknown_var,
        _missing_start_state,
        _unknown_transition_target,
        _state_without_transition,
        _unknown_action_in_table,
        _default_not_among_actions,
        _no_actions,
        _priority_without_a_ternary_key,
        _entry_arity,
        _select_arity,
        _else_without_if,
        _assign_to_rvalue,
        _out_arg_not_lvalue,
        _out_arg_wrong_width,
        _result_for_void_method,
        _bad_cast,
        _slice_out_of_range,
        _truth_value,
        _read_next,
        _duplicate_name,
        _local_reuses_program_name,
        _unknown_error,
        _unknown_enum_member,
    ],
    ids=lambda f: f.__name__.lstrip("_"),
)
def test_mistakes_raise(mistake: Callable[[Program], None]) -> None:
    with pytest.raises(EdslError):
        mistake(base())


def test_error_messages_name_the_problem() -> None:
    p = base()
    c = p.control("C")
    with pytest.raises(EdslError, match="bit<8> vs bit<16>"):
        _ = c.hdr.h.f + c.hdr.h.g
    with pytest.raises(EdslError, match="no field 'nope'; fields are f, g"):
        _ = c.hdr.h.nope
    with pytest.raises(EdslError, match="no action 'missing'"):
        c.table("t", actions=["missing"])
    with pytest.raises(EdslError, match="no start state"):
        p.parser("P").state("s").accept()
        p.build()


def test_an_int_shift_amount_wider_than_the_left_operand_builds() -> None:
    """`bit<2> x << 4` is P4 (the amount's width is free) and is 0; the
    eDSL gives `4` the smallest width that holds it, bit<3>, instead of
    refusing it as "does not fit in bit<2>". An amount that fits keeps the
    left operand's width, as before."""
    p = Program("shift")
    h = p.header("h_t", v=bit(2), pad=bit(6))
    p.headers = p.struct("headers", h=h)
    p.metadata = p.struct("metadata")
    with p.parser("P") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.h)
            s.accept()
    with p.control("C") as c:
        with c.body() as b:
            b.assign(c.hdr.h.v, c.hdr.h.v << 4)
            b.assign(c.hdr.h.pad, c.hdr.h.pad >> 1)
    with p.deparser("D") as d:
        with d.body() as b:
            b.emit(d.hdr.h)
    p.export("parser", "P")
    p.export("control", "C")
    p.export("deparser", "D")
    program = p.build()
    assert validator.validate(program) == []
    shifts = [st.assign.value.binary.right.literal.bits for st in program.blocks[1].body]
    assert (shifts[0].width, shifts[0].value) == (3, "4")
    assert (shifts[1].width, shifts[1].value) == (6, "1")
    loaded = arch.load(program)
    # v = 0b11 << 4 is 0 in bit<2>; pad = 0b111111 >> 1 is 0b011111.
    assert arch.Switch(2).run(loaded, loaded.entries(), 0, b"\xff") == [(0, b"\x1f")]


def test_advance_takes_a_bit32_amount() -> None:
    """core.p4's `advance(in bit<32>)`: the validator requires the width and
    the printed program would not compile otherwise, so the eDSL refuses a
    narrower Expr rather than build a program the validator rejects."""
    p = base()
    with p.parser("P") as ps:
        with ps.state("start") as s:
            s.advance(8)
            s.advance(ps.meta.x.cast(bit(32)) * 8)
            with pytest.raises(EdslError, match=r"advance needs a bit<32> amount: .*bit<8>"):
                s.advance(ps.meta.x)
            s.accept()
    amounts = [st.advance.bits for st in p.build().blocks[0].states[0].body]
    assert amounts[0] == p.literal(8, bit(32)).pb
    assert amounts[1].binary.left.cast.to == bit(32)
