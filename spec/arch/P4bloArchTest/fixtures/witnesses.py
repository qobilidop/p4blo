"""Witness pairs for the Lean rule tags, and the generator of witnesses.json.

A rule tag of `P4bloIR.Coverage` claims that a request exercised one rule of
the semantics. The claim is only as good as the tag's condition, and a
condition that fires in the wrong configuration is caught by nothing else:
the differential campaigns measure which tags are hit, not whether they
should be. This table pins the conditions down. Every tag that stands for a
closed behavior, `<category>.<construct>.<case>`, has a case that must
report it and a case that must not, chosen at the boundary of its condition
where one exists; every other tag has a case that must report it.

Each case is a small program, the host's entries and a packet, with the
tags the Lean observer must report (`hits`) and must not (`misses`) and the
reply the real run gives (`reply`), so that a witness is anchored to what
actually happened. The replies come from the Python reference interpreter;
the Lean test (`spec/arch/P4bloArchTest/Coverage.lean`) checks that Lean gives
the same reply and the stated tags, and that the table covers the
inventory. `tests/test_drt_coverage.py` validates every program and checks
that witnesses.json is what this module generates.

Most programs share one template: header `h_t { a: bit<8> }`; struct
`H { h, g: h_t; s: h_t[2]; e: e_t; q: q_t }` with `e_t` of no fields and
`q_t { b: bit<4> }`; an empty `M`; a parser that extracts `hdr.h`; a control
that varies; a deparser that emits `hdr`. The first packet byte is `x`,
which is `hdr.h.a` after the parse and usually decides the case.

Regenerate with `uv run python spec/arch/P4bloArchTest/fixtures/witnesses.py`.
"""

from __future__ import annotations

import functools
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from google.protobuf import json_format

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.run import python_outcome
from p4blo.v0 import p4blo_pb2 as pb

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "witnesses.json"
PORTS = 4

# ---------------------------------------------------------------------------
# Expressions, lvalues and statements
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r"(\w+)|\.(\w+)|\[([^\]]+)\]")


def _tokens(path: str) -> list[tuple[str, str]]:
    """`a.b[i].c` as [("var", "a"), ("member", "b"), ("index", "i"), ...]."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _TOKEN.finditer(path):
        assert m.start() == pos, f"bad path {path!r}"
        pos = m.end()
        if m[1] is not None:
            assert not out, f"bad path {path!r}"
            out.append(("var", m[1]))
        elif m[2] is not None:
            out.append(("member", m[2]))
        else:
            out.append(("index", m[3]))
    assert pos == len(path), f"bad path {path!r}"
    return out


def _index(text: str) -> pb.Expr:
    """An index: a number is a `bit<32>` literal, anything else a path."""
    return lit(32, int(text)) if text.isdigit() else E(text)


def E(path: str) -> pb.Expr:
    """The expression a dotted path names, such as `hdr.s[idx].a`."""
    expr = pb.Expr()
    for kind, text in _tokens(path):
        if kind == "var":
            expr = pb.Expr(var=text)
        elif kind == "member":
            expr = pb.Expr(member=pb.Member(base=expr, field=text))
        else:
            expr = pb.Expr(index=pb.Index(base=expr, index=_index(text)))
    return expr


def L(path: str) -> pb.LValue:
    """The lvalue a dotted path names; a final `.next` is `hs.next`."""
    lv = pb.LValue()
    for kind, text in _tokens(path):
        if kind == "var":
            lv = pb.LValue(var=text)
        elif kind == "member" and text == "next":
            lv = pb.LValue(next=pb.Next(stack=lv))
        elif kind == "member":
            lv = pb.LValue(member=pb.LMember(base=lv, field=text))
        else:
            lv = pb.LValue(index=pb.LIndex(base=lv, index=_index(text)))
    return lv


def bits_literal(width: int, value: int) -> pb.Literal:
    return pb.Literal(bits=pb.BitsLiteral(width=width, value=str(value)))


def lit(width: int, value: int) -> pb.Expr:
    return pb.Expr(literal=bits_literal(width, value))


def boolean(value: bool) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(boolean=value))


def error(name: str) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(error=name))


def enum(enum_type: str, member: str) -> pb.Expr:
    return pb.Expr(
        literal=pb.Literal(enum_member=pb.EnumLiteral(enum_type=enum_type, member=member))
    )


_BINARY = {
    "+": pb.BINARY_OP_ADD,
    "-": pb.BINARY_OP_SUB,
    "*": pb.BINARY_OP_MUL,
    "|+|": pb.BINARY_OP_ADD_SAT,
    "|-|": pb.BINARY_OP_SUB_SAT,
    "&": pb.BINARY_OP_BIT_AND,
    "|": pb.BINARY_OP_BIT_OR,
    "^": pb.BINARY_OP_BIT_XOR,
    "<<": pb.BINARY_OP_SHL,
    ">>": pb.BINARY_OP_SHR,
    "++": pb.BINARY_OP_CONCAT,
    "==": pb.BINARY_OP_EQ,
    "!=": pb.BINARY_OP_NE,
    "<": pb.BINARY_OP_LT,
    "<=": pb.BINARY_OP_LE,
    ">": pb.BINARY_OP_GT,
    ">=": pb.BINARY_OP_GE,
    "&&": pb.BINARY_OP_AND,
    "||": pb.BINARY_OP_OR,
}


def op(symbol: str, left: pb.Expr | str, right: pb.Expr | str | int) -> pb.Expr:
    """`left symbol right`; a string is a path, an int an 8-bit literal."""
    lhs = E(left) if isinstance(left, str) else left
    rhs = E(right) if isinstance(right, str) else lit(8, right) if isinstance(right, int) else right
    return pb.Expr(binary=pb.Binary(op=_BINARY[symbol], left=lhs, right=rhs))


def unary(kind: pb.UnaryOp, operand: pb.Expr) -> pb.Expr:
    return pb.Expr(unary=pb.Unary(op=kind, operand=operand))


def bits(width: int) -> pb.Type:
    return pb.Type(bits=width)


BOOL = pb.Type(boolean=pb.BoolType())


def cast(to: pb.Type, operand: pb.Expr) -> pb.Expr:
    return pb.Expr(cast=pb.Cast(to=to, operand=operand))


def mux(condition: pb.Expr, then: pb.Expr, otherwise: pb.Expr) -> pb.Expr:
    return pb.Expr(mux=pb.Mux(**{"condition": condition, "then": then, "otherwise": otherwise}))


def x_below(n: int) -> pb.Expr:
    """`hdr.h.a < n`, the usual case split on the first packet byte."""
    return op("<", "hdr.h.a", n)


def assign(target: str, value: pb.Expr | str | int) -> pb.Stmt:
    v = E(value) if isinstance(value, str) else lit(8, value) if isinstance(value, int) else value
    return pb.Stmt(assign=pb.Assign(target=L(target), value=v))


def if_(condition: pb.Expr, then: Sequence[pb.Stmt], otherwise: Sequence[pb.Stmt] = ()) -> pb.Stmt:
    return pb.Stmt(
        conditional=pb.If(**{"condition": condition, "then": then, "otherwise": otherwise})
    )


def set_valid(path: str) -> pb.Stmt:
    return pb.Stmt(set_valid=pb.SetValid(header=L(path)))


def set_invalid(path: str) -> pb.Stmt:
    return pb.Stmt(set_invalid=pb.SetInvalid(header=L(path)))


def push(path: str, count: int) -> pb.Stmt:
    return pb.Stmt(push=pb.Push(stack=L(path), count=count))


def pop(path: str, count: int) -> pb.Stmt:
    return pb.Stmt(pop=pb.Pop(stack=L(path), count=count))


def extract(path: str) -> pb.Stmt:
    return pb.Stmt(extract=pb.Extract(target=L(path)))


def emit(value: pb.Expr | str) -> pb.Stmt:
    return pb.Stmt(emit=pb.Emit(value=E(value) if isinstance(value, str) else value))


def arg_in(value: pb.Expr | str) -> pb.Arg:
    return pb.Arg(expr=E(value) if isinstance(value, str) else value)


def arg_out(path: str) -> pb.Arg:
    return pb.Arg(lvalue=L(path))


def call_action(name: str, *args: pb.Arg) -> pb.Stmt:
    return pb.Stmt(call_action=pb.CallAction(action=name, args=args))


def call_block(name: str, *args: pb.Arg) -> pb.Stmt:
    return pb.Stmt(call_block=pb.CallBlock(block=name, args=args))


def call_extern(instance: str, method: str, *args: pb.Arg, result: str | None = None) -> pb.Stmt:
    call = pb.CallExtern(instance=instance, method=method, args=args)
    if result is not None:
        call.result.CopyFrom(L(result))
    return pb.Stmt(call_extern=call)


def apply(table: str, hit: str | None = None) -> pb.Stmt:
    a = pb.Apply(table=table)
    if hit is not None:
        a.hit.CopyFrom(L(hit))
    return pb.Stmt(apply=a)


def param(name: str, type: pb.Type, direction: pb.Direction) -> pb.Param:
    return pb.Param(name=name, type=type, direction=direction)


def local(name: str, type: pb.Type) -> pb.Var:
    return pb.Var(name=name, type=type)


# ---------------------------------------------------------------------------
# Parser states
# ---------------------------------------------------------------------------


def to(target: str) -> pb.Target:
    if target == "accept":
        return pb.Target(accept=pb.Accept())
    if target == "reject":
        return pb.Target(reject=pb.Reject())
    return pb.Target(state=target)


def exact(value: pb.Literal) -> pb.KeySet:
    return pb.KeySet(exact=value)


def exact8(value: int) -> pb.KeySet:
    return exact(bits_literal(8, value))


DONT_CARE = pb.KeySet(dont_care=pb.DontCare())


def state(
    name: str,
    body: Sequence[pb.Stmt] = (),
    goto: str = "accept",
    select: Sequence[pb.Expr | str] | None = None,
    cases: Sequence[tuple[Sequence[pb.KeySet], str]] = (),
) -> pb.State:
    """A state that goes to `goto`, or selects on `select` over `cases`."""
    if select is None:
        transition = pb.Transition(direct=to(goto))
    else:
        keys = [E(k) if isinstance(k, str) else k for k in select]
        transition = pb.Transition(
            select=pb.Select(
                keys=keys, cases=[pb.SelectCase(sets=s, target=to(t)) for s, t in cases]
            )
        )
    return pb.State(name=name, body=body, transition=transition)


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------

H = pb.Type(struct="H")
M = pb.Type(struct="M")
H_T = pb.Type(header="h_t")
IN, OUT, INOUT, NONE = pb.DIRECTION_IN, pb.DIRECTION_OUT, pb.DIRECTION_INOUT, pb.DIRECTION_NONE


def _types(program: pb.Program) -> None:
    def fields(*items: tuple[str, pb.Type]) -> list[pb.Field]:
        return [pb.Field(name=n, type=t) for n, t in items]

    program.errors.extend(ir.CORE_ERRORS)
    program.header_types.extend(
        [
            pb.HeaderType(name="h_t", fields=fields(("a", bits(8)))),
            pb.HeaderType(name="e_t"),
            pb.HeaderType(name="q_t", fields=fields(("b", bits(4)))),
        ]
    )
    stack = pb.Type(stack=pb.StackType(header="h_t", size=2))
    program.struct_types.extend(
        [
            pb.StructType(
                name="H",
                fields=fields(
                    ("h", H_T),
                    ("g", H_T),
                    ("s", stack),
                    ("e", pb.Type(header="e_t")),
                    ("q", pb.Type(header="q_t")),
                ),
            ),
            pb.StructType(name="M"),
        ]
    )
    program.enum_types.append(pb.EnumType(name="Color", members=["Red", "Green"]))


@dataclass
class Spec:
    """The parts of a witness program that vary; the rest is the template."""

    body: Sequence[pb.Stmt] = ()
    locals: Sequence[pb.Var] = ()
    actions: Sequence[pb.Action] = ()
    tables: Sequence[pb.Table] = ()
    states: Sequence[pb.State] = (state("start", [extract("hdr.h")]),)
    parser_locals: Sequence[pb.Var] = ()
    emits: Sequence[str] = ("hdr",)
    blocks: Sequence[pb.Block] = ()
    externs: bool = False


def _externs(program: pb.Program) -> None:
    b8, b16, b32 = bits(8), bits(16), bits(32)
    program.extern_types.extend(
        [
            pb.ExternType(
                name="register",
                constructor_params=[param("size", b32, IN)],
                methods=[
                    pb.Method(
                        name="read", params=[param("result", b8, OUT), param("index", b32, IN)]
                    ),
                    pb.Method(
                        name="write", params=[param("index", b32, IN), param("value", b8, IN)]
                    ),
                ],
            ),
            pb.ExternType(
                name="checksum16",
                methods=[pb.Method(name="compute", params=[param("data", b16, IN)], returns=b16)],
            ),
        ]
    )
    program.extern_instances.extend(
        [
            pb.ExternInstance(name="r", extern_type="register", args=[bits_literal(32, 4)]),
            pb.ExternInstance(name="c", extern_type="checksum16"),
        ]
    )


def build(name: str, spec: Spec) -> pb.Program:
    program = pb.Program(name=name, headers="H", metadata="M")
    _types(program)
    if spec.externs:
        _externs(program)
    program.blocks.extend(
        [
            pb.Block(
                name="P",
                kind=pb.BLOCK_KIND_PARSER,
                params=[param("hdr", H, OUT), param("meta", M, INOUT)],
                locals=spec.parser_locals,
                states=spec.states,
                start_state="start",
            ),
            *spec.blocks,
            pb.Block(
                name="C",
                kind=pb.BLOCK_KIND_CONTROL,
                params=[param("hdr", H, INOUT), param("meta", M, INOUT)],
                locals=spec.locals,
                actions=spec.actions,
                tables=spec.tables,
                body=spec.body,
            ),
            pb.Block(
                name="D",
                kind=pb.BLOCK_KIND_DEPARSER,
                params=[param("hdr", H, IN)],
                body=[emit(e) for e in spec.emits],
            ),
        ]
    )
    program.exports.extend(
        [
            pb.Export(role="parser", block="P"),
            pb.Export(role="control", block="C"),
            pb.Export(role="deparser", block="D"),
        ]
    )
    return program


def control(
    *body: pb.Stmt,
    locals: Sequence[pb.Var] = (),
    actions: Sequence[pb.Action] = (),
    tables: Sequence[pb.Table] = (),
    blocks: Sequence[pb.Block] = (),
    emits: Sequence[str] = ("hdr",),
    externs: bool = False,
) -> Spec:
    """The template with this control body and its declarations."""
    return Spec(
        body=body,
        locals=locals,
        actions=actions,
        tables=tables,
        blocks=blocks,
        emits=emits,
        externs=externs,
    )


def result(expr: pb.Expr, *before: pb.Stmt, locals: Sequence[pb.Var] = ()) -> Spec:
    """A control that runs `before`, then sets `hdr.h.a = expr`."""
    return Spec(body=[*before, assign("hdr.h.a", expr)], locals=locals)


def parser(
    *states: pb.State, locals: Sequence[pb.Var] = (), blocks: Sequence[pb.Block] = ()
) -> Spec:
    """The template with these parser states, from `start`, and an empty control."""
    return Spec(states=states, parser_locals=locals, blocks=blocks)


def action(name: str, body: Sequence[pb.Stmt], *params: pb.Param) -> pb.Action:
    return pb.Action(name=name, params=params, body=body)


NO_ACTION = action("NoAction", [])
SET = action("set", [assign("hdr.h.a", "v")], param("v", bits(8), NONE))


def call(name: str, *args: int) -> pb.ActionCall:
    return pb.ActionCall(action=name, args=[bits_literal(8, a) for a in args])


def table(
    kind: pb.MatchKind,
    actions: Sequence[str] = ("set", "NoAction"),
    default: pb.ActionCall | None = None,
    const_entries: Sequence[pb.Entry] = (),
) -> pb.Table:
    t = pb.Table(
        name="t",
        keys=[pb.Key(expr=E("hdr.h.a"), match_kind=kind, name="hdr.h.a")],
        actions=actions,
        const_entries=const_entries,
        size=16,
    )
    if default is not None:
        t.default_action.CopyFrom(default)
    return t


def entry(key: pb.KeyValue, action_call: pb.ActionCall, priority: int = 0) -> pb.Entry:
    return pb.Entry(keys=[key], action=action_call, priority=priority)


def exact_key(value: int) -> pb.KeyValue:
    return pb.KeyValue(exact=str(value))


def lpm_key(value: int, prefix: int) -> pb.KeyValue:
    return pb.KeyValue(lpm=pb.LpmValue(value=str(value), prefix_len=prefix))


def ternary_key(value: int, mask: int) -> pb.KeyValue:
    return pb.KeyValue(ternary=pb.TernaryValue(value=str(value), mask=str(mask)))


def host(entries: Sequence[pb.Entry] = (), default: pb.ActionCall | None = None) -> pb.Entries:
    te = pb.TableEntries(block="C", table="t", entries=entries)
    if default is not None:
        te.default_action.CopyFrom(default)
    return pb.Entries(tables=[te])


# ---------------------------------------------------------------------------
# The witness table
# ---------------------------------------------------------------------------


@dataclass
class Witness:
    """One request of one program, with the tags it must and must not report."""

    program: str
    packet: bytes
    hits: Sequence[str]
    misses: Sequence[str] = ()
    entries: pb.Entries = field(default_factory=pb.Entries)


PROGRAMS: dict[str, pb.Program] = {}
WITNESSES: list[Witness] = []


def program(name: str, spec: Spec) -> str:
    assert name not in PROGRAMS, name
    PROGRAMS[name] = build(name, spec)
    return name


def case(
    name: str,
    packet: Sequence[int],
    hits: Sequence[str],
    misses: Sequence[str] = (),
    entries: pb.Entries | None = None,
) -> None:
    WITNESSES.append(Witness(name, bytes(packet), hits, misses, entries or pb.Entries()))


EQUALITY_KINDS = [
    "expr.equality.bits",
    "expr.equality.bool",
    "expr.equality.enum",
    "expr.equality.error",
    "expr.equality.struct",
    "expr.equality.stack",
]
HEADER_CASES = [
    "expr.equality.header.bothValid",
    "expr.equality.header.validityDiffers",
    "expr.equality.header.bothInvalid",
    "expr.equality.header.invalidFieldsDiffer",
]
TABLE_MISSES = ["table.miss.defaultAction", "table.miss.noAction", "table.miss.hostDefault"]


def arithmetic() -> None:
    """Values and operations: each closed behavior of `bit<N>` arithmetic at
    its boundary, the negative one step inside it."""
    for name, symbol, operand, tag, pos, neg in [
        ("add", "+", 5, "expr.add.wrap", 251, 250),
        ("sub", "-", 5, "expr.sub.wrap", 4, 5),
        ("mul", "*", 2, "expr.mul.wrap", 128, 127),
        ("addSat", "|+|", 5, "expr.addSat.clamp", 251, 250),
        ("subSat", "|-|", 5, "expr.subSat.clamp", 4, 5),
        ("shlTruncate", "<<", 1, "expr.shl.truncate", 128, 127),
    ]:
        p = program(name, result(op(symbol, "hdr.h.a", operand)))
        plain = "expr.shl" if symbol == "<<" else f"expr.{name}"
        case(p, [pos], [plain, tag, "expr.literal", "expr.member", "stmt.assign"])
        case(p, [neg], [plain], [tag, "expr.shl.overflow", "expr.shift.otherWidth"])
    p = program("shlOverflow", result(op("<<", lit(8, 1), "hdr.h.a")))
    case(p, [8], ["expr.shl", "expr.shl.overflow"], ["expr.shl.truncate"])
    case(p, [7], ["expr.shl"], ["expr.shl.overflow", "expr.shl.truncate"])
    p = program("shrOverflow", result(op(">>", lit(8, 0xFF), "hdr.h.a")))
    case(p, [8], ["expr.shr", "expr.shr.overflow"])
    case(p, [7], ["expr.shr"], ["expr.shr.overflow"])
    p = program("shiftOtherWidth", result(op("<<", "hdr.h.a", lit(4, 1))))
    case(p, [1], ["expr.shl", "expr.shift.otherWidth"], ["expr.shl.truncate"])


def equality() -> None:
    """Values and operations: `==` and `!=` by the type of their operands,
    and the header rule at the top and nested in a struct or stack."""

    def others(kind: str) -> list[str]:
        return [k for k in EQUALITY_KINDS if k != kind] + HEADER_CASES

    def one_two(cond: pb.Expr) -> pb.Expr:
        return mux(cond, lit(8, 1), lit(8, 2))

    p = program("eqBits", result(one_two(op("==", "hdr.h.a", 3))))
    case(p, [3], ["expr.eq", "expr.equality.bits", "expr.mux"], others("expr.equality.bits"))
    p = program(
        "eqBool",
        result(
            one_two(op("==", "r", boolean(True))),
            assign("r", x_below(3)),
            locals=[local("r", BOOL)],
        ),
    )
    case(p, [1], ["expr.eq", "expr.equality.bool", "lvalue.var"], others("expr.equality.bool"))
    p = program(
        "eqEnum",
        result(
            one_two(op("!=", "k", enum("Color", "Red"))),
            if_(x_below(3), [assign("k", enum("Color", "Green"))]),
            locals=[local("k", pb.Type(enum_type="Color"))],
        ),
    )
    case(p, [1], ["expr.ne", "expr.equality.enum"], others("expr.equality.enum"))
    p = program(
        "eqError",
        result(
            one_two(op("==", "err", error("NoError"))),
            if_(x_below(3), [assign("err", error("PacketTooShort"))]),
            locals=[local("err", pb.Type(error=pb.ErrorType()))],
        ),
    )
    case(p, [1], ["expr.eq", "expr.equality.error"], others("expr.equality.error"))
    # hdr.h is invalid when bit 7 of x is set, hdr.g valid when bit 6 is,
    # and hdr.g.a is x with bit 0 cleared; hdr.s[0].a records the result.
    p = program(
        "eqHeader",
        control(
            if_(op(">", "hdr.h.a", 127), [set_invalid("hdr.h")]),
            if_(op("!=", op("&", "hdr.h.a", 64), 0), [set_valid("hdr.g")]),
            assign("hdr.g.a", op("&", "hdr.h.a", 0xFE)),
            assign("r", op("==", "hdr.h", "hdr.g")),
            set_valid("hdr.s[0]"),
            assign("hdr.s[0].a", one_two(E("r"))),
            locals=[local("r", BOOL)],
        ),
    )
    not_nested = ["expr.equality.struct", "expr.equality.stack"]
    case(p, [0x40], ["expr.equality.header.bothValid"], [*HEADER_CASES[1:], *not_nested])
    case(p, [0x00], ["expr.equality.header.validityDiffers"], [*HEADER_CASES[::2], *not_nested])
    case(p, [0x80], ["expr.equality.header.bothInvalid"], [*HEADER_CASES[:2], HEADER_CASES[3]])
    case(p, [0x81], HEADER_CASES[2:], HEADER_CASES[:2])
    # A struct and a stack whose headers differ only in the stored fields
    # of invalid ones: every header inside is compared by the header rule.
    p = program(
        "eqNested",
        result(
            mux(op("&&", "r", "q"), lit(8, 1), lit(8, 0)),
            assign("k", "hdr"),
            assign("k.g.a", 9),
            assign("k.s[0].a", 9),
            assign("r", op("==", "k", "hdr")),
            assign("q", op("==", "k.s", "hdr.s")),
            locals=[local("k", H), local("r", BOOL), local("q", BOOL)],
        ),
    )
    case(
        p,
        [0x2A],
        ["expr.equality.struct", "expr.equality.stack", *HEADER_CASES[::2], HEADER_CASES[3]],
        ["expr.equality.stack.nextIndexDiffers", HEADER_CASES[1]],
    )
    p = program(
        "eqStackNextIndex",
        result(
            mux(op("==", "k.s", "hdr.s"), lit(8, 1), lit(8, 2)),
            if_(x_below(1), [push("hdr.s", 1)]),
            locals=[local("k", H)],
        ),
    )
    case(p, [0], ["expr.equality.stack", "expr.equality.stack.nextIndexDiffers"])
    case(p, [1], ["expr.equality.stack"], ["expr.equality.stack.nextIndexDiffers"])


def casts() -> None:
    """Values and operations: the five casts the ledger names."""
    all_casts = [
        "expr.cast.truncate",
        "expr.cast.extend",
        "expr.cast.sameWidth",
        "expr.cast.boolToBits",
        "expr.cast.bitsToBool",
    ]
    p = program("castNarrow", result(cast(bits(8), cast(bits(4), E("hdr.h.a")))))
    case(p, [0x5A], ["expr.cast", *all_casts[:2]], all_casts[2:])
    p = program("castSame", result(cast(bits(8), E("hdr.h.a"))))
    case(p, [7], ["expr.cast", "expr.cast.sameWidth"], [*all_casts[:2], *all_casts[3:]])
    p = program("castBool", result(cast(bits(8), cast(bits(1), x_below(3)))))
    case(p, [1], ["expr.cast.boolToBits", "expr.cast.extend"], ["expr.cast.bitsToBool"])
    p = program(
        "castToBool", result(mux(cast(BOOL, cast(bits(1), E("hdr.h.a"))), lit(8, 1), lit(8, 2)))
    )
    case(p, [3], ["expr.cast.bitsToBool", "expr.cast.truncate"], ["expr.cast.boolToBits"])


def short_circuits() -> None:
    """Expressions, "Evaluation order": `&&` and `||` skip their right operand."""
    both = op("&&", x_below(5), op(">", "hdr.h.a", 2))
    p = program("and", result(mux(both, lit(8, 1), lit(8, 2))))
    case(p, [9], ["expr.and", "expr.and.shortCircuit", "expr.lt"], ["expr.gt"])
    case(p, [3], ["expr.and", "expr.gt"], ["expr.and.shortCircuit"])
    either = op("||", x_below(5), op(">", "hdr.h.a", 200))
    p = program("or", result(mux(either, lit(8, 1), lit(8, 2))))
    case(p, [1], ["expr.or", "expr.or.shortCircuit"], ["expr.gt"])
    case(p, [9], ["expr.or", "expr.gt"], ["expr.or.shortCircuit"])


def uninitialized() -> None:
    """Values and operations, "Uninitialized variables": a block local and
    an action's `out` parameter read before they are written."""
    p = program(
        "uninitLocal",
        result(E("y"), if_(x_below(1), [assign("y", 7)]), locals=[local("y", bits(8))]),
    )
    branches = ["stmt.conditional", "expr.var"]
    case(
        p,
        [1],
        ["value.uninitialized", "stmt.conditional.otherwise", *branches],
        ["stmt.conditional.then"],
    )
    case(
        p,
        [0],
        ["stmt.conditional.then", *branches],
        ["value.uninitialized", "stmt.conditional.otherwise"],
    )
    # b(out x, in c) writes x only when c is 0 and then reads it; the call
    # passes hdr.h.a as both, so the `in` argument overlaps the `out` one.
    b = action(
        "b",
        [if_(op("<", "c", 1), [assign("x", 5)]), assign("y", "x")],
        param("x", bits(8), OUT),
        param("c", bits(8), IN),
    )
    p = program(
        "uninitActionOut",
        control(
            call_action("b", arg_out("hdr.h.a"), arg_in("hdr.h.a")),
            set_valid("hdr.g"),
            assign("hdr.g.a", "y"),
            locals=[local("y", bits(8))],
            actions=[b],
        ),
    )
    direct_call = ["call.action", "stmt.callAction", "call.param.out", "call.param.in"]
    one_out = ["call.copyOut.order", "call.param.inout", "call.action.nested"]
    case(p, [1], ["value.uninitialized", "call.copyIn.overlap", *direct_call], one_out)
    case(p, [0], ["call.copyIn.overlap", *direct_call], ["value.uninitialized", *one_out])


def headers() -> None:
    """The header entries: each program makes hdr.g valid when x is 0."""
    g_valid_if_zero = if_(x_below(1), [set_valid("hdr.g")])
    for name, stmt, tag in [
        ("readInvalid", assign("hdr.h.a", op("+", "hdr.g.a", 1)), "header.field.readInvalid"),
        ("writeInvalid", assign("hdr.g.a", 7), "header.field.writeInvalid"),
        ("assignInvalid", assign("hdr.s[0]", "hdr.g"), "header.assign.invalid"),
        ("setInvalidTwice", set_invalid("hdr.g"), "header.setInvalid.alreadyInvalid"),
    ]:
        kind = "stmt.setInvalid" if name == "setInvalidTwice" else "stmt.assign"
        p = program(name, control(g_valid_if_zero, stmt))
        case(p, [1], [tag, "stmt.conditional.otherwise", kind])
        case(p, [0], ["stmt.conditional.then"], [tag])
    p = program("setValidTwice", control(g_valid_if_zero, set_valid("hdr.g")))
    case(p, [0], ["header.setValid.alreadyValid", "stmt.setValid"])
    case(p, [1], ["stmt.setValid"], ["header.setValid.alreadyValid"])
    # a(inout x) calls b(out) on x.a: b's copy-back writes a field of a's
    # parameter, in a's name layer, and that header is invalid when x is 1.
    inner = action("b", [assign("x", 1)], param("x", bits(8), OUT))
    outer = action("a", [call_action("b", arg_out("x.a"))], param("x", H_T, INOUT))
    p = program(
        "nestedCopyBack",
        control(
            g_valid_if_zero,
            call_action("a", arg_out("hdr.g")),
            set_valid("hdr.g"),
            actions=[inner, outer],
        ),
    )
    nested = ["call.action.nested", "call.param.out", "call.param.inout"]
    case(p, [1], ["header.field.writeInvalid", *nested], ["call.param.in", "call.copyOut.order"])
    case(p, [0], nested, ["header.field.writeInvalid"])


def stacks() -> None:
    """The stack entries. `hs.lastIndex` is allowed only in a parser, so its
    witness is a parser that sets `hdr.h.a` to it."""
    last = cast(bits(8), pb.Expr(last_index=pb.LastIndex(stack=E("hdr.s"))))
    idx = [local("idx", bits(32))]
    set_idx = assign("idx", cast(bits(32), E("hdr.h.a")))
    p = program("readOutOfRange", result(op("+", "hdr.s[idx].a", 1), set_idx, locals=idx))
    case(p, [2], ["stack.index.readOutOfRange", "expr.index"])
    case(p, [1], ["expr.index", "header.field.readInvalid"], ["stack.index.readOutOfRange"])
    p = program("writeOutOfRange", control(set_idx, set_valid("hdr.s[idx]"), locals=idx))
    case(p, [2], ["stack.index.writeOutOfRange", "lvalue.index"])
    case(p, [1], ["lvalue.index"], ["stack.index.writeOutOfRange"])
    # a(inout e) moves the index its argument `hdr.s[t]` read, from x to
    # 5 - x. Copy-back writes the element t named at copy-in (ledger:
    # Copy-back target), so the write is out of range when x is 5 and in
    # range when x is 0, whatever t is when the action returns.
    t = [local("t", bits(32))]
    set_t = assign("t", cast(bits(32), E("hdr.h.a")))
    moves = action(
        "a",
        [assign("t", op("-", lit(32, 5), "t")), set_valid("e"), assign("e.a", 119)],
        param("e", H_T, INOUT),
    )
    p = program(
        "copyBackIndexMoves",
        control(set_t, call_action("a", arg_out("hdr.s[t]")), locals=t, actions=[moves]),
    )
    copied = ["call.action", "call.param.inout", "lvalue.index"]
    case(p, [5], ["stack.index.writeOutOfRange", *copied])
    case(p, [0], copied, ["stack.index.writeOutOfRange"])
    # The stack is empty unless x is 0, which extracts one element.
    p = program(
        "lastIndexEmpty",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(0)], "fill"), ([DONT_CARE], "look")],
            ),
            state("fill", [extract("hdr.s.next")], goto="look"),
            state("look", [assign("hdr.h.a", last)]),
        ),
    )
    case(p, [1], ["stack.lastIndex.empty", "expr.lastIndex"])
    case(p, [0, 0x0B], ["expr.lastIndex"], ["stack.lastIndex.empty"])
    # push_front(2) clamps after a push of 1 (x = 0); pop_front(1) clamps
    # unless a push of 2 came first (x = 1).
    p = program("pushClamp", control(if_(x_below(1), [push("hdr.s", 1)]), push("hdr.s", 2)))
    case(p, [0], ["stack.push.clamp", "stmt.push"])
    case(p, [1], ["stmt.push"], ["stack.push.clamp", "stack.push.oversize"])
    p = program("popClamp", control(if_(x_below(1), [push("hdr.s", 2)]), pop("hdr.s", 1)))
    case(p, [1], ["stack.pop.clamp", "stmt.pop"])
    case(p, [0], ["stmt.pop"], ["stack.pop.clamp", "stack.pop.oversize"])
    for name, make, tag in [
        ("pushOversize", push, "stack.push.oversize"),
        ("popOversize", pop, "stack.pop.oversize"),
    ]:
        p = program(name, control(if_(x_below(1), [make("hdr.s", 3)], [make("hdr.s", 2)])))
        kind = "stmt.push" if make is push else "stmt.pop"
        case(p, [0], [tag, kind])
        case(p, [1], [kind], [tag])


def parsers() -> None:
    """The parser entries, each with its own parser and an empty control."""
    p = program("extractNextOnly", parser(state("start", [extract("hdr.s.next")])))
    case(p, [5], ["parser.extract.next", "stmt.extract"], ["parser.extract.header"])
    p = program("extract", Spec())
    case(
        p,
        [0x2A],
        [
            "stmt.extract",
            "parser.extract.header",
            "parser.transition.direct",
            "parser.target.accept",
            "lvalue.member",
            "emit.struct",
            "emit.stack",
            "emit.header.valid",
            "emit.header.invalid",
        ],
        [
            "parser.extract.tooShort",
            "parser.extract.next",
            "parser.extract.zeroWidth",
            "parser.transition.select",
            "emit.padding",
        ],
    )
    case(p, [], ["parser.extract.tooShort"], ["parser.target.accept", "parser.transition.direct"])

    # x = 3 extracts three times into a stack of two, x = 2 twice.
    def to_next(name: str) -> pb.State:
        return state(
            name, [extract("hdr.s.next")], goto={"n1": "n2", "n2": "n3"}.get(name, "accept")
        )

    p = program(
        "extractNext",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(3)], "n1"), ([exact8(2)], "n2"), ([DONT_CARE], "accept")],
            ),
            to_next("n1"),
            to_next("n2"),
            to_next("n3"),
        ),
    )
    full = ["parser.extract.next.full", "parser.extract.next.fullAndShort"]
    case(p, [3, 10, 11, 12], ["parser.extract.next", full[0]], [full[1]])
    case(p, [3, 10, 11], ["parser.extract.next", *full])
    case(
        p,
        [2, 10, 11],
        ["parser.extract.next", "parser.target.state"],
        [*full, "parser.extract.tooShort"],
    )
    case(p, [2, 10], ["parser.extract.next", "parser.extract.tooShort"], full)
    p = program(
        "extractZeroWidth",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(1)], "z"), ([DONT_CARE], "accept")],
            ),
            state("z", [extract("hdr.e")]),
        ),
    )
    case(p, [1], ["parser.extract.zeroWidth", "parser.extract.header"], ["parser.extract.tooShort"])
    case(p, [2], ["parser.extract.header"], ["parser.extract.zeroWidth"])
    p = program(
        "extractIndexOutOfRange",
        parser(
            state(
                "start",
                [
                    extract("hdr.h"),
                    assign("idx", cast(bits(32), E("hdr.h.a"))),
                    extract("hdr.s[idx]"),
                ],
            ),
            locals=[local("idx", bits(32))],
        ),
    )
    case(p, [2, 0x0B], ["parser.extract.indexOutOfRange", "stack.index.writeOutOfRange"])
    case(p, [1, 0x0B], ["parser.extract.header"], ["parser.extract.indexOutOfRange"])
    p = program(
        "advance",
        parser(state("start", [extract("hdr.h"), pb.Stmt(advance=pb.Advance(bits=lit(32, 8)))])),
    )
    case(p, [1, 2], ["stmt.advance"], ["parser.advance.tooShort"])
    case(p, [1], ["stmt.advance", "parser.advance.tooShort"])

    def verify(cond: pb.Expr, err: str) -> pb.Stmt:
        return pb.Stmt(verify=pb.Verify(condition=cond, error=err))

    p = program(
        "verify",
        parser(
            state(
                "start",
                [
                    extract("hdr.h"),
                    verify(op("!=", "hdr.h.a", 9), "NoMatch"),
                    verify(op("!=", "hdr.h.a", 7), "NoError"),
                ],
            )
        ),
    )
    verdicts = ["parser.verify.pass", "parser.verify.fail", "parser.verify.failNoError"]
    case(p, [1], ["stmt.verify", verdicts[0]], verdicts[1:])
    case(p, [9], ["stmt.verify", verdicts[1]], [verdicts[0], verdicts[2]])
    case(p, [7], verdicts)


def lookaheads() -> None:
    """Parsers, "`lookahead<T>`": x picks the type looked ahead at into hdr.g."""

    def look(t: pb.Type) -> pb.Expr:
        return pb.Expr(lookahead=pb.Lookahead(type=t))

    p = program(
        "lookahead",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[
                    ([exact8(1)], "lb"),
                    ([exact8(2)], "lbool"),
                    ([exact8(3)], "lh"),
                    ([DONT_CARE], "accept"),
                ],
            ),
            state("lb", [set_valid("hdr.g"), assign("hdr.g.a", look(bits(8)))]),
            state(
                "lbool",
                [set_valid("hdr.g"), assign("hdr.g.a", cast(bits(8), cast(bits(1), look(BOOL))))],
            ),
            state("lh", [assign("hdr.g", look(H_T))]),
        ),
    )
    kinds = ["expr.lookahead.bits", "expr.lookahead.bool", "expr.lookahead.header"]
    short = "expr.lookahead.tooShort"
    for i, kind in enumerate(kinds):
        case(
            p,
            [i + 1, 0x80 + i],
            ["expr.lookahead", kind],
            [k for k in kinds if k != kind] + [short],
        )
    case(p, [1], ["expr.lookahead", kinds[0], short])


def selects() -> None:
    """Parsers, "`select`": the key-set kinds, order, keys and no match."""
    k = functools.partial(bits_literal, 8)
    masked = pb.KeySet(masked=pb.MaskedValue(value=k(0x10), mask=k(0xF0)))
    ranged = pb.KeySet(range=pb.RangeValue(lo=k(0x18), hi=k(0x2F)))

    def mark(name: str, value: int) -> pb.State:
        """A state that records `value` in a valid hdr.g, then accepts."""
        return state(name, [set_valid("hdr.g"), assign("hdr.g.a", value)])

    p = program(
        "select",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(1)], "sa"), ([masked], "sb"), ([ranged], "sc")],
            ),
            mark("sa", 1),
            mark("sb", 2),
            mark("sc", 3),
        ),
    )
    kinds = ["select.exact", "select.masked", "select.range", "select.dontCare"]
    others = ["select.firstOfSeveral", "select.noMatch", "select.nonBitsKey", "select.multiKey"]
    case(p, [1], ["parser.transition.select", kinds[0]], [*kinds[1:], *others])
    case(p, [0x15], [kinds[1]], [kinds[0], kinds[2], *others])
    case(p, [0x19], [kinds[1], "select.firstOfSeveral"], [kinds[2]])
    case(p, [0x25], [kinds[2]], [*kinds[:2], *others])
    case(p, [0x99], ["select.noMatch"], [*kinds, "select.firstOfSeveral", "parser.target.reject"])
    p = program(
        "selectDefault",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(1)], "accept"), ([DONT_CARE], "sd")],
            ),
            mark("sd", 4),
        ),
    )
    case(p, [5], [kinds[3]], [kinds[0], "select.firstOfSeveral"])
    case(p, [1], [kinds[0], "select.firstOfSeveral"], [kinds[3]])
    true, false = exact(pb.Literal(boolean=True)), exact(pb.Literal(boolean=False))
    p = program(
        "selectBool",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=[x_below(5)],
                cases=[([true], "accept"), ([false], "reject")],
            )
        ),
    )
    case(p, [1], ["select.nonBitsKey", "parser.target.accept"], ["parser.target.reject"])
    case(
        p,
        [9],
        ["select.nonBitsKey", "parser.target.reject"],
        ["parser.target.accept", "parser.subparser.reject", "parser.subparser"],
    )
    p = program(
        "selectTwoKeys",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a", x_below(5)],
                cases=[([exact8(1), true], "accept"), ([DONT_CARE, DONT_CARE], "reject")],
            )
        ),
    )
    case(p, [1], ["select.multiKey", "select.nonBitsKey", "select.exact"])


def loops() -> None:
    """Parsers, "Parser loop bound", and sub-parsers."""
    last = pb.Expr(
        member=pb.Member(
            base=pb.Expr(
                index=pb.Index(
                    base=E("hdr.s"), index=pb.Expr(last_index=pb.LastIndex(stack=E("hdr.s")))
                )
            ),
            field="a",
        )
    )
    p = program(
        "revisit",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(1)], "loop"), ([DONT_CARE], "accept")],
            ),
            state(
                "loop",
                [extract("hdr.s.next")],
                select=[last],
                cases=[([exact8(1)], "loop"), ([DONT_CARE], "accept")],
            ),
        ),
    )
    case(p, [1, 1, 0], ["parser.revisit"], ["parser.timeout"])
    case(p, [1, 0], ["parser.target.state"], ["parser.revisit"])
    p = program(
        "timeout",
        parser(
            state(
                "start",
                [extract("hdr.h")],
                select=["hdr.h.a"],
                cases=[([exact8(1)], "spin"), ([DONT_CARE], "accept")],
            ),
            state(
                "spin", select=["hdr.h.a"], cases=[([exact8(1)], "spin"), ([DONT_CARE], "accept")]
            ),
        ),
    )
    case(p, [1], ["parser.timeout"], ["parser.timeout.subparser", "parser.revisit"])
    case(p, [2], ["parser.target.accept"], ["parser.timeout", "parser.target.state"])
    # SP rejects on 3, verifies false with NoError on 4, extracts hdr.g on 5
    # and accepts otherwise; P calls it once, and twice on 6 without
    # consuming in between.
    sub = pb.Block(
        name="SP",
        kind=pb.BLOCK_KIND_PARSER,
        params=[param("hdr", H, INOUT)],
        states=[
            state(
                "start",
                select=["hdr.h.a"],
                cases=[
                    ([exact8(3)], "reject"),
                    ([exact8(4)], "sv"),
                    ([exact8(5)], "sx"),
                    ([DONT_CARE], "accept"),
                ],
            ),
            state("sv", [pb.Stmt(verify=pb.Verify(condition=boolean(False), error="NoError"))]),
            state("sx", [extract("hdr.g")]),
        ],
        start_state="start",
    )
    p = program(
        "subparser",
        parser(
            state(
                "start",
                [extract("hdr.h"), call_block("SP", arg_out("hdr"))],
                select=["hdr.h.a"],
                cases=[([exact8(6)], "again"), ([DONT_CARE], "accept")],
            ),
            state("again", [call_block("SP", arg_out("hdr"))]),
            blocks=[sub],
        ),
    )
    called = ["parser.subparser", "call.block", "stmt.callBlock", "call.param.inout"]
    fault = ["call.block.faultCopyBack"]
    case(
        p,
        [3],
        [*called, "parser.subparser.reject", "parser.target.reject", *fault],
        ["call.param.out", "call.param.in"],
    )
    case(p, [4], [*called, "parser.verify.failNoError", *fault], ["parser.subparser.reject"])
    case(p, [2], called, ["parser.subparser.reject", *fault, "parser.timeout"])
    case(p, [5, 0x77], [*called, "parser.extract.header"], fault)
    case(p, [6], [*called, "parser.timeout", "parser.timeout.subparser", *fault])


def tables() -> None:
    """The table entries."""
    set_hit = [
        apply("t", hit="r"),
        set_valid("hdr.g"),
        assign("hdr.g.a", mux(E("r"), lit(8, 1), lit(8, 2))),
    ]
    r = [local("r", BOOL)]
    p = program(
        "tableExact",
        control(
            *set_hit,
            locals=r,
            actions=[SET, NO_ACTION],
            tables=[table(pb.MATCH_KIND_EXACT, default=call("set", 0x77))],
        ),
    )
    entries = host([entry(exact_key(1), call("set", 0x11))])
    hit = ["table.hit", "table.key.exact", "call.tableAction", "call.param.none", "stmt.apply"]
    case(p, [1], [*hit, "table.hit.written"], ["table.miss", *TABLE_MISSES], entries)
    case(
        p,
        [2],
        ["table.miss", "table.miss.defaultAction", "table.hit.written"],
        ["table.hit", *TABLE_MISSES[1:]],
        entries,
    )
    case(
        p,
        [2],
        ["table.miss.defaultAction", "table.miss.hostDefault"],
        ["table.miss.noAction"],
        host(default=call("set", 0x77)),
    )
    case(
        p,
        [2],
        ["table.miss.noAction", "table.miss.hostDefault"],
        ["table.miss.defaultAction", "call.param.none"],
        host(default=call("NoAction")),
    )
    p = program(
        "tableNoActionDeclared",
        control(
            apply("t"),
            actions=[SET, NO_ACTION],
            tables=[table(pb.MATCH_KIND_EXACT, default=call("NoAction"))],
        ),
    )
    case(
        p,
        [2],
        ["table.miss", "table.miss.noAction", "call.tableAction"],
        ["table.miss.defaultAction", "table.miss.hostDefault", "call.param.none"],
    )
    case(p, [1], ["table.hit"], ["table.hit.written", "table.miss"], entries)
    p = program(
        "tableNoDefault",
        control(apply("t"), actions=[SET, NO_ACTION], tables=[table(pb.MATCH_KIND_EXACT)]),
    )
    case(
        p,
        [2],
        ["table.miss", "table.miss.noAction"],
        ["table.miss.defaultAction", "call.tableAction"],
    )
    p = program(
        "tableLpm", control(apply("t"), actions=[SET, NO_ACTION], tables=[table(pb.MATCH_KIND_LPM)])
    )
    lpm = host([entry(lpm_key(0x10, 4), call("set", 1)), entry(lpm_key(0x12, 8), call("set", 2))])
    case(
        p,
        [0x12],
        ["table.key.lpm", "table.lpm.longest"],
        ["table.key.exact", "table.key.ternary"],
        lpm,
    )
    case(p, [0x13], ["table.key.lpm", "table.hit"], ["table.lpm.longest"], lpm)
    p = program(
        "tableTernary",
        control(apply("t"), actions=[SET, NO_ACTION], tables=[table(pb.MATCH_KIND_TERNARY)]),
    )
    ternary = host(
        [
            entry(ternary_key(0x10, 0xF0), call("set", 1), 1),
            entry(ternary_key(0x12, 0xFF), call("set", 2), 2),
            entry(ternary_key(0x20, 0xF0), call("set", 3), 0),
        ]
    )
    prio = ["table.ternary.priority", "table.ternary.priorityZero"]
    case(
        p,
        [0x12],
        ["table.key.ternary", prio[0]],
        [prio[1], "table.key.exact", "table.key.lpm"],
        ternary,
    )
    case(p, [0x13], ["table.key.ternary", "table.hit"], prio, ternary)
    case(p, [0x25], [prio[1]], [prio[0]], ternary)
    p = program(
        "tableConst",
        control(
            apply("t"),
            actions=[SET, NO_ACTION],
            tables=[
                table(pb.MATCH_KIND_EXACT, const_entries=[entry(exact_key(5), call("set", 0x55))])
            ],
        ),
    )
    case(p, [5], ["table.constEntry", "table.hit"])
    case(p, [6], ["table.miss"], ["table.constEntry"])
    # w assigns the lvalue the apply writes hit to; n does not.
    w = action("w", [assign("r", boolean(True))])
    n = action("n", [])
    p = program(
        "tableOverwritesAction",
        control(
            *set_hit,
            locals=r,
            actions=[w, n, NO_ACTION],
            tables=[table(pb.MATCH_KIND_EXACT, actions=["w", "n", "NoAction"])],
        ),
    )
    ow = host([entry(exact_key(1), call("w")), entry(exact_key(3), call("n"))])
    case(p, [1], ["table.hit.overwritesAction", "table.hit"], [], ow)
    case(
        p,
        [3],
        ["table.hit", "table.hit.written"],
        ["table.hit.overwritesAction", "call.param.none"],
        ow,
    )


def calls() -> None:
    """Block calls and extern calls."""
    sub = pb.Block(
        name="SC",
        kind=pb.BLOCK_KIND_CONTROL,
        params=[param("i", bits(8), IN), param("o", bits(8), OUT), param("hh", H_T, INOUT)],
        body=[assign("o", op("+", "i", 1)), assign("hh.a", 9)],
    )
    prelude = [set_valid("hdr.g"), set_valid("hdr.s[0]")]
    directions = ["call.param.in", "call.param.out", "call.param.inout"]
    p = program(
        "subcontrol",
        control(
            *prelude,
            call_block("SC", arg_in("hdr.h.a"), arg_out("hdr.g.a"), arg_out("hdr.s[0]")),
            blocks=[sub],
        ),
    )
    case(
        p,
        [1],
        ["call.block", "stmt.callBlock", "call.copyOut.order", *directions],
        ["call.copyIn.overlap", "parser.subparser", "call.block.faultCopyBack", "call.param.none"],
    )
    p = program(
        "subcontrolOverlap",
        control(
            *prelude,
            call_block("SC", arg_in("hdr.s[0].a"), arg_out("hdr.g.a"), arg_out("hdr.s[0]")),
            blocks=[sub],
        ),
    )
    case(p, [1], ["call.copyIn.overlap", "call.block", *directions])
    extern_calls = [
        call_extern("r", "write", arg_in(lit(32, 1)), arg_in("hdr.h.a")),
    ]
    p = program("externWrite", control(*extern_calls, externs=True))
    results = ["call.extern.out", "call.extern.result"]
    case(
        p,
        [0x2A],
        ["call.extern", "stmt.callExtern", "call.param.in"],
        [*results, "call.copyOut.order"],
    )
    p = program(
        "externRead",
        control(
            *extern_calls,
            set_valid("hdr.g"),
            call_extern("r", "read", arg_out("hdr.g.a"), arg_in(lit(32, 1))),
            call_extern("c", "compute", arg_in(op("++", "hdr.h.a", "hdr.g.a")), result="w"),
            set_valid("hdr.s[0]"),
            assign("hdr.s[0].a", pb.Expr(slice=pb.Slice(operand=E("w"), hi=7, lo=0))),
            locals=[local("w", bits(16))],
            externs=True,
        ),
    )
    case(
        p,
        [0x2A],
        ["call.extern", *results, "call.param.out", "expr.concat", "expr.slice"],
        ["call.copyOut.order"],
    )

    # r.read writes `hdr.s[t].a` through the lvalue resolved before the
    # call: out of range when x is 2, a field of the invalid s[1] when x is
    # 1, a field of the valid s[0] when x is 0.
    t = [local("t", bits(32))]
    p = program(
        "externReadIndexed",
        control(
            assign("t", cast(bits(32), E("hdr.h.a"))),
            set_valid("hdr.s[0]"),
            call_extern("r", "read", arg_out("hdr.s[t].a"), arg_in(lit(32, 1))),
            locals=t,
            externs=True,
        ),
    )
    out = ["call.extern.out", "call.param.out", "lvalue.member"]
    case(p, [2], ["stack.index.writeOutOfRange", *out], ["header.field.writeInvalid"])
    case(p, [1], ["header.field.writeInvalid", *out], ["stack.index.writeOutOfRange"])
    case(p, [0], out, ["stack.index.writeOutOfRange", "header.field.writeInvalid"])
    # The index of an out argument is evaluated when it is resolved, before
    # the call, so reading the unassigned `t` there is uninitialized.
    p = program(
        "externReadUninitialized",
        control(
            set_valid("hdr.s[0]"),
            call_extern("r", "read", arg_out("hdr.s[t].a"), arg_in(lit(32, 1))),
            locals=t,
            externs=True,
        ),
    )
    case(p, [0x2A], ["value.uninitialized", *out], ["header.field.writeInvalid"])


def deparsers() -> None:
    """The deparser entries."""
    p = program("emitOne", control(if_(x_below(1), [set_invalid("hdr.h")]), emits=["hdr.h"]))
    case(
        p,
        [1],
        ["emit.header.valid", "stmt.emit"],
        ["emit.header.invalid", "emit.struct", "emit.stack"],
    )
    case(p, [0], ["emit.header.invalid"], ["emit.header.valid"])
    p = program("emitPadding", control(set_valid("hdr.q"), assign("hdr.q.b", lit(4, 5))))
    case(p, [0x2A], ["emit.padding", "emit.struct"])


def remaining_cases() -> None:
    """The evaluator cases no witness above needs on the way."""
    p = program(
        "operators",
        control(
            set_valid("hdr.g"),
            assign("hdr.g.a", unary(pb.UNARY_OP_COMPLEMENT, E("hdr.h.a"))),
            set_valid("hdr.s[1]"),
            assign("hdr.s[1].a", unary(pb.UNARY_OP_NEGATE, E("hdr.h.a"))),
            assign("hdr.s[0]", "hdr.s[1]"),
            assign("hdr.s[0].a", op("|", op("&", "hdr.h.a", 0x0F), op("^", "hdr.h.a", 0x33))),
            assign(
                "r",
                op("&&", unary(pb.UNARY_OP_NOT, op("<=", "hdr.h.a", 3)), op(">=", "hdr.h.a", 1)),
            ),
            assign("r", op("==", "r", pb.Expr(is_valid=pb.IsValid(header=E("hdr.g"))))),
            locals=[local("r", BOOL)],
        ),
    )
    case(
        p,
        [0x2A],
        [
            "expr.complement",
            "expr.negate",
            "expr.bitAnd",
            "expr.bitOr",
            "expr.bitXor",
            "expr.not",
            "expr.le",
            "expr.ge",
            "expr.isValid",
        ],
    )


def generate() -> dict[str, object]:
    """The witness table as the JSON document the Lean test reads."""
    PROGRAMS.clear()
    WITNESSES.clear()
    arithmetic()
    equality()
    casts()
    short_circuits()
    uninitialized()
    headers()
    stacks()
    parsers()
    lookaheads()
    selects()
    loops()
    tables()
    calls()
    deparsers()
    remaining_cases()
    cases: list[dict[str, object]] = []
    for w in WITNESSES:
        loaded = arch.load(PROGRAMS[w.program])
        outcome = python_outcome(loaded, Case(w.entries, 0, w.packet), PORTS)
        assert outcome.error is None and outcome.diagnostic is None, (w.program, outcome)
        assert outcome.outputs is not None
        cases.append(
            {
                "program": w.program,
                "entries": json_format.MessageToDict(w.entries, preserving_proto_field_name=True),
                "packet": w.packet.hex(),
                "hits": sorted(set(w.hits)),
                "misses": sorted(set(w.misses)),
                "reply": {"outputs": [[port, data.hex()] for port, data in outcome.outputs]},
            }
        )
    return {
        "_": "Generated by witnesses.py beside this file; see its docstring.",
        "programs": [json.loads(ir.dump_json(program)) for program in PROGRAMS.values()],
        "cases": cases,
    }


def render() -> str:
    """witnesses.json: one program or case per line, so that a change to one
    witness is a one-line diff."""
    document = generate()

    def one_line(value: object) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def items(key: str) -> str:
        rows = document[key]
        assert isinstance(rows, list)
        return ",\n".join(f"  {one_line(row)}" for row in rows)

    return (
        f'{{\n "_": {json.dumps(document["_"])},\n'
        f' "cases": [\n{items("cases")}\n ],\n'
        f' "programs": [\n{items("programs")}\n ]\n}}\n'
    )


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8")
