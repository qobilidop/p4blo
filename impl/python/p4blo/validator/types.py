"""Types, literals and parameters.

The functions at the top are structural questions about a `pb.Type` that
every later rule asks: its kind, whether two types are equal, how P4 would
write it. `TypeChecks` checks that types are well formed, that type
declarations are (including that no struct contains itself), types
literals, and checks parameter lists and constant argument lists.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    LITERAL_FORMAT,
    LITERAL_RANGE,
    PARAM_DIRECTION,
    REF_UNRESOLVED,
    TYPE_INVALID,
)
from p4blo.validator.names import (
    DIRECTION_NAMES,
    NameChecks,
)


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
# bits only (docs/ir-semantics.md, "Keys are bits").
SCALAR_KINDS = frozenset({"bits", "boolean", "enum_type", "error"})


_DECIMAL = re.compile(r"[0-9]+")


def parse_decimal(text: str) -> int | None:
    return int(text) if _DECIMAL.fullmatch(text) else None


class TypeChecks(NameChecks):
    """Well-formed types, typed literals, and parameter lists."""

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

    def check_params(
        self, params: Sequence[pb.Param], allowed: frozenset[int], path: str, what: str
    ) -> None:
        for i, p in enumerate(params):
            ppath = f"{path}[{i}]"
            if p.direction not in allowed:
                names = ", ".join(DIRECTION_NAMES[d] for d in sorted(allowed))
                self.report(
                    PARAM_DIRECTION,
                    f"{what} param {p.name!r} is {DIRECTION_NAMES[p.direction]}; allowed: {names}",
                    ppath,
                )
            self.check_type(p.type, f"{ppath}.type")
