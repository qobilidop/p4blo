"""Types and declarations the eDSL knows about.

`bit(n)`, `boolean` and `error_t` are plain `pb.Type` values. Headers,
structs, externs and their instances are small declaration objects that
remember what the IR needs later: a header's field types so that
`hdr.ipv4.ttl` resolves to `bit<8>`, an extern's method signatures so that
a call can check its arguments. `TypeTable` holds every declaration of one
program and is what expressions consult.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from p4blo.v0 import p4blo_pb2 as pb


class EdslError(Exception):
    """A mistake the builder can see at build time.

    Width mismatches, unknown fields, unknown actions and the like. The
    validator remains the authority on whether a program is well formed;
    the eDSL only refuses what it cannot represent sensibly.
    """


def bit(width: int) -> pb.Type:
    """The type bit<width>."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise EdslError(f"bit<N> needs an integer N >= 1, got {width!r}")
    return pb.Type(bits=width)


boolean: pb.Type = pb.Type(boolean=pb.BoolType())
"""The type bool."""

error_t: pb.Type = pb.Type(error=pb.ErrorType())
"""The type error."""


@runtime_checkable
class Declared(Protocol):
    """A declaration that can stand for its type: a header, struct or enum."""

    @property
    def type(self) -> pb.Type: ...


type TypeLike = pb.Type | Declared
"""Anything that names a type: a `pb.Type` or a declared header, struct or enum."""


def as_type(t: TypeLike) -> pb.Type:
    if isinstance(t, pb.Type):
        return t
    if isinstance(t, Declared):
        return t.type
    raise EdslError(f"not a type: {t!r}")


def type_str(t: pb.Type) -> str:
    """A type as P4 would write it, for messages."""
    match t.WhichOneof("kind"):
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
            return "<no type>"


def is_bits(t: pb.Type) -> bool:
    return t.WhichOneof("kind") == "bits"


def is_boolean(t: pb.Type) -> bool:
    return t.WhichOneof("kind") == "boolean"


def _fields(what: str, name: str, fields: Mapping[str, TypeLike]) -> dict[str, pb.Type]:
    if not name:
        raise EdslError(f"a {what} needs a name")
    return {f: as_type(t) for f, t in fields.items()}


class HeaderType:
    """A declared header type. `h[n]` is the type of a stack of n of them."""

    def __init__(self, name: str, fields: Mapping[str, TypeLike]) -> None:
        self.name = name
        self.fields = _fields("header", name, fields)
        for f, t in self.fields.items():
            if not (is_bits(t) or is_boolean(t)):
                raise EdslError(
                    f"header {name}: field {f!r} is {type_str(t)}; header fields are bit<N> or bool"
                )

    @property
    def type(self) -> pb.Type:
        return pb.Type(header=self.name)

    def __getitem__(self, size: int) -> pb.Type:
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise EdslError(f"a stack size is an integer >= 1, got {size!r}")
        return pb.Type(stack=pb.StackType(header=self.name, size=size))

    def build(self) -> pb.HeaderType:
        return pb.HeaderType(
            name=self.name,
            fields=[pb.Field(name=f, type=t) for f, t in self.fields.items()],
        )


class StructType:
    """A declared struct type."""

    def __init__(self, name: str, fields: Mapping[str, TypeLike]) -> None:
        self.name = name
        self.fields = _fields("struct", name, fields)

    @property
    def type(self) -> pb.Type:
        return pb.Type(struct=self.name)

    def build(self) -> pb.StructType:
        return pb.StructType(
            name=self.name,
            fields=[pb.Field(name=f, type=t) for f, t in self.fields.items()],
        )


DIRECTIONS: dict[str, pb.Direction] = {
    "none": pb.DIRECTION_NONE,
    "in": pb.DIRECTION_IN,
    "out": pb.DIRECTION_OUT,
    "inout": pb.DIRECTION_INOUT,
}

type ParamSpec = tuple[str, str, TypeLike]
"""A parameter as the eDSL takes it: (name, direction, type), the direction
one of "none", "in", "out", "inout"."""


def make_param(spec: ParamSpec, where: str) -> pb.Param:
    name, direction, t = spec
    if not name:
        raise EdslError(f"{where}: a parameter needs a name")
    if direction not in DIRECTIONS:
        raise EdslError(
            f"{where}: parameter {name!r} has direction {direction!r}; "
            f"expected one of {', '.join(DIRECTIONS)}"
        )
    return pb.Param(name=name, type=as_type(t), direction=DIRECTIONS[direction])


def make_params(specs: Sequence[ParamSpec], where: str) -> list[pb.Param]:
    params = [make_param(s, where) for s in specs]
    names = [p.name for p in params]
    if len(set(names)) != len(names):
        raise EdslError(f"{where}: a parameter name is repeated")
    return params


@dataclass(frozen=True)
class MethodSpec:
    """An extern method: its parameters and, when it returns one, its result type."""

    params: Sequence[ParamSpec]
    returns: TypeLike | None = None


def method(params: Sequence[ParamSpec], returns: TypeLike | None = None) -> MethodSpec:
    """Declare an extern method; `returns` is its result type, if any."""
    return MethodSpec(list(params), returns)


class ExternType:
    """A declared, monomorphic extern type.

    Constructor parameters are `in` and may be given as bare types, in which
    case they are named `arg0`, `arg1`, ...; a `(name, type)` pair names one.
    """

    def __init__(
        self,
        name: str,
        constructor: Sequence[TypeLike | tuple[str, TypeLike]],
        methods: Mapping[str, Sequence[ParamSpec] | MethodSpec],
    ) -> None:
        if not name:
            raise EdslError("an extern type needs a name")
        self.name = name
        self.constructor_params: list[pb.Param] = []
        for i, c in enumerate(constructor):
            pname, t = c if isinstance(c, tuple) else (f"arg{i}", c)
            self.constructor_params.append(
                pb.Param(name=pname, type=as_type(t), direction=pb.DIRECTION_IN)
            )
        self.methods: dict[str, pb.Method] = {}
        for mname, spec in methods.items():
            if not isinstance(spec, MethodSpec):
                spec = MethodSpec(spec)
            m = pb.Method(name=mname, params=make_params(spec.params, f"{name}.{mname}"))
            if spec.returns is not None:
                m.returns.CopyFrom(as_type(spec.returns))
            self.methods[mname] = m

    def method(self, name: str) -> pb.Method:
        if name not in self.methods:
            raise EdslError(
                f"extern {self.name} has no method {name!r}; "
                f"methods are {', '.join(self.methods) or 'none'}"
            )
        return self.methods[name]

    def build(self) -> pb.ExternType:
        return pb.ExternType(
            name=self.name,
            constructor_params=self.constructor_params,
            methods=list(self.methods.values()),
        )


class ExternInstance:
    """A declared instance of an extern type, with its constructor arguments."""

    def __init__(self, name: str, extern_type: ExternType, args: Sequence[pb.Literal]) -> None:
        if not name:
            raise EdslError("an extern instance needs a name")
        self.name = name
        self.extern_type = extern_type
        self.args = list(args)

    def build(self) -> pb.ExternInstance:
        return pb.ExternInstance(name=self.name, extern_type=self.extern_type.name, args=self.args)


@dataclass
class TypeTable:
    """Every declaration of one program that an expression may need."""

    headers: dict[str, HeaderType] = field(default_factory=dict)
    structs: dict[str, StructType] = field(default_factory=dict)
    enums: dict[str, list[str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def fields(self, t: pb.Type) -> dict[str, pb.Type] | None:
        """The fields of a header or struct type; None for any other type."""
        match t.WhichOneof("kind"):
            case "header":
                return self.headers[t.header].fields
            case "struct":
                return self.structs[t.struct].fields
            case _:
                return None
