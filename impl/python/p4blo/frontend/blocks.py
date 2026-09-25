"""Blocks: P4-SpecTec's parsers and controls as IR blocks.

`BlockCx` translates one parser or control declaration, as instantiated,
into a `pb.Block`: its parameters, locals, actions, tables, states and
body, performing every statement- and expression-level elaboration of
docs/p4-spec-coverage.md (see `p4blo.frontend.spectec_il` for the list).
It reaches the architecture only through `Architecture`, which
`p4blo.frontend.v1model` implements.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from p4blo import ir
from p4blo.frontend import il
from p4blo.frontend.common import (
    BOOL,
    Access,
    ActionB,
    BadConstB,
    Bits,
    BlockInstB,
    BoundArgB,
    ConstB,
    EnumVal,
    ErrorVal,
    Excluded,
    ExternFunctionB,
    ExternInstB,
    FunctionB,
    Int,
    IntrinsicB,
    NotTranslated,
    ParamIL,
    Scope,
    TableB,
    Val,
    VarB,
    _wrap,
    access,
    assign,
    binary,
    bits_type,
    is_packet_type,
    lit_bits,
    literal_of,
    lmember,
    lvalue_parts,
    lvalue_to_expr,
    lvar,
    may_alias,
    member,
    prefixed_name,
    reads,
    strip_alias,
    typed_parts,
    unary,
    var,
)
from p4blo.frontend.il import Node
from p4blo.v0 import p4blo_pb2 as pb

if TYPE_CHECKING:
    from p4blo.frontend.spectec_il import Translator

# ---------------------------------------------------------------------------
# The architecture hook
# ---------------------------------------------------------------------------


class Architecture:
    """What an architecture binding supplies to block translation.

    `p4blo.frontend.v1model.V1Model` is the one implementation: it maps
    intrinsic metadata onto the metadata contract and the architecture's
    extern functions and objects onto the extern families.
    """

    def metadata_read(self, cx: BlockCx, fieldname: str) -> pb.Expr:
        raise Excluded("standard_metadata and other intrinsic metadata parameters", "by thesis")

    def metadata_write(self, cx: BlockCx, fieldname: str, value: pb.Expr) -> list[pb.Stmt]:
        raise Excluded("standard_metadata and other intrinsic metadata parameters", "by thesis")

    def extern_function(
        self, cx: BlockCx, name: str, targs: list[Node], args: list[Node]
    ) -> list[pb.Stmt]:
        raise Excluded(
            "externFunctionDeclarationIR: an architecture's functions", "by thesis", name
        )

    def extern_object(self, cx: BlockCx, inst_name: str, t: Node, args: list[Node]) -> ExternInstB:
        raise NotTranslated("instantiationIR of an extern object", inst_name)

    def is_intrinsic(self, t: Node) -> bool:
        return False


# ---------------------------------------------------------------------------
# Block translation
# ---------------------------------------------------------------------------

KIND = {
    "parser": pb.BLOCK_KIND_PARSER,
    "control": pb.BLOCK_KIND_CONTROL,
    "deparser": pb.BLOCK_KIND_DEPARSER,
}

BINOPS: dict[str, int] = {
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

COMPOUND = {
    "+=": "+",
    "-=": "-",
    "*=": "*",
    "|+|=": "|+|",
    "|-|=": "|-|",
    "&=": "&",
    "|=": "|",
    "^=": "^",
    "<<=": "<<",
    ">>=": ">>",
    "/=": "/",
    "%=": "%",
    "++=": "++",
}


@dataclass
class Marker:
    """The `action_run` elaboration of one table: the local, each labelled
    action's number, and the value the local starts at before the table is
    applied. It starts at 0, which no label has, unless `NoAction` is a
    label: the IR's `NoAction` has no body to write a marker in, so the
    local starts at `NoAction`'s number and every other action of the table
    writes its own number, or 0."""

    local: str
    numbers: dict[str, int]
    actions: list[str]

    @property
    def initial(self) -> int:
        return self.numbers.get("NoAction", 0)


class BlockCx:
    """The translation of one block."""

    def __init__(self, tr: Translator, decl: Node, name: str, kind: str, scope: Scope) -> None:
        self.tr = tr
        self.decl = decl
        self.kind = kind
        self.block = pb.Block(name=name, kind=KIND[kind])  # type: ignore[arg-type]
        self.scope = scope
        self.taken: set[str] = set()
        self.meta: str | None = None  # the IR name of the M parameter
        self.part = "ingress"  # which v1model control a merged body came from
        self.action: str | None = None
        self.markers: dict[str, Marker] = {}
        self.action_copies: dict[tuple[str, str], str] = {}  # (action, table) -> copy
        # Actions bound in some table and also used unbound.
        self.bound_actions: set[str] = set()
        self.pre: list[pb.Stmt] = []
        # True while translating a parser state, an action or an inlined
        # function: code P4 enters afresh each time, whose declarations
        # without an initializer start at their default on every entry.
        self.reentered = False

    # -- names

    def fresh(self, base: str) -> str:
        taken = self.taken | self.tr.program_names()
        name, i = base, 0
        while name in taken:
            name = f"{base}_{i}"
            i += 1
        self.taken.add(name)
        return name

    def add_local(self, base: str, t: pb.Type) -> str:
        name = self.fresh(base)
        self.block.locals.append(pb.Var(name=name, type=t))
        return name

    def hoist(self, stmts: Iterable[pb.Stmt]) -> None:
        self.pre.extend(stmts)

    def zero(self, target: pb.LValue, t: pb.Type) -> list[pb.Stmt]:
        """Statements that give `target` the IR's zero value of `t`
        (docs/ir-semantics.md, "Uninitialized variables"): zero bits,
        `false`, `NoError`, an enum's first member, a header invalid with
        zero fields, a struct field by field, and a stack emptied by popping
        all of it, which leaves every element invalid with zero fields and
        `nextIndex` at 0."""
        tr = self.tr
        match t.WhichOneof("kind"):
            case "bits":
                return [assign(target, lit_bits(t.bits, 0))]
            case "boolean":
                return [assign(target, pb.Expr(literal=pb.Literal(boolean=False)))]
            case "error":
                return [assign(target, pb.Expr(literal=pb.Literal(error="NoError")))]
            case "enum_type":
                first = tr.enum_types[t.enum_type].members[0]
                lit = pb.EnumLiteral(enum_type=t.enum_type, member=first)
                return [assign(target, pb.Expr(literal=pb.Literal(enum_member=lit)))]
            case "header":
                out = [pb.Stmt(set_invalid=pb.SetInvalid(header=target))]
                for f in tr.header_types[t.header].fields:
                    out.extend(self.zero(lmember(target, f.name), f.type))
                return out
            case "struct":
                out: list[pb.Stmt] = []
                for f in tr.struct_types[t.struct].fields:
                    out.extend(self.zero(lmember(target, f.name), f.type))
                return out
            case "stack":
                return [pb.Stmt(pop=pb.Pop(stack=target, count=t.stack.size))]
            case kind:
                raise il.ILError(f"no zero value for a {kind}")

    def _reentered[T](self, f: Callable[[], T]) -> T:
        saved = self.reentered
        self.reentered = True
        try:
            return f()
        finally:
            self.reentered = saved

    # -- types and values

    def fold(self, te: Node) -> Val | None:
        """The compile-time value of a typed expression, when it has one."""
        e, t, ctk = typed_parts(te)
        if ctk == "DYN":
            return None
        return self._fold(e, t)

    def fold_keyset(self, te: Node) -> Val | None:
        """A keyset element's value. The IL types a keyset as a set, which
        is not compile-time known as a whole; its element is."""
        e, t, _ = typed_parts(te)
        return self._fold(e, t)

    def _fold(self, e: Node, t: Node) -> Val | None:
        tr = self.tr
        match e.c:
            case "TRUE":
                return True
            case "FALSE":
                return False
            case "% W %" | "D %":
                return tr.value(e)
            case "% S %":
                raise Excluded("literalExpressionIR: nat S int (signed)", "by scope")
            case "_BARE %" | ". %":
                name, top = prefixed_name(e)
                b = self.scope.lookup(name, top)
                if isinstance(b, ConstB):
                    return b.value
                if isinstance(b, BadConstB):
                    raise b.error
                return None
            case "ERROR . %":
                return ErrorVal(e.text(0))
            case "(%) %":
                inner = self.fold(e.node(1))
                return None if inner is None else tr.cast_val(inner, e.node(0))
            case "% . %":
                base = e.node(0)
                if base.c == "TYPE %":
                    type_name, _ = prefixed_name(base.node(0))
                    return tr.enum_value(type_name, e.text(1), t)
                _, base_t, _ = typed_parts(base)
                bt = strip_alias(base_t)
                if bt.c == "HEADER_STACK % [%]" and e.text(1) == "size":
                    st = strip_alias(t)
                    return _wrap(st.num(0), bt.num(1)) if st.c == "BIT <%>" else Int(bt.num(1))
                return None
            case "(%)":
                return self.fold(e.node(0))
            case "% %":
                if e.t != "unaryExpressionIR":
                    return None
                v = self.fold(e.node(1))
                return None if v is None else self._unop(e.node(0).c, v)
            case "% % %":
                if e.t != "binaryExpressionIR":
                    return None
                op = e.node(1).c
                left = self.fold(e.node(0))
                if left is None:
                    return None
                if op == "&&" and left is False:
                    return False
                if op == "||" and left is True:
                    return True
                right = self.fold(e.node(2))
                return None if right is None else self._binop(op, left, right)
            case "% ? % : %":
                c = self.fold(e.node(0))
                if not isinstance(c, bool):
                    return None
                return self.fold(e.node(1) if c else e.node(2))
            case "% [% % %]":
                base = self.fold(e.node(0))
                if not isinstance(base, Bits | Int) or e.node(2).c not in (":", "+:"):
                    return None
                a, b = self.fold(e.node(1)), self.fold(e.node(3))
                if not isinstance(a, Bits | Int) or not isinstance(b, Bits | Int):
                    return None
                hi, lo = (
                    (a.value, b.value) if e.node(2).c == ":" else (a.value + b.value - 1, a.value)
                )
                return Bits(hi - lo + 1, (base.value >> lo) & ((1 << (hi - lo + 1)) - 1))
            case _:
                return None

    @staticmethod
    def _unop(op: str, v: Val) -> Val | None:
        match op, v:
            case "!", bool():
                return not v
            case "~", Bits():
                return _wrap(v.width, ~v.value)
            case "-", Bits():
                return _wrap(v.width, -v.value)
            case "-", Int():
                return Int(-v.value)
            case "+", Bits() | Int():
                return v
            case _:
                return None

    @staticmethod
    def _binop(op: str, a: Val, b: Val) -> Val | None:
        if op in ("==", "!="):
            eq = a == b
            return eq if op == "==" else not eq
        if isinstance(a, bool) and isinstance(b, bool):
            return {"&&": a and b, "||": a or b}.get(op)
        if isinstance(a, Int) and isinstance(b, Int):
            x, y = a.value, b.value
            match op:
                case "+":
                    return Int(x + y)
                case "-":
                    return Int(x - y)
                case "*":
                    return Int(x * y)
                case "/" if y:
                    return Int(x // y) if x >= 0 and y > 0 else None
                case "%" if y:
                    return Int(x % y) if x >= 0 and y > 0 else None
                case "<<":
                    return Int(x << y)
                case ">>":
                    return Int(x >> y)
                case "&":
                    return Int(x & y)
                case "|":
                    return Int(x | y)
                case "^":
                    return Int(x ^ y)
                case "<":
                    return x < y
                case "<=":
                    return x <= y
                case ">":
                    return x > y
                case ">=":
                    return x >= y
            return None
        if isinstance(a, Bits) and isinstance(b, Bits | Int):
            w, x, y = a.width, a.value, b.value
            match op:
                case "<<":
                    return _wrap(w, x << y) if y < w else Bits(w, 0)
                case ">>":
                    return Bits(w, x >> y)
            if isinstance(b, Int):
                return None
            if op == "++":
                return Bits(a.width + b.width, (x << b.width) | y)
            if a.width != b.width:
                return None
            match op:
                case "+":
                    return _wrap(w, x + y)
                case "-":
                    return _wrap(w, x - y)
                case "*":
                    return _wrap(w, x * y)
                case "|+|":
                    return Bits(w, min(x + y, (1 << w) - 1))
                case "|-|":
                    return Bits(w, max(x - y, 0))
                case "/" if y:
                    return Bits(w, x // y)
                case "%" if y:
                    return Bits(w, x % y)
                case "&":
                    return Bits(w, x & y)
                case "|":
                    return Bits(w, x | y)
                case "^":
                    return Bits(w, x ^ y)
                case "<":
                    return x < y
                case "<=":
                    return x <= y
                case ">":
                    return x > y
                case ">=":
                    return x >= y
        return None

    def int_of(self, te: Node, what: str) -> int:
        """A compile-time known natural number (a slice bound, a count)."""
        v = self.fold(te)
        if isinstance(v, Int | Bits) and v.value >= 0:
            return v.value
        raise NotTranslated(what, "not a compile-time known number")

    def literal(self, te: Node, t: pb.Type | None = None) -> pb.Literal:
        """A compile-time known expression as a literal, an unsized one at `t`."""
        v = self.fold(te)
        if isinstance(v, Int) and t is not None and t.WhichOneof("kind") == "bits":
            v = _wrap(t.bits, v.value)
        lit = None if v is None else literal_of(v)
        if lit is None:
            raise NotTranslated("literalExpressionIR", f"not a compile-time constant: {te.short()}")
        return lit

    def index(self, te: Node) -> pb.Expr:
        """A stack index; an unsized constant index is a `bit<32>`, the
        width `lastIndex` has."""
        v = self.fold(te)
        if isinstance(v, Int):
            return lit_bits(32, v.value)
        return self.expr(te)

    def width_of(self, t: Node) -> int:
        st = strip_alias(t)
        if st.c == "ENUM % <%> {%}":
            st = strip_alias(st.node(1))
        if st.c != "BIT <%>":
            raise NotTranslated("fixedBitTypeIR", f"expected bits, got {st.short()}")
        return st.num(0)

    # -- expressions

    def expr(self, te: Node) -> pb.Expr:
        """An expression. Only what the IR cannot hold is folded: named
        constants, arbitrary-precision `int` arithmetic and the casts that
        size it, `/` and `%`, enum members and `hs.size`. Everything else
        keeps its shape, `~8w1` staying a complement."""
        e, t, ctk = typed_parts(te)
        st = strip_alias(t)
        if (
            ctk != "DYN"
            and self._must_fold(e)
            and st.c
            in (
                "BIT <%>",
                "BOOL",
                "ERROR",
                "ENUM % {%}",
                "ENUM % <%> {%}",
            )
        ):
            v = self.fold(te)
            if v is not None:
                if isinstance(v, EnumVal) and st.c == "ENUM % {%}":
                    self.tr.type_of(st)
                lit = literal_of(v)
                if lit is not None:
                    return pb.Expr(literal=lit)
        return self._expr(e, t)

    def _must_fold(self, e: Node) -> bool:
        match e.c:
            case "_BARE %" | ". %":
                name, top = prefixed_name(e)
                return isinstance(self.scope.lookup(name, top), ConstB | BadConstB)
            case "(%)":
                return self._must_fold(typed_parts(e.node(0))[0])
            case "% . %":
                base = e.node(0)
                if base.c == "TYPE %":
                    return True
                _, bt, _ = typed_parts(base)
                return strip_alias(bt).c == "HEADER_STACK % [%]" and e.text(1) == "size"
            case "% % %" if e.t == "binaryExpressionIR":
                if e.node(1).c in ("/", "%"):
                    return True
                return self._is_int(e.node(0)) or self._is_int(e.node(2))
            case "% %" if e.t == "unaryExpressionIR":
                return self._is_int(e.node(1))
            case "(%) %" | "% ? % : %":
                return any(self._is_int(x) for x in e.a if isinstance(x, Node) and x.c == "% # %")
            case _:
                return False

    @staticmethod
    def _is_int(te: Node) -> bool:
        return strip_alias(typed_parts(te)[1]).c == "INT"

    def _expr(self, e: Node, t: Node) -> pb.Expr:
        match e.c:
            case "_BARE %" | ". %":
                name, top = prefixed_name(e)
                b = self.scope.lookup(name, top)
                if isinstance(b, VarB):
                    return var(b.name)
                if isinstance(b, BoundArgB):
                    return self._in_scope(b.scope, lambda: self.expr(b.te))
                if isinstance(b, ConstB):
                    lit = literal_of(b.value)
                    if lit is not None:
                        return pb.Expr(literal=lit)
                if isinstance(b, IntrinsicB):
                    raise Excluded(
                        "standard_metadata and other intrinsic metadata parameters",
                        "by thesis",
                        f"{name} used as a value",
                    )
                raise NotTranslated("referenceExpressionIR", f"{name} is not a variable here")
            case "TRUE" | "FALSE" | "% W %":
                v = self.tr.value(e)
                assert v is not None
                lit = literal_of(v)
                assert lit is not None
                return pb.Expr(literal=lit)
            case "D %":
                raise NotTranslated("intTypeIR (INT)", f"the unsized {e.num(0)} has no width here")
            case "% S %":
                raise Excluded("literalExpressionIR: nat S int (signed)", "by scope")
            case '" % "':
                raise Excluded("literalExpressionIR: stringLiteral", "by scope")
            case "...":
                raise Excluded("defaultExpressionIR (...)", "by elaboration")
            case "(%)":
                return self.expr(e.node(0))
            case "ERROR . %":
                return pb.Expr(literal=pb.Literal(error=e.text(0)))
            case "(%) %":
                to = strip_alias(e.node(0))
                if to.c in ("HEADER % <%> {%}", "STRUCT % <%> {%}") and _aggregate_source(
                    e.node(1)
                ):
                    return self._aggregate(to, e.node(1))
                return self._cast(e.node(0), e.node(1))
            case "% ? % : %":
                cond = self.expr(e.node(0))
                then, then_pre = self.captured(e.node(1))
                other, other_pre = self.captured(e.node(2))
                if not then_pre and not other_pre:
                    return pb.Expr(mux=pb.Mux(condition=cond, then=then, otherwise=other))
                # A branch with a call: only the chosen branch runs.
                result = self.add_local("mux", self.tr.type_of(t))
                self.pre.append(
                    pb.Stmt(
                        conditional=pb.If(
                            condition=cond,
                            then=[*then_pre, assign(lvar(result), then)],
                            otherwise=[*other_pre, assign(lvar(result), other)],
                        )
                    )
                )
                return var(result)
            case "% %" if e.t == "unaryExpressionIR":
                op = e.node(0).c
                operand = self.expr(e.node(1))
                match op:
                    case "!":
                        return unary(pb.UNARY_OP_NOT, operand)
                    case "~":
                        return unary(pb.UNARY_OP_COMPLEMENT, operand)
                    case "-":
                        return unary(pb.UNARY_OP_NEGATE, operand)
                    case "+":
                        return operand
                raise NotTranslated("unaryExpressionIR", op)
            case "% % %" if e.t == "binaryExpressionIR":
                return self._binary(e)
            case "% . %":
                return self._member(e, t)
            case "% [%]":
                return pb.Expr(
                    index=pb.Index(base=self.expr(e.node(0)), index=self.index(e.node(1)))
                )
            case "% [% % %]":
                return self._slice(e)
            case "% <%> (%)":
                return self._call_expr(e, t)
            case "SEQ {%}" | "SEQ {% , ...}":
                raise Excluded(
                    "sequenceExpressionIR, recordExpressionIR elsewhere", "by elaboration"
                )
            case "RECORD {%}" | "RECORD {% , ...}":
                raise Excluded(
                    "sequenceExpressionIR, recordExpressionIR elsewhere", "by elaboration"
                )
            case "{#}":
                raise Excluded("invalidHeaderExpressionIR ({#})", "by elaboration")
            case _:
                raise NotTranslated(e.t, e.short())

    def _aggregate(self, to: Node, te: Node) -> pb.Expr:
        """A list or record initializer of a header or struct (p4c
        `StructInitializers`): a fresh local, made valid when a header, and
        assigned field by field in order."""
        t = self.tr.type_of(to)
        local = self.add_local("initializer", t)
        stmts: list[pb.Stmt] = []
        self._initialize(lvar(local), to, te, stmts)
        self.hoist(stmts)
        return var(local)

    def _initialize(self, target: pb.LValue, to: Node, te: Node, out: list[pb.Stmt]) -> None:
        e = _aggregate_source(te)
        assert e is not None
        fields = [(f.text(2), f.node(1)) for f in to.nodes(2)]
        if e.c in ("SEQ {%}",):
            values = e.nodes(0)
            if len(values) != len(fields):
                raise il.ILError("initializer arity")
            pairs = list(zip(fields, values, strict=True))
        elif e.c in ("RECORD {%}",):
            by_name = {n.text(0): n.node(1) for n in e.nodes(0)}
            pairs = [((name, ft), by_name[name]) for name, ft in fields]
        else:
            raise Excluded(
                "sequenceExpressionIR, recordExpressionIR elsewhere", "by elaboration", e.c
            )
        if to.c == "HEADER % <%> {%}":
            out.append(pb.Stmt(set_valid=pb.SetValid(header=target)))
        for (name, ft), value in pairs:
            field_target = lmember(target, self.tr.field_name(to, name))
            fts = strip_alias(ft)
            if fts.c in ("HEADER % <%> {%}", "STRUCT % <%> {%}") and _aggregate_source(value):
                self._initialize(field_target, fts, value, out)
            elif self._is_int(value):
                # An unsized element takes its field's width.
                lit = self.literal(value, self.tr.type_of(ft))
                out.append(assign(field_target, pb.Expr(literal=lit)))
            else:
                v, pre = self.captured(value)
                out.extend(pre)
                out.append(assign(field_target, v))

    def _cast(self, target: Node, te: Node) -> pb.Expr:
        _, source_t, _ = typed_parts(te)
        to = strip_alias(target)
        if to.c == "SET <%>":
            raise NotTranslated("setTypeIR", "a keyset outside a select or an entry")
        if to.c in ("TUPLE <%>", "LIST <%>"):
            raise Excluded("listTypeIR, tupleTypeIR", "by elaboration")
        to_ir = self.tr.type_of(to)
        from_ir = self.tr.type_of(source_t)
        operand = self.expr(te)
        if to_ir == from_ir:
            return operand
        kinds = (from_ir.WhichOneof("kind"), to_ir.WhichOneof("kind"))
        ok = kinds == ("bits", "bits") or (
            kinds in (("boolean", "bits"), ("bits", "boolean"))
            and (from_ir.bits == 1 if kinds[0] == "bits" else to_ir.bits == 1)
        )
        if not ok:
            raise NotTranslated("castExpressionIR", f"a cast from {kinds[0]} to {kinds[1]}")
        return pb.Expr(cast=pb.Cast(to=to_ir, operand=operand))

    def _binary(self, e: Node) -> pb.Expr:
        op = e.node(1).c
        if op in ("/", "%"):
            raise NotTranslated(
                "binaryExpressionIR with /, %", "division of a value not known at compile time"
            )
        if op not in BINOPS:
            raise NotTranslated("binaryExpressionIR", f"operator {op}")
        left = self.expr(e.node(0))
        if op in ("&&", "||"):
            right, right_pre = self.captured(e.node(2))
            if not right_pre:
                return binary(BINOPS[op], left, right)
            # The right operand has a call, which runs only when the left
            # one does not decide.
            result = self.add_local("cond", BOOL)
            self.pre.append(assign(lvar(result), left))
            guard = var(result) if op == "&&" else unary(pb.UNARY_OP_NOT, var(result))
            self.pre.append(
                pb.Stmt(
                    conditional=pb.If(
                        condition=guard, then=[*right_pre, assign(lvar(result), right)]
                    )
                )
            )
            return var(result)
        if op in ("<<", ">>"):
            right_te = e.node(2)
            v = self.fold(right_te)
            if isinstance(v, Int):
                _, lt, _ = typed_parts(e.node(0))
                w = self.width_of(lt)
                width = w if v.value < (1 << w) else max(1, v.value.bit_length())
                right = lit_bits(width, v.value)
            else:
                right, right_pre = self.captured(right_te)
                left = self.snapshot(left, right_pre, e.node(0))
                self.pre.extend(right_pre)
            return binary(BINOPS[op], left, right)
        right, right_pre = self.captured(e.node(2))
        left = self.snapshot(left, right_pre, e.node(0))
        self.pre.extend(right_pre)
        return binary(BINOPS[op], left, right)

    def captured(self, te: Node) -> tuple[pb.Expr, list[pb.Stmt]]:
        """An expression and the statements its calls were hoisted into,
        kept apart from the ones already pending."""
        saved = self.pre
        self.pre = []
        try:
            e = self.expr(te)
            return e, self.pre
        finally:
            self.pre = saved

    def snapshot(self, e: pb.Expr, later: list[pb.Stmt], te: Node) -> pb.Expr:
        """`e`, read before the statements `later` hoisted out of an operand
        to its right: P4 evaluates operands left to right."""
        if not later or e.WhichOneof("kind") == "literal":
            return e
        local = self.add_local("tmp", self.tr.type_of(typed_parts(te)[1]))
        self.pre.append(assign(lvar(local), e))
        return var(local)

    def _member(self, e: Node, t: Node) -> pb.Expr:
        base = e.node(0)
        name = e.text(1)
        if base.c == "TYPE %":
            v = self._fold(e, t)
            lit = None if v is None else literal_of(v)
            if lit is None:
                raise NotTranslated("memberAccessExpressionIR", f"type member {name}")
            return pb.Expr(literal=lit)
        base_e, base_t, _ = typed_parts(base)
        bt = strip_alias(base_t)
        if base_e.c == "_BARE %" and isinstance(self.scope.lookup(base_e.text(0)), IntrinsicB):
            assert self.tr.arch is not None
            return self.tr.arch.metadata_read(self, name)
        if bt.c == "HEADER_STACK % [%]":
            stack = self.expr(base)
            match name:
                case "last":
                    return pb.Expr(
                        index=pb.Index(
                            base=stack, index=pb.Expr(last_index=pb.LastIndex(stack=stack))
                        )
                    )
                case "lastIndex":
                    return pb.Expr(last_index=pb.LastIndex(stack=stack))
                case "next":
                    raise NotTranslated("memberAccessExpressionIR: hs.next", "read as a value")
                case "size":
                    raise il.ILError("hs.size should have folded")
        if bt.c == "TABLE_STRUCT % {HIT % ; MISS % ; ACTION_RUN % ;}":
            return self._table_result(base_e, name)
        if bt.c in ("HEADER % <%> {%}", "STRUCT % <%> {%}"):
            return member(self.expr(base), self.tr.field_name(bt, name))
        raise NotTranslated("memberAccessExpressionIR", f".{name} of {bt.short()}")

    def _table_result(self, call: Node, name: str) -> pb.Expr:
        table = self._applied_table(call)
        if name == "action_run":
            raise NotTranslated(
                "memberAccessExpressionIR: t.apply().action_run", "outside a switch statement"
            )
        hit = self.add_local(f"{table}_hit", BOOL)
        self.hoist([pb.Stmt(apply=pb.Apply(table=table, hit=lvar(hit)))])
        if name == "hit":
            return var(hit)
        if name == "miss":
            return unary(pb.UNARY_OP_NOT, var(hit))
        raise NotTranslated("tableMetadataStructTypeIR", name)

    def _applied_table(self, call: Node) -> str:
        """The table of `t.apply()`."""
        if call.c != "% <%> (%)":
            raise NotTranslated("callExpressionIR", "a table result not of t.apply()")
        target = call.node(0)
        if target.c != "% . %" or target.text(1) != "apply":
            raise NotTranslated("callExpressionIR", call.short())
        base_e, _, _ = typed_parts(target.node(0))
        name, top = prefixed_name(base_e)
        b = self.scope.lookup(name, top)
        if not isinstance(b, TableB):
            raise NotTranslated("callExpressionIR", f"{name}.apply() is not a table's")
        if self.action is not None:
            raise il.ILError("apply inside an action")
        return b.name

    def _slice(self, e: Node) -> pb.Expr:
        operand = self.expr(e.node(0))
        hi_te, op, lo_te = e.node(1), e.node(2).c, e.node(3)
        if op == ":":
            hi = self.int_of(hi_te, "sliceAccessExpressionIR")
            lo = self.int_of(lo_te, "sliceAccessExpressionIR")
        elif op == "+:":
            lo = self.int_of(hi_te, "sliceAccessExpressionIR with +:")
            hi = lo + self.int_of(lo_te, "sliceAccessExpressionIR with +:") - 1
        else:
            raise NotTranslated("sliceAccessExpressionIR", op)
        return pb.Expr(slice=pb.Slice(operand=operand, hi=hi, lo=lo))

    def _call_expr(self, e: Node, t: Node) -> pb.Expr:
        target = e.node(0)
        targs = e.nodes(1)
        args = e.nodes(2)
        if target.c == "% . %":
            base = target.node(0)
            method = target.text(1)
            base_e, base_t, _ = typed_parts(base)
            bt = strip_alias(base_t)
            if bt.c == "HEADER % <%> {%}" and method == "isValid":
                return pb.Expr(is_valid=pb.IsValid(header=self.expr(base)))
            if is_packet_type(bt) == "packet_in" and method == "lookahead":
                if self.kind != "parser":
                    raise il.ILError("lookahead outside a parser")
                return pb.Expr(lookahead=pb.Lookahead(type=self.tr.type_of(targs[0])))
            if is_packet_type(bt) == "packet_in" and method == "length":
                raise Excluded("callExpressionIR: packet.length()", "by scope")
            if method in ("minSizeInBits", "minSizeInBytes", "maxSizeInBits", "maxSizeInBytes"):
                raise NotTranslated("callExpressionIR: size methods", "not folded by the typed IL")
            if bt.c == "EXTERN % <%> %":
                result_t = self.tr.type_of(t)
                result = self.add_local(f"{method}_result", result_t)
                self.hoist(self._extern_method(base_e, bt, method, args, lvar(result)))
                return var(result)
        if target.c in ("_BARE %", ". %"):
            name, top = prefixed_name(target)
            b = self.scope.lookup(name, top)
            if isinstance(b, FunctionB):
                result_t = self.tr.type_of(t)
                result = self.add_local(f"{name}_result", result_t)
                self.hoist(self._inline(b.decl, targs, args, lvar(result)))
                return var(result)
            if isinstance(b, ExternFunctionB):
                raise Excluded(
                    "externFunctionDeclarationIR: an architecture's functions",
                    "by thesis",
                    f"{name} in expression position",
                )
        if target.c == "TYPE % . %":
            raise Excluded(
                "callableTargetIR: TYPE name . method (static extern method)", "by scope"
            )
        raise NotTranslated("callExpressionIR", e.short())

    # -- lvalues

    def lvalue(self, tl: Node) -> pb.LValue:
        lv, t = lvalue_parts(tl)
        match lv.c:
            case "_BARE %" | ". %":
                name, top = prefixed_name(lv)
                b = self.scope.lookup(name, top)
                if isinstance(b, VarB):
                    return lvar(b.name)
                if isinstance(b, BoundArgB):
                    return self._in_scope(b.scope, lambda: self.lvalue_of_expr(b.te))
                raise NotTranslated("lvalueIR: referenceExpressionIR", f"{name} is not a variable")
            case "% . %":
                base = lv.node(0)
                name = lv.text(1)
                base_lv, base_t = lvalue_parts(base)
                bt = strip_alias(base_t)
                if base_lv.c == "_BARE %" and isinstance(
                    self.scope.lookup(base_lv.text(0)), IntrinsicB
                ):
                    raise _IntrinsicWrite(name)
                if bt.c == "HEADER_STACK % [%]":
                    stack = self.lvalue(base)
                    match name:
                        case "next":
                            if self.kind != "parser":
                                raise il.ILError("hs.next outside a parser")
                            return pb.LValue(next=pb.Next(stack=stack))
                        case "last":
                            index = pb.Expr(last_index=pb.LastIndex(stack=lvalue_to_expr(stack)))
                            return pb.LValue(index=pb.LIndex(base=stack, index=index))
                return lmember(self.lvalue(base), self.tr.field_name(bt, name))
            case "% [%]":
                return pb.LValue(
                    index=pb.LIndex(base=self.lvalue(lv.node(0)), index=self.index(lv.node(1)))
                )
            case "(%)":
                return self.lvalue(lv.node(0))
            case "% [% % %]":
                raise NotTranslated("lvalueIR: slice", "a slice nested inside an lvalue")
            case _:
                raise NotTranslated(lv.t, lv.short())

    def lvalue_of_expr(self, te: Node) -> pb.LValue:
        """An `out` or `inout` argument, or the target of a method, which the
        IL types as an expression: an access path, `hs.next` or `hs.last`."""
        e, t, _ = typed_parts(te)
        match e.c:
            case "_BARE %" | ". %":
                name, top = prefixed_name(e)
                b = self.scope.lookup(name, top)
                if isinstance(b, VarB):
                    return lvar(b.name)
                if isinstance(b, BoundArgB):
                    return self._in_scope(b.scope, lambda: self.lvalue_of_expr(b.te))
                if isinstance(b, IntrinsicB):
                    raise Excluded(
                        "standard_metadata and other intrinsic metadata parameters",
                        "by thesis",
                        f"{name} passed as an argument",
                    )
            case "(%)":
                return self.lvalue_of_expr(e.node(0))
            case "% . %" if e.node(0).c == "% # %":
                base = e.node(0)
                base_e, base_t, _ = typed_parts(base)
                bt = strip_alias(base_t)
                name = e.text(1)
                if base_e.c == "_BARE %" and isinstance(
                    self.scope.lookup(base_e.text(0)), IntrinsicB
                ):
                    raise Excluded(
                        "standard_metadata and other intrinsic metadata parameters",
                        "by thesis",
                        f"standard_metadata.{name} as an out argument",
                    )
                if bt.c == "HEADER_STACK % [%]":
                    stack = self.lvalue_of_expr(base)
                    if name == "next":
                        if self.kind != "parser":
                            raise il.ILError("hs.next outside a parser")
                        return pb.LValue(next=pb.Next(stack=stack))
                    if name == "last":
                        index = pb.Expr(last_index=pb.LastIndex(stack=lvalue_to_expr(stack)))
                        return pb.LValue(index=pb.LIndex(base=stack, index=index))
                if bt.c in ("HEADER % <%> {%}", "STRUCT % <%> {%}"):
                    return lmember(self.lvalue_of_expr(base), self.tr.field_name(bt, name))
            case "% [%]":
                return pb.LValue(
                    index=pb.LIndex(
                        base=self.lvalue_of_expr(e.node(0)), index=self.index(e.node(1))
                    )
                )
        del t
        raise NotTranslated("argumentIR", f"not an lvalue: {te.short()}")

    def _in_scope[T](self, scope: Scope, f: Callable[[], T]) -> T:
        saved = self.scope
        self.scope = scope
        try:
            return f()
        finally:
            self.scope = saved

    def _expr_lvalue(self, te: Node) -> pb.LValue:
        return self.lvalue_of_expr(te)

    # -- arguments

    def ordered_args(self, params: Sequence[ParamIL], args: Sequence[Node]) -> list[Node | None]:
        """Arguments in parameter order; None where `_` or a default stands.
        Named arguments are put in order (p4c `OrderArguments`)."""
        out: list[Node | None] = [None] * len(params)
        positional = True
        for i, a in enumerate(args):
            match a.c:
                case "% # %":
                    if not positional:
                        raise il.ILError("positional argument after a named one")
                    out[i] = a
                case "_":
                    out[i] = None
                case "% = %":
                    positional = False
                    out[self._param_index(params, a.text(0))] = a.node(1)
                case "% = _":
                    positional = False
                    out[self._param_index(params, a.text(0))] = None
                case _:
                    raise NotTranslated("argumentIR", a.short())
        return out

    @staticmethod
    def _param_index(params: Sequence[ParamIL], name: str) -> int:
        for i, p in enumerate(params):
            if p.name == name:
                return i
        raise il.ILError(f"no parameter {name}")

    def call_args(
        self, params: Sequence[ParamIL], args: Sequence[Node], param_types: Sequence[pb.Type]
    ) -> tuple[list[pb.Arg], list[pb.Stmt]]:
        """Arguments of a call, and the statements to run after it.

        P4 copies arguments in, runs the callee, and copies `out` and `inout`
        arguments back left to right. The IR does the same but refuses two
        `out` arguments that may alias, and has no slice lvalue; both go
        through a fresh local, copied in before the call when `inout` and
        back after it, in order. An `in` argument that overlaps an `out`
        one is copied into a local first, which is what copy-in means and
        what p4c's side-effect ordering does."""
        ordered = self.ordered_args(params, args)
        out: list[pb.Arg] = []
        post: list[pb.Stmt] = []
        writes: list[Access] = []
        for p, a, pt in zip(params, ordered, param_types, strict=True):
            if p.direction not in (pb.DIRECTION_OUT, pb.DIRECTION_INOUT):
                if a is None:
                    raise NotTranslated("argumentIR: _", f"for the in parameter {p.name}")
                ex, pre = self.captured(a)
                if pre:
                    # Arguments are evaluated left to right; a call hoisted
                    # out of this one runs after the earlier ones are read.
                    for j, (earlier, et) in enumerate(zip(out, param_types, strict=False)):
                        if (
                            earlier.WhichOneof("kind") == "expr"
                            and earlier.expr.WhichOneof("kind") != "literal"
                        ):
                            tmp = self.add_local("tmp", et)
                            self.pre.append(assign(lvar(tmp), earlier.expr))
                            out[j] = pb.Arg(expr=var(tmp))
                    self.pre.extend(pre)
                out.append(pb.Arg(expr=ex))
                continue
            if a is None:
                out.append(pb.Arg(lvalue=lvar(self.add_local(f"{p.name}_unused", pt))))
                continue
            e, _, _ = typed_parts(a)
            if e.c == "% [% % %]":
                target, hi, lo, n = self._slice_target(e.node(0), e.node(1), e.node(2).c, e.node(3))
                tmp = self.add_local(p.name, pt)
                if p.direction == pb.DIRECTION_INOUT:
                    field_e = lvalue_to_expr(target)
                    self.pre.append(
                        assign(lvar(tmp), pb.Expr(slice=pb.Slice(operand=field_e, hi=hi, lo=lo)))
                    )
                post.append(self._rmw(target, n, hi, lo, var(tmp)))
                out.append(pb.Arg(lvalue=lvar(tmp)))
                continue
            lv = self.lvalue_of_expr(a)
            path = access(lv)
            if path is not None and any(may_alias(path, w) for w in writes):
                tmp = self.add_local(p.name, pt)
                if p.direction == pb.DIRECTION_INOUT:
                    self.pre.append(assign(lvar(tmp), lvalue_to_expr(lv)))
                post.append(assign(lv, var(tmp)))
                out.append(pb.Arg(lvalue=lvar(tmp)))
                continue
            if path is not None:
                writes.append(path)
            out.append(pb.Arg(lvalue=lv))
        for i, (p, arg, pt) in enumerate(zip(params, out, param_types, strict=True)):
            if arg.WhichOneof("kind") != "expr":
                continue
            if not any(may_alias(r, w) for r in reads(arg.expr) for w in writes):
                continue
            # Named after what it copies, `hdr.h1.op1` giving `op1`.
            dotted = ir.dotted_path(arg.expr)
            local = self.add_local(dotted.rsplit(".", 1)[-1] if dotted else p.name, pt)
            self.pre.append(assign(lvar(local), arg.expr))
            out[i] = pb.Arg(expr=var(local))
        return out, post

    # -- statements

    def stmts(self, items: Iterable[Node]) -> list[pb.Stmt]:
        out: list[pb.Stmt] = []
        for s in items:
            out.extend(self.stmt(s))
        return out

    def stmt(self, s: Node) -> list[pb.Stmt]:
        saved = self.pre
        self.pre = []
        try:
            body = self._stmt(s)
            return self.pre + body
        finally:
            self.pre = saved

    def _stmt(self, s: Node) -> list[pb.Stmt]:
        match s.c:
            case ";" | "/* empty */":
                return []
            case "% CONST % % % ;":
                self.scope.bind(s.text(2), ConstB(self.tr.const_value(s.node(1), s.node(3))))
                return []
            case "% % % % ;" if s.t == "variableDeclarationIR":
                return self._var_decl(s)
            case "% % % ;" if s.t == "assignmentStatementIR":
                return self._assignment(s)
            case "% <%> (%) ;":
                return self._call_stmt(s)
            case "% . APPLY (%) ;":
                return self._direct_apply(s)
            case "% {%}":
                inner = self.scope
                self.scope = inner.child()
                try:
                    return self.stmts(s.nodes(1))
                finally:
                    self.scope = inner
            case "IF (%) %" | "IF (%) % ELSE %":
                cond = self.expr(s.node(0))
                then = self._branch(s.node(1))
                other = self._branch(s.node(2)) if len(s.a) > 2 else []
                return [pb.Stmt(conditional=pb.If(condition=cond, then=then, otherwise=other))]
            case "SWITCH (%) {%}":
                return self._switch(s)
            case "RETURN ;" | "RETURN % ;":
                raise Excluded("returnStatementIR", "by scope")
            case "EXIT ;" | "exit ;":
                raise Excluded("exitStatementIR", "by scope")
            case "BREAK ;" | "CONTINUE ;":
                raise Excluded("breakStatementIR, continueStatementIR", "by scope")
            case _:
                if s.t in ("exitStatementIR", "exitStatement"):
                    raise Excluded("exitStatementIR", "by scope")
                if s.t in ("forStatementIR",):
                    raise Excluded(
                        "forStatementIR (all three forms), forInitStatementIR, "
                        "forUpdateStatementIR, forCollectionExpressionIR",
                        "by scope",
                    )
                if s.t in (
                    "breakStatementIR",
                    "continueStatementIR",
                    "breakStatement",
                    "continueStatement",
                ):
                    raise Excluded("breakStatementIR, continueStatementIR", "by scope")
                if s.t in ("emptyStatementIR", "emptyStatement"):
                    return []
                raise NotTranslated(s.t, s.short())

    def _branch(self, s: Node) -> list[pb.Stmt]:
        inner = self.scope
        self.scope = inner.child()
        try:
            return self.stmt(s)
        finally:
            self.scope = inner

    def _var_decl(self, s: Node) -> list[pb.Stmt]:
        """A declaration inside a body, hoisted to a block local. Without
        an initializer it is re-zeroed where it stood when the body is
        entered afresh each time (a state, an action, an inlined function):
        P4 gives it its default on every entry, while a block local keeps
        its value (docs/ir-semantics.md, "State-local variables")."""
        name = s.text(2)
        t = self.tr.type_of(s.node(1), name)
        local = self.add_local(name, t)
        self.scope.bind(name, VarB(local))
        init = s.opt(3)
        if init is None:
            return self.zero(lvar(local), t) if self.reentered else []
        assert isinstance(init, Node)
        return [assign(lvar(local), self.expr(init.node(0)))]

    def _assignment(self, s: Node) -> list[pb.Stmt]:
        target, op_node, value = s.node(0), s.node(1), s.node(2)
        op = op_node.c
        lv_node, lt = lvalue_parts(target)
        if lv_node.c == "% [% % %]":
            return self._slice_assign(lv_node, lt, op, value)
        try:
            lv = self.lvalue(target)
        except _IntrinsicWrite as w:
            if op != "=":
                raise NotTranslated(
                    "assignmentStatementIR", "compound assignment to metadata"
                ) from w
            assert self.tr.arch is not None
            return self.tr.arch.metadata_write(self, w.fieldname, self.expr(value))
        if op == "=":
            direct = self._hit_into(value, lv)
            if direct is not None:
                return direct
        rhs = self.expr(value)
        if op != "=":
            rhs = self._compound(op, lvalue_to_expr(lv), rhs, value, lt)
        return [assign(lv, rhs)]

    def _hit_into(self, value: Node, lv: pb.LValue) -> list[pb.Stmt] | None:
        """`x = t.apply().hit` is `Apply.hit` into `x`, with no temporary."""
        e, _, _ = typed_parts(value)
        if e.c != "% . %" or e.text(1) not in ("hit", "miss") or e.node(0).c != "% # %":
            return None
        call, bt, _ = typed_parts(e.node(0))
        if not strip_alias(bt).c.startswith("TABLE_STRUCT"):
            return None
        table = self._applied_table(call)
        out = [pb.Stmt(apply=pb.Apply(table=table, hit=lv))]
        if e.text(1) == "miss":
            out.append(assign(lv, unary(pb.UNARY_OP_NOT, lvalue_to_expr(lv))))
        return out

    def _compound(self, op: str, current: pb.Expr, rhs: pb.Expr, value: Node, lt: Node) -> pb.Expr:
        base = COMPOUND.get(op)
        if base is None or base in ("/", "%"):
            raise NotTranslated("assignmentStatementIR", f"compound {op}")
        if base in ("<<", ">>"):
            v = self.fold(value)
            if isinstance(v, Int):
                rhs = lit_bits(self.width_of(lt), v.value)
        return binary(BINOPS[base], current, rhs)

    def _slice_target(
        self, base: Node, hi_te: Node, sliceop: str, lo_te: Node
    ) -> tuple[pb.LValue, int, int, int]:
        """The field, bounds and field width of a slice used as an lvalue;
        `base` is a typed lvalue or a typed expression."""
        what = "lvalueIR: typedLvalueIR [ e sliceop e ]"
        if sliceop == ":":
            hi, lo = self.int_of(hi_te, what), self.int_of(lo_te, what)
        elif sliceop == "+:":
            lo = self.int_of(hi_te, what)
            hi = lo + self.int_of(lo_te, what) - 1
        else:
            raise NotTranslated(what, sliceop)
        if base.c == "% # %" and base.node(1).c == "(%)":
            _, base_t = lvalue_parts(base)
            target = self.lvalue(base)
        else:
            _, base_t, _ = typed_parts(base)
            target = self.lvalue_of_expr(base)
        return target, hi, lo, self.width_of(base_t)

    @staticmethod
    def _rmw(target: pb.LValue, n: int, hi: int, lo: int, value: pb.Expr) -> pb.Stmt:
        """`f[hi:lo] = v` as `f = (f & ~mask) | ((bit<N>) v << lo)`, every
        literal at the field's width (the stacks README's formula)."""
        w = hi - lo + 1
        field_e = lvalue_to_expr(target)
        mask = ((1 << w) - 1) << lo
        if value.WhichOneof("kind") == "literal" and value.literal.WhichOneof("value") == "bits":
            widened = lit_bits(n, int(value.literal.bits.value))
        elif w == n:
            widened = value
        else:
            widened = pb.Expr(cast=pb.Cast(to=bits_type(n), operand=value))
        cleared = binary(
            pb.BINARY_OP_BIT_AND, field_e, unary(pb.UNARY_OP_COMPLEMENT, lit_bits(n, mask))
        )
        shifted = binary(pb.BINARY_OP_SHL, widened, lit_bits(n, lo))
        return assign(target, binary(pb.BINARY_OP_BIT_OR, cleared, shifted))

    def _slice_assign(self, lv_node: Node, lt: Node, op: str, value: Node) -> list[pb.Stmt]:
        target, hi, lo, n = self._slice_target(
            lv_node.node(0), lv_node.node(1), lv_node.node(2).c, lv_node.node(3)
        )
        rhs = self.expr(value)
        if op != "=":
            current = pb.Expr(slice=pb.Slice(operand=lvalue_to_expr(target), hi=hi, lo=lo))
            rhs = self._compound(op, current, rhs, value, lt)
        return [self._rmw(target, n, hi, lo, rhs)]

    def _direct_apply(self, s: Node) -> list[pb.Stmt]:
        target = s.node(0)
        name, top = prefixed_name(target.node(0))
        if target.list(1):
            raise Excluded("callExpressionIR: < typeArgumentListIR > on a call", "by elaboration")
        decl = self.tr.block_decls.get(name)
        if decl is None:
            raise NotTranslated("directApplicationStatementIR", name)
        block = self.tr.sub_block(decl, [], self)
        return self._call_block(block, decl, s.nodes(1))

    def _call_block(self, block: str, decl: Node, args: list[Node]) -> list[pb.Stmt]:
        params = [ParamIL.of(p) for p in decl.nodes(4)]
        kept = [
            (p, a)
            for p, a in zip(params, self._pad(params, args), strict=True)
            if not is_packet_type(p.type)
        ]
        if any(self.tr.arch is not None and self.tr.arch.is_intrinsic(p.type) for p, _ in kept):
            raise Excluded(
                "standard_metadata and other intrinsic metadata parameters",
                "by thesis",
                f"passed to {block}",
            )
        ps = [p for p, _ in kept]
        types = [self.tr.type_of(p.type, p.name) for p in ps]
        call_args, post = self.call_args(ps, [a for _, a in kept], types)
        return [pb.Stmt(call_block=pb.CallBlock(block=block, args=call_args)), *post]

    @staticmethod
    def _pad(params: Sequence[ParamIL], args: Sequence[Node]) -> list[Node]:
        # Arguments are positional here once named ones are ordered; a named
        # argument list is ordered first so that packet arguments drop out
        # by position.
        if any(a.c in ("% = %", "% = _") for a in args):
            order = {p.name: i for i, p in enumerate(params)}
            by_index: list[Node | None] = [None] * len(params)
            for a in args:
                if a.c == "% = %" or a.c == "% = _":
                    by_index[order[a.text(0)]] = a
            return [a if a is not None else Node("argumentIR", "_", ()) for a in by_index]
        return list(args) + [Node("argumentIR", "_", ())] * (len(params) - len(args))

    def _call_stmt(self, s: Node) -> list[pb.Stmt]:
        target, targs, args = s.node(0), s.nodes(1), s.nodes(2)
        if target.c == "% . %":
            return self._method_stmt(target, targs, args)
        if target.c in ("_BARE %", ". %"):
            name, top = prefixed_name(target)
            b = self.scope.lookup(name, top)
            match b:
                case ActionB():
                    return self._call_action(b, args)
                case FunctionB():
                    return self._inline(b.decl, targs, args, None)
                case ExternFunctionB():
                    if name == "verify":
                        cond = self.expr(args[0])
                        err = self.fold(args[1])
                        if not isinstance(err, ErrorVal):
                            raise NotTranslated("callStatementIR: verify(c, e)", "a computed error")
                        if self.kind != "parser":
                            raise il.ILError("verify outside a parser")
                        return [pb.Stmt(verify=pb.Verify(condition=cond, error=err.name))]
                    assert self.tr.arch is not None
                    return self.tr.arch.extern_function(self, name, targs, args)
                case _:
                    raise NotTranslated("callStatementIR", f"call of {name}")
        if target.c == "TYPE % . %":
            raise Excluded(
                "callableTargetIR: TYPE name . method (static extern method)", "by scope"
            )
        raise NotTranslated("callStatementIR", s.short())

    def _call_action(self, b: ActionB, args: list[Node]) -> list[pb.Stmt]:
        if self.kind != "control":
            raise il.ILError("action call outside a control")
        name = self.use_action(b)
        params = [ParamIL.of(p) for p in b.decl.nodes(2)]
        types = [self.tr.type_of(p.type, p.name) for p in params]
        call_args, post = self.call_args(params, args, types)
        return [pb.Stmt(call_action=pb.CallAction(action=name, args=call_args)), *post]

    def _method_stmt(self, target: Node, targs: list[Node], args: list[Node]) -> list[pb.Stmt]:
        base, method = target.node(0), target.text(1)
        base_e, base_t, _ = typed_parts(base)
        bt = strip_alias(base_t)
        packet = is_packet_type(bt)
        if packet == "packet_in":
            match method, len(args):
                case "extract", 1:
                    if args[0].c == "_":
                        # Extracting into `_` still consumes the header.
                        t = self.tr.type_of(targs[0])
                        return [
                            pb.Stmt(extract=pb.Extract(target=lvar(self.add_local("unused", t))))
                        ]
                    return [pb.Stmt(extract=pb.Extract(target=self.lvalue_of_expr(args[0])))]
                case "extract", 2:
                    raise Excluded("callStatementIR: packet.extract(h, n)", "by scope")
                case "advance", 1:
                    return [pb.Stmt(advance=pb.Advance(bits=self.expr(args[0])))]
                case "lookahead", 0:
                    # Its value is dropped, but a lookahead past the end of
                    # the packet still rejects.
                    # A lookahead of an aggregate needs only its width here.
                    width = _flat_width(targs[0])
                    t = self.tr.type_of(targs[0]) if width is None else bits_type(width)
                    look = pb.Expr(lookahead=pb.Lookahead(type=t))
                    return [assign(lvar(self.add_local("lookahead", t)), look)]
                case "length", 0:
                    raise Excluded("callExpressionIR: packet.length()", "by scope")
            raise NotTranslated("callStatementIR", f"packet_in.{method}")
        if packet == "packet_out":
            if method == "emit" and len(args) == 1:
                return [pb.Stmt(emit=pb.Emit(value=self.expr(args[0])))]
            raise NotTranslated("callStatementIR", f"packet_out.{method}")
        if bt.c == "HEADER % <%> {%}":
            match method:
                case "setValid":
                    return [pb.Stmt(set_valid=pb.SetValid(header=self._expr_lvalue(base)))]
                case "setInvalid":
                    return [pb.Stmt(set_invalid=pb.SetInvalid(header=self._expr_lvalue(base)))]
                case "isValid":
                    return []
        if bt.c == "HEADER_STACK % [%]" and method in ("push_front", "pop_front"):
            count = self.int_of(args[0], f"callStatementIR: hs.{method}(n)")
            stack = self._expr_lvalue(base)
            if method == "push_front":
                return [pb.Stmt(push=pb.Push(stack=stack, count=count))]
            return [pb.Stmt(pop=pb.Pop(stack=stack, count=count))]
        if bt.c == "TABLE % {%}" and method == "apply":
            table = self._table_name(base_e)
            return [pb.Stmt(apply=pb.Apply(table=table))]
        if bt.c in ("PARSER % <%> (%)", "CONTROL % <%> (%)") and method == "apply":
            name, top = prefixed_name(base_e)
            b = self.scope.lookup(name, top)
            if not isinstance(b, BlockInstB):
                raise NotTranslated("callStatementIR", f"{name}.apply() on a non-instance")
            return self._call_block(b.block, b.decl, args)
        if bt.c == "EXTERN % <%> %":
            return self._extern_method(base_e, bt, method, args, None)
        raise NotTranslated("callStatementIR", f".{method} on {bt.short()}")

    def _table_name(self, base_e: Node) -> str:
        name, top = prefixed_name(base_e)
        b = self.scope.lookup(name, top)
        if not isinstance(b, TableB):
            raise NotTranslated("callStatementIR: t.apply()", f"{name} is not a table")
        return b.name

    def _extern_method(
        self, base_e: Node, bt: Node, method: str, args: list[Node], result: pb.LValue | None
    ) -> list[pb.Stmt]:
        if base_e.c not in ("_BARE %", ". %"):
            raise NotTranslated("callStatementIR", "an extern method on a computed object")
        name, top = prefixed_name(base_e)
        b = self.scope.lookup(name, top)
        if not isinstance(b, ExternInstB):
            raise NotTranslated("callStatementIR", f"{name} is not an extern instance")
        decl = self.tr.extern_types[b.extern_type]
        m = next((m for m in decl.methods if m.name == method and len(m.params) == len(args)), None)
        if m is None:
            raise NotTranslated("externMethodPrototypeIR", f"{b.extern_type}.{method}/{len(args)}")
        params = [
            ParamIL(
                p.name,
                p.direction if p.direction else pb.DIRECTION_IN,
                Node("typeIR", "", ()),
                Node("", "", ()),
            )
            for p in m.params
        ]
        call_args, post = self.call_args(params, args, [p.type for p in m.params])
        call = pb.CallExtern(instance=b.instance, method=method, args=call_args)
        if m.HasField("returns"):
            if result is None:
                result = lvar(self.add_local(f"{method}_result", m.returns))
            call.result.CopyFrom(result)
        return [pb.Stmt(call_extern=call), *post]

    def _switch(self, s: Node) -> list[pb.Stmt]:
        subject = s.node(0)
        cases = s.nodes(1)
        e, t, _ = typed_parts(subject)
        if e.c == "% . %" and e.text(1) == "action_run":
            base_e, _, _ = typed_parts(e.node(0))
            return self._switch_action_run(base_e, cases)
        # A switch on a value is an if-chain (p4c SimplifySwitch).
        key_t = self.tr.type_of(t)
        key = self.add_local("switch_key", key_t)
        out = [assign(lvar(key), self.expr(subject))]
        chain: list[tuple[list[pb.Expr], list[pb.Stmt]]] = []
        default: list[pb.Stmt] | None = None
        pending: list[pb.Expr] = []
        for c in cases:
            label = c.node(0)
            body = self._case_body(c)
            if label.c == "DEFAULT":
                default = body if body is not None else []
                continue
            pending.append(binary(pb.BINARY_OP_EQ, var(key), self.expr(label)))
            if body is not None:
                chain.append((pending, body))
                pending = []
        out.extend(self._if_chain(chain, default or []))
        return out

    def _case_body(self, c: Node) -> list[pb.Stmt] | None:
        """A case's statements; None for a fall-through label."""
        if c.c == "% :":
            return None
        return self._branch(c.node(1))

    @staticmethod
    def _if_chain(
        chain: list[tuple[list[pb.Expr], list[pb.Stmt]]], default: list[pb.Stmt]
    ) -> list[pb.Stmt]:
        out = default
        for conds, body in reversed(chain):
            cond = conds[0]
            for c in conds[1:]:
                cond = binary(pb.BINARY_OP_OR, cond, c)
            out = [pb.Stmt(conditional=pb.If(condition=cond, then=body, otherwise=out))]
        return out

    def _switch_action_run(self, call: Node, cases: list[Node]) -> list[pb.Stmt]:
        table = self._applied_table(call)
        marker = self.markers.get(table)
        if marker is None:
            raise il.ILError(f"no marker prepared for {table}")
        run = marker.local
        out = [
            assign(lvar(run), lit_bits(8, marker.initial)),
            pb.Stmt(apply=pb.Apply(table=table)),
        ]
        chain: list[tuple[list[pb.Expr], list[pb.Stmt]]] = []
        default: list[pb.Stmt] = []
        pending: list[pb.Expr] = []
        for c in cases:
            label = c.node(0)
            body = self._case_body(c)
            if label.c == "DEFAULT":
                default = body or []
                continue
            le, _, _ = typed_parts(label)
            action, _ = prefixed_name(le)
            pending.append(binary(pb.BINARY_OP_EQ, var(run), lit_bits(8, marker.numbers[action])))
            if body is not None:
                chain.append((pending, body))
                pending = []
        out.extend(self._if_chain(chain, default))
        return out

    # -- functions

    def _inline(
        self, decl: Node, targs: list[Node], args: list[Node], result: pb.LValue | None
    ) -> list[pb.Stmt]:
        """A function call inlined (p4c `InlineFunctions`): parameters are
        fresh locals, copied in and out, and the one trailing `return e` is
        an assignment to the result."""
        if targs:
            raise Excluded("callExpressionIR: < typeArgumentListIR > on a call", "by elaboration")
        proto = decl.node(1)
        fname = proto.text(1)
        params = [ParamIL.of(p) for p in proto.nodes(4)]
        body = decl.node(2).nodes(1)
        returns = [n for n in il.walk(body) if n.c in ("RETURN ;", "RETURN % ;")]
        tail = body[-1] if body else None
        if returns and (
            tail is None or tail.c not in ("RETURN ;", "RETURN % ;") or len(returns) > 1
        ):
            raise NotTranslated(
                "functionDeclarationIR", f"{fname}: a return other than the last statement"
            )
        ordered = self.ordered_args(params, args)
        out: list[pb.Stmt] = []
        inner = self.scope
        fscope = self.tr.global_scope.child()
        copy_out: list[tuple[pb.LValue, str]] = []
        for p, a in zip(params, ordered, strict=True):
            t = self.tr.type_of(p.type, p.name)
            local = self.add_local(f"{fname}_{p.name}", t)
            fscope.bind(p.name, VarB(local))
            if (
                p.direction in (pb.DIRECTION_IN, pb.DIRECTION_INOUT, pb.DIRECTION_NONE)
                and a is not None
            ):
                out.append(assign(lvar(local), self.expr(a)))
            else:
                # An `out` parameter starts at its default on every call,
                # like a local declared without an initializer.
                out.extend(self.zero(lvar(local), t))
            if p.direction in (pb.DIRECTION_OUT, pb.DIRECTION_INOUT) and a is not None:
                copy_out.append((self.lvalue_of_expr(a), local))
        self.scope = fscope
        try:
            stmts = body[:-1] if returns else body
            out.extend(self._reentered(lambda: self.stmts(stmts)))
            if returns and tail is not None and tail.c == "RETURN % ;":
                value = self.expr(tail.node(0))
                if result is not None:
                    out.append(assign(result, value))
        finally:
            self.scope = inner
        for lv, local in copy_out:
            out.append(assign(lv, var(local)))
        return out

    # -- actions and tables

    def use_action(self, b: ActionB) -> str:
        """The IR name of an action called from the block, adding a
        top-level action to the block the first time."""
        if b.decl in self.tr.top_actions.values() and b.name not in self.taken:
            self.translate_action(b.decl, b.name)
        return b.name

    def translate_action(
        self,
        decl: Node,
        name: str,
        bound: dict[str, Node] | None = None,
        marker: Sequence[tuple[str, int]] = (),
    ) -> pb.Action:
        params = [ParamIL.of(p) for p in decl.nodes(2)]
        action = pb.Action(name=name)
        saved_scope, saved_action = self.scope, self.action
        self.scope = self.scope.child()
        self.action = name
        try:
            for p in params:
                if bound is not None and p.name in bound:
                    continue
                if p.direction != pb.DIRECTION_NONE and bound is not None:
                    raise NotTranslated(
                        "tableActionIR", f"{name}: a directional parameter left unbound"
                    )
                t = self.tr.type_of(p.type, p.name)
                action.params.append(pb.Param(name=p.name, type=t, direction=p.direction))  # type: ignore[arg-type]
                self.scope.bind(p.name, VarB(p.name))
            if bound:
                used = {n.text(0) for n in il.walk(decl.node(3)) if n.c == "_BARE %"}
                for pname, te in bound.items():
                    # Substituting the bound expression is copy-in and
                    # copy-out only when the body reaches what it names
                    # through the parameter alone.
                    roots = {n.text(0) for n in il.walk(te) if n.c == "_BARE %"}
                    if roots & (used - {pname}):
                        raise NotTranslated(
                            "tableActionIR", f"{name}: a bound argument the body also reaches"
                        )
                    self.scope.bind(pname, BoundArgB(te, saved_scope))
            action.body.extend(self._reentered(lambda: self.stmts(decl.node(3).nodes(1))))
            for local, number in marker:
                action.body.append(assign(lvar(local), lit_bits(8, number)))
        finally:
            self.scope, self.action = saved_scope, saved_action
        self.taken.add(name)
        self.block.actions.append(action)
        return action

    def translate_table(self, decl: Node) -> None:
        name = decl.text(2)
        table = pb.Table(name=name)
        props = decl.nodes(3)
        largest_wins = True
        for p in props:
            if p.c == "% % CUSTOM % % ;" or p.c == "% % CUSTOM_CONST % % ;":
                if p.text(2) == "largest_priority_wins":
                    v = self.fold(p.node(3).node(0)) if p.node(3).c == "= %" else None
                    if v is None and p.node(3).c == "= _VALUE %":
                        v = self.tr.value(p.node(3).node(0))
                    largest_wins = v is not False
        for p in props:
            match p.c:
                case "KEY = {%}":
                    for k in p.nodes(0):
                        table.keys.append(self._key(k))
                case "ACTIONS = {%}":
                    for a in p.nodes(0):
                        action = self._table_action(name, a)
                        # P4-SpecTec inserts `.NoAction` when the list names
                        # `NoAction` without the dot; it is one action.
                        if action not in table.actions:
                            table.actions.append(action)
                case "% % DEFAULT_ACTION = % ;":
                    table.default_action.CopyFrom(self._action_call(name, p.node(2)))
                    table.const_default_action = p.opt(1) is not None
                case "% % ENTRIES = {%}":
                    if p.opt(1) is None:
                        raise Excluded(
                            "tableEntriesPropertyIR without const, and a per-entry constIR",
                            "by scope",
                        )
                    ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in table.keys)
                    entries = [self._entry(name, table, e) for e in p.nodes(2)]
                    if ternary:
                        priorities = [pr for _, pr in entries]
                        if any(pr is None for pr in priorities):
                            raise NotTranslated(
                                "tableEntryPriorityIR", f"{name}: an entry without a priority"
                            )
                        numbers = [pr for pr in priorities if pr is not None]
                        top = max(numbers, default=0)
                        for (entry, pr), n in zip(entries, numbers, strict=True):
                            entry.priority = n if largest_wins else top + 1 - n
                            del pr
                    table.const_entries.extend(e for e, _ in entries)
                case "% % CUSTOM % % ;" | "% % CUSTOM_CONST % % ;":
                    prop = p.text(2)
                    init = p.node(3)
                    if prop == "size":
                        te = init.node(0)
                        if init.c == "= %":
                            table.size = self.int_of(te, "tableCustomPropertyIR: size")
                        else:
                            v = self.tr.value(te)
                            table.size = v.value if isinstance(v, Int | Bits) else 0
                    elif prop in ("largest_priority_wins", "priority_delta"):
                        pass
                    else:
                        raise Excluded(
                            "tableCustomPropertyIR: implementation, counters, meters, psa_* "
                            "and other architecture properties",
                            "by thesis",
                            prop,
                        )
                case _:
                    raise NotTranslated("tablePropertyIR", p.short())
        self.taken.add(name)
        self.block.tables.append(table)

    def _key(self, k: Node) -> pb.Key:
        te, key_name, kind = k.node(0), k.text(1), k.text(2)
        match kind:
            case "exact":
                mk = pb.MATCH_KIND_EXACT
            case "lpm":
                mk = pb.MATCH_KIND_LPM
            case "ternary":
                mk = pb.MATCH_KIND_TERNARY
            case "selector":
                raise Excluded("tableKeyIR: match kind selector", "by thesis")
            case "range" | "optional":
                raise Excluded("tableKeyIR: match kinds range, optional", "by thesis", kind)
            case _:
                raise Excluded("tableKeyIR: match kinds range, optional", "by thesis", kind)
        e = self.expr(te)
        _, t, _ = typed_parts(te)
        kt = self.tr.type_of(t)
        if kt.WhichOneof("kind") == "boolean":
            e = pb.Expr(cast=pb.Cast(to=bits_type(1), operand=e))
        elif kt.WhichOneof("kind") != "bits":
            raise NotTranslated("tableKeyIR", f"a key of type {kt.WhichOneof('kind')}")
        key = pb.Key(expr=e, match_kind=mk)  # type: ignore[arg-type]
        # The key's control-plane name is P4's unless it read intrinsic
        # metadata, which the contract has renamed: the IR's path is the
        # name a host can use then.
        intrinsic = any(
            n.c == "_BARE %" and isinstance(self.scope.lookup(n.text(0)), IntrinsicB)
            for n in il.walk(te)
        )
        if ir.dotted_path(e) != key_name and not intrinsic:
            key.name = key_name
        return key

    def _table_action(self, table: str, a: Node) -> str:
        ref = a.node(1)
        name, top = prefixed_name(ref.node(0))
        b = self.scope.lookup(name, top)
        if not isinstance(b, ActionB):
            raise NotTranslated("tableActionIR", f"{name} is not an action")
        if not ref.nodes(2):
            return b.name
        return self.action_copies[(b.name, table)]

    def _action_call(self, table: str, ref: Node) -> pb.ActionCall:
        """A table's default action or an entry's action, with data literals."""
        name, top = prefixed_name(ref.node(0))
        b = self.scope.lookup(name, top)
        if not isinstance(b, ActionB):
            raise NotTranslated("tableActionReferenceIR", f"{name} is not an action")
        params = [ParamIL.of(p) for p in b.decl.nodes(2)]
        args = ref.nodes(2)
        ordered = self.ordered_args(params, args)
        target = self.action_copies.get((b.name, table), b.name)
        call = pb.ActionCall(action=target)
        for p, a in zip(params, ordered, strict=True):
            if p.direction != pb.DIRECTION_NONE:
                continue
            if a is None:
                raise NotTranslated("tableActionReferenceIR", f"{name}: missing action data")
            call.args.append(self.literal(a, self.tr.type_of(p.type, p.name)))
        return call

    def _entry(self, table: str, t: pb.Table, e: Node) -> tuple[pb.Entry, int | None]:
        if e.opt(0) is not None:
            raise Excluded(
                "tableEntriesPropertyIR without const, and a per-entry constIR", "by scope"
            )
        pr_node = e.opt(1)
        priority: int | None = None
        if pr_node is not None:
            assert isinstance(pr_node, Node)
            v = self.tr.value(pr_node.node(0))
            if not isinstance(v, Int | Bits):
                raise NotTranslated("tableEntryPriorityIR", pr_node.short())
            priority = v.value
        keyset = e.node(2)
        sets = keyset.nodes(0) if keyset.c == "(%)" else [keyset]
        if len(sets) != len(t.keys):
            raise il.ILError(f"{table}: entry arity")
        entry = pb.Entry()
        for key, ks in zip(t.keys, sets, strict=True):
            entry.keys.append(self._key_value(table, key, ks))
        entry.action.CopyFrom(self._action_call(table, e.node(3)))
        return entry, priority

    def _key_value(self, table: str, key: pb.Key, ks: Node) -> pb.KeyValue:
        width = self._key_width(key)
        full = (1 << width) - 1

        def num(te: Node) -> int:
            v = self.fold_keyset(te)
            if isinstance(v, bool):
                return int(v)
            if isinstance(v, Int | Bits):
                return v.value % (1 << width)
            raise NotTranslated("tableEntryIR: the keyset", f"not a constant: {te.short()}")

        match ks.c:
            case "DEFAULT" | "_":
                value, mask = 0, 0
            case "% &&& %":
                value, mask = num(ks.node(0)), num(ks.node(1))
            case "% .. %":
                raise Excluded("simpleKeysetExpressionIR: e .. e in a table entry", "by thesis")
            case "% # %":
                value, mask = num(ks), full
            case _:
                raise NotTranslated("simpleKeysetExpressionIR", ks.short())
        value &= mask
        match key.match_kind:
            case pb.MATCH_KIND_EXACT:
                if mask != full:
                    raise NotTranslated("tableEntryIR", f"{table}: a masked value on an exact key")
                return pb.KeyValue(exact=str(value))
            case pb.MATCH_KIND_LPM:
                prefix = bin(mask).count("1")
                if mask != (full ^ ((1 << (width - prefix)) - 1)):
                    raise NotTranslated(
                        "tableEntryIR", f"{table}: an lpm mask that is not a prefix"
                    )
                return pb.KeyValue(lpm=pb.LpmValue(value=str(value), prefix_len=prefix))
            case _:
                return pb.KeyValue(ternary=pb.TernaryValue(value=str(value), mask=str(mask)))

    def _key_width(self, key: pb.Key) -> int:
        widths = _Widths(self)
        return widths.of(key.expr)

    # -- parser states

    def state(self, st: Node) -> pb.State:
        name = st.text(1)
        body = self._reentered(lambda: self.stmts(st.nodes(2)))
        trans = st.node(3).node(0)
        state = pb.State(name=name, body=body)
        if trans.c == "% ;":
            state.transition.direct.CopyFrom(self._target(trans.text(0)))
        elif trans.c == "SELECT (%) {%}":
            select = pb.Select(keys=[self.expr(k) for k in trans.nodes(0)])
            key_types = [self.tr.type_of(typed_parts(k)[1]) for k in trans.nodes(0)]
            for case in trans.nodes(1):
                ks = case.node(0)
                sets = ks.nodes(0) if ks.c == "(%)" else [ks]
                if len(sets) == 1 and len(key_types) > 1 and sets[0].c in ("DEFAULT", "_"):
                    sets = sets * len(key_types)
                select.cases.append(
                    pb.SelectCase(
                        sets=[self._key_set(s, kt) for s, kt in zip(sets, key_types, strict=True)],
                        target=self._target(case.text(1)),
                    )
                )
            # Hoisted statements of the keys belong to the state body.
            state.body.extend(self.pre)
            self.pre = []
            state.transition.select.CopyFrom(select)
        else:
            raise NotTranslated("transitionStatementIR", trans.short())
        return state

    @staticmethod
    def _target(name: str) -> pb.Target:
        if name == "accept":
            return pb.Target(accept=pb.Accept())
        if name == "reject":
            return pb.Target(reject=pb.Reject())
        return pb.Target(state=name)

    def _key_set(self, ks: Node, kt: pb.Type) -> pb.KeySet:
        match ks.c:
            case "DEFAULT" | "_":
                return pb.KeySet(dont_care=pb.DontCare())
            case "% &&& %":
                return pb.KeySet(
                    masked=pb.MaskedValue(
                        value=self._set_literal(ks.node(0), kt),
                        mask=self._set_literal(ks.node(1), kt),
                    )
                )
            case "% .. %":
                return pb.KeySet(
                    range=pb.RangeValue(
                        lo=self._set_literal(ks.node(0), kt), hi=self._set_literal(ks.node(1), kt)
                    )
                )
            case "% # %":
                return pb.KeySet(exact=self._set_literal(ks, kt))
            case _:
                raise NotTranslated("simpleKeysetExpressionIR", ks.short())

    def _set_literal(self, te: Node, kt: pb.Type) -> pb.Literal:
        v = self.fold_keyset(te)
        if isinstance(v, Int) and kt.WhichOneof("kind") == "bits":
            v = _wrap(kt.bits, v.value)
        lit = None if v is None else literal_of(v)
        if lit is None:
            raise NotTranslated("selectCaseIR", f"a keyset that is not a constant: {te.short()}")
        if isinstance(v, EnumVal):
            self.tr.type_of(Node("simpleEnumTypeIR", "ENUM % {%}", (v.enum_type, [])))
        return lit


def _flat_width(t: Node) -> int | None:
    """The bit width of a header or struct of bits and bools, else None."""
    t = strip_alias(t)
    if t.c not in ("HEADER % <%> {%}", "STRUCT % <%> {%}"):
        return None
    total = 0
    for f in t.nodes(2):
        ft = strip_alias(f.node(1))
        if ft.c == "BIT <%>":
            total += ft.num(0)
        elif ft.c == "BOOL":
            total += 1
        else:
            inner = _flat_width(ft)
            if inner is None:
                return None
            total += inner
    return total or None


def _aggregate_source(te: Node) -> Node | None:
    """The list or record expression under casts to list types, if any."""
    e, _, _ = typed_parts(te)
    while e.c == "(%) %" and strip_alias(e.node(0)).c in (
        "SEQ <%>",
        "SEQ <% , ...>",
        "TUPLE <%>",
        "RECORD {%}",
    ):
        e, _, _ = typed_parts(e.node(1))
    return e if e.c in ("SEQ {%}", "RECORD {%}") else None


class _IntrinsicWrite(Exception):
    """An assignment to an intrinsic metadata field, caught by the statement."""

    def __init__(self, fieldname: str) -> None:
        super().__init__(fieldname)
        self.fieldname = fieldname


class _Widths:
    """The width of a table key expression in a translated block."""

    def __init__(self, cx: BlockCx) -> None:
        self.cx = cx

    def of(self, e: pb.Expr) -> int:
        t = self.type(e)
        if t.WhichOneof("kind") != "bits":
            raise NotTranslated("tableKeyIR", "a key that is not bits")
        return t.bits

    def type(self, e: pb.Expr) -> pb.Type:
        tr, block = self.cx.tr, self.cx.block
        match e.WhichOneof("kind"):
            case "literal":
                lit = e.literal
                if lit.WhichOneof("value") == "bits":
                    return bits_type(lit.bits.width)
                return BOOL
            case "var":
                for p in [*block.params, *block.locals]:
                    if p.name == e.var:
                        return p.type
                raise il.ILError(f"unknown key variable {e.var}")
            case "member":
                base = self.type(e.member.base)
                name = base.header or base.struct
                fields = (
                    tr.header_types[name].fields
                    if name in tr.header_types
                    else tr.struct_types[name].fields
                )
                for f in fields:
                    if f.name == e.member.field:
                        return f.type
                raise il.ILError(f"no field {e.member.field}")
            case "index":
                return pb.Type(header=self.type(e.index.base).stack.header)
            case "cast":
                return e.cast.to
            case "slice":
                return bits_type(e.slice.hi - e.slice.lo + 1)
            case "binary":
                left = self.type(e.binary.left)
                if e.binary.op == pb.BINARY_OP_CONCAT:
                    return bits_type(left.bits + self.type(e.binary.right).bits)
                if e.binary.op in (
                    pb.BINARY_OP_EQ,
                    pb.BINARY_OP_NE,
                    pb.BINARY_OP_LT,
                    pb.BINARY_OP_LE,
                    pb.BINARY_OP_GT,
                    pb.BINARY_OP_GE,
                    pb.BINARY_OP_AND,
                    pb.BINARY_OP_OR,
                ):
                    return BOOL
                return left
            case "unary":
                return self.type(e.unary.operand)
            case "last_index":
                return bits_type(32)
            case "is_valid":
                return BOOL
            case "mux":
                return self.type(e.mux.then)
            case _:
                raise NotTranslated("tableKeyIR", f"a {e.WhichOneof('kind')} key")


# ---------------------------------------------------------------------------
# Whole blocks
# ---------------------------------------------------------------------------


def _bind_block_declarations(cx: BlockCx, locals_: list[Node]) -> list[Node]:
    """Bind a block's local declarations; return the ones translated in
    order afterwards (variables, actions, tables, states' prerequisites)."""
    tr = cx.tr
    rest: list[Node] = []
    for d in locals_:
        match d.c:
            case "% CONST % % % ;":
                cx.scope.bind(d.text(2), ConstB(tr.const_value(d.node(1), d.node(3))))
            case "% % % (%) % % ;":
                _instantiate(cx, d)
            case "% ACTION % (%) %":
                cx.scope.bind(d.text(1), ActionB(d.text(1), d))
                rest.append(d)
            case "% TABLE % % {%}":
                cx.scope.bind(d.text(2), TableB(d.text(2)))
                rest.append(d)
            case "% % % % ;":
                rest.append(d)
            case "% VALUE_SET <%> (%) % ;":
                raise Excluded("valueSetDeclarationIR", "by scope")
            case _:
                if d.t == "valueSetDeclarationIR":
                    raise Excluded("valueSetDeclarationIR", "by scope")
                raise NotTranslated(d.t, d.short())
    return rest


def _instantiate(cx: BlockCx, d: Node) -> None:
    """A local instantiation: a sub-block instance or an extern instance."""
    tr = cx.tr
    t = strip_alias(d.node(1))
    inst_name = d.text(4)
    if d.opt(5) is not None:
        raise Excluded("objectInitializerIR, ABSTRACT in externMethodPrototypeIR", "by scope")
    args = d.nodes(3)
    if t.c in ("PARSER % <%> (%)", "CONTROL % <%> (%)"):
        decl_name, _ = prefixed_name(d.node(2).node(0))
        decl = tr.block_decls[decl_name]
        block = tr.sub_block(decl, args, cx)
        cx.scope.bind(inst_name, BlockInstB(block, decl))
        return
    if t.c == "EXTERN % <%> %":
        assert tr.arch is not None
        cx.scope.bind(inst_name, tr.arch.extern_object(cx, inst_name, t, args))
        return
    if t.c == "PACKAGE % <%> {%}":
        raise Excluded("instantiationIR of a package (main)", "by thesis", inst_name)
    raise NotTranslated("instantiationIR", d.short())


def _prepare_actions(cx: BlockCx, rest: list[Node]) -> None:
    """Per-table action copies and `action_run` markers, decided before any
    action is translated since both change action bodies."""
    tables = [d for d in rest if d.c == "% TABLE % % {%}"]
    bound: dict[str, list[tuple[str, list[Node]]]] = {}
    for tbl in tables:
        for p in tbl.nodes(3):
            if p.c != "ACTIONS = {%}":
                continue
            for a in p.nodes(0):
                ref = a.node(1)
                name, top = prefixed_name(ref.node(0))
                if ref.nodes(2):
                    bound.setdefault(name, []).append((tbl.text(2), ref.nodes(2)))
    # An action also used unbound, listed plainly or called, keeps its name,
    # and its copies are numbered from 1; otherwise the first copy takes the
    # name, as p4c's frontend names them (`setbyte`, `setbyte_1`, ...).
    plain: set[str] = set()
    for n in il.walk(cx.decl):
        if n.t == "tableActionReferenceIR" and not n.nodes(2):
            plain.add(prefixed_name(n.node(0))[0])
        if n.c == "% <%> (%) ;" and n.node(0).c in ("_BARE %", ". %"):
            plain.add(prefixed_name(n.node(0))[0])
    for action, uses in bound.items():
        start = 1 if action in plain else 0
        for i, (table, _) in enumerate(uses, start):
            cx.action_copies[(action, table)] = action if i == 0 else f"{action}_{i}"
        if action in plain:
            cx.bound_actions.add(action)
    # action_run markers: the labels of every switch on t.apply().action_run.
    body_nodes = [n for n in il.walk(cx.decl) if n.c == "SWITCH (%) {%}"]
    for sw in body_nodes:
        e, _, _ = typed_parts(sw.node(0))
        if not (e.c == "% . %" and e.text(1) == "action_run"):
            continue
        call, _, _ = typed_parts(e.node(0))
        table_e, _, _ = typed_parts(call.node(0).node(0))
        table, _ = prefixed_name(table_e)
        labels: list[str] = []
        for c in sw.nodes(1):
            label = c.node(0)
            if label.c == "DEFAULT":
                continue
            le, _, _ = typed_parts(label)
            labels.append(prefixed_name(le)[0])
        if table in cx.markers:
            raise NotTranslated(
                "switchStatementIR on t.apply().action_run", f"{table} switched twice"
            )
        if len(labels) > 255:
            raise NotTranslated("switchStatementIR on t.apply().action_run", "more than 255 labels")
        local = cx.add_local(f"{table}_run", bits_type(8))
        decl = next(t for t in tables if t.text(2) == table)
        actions = [
            prefixed_name(n.node(0))[0] for n in il.walk(decl) if n.t == "tableActionReferenceIR"
        ]
        cx.markers[table] = Marker(local, {a: i + 1 for i, a in enumerate(labels)}, actions)


def _marker_for(cx: BlockCx, action: str, table_of_copy: str | None) -> list[tuple[str, int]]:
    """The marker assignments `action` ends with, one per switched table."""
    out: list[tuple[str, int]] = []
    for table, m in cx.markers.items():
        if table_of_copy is not None and table_of_copy != table:
            continue
        if action == "NoAction":
            continue
        if action in m.numbers:
            out.append((m.local, m.numbers[action]))
        elif m.initial and action in m.actions:
            out.append((m.local, 0))
    return out


def translate_locals(cx: BlockCx, rest: list[Node]) -> None:
    """Variables, actions and tables of a parser or control, in order."""
    _prepare_actions(cx, rest)
    # Top-level actions a table names are the block's too, first, in the
    # program's order.
    named: set[str] = set()
    for d in rest:
        if d.c == "% TABLE % % {%}":
            for n in il.walk(d):
                if n.t == "tableActionReferenceIR":
                    named.add(prefixed_name(n.node(0))[0])
    for name, decl in cx.tr.top_actions.items():
        local = any(d.c == "% ACTION % (%) %" and d.text(1) == name for d in rest)
        if name in named and not local:
            b = cx.scope.lookup(name)
            if isinstance(b, ActionB) and b.decl is decl:
                _translate_action_decl(cx, decl)
    for d in rest:
        match d.c:
            case "% % % % ;":
                name = d.text(2)
                t = cx.tr.type_of(d.node(1), name)
                local = cx.add_local(name, t)
                cx.scope.bind(name, VarB(local))
                init = d.opt(3)
                if init is not None:
                    assert isinstance(init, Node)
                    # A block-level local starts at zero in the IR (docs/
                    # ir-semantics.md), so a zero initializer is already
                    # done; the printer writes one for every scalar local.
                    v = cx.fold(init.node(0))
                    if not _is_zero(v):
                        cx.block.body.extend(cx.stmt(_init_stmt(d, init)))
            case "% ACTION % (%) %":
                _translate_action_decl(cx, d)
            case "% TABLE % % {%}":
                cx.translate_table(d)


def _translate_action_decl(cx: BlockCx, d: Node) -> None:
    """An action, as itself when used unbound and once per table that binds
    some of its parameters."""
    name = d.text(1)
    copies = [(t, c) for (a, t), c in cx.action_copies.items() if a == name]
    if not copies or name in cx.bound_actions:
        cx.translate_action(d, name, marker=_marker_for(cx, name, None))
    for table, copy_name in copies:
        uses = _bound_args(d, cx, table)
        cx.translate_action(d, copy_name, bound=uses, marker=_marker_for(cx, name, table))


def _is_zero(v: Val | None) -> bool:
    return v is False or (isinstance(v, Bits | Int) and v.value == 0)


def _init_stmt(decl: Node, init: Node) -> Node:
    """A variable initializer as the assignment it means."""
    lvalue = Node(
        "typedLvalueIR",
        "% # %",
        (
            Node("prefixedNameIR", "_BARE %", (decl.text(2),)),
            Node("lvalueNoteIR", "(%)", (decl.node(1),)),
        ),
    )
    return Node(
        "assignmentStatementIR", "% % % ;", (lvalue, Node("assignop", "=", ()), init.node(0))
    )


def _bound_args(action: Node, cx: BlockCx, table: str) -> dict[str, Node]:
    params = [ParamIL.of(p) for p in action.nodes(2)]
    for d in il.walk(cx.decl):
        if d.c == "% TABLE % % {%}" and d.text(2) == table:
            for n in il.walk(d):
                if n.t == "tableActionReferenceIR" and prefixed_name(n.node(0))[0] == action.text(
                    1
                ):
                    args = n.nodes(2)
                    if args:
                        ordered = cx.ordered_args(params, args)
                        return {
                            p.name: a
                            for p, a in zip(params, ordered, strict=False)
                            if a is not None
                        }
    raise il.ILError(f"no binding of {action.text(1)} in {table}")


def translate_block(
    tr: Translator,
    decl: Node,
    name: str,
    kind: str,
    ctor_values: Sequence[Val],
    part: str = "ingress",
    meta_index: int | None = None,
) -> BlockCx:
    """One parser or control declaration as a block, constructor parameters
    bound to `ctor_values` (one block per instantiation)."""
    parser = decl.c.startswith("% PARSER")
    if decl.list(2) or decl.list(3):
        raise Excluded("its two typeParameterListIR", "by elaboration", decl.text(1))
    scope = tr.global_scope.child()
    cx = BlockCx(tr, decl, name, kind, scope)
    cx.part = part
    ctor = [ParamIL.of(p) for p in decl.nodes(5)]
    for p, v in zip(ctor, ctor_values, strict=True):
        scope.bind(p.name, ConstB(v))
    il_params = [ParamIL.of(n) for n in decl.nodes(4)]
    for i, p in enumerate(il_params):
        if is_packet_type(p.type):
            continue
        if tr.arch is not None and tr.arch.is_intrinsic(p.type):
            scope.bind(p.name, IntrinsicB(p.name))
            continue
        if p.direction == pb.DIRECTION_NONE:
            raise NotTranslated("parameterIR", f"{decl.text(1)}.{p.name} has no direction")
        t = tr.type_of(p.type, p.name)
        ir_name = p.name
        if meta_index is not None and i == meta_index:
            # The metadata parameter carries the contract fields that were
            # standard_metadata's too; it is named `meta` unless the block
            # uses that name for something else.
            others = {
                q.name
                for q in il_params
                if q is not p and not (tr.arch is not None and tr.arch.is_intrinsic(q.type))
            } | {
                d.text(2) if d.c == "% % % % ;" else d.text(1)
                for d in decl.nodes(6)
                if d.c in ("% % % % ;", "% ACTION % (%) %")
            }
            if "meta" not in others:
                ir_name = "meta"
            cx.meta = ir_name
        cx.block.params.append(pb.Param(name=ir_name, type=t, direction=p.direction))  # type: ignore[arg-type]
        cx.taken.add(ir_name)
        scope.bind(p.name, VarB(ir_name))
    if parser:
        states = decl.nodes(7)
        cx.taken |= {st.text(1) for st in states}
        rest = _bind_block_declarations(cx, decl.nodes(6))
        translate_locals(cx, rest)
        prologue = list(cx.block.body)
        del cx.block.body[:]
        for st in states:
            cx.block.states.append(cx.state(st))
        start = next((s for s in cx.block.states if s.name == "start"), None)
        if start is None:
            raise il.ILError(f"parser {name} has no start state")
        cx.block.start_state = "start"
        if prologue:
            # Parser-level initializers run once, when the parser starts; a
            # start state that is also a loop target gets an entry state.
            reentered = any(
                t.state == "start"
                for st in cx.block.states
                for t in (
                    [st.transition.direct]
                    if st.transition.WhichOneof("kind") == "direct"
                    else [c.target for c in st.transition.select.cases]
                )
            )
            if reentered:
                entry = cx.fresh("start_init")
                cx.block.states.insert(
                    0,
                    pb.State(
                        name=entry,
                        body=prologue,
                        transition=pb.Transition(direct=pb.Target(state="start")),
                    ),
                )
                cx.block.start_state = entry
            else:
                body = prologue + list(start.body)
                del start.body[:]
                start.body.extend(body)
    else:
        rest = _bind_block_declarations(cx, decl.nodes(6))
        translate_locals(cx, rest)
        inner = cx.scope
        cx.scope = inner.child()
        try:
            cx.block.body.extend(cx.stmts(decl.node(7).nodes(1)))
        finally:
            cx.scope = inner
    return cx


def block_kind(decl: Node) -> str:
    if decl.c.startswith("% PARSER"):
        return "parser"
    params = [ParamIL.of(p) for p in decl.nodes(4)]
    return "deparser" if any(is_packet_type(p.type) == "packet_out" for p in params) else "control"


def owns_state(decl: Node) -> bool:
    return any(
        d.t == "instantiationIR" and strip_alias(d.node(1)).c == "EXTERN % <%> %"
        for d in decl.nodes(6)
    )


def ctor_value(cx: BlockCx, a: Node) -> Val:
    te = a if a.c == "% # %" else a.node(1) if a.c == "% = %" else None
    if te is None:
        raise NotTranslated("argumentIR", f"constructor argument {a.short()}")
    v = cx.fold(te)
    if v is None:
        raise NotTranslated(
            "its constructorParameterListIR", "a constructor argument that is not a scalar constant"
        )
    return v
