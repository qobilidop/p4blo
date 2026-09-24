# pyright: strict
"""Views: headers, structs and header stacks as classes.

A header or struct type is a class whose body annotates its fields:

    class ipv4_t(Header):
        ttl: bit8
        dstAddr: bit32

    class headers(Struct):
        ipv4: ipv4_t
        vlan: Stack[vlan_t, L[2]]

The static rules:

- Every field is a real attribute of the declared type, so `hdr.ipv4.tt1`
  is an unknown attribute to the checker and `hdr.eth.type` is the field
  `type`. There is no `__getattr__`. A field named like one of the view's
  own methods (`is_valid`, `field`) or starting with `_` is refused at
  class definition; `rename={"attr": "ir_name"}` gives such a field its
  IR name under another attribute, and `view.field("ir_name")` reaches
  any field by its IR name, for generated code.
- A view reached through a block parameter is bound: its fields are
  places (`Var`, a `Bool`, an `Enum` or `Error` value, a nested view).
  A view reached through the class, `headers.ipv4.dstAddr`, is unbound: a
  path through the type, which only a table key may use; it binds to the
  block parameter of that type when the block is assembled.
- `Stack[H, L[N]]` is a stack of N headers of type H: `s[i]`, `s.next`
  (an extract target only), `s.last` (which is `s[s.last_index]`) and
  `s.last_index`, a `Bits[L[32]]`.
- The IR name of a type is the class name unless `name=` is given as a
  class keyword. Types are program-independent: a program registers each
  one it uses on first use, in the order it meets them.

At run time `__init_subclass__` reads the annotations with `get_type_hints`
and builds the core `HeaderType` or `StructType`, which checks what the IR
requires (a header's fields are `bit<N>` or `bool`).
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, cast, get_args, get_origin
from typing import Literal as L

from p4blo.edsl.core.expr import Expr as CoreExpr
from p4blo.edsl.core.types import HeaderType, StructType, type_str
from p4blo.edsl.errors import EdslError, provenance, user_globals
from p4blo.edsl.values import (
    Bits,
    Bool,
    Enum,
    Error,
    In,
    InOut,
    Out,
    Ref,
    Value,
    Var,
    operand,
    width_of,
)
from p4blo.v0 import p4blo_pb2 as pb

# -- reading annotations ------------------------------------------------------


@dataclass(frozen=True)
class Kind:
    """What a type annotation denotes: the IR type, and how to make the
    value standing for a place of that type (bound to a core expression,
    or unbound with a `Ref`)."""

    pb_type: pb.Type
    make: Callable[[CoreExpr | None, Ref | None], Value]

    def at(self, core: CoreExpr | None, ref: Ref | None) -> Value:
        return self.make(core, ref)


def direction_of(annotation: object) -> tuple[str | None, object]:
    """Split `In[T]`/`Out[T]`/`InOut[T]` into the direction and `T`."""
    origin = get_origin(annotation)
    for marker, direction in ((In, "in"), (Out, "out"), (InOut, "inout")):
        if origin is marker:
            return direction, get_args(annotation)[0]
    return None, annotation


def kind_of(annotation: object) -> Kind:
    """The `Kind` of a field, local or parameter annotation."""
    direction, t = direction_of(annotation)
    if direction is not None:
        raise EdslError(f"{direction} is a parameter direction; a field or local has none")
    width = width_of(t)
    if width is not None:
        return Kind(pb.Type(bits=width), Var[Any]._at)  # pyright: ignore[reportPrivateUsage]
    if get_origin(t) is Bits or get_origin(t) is Var:
        raise EdslError(f"{t!r} has no width; declare a field or local as bit8, bit(n), ...")
    if isinstance(t, type):
        if issubclass(t, Bool):
            return Kind(pb.Type(boolean=pb.BoolType()), Bool._at)  # pyright: ignore[reportPrivateUsage]
        if issubclass(t, Enum):
            return Kind(t._pb_type_of(), t._at)  # pyright: ignore[reportPrivateUsage]
        if issubclass(t, Error):
            return Kind(pb.Type(error=pb.ErrorType()), Error._at)  # pyright: ignore[reportPrivateUsage]
        if issubclass(t, View):
            return Kind(t.__pb_type__, t)
    if get_origin(annotation) is Stack:
        return Stack._kind(annotation)  # pyright: ignore[reportPrivateUsage]
    raise EdslError(
        f"{t!r} is not a p4blo type; use bit8 (or bit(n)), Bool, an Enum, Error, "
        "a Header, a Struct or Stack[H, L[n]]"
    )


def pb_type_of(annotation: object) -> pb.Type:
    return kind_of(annotation).pb_type


def make_value(annotation: object, core: CoreExpr) -> Value:
    """The value of `annotation`'s type standing for the place `core`."""
    return kind_of(annotation).at(core, None)


def own_annotations(cls: type) -> dict[str, object]:
    """The annotations in this class's own body, in order, evaluated.

    A string annotation (`from __future__ import annotations`) is evaluated
    in the defining module's globals and the class namespace, as
    `get_type_hints` would, except that the module need not be importable
    under its name: a corpus program is loaded from its file.
    """
    own = cast("dict[str, object]", cls.__dict__.get("__annotations__", {}))
    if not own:
        return {}
    module = sys.modules.get(cls.__module__)
    globalns = module.__dict__ if module is not None else user_globals()
    localns = dict(vars(cls))
    localns.update(
        {p.__name__: p for p in cast("tuple[Any, ...]", getattr(cls, "__type_params__", ()))}
    )
    out: dict[str, object] = {}
    for name, annotation in own.items():
        if isinstance(annotation, str):
            try:
                annotation = eval(annotation, globalns, localns)  # noqa: S307
            except NameError as e:
                raise EdslError(f"{cls.__name__}: {e}") from None
        if get_origin(annotation) is not ClassVar:
            out[name] = annotation
    return out


# -- views --------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    attr: str
    ir_name: str
    annotation: object
    kind: Kind


class _Field:
    """The class attribute standing for a field: through the class it is
    the unbound path; on an instance the bound value set in `__init__`
    shadows it."""

    def __init__(self, attr: str) -> None:
        self.attr = attr

    def __get__(self, obj: object, owner: type[View]) -> Value:
        spec = owner.__fields__[self.attr]
        if obj is not None:  # a write-only view, `stack.next`, binds no fields
            raise EdslError(f"{obj!r} may only be written to (extracted into), not read")
        return spec.kind.at(None, Ref(owner, (spec.ir_name,), spec.kind.pb_type))


_RESERVED = frozenset({"is_valid", "field"})


class View(Value):
    """The base of `Header` and `Struct`."""

    __ir_name__: ClassVar[str] = ""
    __fields__: ClassVar[dict[str, FieldSpec]] = {}
    __pb_type__: ClassVar[pb.Type] = pb.Type()
    _what: ClassVar[str] = "view"

    def __init_subclass__(
        cls, name: str | None = None, rename: Mapping[str, str] = {}, **kwargs: Any
    ) -> None:
        super().__init_subclass__(**kwargs)
        if cls._what == "view":  # Header and Struct themselves
            return
        cls.__ir_name__ = name or cls.__name__
        fields: dict[str, FieldSpec] = {}
        for attr, annotation in own_annotations(cls).items():
            if attr in _RESERVED or attr.startswith("_"):
                hint = (
                    f"a view's own name; did you mean {attr}_? "
                    f'`rename={{"{attr}_": "{attr}"}}` keeps the IR name'
                )
                raise EdslError(f"{cls._what} {cls.__ir_name__}: field {attr!r} is {hint}")
            try:
                kind = kind_of(annotation)
            except EdslError as e:
                raise EdslError(f"{cls._what} {cls.__ir_name__}, field {attr!r}: {e}") from None
            fields[attr] = FieldSpec(attr, rename.get(attr, attr), annotation, kind)
            setattr(cls, attr, _Field(attr))
        for attr in rename:
            if attr not in fields:
                raise EdslError(f"{cls._what} {cls.__ir_name__}: rename names no field {attr!r}")
        cls.__fields__ = fields
        cls._declare({f.ir_name: f.kind.pb_type for f in fields.values()})

    @classmethod
    def _declare(cls, fields: dict[str, pb.Type]) -> None:
        raise NotImplementedError

    def __init__(self, core: CoreExpr | None = None, ref: Ref | None = None) -> None:
        """A view standing for the place `core`, or for the path `ref`."""
        self._core = core
        self._ref = ref
        if core is not None and core.node is None:
            return  # write-only (`stack.next`): no field can be read
        for spec in type(self).__fields__.values():
            child_core = None if core is None else core.field(spec.ir_name)
            child_ref = None if ref is None else ref.child(spec.ir_name, spec.kind.pb_type)
            setattr(self, spec.attr, spec.kind.at(child_core, child_ref))

    def field(self, name: str) -> Value:
        """The field whose IR name is `name`, whatever its attribute: the
        escape for generated code and renamed fields."""
        for spec in type(self).__fields__.values():
            if spec.ir_name == name:
                return cast(Value, getattr(self, spec.attr))
        fields = ", ".join(s.ir_name for s in type(self).__fields__.values()) or "none"
        raise EdslError(f"{type(self).__ir_name__} has no field {name!r}; fields are {fields}")


class Header(View):
    """A header type; subclass it with `bit<N>` and `bool` fields."""

    _what: ClassVar[str] = "header"

    @classmethod
    def _declare(cls, fields: dict[str, pb.Type]) -> None:
        with provenance():
            # Building the core type is the check, not the result: it is
            # what refuses a header field of struct type here, at the
            # declaration, rather than when a program first uses the class.
            HeaderType(cls.__ir_name__, fields)
        cls.__pb_type__ = pb.Type(header=cls.__ir_name__)

    def is_valid(self) -> Bool:
        with provenance():
            return Bool._at(self._expr.is_valid())  # pyright: ignore[reportPrivateUsage]


class Struct(View):
    """A struct type; subclass it with fields of any type."""

    _what: ClassVar[str] = "struct"

    @classmethod
    def _declare(cls, fields: dict[str, pb.Type]) -> None:
        with provenance():
            StructType(cls.__ir_name__, fields)  # the check, as for a header
        cls.__pb_type__ = pb.Type(struct=cls.__ir_name__)


class Stack[H: Header, N: int](Value):
    """A header stack `H[N]`, declared as a field `Stack[H, L[N]]`."""

    _header: type[Header] = Header
    _size: int = 0

    @classmethod
    def _kind(cls, annotation: object) -> Kind:
        args = get_args(annotation)
        header = args[0] if len(args) == 2 else None
        size_args = get_args(args[1]) if len(args) == 2 and get_origin(args[1]) is L else ()
        size = size_args[0] if len(size_args) == 1 else None
        if (
            not isinstance(header, type)
            or not issubclass(header, Header)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 1
        ):
            raise EdslError(
                f"a stack is Stack[H, L[n]] with H a Header and n >= 1, got {annotation!r}"
            )
        pb_type = pb.Type(stack=pb.StackType(header=header.__ir_name__, size=size))

        def make(core: CoreExpr | None, ref: Ref | None) -> Value:
            stack = cls._at(core, ref)
            stack._header = header
            stack._size = size
            return stack

        return Kind(pb_type, make)

    def _element(self, core: CoreExpr | None, ref: Ref | None) -> H:
        return cast(H, self._header(core, ref))

    def __getitem__(self, index: int | Bits[Any]) -> H:
        """`stack[i]`; an int index is a `bit<32>` literal."""
        if self._core is None and self._ref is not None:
            if isinstance(index, Bits):
                raise EdslError(f"{self._ref}[...] needs an int index in a path through a type")
            return self._element(None, self._ref.child(index, self._header.__pb_type__))
        with provenance():
            return self._element(self._expr[operand(index)], None)

    @property
    def next(self) -> H:
        """`stack.next`, the target of an extract into the stack; write-only."""
        with provenance():
            return self._element(self._expr.next, None)

    @property
    def last_index(self) -> Bits[L[32]]:
        """`stack.lastIndex`."""
        with provenance():
            return Bits[Any]._at(self._expr.last_index)  # pyright: ignore[reportPrivateUsage]

    @property
    def last(self) -> H:
        """`stack.last`, which is `stack[stack.lastIndex]`."""
        return self[self.last_index]

    def __repr__(self) -> str:
        if self._core is None and self._ref is not None:
            return f"Stack({self._ref})"
        return f"Stack({type_str(self._pb_type)})"


def view_class(t: object) -> type[View] | None:
    """The view class an annotation names, through a direction if any."""
    _, inner = direction_of(t)
    if isinstance(inner, type) and issubclass(inner, View):
        return inner
    return None


__all__ = [
    "FieldSpec",
    "Header",
    "Kind",
    "Stack",
    "Struct",
    "View",
    "direction_of",
    "kind_of",
    "make_value",
    "own_annotations",
    "pb_type_of",
    "view_class",
]
