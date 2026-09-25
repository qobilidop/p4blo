"""Program families aimed at the rules of the semantics.

The families of `programs.py` and `stateful_programs.py` vary an expression
or a register update inside a fixed context. The families here vary the
program's shape: which statements a control runs and in what context, and
what a parser's states extract, look ahead at, verify and select on. They
exist because the rule tags of the Lean semantics (`P4bloIR.Coverage`) that
the fixed families never reached, listed in `tests/drt-unhit-tags.json`,
are all about shape: direct and nested action calls, equality on headers,
structs, stacks and enums, whole-header assignment, stack indices taken
from the packet, `advance`, `lookahead` of `bool` and headers, selects with
ranges, several keys, no default and non-`bit` keys, explicit rejection in
a sub-parser, and parser loops that consume nothing.

A family is a function of a `Chooser` (`p4blo.drt.choice`), which makes
every decision and names it. Every option is typed by construction, so any
sequence of decisions is a well-typed program, and a program the validator
refuses is a generator bug that fails the campaign rather than being
filtered. A `RandomChooser` makes a seed name a program and its cases
exactly; the tests' Hypothesis chooser shrinks a failing program to a
smaller one of the same types; `guided.GuidedChooser` weights the options
by what a campaign has learned.

Every labelled decision a sample took is one of its `features`, spelled
`point=label`. The points are named by the context the decision is made in
(`control.feature`, `call.args`, `parser.stmt`, `subparser.stmt`,
`select.key`), so a feature says which construct encloses what it chose;
the guided driver pairs each rule tag a run hits with each feature of the
program, the one-feature-sensitive coverage of ESMeta's JESTfs. `TARGETS`
names, for the options built to reach a rule, the tags they aim at.

Profiles. `lean` draws from everything. `spectec` leaves out the choices
whose outcome the ledger (docs/ir-semantics.md) records as a deviation
from P4-SpecTec or as a refinement of a case SpecTec gives no outcome for,
so that a disagreement on the simulator is a finding and never a known
difference: header equality where the operands' validity differs or both
are invalid ("Header equality"), a stack read out of range ("Index out of
range"), `lastIndex` of an empty stack ("`hs.lastIndex`"), and parser
loops, whose revisit rule has no counterpart there ("Parser loop bound").
Its parsers are acyclic and call their sub-parser at most once per path.

All programs share one template (`template`): `h_t { a: bit<8> }`, a
zero-width `e_t`, a result header `o_t` of six bytes, a struct `S_t` of a
byte and a header, the enum `Color`, and `H { h, g: h_t; s: h_t[N]; e: e_t;
o: o_t }`. Every emitted header is a whole number of bytes, so the
simulator's unpadded emission (docs/ir-semantics.md, "Deparsers") never
enters a comparison.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from p4blo import ir
from p4blo.drt.case import Case
from p4blo.drt.choice import Chooser, RandomChooser
from p4blo.drt.generate import generate
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "FAMILIES",
    "TARGETS",
    "Profile",
    "Sample",
    "control_family",
    "parser_family",
    "sample",
]

Profile = Literal["lean", "spectec"]


@dataclass(frozen=True)
class Sample:
    """A program, the requests sent to it in order, and the decisions that
    made it."""

    family: str
    program: pb.Program
    cases: tuple[Case, ...]
    features: frozenset[str]

    def describe(self) -> str:
        """The top-level decisions, for a report line."""
        top = sorted(
            f.split("=", 1)[1]
            for f in self.features
            if f.startswith(("control.feature=", "parser.stmt=", "parser.transition="))
        )
        return f"{self.family}: {' '.join(dict.fromkeys(top))}"


# The rule tags an option is built to reach. The guided driver favours an
# option while one of its targets is unhit; the list is a hint, not a claim,
# and the tags a run actually hits are what the campaign measures.
TARGETS: dict[str, tuple[str, ...]] = {
    "control.feature=call": ("call.action", "stmt.callAction"),
    "call.nested=yes": ("call.action.nested",),
    "call.args=overlap": ("call.copyIn.overlap",),
    "control.feature=eq_header": (
        "expr.equality.header.bothValid",
        "expr.equality.header.validityDiffers",
        "expr.equality.header.bothInvalid",
        "expr.equality.header.invalidFieldsDiffer",
    ),
    "validity=invalid": (
        "expr.equality.header.bothInvalid",
        "expr.equality.header.invalidFieldsDiffer",
    ),
    "validity=packet": ("expr.equality.header.validityDiffers",),
    "control.feature=eq_struct": ("expr.equality.struct",),
    "control.feature=eq_stack": ("expr.equality.stack",),
    "eq_stack.push=packet": ("expr.equality.stack.nextIndexDiffers",),
    "control.feature=eq_enum": ("expr.equality.enum",),
    "control.feature=header_assign": ("header.assign.invalid",),
    "header_assign.validity=invalid": ("header.assign.invalid",),
    "control.feature=set_valid": ("header.setValid.alreadyValid",),
    "stack.index=packet": ("stack.index.readOutOfRange", "stack.index.writeOutOfRange"),
    "control.feature=table": ("table.hit", "table.miss"),
    "table.action=hit": ("table.hit.overwritesAction",),
    "table.default=none": ("table.miss.noAction",),
    "parser.stmt=extract_index": ("parser.extract.indexOutOfRange",),
    "subparser.stmt=extract_index": ("parser.extract.indexOutOfRange",),
    "parser.stmt=extract_empty": ("parser.extract.zeroWidth",),
    "parser.stmt=advance": ("stmt.advance", "parser.advance.tooShort"),
    "parser.stmt=lookahead_bool": ("expr.lookahead.bool",),
    "parser.stmt=lookahead_header": ("expr.lookahead.header",),
    "parser.stmt=lookahead_logic": ("expr.lookahead.tooShort",),
    "parser.stmt=last_index": ("stack.lastIndex.empty",),
    "parser.stmt=verify": ("parser.verify.fail", "parser.verify.failNoError"),
    "subparser.stmt=verify": ("parser.verify.failNoError",),
    "verify.error=NoError": ("parser.verify.failNoError",),
    "parser.transition=reject": ("parser.target.reject",),
    "subparser.transition=reject": ("parser.subparser.reject",),
    "parser.transition=loop": ("parser.timeout", "parser.revisit"),
    "subparser.transition=loop": ("parser.timeout.subparser",),
    "parser.stmt=call_sp": ("parser.subparser",),
    "select.keys=two": ("select.multiKey",),
    "select.key=bool": ("select.nonBitsKey",),
    "select.key=enum": ("select.nonBitsKey",),
    "select.key=error": ("select.nonBitsKey",),
    "select.default=no": ("select.noMatch",),
    "keyset=range": ("select.range",),
    "keyset=masked": ("select.masked",),
}


# ---------------------------------------------------------------------------
# Syntax
# ---------------------------------------------------------------------------

_TOKEN = re.compile(r"(\w+)|\.(\w+)|\[([^\]]+)\]")


def _tokens(path: str) -> list[tuple[str, str]]:
    """`a.b[i].c` as [("var", "a"), ("member", "b"), ("index", "i"), ...]."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _TOKEN.finditer(path):
        if m.start() != pos:
            raise ValueError(f"bad path {path!r}")
        pos = m.end()
        if m[1] is not None:
            out.append(("var", m[1]))
        elif m[2] is not None:
            out.append(("member", m[2]))
        else:
            out.append(("index", m[3]))
    if pos != len(path) or not out or out[0][0] != "var":
        raise ValueError(f"bad path {path!r}")
    return out


def _index(text: str) -> pb.Expr:
    return lit(32, int(text)) if text.isdigit() else E(text)


def E(path: str) -> pb.Expr:
    """The expression a path names, such as `hdr.s[idx].a`."""
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
    """The lvalue a path names; a final `.next` is `hs.next`."""
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


def _as_lvalue(expr: pb.Expr) -> pb.LValue:
    match expr.WhichOneof("kind"):
        case "var":
            return pb.LValue(var=expr.var)
        case "member":
            return pb.LValue(
                member=pb.LMember(base=_as_lvalue(expr.member.base), field=expr.member.field)
            )
        case "index":
            return pb.LValue(
                index=pb.LIndex(base=_as_lvalue(expr.index.base), index=expr.index.index)
            )
        case kind:
            raise ValueError(f"not an lvalue: {kind}")


def bits_literal(width: int, value: int) -> pb.Literal:
    return pb.Literal(bits=pb.BitsLiteral(width=width, value=str(value)))


def lit(width: int, value: int) -> pb.Expr:
    return pb.Expr(literal=bits_literal(width, value))


def boolean(value: bool) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(boolean=value))


def enum(member: str) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(enum_member=pb.EnumLiteral(enum_type="Color", member=member)))


def error(name: str) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(error=name))


def binary(op: pb.BinaryOp, left: pb.Expr, right: pb.Expr) -> pb.Expr:
    return pb.Expr(binary=pb.Binary(op=op, left=left, right=right))


def cast(to: pb.Type, operand: pb.Expr) -> pb.Expr:
    return pb.Expr(cast=pb.Cast(to=to, operand=operand))


def mux(condition: pb.Expr, then: pb.Expr, otherwise: pb.Expr) -> pb.Expr:
    return pb.Expr(mux=pb.Mux(**{"condition": condition, "then": then, "otherwise": otherwise}))


def lookahead(type: pb.Type) -> pb.Expr:
    return pb.Expr(lookahead=pb.Lookahead(type=type))


def is_valid(header: pb.Expr) -> pb.Expr:
    return pb.Expr(is_valid=pb.IsValid(header=header))


def assign(target: pb.LValue | str, value: pb.Expr) -> pb.Stmt:
    lv = L(target) if isinstance(target, str) else target
    return pb.Stmt(assign=pb.Assign(target=lv, value=value))


def if_(condition: pb.Expr, then: Sequence[pb.Stmt], otherwise: Sequence[pb.Stmt] = ()) -> pb.Stmt:
    return pb.Stmt(
        conditional=pb.If(**{"condition": condition, "then": then, "otherwise": otherwise})
    )


def set_valid(target: pb.LValue | str) -> pb.Stmt:
    return pb.Stmt(set_valid=pb.SetValid(header=L(target) if isinstance(target, str) else target))


def set_invalid(target: pb.LValue | str) -> pb.Stmt:
    return pb.Stmt(
        set_invalid=pb.SetInvalid(header=L(target) if isinstance(target, str) else target)
    )


def extract(target: pb.LValue | str) -> pb.Stmt:
    return pb.Stmt(extract=pb.Extract(target=L(target) if isinstance(target, str) else target))


def as_byte(condition: pb.Expr) -> pb.Expr:
    """1 when the condition holds, 2 otherwise, so neither is a zero field."""
    return mux(condition, lit(8, 1), lit(8, 2))


BIT8 = pb.Type(bits=8)
BIT32 = pb.Type(bits=32)
BOOL = pb.Type(boolean=pb.BoolType())
COLOR = pb.Type(enum_type="Color")
ERROR = pb.Type(error=pb.ErrorType())
H_T = pb.Type(header="h_t")
S_T = pb.Type(struct="S_t")
H = pb.Type(struct="H")
IN, OUT, INOUT, NONE = pb.DIRECTION_IN, pb.DIRECTION_OUT, pb.DIRECTION_INOUT, pb.DIRECTION_NONE
EQ, NE, LT = pb.BINARY_OP_EQ, pb.BINARY_OP_NE, pb.BINARY_OP_LT
RESULTS = 6
COLORS = ("Red", "Green", "Blue")
ERRORS = (*ir.CORE_ERRORS, "BadValue")


def stack_type(size: int) -> pb.Type:
    return pb.Type(stack=pb.StackType(header="h_t", size=size))


def template(name: str, stack: int) -> pb.Program:
    """The shared types, an empty parser, control and deparser, exported."""
    program = pb.Program(name=name, headers="H", metadata="M")
    program.errors.extend(ERRORS)
    program.header_types.extend(
        [
            pb.HeaderType(name="h_t", fields=[pb.Field(name="a", type=BIT8)]),
            pb.HeaderType(name="e_t"),
            pb.HeaderType(
                name="o_t", fields=[pb.Field(name=f"r{i}", type=BIT8) for i in range(RESULTS)]
            ),
        ]
    )
    program.struct_types.extend(
        [
            pb.StructType(
                name="H",
                fields=[
                    pb.Field(name="h", type=H_T),
                    pb.Field(name="g", type=H_T),
                    pb.Field(name="s", type=stack_type(stack)),
                    pb.Field(name="e", type=pb.Type(header="e_t")),
                    pb.Field(name="o", type=pb.Type(header="o_t")),
                ],
            ),
            pb.StructType(name="M", fields=[pb.Field(name="parser_error", type=ERROR)]),
            pb.StructType(
                name="S_t", fields=[pb.Field(name="v", type=BIT8), pb.Field(name="x", type=H_T)]
            ),
        ]
    )
    program.enum_types.append(pb.EnumType(name="Color", members=COLORS))
    program.blocks.extend(
        [
            pb.Block(
                name="P",
                kind=pb.BLOCK_KIND_PARSER,
                params=[
                    pb.Param(name="hdr", type=H, direction=OUT),
                    pb.Param(name="meta", type=pb.Type(struct="M"), direction=INOUT),
                ],
                start_state="start",
            ),
            pb.Block(
                name="C",
                kind=pb.BLOCK_KIND_CONTROL,
                params=[
                    pb.Param(name="hdr", type=H, direction=INOUT),
                    pb.Param(name="meta", type=pb.Type(struct="M"), direction=INOUT),
                ],
            ),
            pb.Block(
                name="D",
                kind=pb.BLOCK_KIND_DEPARSER,
                params=[pb.Param(name="hdr", type=H, direction=IN)],
                body=[pb.Stmt(emit=pb.Emit(value=E("hdr")))],
            ),
        ]
    )
    program.exports.extend(
        pb.Export(role=role, block=block)
        for role, block in (("parser", "P"), ("control", "C"), ("deparser", "D"))
    )
    return program


def _block(program: pb.Program, name: str) -> pb.Block:
    return next(b for b in program.blocks if b.name == name)


def _byte(ch: Chooser, point: str) -> int:
    """A packet byte: small values meet the small thresholds conditions use."""
    if ch.choice(f"{point}.byte", ("small", "any")) == "small":
        return ch.integer(point, 0, 4)
    return ch.integer(point, 0, 255)


def _local_error(meta: str = "meta") -> pb.Expr:
    """`meta.parser_error` as a byte: its position in the error list, plus one."""
    value = lit(8, 0)
    for i, name in reversed(list(enumerate(ERRORS))):
        value = mux(binary(EQ, E(f"{meta}.parser_error"), error(name)), lit(8, i + 1), value)
    return value


# ---------------------------------------------------------------------------
# The control family
# ---------------------------------------------------------------------------


class _Control:
    """A control body built one feature at a time. Each feature gets its own
    locals and result byte `hdr.o.r<k>`, so features do not interact
    through storage except where a feature is about `hdr` itself."""

    def __init__(self, ch: Chooser, program: pb.Program, profile: Profile, stack: int) -> None:
        self.ch = ch
        self.program = program
        self.profile = profile
        self.stack = stack
        self.block = _block(program, "C")
        self.body: list[pb.Stmt] = []
        self.tables: list[str] = []

    def local(self, name: str, type: pb.Type) -> str:
        self.block.locals.add(name=name, type=type)
        return name

    def condition(self, point: str) -> pb.Expr:
        """A packet-dependent condition on the parsed bytes."""
        match self.ch.choice(f"{point}.condition", ("x_below", "y_bit")):
            case "x_below":
                return binary(LT, E("hdr.h.a"), lit(8, self.ch.integer(point, 1, 4)))
            case _:
                mask = 1 << self.ch.integer(point, 0, 2)
                return binary(
                    NE, binary(pb.BINARY_OP_BIT_AND, E("hdr.g.a"), lit(8, mask)), lit(8, 0)
                )

    def operand(self, point: str) -> pb.Expr:
        """A byte the packet decides: a parsed field or a constant."""
        match self.ch.choice(f"{point}.operand", ("x", "y", "const")):
            case "x":
                return E("hdr.h.a")
            case "y":
                return E("hdr.g.a")
            case _:
                return lit(8, self.ch.integer(point, 0, 4))

    def feature(self, k: int) -> None:
        kinds = [
            "call",
            "eq_header",
            "eq_struct",
            "eq_stack",
            "eq_enum",
            "header_assign",
            "set_valid",
            "stack_index",
            "table",
        ]
        getattr(self, self.ch.choice("control.feature", kinds))(k)

    # -- calls -----------------------------------------------------------------

    def call(self, k: int) -> None:
        """`f<k>(in x, inout y)` or `f<k>(out y)`, called directly, maybe
        calling a second action; the `in` argument may overlap the other."""
        ch = self.ch
        shape = ch.choice("call.shape", ("in_inout", "out", "header"))
        nested = ch.chance("call.nested")
        name = f"f{k}"
        inner_body: list[pb.Stmt] = []
        if nested:
            # Declared first: printed P4 must declare an action before a call.
            inner = self.block.actions.add(name=f"f{k}_inner")
            inner.params.add(name="z", type=BIT8, direction=INOUT)
            inner.body.append(assign("z", binary(pb.BINARY_OP_BIT_XOR, E("z"), lit(8, 0x5A))))
        action = self.block.actions.add(name=name)
        targets = ["hdr.h.a", "hdr.g.a", f"hdr.o.r{k}"]
        target = ch.choice("call.target", targets)
        args: list[pb.Arg] = []
        if shape == "header":
            action.params.add(name="y", type=H_T, direction=INOUT)
            action.body.append(assign("y.a", binary(pb.BINARY_OP_ADD, E("y.a"), lit(8, 1))))
            if nested:
                inner_body.append(_call_action(f"f{k}_inner", pb.Arg(lvalue=L("y.a"))))
            header = target.rsplit(".", 1)[0] if target != f"hdr.o.r{k}" else "hdr.g"
            args.append(pb.Arg(lvalue=L(header)))
            overlap = ch.choice("call.args", ("disjoint", "overlap"))
            action.params.add(name="c", type=BIT8, direction=IN)
            action.body.append(if_(binary(LT, E("c"), lit(8, 3)), [assign("y.a", E("c"))]))
            args.append(
                pb.Arg(expr=E(f"{header}.a") if overlap == "overlap" else self.operand("call.in"))
            )
        elif shape == "in_inout":
            action.params.add(name="x", type=BIT8, direction=IN)
            action.params.add(name="y", type=BIT8, direction=INOUT)
            action.body.append(assign("y", binary(pb.BINARY_OP_ADD, E("y"), E("x"))))
            if nested:
                inner_body.append(_call_action(f"f{k}_inner", pb.Arg(lvalue=L("y"))))
            overlap = ch.choice("call.args", ("disjoint", "overlap"))
            args.append(pb.Arg(expr=E(target) if overlap == "overlap" else self.operand("call.in")))
            args.append(pb.Arg(lvalue=L(target)))
        else:
            action.params.add(name="y", type=BIT8, direction=OUT)
            action.params.add(name="c", type=BIT8, direction=IN)
            action.body.append(if_(binary(LT, E("c"), lit(8, 3)), [assign("y", lit(8, 7))]))
            if nested:
                inner_body.append(_call_action(f"f{k}_inner", pb.Arg(lvalue=L("y"))))
            args.append(pb.Arg(lvalue=L(target)))
            overlap = ch.choice("call.args", ("disjoint", "overlap"))
            args.append(pb.Arg(expr=E(target) if overlap == "overlap" else self.operand("call.in")))
        action.body.extend(inner_body)
        call = _call_action(name, *args)
        if ch.chance("call.guard"):
            call = if_(self.condition("call.guard"), [call])
        self.body.append(call)

    # -- equality --------------------------------------------------------------

    def validity(self, header: str) -> list[pb.Stmt]:
        """Make a local header valid, leave it invalid, or let the packet decide."""
        options = ("valid",) if self.profile == "spectec" else ("valid", "invalid", "packet")
        match self.ch.choice("validity", options):
            case "valid":
                return [set_valid(header)]
            case "invalid":
                return []
            case _:
                return [if_(self.condition("validity"), [set_valid(header)])]

    def eq_header(self, k: int) -> None:
        x = self.local(f"f{k}x", H_T)
        y = self.local(f"f{k}y", H_T)
        self.body.append(assign(f"{x}.a", E("hdr.h.a")))
        self.body.append(assign(f"{y}.a", self.operand("eq_header.field")))
        self.body.extend(self.validity(x))
        self.body.extend(self.validity(y))
        op = EQ if self.ch.choice("eq.op", ("eq", "ne")) == "eq" else NE
        self.body.append(assign(f"hdr.o.r{k}", as_byte(binary(op, E(x), E(y)))))

    def eq_struct(self, k: int) -> None:
        p = self.local(f"f{k}p", S_T)
        q = self.local(f"f{k}q", S_T)
        for name in (p, q):
            self.body.append(assign(f"{name}.v", self.operand("eq_struct.v")))
            self.body.append(assign(f"{name}.x.a", E("hdr.h.a")))
            self.body.extend(self.validity(f"{name}.x"))
        if self.ch.chance("eq_struct.copy"):
            self.body.append(assign(q, E(p)))
        op = EQ if self.ch.choice("eq.op", ("eq", "ne")) == "eq" else NE
        self.body.append(assign(f"hdr.o.r{k}", as_byte(binary(op, E(p), E(q)))))

    def eq_stack(self, k: int) -> None:
        size = self.ch.integer("eq_stack.size", 1, 3)
        p = self.local(f"f{k}p", stack_type(size))
        q = self.local(f"f{k}q", stack_type(size))
        for name in (p, q):
            for i in range(size):
                self.body.append(assign(f"{name}[{i}].a", self.operand("eq_stack.field")))
                if self.profile == "spectec":
                    self.body.append(set_valid(f"{name}[{i}]"))
                else:
                    self.body.extend(self.validity(f"{name}[{i}]"))
        if self.profile == "lean":
            # push_front moves nextIndex, which equality ignores.
            match self.ch.choice("eq_stack.push", ("none", "both", "packet")):
                case "both":
                    for name in (p, q):
                        self.body.append(pb.Stmt(push=pb.Push(stack=L(name), count=1)))
                case "packet":
                    push = pb.Stmt(push=pb.Push(stack=L(p), count=1))
                    self.body.append(if_(self.condition("eq_stack.push"), [push]))
                case _:
                    pass
        op = EQ if self.ch.choice("eq.op", ("eq", "ne")) == "eq" else NE
        self.body.append(assign(f"hdr.o.r{k}", as_byte(binary(op, E(p), E(q)))))

    def eq_enum(self, k: int) -> None:
        c = self.local(f"f{k}c", COLOR)
        first, second = (self.ch.choice("eq_enum.member", COLORS) for _ in range(2))
        self.body.append(
            if_(self.condition("eq_enum"), [assign(c, enum(first))], [assign(c, enum(second))])
        )
        op = EQ if self.ch.choice("eq.op", ("eq", "ne")) == "eq" else NE
        other = self.ch.choice("eq_enum.other", COLORS)
        self.body.append(assign(f"hdr.o.r{k}", as_byte(binary(op, E(c), enum(other)))))

    # -- headers and stacks ------------------------------------------------------

    def header_assign(self, k: int) -> None:
        """A whole header assigned from a local that may be invalid."""
        x = self.local(f"f{k}x", H_T)
        self.body.append(assign(f"{x}.a", self.operand("header_assign.field")))
        match self.ch.choice("header_assign.validity", ("valid", "invalid", "packet")):
            case "valid":
                self.body.append(set_valid(x))
            case "packet":
                self.body.append(if_(self.condition("header_assign"), [set_valid(x)]))
            case _:
                pass
        target = self.ch.choice("header_assign.target", ("hdr.g", "hdr.s[0]"))
        self.body.append(assign(target, E(x)))

    def set_valid(self, k: int) -> None:
        """setValid on a header that the packet, or an earlier statement,
        may already have made valid."""
        target = self.ch.choice("set_valid.target", ("hdr.g", "hdr.s[0]", "hdr.e"))
        match self.ch.choice("set_valid.before", ("none", "set_valid", "set_invalid")):
            case "set_valid":
                self.body.append(if_(self.condition("set_valid"), [set_valid(target)]))
            case "set_invalid":
                self.body.append(if_(self.condition("set_valid"), [set_invalid(target)]))
            case _:
                pass
        self.body.append(set_valid(target))

    def stack_index(self, k: int) -> None:
        """An element of `hdr.s` at an index the packet decides."""
        i = self.local(f"f{k}i", BIT32)
        index = self.ch.choice("stack.index", ("masked", "packet"))
        byte = E("hdr.h.a")
        if index == "masked":
            byte = binary(
                pb.BINARY_OP_BIT_AND, byte, lit(8, (1 << (self.stack - 1).bit_length()) - 1)
            )
            # Keep it in range: a mask of the next power of two, then a select.
            byte = mux(binary(LT, byte, lit(8, self.stack)), byte, lit(8, 0))
        self.body.append(assign(i, cast(BIT32, byte)))
        element = f"hdr.s[{i}]"
        uses = ["write", "set_valid", "assign", "read"]
        if self.profile == "spectec" and index == "packet":
            uses.remove("read")
        match self.ch.choice("stack.use", uses):
            case "write":
                self.body.append(assign(f"{element}.a", self.operand("stack.value")))
            case "set_valid":
                self.body.append(set_valid(element))
            case "assign":
                self.body.append(assign(element, E("hdr.h")))
            case _:
                self.body.append(
                    assign(f"hdr.o.r{k}", binary(pb.BINARY_OP_ADD, E(f"{element}.a"), lit(8, 1)))
                )

    # -- tables ------------------------------------------------------------------

    def table(self, k: int) -> None:
        """A table on `hdr.h.a` whose actions set a result byte, assign the
        lvalue the apply writes `hit` to, or do nothing."""
        ch = self.ch
        name = f"t{k}"
        hit = self.local(f"f{k}r", BOOL)
        kinds = ("exact",) if self.profile == "spectec" else ("exact", "ternary", "lpm")
        kind = ch.choice("table.key", kinds)
        match_kind = {
            "exact": pb.MATCH_KIND_EXACT,
            "ternary": pb.MATCH_KIND_TERNARY,
            "lpm": pb.MATCH_KIND_LPM,
        }[kind]
        set_action = self.block.actions.add(name=f"{name}_set")
        set_action.params.add(name="v", type=BIT8, direction=NONE)
        set_action.body.append(assign(f"hdr.o.r{k}", E("v")))
        hit_action = self.block.actions.add(name=f"{name}_hit")
        hit_action.body.append(assign(hit, boolean(ch.chance("table.hit_value"))))
        if not any(a.name == "NoAction" for a in self.block.actions):
            self.block.actions.add(name="NoAction")
        table = self.block.tables.add(
            name=name,
            keys=[pb.Key(expr=E("hdr.h.a"), match_kind=match_kind, name="hdr.h.a")],
            actions=[set_action.name, hit_action.name, "NoAction"],
            size=16,
        )
        match ch.choice("table.default", ("none", "set", "hit", "const")):
            case "set":
                table.default_action.CopyFrom(
                    pb.ActionCall(action=set_action.name, args=[bits_literal(8, 0x77)])
                )
            case "hit":
                table.default_action.CopyFrom(pb.ActionCall(action=hit_action.name))
            case "const":
                table.default_action.CopyFrom(pb.ActionCall(action="NoAction"))
                table.const_default_action = True
            case _:
                pass
        self.body.append(assign(hit, boolean(False)))
        apply = pb.Apply(table=name)
        if ch.chance("table.hit_lvalue"):
            apply.hit.CopyFrom(L(hit))
        self.body.append(pb.Stmt(apply=apply))
        self.body.append(assign(f"hdr.o.r{(k + 3) % RESULTS}", as_byte(E(hit))))
        self.tables.append(name)

    def entries(self, point: str) -> pb.Entries:
        """Host entries for every table: a few distinct small keys, each
        with an action the chooser picks."""
        entries = pb.Entries()
        for name in self.tables:
            table = next(t for t in self.block.tables if t.name == name)
            te = entries.tables.add(block="C", table=name)
            keys = sorted(
                {self.ch.integer(point, 0, 4) for _ in range(self.ch.integer(point, 0, 3))}
            )
            for priority, key in enumerate(keys):
                label = self.ch.choice("table.action", ("set", "hit", "none"))
                action = {"set": f"{name}_set", "hit": f"{name}_hit", "none": "NoAction"}[label]
                call = pb.ActionCall(action=action)
                if label == "set":
                    call.args.append(bits_literal(8, self.ch.integer(point, 0, 255)))
                entry = te.entries.add(action=call)
                match table.keys[0].match_kind:
                    case pb.MATCH_KIND_TERNARY:
                        entry.keys.add(ternary=pb.TernaryValue(value=str(key), mask="255"))
                        entry.priority = priority
                    case pb.MATCH_KIND_LPM:
                        entry.keys.add(lpm=pb.LpmValue(value=str(key), prefix_len=8))
                    case _:
                        entry.keys.add(exact=str(key))
            if not table.const_default_action and self.ch.chance("table.host_default"):
                te.default_action.CopyFrom(pb.ActionCall(action=f"{name}_hit"))
            if not te.entries and not te.HasField("default_action"):
                entries.tables.pop()
        return entries


def _call_action(name: str, *args: pb.Arg) -> pb.Stmt:
    return pb.Stmt(call_action=pb.CallAction(action=name, args=args))


def control_family(ch: Chooser, profile: Profile = "lean", cases: int = 4) -> Sample:
    """A parser that extracts `hdr.h` and `hdr.g`, a control of one to four
    features, and packets whose two bytes decide the conditions."""
    stack = ch.integer("control.stack", 1, 3)
    program = template("generated-control", stack)
    parser = _block(program, "P")
    parser.states.add(
        name="start",
        body=[extract("hdr.h"), extract("hdr.g")],
        transition=pb.Transition(direct=pb.Target(accept=pb.Accept())),
    )
    control = _Control(ch, program, profile, stack)
    control.body.append(set_valid("hdr.o"))
    control.body.extend(assign(f"hdr.o.r{i}", lit(8, 0)) for i in range(RESULTS))
    for k in range(ch.integer("control.features", 1, 4)):
        control.feature(k)
    control.block.body.extend(control.body)
    requests: list[Case] = []
    for number in range(cases):
        length = ch.choice("packet.length", ("two", "short", "long"))
        size = {"two": 2, "short": ch.integer("packet", 0, 1), "long": ch.integer("packet", 3, 6)}[
            length
        ]
        if profile == "spectec":
            size = max(size, 1)  # STF cannot send an empty packet
        packet = bytes(_byte(ch, "packet") for _ in range(size))
        requests.append(Case(control.entries("entries"), number % 4, packet))
    return Sample("control", program, tuple(requests), frozenset(ch.features))


# ---------------------------------------------------------------------------
# The parser family
# ---------------------------------------------------------------------------


class _Parser:
    """A parser block's states, built for the main parser (`P`) or the
    sub-parser (`SP`), which differ only in what they may call."""

    def __init__(
        self,
        ch: Chooser,
        block: pb.Block,
        where: Literal["parser", "subparser"],
        profile: Profile,
        stack: int,
        states: int,
    ) -> None:
        self.ch = ch
        self.block = block
        self.where = where
        self.profile = profile
        self.stack = stack
        self.names = ["start", *(f"{where[0]}{i}" for i in range(1, states))]
        self.may_call = False
        self.called = False
        for name, type in (("idx", BIT32), ("c", COLOR), ("err", ERROR), ("flag", BOOL)):
            block.locals.add(name=name, type=type)

    def point(self, name: str) -> str:
        return f"{self.where}.{name}"

    def build(self) -> None:
        for i, name in enumerate(self.names):
            body: list[pb.Stmt] = []
            if i == 0 and self.where == "parser":
                body.append(extract("hdr.h"))
                # Most programs with a sub-parser call it where every packet goes.
                if self.may_call and self.ch.chance("parser.call_at_start"):
                    body.extend(self.call())
            for _ in range(self.ch.integer(self.point("stmts"), 0, 3)):
                body.extend(self.stmt())
            self.block.states.add(name=name, body=body, transition=self.transition(i))
        self.block.start_state = "start"

    # -- statements --------------------------------------------------------------

    def byte(self) -> pb.Expr:
        """A byte the packet decides, in the parser: a field, a lookahead, the key argument."""
        options = ["x", "lookahead", "const"]
        if self.where == "subparser":
            options.append("k")
        match self.ch.choice(self.point("byte"), options):
            case "x":
                return E("hdr.h.a")
            case "lookahead":
                return lookahead(BIT8)
            case "k":
                return E("k")
            case _:
                return lit(8, self.ch.integer("byte", 0, 4))

    def condition(self) -> pb.Expr:
        """A condition on a packet byte. Packet bytes are mostly large, so
        half the comparisons are mostly true and half mostly false."""
        options = ("below", "at_least", "flag", "equal", "differs")
        k = lit(8, self.ch.integer("condition", 1, 4))
        match self.ch.choice(self.point("condition"), options):
            case "below":
                return binary(LT, self.byte(), k)
            case "at_least":
                return binary(pb.BINARY_OP_GE, self.byte(), k)
            case "flag":
                return E("flag")
            case "equal":
                return binary(EQ, self.byte(), k)
            case _:
                return binary(NE, self.byte(), k)

    def in_range(self, byte: pb.Expr) -> pb.Expr:
        """A byte mapped into the stack's index range."""
        mask = (1 << (self.stack - 1).bit_length()) - 1
        masked = binary(pb.BINARY_OP_BIT_AND, byte, lit(8, mask))
        return mux(binary(LT, masked, lit(8, self.stack)), masked, lit(8, 0))

    def stmt(self) -> list[pb.Stmt]:
        ch = self.ch
        kinds = [
            "extract_h",
            "extract_g",
            "extract_next",
            "extract_index",
            "extract_empty",
            "advance",
            "lookahead_bits",
            "lookahead_bool",
            "lookahead_header",
            "lookahead_field",
            "lookahead_index",
            "lookahead_logic",
            "last_index",
            "verify",
            "set_enum",
            "set_error",
            "if",
        ]
        if self.may_call and not (self.profile == "spectec" and self.called):
            kinds.append("call_sp")
        kind = ch.choice(self.point("stmt"), kinds)
        r = f"hdr.o.r{ch.integer('result', 1, RESULTS - 1)}"
        match kind:
            case "extract_h" | "extract_g":
                return [extract(f"hdr.{kind[-1]}")]
            case "extract_next":
                return [extract("hdr.s.next")]
            case "extract_index":
                byte = self.byte()
                if ch.choice(self.point("index"), ("masked", "packet")) == "masked":
                    byte = self.in_range(byte)
                return [assign("idx", cast(BIT32, byte)), extract("hdr.s[idx]")]
            case "extract_empty":
                return [extract("hdr.e")]
            case "advance":
                match ch.choice(self.point("advance"), ("const", "field", "lookahead")):
                    case "const":
                        amount = lit(32, 8 * ch.integer("advance", 0, 3))
                    case "field":
                        amount = cast(
                            BIT32, binary(pb.BINARY_OP_BIT_AND, E("hdr.h.a"), lit(8, 0x18))
                        )
                    case _:
                        amount = cast(
                            BIT32, binary(pb.BINARY_OP_BIT_AND, lookahead(BIT8), lit(8, 0x18))
                        )
                return [pb.Stmt(advance=pb.Advance(bits=amount))]
            case "lookahead_bits":
                return [assign(r, lookahead(BIT8))]
            case "lookahead_bool":
                return [assign("flag", lookahead(BOOL)), assign(r, as_byte(E("flag")))]
            case "lookahead_header":
                return [assign("hdr.g", lookahead(H_T))]
            case "lookahead_field":
                match ch.choice(self.point("lookahead_field"), ("member", "slice")):
                    case "member":
                        value = pb.Expr(member=pb.Member(base=lookahead(H_T), field="a"))
                    case _:
                        value = pb.Expr(
                            slice=pb.Slice(operand=lookahead(pb.Type(bits=16)), hi=11, lo=4)
                        )
                return [assign(r, value)]
            case "lookahead_index":
                return self.lookahead_index(r)
            case "lookahead_logic":
                return self.lookahead_logic(r)
            case "last_index":
                last = cast(BIT8, pb.Expr(last_index=pb.LastIndex(stack=E("hdr.s"))))
                if self.profile == "spectec":
                    # lastIndex of an empty stack deviates; read it after an extract.
                    return [extract("hdr.s.next"), assign(r, last)]
                return [assign(r, last)]
            case "verify":
                name = ch.choice("verify.error", ("NoMatch", "NoError", "BadValue"))
                verify = pb.Verify(condition=self.condition(), error=name)
                return [pb.Stmt(verify=verify)]
            case "set_enum":
                first, second = (ch.choice("set_enum.member", COLORS) for _ in range(2))
                return [
                    if_(self.condition(), [assign("c", enum(first))], [assign("c", enum(second))])
                ]
            case "set_error":
                first, second = (ch.choice("set_error.error", ERRORS[:3]) for _ in range(2))
                return [
                    if_(
                        self.condition(),
                        [assign("err", error(first))],
                        [assign("err", error(second))],
                    )
                ]
            case "if":
                then = [assign(r, lit(8, ch.integer("if", 1, 4)))]
                otherwise = (
                    [assign(r, lit(8, ch.integer("if", 5, 9)))]
                    if ch.chance(self.point("else"))
                    else []
                )
                return [if_(self.condition(), then, otherwise)]
            case _:
                return self.call()

    def call(self) -> list[pb.Stmt]:
        """`SP(hdr, k)`, where the key argument may itself read the packet."""
        self.called = True
        call = pb.CallBlock(block="SP", args=[pb.Arg(lvalue=L("hdr")), pb.Arg(expr=self.byte())])
        return [pb.Stmt(call_block=call)]

    def lookahead_logic(self, r: str) -> list[pb.Stmt]:
        """A packet read as the operand of `!`, `~`, `&&` or `||`, so that on a
        short packet the operator itself propagates the fault."""
        read = lookahead(BOOL)
        match self.ch.choice(self.point("lookahead_logic"), ("not", "and", "or", "complement")):
            case "not":
                return [assign("flag", pb.Expr(unary=pb.Unary(op=pb.UNARY_OP_NOT, operand=read)))]
            case "and":
                return [assign("flag", binary(pb.BINARY_OP_AND, read, E("flag")))]
            case "or":
                return [assign("flag", binary(pb.BINARY_OP_OR, read, E("flag")))]
            case _:
                complement = pb.Unary(op=pb.UNARY_OP_COMPLEMENT, operand=lookahead(BIT8))
                return [assign(r, pb.Expr(unary=complement))]

    def lookahead_index(self, r: str) -> list[pb.Stmt]:
        """A stack element at an index read ahead from the packet; on a
        short packet the index itself raises."""
        index = cast(BIT32, self.in_range(lookahead(BIT8)))
        element = pb.Expr(index=pb.Index(base=E("hdr.s"), index=index))
        target = _as_lvalue(element)
        match self.ch.choice(
            self.point("lookahead_index"), ("read", "write", "set_valid", "set_invalid", "is_valid")
        ):
            case "read":
                return [assign(r, pb.Expr(member=pb.Member(base=element, field="a")))]
            case "write":
                return [assign(pb.LValue(member=pb.LMember(base=target, field="a")), lit(8, 9))]
            case "set_valid":
                return [set_valid(target)]
            case "set_invalid":
                return [set_invalid(target)]
            case _:
                return [assign(r, as_byte(is_valid(element)))]

    # -- transitions -----------------------------------------------------------

    def target(self, i: int, point: str) -> pb.Target:
        """accept, reject, or a state: a later one, or in the lean profile
        any one, so that loops, revisits and timeouts happen."""
        options = ["accept", "reject"]
        later = self.names[i + 1 :]
        if later:
            options.append("forward")
        if self.profile == "lean":
            options.append("loop")
        match self.ch.choice(point, options):
            case "accept":
                return pb.Target(accept=pb.Accept())
            case "reject":
                return pb.Target(reject=pb.Reject())
            case "forward":
                return pb.Target(state=later[self.ch.integer(point, 0, len(later) - 1)])
            case _:
                return pb.Target(state=self.names[self.ch.integer(point, 0, i)])

    def transition(self, i: int) -> pb.Transition:
        if self.ch.choice(self.point("transition.kind"), ("direct", "select")) == "direct":
            return pb.Transition(direct=self.target(i, self.point("transition")))
        keys: list[tuple[str, pb.Expr]] = []
        for _ in range(2 if self.ch.choice("select.keys", ("one", "two")) == "two" else 1):
            keys.append(self.key())
        cases: list[pb.SelectCase] = []
        for _ in range(self.ch.integer("select.cases", 1, 3)):
            case = pb.SelectCase(target=self.target(i, self.point("transition")))
            case.sets.extend(self.keyset(kind) for kind, _ in keys)
            cases.append(case)
        if self.ch.choice("select.default", ("yes", "no")) == "yes":
            default = pb.SelectCase(target=self.target(i, self.point("transition")))
            default.sets.extend(pb.KeySet(dont_care=pb.DontCare()) for _ in keys)
            cases.append(default)
        return pb.Transition(select=pb.Select(keys=[k for _, k in keys], cases=cases))

    def key(self) -> tuple[str, pb.Expr]:
        match self.ch.choice("select.key", ("bits", "bool", "enum", "error")):
            case "bits":
                return "bits", self.byte()
            case "bool":
                return "bool", self.condition()
            case "enum":
                return "enum", E("c")
            case _:
                return "error", E("err")

    def keyset(self, kind: str) -> pb.KeySet:
        ch = self.ch
        if kind != "bits":
            if ch.choice("keyset", ("exact", "dont_care")) == "dont_care":
                return pb.KeySet(dont_care=pb.DontCare())
            match kind:
                case "bool":
                    value = pb.Literal(boolean=ch.chance("keyset.bool"))
                case "enum":
                    member = ch.choice("keyset.enum", COLORS)
                    value = pb.Literal(enum_member=pb.EnumLiteral(enum_type="Color", member=member))
                case _:
                    value = pb.Literal(error=ch.choice("keyset.error", ERRORS[:3]))
            return pb.KeySet(exact=value)
        match ch.choice("keyset", ("exact", "masked", "range", "dont_care")):
            case "exact":
                return pb.KeySet(exact=bits_literal(8, ch.integer("keyset", 0, 4)))
            case "masked":
                mask = ch.integer("keyset", 0, 255)
                value = ch.integer("keyset", 0, 255) & mask
                return pb.KeySet(
                    masked=pb.MaskedValue(value=bits_literal(8, value), mask=bits_literal(8, mask))
                )
            case "range":
                lo = ch.integer("keyset", 0, 4)
                hi = lo + ch.integer("keyset", 0, 8)
                return pb.KeySet(
                    range=pb.RangeValue(lo=bits_literal(8, lo), hi=bits_literal(8, hi))
                )
            case _:
                return pb.KeySet(dont_care=pb.DontCare())


def parser_family(ch: Chooser, profile: Profile = "lean", cases: int = 4) -> Sample:
    """A parser of one to four states, maybe with a sub-parser, and a control
    that records the parser's error; packets come from walking the parser
    (`p4blo.drt.generate`), from a seed the chooser draws."""
    stack = ch.integer("parser.stack", 1, 3)
    program = template("generated-parser", stack)
    main = _block(program, "P")
    has_sub = ch.chance("parser.has_subparser")
    if has_sub:
        sub = pb.Block(
            name="SP",
            kind=pb.BLOCK_KIND_PARSER,
            params=[
                pb.Param(name="hdr", type=H, direction=INOUT),
                pb.Param(name="k", type=BIT8, direction=IN),
            ],
        )
        _Parser(ch, sub, "subparser", profile, stack, ch.integer("subparser.states", 1, 3)).build()
        program.blocks.insert(1, sub)
    builder = _Parser(ch, main, "parser", profile, stack, ch.integer("parser.states", 1, 4))
    builder.may_call = has_sub
    builder.build()
    control = _block(program, "C")
    control.body.extend([set_valid("hdr.o"), assign("hdr.o.r0", _local_error())])
    seed = ch.integer("packets", 0, 2**32 - 1)
    requests = generate(ir.Index.build(program), seed, cases)
    # The last packet is cut to its first byte, so that every program meets
    # a packet read past the end somewhere.
    last = requests[-1]
    requests[-1] = Case(last.entries, last.ingress_port, last.packet[:1])
    if profile == "spectec":
        requests = [c if c.packet else Case(c.entries, c.ingress_port, b"\x00") for c in requests]
    return Sample("parser", program, tuple(requests), frozenset(ch.features))


type Family = Callable[[Chooser, Profile], Sample]

FAMILIES: dict[str, Family] = {
    "control": control_family,
    "parser": parser_family,
}


def sample(family: str, seed: int, profile: Profile = "lean") -> Sample:
    """The sample a seed names: the family's decisions from `random.Random(seed)`."""
    return FAMILIES[family](RandomChooser(random.Random(seed)), profile)
