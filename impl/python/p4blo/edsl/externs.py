# pyright: strict
"""Externs: a family is a class whose methods are typed signatures.

    class Register[T: Bits[Any]](Extern, name="register"):
        def __init__(self, name: str, size: Const[bit32]) -> None: ...
        def read(self, result: Out[T], index: In[Val[bit32]]) -> None: ...
        def write(self, index: In[Val[bit32]], value: In[Val[T]]) -> None: ...

    r = Register[bit8]("r", size=256)      # binds T
    r.read(self.meta.x, self.meta.idx)     # in a block body: a call_extern

The static rules:

- An instance is `Family[bit8](name, args...)`: the type argument binds the
  family's width and the instance is what a program lists in
  `externs=[...]`. A method call is checked against its signature: names,
  argument count, and for an `Out`/`InOut` parameter, `Out[T]`, that the
  argument is a place of exactly that type (`Var[L[8]]` for `bit8`), so
  an expression there is a static error. An `in` parameter is written
  `In[Val[T]]`: it accepts any bit string or int, and its width is bound
  from `T` and checked at run time by the core.
- A method with a result, `def compute(self, data: In[Val[T]]) -> Bits[L[16]]`,
  is used in expression position: `self.assign(x, csum.compute(d))`
  records one `call_extern` whose result is `x`. The result may be used
  nowhere else, and a result left unassigned fails the build.
- A method without a result is a statement: `pkts.count(idx)` records
  into the block body being assembled.

At run time `__init_subclass__` replaces each method with a recorder and
the signatures, read with `get_type_hints` and the instance's type
arguments, derive the IR `ExternType`: constructor parameters from
`__init__`'s `Const[...]` parameters, methods from theirs. The IR type
name is the class keyword `name=`, or `type_name=` on an instance when a
program needs two widths of one family (`register.16`, say).
"""

from __future__ import annotations

import functools
import inspect
import types
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
from typing import (
    Literal as L,
)

from p4blo.edsl.core.types import ExternInstance as CoreExternInstance
from p4blo.edsl.core.types import ExternType as CoreExternType
from p4blo.edsl.core.types import MethodSpec
from p4blo.edsl.core.types import ParamSpec as CoreParam
from p4blo.edsl.errors import EdslError, provenance
from p4blo.edsl.values import Bits, Const, In, Out, Val, bit32
from p4blo.edsl.views import direction_of, pb_type_of
from p4blo.v0 import p4blo_pb2 as pb

if TYPE_CHECKING:
    from p4blo.edsl.program import Build


def _substitute(annotation: object, mapping: dict[Any, object]) -> object:
    """`annotation` with the class's type variables replaced."""
    if isinstance(annotation, TypeVar):
        return mapping.get(annotation, annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None or not args:
        return annotation
    new = tuple(_substitute(a, mapping) for a in args)
    if origin is Union or origin is types.UnionType:
        union: Any = new[0]
        for member in new[1:]:
            union = union | member
        return union
    subscriptable: Any = origin
    return subscriptable[new[0] if len(new) == 1 else new]


def _param_type(annotation: object, where: str) -> pb.Type:
    """The IR type of a method or constructor parameter annotation, with
    `Val[T]` and `Const[T]` unwrapped and `| int` dropped."""
    origin = get_origin(annotation)
    if origin is Val or origin is Const:
        annotation = get_args(annotation)[0]
        origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        kept = [a for a in get_args(annotation) if a is not int and a is not bool]
        if len(kept) != 1:
            raise EdslError(f"{where}: {annotation!r} is not one type")
        annotation = kept[0]
    if isinstance(annotation, TypeVar):
        raise EdslError(
            f"{where}: {annotation} is unbound; instantiate the family with its type "
            f"argument, Family[bit8](...)"
        )
    try:
        return pb_type_of(annotation)
    except EdslError as e:
        raise EdslError(f"{where}: {e}") from None


class Extern:
    """The base of every extern family; see the module docstring."""

    __ir_name__: ClassVar[str] = ""
    __methods__: ClassVar[dict[str, Callable[..., object]]] = {}

    def __init_subclass__(cls, name: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.__ir_name__ = name or cls.__name__
        methods = dict(cls.__methods__)
        for attr, member in list(vars(cls).items()):
            if attr.startswith("_") or not inspect.isfunction(member):
                continue
            methods[attr] = member
            setattr(cls, attr, _recorder(attr, member))
        cls.__methods__ = methods

    def __init__(self, name: str, *args: int, type_name: str = "") -> None:
        if not name:
            raise EdslError("an extern instance needs a name")
        self._name = name
        self._args = args
        self._type_name = type_name

    @property
    def name(self) -> str:
        return self._name

    def _type_arguments(self) -> dict[Any, object]:
        cls = type(self)
        params: tuple[Any, ...] = ()
        for klass in cls.__mro__:
            params = getattr(klass, "__type_params__", ())
            if params:
                break
        if not params:
            return {}
        orig = getattr(self, "__orig_class__", None)
        args = get_args(orig) if orig is not None else ()
        if len(args) != len(params):
            raise EdslError(
                f"{cls.__name__} needs its type argument: {cls.__name__}[bit8]({self._name!r}, ...)"
            )
        return dict(zip(params, args, strict=True))

    def _localns(self) -> dict[str, object]:
        return {p.__name__: p for p in self._type_arguments()}

    def _constructor(self) -> list[tuple[str, pb.Type]]:
        cls = type(self)
        init = cls.__init__
        hints = get_type_hints(init, localns=self._localns())
        mapping = self._type_arguments()
        out: list[tuple[str, pb.Type]] = []
        for p in list(inspect.signature(init).parameters.values())[2:]:
            if p.kind in (p.KEYWORD_ONLY, p.VAR_KEYWORD, p.VAR_POSITIONAL):
                continue
            if p.name not in hints:
                raise EdslError(
                    f"{cls.__name__}.__init__: parameter {p.name!r} needs a Const[...] type"
                )
            t = _substitute(hints[p.name], mapping)
            out.append((p.name, _param_type(t, f"{cls.__name__} constructor {p.name}")))
        return out

    def _methods(self) -> dict[str, MethodSpec]:
        cls = type(self)
        mapping = self._type_arguments()
        out: dict[str, MethodSpec] = {}
        for mname, fn in cls.__methods__.items():
            hints = get_type_hints(fn, localns=self._localns())
            params: list[CoreParam] = []
            for p in list(inspect.signature(fn).parameters.values())[1:]:
                where = f"{cls.__name__}.{mname} parameter {p.name}"
                if p.name not in hints:
                    raise EdslError(f"{where} needs an In[...], Out[...] or InOut[...] type")
                direction, t = direction_of(hints[p.name])
                if direction is None:
                    raise EdslError(f"{where} needs a direction: In[...], Out[...] or InOut[...]")
                params.append((p.name, direction, _param_type(_substitute(t, mapping), where)))
            returns = hints.get("return")
            spec_returns = (
                None
                if returns is None or returns is type(None)
                else _param_type(_substitute(returns, mapping), f"{cls.__name__}.{mname} result")
            )
            out[mname] = MethodSpec(params, spec_returns)
        return out

    def _declare(self, build: Build) -> CoreExternInstance:
        """Declare this instance's type (once per name) and the instance."""
        cls = type(self)
        type_name = self._type_name or cls.__ir_name__
        constructor = self._constructor()
        methods = self._methods()
        with provenance():
            declared = CoreExternType(type_name, constructor, methods).build()
        existing = build.extern_types.get(type_name)
        if existing is None:
            with provenance():
                existing = build.core.extern_type(
                    type_name, constructor=constructor, methods=methods
                )
            build.extern_types[type_name] = existing
        elif existing.build() != declared:
            raise EdslError(
                f"extern type {type_name!r} is declared with two signatures; give one "
                f"instance a type_name= such as {type_name!r}.8"
            )
        with provenance():
            return build.core.extern_instance(self._name, existing, *self._args)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._name!r})"


def _recorder(method: str, fn: Callable[..., object]) -> Callable[..., object]:
    sig = inspect.signature(fn)
    sig = sig.replace(parameters=list(sig.parameters.values())[1:])

    @functools.wraps(fn)
    def record(self: Extern, *args: object, **kwargs: object) -> object:
        from p4blo.edsl.blocks import current_block

        try:
            bound = sig.bind(*args, **kwargs)
        except TypeError as e:
            raise EdslError(f"{self.name}.{method}: {e}") from None
        return current_block()._call_extern(self, method, list(bound.arguments.values()))  # pyright: ignore[reportPrivateUsage]

    return record


# -- the families the corpus implements (impl/python/p4blo/arch/externs) ----------------


class Register[T: Bits[Any]](Extern, name="register"):
    """`register<T>`: `read(out T result, in bit<32> index)` and
    `write(in bit<32> index, in T value)`, constructed with a size."""

    def __init__(self, name: str, size: Const[bit32], *, type_name: str = "") -> None:
        super().__init__(name, size, type_name=type_name)

    def read(self, result: Out[T], index: In[Val[bit32]]) -> None: ...

    def write(self, index: In[Val[bit32]], value: In[Val[T]]) -> None: ...


class Counter(Extern, name="counter"):
    """A packet counter array: `count(in bit<32> index)`, constructed with a size."""

    def __init__(self, name: str, size: Const[bit32], *, type_name: str = "") -> None:
        super().__init__(name, size, type_name=type_name)

    def count(self, index: In[Val[bit32]]) -> None: ...


class Checksum16[T: Bits[Any]](Extern, name="checksum16"):
    """The Internet checksum: `bit<16> compute(in T data)`."""

    def __init__(self, name: str, *, type_name: str = "") -> None:
        super().__init__(name, type_name=type_name)

    def compute(self, data: In[Val[T]]) -> Bits[L[16]]: ...


class CRC16[T: Bits[Any]](Extern, name="crc16"):
    """Full CRC-16/ARC: `bit<16> compute(in T data)`, byte-aligned T."""

    def __init__(self, name: str, *, type_name: str = "") -> None:
        super().__init__(name, type_name=type_name)

    def compute(self, data: In[Val[T]]) -> Bits[L[16]]: ...


class CRC32[T: Bits[Any]](Extern, name="crc32"):
    """Full CRC-32/ISO-HDLC: `bit<32> compute(in T data)`, byte-aligned T."""

    def __init__(self, name: str, *, type_name: str = "") -> None:
        super().__init__(name, type_name=type_name)

    def compute(self, data: In[Val[T]]) -> Bits[L[32]]: ...


__all__ = ["CRC16", "CRC32", "Checksum16", "Counter", "Extern", "Register"]
