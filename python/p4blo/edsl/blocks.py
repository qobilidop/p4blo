# pyright: strict
"""Blocks: parsers, controls and deparsers as classes.

    class MyParser(Parser[headers, metadata]):
        @state(start=True)
        def start(self) -> Transition:
            self.extract(self.hdr.ethernet)
            return self.select(self.hdr.ethernet.etherType,
                               {EtherType.IPV4: self.parse_ipv4}, default=self.accept)

    class MyIngress(Control[headers, metadata]):
        @action
        def forward(self, port: bit9) -> None:
            self.assign(self.meta.egress_port, port)

        t = Table(keys=[lpm(headers.ipv4.dstAddr)], actions=[forward], default=forward(bit9(1)))

        def apply(self) -> None:
            self.apply_table(self.t)

The static rules:

- `Parser[H, M]`, `Control[H, M]` and `Deparser[H]` type `self.hdr` and
  `self.meta`. A block's parameters are its own class-body annotations
  wrapped in `In`/`Out`/`InOut`, in order, and replace the defaults
  (`hdr`, `meta` with the conventional directions) when there are any; a
  bare annotation, `ex1_run: bit8`, is a block local. Each is a real
  attribute of the declared type, so a typo is a static error.
- A `@state` method returns a `Transition`: `self.goto(self.other)`,
  `self.select(...)`, `self.accept` or `self.reject`. `self.other` is the
  state as an attribute, so a misspelled target is a static error, and
  forward references and loops cost nothing because bodies run only when
  the block is assembled.
- `@action` turns a method into an `Action[P]` with the method's
  parameters after `self` as its `ParamSpec`: `self.forward(port=x)` in
  a body records a call, and `forward(bit9(1))` in the class body is the
  literal a table's `default=` or `entry(...)` takes. Both are checked
  against the declared parameters, names, count and widths. Action
  parameters are directionless in the IR.
- `Table` is a class attribute holding action objects and typed keys;
  `keys=(k1, k2)` as a tuple types the entries for one to four keys, so
  that a const entry value of the wrong width is a static error. A
  `keys=[...]` list is the untyped form, for generated programs; its
  entries are checked at run time alone.
- `self.assign(target: Var[W], value: Bits[W] | int)`: a place on the
  left, anything of that width on the right; `Bool`, `Enum` and `Error`
  places have their own overloads. `self.call(Sub, args...)` calls a
  sub-block, whose arguments are checked at run time against its
  parameters. `self.local(name, bit8)` declares a block local, a `Var`.
- Control flow is explicit: `with self.if_(c):`, `elif_`, `else_`.

The two clocks are documented in `p4blo.edsl.__init__`: a block class is
assembled once per `Program.build()`, when its methods run with a recording
`self`; the IR they record runs per packet.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Concatenate,
    Self,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)
from typing import (
    Literal as L,
)

from p4blo.edsl.core.blocks import (
    ACCEPT,
    REJECT,
    ControlBody,
    DeparserBody,
    DontCare,
    Masked,
    Prefix,
    Range,
    StateBody,
    Stmts,
    dont_care,
    keyset,
    masked,
    prefix,
    range_,
)
from p4blo.edsl.core.blocks import Block as CoreBlock
from p4blo.edsl.core.blocks import Control as CoreControl
from p4blo.edsl.core.blocks import Deparser as CoreDeparser
from p4blo.edsl.core.blocks import Entry as CoreEntry
from p4blo.edsl.core.blocks import Key as CoreKey
from p4blo.edsl.core.blocks import Parser as CoreParser
from p4blo.edsl.core.blocks import Table as CoreTable
from p4blo.edsl.core.expr import Expr as CoreExpr
from p4blo.edsl.core.types import ParamSpec as CoreParam
from p4blo.edsl.core.types import type_str
from p4blo.edsl.errors import EdslError, caller_location, provenance
from p4blo.edsl.values import Bits, Bool, Enum, Error, Value, Var, operand
from p4blo.edsl.views import (
    Header,
    Stack,
    Struct,
    View,
    direction_of,
    kind_of,
    own_annotations,
    view_class,
)
from p4blo.v0 import p4blo_pb2 as pb

if TYPE_CHECKING:
    from p4blo.edsl.program import Build


# -- the recording context ----------------------------------------------------

_ACTIVE: list[Block] = []
"""The blocks being assembled, innermost last: what a bare extern call
records into."""


def current_block() -> Block:
    if not _ACTIVE:
        raise EdslError(
            "not inside a block body: statements belong in a @state, an @action or apply()"
        )
    return _ACTIVE[-1]


# -- transitions --------------------------------------------------------------


class Transition:
    """What a `@state` method returns: the state's one transition."""


class Accept(Transition):
    """`self.accept`: the parser accepts."""

    def __repr__(self) -> str:
        return "accept"


class Reject(Transition):
    """`self.reject`: the parser rejects."""

    def __repr__(self) -> str:
        return "reject"


@dataclass(frozen=True)
class StateRef:
    """A state reached as an attribute, `self.parse_ipv4`: a target."""

    owner: type[Parser[Any, Any]]
    name: str

    def __repr__(self) -> str:
        return f"{self.owner.__name__}.{self.name}"


type Target = StateRef | Accept | Reject

type KeySet = int | bool | Bits[Any] | Enum | Error | Masked | Range | DontCare
"""One select keyset: a constant, `masked(v, m)`, `range_(lo, hi)` or `dont_care`."""

type _CoreKeySet = CoreExpr | int | bool | Masked | Range | DontCare
type _CoreTarget = str | Any  # a state name, or the core's accept/reject values


@dataclass(frozen=True)
class _Goto(Transition):
    target: Target


@dataclass(frozen=True)
class _Select(Transition):
    keys: list[CoreExpr]
    cases: list[tuple[tuple[_CoreKeySet, ...], Target]]
    default: Target | None


class State:
    """What `@state` makes of a method; through an instance it is a `StateRef`."""

    def __init__(self, func: Callable[[Any], Transition], start: bool) -> None:
        self.func = func
        self.start = start
        self.name = func.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, obj: None, owner: type) -> State: ...
    @overload
    def __get__(self, obj: object, owner: type) -> StateRef: ...
    def __get__(self, obj: object | None, owner: type) -> State | StateRef:
        if obj is None:
            return self
        if not issubclass(owner, Parser):
            raise EdslError(f"@state {self.name} belongs in a Parser, not {owner.__name__}")
        return StateRef(cast("type[Parser[Any, Any]]", owner), self.name)


@overload
def state[S](func: Callable[[S], Transition], /) -> State: ...
@overload
def state(*, start: bool = False) -> Callable[[Callable[[Any], Transition]], State]: ...
def state(
    func: Callable[[Any], Transition] | None = None, /, *, start: bool = False
) -> State | Callable[[Callable[[Any], Transition]], State]:
    """Declare a parser state; `start=True` marks the start state (else the
    first state is). The method returns its transition."""
    if func is not None:
        return State(func, start)
    return lambda f: State(f, start)


# -- actions ------------------------------------------------------------------


@dataclass(frozen=True)
class ActionCall:
    """An action with its arguments: what `default=` and `entry(...)` take."""

    action: Action[...]
    args: tuple[object, ...]
    kwargs: Mapping[str, object]

    def __repr__(self) -> str:
        return f"{self.action.name}(...)"


class Action[**P]:
    """What `@action` makes of a method. Calling it makes an `ActionCall`,
    and through a block instance also records a `call_action` statement."""

    def __init__(self, func: Callable[..., None]) -> None:
        self.func = func
        self.name = func.__name__
        self._owner: Block | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: object | None, owner: type) -> Action[P]:
        if obj is None or not isinstance(obj, Block):
            return self
        bound: Action[P] = Action(self.func)
        bound.name = self.name
        bound._owner = obj
        return bound

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> ActionCall:
        call = ActionCall(self, args, kwargs)
        if self._owner is not None:
            self._owner._record_action_call(call)  # pyright: ignore[reportPrivateUsage]
        return call

    def _signature(self) -> inspect.Signature:
        """The parameters after `self`."""
        sig = inspect.signature(self.func)
        params = list(sig.parameters.values())[1:]
        return sig.replace(parameters=params)

    def _params(self) -> list[tuple[str, object]]:
        """`(name, annotation)` per parameter, in order."""
        hints = get_type_hints(self.func)
        out: list[tuple[str, object]] = []
        for p in self._signature().parameters.values():
            if p.kind not in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY, p.KEYWORD_ONLY):
                raise EdslError(f"action {self.name}: parameter {p.name!r} must be a plain one")
            if p.name not in hints:
                raise EdslError(f"action {self.name}: parameter {p.name!r} needs a type")
            _, t = direction_of(hints[p.name])  # action data is directionless in the IR
            out.append((p.name, t))
        return out

    def _arguments(self, call: ActionCall) -> list[object]:
        """The call's arguments in parameter order."""
        try:
            bound = self._signature().bind(*call.args, **call.kwargs)
        except TypeError as e:
            raise EdslError(f"action {self.name}: {e}") from None
        return list(bound.arguments.values())


def action[S, **P](func: Callable[Concatenate[S, P], None]) -> Action[P]:
    """Declare an action; its parameters after `self` are its action data."""
    return Action(func)


# -- tables -------------------------------------------------------------------


class Key[W: int]:
    """A table key: a value and its match kind; `name` is the host-facing
    name, empty for the expression's dotted path."""

    def __init__(self, value: Value, match_kind: pb.MatchKind, name: str) -> None:
        self.value = value
        self.match_kind = match_kind
        self.name = name

    def _invariant(self, w: W) -> W:
        return w


@overload
def exact[W: int](value: Bits[W], name: str = "") -> Key[W]: ...
@overload
def exact(value: Value, name: str = "") -> Key[Any]: ...
def exact(value: Value, name: str = "") -> Key[Any]:
    return Key(value, pb.MATCH_KIND_EXACT, name)


@overload
def lpm[W: int](value: Bits[W], name: str = "") -> Key[W]: ...
@overload
def lpm(value: Value, name: str = "") -> Key[Any]: ...
def lpm(value: Value, name: str = "") -> Key[Any]:
    return Key(value, pb.MATCH_KIND_LPM, name)


@overload
def ternary[W: int](value: Bits[W], name: str = "") -> Key[W]: ...
@overload
def ternary(value: Value, name: str = "") -> Key[Any]: ...
def ternary(value: Value, name: str = "") -> Key[Any]:
    return Key(value, pb.MATCH_KIND_TERNARY, name)


type KeyValue[W: int] = int | Bits[W] | Masked | Prefix | DontCare
"""One entry value: an int or literal for an exact key, `prefix(v, n)` for
an lpm key, `masked(v, m)`, an int or `dont_care` for a ternary key."""


class Entry[KS]:
    """A const entry; `KS` is the tuple of key widths."""

    def __init__(self, keys: tuple[object, ...], action: ActionCall, priority: int) -> None:
        self.keys = keys
        self.action = action
        self.priority = priority

    def _invariant(self, ks: KS) -> KS:
        return ks


@overload
def entry[A: int](
    keys: KeyValue[A] | tuple[KeyValue[A]], action: ActionCall, priority: int = 0
) -> Entry[tuple[A]]: ...
@overload
def entry[A: int, B: int](
    keys: tuple[KeyValue[A], KeyValue[B]], action: ActionCall, priority: int = 0
) -> Entry[tuple[A, B]]: ...
@overload
def entry[A: int, B: int, C: int](
    keys: tuple[KeyValue[A], KeyValue[B], KeyValue[C]], action: ActionCall, priority: int = 0
) -> Entry[tuple[A, B, C]]: ...
@overload
def entry[A: int, B: int, C: int, D: int](
    keys: tuple[KeyValue[A], KeyValue[B], KeyValue[C], KeyValue[D]],
    action: ActionCall,
    priority: int = 0,
) -> Entry[tuple[A, B, C, D]]: ...
@overload
def entry(
    keys: KeyValue[Any] | tuple[KeyValue[Any], ...], action: ActionCall, priority: int = 0
) -> Entry[tuple[Any, ...]]: ...
def entry(keys: object, action: ActionCall, priority: int = 0) -> Entry[Any]:
    """A const entry: one value per key, in order, and the action to run."""
    if not isinstance(action, ActionCall):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise EdslError(f"an entry's action is an action call such as drop(), got {action!r}")
    key_tuple = cast("tuple[object, ...]", keys) if isinstance(keys, tuple) else (keys,)
    return Entry(key_tuple, action, priority)


type AnyAction = Action[...]


class Table[KS]:
    """A table declared as a class attribute of a control. `KS` is the
    tuple of key widths when `keys` is a tuple of one to four keys."""

    @overload
    def __init__[A: int](
        self: Table[tuple[A]],
        keys: tuple[Key[A]],
        *,
        actions: Sequence[AnyAction],
        default: ActionCall | None = None,
        const_default: bool = False,
        entries: Sequence[Entry[tuple[A]]] = (),
        size: int = 0,
    ) -> None: ...
    @overload
    def __init__[A: int, B: int](
        self: Table[tuple[A, B]],
        keys: tuple[Key[A], Key[B]],
        *,
        actions: Sequence[AnyAction],
        default: ActionCall | None = None,
        const_default: bool = False,
        entries: Sequence[Entry[tuple[A, B]]] = (),
        size: int = 0,
    ) -> None: ...
    @overload
    def __init__[A: int, B: int, C: int](
        self: Table[tuple[A, B, C]],
        keys: tuple[Key[A], Key[B], Key[C]],
        *,
        actions: Sequence[AnyAction],
        default: ActionCall | None = None,
        const_default: bool = False,
        entries: Sequence[Entry[tuple[A, B, C]]] = (),
        size: int = 0,
    ) -> None: ...
    @overload
    def __init__[A: int, B: int, C: int, D: int](
        self: Table[tuple[A, B, C, D]],
        keys: tuple[Key[A], Key[B], Key[C], Key[D]],
        *,
        actions: Sequence[AnyAction],
        default: ActionCall | None = None,
        const_default: bool = False,
        entries: Sequence[Entry[tuple[A, B, C, D]]] = (),
        size: int = 0,
    ) -> None: ...
    @overload
    def __init__(
        self: Table[tuple[Any, ...]],
        keys: list[Key[Any]] = ...,
        *,
        actions: Sequence[AnyAction],
        default: ActionCall | None = None,
        const_default: bool = False,
        entries: Sequence[Entry[Any]] = (),
        size: int = 0,
    ) -> None: ...
    def __init__(
        self,
        keys: Sequence[Key[Any]] = (),
        *,
        actions: Sequence[AnyAction],
        default: ActionCall | None = None,
        const_default: bool = False,
        entries: Sequence[Entry[Any]] = (),
        size: int = 0,
    ) -> None:
        self.keys = list(keys)
        self.actions = list(actions)
        self.default = default
        self.const_default = const_default
        self.entries = list(entries)
        self.size = size
        self.name = ""
        self._core: CoreTable | None = None
        for k in self.keys:
            if not isinstance(k, Key):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise EdslError(f"table keys are exact(e), lpm(e) or ternary(e); got {k!r}")
        for a in self.actions:
            if not isinstance(a, Action):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise EdslError(f"a table's actions are @action methods; got {a!r}")

    def _invariant(self, ks: KS) -> KS:
        return ks

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: object | None, owner: type) -> Self:
        if obj is None or not isinstance(obj, Control):
            return self
        return cast(Self, obj._bound_table(self))  # pyright: ignore[reportPrivateUsage]

    def _bound(self, core: CoreTable) -> Table[KS]:
        bound = cast(
            "Table[KS]",
            Table(
                self.keys,
                actions=self.actions,
                default=self.default,
                const_default=self.const_default,
                entries=self.entries,
                size=self.size,
            ),
        )
        bound.name = self.name
        bound._core = core
        return bound


# -- extern results -----------------------------------------------------------


class ExternResult(Bits[Any]):
    """The value of an extern method with a result, pending its assignment:
    `self.assign(x, csum.compute(data))` records one `call_extern` with `x`
    as the result. It cannot be used anywhere else."""

    def __init__(self, instance: object, method: str, args: list[object]) -> None:
        self.instance = instance
        self.method = method
        self.args = args
        self.location = caller_location()

    @property
    def _expr(self) -> CoreExpr:
        raise EdslError(
            f"the result of {self.method}(...) must be assigned directly: "
            f"self.assign(target, {self.method}(...))"
        )


# -- blocks -------------------------------------------------------------------

type ParamDecl = tuple[str, str, object]
"""A block parameter: name, direction, the annotation inside the direction."""


class Block:
    """The base of `Parser`, `Control` and `Deparser`: parameters, locals,
    the statements every kind may record, and the assembly machinery."""

    __ir_name__: ClassVar[str] = ""
    __params__: ClassVar[list[ParamDecl] | None] = None
    __locals__: ClassVar[list[tuple[str, object]]] = []
    __states__: ClassVar[dict[str, State]] = {}
    __actions__: ClassVar[dict[str, Action[...]]] = {}
    __tables__: ClassVar[dict[str, Table[Any]]] = {}
    _kind: ClassVar[str] = ""
    _hdr_type: ClassVar[type[Struct] | None] = None
    _meta_type: ClassVar[type[Struct] | None] = None

    def __init_subclass__(cls, name: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "_kind" in cls.__dict__:
            return  # Parser, Control and Deparser themselves, which set `_kind`
        cls.__ir_name__ = name or cls.__name__
        for base in cast("tuple[object, ...]", getattr(cls, "__orig_bases__", ())):
            origin = get_origin(base)
            if isinstance(origin, type) and issubclass(origin, Block):
                args = get_args(base)
                cls._hdr_type = _struct_arg(cls, args[0]) if len(args) > 0 else None
                cls._meta_type = _struct_arg(cls, args[1]) if len(args) > 1 else None
        params: list[ParamDecl] = []
        locals_: list[tuple[str, object]] = []
        for attr, annotation in own_annotations(cls).items():
            if attr in ("hdr", "meta") and attr not in cls.__dict__.get("__annotations__", {}):
                continue
            direction, t = direction_of(annotation)
            if direction is not None:
                params.append((attr, direction, t))
            else:
                locals_.append((attr, annotation))
        if params:
            cls.__params__ = params
        cls.__locals__ = [*cls.__locals__, *locals_]
        states: dict[str, State] = {}
        actions: dict[str, Action[...]] = {}
        tables: dict[str, Table[Any]] = {}
        for klass in reversed(cls.__mro__):
            for attr, member in vars(klass).items():
                if isinstance(member, State):
                    states[attr] = member
                elif isinstance(member, Action):
                    actions[attr] = member
                elif isinstance(member, Table):
                    tables[attr] = cast("Table[Any]", member)
        cls.__states__, cls.__actions__, cls.__tables__ = states, actions, tables
        if states and cls._kind != "parser":
            raise EdslError(f"{cls._kind} {cls.__ir_name__}: @state belongs in a Parser")
        if (actions or tables) and cls._kind != "control":
            raise EdslError(f"{cls._kind} {cls.__ir_name__}: @action and Table belong in a Control")

    @classmethod
    def _param_decls(cls) -> list[ParamDecl]:
        if cls.__params__ is not None:
            return cls.__params__
        h, m = cls._hdr_type, cls._meta_type
        defaults = {
            "parser": [("hdr", "out", h), ("meta", "inout", m)],
            "control": [("hdr", "inout", h), ("meta", "inout", m)],
            "deparser": [("hdr", "in", h)],
        }[cls._kind]
        for _, _, t in defaults:
            if t is None:
                raise EdslError(
                    f"{cls._kind} {cls.__ir_name__}: give the program's types, "
                    f"{cls._kind.capitalize()}[headers, metadata], or declare its parameters"
                )
        return cast("list[ParamDecl]", defaults)

    def __init__(self, build: Build, core: CoreBlock) -> None:
        self._build = build
        self._core = core
        self._stmts: Stmts | None = None
        self._tables: dict[str, Table[Any]] = {}
        for pname, _, t in type(self)._param_decls():
            setattr(self, pname, kind_of(t).at(core.var(pname), None))
        for lname, t in type(self).__locals__:
            with provenance():
                setattr(self, lname, kind_of(t).at(core.local(lname, kind_of(t).pb_type), None))

    @classmethod
    def _make_core(cls, build: Build) -> CoreBlock:
        raise NotImplementedError

    @classmethod
    def _core_params(cls, build: Build) -> list[CoreParam]:
        return [(n, d, build.pb_type(t)) for n, d, t in cls._param_decls()]

    @classmethod
    def _assemble(cls, build: Build, before: CoreBlock | None) -> CoreBlock:
        """Build this block into `build`, placed before `before` when given."""
        core = cls._make_core(build)
        build.core.add_block(core, before=before)
        build.blocks[cls] = core
        inst = cls(build, core)
        _ACTIVE.append(inst)
        try:
            inst._run()
        finally:
            _ACTIVE.pop()
        return core

    def _run(self) -> None:
        raise NotImplementedError

    def _record(self) -> Stmts:
        if self._stmts is None:
            raise EdslError(
                f"{type(self)._kind} {type(self).__ir_name__}: statements belong in a "
                "@state, an @action or apply()"
            )
        return self._stmts

    # -- statements every block may record ---------------------------------

    @overload
    def assign[W: int](self, target: Var[W], value: Bits[W] | int) -> None: ...
    @overload
    def assign(self, target: Bool, value: Bool | bool) -> None: ...
    @overload
    def assign[E: Enum](self, target: E, value: E) -> None: ...
    @overload
    def assign(self, target: Error, value: Error) -> None: ...
    def assign(self, target: Value, value: object) -> None:
        """`target = value`; an int value takes the target's width."""
        stmts = self._record()
        if isinstance(value, ExternResult):
            self._call_extern_stmt(value, stmts, target)
            return
        with provenance():
            stmts.assign(target._expr, operand(value))  # pyright: ignore[reportPrivateUsage]

    def assign_slice(self, target: Var[Any], hi: int, lo: int, value: int) -> None:
        """`target[hi:lo] = value`, as the read-modify-write the IR has (see
        the core's `assign_slice`)."""
        with provenance():
            self._record().assign_slice(target._expr, hi, lo, value)  # pyright: ignore[reportPrivateUsage]

    @contextmanager
    def if_(self, condition: Bool | bool) -> Generator[None]:
        """`if (condition) { ... }`: the statements inside the `with`."""
        with provenance():
            cm = self._record().if_(operand(condition))
        with cm:
            yield

    @contextmanager
    def elif_(self, condition: Bool | bool) -> Generator[None]:
        """`else if (condition) { ... }`, after an `if_` or `elif_`."""
        with provenance():
            cm = self._record().elif_(operand(condition))
        with cm:
            yield

    @contextmanager
    def else_(self) -> Generator[None]:
        """`else { ... }`, after an `if_` or `elif_`."""
        with provenance():
            cm = self._record().else_()
        with cm:
            yield

    def call(self, block: type[Block], *args: Value | int | bool) -> None:
        """Call a sub-parser or sub-control with arguments for its
        parameters, checked at run time; the callee is built on first use,
        ahead of this block."""
        if not (isinstance(block, type) and issubclass(block, Block)) or not block._kind:  # pyright: ignore[reportUnnecessaryIsInstance]
            raise EdslError(f"call needs a Parser or Control class, got {block!r}")
        callee = self._build.block(block, before=self._core)
        with provenance():
            self._record().call_block(callee, *[operand(a) for a in args])

    def set_valid(self, header: Header) -> None:
        with provenance():
            self._record().set_valid(header._expr)  # pyright: ignore[reportPrivateUsage]

    def set_invalid(self, header: Header) -> None:
        with provenance():
            self._record().set_invalid(header._expr)  # pyright: ignore[reportPrivateUsage]

    def push(self, stack: Stack[Any, Any], count: int) -> None:
        """`stack.push_front(count)`."""
        with provenance():
            self._record().push(stack._expr, count)  # pyright: ignore[reportPrivateUsage]

    def pop(self, stack: Stack[Any, Any], count: int) -> None:
        """`stack.pop_front(count)`."""
        with provenance():
            self._record().pop(stack._expr, count)  # pyright: ignore[reportPrivateUsage]

    @overload
    def local[W: int](self, name: str, type: type[Bits[W]]) -> Var[W]: ...
    @overload
    def local(self, name: str, type: type[Bool]) -> Bool: ...
    @overload
    def local[E: Enum](self, name: str, type: type[E]) -> E: ...
    @overload
    def local(self, name: str, type: type[Error]) -> Error: ...
    @overload
    def local[V: View](self, name: str, type: type[V]) -> V: ...
    def local(self, name: str, type: object) -> Value:
        """Declare a block local of `type` (`bit8`, `bit(n)`, `Bool`, an
        `Enum`, `Error`, a header or struct) and return it, a place."""
        kind = kind_of(type)
        self._build.pb_type(type)
        with provenance():
            return kind.at(self._core.local(name, kind.pb_type), None)

    # -- externs -----------------------------------------------------------

    def _call_extern(self, instance: object, method: str, args: list[object]) -> object:
        """A method call on an extern instance: recorded now when it returns
        nothing, else deferred to the `assign` that takes its result."""
        core_instance = self._build.extern_core(instance)
        with provenance():
            m = core_instance.extern_type.method(method)
        if m.HasField("returns"):
            result = ExternResult(instance, method, args)
            self._build.pending.append(result)
            return result
        with provenance():
            self._record().call(core_instance, method, *[operand(a) for a in args])
        return None

    def _call_extern_stmt(self, result: ExternResult, stmts: Stmts, target: Value) -> None:
        core_instance = self._build.extern_core(result.instance)
        self._build.pending.remove(result)
        with provenance():
            stmts.call(
                core_instance,
                result.method,
                *[operand(a) for a in result.args],
                result=target._expr,  # pyright: ignore[reportPrivateUsage]
            )

    def _record_action_call(self, call: ActionCall) -> None:
        raise EdslError(f"{type(self)._kind} {type(self).__ir_name__} has no actions to call")

    # -- unbound paths -----------------------------------------------------

    def _resolve(self, value: Value, what: str) -> CoreExpr:
        """A bound value's expression, or an unbound path bound to the
        parameter of its type."""
        if value._core is not None:  # pyright: ignore[reportPrivateUsage]
            return value._core  # pyright: ignore[reportPrivateUsage]
        ref = value._ref  # pyright: ignore[reportPrivateUsage]
        if ref is None:
            raise EdslError(f"{what}: {value!r} is not a value")
        candidates = [n for n, _, t in type(self)._param_decls() if view_class(t) is ref.root]
        if len(candidates) != 1:
            params = ", ".join(n for n, _, _ in type(self)._param_decls())
            raise EdslError(
                f"{what}: {ref} binds to the parameter of type {ref.root.__name__}, and "
                f"{type(self).__ir_name__} has {len(candidates)} such parameters ({params})"
            )
        with provenance():
            expr = self._core.var(candidates[0])
            for step in ref.path:
                expr = expr.field(step) if isinstance(step, str) else expr[step]
        return expr


def _struct_arg(cls: type, arg: object) -> type[Struct] | None:
    if isinstance(arg, type) and issubclass(arg, Struct):
        return arg
    raise EdslError(f"{cls.__name__}: the types of a block are Struct classes, got {arg!r}")


class Parser[H: Struct, M: Struct](Block):
    """A parser: `@state` methods, the first (or the one `start=True`) the
    start state; by default over `(out H hdr, inout M meta)`."""

    _kind: ClassVar[str] = "parser"
    hdr: H
    meta: M

    @classmethod
    def _make_core(cls, build: Build) -> CoreBlock:
        with provenance():
            return CoreParser(build.core, cls.__ir_name__, cls._core_params(build))

    def _run(self) -> None:
        cls = type(self)
        core = self._core
        assert isinstance(core, CoreParser)
        if not cls.__states__:
            raise EdslError(f"parser {cls.__ir_name__} has no @state")
        explicit = any(s.start for s in cls.__states__.values())
        for i, (name, st) in enumerate(cls.__states__.items()):
            with provenance():
                body = core.state(name, start=st.start or (i == 0 and not explicit))
            self._stmts = body
            with provenance():
                transition = st.func(self)
            if not isinstance(transition, Transition):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise EdslError(
                    f"state {name} must return its transition: self.goto(...), "
                    f"self.select(...), self.accept or self.reject; got {transition!r}",
                )
            self._transition(body, transition)
            self._stmts = None

    def _transition(self, body: StateBody, transition: Transition) -> None:
        with provenance():
            if isinstance(transition, Accept):
                body.accept()
            elif isinstance(transition, Reject):
                body.reject()
            elif isinstance(transition, _Goto):
                body.transition(self._target(transition.target))
            elif isinstance(transition, _Select):
                cases = [(sets, self._target(t)) for sets, t in transition.cases]
                default = None if transition.default is None else self._target(transition.default)
                body.select(transition.keys, cases, default=default)
            else:
                raise EdslError(f"not a transition: {transition!r}")

    def _target(self, target: Target) -> _CoreTarget:
        if isinstance(target, Accept):
            return ACCEPT
        if isinstance(target, Reject):
            return REJECT
        if not isinstance(target, StateRef):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise EdslError(
                f"a target is a state (self.parse_x), self.accept or self.reject; got {target!r}"
            )
        if target.name not in type(self).__states__ or not issubclass(type(self), target.owner):
            raise EdslError(f"{target} is not a state of parser {type(self).__ir_name__}")
        return target.name

    def _state(self) -> StateBody:
        stmts = self._record()
        if not isinstance(stmts, StateBody):
            raise EdslError("extract, advance, verify and lookahead belong in a @state")
        return stmts

    @property
    def accept(self) -> Accept:
        return Accept()

    @property
    def reject(self) -> Reject:
        return Reject()

    def goto(self, target: Target) -> Transition:
        """Transition unconditionally to `target`."""
        return _Goto(target)

    def select(
        self,
        keys: Value | tuple[Value, ...],
        cases: Mapping[KeySet | tuple[KeySet, ...], Target],
        *,
        default: Target | None = None,
    ) -> Transition:
        """`transition select(keys) { ... }`: `cases` maps a keyset (a tuple
        of them for several keys) to a target, in order; `default` matches
        anything. A keyset repeated, or one after a case that matches
        anything, is refused as unreachable; the two are compared as IR
        keysets, because two equal eDSL values are distinct objects whose
        `==` builds a comparison expression rather than deciding."""
        key_tuple = keys if isinstance(keys, tuple) else (keys,)
        with provenance():
            core_keys = [k._expr for k in key_tuple]  # pyright: ignore[reportPrivateUsage]
        core_cases: list[tuple[tuple[_CoreKeySet, ...], Target]] = []
        seen: list[tuple[pb.KeySet, ...]] = []
        for spec, target in cases.items():
            sets = spec if isinstance(spec, tuple) else (spec,)
            if len(sets) != len(core_keys):
                raise EdslError(f"select has {len(core_keys)} keys; case {spec!r} has {len(sets)}")
            core_sets = tuple(_core_keyset(s) for s in sets)
            with provenance():
                normal = tuple(
                    keyset(self._core.types, s, k.type)
                    for s, k in zip(core_sets, core_keys, strict=True)
                )
            if seen and all(s.WhichOneof("kind") == "dont_care" for s in seen[-1]):
                raise EdslError(f"select: case {spec!r} is unreachable after one matching anything")
            if normal in seen:
                raise EdslError(f"select: case {spec!r} is repeated")
            seen.append(normal)
            core_cases.append((core_sets, target))
        return _Select(core_keys, core_cases, default)

    def extract(self, target: Header) -> None:
        """Extract a header from the packet into `target` (`hdr.ipv4`, or
        `hdr.stack.next`)."""
        with provenance():
            self._state().extract(target._expr)  # pyright: ignore[reportPrivateUsage]

    def advance(self, bits: Bits[Any] | int) -> None:
        """Skip `bits` bits of the packet; the amount is a `bit<32>`."""
        with provenance():
            self._state().advance(operand(bits))

    def verify(self, condition: Bool | bool, error: Error) -> None:
        """Raise `error` unless `condition` holds."""
        stmts = self._state()
        with provenance():
            name = error.name
        if name not in stmts.types.errors:
            raise EdslError(
                f"error {name} is not declared by this program: pass its Errors class "
                "to Program(errors=...)"
            )
        with provenance():
            stmts.verify(operand(condition), name)

    @overload
    def lookahead(self, type: type[Bits[Any]]) -> Bits[int]: ...
    @overload
    def lookahead[V: Header](self, type: type[V]) -> V: ...
    def lookahead(self, type: object) -> Value:
        """Read a value of `type` from the packet without consuming it."""
        kind = kind_of(type)
        self._build.pb_type(type)
        stmts = self._state()
        with provenance():
            return kind.at(stmts.lookahead(kind.pb_type), None)


def _core_keyset(s: KeySet) -> _CoreKeySet:
    if isinstance(s, Masked | Range | DontCare):
        return s
    return operand(s)


class Control[H: Struct, M: Struct](Block):
    """A control: `@action` methods, `Table` attributes and `apply`; by
    default over `(inout H hdr, inout M meta)`."""

    _kind: ClassVar[str] = "control"
    hdr: H
    meta: M

    @classmethod
    def _make_core(cls, build: Build) -> CoreBlock:
        with provenance():
            return CoreControl(build.core, cls.__ir_name__, cls._core_params(build))

    def _run(self) -> None:
        cls = type(self)
        core = self._core
        assert isinstance(core, CoreControl)
        for name, act in cls.__actions__.items():
            params = act._params()  # pyright: ignore[reportPrivateUsage]
            kinds = {p: kind_of(t) for p, t in params}
            for _, t in params:
                self._build.pb_type(t)
            with provenance():
                body = core.action(name, **{p: k.pb_type for p, k in kinds.items()})
            values = [kinds[p].at(body.var(p), None) for p, _ in params]
            self._stmts = body
            with provenance():
                act.func(self, *values)
            self._stmts = None
        for name, table in cls.__tables__.items():
            self._tables[name] = table._bound(self._declare_table(name, table, core))  # pyright: ignore[reportPrivateUsage]
        self._stmts = core.body()
        with provenance():
            self.apply()
        self._stmts = None

    def _declare_table(self, name: str, table: Table[Any], core: CoreControl) -> CoreTable:
        what = f"table {name}"
        for a in table.actions:
            if type(self).__actions__.get(a.name) is not a:
                raise EdslError(f"{what}: {a.name} is not an action of {type(self).__ir_name__}")
        keys = [
            CoreKey(self._resolve(k.value, f"{what} key"), k.match_kind, k.name) for k in table.keys
        ]
        default = None if table.default is None else self._action_spec(table.default, what)
        entries: list[CoreEntry] = []
        for i, e in enumerate(table.entries):
            where = f"{what} entry {i}"
            spec = self._action_spec(e.action, where)
            # Pair each value with its key's type, so that a typed value of
            # the wrong width is refused here and not only where it fits; a
            # value with no key is left to the core's arity check.
            values = tuple(
                _core_key_value(v, keys[j].expr.type if j < len(keys) else None, where)
                for j, v in enumerate(e.keys)
            )
            entries.append(CoreEntry(values, spec, e.priority))
        with provenance():
            return core.table(
                name,
                keys=keys,
                actions=[a.name for a in table.actions],
                default=default,
                const_default=table.const_default,
                const_entries=entries,
                size=table.size,
            )

    def _action_spec(self, call: ActionCall, what: str) -> tuple[str, *tuple[Any, ...]]:
        act = call.action
        if type(self).__actions__.get(act.name) is not act and not (
            act._owner is self and type(self).__actions__.get(act.name) is not None  # pyright: ignore[reportPrivateUsage]
        ):
            raise EdslError(f"{what}: {act.name} is not an action of {type(self).__ir_name__}")
        args = act._arguments(call)  # pyright: ignore[reportPrivateUsage]
        with provenance():
            return (act.name, *[operand(a) for a in args])

    def _bound_table(self, table: Table[Any]) -> Table[Any]:
        if table.name not in self._tables:
            raise EdslError(
                f"table {table.name} is not yet declared; apply() runs after the tables"
            )
        return self._tables[table.name]

    def _record_action_call(self, call: ActionCall) -> None:
        stmts = self._record()
        if not isinstance(stmts, ControlBody):
            raise EdslError(f"an action is called from apply(), not from {call.action.name}")
        name, *args = self._action_spec(call, f"call of {call.action.name}")
        with provenance():
            stmts.call_action(name, *args)

    def apply_table(self, table: Table[Any], hit: Bool | None = None) -> None:
        """Apply a table; `hit`, a bool place, receives whether an entry matched."""
        stmts = self._record()
        if not isinstance(stmts, ControlBody):
            raise EdslError("a table is applied from apply(), not from an action")
        if table._core is None:  # pyright: ignore[reportPrivateUsage]
            raise EdslError(f"apply_table needs the table through self, self.{table.name}")
        with provenance():
            stmts.apply(
                table._core,  # pyright: ignore[reportPrivateUsage]
                None if hit is None else hit._expr,  # pyright: ignore[reportPrivateUsage]
            )

    def apply(self) -> None:
        """The control's body; override it. Empty by default."""


def _core_key_value(
    k: object, key_type: pb.Type | None, what: str
) -> int | Masked | Prefix | DontCare:
    """One entry value as the core takes it, an int. The IR stores decimal
    strings of the key's width, so the value's own width is gone by then:
    a typed value is checked against `key_type` here, the run-time half of
    the static guarantee `Table`'s typed overloads give."""
    if isinstance(k, Masked | Prefix | DontCare):
        return k
    if isinstance(k, Bits):
        with provenance():
            expr = k._expr  # pyright: ignore[reportPrivateUsage]
        if not expr.is_literal:
            raise EdslError(f"an entry value is a constant, got {k!r}")
        if key_type is not None and expr.type != key_type:
            raise EdslError(
                f"{what}: the value is {type_str(expr.type)}, the key is {type_str(key_type)}"
            )
        return int(expr.pb.literal.bits.value)
    if isinstance(k, bool) or not isinstance(k, int):
        raise EdslError(
            f"an entry value is an int, a literal, prefix(...), masked(...) or dont_care; got {k!r}"
        )
    return int(k)


class Deparser[H: Struct](Block):
    """A deparser: `apply` emits headers; by default over `(in H hdr)`."""

    _kind: ClassVar[str] = "deparser"
    hdr: H

    @classmethod
    def _make_core(cls, build: Build) -> CoreBlock:
        with provenance():
            return CoreDeparser(build.core, cls.__ir_name__, cls._core_params(build))

    def _run(self) -> None:
        core = self._core
        assert isinstance(core, CoreDeparser)
        self._stmts = core.body()
        with provenance():
            self.apply()
        self._stmts = None

    def emit(self, value: View | Stack[Any, Any]) -> None:
        """Emit a header, or every header of a struct or stack."""
        stmts = self._record()
        if not isinstance(stmts, DeparserBody):
            raise EdslError("emit belongs in a deparser's apply()")
        with provenance():
            stmts.emit(value._expr)  # pyright: ignore[reportPrivateUsage]

    def apply(self) -> None:
        """The deparser's body; override it."""


_ = L  # `L` is re-exported for annotations such as `Stack[h, L[2]]`

__all__ = [
    "Accept",
    "Action",
    "ActionCall",
    "Block",
    "Control",
    "Deparser",
    "DontCare",
    "Entry",
    "ExternResult",
    "Key",
    "KeySet",
    "KeyValue",
    "Masked",
    "Parser",
    "Prefix",
    "Range",
    "Reject",
    "State",
    "StateRef",
    "Table",
    "Target",
    "Transition",
    "action",
    "current_block",
    "dont_care",
    "entry",
    "exact",
    "lpm",
    "masked",
    "prefix",
    "range_",
    "state",
    "ternary",
]
