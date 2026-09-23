"""Blocks, statements, actions, tables and parser states.

A block builder registers with its program when it is created and is built
into a `pb.Block` when the program is. Its params and locals are reachable
as attributes (`c.hdr`, `c.meta`) and give typed `Expr` paths. Statement
lists are built by `Stmts` and its per-kind subclasses; control flow is
explicit (`with b.if_(cond): ...`), so that every construct is a builder
call and nothing reads Python source.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from p4blo.edsl.core.expr import BIT32, Expr, Operand, constant, literal
from p4blo.edsl.core.types import (
    EdslError,
    ExternInstance,
    ParamSpec,
    TypeLike,
    TypeTable,
    as_type,
    boolean,
    is_bits,
    make_params,
    type_str,
)
from p4blo.v0 import p4blo_pb2 as pb

if TYPE_CHECKING:
    from p4blo.edsl.core.program import Program


# ---------------------------------------------------------------------------
# Match values: select keysets and table entries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Masked:
    """`value &&& mask`: a select keyset, or a ternary entry value."""

    value: int
    mask: int


@dataclass(frozen=True)
class Range:
    """`lo..hi`, inclusive: a select keyset."""

    lo: int
    hi: int


@dataclass(frozen=True)
class Prefix:
    """`value/length`: an lpm entry value."""

    value: int
    length: int


class DontCare:
    """The `_` keyset; `dont_care` is its one value."""

    def __repr__(self) -> str:
        return "dont_care"


dont_care = DontCare()


def masked(value: int, mask: int) -> Masked:
    return Masked(value, mask)


def range_(lo: int, hi: int) -> Range:
    return Range(lo, hi)


def prefix(value: int, length: int) -> Prefix:
    return Prefix(value, length)


type KeySetSpec = Operand | Masked | Range | DontCare
"""One select keyset: a constant (int, bool, enum or error literal),
`masked(v, m)`, `range_(lo, hi)` or `dont_care`."""

type KeyValueSpec = int | Masked | Prefix | DontCare
"""One table entry value: an int for an exact key, `prefix(v, n)` for an
lpm key, `masked(v, m)` or an int or `dont_care` for a ternary key."""


def keyset(types: TypeTable, spec: KeySetSpec, key: pb.Type) -> pb.KeySet:
    """One select keyset as the IR holds it. Public because the typed
    surface normalises through it before comparing two keysets: a
    `pb.KeySet` compares by value, an `Expr` does not."""
    if isinstance(spec, DontCare):
        return pb.KeySet(dont_care=pb.DontCare())
    if isinstance(spec, Masked):
        _bits_key(key, "masked")
        value = constant(types, spec.value, key)
        mask = constant(types, spec.mask, key)
        return pb.KeySet(masked=pb.MaskedValue(value=value, mask=mask))
    if isinstance(spec, Range):
        _bits_key(key, "range_")
        lo = constant(types, spec.lo, key)
        hi = constant(types, spec.hi, key)
        return pb.KeySet(range=pb.RangeValue(lo=lo, hi=hi))
    return pb.KeySet(exact=constant(types, spec, key))


def _bits_key(key: pb.Type, what: str) -> None:
    if not is_bits(key):
        raise EdslError(f"{what} needs a bit<N> key, got {type_str(key)}")


def _key_value(types: TypeTable, spec: KeyValueSpec, key: pb.Key, key_type: pb.Type) -> pb.KeyValue:
    """An entry value for one key; `KeyValue` writes decimal strings of the
    key's width, so only bit<N> keys can have entries."""
    _bits_key(key_type, "a table entry")
    width = key_type.bits
    full = (1 << width) - 1

    def dec(value: int, what: str) -> str:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= full:
            raise EdslError(f"{what} {value!r} does not fit in {type_str(key_type)}")
        return str(value)

    match key.match_kind:
        case pb.MATCH_KIND_EXACT:
            if not isinstance(spec, int):
                raise EdslError(f"an exact key takes an int entry value, got {spec!r}")
            return pb.KeyValue(exact=dec(spec, "exact value"))
        case pb.MATCH_KIND_LPM:
            if not isinstance(spec, Prefix):
                raise EdslError(f"an lpm key takes prefix(value, length), got {spec!r}")
            if not 0 <= spec.length <= width:
                raise EdslError(f"prefix length {spec.length} exceeds {type_str(key_type)}")
            value = pb.LpmValue(value=dec(spec.value, "prefix value"), prefix_len=spec.length)
            return pb.KeyValue(lpm=value)
        case pb.MATCH_KIND_TERNARY:
            if isinstance(spec, DontCare):
                spec = Masked(0, 0)
            elif isinstance(spec, int):
                spec = Masked(spec, full)
            if not isinstance(spec, Masked):
                raise EdslError(f"a ternary key takes masked(value, mask), got {spec!r}")
            value = pb.TernaryValue(value=dec(spec.value, "value"), mask=dec(spec.mask, "mask"))
            return pb.KeyValue(ternary=value)
        case _:
            raise EdslError("key has no match kind")


# ---------------------------------------------------------------------------
# Table declarations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Key:
    """A table key: an expression and its match kind. `name` is what the
    host calls it; empty means the expression's dotted path."""

    expr: Expr
    match_kind: pb.MatchKind
    name: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.expr, Expr):
            hint = ""
            if isinstance(self.expr, pb.Type):
                # `hdr.eth.type` is the Expr's own attribute (expr.py, the
                # shadowing rule), the usual way a pb.Type gets here.
                hint = "; a field named like an Expr attribute is reached as .field(name)"
            raise EdslError(f"a key is an Expr, got {self.expr!r}{hint}")


def exact(expr: Expr, name: str = "") -> Key:
    return Key(expr, pb.MATCH_KIND_EXACT, name)


def lpm(expr: Expr, name: str = "") -> Key:
    return Key(expr, pb.MATCH_KIND_LPM, name)


def ternary(expr: Expr, name: str = "") -> Key:
    return Key(expr, pb.MATCH_KIND_TERNARY, name)


type ActionSpec = str | ActionBody | tuple[str | ActionBody, *tuple[Operand, ...]]
"""An action call: a name, or `(name, arg, ...)` with its action data."""


@dataclass(frozen=True)
class Entry:
    keys: tuple[KeyValueSpec, ...]
    action: ActionSpec
    priority: int = 0


def entry(
    keys: KeyValueSpec | tuple[KeyValueSpec, ...],
    action: ActionSpec,
    priority: int = 0,
) -> Entry:
    """A const entry: one value per key, in order, and the action to run."""
    return Entry(keys if isinstance(keys, tuple) else (keys,), action, priority)


class Table:
    """A declared table; `b.apply(t)` applies it."""

    def __init__(self, name: str, message: pb.Table) -> None:
        self.name = name
        self.message = message


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

type Target = str | StateBody | Accept | Reject


class Accept:
    """The parser's accept state; `ps.accept` is its value."""

    def __repr__(self) -> str:
        return "accept"


class Reject:
    """The parser's reject state; `ps.reject` is its value."""

    def __repr__(self) -> str:
        return "reject"


ACCEPT = Accept()
REJECT = Reject()


class Stmts:
    """A statement list under construction.

    Every kind of block may hold these statements; `ControlBody`,
    `StateBody` and `DeparserBody` add the ones specific to their kind.
    Attribute access resolves the enclosing block's params and locals.
    """

    def __init__(self, block: Block, stmts: list[pb.Stmt]) -> None:
        self.block = block
        # One statement list per open block, innermost last, and beside each
        # the `if` its last statement is, so that `else_` knows what it
        # continues at its own nesting level and nothing deeper.
        self._targets: list[list[pb.Stmt]] = [stmts]
        self._open_ifs: list[pb.Stmt | None] = [None]

    @property
    def types(self) -> TypeTable:
        return self.block.types

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def __getattr__(self, name: str) -> Expr:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.var(name)

    def var(self, name: str) -> Expr:
        """The param or local `name`, as an expression."""
        return self.block.var(name)

    def local(self, name: str, type: TypeLike) -> Expr:
        """Declare a block local here; it is hoisted to the block."""
        return self.block.local(name, type)

    def _emit(self, stmt: pb.Stmt) -> None:
        self._targets[-1].append(stmt)
        self._open_ifs[-1] = None

    @contextmanager
    def _nested(self, stmts: list[pb.Stmt]) -> Iterator[None]:
        """Statements emitted inside the `with` go to `stmts`."""
        self._targets.append(stmts)
        self._open_ifs.append(None)
        try:
            yield
        finally:
            self._targets.pop()
            self._open_ifs.pop()

    def assign(self, target: Expr, value: Operand) -> None:
        """`target = value`; an int value takes the target's type."""
        if not isinstance(target, Expr):
            raise EdslError(f"assign needs an lvalue target, got {target!r}")
        rhs = literal(self.types, value, target.type)
        self._emit(pb.Stmt(assign=pb.Assign(target=target.lval, value=rhs.pb)))

    def assign_slice(self, target: Expr, hi: int, lo: int, value: int) -> None:
        """`target[hi:lo] = value`, the named elaboration of P4's slice lvalue.

        The IR has no slice lvalue: a slice may be read, never written. P4
        allows the write, and it means the read-modify-write

            target = (target & ~mask) | (value << lo)

        where `mask` covers bits `hi` down to `lo`. That is what this emits,
        with `mask`, `value` and `lo` each a `bit<W>` literal at the target's
        width W, so that nothing is inferred and no cast appears. `value` is
        an int that fits the slice.
        """
        if not isinstance(target, Expr) or target.lvalue is None:
            raise EdslError(f"assign_slice needs a bit<N> lvalue target, got {target!r}")
        if not is_bits(target.type):
            raise EdslError(f"assign_slice needs a bit<N> target, got {type_str(target.type)}")
        width = target.type.bits
        if not (isinstance(hi, int) and isinstance(lo, int) and 0 <= lo <= hi < width):
            raise EdslError(f"slice [{hi}:{lo}] is out of range for {type_str(target.type)}")
        size = hi - lo + 1
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < (1 << size):
            raise EdslError(f"{value!r} does not fit in the {size}-bit slice [{hi}:{lo}]")
        mask = literal(self.types, ((1 << size) - 1) << lo, target.type)
        shifted = literal(self.types, value, target.type) << lo
        self.assign(target, (target & ~mask) | shifted)

    @contextmanager
    def if_(self, condition: Operand) -> Iterator[Self]:
        """`if (condition) { ... }`; statements inside the `with` form the branch."""
        cond = literal(self.types, condition, boolean)
        stmt = pb.Stmt(conditional=pb.If(condition=cond.pb))
        then: list[pb.Stmt] = []
        with self._nested(then):
            yield self
        stmt.conditional.then.extend(then)
        self._emit(stmt)
        self._open_ifs[-1] = stmt

    def _continue_if(self, what: str) -> pb.Stmt:
        """The `if` at this nesting level that `what` continues; it takes it,
        so that only one `else_` can."""
        stmt = self._open_ifs[-1]
        if stmt is None:
            raise EdslError(f"{what} must follow an if_ block directly")
        self._open_ifs[-1] = None
        return stmt

    @contextmanager
    def else_(self) -> Iterator[Self]:
        """The `else` of the `if_` block just closed at this nesting level."""
        stmt = self._continue_if("else_")
        otherwise: list[pb.Stmt] = []
        with self._nested(otherwise):
            yield self
        stmt.conditional.otherwise.extend(otherwise)

    @contextmanager
    def elif_(self, condition: Operand) -> Iterator[Self]:
        """`else if (condition) { ... }`: an `else_` holding one `if_`.

        The ladder nests as P4's does, each arm the sole statement of the
        previous arm's `else`, and the next `elif_` or `else_` at this
        level continues the innermost `if`.
        """
        stmt = self._continue_if("elif_")
        otherwise: list[pb.Stmt] = []
        with self._nested(otherwise):
            with self.if_(condition):
                yield self
        stmt.conditional.otherwise.extend(otherwise)
        # `extend` copies, so the arm the ladder continues is the copy now
        # inside `stmt`, not the message `if_` built.
        self._open_ifs[-1] = stmt.conditional.otherwise[-1]

    def _args(self, params: Sequence[pb.Param], args: Sequence[Operand], what: str) -> list[pb.Arg]:
        """Arguments against parameters: in and directionless take an
        expression, out and inout an lvalue of the parameter's type."""
        if len(args) != len(params):
            raise EdslError(f"{what} takes {len(params)} arguments, got {len(args)}")
        out: list[pb.Arg] = []
        for param, arg in zip(params, args, strict=True):
            where = f"{what}, argument {param.name!r}"
            if param.direction in (pb.DIRECTION_OUT, pb.DIRECTION_INOUT):
                if not isinstance(arg, Expr) or arg.lvalue is None:
                    raise EdslError(f"{where}: an out/inout argument must be an lvalue")
                if arg.type != param.type:
                    raise EdslError(
                        f"{where}: expected {type_str(param.type)}, got {type_str(arg.type)}"
                    )
                out.append(pb.Arg(lvalue=arg.lval))
            else:
                try:
                    value = literal(self.types, arg, param.type)
                except EdslError as e:
                    raise EdslError(f"{where}: {e}") from None
                out.append(pb.Arg(expr=value.pb))
        return out

    def call(
        self,
        instance: ExternInstance,
        method: str,
        *args: Operand,
        result: Expr | None = None,
    ) -> None:
        """Call `method` on an extern instance; `result` receives a return value."""
        if not isinstance(instance, ExternInstance):
            raise EdslError(f"call needs an extern instance, got {instance!r}")
        m = instance.extern_type.method(method)
        what = f"{instance.name}.{method}"
        stmt = pb.Stmt(
            call_extern=pb.CallExtern(
                instance=instance.name, method=method, args=self._args(m.params, args, what)
            )
        )
        if result is not None:
            if not m.HasField("returns"):
                raise EdslError(f"{what} returns nothing; no result to assign")
            if result.type != m.returns:
                raise EdslError(
                    f"{what} returns {type_str(m.returns)}, result is {type_str(result.type)}"
                )
            stmt.call_extern.result.CopyFrom(result.lval)
        self._emit(stmt)

    def call_block(self, block: Block | str, *args: Operand) -> None:
        """Call a sub-parser or sub-control with arguments for its params."""
        callee = block if isinstance(block, Block) else self.block.program.block(block)
        stmt = pb.Stmt(
            call_block=pb.CallBlock(
                block=callee.name, args=self._args(callee.params, args, f"block {callee.name}")
            )
        )
        self._emit(stmt)

    def _header(self, header: Expr, what: str) -> pb.LValue:
        if not isinstance(header, Expr) or header.type.WhichOneof("kind") != "header":
            raise EdslError(f"{what} needs a header lvalue, got {header!r}")
        return header.lval

    def _stack(self, stack: Expr, count: int, what: str) -> pb.LValue:
        if not isinstance(stack, Expr) or stack.type.WhichOneof("kind") != "stack":
            raise EdslError(f"{what} needs a stack lvalue, got {stack!r}")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise EdslError(f"{what} count is an integer >= 1, got {count!r}")
        return stack.lval

    def set_valid(self, header: Expr) -> None:
        self._emit(pb.Stmt(set_valid=pb.SetValid(header=self._header(header, "set_valid"))))

    def set_invalid(self, header: Expr) -> None:
        lval = self._header(header, "set_invalid")
        self._emit(pb.Stmt(set_invalid=pb.SetInvalid(header=lval)))

    def push(self, stack: Expr, count: int) -> None:
        """`stack.push_front(count)`."""
        lval = self._stack(stack, count, "push")
        self._emit(pb.Stmt(push=pb.Push(stack=lval, count=count)))

    def pop(self, stack: Expr, count: int) -> None:
        """`stack.pop_front(count)`."""
        lval = self._stack(stack, count, "pop")
        self._emit(pb.Stmt(pop=pb.Pop(stack=lval, count=count)))


class ActionBody(Stmts):
    """An action's body; its params are attributes (`a.port`)."""

    def __init__(self, block: Control, name: str, params: Sequence[pb.Param]) -> None:
        self.name = name
        self.params = list(params)
        self._param_types = {p.name: p.type for p in self.params}
        super().__init__(block, [])

    @property
    def stmts(self) -> list[pb.Stmt]:
        return self._targets[0]

    def var(self, name: str) -> Expr:
        if name in self._param_types:
            t = self._param_types[name]
            return Expr(self.types, t, pb.Expr(var=name), pb.LValue(var=name))
        return self.block.var(name)

    def build(self) -> pb.Action:
        return pb.Action(name=self.name, params=self.params, body=self.stmts)


class ControlBody(Stmts):
    """A control's body: adds table application and direct action calls."""

    def apply(self, table: Table | str, hit: Expr | None = None) -> None:
        """Apply a table; `hit`, a bool lvalue, receives whether an entry matched."""
        control = self.block
        if not isinstance(control, Control):
            raise EdslError("apply belongs in a control")
        t = control.table_named(table.name if isinstance(table, Table) else table)
        stmt = pb.Stmt(apply=pb.Apply(table=t.name))
        if hit is not None:
            if hit.type != boolean:
                raise EdslError(f"hit must be a bool lvalue, got {type_str(hit.type)}")
            stmt.apply.hit.CopyFrom(hit.lval)
        self._emit(stmt)

    def call_action(self, action: str | ActionBody, *args: Operand) -> None:
        """Call an action of this control directly, with its action data."""
        control = self.block
        if not isinstance(control, Control):
            raise EdslError("call_action belongs in a control")
        a = control.action_named(action.name if isinstance(action, ActionBody) else action)
        stmt = pb.Stmt(
            call_action=pb.CallAction(
                action=a.name, args=self._args(a.params, args, f"action {a.name}")
            )
        )
        self._emit(stmt)


class DeparserBody(Stmts):
    """A deparser's body: adds emit."""

    def emit(self, value: Expr) -> None:
        """Emit a header, or every header of a struct or stack."""
        if not isinstance(value, Expr) or value.type.WhichOneof("kind") not in (
            "header",
            "struct",
            "stack",
        ):
            raise EdslError(f"emit needs a header, struct or stack, got {value!r}")
        self._emit(pb.Stmt(emit=pb.Emit(value=value.pb)))


class StateBody(Stmts):
    """A parser state: its body and its one transition."""

    def __init__(self, block: Parser, name: str) -> None:
        if not name:
            raise EdslError("a state needs a name")
        self.name = name
        self._transition: pb.Transition | None = None
        super().__init__(block, [])

    @property
    def stmts(self) -> list[pb.Stmt]:
        return self._targets[0]

    def extract(self, target: Expr) -> None:
        """Extract a header from the packet into `target`, a header lvalue
        (`hdr.ipv4`, or `hdr.stack.next`)."""
        self._emit(pb.Stmt(extract=pb.Extract(target=self._header(target, "extract"))))

    def advance(self, bits: Operand) -> None:
        """Skip `bits` bits of the packet. The amount is a bit<32>, as
        core.p4 declares `advance`; an int becomes one, an Expr of another
        width is refused (cast it, as P4 would make you)."""
        try:
            amount = literal(self.types, bits, BIT32)
        except EdslError as e:
            raise EdslError(f"advance needs a bit<32> amount: {e}") from None
        self._emit(pb.Stmt(advance=pb.Advance(bits=amount.pb)))

    def verify(self, condition: Operand, error: str | Expr) -> None:
        """Raise `error` unless `condition` holds."""
        cond = literal(self.types, condition, boolean)
        name = _error_name(self.types, error)
        self._emit(pb.Stmt(verify=pb.Verify(condition=cond.pb, error=name)))

    def lookahead(self, type: TypeLike) -> Expr:
        """Read a value of `type` from the packet without consuming it."""
        t = as_type(type)
        return Expr(self.types, t, pb.Expr(lookahead=pb.Lookahead(type=t)))

    def _set_transition(self, transition: pb.Transition) -> None:
        if self._transition is not None:
            raise EdslError(f"state {self.name!r} already has a transition")
        self._transition = transition

    def transition(self, target: Target) -> None:
        """Transition unconditionally to a state, `ps.accept` or `ps.reject`."""
        self._set_transition(pb.Transition(direct=_target(target)))

    def accept(self) -> None:
        self.transition(ACCEPT)

    def reject(self) -> None:
        self.transition(REJECT)

    def select(
        self,
        keys: Expr | Sequence[Expr],
        cases: Mapping[KeySetSpec | tuple[KeySetSpec, ...], Target]
        | Sequence[tuple[KeySetSpec | tuple[KeySetSpec, ...], Target]],
        *,
        default: Target | None = None,
    ) -> None:
        """`transition select(keys) { ... }`.

        `cases` maps a keyset, or a tuple of them when `keys` is a sequence,
        to a target, in the order they are tried; `default` adds a final
        case that matches anything.
        """
        key_list = [keys] if isinstance(keys, Expr) else list(keys)
        if not key_list:
            raise EdslError("select needs at least one key")
        select = pb.Select(keys=[k.pb for k in key_list])
        items = cases.items() if isinstance(cases, Mapping) else cases
        for spec, target in items:
            sets = spec if isinstance(spec, tuple) else (spec,)
            if len(sets) != len(key_list):
                raise EdslError(f"select has {len(key_list)} keys; case {spec!r} has {len(sets)}")
            case = select.cases.add(target=_target(target))
            for s, k in zip(sets, key_list, strict=True):
                case.sets.append(keyset(self.types, s, k.type))
        if default is not None:
            case = select.cases.add(target=_target(default))
            for _ in key_list:
                case.sets.add(dont_care=pb.DontCare())
        self._set_transition(pb.Transition(select=select))

    def build(self) -> pb.State:
        if self._transition is None:
            raise EdslError(f"state {self.name!r} has no transition")
        return pb.State(name=self.name, body=self.stmts, transition=self._transition)


def _target(target: Target) -> pb.Target:
    if isinstance(target, Accept):
        return pb.Target(accept=pb.Accept())
    if isinstance(target, Reject):
        return pb.Target(reject=pb.Reject())
    if isinstance(target, StateBody):
        return pb.Target(state=target.name)
    if isinstance(target, str) and target:
        return pb.Target(state=target)
    raise EdslError(f"a transition target is a state name, ps.accept or ps.reject; got {target!r}")


def _error_name(types: TypeTable, error: str | Expr) -> str:
    if isinstance(error, Expr):
        if not error.is_literal or error.pb.literal.WhichOneof("value") != "error":
            raise EdslError(f"expected an error literal, got {error!r}")
        return error.pb.literal.error
    if error not in types.errors:
        raise EdslError(f"no error {error!r}; errors are {', '.join(types.errors)}")
    return error


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


class Block:
    """A block under construction: the base of `Parser`, `Control` and `Deparser`."""

    kind: pb.BlockKind = pb.BLOCK_KIND_UNSPECIFIED

    def __init__(self, program: Program, name: str, params: Sequence[ParamSpec]) -> None:
        if not name:
            raise EdslError("a block needs a name")
        self.program = program
        self.name = name
        self.params: list[pb.Param] = make_params(params, f"block {name}")
        self.locals: list[pb.Var] = []
        self._vars: dict[str, pb.Type] = {p.name: p.type for p in self.params}
        self._names: dict[str, str] = {p.name: "param" for p in self.params}
        self._body: list[pb.Stmt] = []

    @property
    def types(self) -> TypeTable:
        return self.program.types

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def declare(self, name: str, what: str) -> None:
        """Take `name` in this block's namespace, or refuse it."""
        if not name:
            raise EdslError(f"block {self.name}: a {what} needs a name")
        if name in self._names:
            raise EdslError(
                f"block {self.name}: {what} {name!r} reuses the name of a {self._names[name]}"
            )
        if self.program.declares(name):
            raise EdslError(f"block {self.name}: {what} {name!r} reuses a program-level name")
        self._names[name] = what

    def __getattr__(self, name: str) -> Expr:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.var(name)

    def var(self, name: str) -> Expr:
        """The param or local `name`, as an expression."""
        if name not in self._vars:
            raise EdslError(
                f"block {self.name} has no param or local {name!r}; "
                f"it has {', '.join(self._vars) or 'none'}"
            )
        return Expr(self.types, self._vars[name], pb.Expr(var=name), pb.LValue(var=name))

    def local(self, name: str, type: TypeLike) -> Expr:
        """Declare a block local and return it."""
        self.declare(name, "local")
        t = as_type(type)
        self.locals.append(pb.Var(name=name, type=t))
        self._vars[name] = t
        return self.var(name)

    def build(self) -> pb.Block:
        return pb.Block(name=self.name, kind=self.kind, params=self.params, locals=self.locals)


class Parser(Block):
    """A parser block: states and a start state, no body."""

    kind = pb.BLOCK_KIND_PARSER

    def __init__(self, program: Program, name: str, params: Sequence[ParamSpec]) -> None:
        super().__init__(program, name, params)
        self.states: list[StateBody] = []
        self.start: str | None = None

    @property
    def accept(self) -> Accept:
        return ACCEPT

    @property
    def reject(self) -> Reject:
        return REJECT

    def state(self, name: str, *, start: bool = False) -> StateBody:
        """Declare a state; fill it in a `with`. The start state is the one
        flagged `start=True`, or failing that the one named `start`."""
        self.declare(name, "state")
        if start:
            if self.start is not None:
                raise EdslError(f"parser {self.name}: {self.start!r} is already the start state")
            self.start = name
        s = StateBody(self, name)
        self.states.append(s)
        return s

    def build(self) -> pb.Block:
        block = super().build()
        names = {s.name for s in self.states}
        start = self.start if self.start is not None else "start" if "start" in names else None
        if start is None:
            raise EdslError(f"parser {self.name} has no start state")
        for s in self.states:
            state = s.build()
            for target in _targets(state.transition):
                if target.WhichOneof("kind") == "state" and target.state not in names:
                    raise EdslError(
                        f"parser {self.name}: state {s.name!r} transitions to "
                        f"unknown state {target.state!r}"
                    )
            block.states.append(state)
        block.start_state = start
        return block


def _targets(transition: pb.Transition) -> Iterator[pb.Target]:
    if transition.WhichOneof("kind") == "direct":
        yield transition.direct
    else:
        for case in transition.select.cases:
            yield case.target


class Control(Block):
    """A control block: actions, tables and a body."""

    kind = pb.BLOCK_KIND_CONTROL

    def __init__(self, program: Program, name: str, params: Sequence[ParamSpec]) -> None:
        super().__init__(program, name, params)
        self.actions: list[ActionBody] = []
        self.tables: list[Table] = []

    def action(self, name: str, /, **params: TypeLike) -> ActionBody:
        """Declare an action; keyword params are its action data, in order.
        Fill the body in a `with`, or leave it empty."""
        self.declare(name, "action")
        specs: list[ParamSpec] = [(p, "none", t) for p, t in params.items()]
        for p in params:
            if p in self._names:
                raise EdslError(
                    f"action {name}: param {p!r} reuses the name of a "
                    f"{self._names[p]} of block {self.name}"
                )
            if self.program.declares(p):
                raise EdslError(f"action {name}: param {p!r} reuses a program-level name")
        a = ActionBody(self, name, make_params(specs, f"action {name}"))
        self.actions.append(a)
        return a

    def action_named(self, name: str) -> ActionBody:
        for a in self.actions:
            if a.name == name:
                return a
        raise EdslError(
            f"control {self.name} has no action {name!r}; "
            f"actions are {', '.join(a.name for a in self.actions) or 'none'}"
        )

    @staticmethod
    def _action_name(action: str | ActionBody) -> str:
        return action.name if isinstance(action, ActionBody) else action

    def table_named(self, name: str) -> Table:
        for t in self.tables:
            if t.name == name:
                return t
        raise EdslError(f"control {self.name} has no table {name!r}")

    def _action_call(self, spec: ActionSpec, allowed: Sequence[str], what: str) -> pb.ActionCall:
        head, args = (spec[0], spec[1:]) if isinstance(spec, tuple) else (spec, ())
        a = self.action_named(self._action_name(head))
        if a.name not in allowed:
            raise EdslError(f"{what}: {a.name!r} is not among the table's actions")
        if len(args) != len(a.params):
            raise EdslError(f"{what}: action {a.name} takes {len(a.params)} args, got {len(args)}")
        call = pb.ActionCall(action=a.name)
        for param, arg in zip(a.params, args, strict=True):
            call.args.append(constant(self.types, arg, param.type))
        return call

    def table(
        self,
        name: str,
        *,
        keys: Sequence[Key] = (),
        actions: Sequence[str | ActionBody],
        default: ActionSpec | None = None,
        const_default: bool = False,
        const_entries: Sequence[Entry] = (),
        size: int = 0,
    ) -> Table:
        """Declare a table over actions already declared in this control.

        `default` names the action run on a miss, with its args when it has
        any; absent means NoAction. `const_entries` are installed before any
        host entry; a ternary table gives each a priority.
        """
        self.declare(name, "table")
        names = [self.action_named(self._action_name(a)).name for a in actions]
        if len(set(names)) != len(names):
            raise EdslError(f"table {name}: an action is listed twice")
        message = pb.Table(name=name, actions=names, const_default_action=const_default, size=size)
        for k in keys:
            if not isinstance(k, Key):
                raise EdslError(f"table {name}: keys are lpm(e), exact(e) or ternary(e); got {k!r}")
            message.keys.add(expr=k.expr.pb, match_kind=k.match_kind, name=k.name)
        if default is not None:
            call = self._action_call(default, names, f"table {name} default")
            message.default_action.CopyFrom(call)
        elif const_default:
            raise EdslError(f"table {name}: const_default needs a default action")
        for i, e in enumerate(const_entries):
            what = f"table {name} entry {i}"
            if not isinstance(e, Entry):
                raise EdslError(f"{what}: entries are entry(keys, action, priority)")
            if len(e.keys) != len(keys):
                raise EdslError(f"{what}: {len(keys)} keys expected, got {len(e.keys)}")
            row = message.const_entries.add(priority=e.priority)
            for spec, k, pk in zip(e.keys, keys, message.keys, strict=True):
                row.keys.append(_key_value(self.types, spec, pk, k.expr.type))
            row.action.CopyFrom(self._action_call(e.action, names, what))
        t = Table(name, message)
        self.tables.append(t)
        return t

    def body(self) -> ControlBody:
        """The `apply { ... }` body; statements append in order."""
        return ControlBody(self, self._body)

    apply = body

    def build(self) -> pb.Block:
        block = super().build()
        block.actions.extend(a.build() for a in self.actions)
        block.tables.extend(t.message for t in self.tables)
        block.body.extend(self._body)
        return block


class Deparser(Block):
    """A deparser block: a body of emits over the packet."""

    kind = pb.BLOCK_KIND_DEPARSER

    def body(self) -> DeparserBody:
        return DeparserBody(self, self._body)

    apply = body

    def build(self) -> pb.Block:
        block = super().build()
        block.body.extend(self._body)
        return block


__all__ = [
    "ACCEPT",
    "REJECT",
    "ActionBody",
    "Block",
    "Control",
    "ControlBody",
    "Deparser",
    "DeparserBody",
    "Entry",
    "Key",
    "Masked",
    "Parser",
    "Prefix",
    "Range",
    "StateBody",
    "Stmts",
    "Table",
    "dont_care",
    "entry",
    "exact",
    "keyset",
    "lpm",
    "masked",
    "prefix",
    "range_",
    "ternary",
]
