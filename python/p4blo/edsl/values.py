# pyright: strict
"""Values: bit strings, booleans, enum and error members, and their widths.

The static rules, which pyright checks and every run-time check of the
core builder backs:

- `Bits[W]` is any value of type `bit<W>`; `Var[W]`, a subclass, is a
  place holding one: a field, a local, an `out`/`inout` parameter. The
  aliases `bit1`..`bit64` name places, `bitN = Var[L[N]]`, because they
  appear in declarations; `bit(n)` is the same for a width computed at
  run time, typed `Var[Any]`.
- A literal is written `bit8(1)`; it takes the alias's width. To the
  checker it is what the alias names, a `Var[L[8]]`, so that an action
  parameter declared `port: bit9` accepts `bit9(1)`; at run time a
  literal is no place, and the core refuses writing to it. `Bits(1)`
  alone has no width and is refused at run time.
- Operators are `(self: Bits[W], other: Bits[W] | int) -> Bits[W]`, which
  is the run-time rule: an `int` (an `IntEnum` member included) takes the
  other operand's width and must fit. Comparisons return `Bool`. Shift
  amounts may have any width.
- `concat`, slices and `lookahead` return `Bits[int]`, a width the type
  system cannot know, and no typed place accepts one: `x.as_(bit16)`
  asserts the width at run time and narrows it for the checker.
  `x.cast(bit16)` is a real cast, typed `Bits[L[16]]`.
- `Bool` is a boolean, value or place alike: a `bool` field is declared
  `drop: Bool` and assigned with `self.assign(self.meta.drop, True)`;
  Python `True`/`False` are literals in context. Whether a `Bool` is a
  place is checked at run time, as for `Enum` and `Error` values.
- An `Enum` subclass is a P4 enum whose members are annotated in its
  body (`RED: Color`); an `Errors` subclass declares error names the same
  way (`BadChecksum: Error`); `CoreErrors` holds core.p4's seven. `Error`
  is the type of an error value, place or member alike.
- `In[T]`, `Out[T]` and `InOut[T]` are the directions of block and extern
  parameters. Statically each is `T`: an `Out[bit8]` is a `Var[L[8]]`, so
  passing an expression where a place is required is a static error.
  `Val[T]` is the type an `in` extern parameter accepts, `Bits[Any] | int`,
  with the width of `T` bound and checked at run time; `Const[T]` is an
  `int` constructor argument of that type. At run time the four are read
  from the annotations to derive the IR.
- A value has no truth value: `if x == y:` is refused with the reason;
  control flow is `with self.if_(...)`, and `mux` is the conditional value.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Self, cast, get_args, get_origin, overload
from typing import Literal as L

from p4blo.edsl.core.expr import Expr as CoreExpr
from p4blo.edsl.core.expr import concat as core_concat
from p4blo.edsl.core.expr import literal as core_literal
from p4blo.edsl.core.expr import mux as core_mux
from p4blo.edsl.core.types import TypeTable, boolean, error_t, type_str
from p4blo.edsl.errors import EdslError, provenance
from p4blo.v0 import p4blo_pb2 as pb

# Literals need no declarations, so one empty table serves them all; every
# check the core makes compares `pb.Type`s, never tables.
LITERALS = TypeTable()

# -- directions ---------------------------------------------------------------

type In[T] = T
"""An `in` parameter of type T."""

type Out[T] = T
"""An `out` parameter: a place of type T."""

type InOut[T] = T
"""An `inout` parameter: a place of type T."""

type Val[T] = Bits[Any] | int
"""What an `in` extern parameter of type T accepts: any bit string or int;
the width is T's and is checked at run time."""

type Const[T] = int
"""An extern constructor argument: an int literal of type T."""


# -- the common base ----------------------------------------------------------


@dataclass(frozen=True)
class Ref:
    """An unbound path: a field of a type rather than of a value, as
    `headers.ipv4.dstAddr` names one in a class body. A table key written
    this way binds to the block parameter of that type when the block is
    assembled."""

    root: type
    path: tuple[str | int, ...]
    type: pb.Type

    def __str__(self) -> str:
        steps = "".join(f".{p}" if isinstance(p, str) else f"[{p}]" for p in self.path)
        return f"{self.root.__name__}{steps}"

    def child(self, step: str | int, type: pb.Type) -> Ref:
        return Ref(self.root, (*self.path, step), type)


class Value:
    """A typed value: what a core `Expr` is at the surface.

    Bound values hold their core expression; unbound ones hold a `Ref`.
    Nothing here is public, so that a view's field may take any name.
    """

    _core: CoreExpr | None = None
    _ref: Ref | None = None

    @classmethod
    def _at(cls, core: CoreExpr | None, ref: Ref | None = None) -> Self:
        obj = object.__new__(cls)
        obj._core = core
        obj._ref = ref
        return obj

    @property
    def _expr(self) -> CoreExpr:
        if self._core is None:
            if self._ref is not None:
                raise EdslError(
                    f"{self._ref} names a field of the type {self._ref.root.__name__}, "
                    "not a value; a path through a type is only for table keys, and "
                    "inside a block the value is reached through the block's parameter"
                )
            raise EdslError(f"{self!r} is not a value here")
        return self._core

    @property
    def _pb_type(self) -> pb.Type:
        if self._ref is not None and self._core is None:
            return self._ref.type
        return self._expr.type

    def __repr__(self) -> str:
        if self._core is None and self._ref is not None:
            return f"{type(self).__name__}({self._ref})"
        return f"{type(self).__name__}({type_str(self._pb_type)})"

    def __bool__(self) -> bool:
        raise EdslError(
            f"{self!r} has no truth value; use `with self.if_(cond):` for control flow, "
            "mux(cond, a, b) for a conditional value, and & | ~ for logic"
        )

    def __hash__(self) -> int:
        return id(self)


def operand(value: object) -> CoreExpr | int | bool:
    """`value` as the core takes it: a core expression, or a Python int or
    bool literal that takes its type from context."""
    if isinstance(value, Value):
        return value._expr  # pyright: ignore[reportPrivateUsage]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)  # an IntEnum member is its int
    raise EdslError(f"not a value: {value!r}")


# -- bit strings --------------------------------------------------------------


def width_of(t: object) -> int | None:
    """The width a `Bits[L[N]]` or `Var[L[N]]` type carries; None when it
    carries `Any` or is not such a type."""
    origin = get_origin(t)
    if origin is not Bits and origin is not Var:
        return None
    args = get_args(t)
    if len(args) != 1 or get_origin(args[0]) is not L:
        return None
    literal_args = get_args(args[0])
    if len(literal_args) != 1:
        return None
    n = literal_args[0]
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return None
    return n


type _CoreOperand = CoreExpr | int | bool
type _Binary = Callable[[CoreExpr, _CoreOperand], CoreExpr]


def _bits(core: CoreExpr) -> Bits[Any]:
    return Bits[Any]._at(core)  # pyright: ignore[reportPrivateUsage]


def _bool(core: CoreExpr) -> Bool:
    return Bool._at(core)  # pyright: ignore[reportPrivateUsage]


class Bits[W: int](Value):
    """A value of type `bit<W>`; see the module docstring for the rules."""

    _lit: int | None = None

    def __init__(self, value: int) -> None:
        """A literal; the width comes from the alias it is called through,
        `bit8(1)`, and is resolved when the literal is first used."""
        if isinstance(value, bool) or not isinstance(value, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise EdslError(f"a bit<N> literal is an int, got {value!r}")
        self._lit = int(value)

    @property
    def _expr(self) -> CoreExpr:
        if self._core is None and self._lit is not None:
            width = width_of(getattr(self, "__orig_class__", None))
            if width is None:
                raise EdslError(
                    f"a literal needs a width: write bit8({self._lit}) or bit(n)({self._lit}), "
                    f"not Bits({self._lit})"
                )
            with provenance():
                self._core = core_literal(LITERALS, self._lit, pb.Type(bits=width))
        return super()._expr

    @property
    def width(self) -> int:
        with provenance():
            return self._expr.width

    # -- arithmetic and bitwise, all `Bits[W] x (Bits[W] | int) -> Bits[W]` --

    def _binary(self, op: _Binary, other: object) -> Bits[W]:
        with provenance():
            return _bits(op(self._expr, operand(other)))

    def _reflected(self, op: _Binary, other: object) -> Bits[W]:
        """`other op self` with `other` an int: it takes this width first."""
        with provenance():
            left = core_literal(LITERALS, operand(other), self._expr.type)
            return _bits(op(left, self._expr))

    def __add__(self, other: Bits[W] | int) -> Bits[W]:
        return self._binary(lambda a, b: a + b, other)

    def __radd__(self, other: int) -> Bits[W]:
        return self._reflected(lambda a, b: a + b, other)

    def __sub__(self, other: Bits[W] | int) -> Bits[W]:
        return self._binary(lambda a, b: a - b, other)

    def __rsub__(self, other: int) -> Bits[W]:
        return self._reflected(lambda a, b: a - b, other)

    def __mul__(self, other: Bits[W] | int) -> Bits[W]:
        return self._binary(lambda a, b: a * b, other)

    def __rmul__(self, other: int) -> Bits[W]:
        return self._reflected(lambda a, b: a * b, other)

    def add_sat(self, other: Bits[W] | int) -> Bits[W]:
        """Saturating add, P4's `|+|`."""
        return self._binary(lambda a, b: a.add_sat(b), other)

    def sub_sat(self, other: Bits[W] | int) -> Bits[W]:
        """Saturating subtract, P4's `|-|`."""
        return self._binary(lambda a, b: a.sub_sat(b), other)

    def __and__(self, other: Bits[W] | int) -> Bits[W]:
        return self._binary(lambda a, b: a & b, other)

    def __rand__(self, other: int) -> Bits[W]:
        return self._reflected(lambda a, b: a & b, other)

    def __or__(self, other: Bits[W] | int) -> Bits[W]:
        return self._binary(lambda a, b: a | b, other)

    def __ror__(self, other: int) -> Bits[W]:
        return self._reflected(lambda a, b: a | b, other)

    def __xor__(self, other: Bits[W] | int) -> Bits[W]:
        return self._binary(lambda a, b: a ^ b, other)

    def __rxor__(self, other: int) -> Bits[W]:
        return self._reflected(lambda a, b: a ^ b, other)

    def __lshift__(self, other: Bits[Any] | int) -> Bits[W]:
        return self._binary(lambda a, b: a << b, other)

    def __rshift__(self, other: Bits[Any] | int) -> Bits[W]:
        return self._binary(lambda a, b: a >> b, other)

    def __invert__(self) -> Bits[W]:
        with provenance():
            return _bits(~self._expr)

    def __neg__(self) -> Bits[W]:
        with provenance():
            return _bits(-self._expr)

    # -- comparisons, `-> Bool` --------------------------------------------

    def _compare(self, op: _Binary, other: object) -> Bool:
        with provenance():
            return _bool(op(self._expr, operand(other)))

    def __eq__(self, other: Bits[W] | int) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._compare(lambda a, b: a == b, other)

    def __ne__(self, other: Bits[W] | int) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._compare(lambda a, b: a != b, other)

    def __lt__(self, other: Bits[W] | int) -> Bool:
        return self._compare(lambda a, b: a < b, other)

    def __le__(self, other: Bits[W] | int) -> Bool:
        return self._compare(lambda a, b: a <= b, other)

    def __gt__(self, other: Bits[W] | int) -> Bool:
        return self._compare(lambda a, b: a > b, other)

    def __ge__(self, other: Bits[W] | int) -> Bool:
        return self._compare(lambda a, b: a >= b, other)

    __hash__ = Value.__hash__

    # -- width changes -----------------------------------------------------

    def __getitem__(self, key: slice) -> Bits[int]:
        """`x[hi:lo]`, a bit slice; its width is `hi - lo + 1`, unknown to the checker."""
        with provenance():
            return _bits(self._expr[key])

    def cast[V: int](self, to: type[Bits[V]]) -> Bits[V]:
        """An explicit cast to `bit<V>`, the one way a cast enters the IR."""
        with provenance():
            return _bits(self._expr.cast(_width_type(to, "cast")))

    def as_[V: int](self, to: type[Bits[V]]) -> Bits[V]:
        """The same value, asserted to have width V: a check, not a cast.
        Narrows `Bits[Any]` (a concat, a slice, a lookahead) for the checker."""
        with provenance():
            expected = _width_type(to, "as_")
            if self._expr.type != expected:
                raise EdslError(
                    f"as_: the value is {type_str(self._expr.type)}, not {type_str(expected)}"
                )
            return _bits(self._expr)


def _width_type(to: object, what: str) -> pb.Type:
    width = width_of(to)
    if width is None:
        raise EdslError(f"{what} needs a bit<N> type such as bit16 or bit(n), got {to!r}")
    return pb.Type(bits=width)


class Var[W: int](Bits[W]):
    """A place holding a `bit<W>`: a field, a local, an out/inout parameter.

    `Var[L[8]]` is what `bit8` names in a declaration; calling it,
    `bit8(1)`, makes a literal of that width (see `Bits.__init__`), which
    the core refuses as a place at run time.
    """


def bit(n: int) -> type[Var[Any]]:
    """`bit<n>` for an `n` known only at run time; `bit(n)(v)` is a literal.
    The checker sees `Var[Any]`, so a program written with it is checked
    for widths at run time alone."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:  # pyright: ignore[reportUnnecessaryIsInstance]
        raise EdslError(f"bit(n) needs an integer n >= 1, got {n!r}")
    literal: Any = cast(Any, L)[n]
    return cast("type[Var[Any]]", cast(Any, Var)[literal])


# The aliases pyright reads: a place of each common width.
bit1 = Var[L[1]]
bit2 = Var[L[2]]
bit3 = Var[L[3]]
bit4 = Var[L[4]]
bit5 = Var[L[5]]
bit6 = Var[L[6]]
bit7 = Var[L[7]]
bit8 = Var[L[8]]
bit9 = Var[L[9]]
bit10 = Var[L[10]]
bit11 = Var[L[11]]
bit12 = Var[L[12]]
bit13 = Var[L[13]]
bit14 = Var[L[14]]
bit15 = Var[L[15]]
bit16 = Var[L[16]]
bit17 = Var[L[17]]
bit18 = Var[L[18]]
bit19 = Var[L[19]]
bit20 = Var[L[20]]
bit21 = Var[L[21]]
bit22 = Var[L[22]]
bit23 = Var[L[23]]
bit24 = Var[L[24]]
bit25 = Var[L[25]]
bit26 = Var[L[26]]
bit27 = Var[L[27]]
bit28 = Var[L[28]]
bit29 = Var[L[29]]
bit30 = Var[L[30]]
bit31 = Var[L[31]]
bit32 = Var[L[32]]
bit33 = Var[L[33]]
bit34 = Var[L[34]]
bit35 = Var[L[35]]
bit36 = Var[L[36]]
bit37 = Var[L[37]]
bit38 = Var[L[38]]
bit39 = Var[L[39]]
bit40 = Var[L[40]]
bit41 = Var[L[41]]
bit42 = Var[L[42]]
bit43 = Var[L[43]]
bit44 = Var[L[44]]
bit45 = Var[L[45]]
bit46 = Var[L[46]]
bit47 = Var[L[47]]
bit48 = Var[L[48]]
bit49 = Var[L[49]]
bit50 = Var[L[50]]
bit51 = Var[L[51]]
bit52 = Var[L[52]]
bit53 = Var[L[53]]
bit54 = Var[L[54]]
bit55 = Var[L[55]]
bit56 = Var[L[56]]
bit57 = Var[L[57]]
bit58 = Var[L[58]]
bit59 = Var[L[59]]
bit60 = Var[L[60]]
bit61 = Var[L[61]]
bit62 = Var[L[62]]
bit63 = Var[L[63]]
bit64 = Var[L[64]]


def concat(left: Bits[Any], right: Bits[Any], *rest: Bits[Any]) -> Bits[int]:
    """`left ++ right ++ ...`, the first operand in the high bits, chained
    from the left as P4's `++` associates. The width is the sum, which the
    checker cannot see: narrow it with `as_` where a width is needed."""
    with provenance():
        exprs = [_expr_of(x, "concat") for x in (left, right, *rest)]
        return _bits(core_concat(exprs[0], exprs[1], *exprs[2:]))


@overload
def mux[W: int](
    condition: Bool | bool, then: Bits[W] | int, otherwise: Bits[W] | int
) -> Bits[W]: ...
@overload
def mux(condition: Bool | bool, then: Bool | bool, otherwise: Bool | bool) -> Bool: ...
def mux(condition: object, then: object, otherwise: object) -> Bits[Any] | Bool:
    """`condition ? then : otherwise`; the branches share one type, which
    an int branch takes from the other."""
    with provenance():
        result = core_mux(operand(condition), operand(then), operand(otherwise))
        return _bool(result) if result.type == boolean else _bits(result)


def _expr_of(value: object, what: str) -> CoreExpr:
    if not isinstance(value, Value):
        raise EdslError(f"{what} needs values with a width; an int has none of its own")
    return value._expr  # pyright: ignore[reportPrivateUsage]


# -- booleans -----------------------------------------------------------------


class Bool(Value):
    """A boolean value; comparisons produce one, `if_` and `verify` take one."""

    def _binary(self, op: _Binary, other: object) -> Bool:
        with provenance():
            return _bool(op(self._expr, operand(other)))

    def __and__(self, other: Bool | bool) -> Bool:
        return self._binary(lambda a, b: a & b, other)

    def __rand__(self, other: bool) -> Bool:
        return self._binary(lambda a, b: a & b, other)

    def __or__(self, other: Bool | bool) -> Bool:
        return self._binary(lambda a, b: a | b, other)

    def __ror__(self, other: bool) -> Bool:
        return self._binary(lambda a, b: a | b, other)

    def __invert__(self) -> Bool:
        with provenance():
            return _bool(~self._expr)

    def __eq__(self, other: Bool | bool) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._binary(lambda a, b: a == b, other)

    def __ne__(self, other: Bool | bool) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self._binary(lambda a, b: a != b, other)

    __hash__ = Value.__hash__


# -- enums and errors ---------------------------------------------------------


def _own_annotations(cls: type) -> list[str]:
    """The names annotated in this class's own body, in order."""
    annotations = cls.__dict__.get("__annotations__", {})
    return [name for name in cast("dict[str, object]", annotations) if not name.startswith("_")]


class Enum(Value):
    """A P4 enum type, declared as a class whose body annotates its
    members with the class itself:

        class Color(Enum):
            RED: Color
            GREEN: Color

    `Color.RED` is the member literal; a field or local of type `Color`
    holds one. The IR name is the class name unless `name=` is given.
    """

    __ir_name__: ClassVar[str] = ""
    __members__: ClassVar[tuple[str, ...]] = ()
    _member: str | None = None

    def __init_subclass__(cls, name: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.__ir_name__ = name or cls.__name__
        members = tuple(_own_annotations(cls))
        if not members:
            raise EdslError(
                f"enum {cls.__ir_name__} needs at least one member, `NAME: {cls.__name__}`"
            )
        cls.__members__ = members
        t = pb.Type(enum_type=cls.__ir_name__)
        for m in members:
            lit = pb.Literal(enum_member=pb.EnumLiteral(enum_type=cls.__ir_name__, member=m))
            value = cls._at(CoreExpr(LITERALS, t, pb.Expr(literal=lit)))
            value._member = m
            setattr(cls, m, value)

    @classmethod
    def _pb_type_of(cls) -> pb.Type:
        return pb.Type(enum_type=cls.__ir_name__)

    def __repr__(self) -> str:
        if self._member is not None:
            return f"{type(self).__name__}.{self._member}"
        return super().__repr__()

    def __eq__(self, other: Self) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        with provenance():
            return _bool(self._expr == operand(other))

    def __ne__(self, other: Self) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        with provenance():
            return _bool(self._expr != operand(other))

    __hash__ = Value.__hash__


class Error(Value):
    """An error value: a member of an `Errors` set, or a place of type `error`."""

    _member: str | None = None

    @classmethod
    def _named(cls, name: str) -> Error:
        value = cls._at(CoreExpr(LITERALS, error_t, pb.Expr(literal=pb.Literal(error=name))))
        value._member = name
        return value

    @property
    def name(self) -> str:
        """The error's name, when this is a member."""
        if self._member is None:
            raise EdslError(f"{self!r} is a place of type error, not an error name")
        return self._member

    def __repr__(self) -> str:
        if self._member is not None:
            return f"Error({self._member})"
        return super().__repr__()

    def __eq__(self, other: Error) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        with provenance():
            return _bool(self._expr == operand(other))

    def __ne__(self, other: Error) -> Bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        with provenance():
            return _bool(self._expr != operand(other))

    __hash__ = Value.__hash__


class Errors:
    """A set of error declarations, one class-body annotation per name:

        class errors(Errors):
            BadChecksum: Error

    `errors.BadChecksum` is the member; `Program(errors=errors)` declares
    the set after core.p4's seven, which `CoreErrors` holds.
    """

    __members__: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        members = tuple(_own_annotations(cls))
        if not members:
            raise EdslError(f"{cls.__name__} declares no error; annotate each as `NAME: Error`")
        cls.__members__ = members
        for m in members:
            setattr(cls, m, Error._named(m))  # pyright: ignore[reportPrivateUsage]


class CoreErrors(Errors):
    """core.p4's errors, which every program starts with."""

    NoError: Error
    PacketTooShort: Error
    NoMatch: Error
    StackOutOfBounds: Error
    HeaderTooShort: Error
    ParserTimeout: Error
    ParserInvalidArgument: Error


__all__ = [
    "Bits",
    "Bool",
    "Const",
    "CoreErrors",
    "Enum",
    "Error",
    "Errors",
    "In",
    "InOut",
    "L",
    "LITERALS",
    "Out",
    "Ref",
    "Val",
    "Value",
    "Var",
    "bit",
    "bit1",
    "bit2",
    "bit3",
    "bit4",
    "bit5",
    "bit6",
    "bit7",
    "bit8",
    "bit9",
    "bit10",
    "bit11",
    "bit12",
    "bit13",
    "bit14",
    "bit15",
    "bit16",
    "bit17",
    "bit18",
    "bit19",
    "bit20",
    "bit21",
    "bit22",
    "bit23",
    "bit24",
    "bit25",
    "bit26",
    "bit27",
    "bit28",
    "bit29",
    "bit30",
    "bit31",
    "bit32",
    "bit33",
    "bit34",
    "bit35",
    "bit36",
    "bit37",
    "bit38",
    "bit39",
    "bit40",
    "bit41",
    "bit42",
    "bit43",
    "bit44",
    "bit45",
    "bit46",
    "bit47",
    "bit48",
    "bit49",
    "bit50",
    "bit51",
    "bit52",
    "bit53",
    "bit54",
    "bit55",
    "bit56",
    "bit57",
    "bit58",
    "bit59",
    "bit60",
    "bit61",
    "bit62",
    "bit63",
    "bit64",
    "concat",
    "mux",
    "operand",
    "width_of",
]
