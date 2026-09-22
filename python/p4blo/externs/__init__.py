"""The extern registry.

At the IR level an extern is a declared type with method signatures, an
instance with constructor arguments, and call sites. This package binds each
instance to a Python implementation at load time and refuses to load on any
mismatch between the program's declaration and what the implementation
provides: method names, arity, directions and widths.

An implementation describes the family of declarations it accepts with a
`Shape`: the constructor and method parameters, where a width may be a
variable such as `"T"` that the declaration binds consistently. `Register`
is the example: `read(out T result, in bit<32> index)` and
`write(in bit<32> index, in T value)` for any width `T`.

The implementations under this package are corpus material: each is pinned
to its Lean model by vectors. They are not part of the IR.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from p4blo.interp import ExternBinding
from p4blo.interp.values import Bits, EnumValue, ErrorValue, Value
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


class BindError(Exception):
    """A program's extern declaration does not match its implementation."""


type Width = int | str
"""A bit width, or the name of a width variable bound by the declaration."""


@dataclass(frozen=True)
class ParamShape:
    direction: pb.Direction.ValueType
    width: Width


@dataclass(frozen=True)
class MethodShape:
    params: tuple[ParamShape, ...]
    returns: Width | None = None


@dataclass(frozen=True)
class Shape:
    """The declarations an implementation accepts."""

    constructor: tuple[Width, ...]
    methods: dict[str, MethodShape]


@dataclass
class Bindings:
    """Width variables bound while matching a declaration against a shape."""

    widths: dict[str, int] = field(default_factory=dict)

    def unify(self, expected: Width, type: pb.Type, where: str) -> None:
        if type.WhichOneof("kind") != "bits":
            raise BindError(f"{where}: expected bits, got {type.WhichOneof('kind')}")
        if isinstance(expected, int):
            if type.bits != expected:
                raise BindError(f"{where}: expected bit<{expected}>, got bit<{type.bits}>")
            return
        bound = self.widths.setdefault(expected, type.bits)
        if bound != type.bits:
            raise BindError(f"{where}: {expected} is bit<{bound}> elsewhere, bit<{type.bits}> here")


def match_shape(decl: pb.ExternType, shape: Shape) -> Bindings:
    """Check `decl` against `shape`; return the width bindings or raise."""
    bindings = Bindings()
    name = decl.name
    if len(decl.constructor_params) != len(shape.constructor):
        raise BindError(
            f"{name}: constructor takes {len(shape.constructor)} args, "
            f"declared {len(decl.constructor_params)}"
        )
    for i, (param, width) in enumerate(
        zip(decl.constructor_params, shape.constructor, strict=True)
    ):
        if param.direction != pb.DIRECTION_IN:
            raise BindError(f"{name}: constructor param {i} must be in")
        bindings.unify(width, param.type, f"{name} constructor param {i}")
    declared = {m.name: m for m in decl.methods}
    if set(declared) != set(shape.methods):
        raise BindError(
            f"{name}: methods {sorted(declared)} declared, {sorted(shape.methods)} implemented"
        )
    for method_name, method_shape in shape.methods.items():
        method = declared[method_name]
        where = f"{name}.{method_name}"
        if len(method.params) != len(method_shape.params):
            raise BindError(f"{where}: {len(method_shape.params)} params expected")
        for i, (param, expected) in enumerate(zip(method.params, method_shape.params, strict=True)):
            if param.direction != expected.direction:
                raise BindError(f"{where} param {i}: direction mismatch")
            bindings.unify(expected.width, param.type, f"{where} param {i}")
        if (method_shape.returns is None) != (not method.HasField("returns")):
            raise BindError(f"{where}: return type mismatch")
        if method_shape.returns is not None:
            bindings.unify(method_shape.returns, method.returns, f"{where} return")
    return bindings


type Factory = Callable[[pb.ExternType, Bindings, Sequence[Value]], ExternBinding]
"""Builds a binding from the declaration, its width bindings and the
constructor argument values."""


@dataclass(frozen=True)
class Implementation:
    """A Python implementation of one family of extern types."""

    extern_type: str
    shape: Shape
    factory: Factory


@dataclass
class Registry:
    implementations: dict[str, Implementation] = field(default_factory=dict)

    def register(self, impl: Implementation) -> None:
        if impl.extern_type in self.implementations:
            raise ValueError(f"{impl.extern_type} registered twice")
        self.implementations[impl.extern_type] = impl

    def bind(self, index: Index) -> dict[str, ExternBinding]:
        """One binding per extern instance of the program, by instance name.

        Raises `BindError` on a declaration without an implementation or with
        a mismatched shape, and on constructor arguments that do not fit.
        """
        bound: dict[str, ExternBinding] = {}
        for instance in index.program.extern_instances:
            decl = index.extern_types[instance.extern_type]
            impl = self.implementations.get(decl.name)
            if impl is None:
                raise BindError(f"no implementation for extern type {decl.name!r}")
            bindings = match_shape(decl, impl.shape)
            args = [literal_value(lit, index) for lit in instance.args]
            for i, (param, value) in enumerate(zip(decl.constructor_params, args, strict=False)):
                if not fits(value, param.type):
                    raise BindError(f"{instance.name}: constructor arg {i} does not fit")
            bound[instance.name] = impl.factory(decl, bindings, args)
        return bound


def literal_value(lit: pb.Literal, index: Index) -> Value:
    """The value of a literal."""
    match lit.WhichOneof("value"):
        case "bits":
            return Bits(lit.bits.width, int(lit.bits.value))
        case "boolean":
            return lit.boolean
        case "enum_member":
            return EnumValue(lit.enum_member.enum_type, lit.enum_member.member)
        case "error":
            return ErrorValue(lit.error)
        case _:
            raise ValueError("literal has no value")


def fits(value: Value, type: pb.Type) -> bool:
    """Whether a value has exactly this type (bits, boolean, enum, error)."""
    match type.WhichOneof("kind"):
        case "bits":
            return isinstance(value, Bits) and value.width == type.bits
        case "boolean":
            return isinstance(value, bool)
        case "enum_type":
            return isinstance(value, EnumValue) and value.enum_type == type.enum_type
        case "error":
            return isinstance(value, ErrorValue)
        case _:
            return False


def default_registry() -> Registry:
    """Every implementation shipped with the corpus."""
    from p4blo.externs import checksum, counter, register

    registry = Registry()
    registry.register(register.IMPLEMENTATION)
    registry.register(counter.IMPLEMENTATION)
    registry.register(checksum.IMPLEMENTATION)
    return registry


__all__ = [
    "BindError",
    "Bindings",
    "Factory",
    "Implementation",
    "MethodShape",
    "ParamShape",
    "Registry",
    "Shape",
    "default_registry",
    "fits",
    "literal_value",
    "match_shape",
]
