"""IR to P4-16 text, wrapped in a v1model shim.

The IR has no architecture; the printed program supplies v1model's six
blocks so that it compiles with p4c and runs on BMv2 or P4-SpecTec's
simulator. The shim is the whole architecture binding and lives in
`standard_metadata_binding`; everything else is a faithful reversal of the
IR's dedicated nodes back into P4 syntax (`packet.extract(...)`,
`h.isValid()`, `s.push_front(n)` and so on; see .agents/decisions.md).

Entry points: `print_program` for a whole program, and `print_type`,
`print_expr`, `print_lvalue` and `print_stmt` for pieces. A program handed
to `print_program` is assumed valid; what the printer cannot express raises
`PrintError`.

Conventions of the output, chosen for correctness over readability:

- every non-leaf operand is parenthesized, so precedence never matters;
- literals carry their width, `8w255`;
- scalar locals get their zero initializer (docs/ir-semantics.md, uninitialized
  variables), so p4c does not warn and the oracle starts where the reference
  interpreter does;
- a table with a ternary key prints non-const `entries` with
  `priority = N` and `largest_priority_wins = true`, because p4c refuses
  priorities on `const entries` and rejects `@priority` annotations; the
  entries are sorted by descending priority to match p4c's expectation.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "PrintError",
    "print_expr",
    "print_literal",
    "print_lvalue",
    "print_program",
    "print_stmt",
    "print_type",
    "standard_metadata_binding",
]


class PrintError(Exception):
    """The program uses something the v1model shim cannot express."""


INDENT = "    "

# Fixed names of the shim's own blocks and of the blocks printed for a
# missing role.
VERIFY_CHECKSUM = "MyVerifyChecksum"
EGRESS = "MyEgress"
COMPUTE_CHECKSUM = "MyComputeChecksum"
MISSING_ROLE_NAMES = {
    "parser": "MyParser",
    "control": "MyIngress",
    "deparser": "MyDeparser",
}

# The names of the packet parameters the shim adds to parsers and deparsers.
PACKET = "packet"
STANDARD_METADATA = "standard_metadata"


# ---------------------------------------------------------------------------
# Types and literals
# ---------------------------------------------------------------------------


def print_type(t: pb.Type) -> str:
    """A type as P4 writes it; a stack as `t[N]`, valid only in declarations."""
    match t.WhichOneof("kind"):
        case "bits":
            return f"bit<{t.bits}>"
        case "boolean":
            return "bool"
        case "header":
            return t.header
        case "struct":
            return t.struct
        case "enum_type":
            return t.enum_type
        case "error":
            return "error"
        case "stack":
            return f"{t.stack.header}[{t.stack.size}]"
        case _:
            raise PrintError("type has no kind")


def print_literal(lit: pb.Literal) -> str:
    match lit.WhichOneof("value"):
        case "bits":
            return f"{lit.bits.width}w{lit.bits.value}"
        case "boolean":
            return "true" if lit.boolean else "false"
        case "enum_member":
            return f"{lit.enum_member.enum_type}.{lit.enum_member.member}"
        case "error":
            return f"error.{lit.error}"
        case _:
            raise PrintError("literal has no value")


def _bits(width: int, value: int) -> str:
    return f"{width}w{value}"


# ---------------------------------------------------------------------------
# Expressions and lvalues
# ---------------------------------------------------------------------------

_UNARY_OPS: dict[int, str] = {
    pb.UNARY_OP_NOT: "!",
    pb.UNARY_OP_COMPLEMENT: "~",
    pb.UNARY_OP_NEGATE: "-",
}

_BINARY_OPS: dict[int, str] = {
    pb.BINARY_OP_ADD: "+",
    pb.BINARY_OP_SUB: "-",
    pb.BINARY_OP_MUL: "*",
    pb.BINARY_OP_ADD_SAT: "|+|",
    pb.BINARY_OP_SUB_SAT: "|-|",
    pb.BINARY_OP_BIT_AND: "&",
    pb.BINARY_OP_BIT_OR: "|",
    pb.BINARY_OP_BIT_XOR: "^",
    pb.BINARY_OP_SHL: "<<",
    pb.BINARY_OP_SHR: ">>",
    pb.BINARY_OP_CONCAT: "++",
    pb.BINARY_OP_EQ: "==",
    pb.BINARY_OP_NE: "!=",
    pb.BINARY_OP_LT: "<",
    pb.BINARY_OP_LE: "<=",
    pb.BINARY_OP_GT: ">",
    pb.BINARY_OP_GE: ">=",
    pb.BINARY_OP_AND: "&&",
    pb.BINARY_OP_OR: "||",
}

# Expression kinds that bind tighter than any operator and need no
# parentheses as operands.
_ATOMS = frozenset({"literal", "var", "member", "index", "last_index", "is_valid", "lookahead"})


def print_expr(e: pb.Expr) -> str:
    """An expression, with every non-leaf sub-expression parenthesized."""
    match e.WhichOneof("kind"):
        case "literal":
            return print_literal(e.literal)
        case "var":
            return e.var
        case "member":
            return f"{_operand(e.member.base)}.{e.member.field}"
        case "index":
            return f"{_operand(e.index.base)}[{print_expr(e.index.index)}]"
        case "last_index":
            return f"{_operand(e.last_index.stack)}.lastIndex"
        case "unary":
            op = _UNARY_OPS.get(e.unary.op)
            if op is None:
                raise PrintError("unary expression has no operator")
            return f"{op}{_operand(e.unary.operand)}"
        case "binary":
            op = _BINARY_OPS.get(e.binary.op)
            if op is None:
                raise PrintError("binary expression has no operator")
            return f"{_operand(e.binary.left)} {op} {_operand(e.binary.right)}"
        case "cast":
            return f"({print_type(e.cast.to)}) {_operand(e.cast.operand)}"
        case "slice":
            return f"{_operand(e.slice.operand)}[{e.slice.hi}:{e.slice.lo}]"
        case "is_valid":
            return f"{_operand(e.is_valid.header)}.isValid()"
        case "mux":
            m = e.mux
            return f"{_operand(m.condition)} ? {_operand(m.then)} : {_operand(m.otherwise)}"
        case "lookahead":
            return f"{PACKET}.lookahead<{print_type(e.lookahead.type)}>()"
        case _:
            raise PrintError("expression has no kind")


def _operand(e: pb.Expr) -> str:
    text = print_expr(e)
    return text if e.WhichOneof("kind") in _ATOMS else f"({text})"


def print_lvalue(lv: pb.LValue) -> str:
    match lv.WhichOneof("kind"):
        case "var":
            return lv.var
        case "member":
            return f"{print_lvalue(lv.member.base)}.{lv.member.field}"
        case "index":
            return f"{print_lvalue(lv.index.base)}[{print_expr(lv.index.index)}]"
        case "next":
            return f"{print_lvalue(lv.next.stack)}.next"
        case _:
            raise PrintError("lvalue has no kind")


def _print_arg(arg: pb.Arg) -> str:
    match arg.WhichOneof("kind"):
        case "expr":
            return print_expr(arg.expr)
        case "lvalue":
            return print_lvalue(arg.lvalue)
        case _:
            raise PrintError("argument has no kind")


def _print_args(args: Iterable[pb.Arg]) -> str:
    return ", ".join(_print_arg(a) for a in args)


def _print_action_call(call: pb.ActionCall) -> str:
    return f"{call.action}({', '.join(print_literal(a) for a in call.args)})"


# ---------------------------------------------------------------------------
# The v1model shim
# ---------------------------------------------------------------------------


def standard_metadata_binding(
    index: ir.Index, meta: str, role: str = "control"
) -> tuple[list[str], list[str]]:
    """The v1model shim: the metadata contract mapped onto `standard_metadata`.

    This is the whole architecture binding. The IR's blocks read and write
    fields of their metadata struct M and perform no effect; v1model
    expresses the same decisions through `standard_metadata`. The mapping is
    by field name, each field optional (docs/design.md, "Metadata contract"):

    | M field        | type     | direction              | v1model                             |
    |----------------|----------|------------------------|-------------------------------------|
    | `ingress_port` | `bit<9>` | provided, parser start | `M.ingress_port = sm.ingress_port;` |
    | `parser_error` | `error`  | provided, control      | `M.parser_error = sm.parser_error;` |
    | `egress_port`  | `bit<9>` | consumed               | `sm.egress_spec = M.egress_port;`   |
    | `drop`         | `bool`   | consumed               | `if (M.drop) { mark_to_drop(sm); }` |

    The architectures write `ingress_port` before the parser runs, so the
    shim copies it in at the top of the parser's start state, and again at
    the start of the ingress control's `apply`, where it still holds the
    same value; `parser_error` is set after the parser, so only the control
    copies it. Consumed fields are acted on at the end of the control's
    `apply`, drop last so that it wins over the egress port. `flood` has no
    v1model mapping and is left to the architectures. Any other field of M
    is plain user metadata.

    Returns the prologue and epilogue statements of the block exported as
    `role`, "parser" or "control", `meta` being that block's name for its M
    parameter; a parser's epilogue is empty. A contract field with the wrong
    type is a `PrintError`, since the architectures would refuse it too.
    """
    if role not in ("parser", "control"):
        raise PrintError(f"no standard_metadata binding for role {role!r}")
    fields = {f.name: f.type for f in index.fields(index.program.metadata)}

    def has(name: str, expected: pb.Type) -> bool:
        actual = fields.get(name)
        if actual is None:
            return False
        if actual != expected:
            raise PrintError(
                f"metadata field {name!r} is {print_type(actual)}, "
                f"the contract needs {print_type(expected)}"
            )
        return True

    prologue: list[str] = []
    epilogue: list[str] = []
    sm = STANDARD_METADATA
    control = role == "control"
    if has("ingress_port", pb.Type(bits=9)):
        prologue.append(f"{meta}.ingress_port = {sm}.ingress_port;")
    if has("parser_error", pb.Type(error=pb.ErrorType())) and control:
        prologue.append(f"{meta}.parser_error = {sm}.parser_error;")
    if has("egress_port", pb.Type(bits=9)) and control:
        epilogue.append(f"{sm}.egress_spec = {meta}.egress_port;")
    if has("drop", pb.Type(boolean=pb.BoolType())) and control:
        epilogue.append(f"if ({meta}.drop) {{ mark_to_drop({sm}); }}")
    return prologue, epilogue


# The extern families the shim knows, by ExternType name. Each matches an
# implementation under python/p4blo/externs/.
REGISTER = "register"
COUNTER = "counter"
CHECKSUM16 = "checksum16"
CRC_WIDTHS = {"crc16": 16, "crc32": 32}


def _crc_width(decl: pb.ExternType) -> int:
    width = CRC_WIDTHS[ir.extern_family(decl.name)]
    if decl.constructor_params or len(decl.methods) != 1:
        raise PrintError(f"{decl.name}: CRC declaration has the wrong shape")
    method = decl.methods[0]
    if (
        method.name != "compute"
        or len(method.params) != 1
        or method.params[0].direction != pb.DIRECTION_IN
        or method.params[0].type.WhichOneof("kind") != "bits"
        or method.returns.WhichOneof("kind") != "bits"
        or method.returns.bits != width
    ):
        raise PrintError(f"{decl.name}: CRC declaration has the wrong shape")
    data_width = method.params[0].type.bits
    if data_width == 0 or data_width % 8:
        raise PrintError(f"{decl.name}: data width must be a positive multiple of 8")
    return width


def _instance_size(instance: pb.ExternInstance) -> str:
    if not instance.args or instance.args[0].WhichOneof("value") != "bits":
        raise PrintError(f"extern instance {instance.name!r} has no size argument")
    return print_literal(instance.args[0])


def _print_extern_instance(index: ir.Index, instance: pb.ExternInstance) -> str | None:
    """The v1model instantiation of an extern instance, or None when the
    family has no instance in v1model (checksum16 is a function there)."""
    extern_type = index.extern_types[instance.extern_type]
    family = ir.extern_family(extern_type.name)
    if family == REGISTER:
        # The value width is the width of read's out parameter.
        read = next((m for m in extern_type.methods if m.name == "read"), None)
        if read is None or not read.params:
            raise PrintError(f"extern type {extern_type.name!r} has no read method")
        value_type = print_type(read.params[0].type)
        return f"register<{value_type}>({_instance_size(instance)}) {instance.name};"
    if family == COUNTER:
        return f"counter({_instance_size(instance)}, CounterType.packets) {instance.name};"
    if family == CHECKSUM16:
        return None
    if family in CRC_WIDTHS:
        _crc_width(extern_type)
        if instance.args:
            raise PrintError(f"{family}: constructor takes no arguments")
        return None
    raise PrintError(f"no v1model form for extern type {extern_type.name!r}")


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


def print_stmt(stmt: pb.Stmt, *, index: ir.Index | None = None, depth: int = 0) -> str:
    """A statement, possibly several lines, indented `depth` levels.

    Without an index an extern call prints as a plain method call; with one
    the extern families print in their v1model form.
    """
    return "\n".join(_StmtPrinter(index).lines(stmt, depth))


@dataclass
class _StmtPrinter:
    index: ir.Index | None

    def block(self, stmts: Iterable[pb.Stmt], depth: int) -> list[str]:
        return [line for s in stmts for line in self.lines(s, depth)]

    def lines(self, stmt: pb.Stmt, depth: int) -> list[str]:
        pad = INDENT * depth
        match stmt.WhichOneof("kind"):
            case "assign":
                a = stmt.assign
                return [f"{pad}{print_lvalue(a.target)} = {print_expr(a.value)};"]
            case "conditional":
                return self._conditional(stmt.conditional, depth)
            case "apply":
                a = stmt.apply
                call = f"{a.table}.apply()"
                if a.HasField("hit"):
                    return [f"{pad}{print_lvalue(a.hit)} = {call}.hit;"]
                return [f"{pad}{call};"]
            case "call_action":
                c = stmt.call_action
                return [f"{pad}{c.action}({_print_args(c.args)});"]
            case "call_block":
                c = stmt.call_block
                args = _print_args(c.args)
                if self._callee_takes_packet(c.block):
                    args = f"{PACKET}, {args}" if args else PACKET
                return [f"{pad}{_instance_name(c.block)}.apply({args});"]
            case "call_extern":
                return [f"{pad}{self._call_extern(stmt.call_extern)}"]
            case "set_valid":
                return [f"{pad}{print_lvalue(stmt.set_valid.header)}.setValid();"]
            case "set_invalid":
                return [f"{pad}{print_lvalue(stmt.set_invalid.header)}.setInvalid();"]
            case "push":
                p = stmt.push
                return [f"{pad}{print_lvalue(p.stack)}.push_front({p.count});"]
            case "pop":
                p = stmt.pop
                return [f"{pad}{print_lvalue(p.stack)}.pop_front({p.count});"]
            case "extract":
                return [f"{pad}{PACKET}.extract({print_lvalue(stmt.extract.target)});"]
            case "advance":
                return [f"{pad}{PACKET}.advance({print_expr(stmt.advance.bits)});"]
            case "verify":
                v = stmt.verify
                return [f"{pad}verify({print_expr(v.condition)}, error.{v.error});"]
            case "emit":
                return [f"{pad}{PACKET}.emit({print_expr(stmt.emit.value)});"]
            case _:
                raise PrintError("statement has no kind")

    def _conditional(self, c: pb.If, depth: int) -> list[str]:
        pad = INDENT * depth
        lines = [f"{pad}if ({print_expr(c.condition)}) {{"]
        lines += self.block(c.then, depth + 1)
        if c.otherwise:
            lines.append(f"{pad}}} else {{")
            lines += self.block(c.otherwise, depth + 1)
        lines.append(f"{pad}}}")
        return lines

    def _callee_takes_packet(self, block: str) -> bool:
        if self.index is None:
            return False
        return self.index.blocks[block].kind != pb.BLOCK_KIND_CONTROL

    def _call_extern(self, call: pb.CallExtern) -> str:
        family = None
        if self.index is not None:
            instance = self.index.extern_instances[call.instance]
            family = ir.extern_family(self.index.extern_types[instance.extern_type].name)
        if family == CHECKSUM16:
            return self._checksum(call)
        if family in CRC_WIDTHS:
            assert self.index is not None
            instance = self.index.extern_instances[call.instance]
            width = _crc_width(self.index.extern_types[instance.extern_type])
            if call.method != "compute" or len(call.args) != 1 or not call.HasField("result"):
                raise PrintError(f"{family} call {call.instance}.{call.method} has the wrong shape")
            return (
                f"hash({print_lvalue(call.result)}, HashAlgorithm.{family}, "
                f"{width}w0, {{ {_print_arg(call.args[0])} }}, 64w{1 << width});"
            )
        method = f"{call.instance}.{call.method}({_print_args(call.args)})"
        if call.HasField("result"):
            return f"{print_lvalue(call.result)} = {method};"
        return f"{method};"

    @staticmethod
    def _checksum(call: pb.CallExtern) -> str:
        # v1model has no checksum extern object; its `hash` with
        # HashAlgorithm.csum16, base 0 and max 2^16 is the one's-complement
        # checksum of the data, which is what checksum16.compute returns.
        # That this agrees with python/p4blo/externs/checksum.py is verified
        # against the oracle in step 4 (docs/design.md, "Build order").
        if call.method != "compute" or len(call.args) != 1 or not call.HasField("result"):
            raise PrintError(f"checksum16 call {call.instance}.{call.method} has the wrong shape")
        result = print_lvalue(call.result)
        data = _print_arg(call.args[0])
        return f"hash({result}, HashAlgorithm.csum16, 16w0, {{ {data} }}, 32w65536);"


def _instance_name(block: str) -> str:
    """The name of a sub-block's instantiation in its caller."""
    return f"{block}_inst"


def _walk(stmts: Iterable[pb.Stmt]) -> Iterator[pb.Stmt]:
    """Every statement in `stmts`, recursively through conditionals."""
    for s in stmts:
        yield s
        if s.WhichOneof("kind") == "conditional":
            yield from _walk(s.conditional.then)
            yield from _walk(s.conditional.otherwise)


def _block_stmts(block: pb.Block) -> Iterator[pb.Stmt]:
    yield from _walk(block.body)
    for state in block.states:
        yield from _walk(state.body)
    for action in block.actions:
        yield from _walk(action.body)


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------


def print_program(program: pb.Program, *, index: ir.Index | None = None) -> str:
    """The complete P4-16 program for v1model, as text."""
    if index is None:
        index = ir.Index.build(program)
    return _ProgramPrinter(index).render()


@dataclass
class _ProgramPrinter:
    index: ir.Index
    out: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.p = self.index.program
        self.stmts = _StmtPrinter(self.index)
        self.roles = {e.role: e.block for e in self.p.exports}
        self.exported = set(self.roles.values())
        self.top_level_externs, self.block_externs = self._place_externs()

    # -- output helpers

    def line(self, depth: int, text: str = "") -> None:
        self.out.append(f"{INDENT * depth}{text}" if text else "")

    def lines(self, lines: Iterable[str]) -> None:
        self.out.extend(lines)

    def render(self) -> str:
        p = self.p
        self.line(0, f"// {p.name}: printed by p4blo for v1model. Do not edit.")
        self.line(0, "#include <core.p4>")
        self.line(0, "#include <v1model.p4>")
        self.errors()
        for enum in p.enum_types:
            self.enum(enum)
        for header in p.header_types:
            self.header(header)
        for struct in p.struct_types:
            self.struct(struct)
        if self.top_level_externs:
            self.line(0)
            for name in self.top_level_externs:
                decl = _print_extern_instance(self.index, self.index.extern_instances[name])
                if decl is not None:
                    self.line(0, decl)
        for block in self._block_order():
            self.block(block)
        self.missing_roles()
        self.shim_controls()
        self.main()
        return "\n".join(self.out) + "\n"

    # -- declarations

    def errors(self) -> None:
        extra = [e for e in self.p.errors if e not in ir.CORE_ERRORS]
        if extra:
            self.line(0)
            self.line(0, f"error {{ {', '.join(extra)} }}")

    def enum(self, enum: pb.EnumType) -> None:
        self.line(0)
        self.line(0, f"enum {enum.name} {{ {', '.join(enum.members)} }}")

    def header(self, header: pb.HeaderType) -> None:
        self._fields("header", header.name, header.fields)

    def struct(self, struct: pb.StructType) -> None:
        self._fields("struct", struct.name, struct.fields)

    def _fields(self, keyword: str, name: str, fields: Iterable[pb.Field]) -> None:
        self.line(0)
        self.line(0, f"{keyword} {name} {{")
        for f in fields:
            self.line(1, f"{print_type(f.type)} {f.name};")
        self.line(0, "}")

    # -- externs

    def _place_externs(self) -> tuple[list[str], dict[str, list[str]]]:
        """Where each extern instance is instantiated.

        Inside the one block that uses it when that block is exported, and
        so instantiated exactly once by V1Switch; at top level otherwise,
        which keeps one piece of state per IR instance however many times a
        sub-block is instantiated. v1model allows both for register and
        counter.
        """
        users: dict[str, list[str]] = {name: [] for name in self.index.extern_instances}
        for block in self.p.blocks:
            seen: set[str] = set()
            for stmt in _block_stmts(block):
                if stmt.WhichOneof("kind") == "call_extern":
                    seen.add(stmt.call_extern.instance)
            for name in seen:
                users[name].append(block.name)
        top: list[str] = []
        per_block: dict[str, list[str]] = {b.name: [] for b in self.p.blocks}
        for name, blocks in users.items():
            if len(blocks) == 1 and blocks[0] in self.exported:
                per_block[blocks[0]].append(name)
            else:
                top.append(name)
        return top, per_block

    # -- blocks

    def _block_order(self) -> list[pb.Block]:
        """Program order, except that a callee precedes its callers."""
        order: list[pb.Block] = []
        seen: set[str] = set()

        def visit(block: pb.Block) -> None:
            if block.name in seen:
                return
            seen.add(block.name)
            callees = {
                s.call_block.block
                for s in _block_stmts(block)
                if s.WhichOneof("kind") == "call_block"
            }
            for other in self.p.blocks:
                if other.name in callees:
                    visit(other)
            order.append(block)

        for block in self.p.blocks:
            visit(block)
        return order

    def _role(self, block: pb.Block) -> str | None:
        for role, name in self.roles.items():
            if name == block.name:
                return role
        return None

    def _signature(self, block: pb.Block) -> str:
        """The parameter list: the role's v1model signature for an exported
        block, the block's own parameters otherwise, with the packet first
        for parsers and deparsers."""
        params = [_print_param(p) for p in block.params]
        match self._role(block):
            case "parser":
                self._expect_params(block, [pb.DIRECTION_OUT, pb.DIRECTION_INOUT])
                params = [f"packet_in {PACKET}", *params, _sm_param()]
            case "control":
                self._expect_params(block, [pb.DIRECTION_INOUT, pb.DIRECTION_INOUT])
                params = [*params, _sm_param()]
            case "deparser":
                self._expect_params(block, [pb.DIRECTION_IN])
                params = [f"packet_out {PACKET}", *params]
            case None:
                if block.kind == pb.BLOCK_KIND_PARSER:
                    params = [f"packet_in {PACKET}", *params]
                elif block.kind == pb.BLOCK_KIND_DEPARSER:
                    params = [f"packet_out {PACKET}", *params]
            case role:
                raise PrintError(f"unknown export role {role!r}")
        return ", ".join(params)

    @staticmethod
    def _expect_params(block: pb.Block, directions: list[int]) -> None:
        if [p.direction for p in block.params] != directions:
            raise PrintError(f"block {block.name!r} does not have its role's signature")

    def block(self, block: pb.Block) -> None:
        keyword = "parser" if block.kind == pb.BLOCK_KIND_PARSER else "control"
        self.line(0)
        self.line(0, f"{keyword} {block.name}({self._signature(block)}) {{")
        for name in self.block_externs[block.name]:
            decl = _print_extern_instance(self.index, self.index.extern_instances[name])
            if decl is not None:
                self.line(1, decl)
        for callee in self._callees_in_order(block):
            self.line(1, f"{callee}() {_instance_name(callee)};")
        for local in block.locals:
            self.line(1, self._local(local))
        if block.kind == pb.BLOCK_KIND_PARSER:
            self.states(block)
        else:
            for action in block.actions:
                self.action(action)
            for table in block.tables:
                self.table(table, block)
            self.apply(block)
        self.line(0, "}")

    def _callees_in_order(self, block: pb.Block) -> list[str]:
        callees: list[str] = []
        for s in _block_stmts(block):
            if s.WhichOneof("kind") == "call_block" and s.call_block.block not in callees:
                callees.append(s.call_block.block)
        return callees

    def _local(self, local: pb.Var) -> str:
        decl = f"{print_type(local.type)} {local.name}"
        init = self._zero(local.type)
        return f"{decl} = {init};" if init is not None else f"{decl};"

    def _zero(self, t: pb.Type) -> str | None:
        """The zero value of a scalar type, as docs/ir-semantics.md defines it;
        None for a compound type, which P4 cannot initialize inline."""
        match t.WhichOneof("kind"):
            case "bits":
                return _bits(t.bits, 0)
            case "boolean":
                return "false"
            case "enum_type":
                members = self.index.enum_types[t.enum_type].members
                return f"{t.enum_type}.{members[0]}" if members else None
            case "error":
                return "error.NoError"
            case _:
                return None

    # -- parsers

    def states(self, block: pb.Block) -> None:
        """The states, the shim's prologue first in the exported parser's
        start state (the synthesized one when the IR's start state is not
        named `start`). A loop back into the start state re-runs the copy,
        which is harmless: nothing in between changes `standard_metadata`."""
        prologue: list[str] = []
        if self._role(block) == "parser":
            prologue, _ = standard_metadata_binding(self.index, block.params[1].name, "parser")
        names = {s.name for s in block.states}
        if block.start_state != "start":
            if "start" in names:
                raise PrintError(
                    f"parser {block.name!r} starts at {block.start_state!r} "
                    "but also has a state named 'start'"
                )
            self.line(1, "state start {")
            for s in prologue:
                self.line(2, s)
            self.line(2, f"transition {block.start_state};")
            self.line(1, "}")
            prologue = []
        for state in block.states:
            self.state(state, prologue if state.name == block.start_state else [])

    def state(self, state: pb.State, prologue: Iterable[str] = ()) -> None:
        self.line(1, f"state {state.name} {{")
        for s in prologue:
            self.line(2, s)
        self.lines(self.stmts.block(state.body, 2))
        self.transition(state.transition)
        self.line(1, "}")

    def transition(self, t: pb.Transition) -> None:
        match t.WhichOneof("kind"):
            case "direct":
                self.line(2, f"transition {_print_target(t.direct)};")
            case "select":
                self.select(t.select)
            case _:
                raise PrintError("transition has no kind")

    def select(self, select: pb.Select) -> None:
        keys = ", ".join(print_expr(k) for k in select.keys)
        self.line(2, f"transition select({keys}) {{")
        for case in select.cases:
            self.line(3, f"{_print_key_sets(case.sets)}: {_print_target(case.target)};")
        self.line(2, "}")

    # -- controls

    def action(self, action: pb.Action) -> None:
        if action.name == "NoAction":
            # core.p4 declares it; redeclaring it would clash. The IR has no
            # implicit declarations, so a program's NoAction is an ordinary
            # action that runs whatever body it has; only the one core.p4
            # means can be elided (the validator's NOACTION_RESERVED).
            if action.body or action.params:
                raise PrintError("NoAction with a body or parameters cannot be printed for core.p4")
            return
        params = ", ".join(_print_param(p) for p in action.params)
        self.line(1, f"action {action.name}({params}) {{")
        self.lines(self.stmts.block(action.body, 2))
        self.line(1, "}")

    def table(self, table: pb.Table, block: pb.Block) -> None:
        self.line(1, f"table {table.name} {{")
        if table.keys:
            self.line(2, "key = {")
            for key in table.keys:
                self.line(3, _print_key(key))
            self.line(2, "}")
        default = (
            _print_action_call(table.default_action)
            if table.HasField("default_action")
            else "NoAction()"
        )
        actions = list(table.actions)
        if not table.HasField("default_action") and "NoAction" not in actions:
            # p4c requires the default action to be in the list.
            actions.append("NoAction")
        self.line(2, "actions = {")
        for name in actions:
            self.line(3, f"{name};")
        self.line(2, "}")
        const = "const " if table.const_default_action else ""
        self.line(2, f"{const}default_action = {default};")
        if table.const_entries:
            self.entries(table, block)
        if table.size:
            self.line(2, f"size = {table.size};")
        self.line(1, "}")

    def entries(self, table: pb.Table, block: pb.Block) -> None:
        widths = [self._key_width(key, block) for key in table.keys]
        ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in table.keys)
        entries = list(table.const_entries)
        if ternary:
            # p4c refuses priorities on const entries; the mutable form with
            # largest_priority_wins says the same thing, and p4c warns unless
            # the list is in descending priority order.
            entries.sort(key=lambda e: -e.priority)
            self.line(2, "entries = {")
        else:
            self.line(2, "const entries = {")
        for entry in entries:
            values = [
                _print_key_value(v, k.match_kind, w)
                for v, k, w in zip(entry.keys, table.keys, widths, strict=True)
            ]
            keys = values[0] if len(values) == 1 else f"({', '.join(values)})"
            priority = f"priority = {entry.priority}: " if ternary else ""
            self.line(3, f"{priority}{keys} : {_print_action_call(entry.action)};")
        self.line(2, "}")
        if ternary:
            self.line(2, "largest_priority_wins = true;")

    def _key_width(self, key: pb.Key, block: pb.Block) -> int:
        t = _Typer(self.index, self.index.scopes[block.name]).type_of(key.expr)
        if t.WhichOneof("kind") != "bits":
            raise PrintError(
                f"table key {print_expr(key.expr)} is {print_type(t)}; entries need a bit<N> key"
            )
        return t.bits

    def apply(self, block: pb.Block) -> None:
        prologue: list[str] = []
        epilogue: list[str] = []
        if self._role(block) == "control":
            prologue, epilogue = standard_metadata_binding(self.index, block.params[1].name)
        self.line(1, "apply {")
        for s in prologue:
            self.line(2, s)
        self.lines(self.stmts.block(block.body, 2))
        for s in epilogue:
            self.line(2, s)
        self.line(1, "}")

    # -- the shim's own blocks

    def missing_roles(self) -> None:
        h, m = self.p.headers, self.p.metadata
        for role, name in MISSING_ROLE_NAMES.items():
            if role in self.roles:
                continue
            if name in self.index.program_names:
                raise PrintError(f"no block exported as {role!r} and the name {name!r} is taken")
            self.line(0)
            match role:
                case "parser":
                    params = f"packet_in {PACKET}, out {h} hdr, inout {m} meta, {_sm_param()}"
                    self.line(0, f"parser {name}({params}) {{")
                    self.line(1, "state start {")
                    self.line(2, "transition accept;")
                    self.line(1, "}")
                case "control":
                    params = f"inout {h} hdr, inout {m} meta, {_sm_param()}"
                    self.line(0, f"control {name}({params}) {{")
                    self.line(1, "apply {")
                    self.line(1, "}")
                case _:
                    self.line(0, f"control {name}(packet_out {PACKET}, in {h} hdr) {{")
                    self.line(1, "apply {")
                    self.line(1, "}")
            self.line(0, "}")

    def shim_controls(self) -> None:
        h, m = self.p.headers, self.p.metadata
        checksum_params = f"inout {h} hdr, inout {m} meta"
        egress_params = f"{checksum_params}, {_sm_param()}"
        for name, params in [
            (VERIFY_CHECKSUM, checksum_params),
            (EGRESS, egress_params),
            (COMPUTE_CHECKSUM, checksum_params),
        ]:
            if name in self.index.program_names:
                raise PrintError(f"the shim needs the name {name!r}, which the program uses")
            self.line(0)
            self.line(0, f"control {name}({params}) {{")
            self.line(1, "apply {")
            self.line(1, "}")
            self.line(0, "}")

    def main(self) -> None:
        def block(role: str) -> str:
            return self.roles.get(role, MISSING_ROLE_NAMES[role])

        parts = [
            block("parser"),
            VERIFY_CHECKSUM,
            block("control"),
            EGRESS,
            COMPUTE_CHECKSUM,
            block("deparser"),
        ]
        self.line(0)
        self.line(0, f"V1Switch({', '.join(f'{p}()' for p in parts)}) main;")


# ---------------------------------------------------------------------------
# Pieces of declarations
# ---------------------------------------------------------------------------

_DIRECTIONS: dict[int, str] = {
    pb.DIRECTION_NONE: "",
    pb.DIRECTION_IN: "in ",
    pb.DIRECTION_OUT: "out ",
    pb.DIRECTION_INOUT: "inout ",
}


def _print_param(param: pb.Param) -> str:
    direction = _DIRECTIONS.get(param.direction)
    if direction is None:
        raise PrintError(f"parameter {param.name!r} has no direction")
    return f"{direction}{print_type(param.type)} {param.name}"


def _sm_param() -> str:
    return f"inout standard_metadata_t {STANDARD_METADATA}"


def _print_target(target: pb.Target) -> str:
    match target.WhichOneof("kind"):
        case "state":
            return target.state
        case "accept":
            return "accept"
        case "reject":
            return "reject"
        case _:
            raise PrintError("transition target has no kind")


def _print_key_set(ks: pb.KeySet) -> str:
    match ks.WhichOneof("kind"):
        case "exact":
            return print_literal(ks.exact)
        case "masked":
            return f"{print_literal(ks.masked.value)} &&& {print_literal(ks.masked.mask)}"
        case "range":
            return f"{print_literal(ks.range.lo)}..{print_literal(ks.range.hi)}"
        case "dont_care":
            return "_"
        case _:
            raise PrintError("key set has no kind")


def _print_key_sets(sets: Iterable[pb.KeySet]) -> str:
    sets = list(sets)
    if all(s.WhichOneof("kind") == "dont_care" for s in sets):
        return "default"
    if len(sets) == 1:
        return _print_key_set(sets[0])
    return f"({', '.join(_print_key_set(s) for s in sets)})"


_MATCH_KINDS: dict[int, str] = {
    pb.MATCH_KIND_EXACT: "exact",
    pb.MATCH_KIND_LPM: "lpm",
    pb.MATCH_KIND_TERNARY: "ternary",
}


def _print_key(key: pb.Key) -> str:
    kind = _MATCH_KINDS.get(key.match_kind)
    if kind is None:
        raise PrintError("table key has no match kind")
    expr = print_expr(key.expr)
    text = f"{expr}: {kind}"
    if key.name and key.name != expr:
        text += f' @name("{key.name}")'
    return f"{text};"


def _print_key_value(value: pb.KeyValue, match_kind: int, width: int) -> str:
    match value.WhichOneof("kind"):
        case "exact":
            return _bits(width, int(value.exact))
        case "lpm":
            prefix = value.lpm.prefix_len
            if prefix > width:
                raise PrintError(f"prefix length {prefix} exceeds key width {width}")
            mask = ((1 << prefix) - 1) << (width - prefix)
            return f"{_bits(width, int(value.lpm.value))} &&& {_bits(width, mask)}"
        case "ternary":
            t = value.ternary
            return f"{_bits(width, int(t.value))} &&& {_bits(width, int(t.mask))}"
        case _:
            raise PrintError("entry key value has no kind")


# ---------------------------------------------------------------------------
# Types of expressions, for what the text needs a width for
# ---------------------------------------------------------------------------


@dataclass
class _Typer:
    """The type of an expression in a block scope.

    Only what the printer needs: the width of a table key, so that LPM
    prefixes become masks and entry values carry their width. The validator
    owns typechecking; this trusts a valid program.
    """

    index: ir.Index
    scope: ir.BlockScope
    action: str | None = None

    def type_of(self, e: pb.Expr) -> pb.Type:
        match e.WhichOneof("kind"):
            case "literal":
                return self._literal(e.literal)
            case "var":
                return self.scope.var(e.var, self.action).type
            case "member":
                base = self.type_of(e.member.base)
                for f in self.index.fields(_type_name(base)):
                    if f.name == e.member.field:
                        return f.type
                raise PrintError(f"no field {e.member.field!r} in {print_type(base)}")
            case "index":
                base = self.type_of(e.index.base)
                if base.WhichOneof("kind") != "stack":
                    raise PrintError(f"indexing a {print_type(base)}")
                return pb.Type(header=base.stack.header)
            case "last_index":
                return pb.Type(bits=32)
            case "unary":
                return self.type_of(e.unary.operand)
            case "binary":
                return self._binary(e.binary)
            case "cast":
                return e.cast.to
            case "slice":
                return pb.Type(bits=e.slice.hi - e.slice.lo + 1)
            case "is_valid":
                return pb.Type(boolean=pb.BoolType())
            case "mux":
                return self.type_of(e.mux.then)
            case "lookahead":
                return e.lookahead.type
            case _:
                raise PrintError("expression has no kind")

    def _literal(self, lit: pb.Literal) -> pb.Type:
        match lit.WhichOneof("value"):
            case "bits":
                return pb.Type(bits=lit.bits.width)
            case "boolean":
                return pb.Type(boolean=pb.BoolType())
            case "enum_member":
                return pb.Type(enum_type=lit.enum_member.enum_type)
            case "error":
                return pb.Type(error=pb.ErrorType())
            case _:
                raise PrintError("literal has no value")

    def _binary(self, b: pb.Binary) -> pb.Type:
        if b.op == pb.BINARY_OP_CONCAT:
            left, right = self.type_of(b.left), self.type_of(b.right)
            return pb.Type(bits=left.bits + right.bits)
        if b.op in (
            pb.BINARY_OP_EQ,
            pb.BINARY_OP_NE,
            pb.BINARY_OP_LT,
            pb.BINARY_OP_LE,
            pb.BINARY_OP_GT,
            pb.BINARY_OP_GE,
            pb.BINARY_OP_AND,
            pb.BINARY_OP_OR,
        ):
            return pb.Type(boolean=pb.BoolType())
        return self.type_of(b.left)


def _type_name(t: pb.Type) -> str:
    match t.WhichOneof("kind"):
        case "header":
            return t.header
        case "struct":
            return t.struct
        case _:
            raise PrintError(f"{print_type(t)} has no fields")
