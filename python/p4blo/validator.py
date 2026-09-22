"""The validator: everything the schema cannot express.

`validate` returns every problem it finds as a `Diagnostic`; `check` raises
`ValidationError` on a non-empty list and otherwise hands back the `ir.Index`
the interpreter and the printer build on. The rules are the contract stated
in the header of proto/p4blo/v0/p4blo.proto, made executable, so this module
is meant to be read as that contract's fine print: one function per
declaration, statement and expression kind, in the order of the schema.

Every diagnostic carries a protobuf-style path to the offending element, for
example `blocks[1].states[2].transition.select.cases[0].sets[1]`.

Codes
-----
Structure and names
  NAME_EMPTY          a declaration, field, member, method or key has no name
  NAME_DUPLICATE      two names collide in one namespace (Index.build stops here)
  ERROR_LIST          Program.errors does not begin with core.p4's errors in order
  REF_UNRESOLVED      a reference names no declaration, field, member, method or error
  REF_KIND            a reference names a declaration of the wrong kind
  SCOPE_VAR           a variable that exists is not visible from here
  SCOPE_DECL          an action, table or state of another block is used here
  EXPORT_DUPLICATE    two exports share a role
  EXPORT_SIGNATURE    an exported block lacks the signature of its kind
Types and literals
  TYPE_INVALID        a malformed Type: no kind, bit<0>, an empty stack or enum,
                      a non-scalar header field, a struct that contains itself
  LITERAL_FORMAT      a literal with no value, or a bits value that is not decimal
  LITERAL_RANGE       a bits literal of width 0 or with a value >= 2^width
Blocks
  BLOCK_KIND_SHAPE    a block without a kind, or with the states, body,
                      start_state, actions or tables of another kind
  PARSER_START_STATE  a parser's start_state is not one of its states
  BLOCK_KIND_STMT     a statement in a block kind that does not allow it
  PARSER_ONLY         lookahead outside a parser
  NEXT_ONLY_EXTRACT   stack.next anywhere but as the target of an extract
  PARAM_DIRECTION     a parameter direction its owner does not allow
Expressions, lvalues and statements
  EXPR_INVALID        an expression or lvalue with no kind, or an unspecified operator
  STMT_INVALID        a statement with no kind
  TYPE_MISMATCH       an operand, condition, target or value of the wrong type
  CAST_INVALID        a cast the IR does not allow
  SLICE_RANGE         a slice with lo > hi or hi >= width
  LVALUE_READONLY     a write to an `in` or directionless parameter
  STACK_COUNT         push or pop with count 0
  ARG_COUNT           a call with the wrong number of arguments
  ARG_DIRECTION       an argument's form (in expr / out lvalue) against its param
  ARG_TYPE            an argument's type against its param
  CALL_KIND           a block calling a block of another kind
  CALL_ALIAS          two arguments of one call that may alias (see check_args)
  CALL_CYCLE          a cycle in the block call graph, or among one block's actions
  EXTERN_RESULT       a result lvalue missing, unexpected or of the wrong type
Parsers
  PARSER_TRANSITION   a state without a transition, or a target without a kind
  SELECT_ARITY        a select without keys, or a case with the wrong set count
  SELECT_TYPE         a select key or key set of the wrong type
Tables and entries
  KEY_NAME            two keys of one table share a name
  KEY_TYPE            a match kind on a type it does not apply to
  TABLE_LPM_COUNT     more than one lpm key
  TABLE_KEY_MIX       lpm and ternary keys in one table
  TABLE_ACTIONS       an empty or repeated action list, or a call to an action not in it
  NOACTION_RESERVED   an action named NoAction with a body or parameters
  ACTION_ARGS         action data against the action's params
  ENTRY_SHAPE         key values that do not line up with the keys
  ENTRY_RANGE         a value, prefix length or mask that does not fit its key
  ENTRY_PRIORITY      a priority on a non-ternary table, or two overlapping
                      const entries of a ternary table with one priority
  ENTRY_DUPLICATE     two const entries of a non-ternary table with the same keys
Externs
  EXTERN_ARGS         constructor arguments against the extern type
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import cast

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb

NAME_EMPTY = "NAME_EMPTY"
NAME_DUPLICATE = "NAME_DUPLICATE"
ERROR_LIST = "ERROR_LIST"
REF_UNRESOLVED = "REF_UNRESOLVED"
REF_KIND = "REF_KIND"
SCOPE_VAR = "SCOPE_VAR"
SCOPE_DECL = "SCOPE_DECL"
EXPORT_DUPLICATE = "EXPORT_DUPLICATE"
EXPORT_SIGNATURE = "EXPORT_SIGNATURE"
TYPE_INVALID = "TYPE_INVALID"
LITERAL_FORMAT = "LITERAL_FORMAT"
LITERAL_RANGE = "LITERAL_RANGE"
BLOCK_KIND_SHAPE = "BLOCK_KIND_SHAPE"
PARSER_START_STATE = "PARSER_START_STATE"
BLOCK_KIND_STMT = "BLOCK_KIND_STMT"
PARSER_ONLY = "PARSER_ONLY"
NEXT_ONLY_EXTRACT = "NEXT_ONLY_EXTRACT"
PARAM_DIRECTION = "PARAM_DIRECTION"
EXPR_INVALID = "EXPR_INVALID"
STMT_INVALID = "STMT_INVALID"
TYPE_MISMATCH = "TYPE_MISMATCH"
CAST_INVALID = "CAST_INVALID"
SLICE_RANGE = "SLICE_RANGE"
LVALUE_READONLY = "LVALUE_READONLY"
STACK_COUNT = "STACK_COUNT"
ARG_COUNT = "ARG_COUNT"
ARG_DIRECTION = "ARG_DIRECTION"
ARG_TYPE = "ARG_TYPE"
CALL_KIND = "CALL_KIND"
CALL_ALIAS = "CALL_ALIAS"
CALL_CYCLE = "CALL_CYCLE"
EXTERN_RESULT = "EXTERN_RESULT"
PARSER_TRANSITION = "PARSER_TRANSITION"
SELECT_ARITY = "SELECT_ARITY"
SELECT_TYPE = "SELECT_TYPE"
KEY_NAME = "KEY_NAME"
KEY_TYPE = "KEY_TYPE"
TABLE_LPM_COUNT = "TABLE_LPM_COUNT"
TABLE_KEY_MIX = "TABLE_KEY_MIX"
TABLE_ACTIONS = "TABLE_ACTIONS"
NOACTION_RESERVED = "NOACTION_RESERVED"
ACTION_ARGS = "ACTION_ARGS"
ENTRY_SHAPE = "ENTRY_SHAPE"
ENTRY_RANGE = "ENTRY_RANGE"
ENTRY_PRIORITY = "ENTRY_PRIORITY"
ENTRY_DUPLICATE = "ENTRY_DUPLICATE"
EXTERN_ARGS = "EXTERN_ARGS"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    path: str

    def __str__(self) -> str:
        return f"{self.path}: {self.code}: {self.message}"


class ValidationError(Exception):
    """`check` found at least one problem; `diagnostics` lists them all."""

    diagnostics: list[Diagnostic]

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("\n".join(str(d) for d in diagnostics))
        self.diagnostics = diagnostics


def validate(program: pb.Program) -> list[Diagnostic]:
    """Every problem found in `program`, in the order of the schema."""
    return _Validator(program).run()


def check(program: pb.Program) -> ir.Index:
    """The program's `ir.Index`, or `ValidationError` listing every problem."""
    validator = _Validator(program)
    diagnostics = validator.run()
    if diagnostics or validator.index is None:
        raise ValidationError(diagnostics)
    return validator.index


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


def bits_type(width: int) -> pb.Type:
    return pb.Type(bits=width)


BOOLEAN = pb.Type(boolean=pb.BoolType())
ERROR = pb.Type(error=pb.ErrorType())
BITS32 = bits_type(32)


def kind_of(t: pb.Type) -> str | None:
    return t.WhichOneof("kind")


def is_bits(t: pb.Type) -> bool:
    return kind_of(t) == "bits"


def is_bits32(t: pb.Type) -> bool:
    return is_bits(t) and t.bits == 32


def is_boolean(t: pb.Type) -> bool:
    return kind_of(t) == "boolean"


def is_header(t: pb.Type) -> bool:
    return kind_of(t) == "header"


def is_stack(t: pb.Type) -> bool:
    return kind_of(t) == "stack"


def same_type(a: pb.Type, b: pb.Type) -> bool:
    """Structural type equality: same kind, and the same width or name."""
    kind = kind_of(a)
    if kind is None or kind != kind_of(b):
        return False
    match kind:
        case "bits":
            return a.bits == b.bits
        case "boolean" | "error":
            return True
        case "header":
            return a.header == b.header
        case "struct":
            return a.struct == b.struct
        case "enum_type":
            return a.enum_type == b.enum_type
        case "stack":
            return a.stack.header == b.stack.header and a.stack.size == b.stack.size
        case _:
            return False


def describe(t: pb.Type | None) -> str:
    """A type as P4 would write it, for messages."""
    if t is None:
        return "<unknown>"
    match kind_of(t):
        case "bits":
            return f"bit<{t.bits}>"
        case "boolean":
            return "bool"
        case "header":
            return f"header {t.header}"
        case "struct":
            return f"struct {t.struct}"
        case "enum_type":
            return f"enum {t.enum_type}"
        case "error":
            return "error"
        case "stack":
            return f"{t.stack.header}[{t.stack.size}]"
        case _:
            return "<no kind>"


# Literal-typed: the types a literal or a select key can have. Table keys are
# bits only (docs/semantics.md, "Keys are bits").
_SCALAR_KINDS = frozenset({"bits", "boolean", "enum_type", "error"})

_DECIMAL = re.compile(r"[0-9]+")


def parse_decimal(text: str) -> int | None:
    return int(text) if _DECIMAL.fullmatch(text) else None


# ---------------------------------------------------------------------------
# Scopes and placement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scope:
    """Where a statement or expression stands: a block, and within it
    possibly an action. Variables visible here are the block's params and
    locals, plus the action's params inside an action body."""

    block: pb.Block
    path: str
    names: ir.BlockScope
    action: pb.Action | None = None

    def var(self, name: str) -> pb.Param | pb.Var | None:
        if self.action is not None:
            params = self.names.action_params[self.action.name]
            if name in params:
                return params[name]
        return self.names.vars.get(name)

    @property
    def in_parser(self) -> bool:
        return self.block.kind == pb.BLOCK_KIND_PARSER


_ANY_BLOCK_STMTS = frozenset(
    {
        "assign",
        "conditional",
        "call_block",
        "call_extern",
        "set_valid",
        "set_invalid",
        "push",
        "pop",
    }
)
# The table above `Stmt` in the schema, as data.
_STMTS_BY_KIND: dict[int, frozenset[str]] = {
    pb.BLOCK_KIND_PARSER: _ANY_BLOCK_STMTS | {"extract", "advance", "verify"},
    pb.BLOCK_KIND_CONTROL: _ANY_BLOCK_STMTS | {"apply", "call_action"},
    pb.BLOCK_KIND_DEPARSER: _ANY_BLOCK_STMTS | {"emit"},
}

_BLOCK_PARAM_DIRECTIONS = frozenset({pb.DIRECTION_IN, pb.DIRECTION_OUT, pb.DIRECTION_INOUT})
_ACTION_PARAM_DIRECTIONS = _BLOCK_PARAM_DIRECTIONS | {pb.DIRECTION_NONE}
_OUT_DIRECTIONS = frozenset({pb.DIRECTION_OUT, pb.DIRECTION_INOUT})

_DIRECTION_NAMES: dict[int, str] = {
    pb.DIRECTION_UNSPECIFIED: "unspecified",
    pb.DIRECTION_NONE: "directionless",
    pb.DIRECTION_IN: "in",
    pb.DIRECTION_OUT: "out",
    pb.DIRECTION_INOUT: "inout",
}

_KIND_NAMES = {
    pb.BLOCK_KIND_PARSER: "parser",
    pb.BLOCK_KIND_CONTROL: "control",
    pb.BLOCK_KIND_DEPARSER: "deparser",
}

# The signature an exported block must have, by kind: (direction, H or M).
_EXPORT_SIGNATURES: dict[int, tuple[tuple[int, str], ...]] = {
    pb.BLOCK_KIND_PARSER: ((pb.DIRECTION_OUT, "H"), (pb.DIRECTION_INOUT, "M")),
    pb.BLOCK_KIND_CONTROL: ((pb.DIRECTION_INOUT, "H"), (pb.DIRECTION_INOUT, "M")),
    pb.BLOCK_KIND_DEPARSER: ((pb.DIRECTION_IN, "H"),),
}


# A static description of the storage an lvalue or lvalue-shaped expression
# names: the variable, then one step per member (field name) or index (the
# literal index, or None when it is computed). Two accesses may alias when
# they agree on every step where both are known.
type Access = tuple[str | int | None, ...]


def may_alias(a: Access, b: Access) -> bool:
    for x, y in zip(a, b, strict=False):
        if x is not None and y is not None and x != y:
            return False
    return True


# ---------------------------------------------------------------------------
# Entry patterns, for the tie rules on const entries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExactPattern:
    value: int | str


@dataclass(frozen=True)
class LpmPattern:
    value: int
    prefix_len: int
    width: int

    @property
    def mask(self) -> int:
        return ((1 << self.prefix_len) - 1) << (self.width - self.prefix_len)


@dataclass(frozen=True)
class TernaryPattern:
    value: int
    mask: int


type KeyPattern = ExactPattern | LpmPattern | TernaryPattern


def patterns_overlap(a: KeyPattern, b: KeyPattern) -> bool:
    """Whether some key value matches both patterns."""
    match a, b:
        case ExactPattern(), ExactPattern():
            return a.value == b.value
        case LpmPattern(), LpmPattern():
            mask = a.mask & b.mask
            return a.value & mask == b.value & mask
        case TernaryPattern(), TernaryPattern():
            mask = a.mask & b.mask
            return a.value & mask == b.value & mask
        case _:
            return False


def patterns_equal(a: KeyPattern, b: KeyPattern) -> bool:
    """Whether two patterns match exactly the same key values."""
    match a, b:
        case LpmPattern(), LpmPattern():
            return a.prefix_len == b.prefix_len and a.value & a.mask == b.value & b.mask
        case TernaryPattern(), TernaryPattern():
            return a.mask == b.mask and a.value & a.mask == b.value & b.mask
        case _:
            return a == b


# ---------------------------------------------------------------------------
# The validator
# ---------------------------------------------------------------------------


@dataclass
class _Validator:
    program: pb.Program
    diagnostics: list[Diagnostic] = field(default_factory=list)
    index: ir.Index | None = None
    # The types of H and M once they are known to be structs.
    headers: pb.Type | None = None
    metadata: pb.Type | None = None
    block_paths: dict[str, str] = field(default_factory=dict)
    # Block call graph: caller name -> [(callee name, path of the call)].
    calls: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # The same for the actions of the block being checked, reset per block.
    action_calls: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def report(self, code: str, message: str, path: str) -> None:
        self.diagnostics.append(Diagnostic(code, message, path))

    @property
    def idx(self) -> ir.Index:
        assert self.index is not None
        return self.index

    def run(self) -> list[Diagnostic]:
        try:
            self.index = ir.Index.build(self.program)
        except ir.DuplicateName as e:
            message = str(e)
            code = NAME_EMPTY if "empty" in message or "''" in message else NAME_DUPLICATE
            self.report(code, message, "")
            return self.diagnostics
        self.check_errors()
        self.check_type_declarations()
        self.check_program_types()
        self.check_extern_types()
        self.check_extern_instances()
        for i, block in enumerate(self.program.blocks):
            self.block_paths[block.name] = f"blocks[{i}]"
        for i, block in enumerate(self.program.blocks):
            self.check_block(block, f"blocks[{i}]")
        self.check_exports()
        self.check_call_graph()
        return self.diagnostics

    # -- names and references -----------------------------------------------

    def check_names(self, names: Sequence[str], path: str, what: str) -> None:
        """Names unique and non-empty within one of the small namespaces the
        Index does not cover: fields, enum members, methods, method params."""
        seen: set[str] = set()
        for i, name in enumerate(names):
            if not name:
                self.report(NAME_EMPTY, f"{what} has no name", f"{path}[{i}]")
            elif name in seen:
                self.report(NAME_DUPLICATE, f"{what} {name!r} declared twice", f"{path}[{i}]")
            seen.add(name)

    def resolve[T](
        self, name: str, table: dict[str, T], what: str, path: str, quiet: bool = False
    ) -> T | None:
        """A program-level reference, or None after reporting why not."""
        decl = table.get(name)
        if decl is not None:
            return decl
        if quiet:
            return None
        if name in self.idx.program_names:
            self.report(REF_KIND, f"{name!r} is not a {what}", path)
        elif name:
            self.report(REF_UNRESOLVED, f"no {what} named {name!r}", path)
        else:
            self.report(REF_UNRESOLVED, f"{what} reference is unset", path)
        return None

    def resolve_local[T](
        self, name: str, table: dict[str, T], what: str, scope: Scope, path: str
    ) -> T | None:
        """A block-scoped reference (action, table or state) of the current
        block, or None after reporting why not."""
        decl = table.get(name)
        if decl is not None:
            return decl
        names = scope.names
        if not name:
            self.report(REF_UNRESOLVED, f"{what} reference is unset", path)
        elif (
            name in names.vars
            or name in names.actions
            or name in names.tables
            or name in names.states
            or name in self.idx.program_names
        ):
            self.report(REF_KIND, f"{name!r} is not a {what}", path)
        elif any(name in getattr(s, what + "s") for s in self.idx.scopes.values()):
            self.report(SCOPE_DECL, f"{what} {name!r} belongs to another block", path)
        else:
            self.report(REF_UNRESOLVED, f"no {what} named {name!r}", path)
        return None

    def resolve_var(self, name: str, scope: Scope, path: str) -> pb.Param | pb.Var | None:
        decl = scope.var(name)
        if decl is not None:
            return decl
        names = scope.names
        if not name:
            self.report(REF_UNRESOLVED, "variable reference is unset", path)
        elif (
            name in names.actions
            or name in names.tables
            or name in names.states
            or name in self.idx.program_names
        ):
            self.report(REF_KIND, f"{name!r} is not a variable", path)
        elif any(
            name in s.vars or any(name in ps for ps in s.action_params.values())
            for s in self.idx.scopes.values()
        ):
            self.report(SCOPE_VAR, f"variable {name!r} is not visible here", path)
        else:
            self.report(REF_UNRESOLVED, f"no variable named {name!r}", path)
        return None

    # -- errors, types, literals --------------------------------------------

    def check_errors(self) -> None:
        core = tuple(self.program.errors[: len(ir.CORE_ERRORS)])
        if core != ir.CORE_ERRORS:
            self.report(
                ERROR_LIST,
                f"errors must begin with {', '.join(ir.CORE_ERRORS)}; got {', '.join(core)}",
                "errors",
            )

    def check_type(self, t: pb.Type, path: str, quiet: bool = False) -> bool:
        """Whether `t` is well formed; reports unless `quiet`."""

        def bad(code: str, message: str) -> bool:
            if not quiet:
                self.report(code, message, path)
            return False

        match kind_of(t):
            case None:
                return bad(TYPE_INVALID, "type has no kind")
            case "bits":
                return t.bits >= 1 or bad(TYPE_INVALID, "bit width must be at least 1")
            case "boolean" | "error":
                return True
            case "header":
                return (
                    self.resolve(t.header, self.idx.header_types, "header type", path, quiet)
                    is not None
                )
            case "struct":
                return (
                    self.resolve(t.struct, self.idx.struct_types, "struct type", path, quiet)
                    is not None
                )
            case "enum_type":
                return (
                    self.resolve(t.enum_type, self.idx.enum_types, "enum type", path, quiet)
                    is not None
                )
            case "stack":
                ok = self.resolve(t.stack.header, self.idx.header_types, "header type", path, quiet)
                if t.stack.size < 1:
                    return bad(TYPE_INVALID, "stack size must be at least 1")
                return ok is not None
            case _:
                return bad(TYPE_INVALID, "type has an unknown kind")

    def type_ok(self, t: pb.Type) -> bool:
        return self.check_type(t, "", quiet=True)

    def check_type_declarations(self) -> None:
        for i, header in enumerate(self.program.header_types):
            path = f"header_types[{i}]"
            self.check_names([f.name for f in header.fields], f"{path}.fields", "field")
            for j, f in enumerate(header.fields):
                fpath = f"{path}.fields[{j}].type"
                if self.check_type(f.type, fpath) and not (is_bits(f.type) or is_boolean(f.type)):
                    self.report(TYPE_INVALID, "header fields are bits or boolean", fpath)
        for i, struct in enumerate(self.program.struct_types):
            path = f"struct_types[{i}]"
            self.check_names([f.name for f in struct.fields], f"{path}.fields", "field")
            for j, f in enumerate(struct.fields):
                self.check_type(f.type, f"{path}.fields[{j}].type")
        for i, enum in enumerate(self.program.enum_types):
            path = f"enum_types[{i}]"
            self.check_names(enum.members, f"{path}.members", "enum member")
            if not enum.members:
                self.report(TYPE_INVALID, "enum has no members", path)
        self.check_struct_cycles()

    def check_struct_cycles(self) -> None:
        """A struct may not contain itself, directly or through other structs."""
        white, grey, black = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(self.idx.struct_types, white)

        def visit(name: str, trail: list[str]) -> None:
            color[name] = grey
            for f in self.idx.struct_types[name].fields:
                if kind_of(f.type) != "struct" or f.type.struct not in color:
                    continue
                inner = f.type.struct
                if color[inner] == grey:
                    chain = [*trail, name]
                    cycle = " -> ".join([*chain[chain.index(inner) :], inner])
                    i = list(self.idx.struct_types).index(name)
                    self.report(
                        TYPE_INVALID, f"struct contains itself: {cycle}", f"struct_types[{i}]"
                    )
                elif color[inner] == white:
                    visit(inner, [*trail, name])
            color[name] = black

        for name in color:
            if color[name] == white:
                visit(name, [])

    def check_program_types(self) -> None:
        if self.resolve(self.program.headers, self.idx.struct_types, "struct type", "headers"):
            self.headers = pb.Type(struct=self.program.headers)
        if self.resolve(self.program.metadata, self.idx.struct_types, "struct type", "metadata"):
            self.metadata = pb.Type(struct=self.program.metadata)

    def type_of_literal(self, lit: pb.Literal, path: str) -> pb.Type | None:
        match lit.WhichOneof("value"):
            case "bits":
                b = lit.bits
                if b.width < 1:
                    self.report(LITERAL_RANGE, "literal width must be at least 1", path)
                    return None
                value = parse_decimal(b.value)
                if value is None:
                    self.report(LITERAL_FORMAT, f"literal value {b.value!r} is not decimal", path)
                elif value >= 1 << b.width:
                    self.report(LITERAL_RANGE, f"{b.value} does not fit in bit<{b.width}>", path)
                return bits_type(b.width)
            case "boolean":
                return BOOLEAN
            case "enum_member":
                e = lit.enum_member
                enum = self.resolve(e.enum_type, self.idx.enum_types, "enum type", path)
                if enum is None:
                    return None
                if e.member not in enum.members:
                    self.report(
                        REF_UNRESOLVED, f"enum {enum.name} has no member {e.member!r}", path
                    )
                return pb.Type(enum_type=e.enum_type)
            case "error":
                if lit.error not in self.idx.errors:
                    self.report(REF_UNRESOLVED, f"no error named {lit.error!r}", path)
                return ERROR
            case _:
                self.report(LITERAL_FORMAT, "literal has no value", path)
                return None

    def check_literal_args(
        self, args: Sequence[pb.Literal], params: Sequence[pb.Param], path: str, code: str
    ) -> None:
        """Constant arguments against params: action data or constructor args."""
        if len(args) != len(params):
            self.report(code, f"expected {len(params)} arguments, got {len(args)}", path)
            return
        for i, (arg, param) in enumerate(zip(args, params, strict=True)):
            t = self.type_of_literal(arg, f"{path}[{i}]")
            if t is not None and self.type_ok(param.type) and not same_type(t, param.type):
                self.report(
                    code,
                    f"argument {i} is {describe(t)}, "
                    f"param {param.name!r} is {describe(param.type)}",
                    f"{path}[{i}]",
                )

    # -- externs ---------------------------------------------------------------

    def check_params(
        self, params: Sequence[pb.Param], allowed: frozenset[int], path: str, what: str
    ) -> None:
        for i, p in enumerate(params):
            ppath = f"{path}[{i}]"
            if p.direction not in allowed:
                names = ", ".join(_DIRECTION_NAMES[d] for d in sorted(allowed))
                self.report(
                    PARAM_DIRECTION,
                    f"{what} param {p.name!r} is {_DIRECTION_NAMES[p.direction]}; allowed: {names}",
                    ppath,
                )
            self.check_type(p.type, f"{ppath}.type")

    def check_extern_types(self) -> None:
        for i, ext in enumerate(self.program.extern_types):
            path = f"extern_types[{i}]"
            self.check_names(
                [p.name for p in ext.constructor_params], f"{path}.constructor_params", "param"
            )
            self.check_params(
                ext.constructor_params,
                frozenset({pb.DIRECTION_IN}),
                f"{path}.constructor_params",
                "constructor",
            )
            self.check_names([m.name for m in ext.methods], f"{path}.methods", "method")
            for j, m in enumerate(ext.methods):
                mpath = f"{path}.methods[{j}]"
                self.check_names([p.name for p in m.params], f"{mpath}.params", "param")
                self.check_params(m.params, _BLOCK_PARAM_DIRECTIONS, f"{mpath}.params", "method")
                if m.HasField("returns"):
                    self.check_type(m.returns, f"{mpath}.returns")

    def check_extern_instances(self) -> None:
        for i, inst in enumerate(self.program.extern_instances):
            path = f"extern_instances[{i}]"
            ext = self.resolve(
                inst.extern_type, self.idx.extern_types, "extern type", f"{path}.extern_type"
            )
            if ext is not None:
                self.check_literal_args(
                    inst.args, ext.constructor_params, f"{path}.args", EXTERN_ARGS
                )

    # -- blocks ----------------------------------------------------------------

    def check_block(self, block: pb.Block, path: str) -> None:
        self.check_params(block.params, _BLOCK_PARAM_DIRECTIONS, f"{path}.params", "block")
        for i, v in enumerate(block.locals):
            self.check_type(v.type, f"{path}.locals[{i}].type")
        if block.kind not in _KIND_NAMES:
            self.report(BLOCK_KIND_SHAPE, "block has no kind", path)
            return
        scope = Scope(block, path, self.idx.scopes[block.name])
        if block.kind == pb.BLOCK_KIND_PARSER:
            if not block.states:
                self.report(BLOCK_KIND_SHAPE, "a parser has at least one state", path)
            elif block.start_state not in scope.names.states:
                self.report(
                    PARSER_START_STATE,
                    f"start_state {block.start_state!r} is not a state of this parser",
                    f"{path}.start_state",
                )
            if block.body:
                self.report(BLOCK_KIND_SHAPE, "a parser has states, not a body", f"{path}.body")
            if block.actions:
                self.report(BLOCK_KIND_SHAPE, "a parser has no actions", f"{path}.actions")
            if block.tables:
                self.report(BLOCK_KIND_SHAPE, "a parser has no tables", f"{path}.tables")
        else:
            kind = _KIND_NAMES[block.kind]
            if block.states:
                self.report(BLOCK_KIND_SHAPE, f"a {kind} has a body, not states", f"{path}.states")
            if block.start_state:
                self.report(BLOCK_KIND_SHAPE, f"a {kind} has no start state", f"{path}.start_state")
        self.action_calls = {}
        for i, action in enumerate(block.actions):
            self.check_action(action, scope, f"{path}.actions[{i}]")
        self.report_cycles(scope.names.actions, self.action_calls, "action")
        for i, table in enumerate(block.tables):
            self.check_table(table, scope, f"{path}.tables[{i}]")
        for i, state in enumerate(block.states):
            self.check_state(state, scope, f"{path}.states[{i}]")
        for i, stmt in enumerate(block.body):
            self.check_stmt(stmt, scope, f"{path}.body[{i}]")

    def check_action(self, action: pb.Action, scope: Scope, path: str) -> None:
        if action.name == "NoAction" and (action.body or action.params):
            # The IR has no implicit declarations, so a program's NoAction is
            # an ordinary action; the name is reserved for the one core.p4
            # means, which every P4 reader and the printer's shim assume
            # (docs/semantics.md, "Tables").
            self.report(NOACTION_RESERVED, "NoAction must have no body and no parameters", path)
        self.check_params(action.params, _ACTION_PARAM_DIRECTIONS, f"{path}.params", "action")
        inner = Scope(scope.block, scope.path, scope.names, action)
        for i, stmt in enumerate(action.body):
            self.check_stmt(stmt, inner, f"{path}.body[{i}]")

    def check_exports(self) -> None:
        roles: set[str] = set()
        for i, export in enumerate(self.program.exports):
            path = f"exports[{i}]"
            if export.role in roles:
                self.report(EXPORT_DUPLICATE, f"role {export.role!r} exported twice", path)
            roles.add(export.role)
            block = self.resolve(export.block, self.idx.blocks, "block", f"{path}.block")
            if block is None or block.kind not in _EXPORT_SIGNATURES:
                continue
            if self.headers is None or self.metadata is None:
                continue
            expected = [
                (direction, self.headers if which == "H" else self.metadata)
                for direction, which in _EXPORT_SIGNATURES[block.kind]
            ]
            actual = [(p.direction, p.type) for p in block.params]
            if len(actual) != len(expected) or any(
                d != ed or not same_type(t, et)
                for (d, t), (ed, et) in zip(actual, expected, strict=True)
            ):
                want = ", ".join(f"{_DIRECTION_NAMES[d]} {describe(t)}" for d, t in expected)
                got = ", ".join(f"{_DIRECTION_NAMES[d]} {describe(t)}" for d, t in actual)
                self.report(
                    EXPORT_SIGNATURE,
                    f"{_KIND_NAMES[block.kind]} {block.name!r} must have params ({want}); "
                    f"got ({got})",
                    path,
                )

    def check_call_graph(self) -> None:
        """No cycle among CallBlock edges, so every run terminates. Actions
        are checked the same way per block, so the call graph of blocks and
        actions together is acyclic (docs/semantics.md, "Controls")."""
        self.report_cycles(self.idx.blocks, self.calls, "block")

    def report_cycles(
        self, nodes: Iterable[str], edges: dict[str, list[tuple[str, str]]], what: str
    ) -> None:
        """Every cycle in `edges` over `nodes`, reported at the call that
        closes it."""
        white, grey, black = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(nodes, white)

        def visit(name: str, trail: list[str]) -> None:
            color[name] = grey
            for callee, path in edges.get(name, ()):
                if callee not in color:
                    continue
                if color[callee] == grey:
                    chain = [*trail, name]
                    cycle = " -> ".join([*chain[chain.index(callee) :], callee])
                    self.report(CALL_CYCLE, f"{what} calls form a cycle: {cycle}", path)
                elif color[callee] == white:
                    visit(callee, [*trail, name])
            color[name] = black

        for name in color:
            if color[name] == white:
                visit(name, [])

    # -- statements ------------------------------------------------------------

    def check_stmts(self, stmts: Sequence[pb.Stmt], scope: Scope, path: str) -> None:
        for i, stmt in enumerate(stmts):
            self.check_stmt(stmt, scope, f"{path}[{i}]")

    def check_stmt(self, stmt: pb.Stmt, scope: Scope, path: str) -> None:
        kind = stmt.WhichOneof("kind")
        if kind is None:
            self.report(STMT_INVALID, "statement has no kind", path)
            return
        if kind not in _STMTS_BY_KIND[scope.block.kind]:
            self.report(
                BLOCK_KIND_STMT,
                f"{kind} is not allowed in a {_KIND_NAMES[scope.block.kind]}",
                path,
            )
            return
        path = f"{path}.{kind}"
        match kind:
            case "assign":
                self.check_assign(stmt.assign, scope, path)
            case "conditional":
                self.check_if(stmt.conditional, scope, path)
            case "apply":
                self.check_apply(stmt.apply, scope, path)
            case "call_action":
                self.check_call_action(stmt.call_action, scope, path)
            case "call_block":
                self.check_call_block(stmt.call_block, scope, path)
            case "call_extern":
                self.check_call_extern(stmt.call_extern, scope, path)
            case "set_valid":
                self.expect_lvalue(
                    stmt.set_valid.header, is_header, "a header", scope, f"{path}.header"
                )
            case "set_invalid":
                self.expect_lvalue(
                    stmt.set_invalid.header, is_header, "a header", scope, f"{path}.header"
                )
            case "push":
                self.check_push_pop(stmt.push.stack, stmt.push.count, scope, path)
            case "pop":
                self.check_push_pop(stmt.pop.stack, stmt.pop.count, scope, path)
            case "extract":
                self.check_extract(stmt.extract, scope, path)
            case "advance":
                # core.p4's `advance(in bit<32> sizeInBits)`: the IR is
                # post-elaboration, so the frontend owes the cast.
                self.expect_expr(stmt.advance.bits, is_bits32, "bit<32>", scope, f"{path}.bits")
            case "verify":
                self.check_verify(stmt.verify, scope, path)
            case "emit":
                self.check_emit(stmt.emit, scope, path)

    def check_assign(self, stmt: pb.Assign, scope: Scope, path: str) -> None:
        target = self.type_of_lvalue(stmt.target, scope, f"{path}.target")
        value = self.type_of(stmt.value, scope, f"{path}.value")
        if target is not None and value is not None and not same_type(target, value):
            self.report(
                TYPE_MISMATCH,
                f"cannot assign {describe(value)} to {describe(target)}",
                path,
            )

    def check_if(self, stmt: pb.If, scope: Scope, path: str) -> None:
        self.expect_expr(stmt.condition, is_boolean, "boolean", scope, f"{path}.condition")
        self.check_stmts(stmt.then, scope, f"{path}.then")
        self.check_stmts(stmt.otherwise, scope, f"{path}.otherwise")

    def check_apply(self, stmt: pb.Apply, scope: Scope, path: str) -> None:
        if scope.action is not None:
            self.report(BLOCK_KIND_STMT, "apply is not allowed inside an action", path)
            return
        self.resolve_local(stmt.table, scope.names.tables, "table", scope, f"{path}.table")
        if stmt.HasField("hit"):
            self.expect_lvalue(stmt.hit, is_boolean, "boolean", scope, f"{path}.hit")

    def check_call_action(self, stmt: pb.CallAction, scope: Scope, path: str) -> None:
        action = self.resolve_local(
            stmt.action, scope.names.actions, "action", scope, f"{path}.action"
        )
        if action is None:
            return
        if scope.action is not None:
            self.action_calls.setdefault(scope.action.name, []).append((action.name, path))
        self.check_args(stmt.args, action.params, scope, path)

    def check_call_block(self, stmt: pb.CallBlock, scope: Scope, path: str) -> None:
        if scope.action is not None:
            # P4 forbids applying a control or parser from an action (§14.1).
            self.report(BLOCK_KIND_STMT, "call_block is not allowed inside an action", path)
            return
        callee = self.resolve(stmt.block, self.idx.blocks, "block", f"{path}.block")
        if callee is None:
            return
        self.calls.setdefault(scope.block.name, []).append((callee.name, path))
        # A block calls only blocks of its own kind, so a deparser, which has
        # no entries, never reaches a table (proto, CallBlock).
        if callee.kind != scope.block.kind:
            kind = _KIND_NAMES[scope.block.kind]
            self.report(
                CALL_KIND,
                f"a {kind} may only call a {kind}; "
                f"{callee.name!r} is a {_KIND_NAMES.get(callee.kind, 'block without kind')}",
                f"{path}.block",
            )
        self.check_args(stmt.args, callee.params, scope, path)

    def check_call_extern(self, stmt: pb.CallExtern, scope: Scope, path: str) -> None:
        instance = self.resolve(
            stmt.instance, self.idx.extern_instances, "extern instance", f"{path}.instance"
        )
        if instance is None:
            return
        ext = self.idx.extern_types.get(instance.extern_type)
        if ext is None:
            return  # reported at the instance
        method = next((m for m in ext.methods if m.name == stmt.method), None)
        if method is None:
            self.report(
                REF_UNRESOLVED, f"extern {ext.name} has no method {stmt.method!r}", f"{path}.method"
            )
            return
        self.check_args(stmt.args, method.params, scope, path)
        if method.HasField("returns"):
            if not stmt.HasField("result"):
                self.report(
                    EXTERN_RESULT, f"method {method.name!r} returns a value; result is unset", path
                )
            else:
                t = self.type_of_lvalue(stmt.result, scope, f"{path}.result")
                if (
                    t is not None
                    and self.type_ok(method.returns)
                    and not same_type(t, method.returns)
                ):
                    self.report(
                        EXTERN_RESULT,
                        f"result is {describe(t)}, method returns {describe(method.returns)}",
                        f"{path}.result",
                    )
        elif stmt.HasField("result"):
            self.report(EXTERN_RESULT, f"method {method.name!r} returns nothing", f"{path}.result")

    def check_args(
        self, args: Sequence[pb.Arg], params: Sequence[pb.Param], scope: Scope, path: str
    ) -> None:
        """Arguments against params, and the aliasing rule.

        Aliasing is judged statically and conservatively: two arguments may
        alias when their access paths (variable, then fields and indices)
        agree wherever both are known; a computed index is unknown and
        matches any index. Only `out` and `inout` arguments take part: an
        `in` argument is copied in before anything is written back, so its
        overlapping an out argument changes nothing (§6.8). Two out or inout
        arguments that may alias are an error, so copy-back order never
        matters (docs/semantics.md, "Block calls").
        """
        if len(args) != len(params):
            self.report(ARG_COUNT, f"expected {len(params)} arguments, got {len(args)}", path)
            return
        accesses: list[tuple[str, Access | None]] = []
        for i, (arg, param) in enumerate(zip(args, params, strict=True)):
            apath = f"{path}.args[{i}]"
            kind = arg.WhichOneof("kind")
            wants_out = param.direction in _OUT_DIRECTIONS
            if kind is None:
                self.report(ARG_DIRECTION, "argument has no kind", apath)
                continue
            if wants_out and kind != "lvalue":
                self.report(
                    ARG_DIRECTION,
                    f"param {param.name!r} is {_DIRECTION_NAMES[param.direction]}; "
                    "the argument must be an out lvalue",
                    apath,
                )
                continue
            if not wants_out and kind != "expr":
                self.report(
                    ARG_DIRECTION,
                    f"param {param.name!r} is {_DIRECTION_NAMES[param.direction]}; "
                    "the argument must be an in expression",
                    apath,
                )
                continue
            if kind == "expr":
                t = self.type_of(arg.expr, scope, f"{apath}.expr")
            else:
                t = self.type_of_lvalue(arg.lvalue, scope, f"{apath}.lvalue")
                accesses.append((apath, self.lvalue_access(arg.lvalue)))
            if t is not None and self.type_ok(param.type) and not same_type(t, param.type):
                self.report(
                    ARG_TYPE,
                    f"argument is {describe(t)}, param {param.name!r} is {describe(param.type)}",
                    apath,
                )
        for j, (apath, b) in enumerate(accesses):
            if b is None:
                continue
            if any(a is not None and may_alias(a, b) for _, a in accesses[:j]):
                self.report(CALL_ALIAS, "argument may alias an earlier out argument", apath)

    def check_extract(self, stmt: pb.Extract, scope: Scope, path: str) -> None:
        """The target is a header lvalue, or `stack.next`, which is allowed
        nowhere else (docs/semantics.md, "Header stacks")."""
        target = stmt.target
        if target.WhichOneof("kind") == "next":
            self.expect_lvalue(
                target.next.stack, is_stack, "a stack", scope, f"{path}.target.next.stack"
            )
        else:
            self.expect_lvalue(target, is_header, "a header", scope, f"{path}.target")

    def check_push_pop(self, stack: pb.LValue, count: int, scope: Scope, path: str) -> None:
        self.expect_lvalue(stack, is_stack, "a stack", scope, f"{path}.stack")
        if count < 1:
            self.report(STACK_COUNT, "count must be at least 1", f"{path}.count")

    def check_verify(self, stmt: pb.Verify, scope: Scope, path: str) -> None:
        self.expect_expr(stmt.condition, is_boolean, "boolean", scope, f"{path}.condition")
        if stmt.error not in self.idx.errors:
            self.report(REF_UNRESOLVED, f"no error named {stmt.error!r}", f"{path}.error")

    def check_emit(self, stmt: pb.Emit, scope: Scope, path: str) -> None:
        t = self.type_of(stmt.value, scope, f"{path}.value")
        if t is not None and not self.emittable(t, set()):
            self.report(
                TYPE_MISMATCH,
                f"emit takes a header, a stack, or a struct of those; got {describe(t)}",
                f"{path}.value",
            )

    def emittable(self, t: pb.Type, visiting: set[str]) -> bool:
        match kind_of(t):
            case "header" | "stack":
                return True
            case "struct":
                if t.struct in visiting:
                    return False
                fields = self.idx.struct_types[t.struct].fields
                return all(self.emittable(f.type, visiting | {t.struct}) for f in fields)
            case _:
                return False

    # -- expressions -----------------------------------------------------------

    def expect_expr(self, expr: pb.Expr, ok, what: str, scope: Scope, path: str) -> pb.Type | None:
        """The type of `expr`, reporting TYPE_MISMATCH unless `ok(type)`."""
        t = self.type_of(expr, scope, path)
        if t is not None and not ok(t):
            self.report(TYPE_MISMATCH, f"expected {what}, got {describe(t)}", path)
            return None
        return t

    def expect_lvalue(
        self, lvalue: pb.LValue, ok, what: str, scope: Scope, path: str
    ) -> pb.Type | None:
        t = self.type_of_lvalue(lvalue, scope, path)
        if t is not None and not ok(t):
            self.report(TYPE_MISMATCH, f"expected {what}, got {describe(t)}", path)
            return None
        return t

    def type_of(self, expr: pb.Expr, scope: Scope, path: str) -> pb.Type | None:
        """The type of an expression, or None once a problem is reported.

        Bottom-up: each operator's result type is determined by its operands,
        as the comments on the operators in the schema say.
        """
        match expr.WhichOneof("kind"):
            case "literal":
                return self.type_of_literal(expr.literal, f"{path}.literal")
            case "var":
                decl = self.resolve_var(expr.var, scope, f"{path}.var")
                if decl is None or not self.type_ok(decl.type):
                    return None
                return decl.type
            case "member":
                base = self.type_of(expr.member.base, scope, f"{path}.member.base")
                return self.type_of_field(base, expr.member.field, f"{path}.member")
            case "index":
                return self.type_of_index(expr.index.base, expr.index.index, scope, f"{path}.index")
            case "last_index":
                self.expect_expr(
                    expr.last_index.stack, is_stack, "a stack", scope, f"{path}.last_index.stack"
                )
                return BITS32
            case "unary":
                return self.type_of_unary(expr.unary, scope, f"{path}.unary")
            case "binary":
                return self.type_of_binary(expr.binary, scope, f"{path}.binary")
            case "cast":
                return self.type_of_cast(expr.cast, scope, f"{path}.cast")
            case "slice":
                return self.type_of_slice(expr.slice, scope, f"{path}.slice")
            case "is_valid":
                self.expect_expr(
                    expr.is_valid.header, is_header, "a header", scope, f"{path}.is_valid.header"
                )
                return BOOLEAN
            case "mux":
                return self.type_of_mux(expr.mux, scope, f"{path}.mux")
            case "lookahead":
                return self.type_of_lookahead(expr.lookahead, scope, f"{path}.lookahead")
            case _:
                self.report(EXPR_INVALID, "expression has no kind", path)
                return None

    def type_of_field(self, base: pb.Type | None, name: str, path: str) -> pb.Type | None:
        """The type of field `name` of a header or struct value of type `base`."""
        if base is None:
            return None
        if kind_of(base) not in ("header", "struct"):
            self.report(
                TYPE_MISMATCH, f"expected a header or struct, got {describe(base)}", f"{path}.base"
            )
            return None
        type_name = base.header if is_header(base) else base.struct
        for f in self.idx.fields(type_name):
            if f.name == name:
                return f.type if self.type_ok(f.type) else None
        self.report(REF_UNRESOLVED, f"{describe(base)} has no field {name!r}", f"{path}.field")
        return None

    def type_of_index(
        self, base: pb.Expr, index: pb.Expr, scope: Scope, path: str
    ) -> pb.Type | None:
        stack = self.expect_expr(base, is_stack, "a stack", scope, f"{path}.base")
        self.expect_expr(index, is_bits, "bits", scope, f"{path}.index")
        return pb.Type(header=stack.stack.header) if stack is not None else None

    def type_of_unary(self, expr: pb.Unary, scope: Scope, path: str) -> pb.Type | None:
        match expr.op:
            case pb.UNARY_OP_NOT:
                return self.expect_expr(
                    expr.operand, is_boolean, "boolean", scope, f"{path}.operand"
                )
            case pb.UNARY_OP_COMPLEMENT | pb.UNARY_OP_NEGATE:
                return self.expect_expr(expr.operand, is_bits, "bits", scope, f"{path}.operand")
            case _:
                self.report(EXPR_INVALID, "unary operator is unspecified", f"{path}.op")
                self.type_of(expr.operand, scope, f"{path}.operand")
                return None

    def type_of_binary(self, expr: pb.Binary, scope: Scope, path: str) -> pb.Type | None:
        left = self.type_of(expr.left, scope, f"{path}.left")
        right = self.type_of(expr.right, scope, f"{path}.right")
        if left is None or right is None:
            return None

        def mismatch(message: str) -> None:
            self.report(
                TYPE_MISMATCH,
                f"{pb.BinaryOp.Name(expr.op)}: {message}; "
                f"got {describe(left)} and {describe(right)}",
                path,
            )

        match expr.op:
            case (
                pb.BINARY_OP_ADD
                | pb.BINARY_OP_SUB
                | pb.BINARY_OP_MUL
                | pb.BINARY_OP_ADD_SAT
                | pb.BINARY_OP_SUB_SAT
                | pb.BINARY_OP_BIT_AND
                | pb.BINARY_OP_BIT_OR
                | pb.BINARY_OP_BIT_XOR
            ):
                if is_bits(left) and same_type(left, right):
                    return left
                mismatch("operands must be bits of one width")
            case pb.BINARY_OP_SHL | pb.BINARY_OP_SHR:
                if is_bits(left) and is_bits(right):
                    return left
                mismatch("operands must be bits")
            case pb.BINARY_OP_CONCAT:
                if is_bits(left) and is_bits(right):
                    return bits_type(left.bits + right.bits)
                mismatch("operands must be bits")
            case pb.BINARY_OP_EQ | pb.BINARY_OP_NE:
                if same_type(left, right):
                    return BOOLEAN
                mismatch("operands must have one type")
            case pb.BINARY_OP_LT | pb.BINARY_OP_LE | pb.BINARY_OP_GT | pb.BINARY_OP_GE:
                if is_bits(left) and same_type(left, right):
                    return BOOLEAN
                mismatch("operands must be bits of one width")
            case pb.BINARY_OP_AND | pb.BINARY_OP_OR:
                if is_boolean(left) and is_boolean(right):
                    return BOOLEAN
                mismatch("operands must be boolean")
            case _:
                self.report(EXPR_INVALID, "binary operator is unspecified", f"{path}.op")
        return None

    def type_of_cast(self, expr: pb.Cast, scope: Scope, path: str) -> pb.Type | None:
        to_ok = self.check_type(expr.to, f"{path}.to")
        operand = self.type_of(expr.operand, scope, f"{path}.operand")
        if not to_ok or operand is None:
            return None
        to = expr.to
        allowed = (
            (is_bits(operand) and is_bits(to))
            or (is_boolean(operand) and is_bits(to) and to.bits == 1)
            or (is_bits(operand) and operand.bits == 1 and is_boolean(to))
        )
        if not allowed:
            self.report(CAST_INVALID, f"cannot cast {describe(operand)} to {describe(to)}", path)
            return None
        return to

    def type_of_slice(self, expr: pb.Slice, scope: Scope, path: str) -> pb.Type | None:
        operand = self.expect_expr(expr.operand, is_bits, "bits", scope, f"{path}.operand")
        if operand is None:
            return None
        if not expr.lo <= expr.hi < operand.bits:
            self.report(
                SLICE_RANGE,
                f"[{expr.hi}:{expr.lo}] needs lo <= hi < {operand.bits}",
                path,
            )
            return None
        return bits_type(expr.hi - expr.lo + 1)

    def type_of_mux(self, expr: pb.Mux, scope: Scope, path: str) -> pb.Type | None:
        self.expect_expr(expr.condition, is_boolean, "boolean", scope, f"{path}.condition")
        then = self.type_of(expr.then, scope, f"{path}.then")
        else_ = self.type_of(expr.otherwise, scope, f"{path}.otherwise")
        if then is None or else_ is None:
            return None
        if not same_type(then, else_):
            self.report(
                TYPE_MISMATCH,
                f"branches differ: {describe(then)} and {describe(else_)}",
                path,
            )
            return None
        return then

    def type_of_lookahead(self, expr: pb.Lookahead, scope: Scope, path: str) -> pb.Type | None:
        if not scope.in_parser:
            self.report(PARSER_ONLY, "lookahead is allowed only in a parser", path)
        if not self.check_type(expr.type, f"{path}.type"):
            return None
        # What has a packet width: bool is one bit (docs/semantics.md, "lookahead").
        if not (is_bits(expr.type) or is_boolean(expr.type) or is_header(expr.type)):
            self.report(
                TYPE_MISMATCH,
                f"lookahead reads bits, a boolean or a header, not {describe(expr.type)}",
                f"{path}.type",
            )
            return None
        return expr.type

    # -- lvalues ---------------------------------------------------------------

    def type_of_lvalue(self, lvalue: pb.LValue, scope: Scope, path: str) -> pb.Type | None:
        """The type of an lvalue, or None once a problem is reported. The
        root must be writable: not an `in` or directionless param."""
        match lvalue.WhichOneof("kind"):
            case "var":
                decl = self.resolve_var(lvalue.var, scope, f"{path}.var")
                if decl is None:
                    return None
                if isinstance(decl, pb.Param) and decl.direction in (
                    pb.DIRECTION_IN,
                    pb.DIRECTION_NONE,
                ):
                    self.report(
                        LVALUE_READONLY,
                        f"{_DIRECTION_NAMES[decl.direction]} param {decl.name!r} cannot be written",
                        f"{path}.var",
                    )
                    return None
                return decl.type if self.type_ok(decl.type) else None
            case "member":
                base = self.type_of_lvalue(lvalue.member.base, scope, f"{path}.member.base")
                return self.type_of_field(base, lvalue.member.field, f"{path}.member")
            case "index":
                stack = self.expect_lvalue(
                    lvalue.index.base, is_stack, "a stack", scope, f"{path}.index.base"
                )
                self.expect_expr(lvalue.index.index, is_bits, "bits", scope, f"{path}.index.index")
                return pb.Type(header=stack.stack.header) if stack is not None else None
            case "next":
                # `check_extract` handles the one place it may appear.
                self.report(NEXT_ONLY_EXTRACT, "stack.next is only the target of an extract", path)
                return None
            case _:
                self.report(EXPR_INVALID, "lvalue has no kind", path)
                return None

    def lvalue_access(self, lvalue: pb.LValue) -> Access | None:
        match lvalue.WhichOneof("kind"):
            case "var":
                return (lvalue.var,)
            case "member":
                base = self.lvalue_access(lvalue.member.base)
                return None if base is None else (*base, lvalue.member.field)
            case "index":
                base = self.lvalue_access(lvalue.index.base)
                return None if base is None else (*base, self.static_index(lvalue.index.index))
            case "next":
                base = self.lvalue_access(lvalue.next.stack)
                return None if base is None else (*base, None)
            case _:
                return None

    @staticmethod
    def static_index(expr: pb.Expr) -> int | None:
        if expr.WhichOneof("kind") == "literal" and expr.literal.WhichOneof("value") == "bits":
            return parse_decimal(expr.literal.bits.value)
        return None

    # -- parser states ---------------------------------------------------------

    def check_state(self, state: pb.State, scope: Scope, path: str) -> None:
        self.check_stmts(state.body, scope, f"{path}.body")
        tpath = f"{path}.transition"
        match state.transition.WhichOneof("kind"):
            case "direct":
                self.check_target(state.transition.direct, scope, f"{tpath}.direct")
            case "select":
                self.check_select(state.transition.select, scope, f"{tpath}.select")
            case _:
                self.report(PARSER_TRANSITION, "state has no transition", tpath)

    def check_target(self, target: pb.Target, scope: Scope, path: str) -> None:
        match target.WhichOneof("kind"):
            case "state":
                self.resolve_local(
                    target.state, scope.names.states, "state", scope, f"{path}.state"
                )
            case "accept" | "reject":
                pass
            case _:
                self.report(PARSER_TRANSITION, "target has no kind", path)

    def check_select(self, select: pb.Select, scope: Scope, path: str) -> None:
        if not select.keys:
            self.report(SELECT_ARITY, "select has no keys", path)
        key_types: list[pb.Type | None] = []
        for i, key in enumerate(select.keys):
            t = self.type_of(key, scope, f"{path}.keys[{i}]")
            if t is not None and kind_of(t) not in _SCALAR_KINDS:
                self.report(
                    SELECT_TYPE,
                    f"select key must be a scalar, got {describe(t)}",
                    f"{path}.keys[{i}]",
                )
                t = None
            key_types.append(t)
        for i, case in enumerate(select.cases):
            cpath = f"{path}.cases[{i}]"
            if len(case.sets) != len(select.keys):
                self.report(
                    SELECT_ARITY,
                    f"case has {len(case.sets)} sets for {len(select.keys)} keys",
                    f"{cpath}.sets",
                )
            else:
                for j, (key_set, key_type) in enumerate(zip(case.sets, key_types, strict=True)):
                    self.check_key_set(key_set, key_type, f"{cpath}.sets[{j}]")
            self.check_target(case.target, scope, f"{cpath}.target")

    def check_key_set(self, key_set: pb.KeySet, key: pb.Type | None, path: str) -> None:
        def literal_of_key(lit: pb.Literal, lpath: str) -> None:
            t = self.type_of_literal(lit, lpath)
            if key is not None and t is not None and not same_type(t, key):
                self.report(SELECT_TYPE, f"key is {describe(key)}, literal is {describe(t)}", lpath)

        def bits_key(what: str) -> bool:
            if key is not None and not is_bits(key):
                self.report(SELECT_TYPE, f"{what} needs a bits key, got {describe(key)}", path)
                return False
            return True

        match key_set.WhichOneof("kind"):
            case "exact":
                literal_of_key(key_set.exact, f"{path}.exact")
            case "masked":
                if bits_key("masked"):
                    literal_of_key(key_set.masked.value, f"{path}.masked.value")
                    literal_of_key(key_set.masked.mask, f"{path}.masked.mask")
            case "range":
                if bits_key("range"):
                    literal_of_key(key_set.range.lo, f"{path}.range.lo")
                    literal_of_key(key_set.range.hi, f"{path}.range.hi")
            case "dont_care":
                pass
            case _:
                self.report(SELECT_TYPE, "key set has no kind", path)

    # -- tables ----------------------------------------------------------------

    def check_table(self, table: pb.Table, scope: Scope, path: str) -> None:
        key_types = self.check_keys(table, scope, path)
        kinds = [k.match_kind for k in table.keys]
        if kinds.count(pb.MATCH_KIND_LPM) > 1:
            self.report(TABLE_LPM_COUNT, "a table has at most one lpm key", f"{path}.keys")
        if pb.MATCH_KIND_LPM in kinds and pb.MATCH_KIND_TERNARY in kinds:
            self.report(TABLE_KEY_MIX, "a table with an lpm key has no ternary key", f"{path}.keys")

        if not table.actions:
            self.report(TABLE_ACTIONS, "table lists no actions", f"{path}.actions")
        listed: set[str] = set()
        for i, name in enumerate(table.actions):
            apath = f"{path}.actions[{i}]"
            if name in listed:
                self.report(TABLE_ACTIONS, f"action {name!r} listed twice", apath)
            listed.add(name)
            action = self.resolve_local(name, scope.names.actions, "action", scope, apath)
            if action is not None and any(p.direction != pb.DIRECTION_NONE for p in action.params):
                self.report(
                    PARAM_DIRECTION,
                    f"action {name!r} is invoked by a table, so its params must be directionless",
                    apath,
                )
        if table.HasField("default_action"):
            self.check_action_call(table.default_action, table, scope, f"{path}.default_action")

        has_ternary = pb.MATCH_KIND_TERNARY in kinds
        patterns: list[list[KeyPattern] | None] = []
        for i, entry in enumerate(table.const_entries):
            epath = f"{path}.const_entries[{i}]"
            patterns.append(self.check_entry(entry, table, key_types, has_ternary, scope, epath))
        for j, b in enumerate(patterns):
            if b is None:
                continue
            for i, a in enumerate(patterns[:j]):
                if a is None:
                    continue
                epath = f"{path}.const_entries[{j}]"
                if has_ternary:
                    same_priority = (
                        table.const_entries[i].priority == table.const_entries[j].priority
                    )
                    overlap = all(patterns_overlap(x, y) for x, y in zip(a, b, strict=True))
                    if same_priority and overlap:
                        self.report(
                            ENTRY_PRIORITY,
                            f"entries {i} and {j} overlap with the same priority",
                            epath,
                        )
                elif all(patterns_equal(x, y) for x, y in zip(a, b, strict=True)):
                    self.report(ENTRY_DUPLICATE, f"entries {i} and {j} have the same keys", epath)

    def check_keys(self, table: pb.Table, scope: Scope, path: str) -> list[pb.Type | None]:
        names: set[str] = set()
        key_types: list[pb.Type | None] = []
        for i, key in enumerate(table.keys):
            kpath = f"{path}.keys[{i}]"
            name = ir.key_name(key)
            if name is not None:
                if name in names:
                    self.report(KEY_NAME, f"key name {name!r} used twice", f"{kpath}.name")
                names.add(name)
            t = self.type_of(key.expr, scope, f"{kpath}.expr")
            match key.match_kind:
                case pb.MATCH_KIND_EXACT | pb.MATCH_KIND_LPM | pb.MATCH_KIND_TERNARY:
                    # Table keys are bits only; the frontend casts a boolean or
                    # enum key. Select keys may be any scalar.
                    if t is not None and not is_bits(t):
                        self.report(
                            KEY_TYPE,
                            f"{pb.MatchKind.Name(key.match_kind)} key must be bits, "
                            f"got {describe(t)}",
                            kpath,
                        )
                        t = None
                case _:
                    self.report(KEY_TYPE, "match kind is unspecified", f"{kpath}.match_kind")
                    t = None
            key_types.append(t)
        return key_types

    def check_action_call(
        self, call: pb.ActionCall, table: pb.Table, scope: Scope, path: str
    ) -> None:
        """An action call from a table: default action or entry."""
        action = self.resolve_local(
            call.action, scope.names.actions, "action", scope, f"{path}.action"
        )
        if action is None:
            return
        if call.action not in table.actions:
            self.report(
                TABLE_ACTIONS,
                f"action {call.action!r} is not in the table's action list",
                f"{path}.action",
            )
        self.check_literal_args(call.args, action.params, f"{path}.args", ACTION_ARGS)

    def check_entry(
        self,
        entry: pb.Entry,
        table: pb.Table,
        key_types: Sequence[pb.Type | None],
        has_ternary: bool,
        scope: Scope,
        path: str,
    ) -> list[KeyPattern] | None:
        """One const entry; returns its patterns when every key value parsed."""
        self.check_action_call(entry.action, table, scope, f"{path}.action")
        if not has_ternary and entry.priority != 0:
            self.report(
                ENTRY_PRIORITY, "only a table with a ternary key has priorities", f"{path}.priority"
            )
        if len(entry.keys) != len(table.keys):
            self.report(
                ENTRY_SHAPE,
                f"entry has {len(entry.keys)} values for {len(table.keys)} keys",
                f"{path}.keys",
            )
            return None
        patterns: list[KeyPattern | None] = [
            self.key_pattern(value, key, t, f"{path}.keys[{i}]")
            for i, (value, key, t) in enumerate(zip(entry.keys, table.keys, key_types, strict=True))
        ]
        if any(p is None for p in patterns):
            return None
        return cast(list[KeyPattern], patterns)

    def key_pattern(
        self, value: pb.KeyValue, key: pb.Key, t: pb.Type | None, path: str
    ) -> KeyPattern | None:
        """A key value against its key: the right kind, decimal, in range."""
        kind = value.WhichOneof("kind")
        expected = {
            pb.MATCH_KIND_EXACT: "exact",
            pb.MATCH_KIND_LPM: "lpm",
            pb.MATCH_KIND_TERNARY: "ternary",
        }.get(key.match_kind)
        if kind is None:
            self.report(ENTRY_SHAPE, "key value has no kind", path)
            return None
        if expected is None:
            return None  # the key itself was reported
        if kind != expected:
            self.report(ENTRY_SHAPE, f"key is {expected}, value is {kind}", path)
            return None
        if t is None:
            return None

        def in_width(text: str, what: str, vpath: str) -> int | None:
            number = parse_decimal(text)
            if number is None:
                self.report(ENTRY_SHAPE, f"{what} {text!r} is not decimal", vpath)
            elif number >= 1 << t.bits:
                self.report(ENTRY_RANGE, f"{what} {text} does not fit in {describe(t)}", vpath)
            else:
                return number
            return None

        match kind:
            case "exact":
                number = in_width(value.exact, "value", f"{path}.exact")
                return None if number is None else ExactPattern(number)
            case "lpm":
                number = in_width(value.lpm.value, "value", f"{path}.lpm.value")
                if value.lpm.prefix_len > t.bits:
                    self.report(
                        ENTRY_RANGE,
                        f"prefix length {value.lpm.prefix_len} exceeds {describe(t)}",
                        f"{path}.lpm.prefix_len",
                    )
                    return None
                if number is None:
                    return None
                pattern = LpmPattern(number, value.lpm.prefix_len, t.bits)
                if number & ~pattern.mask:
                    self.report(
                        ENTRY_RANGE, "lpm value has bits below its prefix", f"{path}.lpm.value"
                    )
                    return None
                return pattern
            case _:
                number = in_width(value.ternary.value, "value", f"{path}.ternary.value")
                mask = in_width(value.ternary.mask, "mask", f"{path}.ternary.mask")
                if number is None or mask is None:
                    return None
                if number & ~mask:
                    self.report(
                        ENTRY_RANGE,
                        "ternary value has bits outside its mask",
                        f"{path}.ternary.value",
                    )
                    return None
                return TernaryPattern(number, mask)
