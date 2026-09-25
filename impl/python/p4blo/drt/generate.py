"""Random cases from a seed, shaped by the program.

Everything comes from one `random.Random(seed)`, so a seed names a case
sequence exactly and a divergence is reproducible by seed and index.

## Packets

A packet of random bytes almost never gets past the first `select`, so
packets are made by walking the parser. The walk is a small symbolic
interpreter over the IR: it runs the states from `start` on a packet that
does not exist yet, and every `extract`, `lookahead` and `advance` appends
random bits to it. It remembers which packet bits each extracted field
came from (a `Slot`) and which locals hold a known constant, so that when
a `select` comes, it can pick a case at random and write bits into the
slots of the keys that make the chosen case's key sets match; a `verify`
of `field == constant` is satisfied the same way most of the time, so
that the walk reaches deep states, and left alone the rest of the time,
so that the error path runs too. A sub-parser call aliases the callee's
parameters to the caller's storage and walks the callee's states in
place. Whatever the walk cannot follow, an expression it does not track
or a condition it cannot decide, it leaves to chance: the bytes are still
a plausible packet, and the interpreters, not the walk, decide what
happens to them.

After the walk the packet is finished three ways: as it is, with a random
payload appended, or truncated, which is how `PacketTooShort` is reached.
A small fraction of packets are plain random bytes, for the paths nobody
planned.

Fields that some table keys on are drawn half the time from a small pool
of values that the table's entries draw from too, so that lookups hit.

## Entries

For every table, a random number of entries with key values of the key's
kind and width, canonical, with a priority on ternary tables and action
data of the declared widths. Each is installed into a scratch
`InstalledEntries`, and an entry the install checks reject (a duplicate,
a tie) is dropped, so what comes out installs cleanly. A non-const
default action is sometimes replaced.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field

from p4blo.arch.bindings import BoundIndex
from p4blo.drt.case import Case
from p4blo.interp.tables import InstalledEntries, InstallError
from p4blo.interp.widths import type_of, width_of
from p4blo.ir import BlockScope
from p4blo.v0 import p4blo_pb2 as pb

__all__ = ["Generator", "Tuning", "generate"]


@dataclass(frozen=True)
class Tuning:
    """The distributions, as probabilities and bounds."""

    max_entries: int = 6
    # Probability that a non-const default action is replaced.
    host_default: float = 0.3
    # Probability that a key field, or an entry value, comes from the pool.
    from_pool: float = 0.5
    pool_size: int = 3
    # Probability that a `verify` is made to pass.
    satisfy_verify: float = 0.85
    # After the walk: the packet is truncated, or gets a payload.
    truncate: float = 0.15
    payload: float = 0.5
    max_payload: int = 32
    # Probability that the packet is random bytes instead of a walk.
    random_bytes: float = 0.05
    max_random_bytes: int = 64
    # States entered before a walk gives up.
    max_steps: int = 64


def generate(index: BoundIndex, seed: int, count: int, ports: int = 4) -> list[Case]:
    """`count` cases for a program, deterministic in `seed`."""
    return Generator(index, seed, ports).cases(count)


# A storage location: a variable name, then field names and stack indices.
type Path = tuple[str | int, ...]


@dataclass(frozen=True, slots=True)
class Slot:
    """`width` packet bits starting at bit `offset`."""

    offset: int
    width: int


# What the walk knows about a location: which packet bits it holds, or a
# constant.
type Source = Slot | int


class Generator:
    def __init__(
        self, index: BoundIndex, seed: int, ports: int = 4, tuning: Tuning | None = None
    ) -> None:
        self.index = index
        self.rng = random.Random(seed)
        self.ports = ports
        self.tuning = tuning or Tuning()
        self.pools = self._build_pools()

    def cases(self, count: int) -> list[Case]:
        return [self.case() for _ in range(count)]

    def case(self) -> Case:
        return Case(self.entries(), self.ingress_port(), self.packet())

    def ingress_port(self) -> int:
        return self.rng.randrange(self.ports)

    # -----------------------------------------------------------------------
    # Packets
    # -----------------------------------------------------------------------

    def packet(self) -> bytes:
        rng, tuning = self.rng, self.tuning
        if rng.random() < tuning.random_bytes:
            return rng.randbytes(rng.randint(1, tuning.max_random_bytes))
        walk = Walk(self)
        walk.run(self.index.exported("parser"))
        data = walk.bits.to_bytes()
        roll = rng.random()
        if roll < tuning.truncate and len(data) > 1:
            return data[: rng.randint(1, len(data) - 1)]
        if roll < tuning.truncate + tuning.payload:
            data += rng.randbytes(rng.randint(1, tuning.max_payload))
        return data or rng.randbytes(1)

    # -----------------------------------------------------------------------
    # Entries
    # -----------------------------------------------------------------------

    def entries(self) -> pb.Entries:
        """Random host entries, every one of which installs."""
        installed = InstalledEntries.build(self.index)
        host = pb.Entries()
        for block in self.index.program.blocks:
            for table in block.tables:
                ref = (block.name, table.name)
                widths = installed.key_widths(ref)
                keys = [self._key_path(block, key) for key in table.keys]
                te = host.tables.add(block=block.name, table=table.name)
                for _ in range(self.rng.randint(0, self.tuning.max_entries)):
                    entry = self.entry(block, table, widths, keys)
                    try:
                        installed.install(ref, entry)
                    except InstallError:
                        continue
                    te.entries.append(entry)
                if not table.const_default_action and self.rng.random() < self.tuning.host_default:
                    call = self.action_call(block, table)
                    try:
                        installed.set_default(ref, call)
                    except InstallError:
                        continue
                    te.default_action.CopyFrom(call)
                if not te.entries and not te.HasField("default_action"):
                    host.tables.pop()
        return host

    def entry(
        self, block: pb.Block, table: pb.Table, widths: list[int], keys: list[Path | None]
    ) -> pb.Entry:
        entry = pb.Entry(action=self.action_call(block, table))
        for key, width, path in zip(table.keys, widths, keys, strict=True):
            entry.keys.append(self.key_value(key.match_kind, width, path))
        if any(k.match_kind == pb.MATCH_KIND_TERNARY for k in table.keys):
            entry.priority = self.rng.randint(0, 3)
        return entry

    def key_value(self, kind: int, width: int, path: Path | None) -> pb.KeyValue:
        rng = self.rng
        full = (1 << width) - 1
        value = self.field_value(width, path)
        match kind:
            case pb.MATCH_KIND_EXACT:
                return pb.KeyValue(exact=str(value))
            case pb.MATCH_KIND_LPM:
                prefix = rng.choice([width, width, rng.randint(0, width)])
                value &= full ^ ((1 << (width - prefix)) - 1)
                return pb.KeyValue(lpm=pb.LpmValue(value=str(value), prefix_len=prefix))
            case pb.MATCH_KIND_TERNARY:
                mask = rng.choice([full, full, 0, rng.getrandbits(width)])
                return pb.KeyValue(ternary=pb.TernaryValue(value=str(value & mask), mask=str(mask)))
            case _:
                raise ValueError(f"key has match kind {kind}")

    def action_call(self, block: pb.Block, table: pb.Table) -> pb.ActionCall:
        name = self.rng.choice(list(table.actions))
        action = self.index.scopes[block.name].actions[name]
        return pb.ActionCall(action=name, args=[self.literal(p.type) for p in action.params])

    def literal(self, type: pb.Type) -> pb.Literal:
        rng = self.rng
        match type.WhichOneof("kind"):
            case "bits":
                value = str(rng.getrandbits(type.bits))
                return pb.Literal(bits=pb.BitsLiteral(width=type.bits, value=value))
            case "boolean":
                return pb.Literal(boolean=rng.random() < 0.5)
            case "enum_type":
                member = rng.choice(list(self.index.enum_types[type.enum_type].members))
                return pb.Literal(
                    enum_member=pb.EnumLiteral(enum_type=type.enum_type, member=member)
                )
            case "error":
                return pb.Literal(error=rng.choice(list(self.index.program.errors)))
            case kind:
                raise ValueError(f"no random literal of kind {kind!r}")

    # -----------------------------------------------------------------------
    # Value pools: the fields tables key on
    # -----------------------------------------------------------------------

    def field_value(self, width: int, path: Path | None) -> int:
        """A random value of `width` bits, from the pool of `path` half the
        time when it has one."""
        pool = self.pools.get(path) if path is not None else None
        if pool and self.rng.random() < self.tuning.from_pool:
            return self.rng.choice(pool)
        return self.rng.getrandbits(width)

    def _key_path(self, block: pb.Block, key: pb.Key) -> Path | None:
        """A table key's field as a path into H, or None when it is not one."""
        path = static_path(key.expr)
        if path is None or not block.params or path[0] != block.params[0].name:
            return None
        return ("H", *path[1:])

    def _build_pools(self) -> dict[Path, list[int]]:
        """Per keyed field: a few random values plus the const entries'."""
        installed = InstalledEntries(self.index)
        pools: dict[Path, list[int]] = {}
        for block in self.index.program.blocks:
            for table in block.tables:
                widths = installed.key_widths((block.name, table.name))
                for i, (key, width) in enumerate(zip(table.keys, widths, strict=True)):
                    path = self._key_path(block, key)
                    if path is None:
                        continue
                    pool = pools.setdefault(path, [])
                    pool.extend(self.rng.getrandbits(width) for _ in range(self.tuning.pool_size))
                    pool.extend(_key_value_int(e.keys[i]) for e in table.const_entries)
        return pools


def _key_value_int(kv: pb.KeyValue) -> int:
    match kv.WhichOneof("kind"):
        case "exact":
            return int(kv.exact)
        case "lpm":
            return int(kv.lpm.value)
        case _:
            return int(kv.ternary.value)


def static_path(expr: pb.Expr) -> Path | None:
    """A path of names and literal indices, or None for any other expression."""
    match expr.WhichOneof("kind"):
        case "var":
            return (expr.var,)
        case "member":
            base = static_path(expr.member.base)
            return None if base is None else (*base, expr.member.field)
        case "index":
            base = static_path(expr.index.base)
            i = expr.index.index
            if base is None or i.WhichOneof("kind") != "literal" or not i.literal.HasField("bits"):
                return None
            return (*base, int(i.literal.bits.value))
        case _:
            return None


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------


class BitBuffer:
    """The packet under construction, one entry per bit, most significant
    first. Bits past the end are random when they are first needed."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.bits: list[int] = []

    def ensure(self, length: int) -> None:
        while len(self.bits) < length:
            self.bits.append(self.rng.getrandbits(1))

    def read(self, slot: Slot) -> int:
        value = 0
        for bit in self.bits[slot.offset : slot.offset + slot.width]:
            value = (value << 1) | bit
        return value

    def write(self, slot: Slot, value: int) -> None:
        for i in range(slot.width):
            self.bits[slot.offset + i] = (value >> (slot.width - 1 - i)) & 1

    def to_bytes(self) -> bytes:
        padded = self.bits + [0] * (-len(self.bits) % 8)
        return bytes(int("".join(map(str, padded[i : i + 8])), 2) for i in range(0, len(padded), 8))


class Stop(Exception):
    """The walk cannot continue: a reject, a decided failure, or a bound."""


@dataclass
class Frame:
    """The block being walked and how its variables map to storage."""

    scope: BlockScope
    # Parameter names of a called block, aliased to the caller's paths.
    aliases: dict[str, Path] = field(default_factory=dict)

    def root(self, name: str) -> Path:
        return self.aliases.get(name, (name,))


class Walk:
    def __init__(self, gen: Generator) -> None:
        self.gen = gen
        self.index = gen.index
        self.rng = gen.rng
        self.bits = BitBuffer(gen.rng)
        self.cursor = 0
        self.known: dict[Path, Source] = {}
        self.next_index: dict[Path, int] = {}
        self.steps = 0
        self.frames: list[Frame] = []
        self.depth = 0

    @property
    def frame(self) -> Frame:
        return self.frames[-1]

    def run(self, block: pb.Block) -> None:
        """Walk `block` from its start state; the packet is left in `bits`."""
        headers = block.params[0].name if block.params else "hdr"
        self.frames.append(Frame(self.index.scopes[block.name], {headers: ("H",)}))
        try:
            self.states(block)
        except Stop:
            pass

    def states(self, block: pb.Block) -> None:
        state = self.frame.scope.states[block.start_state]
        while True:
            self.steps += 1
            if self.steps > self.gen.tuning.max_steps:
                raise Stop
            self.execute(state.body)
            target = self.transition(state.transition)
            match target.WhichOneof("kind"):
                case "state":
                    state = self.frame.scope.states[target.state]
                case _:
                    return

    # -- statements ----------------------------------------------------------

    def execute(self, stmts: Iterable[pb.Stmt]) -> None:
        for stmt in stmts:
            match stmt.WhichOneof("kind"):
                case "extract":
                    self.extract(stmt.extract.target)
                case "advance":
                    n = self.value(stmt.advance.bits)
                    if isinstance(n, int):
                        self.consume(n)
                case "verify":
                    self.verify(stmt.verify.condition)
                case "assign":
                    self.assign(stmt.assign.target, stmt.assign.value)
                case "conditional":
                    truth = self.truth(stmt.conditional.condition)
                    if truth is None:
                        truth = self.rng.random() < 0.5
                    self.execute(stmt.conditional.then if truth else stmt.conditional.otherwise)
                case "call_block":
                    self.call_block(stmt.call_block)
                case "push":
                    self.shift(stmt.push.stack, stmt.push.count)
                case "pop":
                    self.shift(stmt.pop.stack, -stmt.pop.count)
                case _:
                    pass

    def extract(self, target: pb.LValue) -> None:
        type = self.lvalue_type(target)
        path = self.lpath(target)
        if path is None:
            self.consume(width_of(type, self.index))
            return
        offset = self.cursor
        for f in self.index.header_types[type.header].fields:
            width = width_of(f.type, self.index)
            slot = Slot(offset, width)
            self.bits.ensure(offset + width)
            self.bits.write(slot, self.gen.field_value(width, (*path, f.name)))
            self.known[(*path, f.name)] = slot
            offset += width
        self.cursor = offset

    def consume(self, width: int) -> None:
        self.cursor += width
        self.bits.ensure(self.cursor)

    def verify(self, condition: pb.Expr) -> None:
        """Make the condition hold, usually; stop if it is known to fail."""
        if self.rng.random() < self.gen.tuning.satisfy_verify:
            self.satisfy(condition)
        if self.truth(condition) is False:
            raise Stop

    def satisfy(self, condition: pb.Expr) -> None:
        """Write packet bits so that `field == constant` conditions, and
        conjunctions of them, hold. Anything else is left as it is."""
        if condition.WhichOneof("kind") != "binary":
            return
        b = condition.binary
        if b.op == pb.BINARY_OP_AND:
            self.satisfy(b.left)
            self.satisfy(b.right)
            return
        if b.op not in (pb.BINARY_OP_EQ, pb.BINARY_OP_NE):
            return
        left, right = self.value(b.left), self.value(b.right)
        if isinstance(left, int) and isinstance(right, Slot):
            left, right = right, left
        if not (isinstance(left, Slot) and isinstance(right, int)):
            return
        if b.op == pb.BINARY_OP_EQ:
            self.bits.write(left, right)
        elif self.bits.read(left) == right:
            self.bits.write(left, right ^ 1)

    def assign(self, target: pb.LValue, expr: pb.Expr) -> None:
        path = self.lpath(target)
        if path is None:
            return
        source = self.path(expr)
        if source is not None and source not in self.known:
            # A header or struct copy: every location under it moves.
            self.forget(path)
            for key, value in list(self.known.items()):
                if key[: len(source)] == source:
                    self.known[(*path, *key[len(source) :])] = value
            for key, value in list(self.next_index.items()):
                if key[: len(source)] == source:
                    self.next_index[(*path, *key[len(source) :])] = value
            return
        value = self.value(expr)
        self.forget(path)
        if value is not None:
            self.known[path] = value

    def forget(self, path: Path) -> None:
        for key in [k for k in self.known if k[: len(path)] == path]:
            del self.known[key]

    def call_block(self, call: pb.CallBlock) -> None:
        callee = self.index.blocks[call.block]
        self.depth += 1
        aliases: dict[str, Path] = {}
        for param, arg in zip(callee.params, call.args, strict=True):
            if arg.WhichOneof("kind") == "lvalue":
                path = self.lpath(arg.lvalue)
            else:
                path = (f"{callee.name}@{self.depth}", param.name)
                value = self.value(arg.expr)
                self.forget(path)
                if value is not None:
                    self.known[path] = value
            if path is not None:
                aliases[param.name] = path
        self.frames.append(Frame(self.index.scopes[callee.name], aliases))
        try:
            self.states(callee)
        finally:
            self.frames.pop()
            self.depth -= 1

    def shift(self, stack: pb.LValue, count: int) -> None:
        path = self.lpath(stack)
        if path is None:
            return
        size = self.lvalue_type(stack).stack.size
        self.next_index[path] = min(max(self.next_index.get(path, 0) + count, 0), size)
        self.forget(path)

    # -- transitions ---------------------------------------------------------

    def transition(self, t: pb.Transition) -> pb.Target:
        if t.WhichOneof("kind") == "direct":
            return t.direct
        return self.select(t.select)

    def select(self, s: pb.Select) -> pb.Target:
        """Pick a case at random, write the bits that make it match, then
        take the first case that matches what the packet now says, as the
        interpreters will."""
        sources = [self.value(k) for k in s.keys]
        for case in self.rng.sample(list(s.cases), len(s.cases)):
            if all(self.constrain(src, ks) for src, ks in zip(sources, case.sets, strict=True)):
                break
        for case in s.cases:
            if all(self.matches(src, ks) for src, ks in zip(sources, case.sets, strict=True)):
                return case.target
        raise Stop

    def constrain(self, source: Source | None, ks: pb.KeySet) -> bool:
        """Make `source` match `ks` if the packet decides it; report whether
        a constant contradicts it."""
        match ks.WhichOneof("kind"):
            case "exact":
                want = _literal_int(ks.exact)
            case "masked":
                want = _literal_int(ks.masked.value)
            case "range":
                want = None
            case _:
                return True
        if isinstance(source, Slot):
            match ks.WhichOneof("kind"):
                case "exact":
                    assert want is not None
                    self.bits.write(source, want)
                case "masked":
                    assert want is not None
                    mask = _literal_int(ks.masked.mask) or 0
                    self.bits.write(source, (self.bits.read(source) & ~mask) | (want & mask))
                case "range":
                    lo, hi = _literal_int(ks.range.lo), _literal_int(ks.range.hi)
                    if lo is not None and hi is not None and lo <= hi:
                        self.bits.write(source, self.rng.randint(lo, hi))
            return True
        return self.matches(source, ks)

    def matches(self, source: Source | None, ks: pb.KeySet) -> bool:
        """Whether the key set matches; an unknown source is taken to match."""
        value = self.bits.read(source) if isinstance(source, Slot) else source
        if value is None:
            return True
        match ks.WhichOneof("kind"):
            case "exact":
                return _literal_int(ks.exact) == value
            case "masked":
                v, m = _literal_int(ks.masked.value), _literal_int(ks.masked.mask)
                return v is None or m is None or (value & m) == (v & m)
            case "range":
                lo, hi = _literal_int(ks.range.lo), _literal_int(ks.range.hi)
                return lo is None or hi is None or lo <= value <= hi
            case _:
                return True

    # -- expressions ---------------------------------------------------------

    def path(self, expr: pb.Expr) -> Path | None:
        """The storage `expr` names, resolved through the frame's aliases."""
        match expr.WhichOneof("kind"):
            case "var":
                return self.frame.root(expr.var)
            case "member":
                base = self.path(expr.member.base)
                return None if base is None else (*base, expr.member.field)
            case "index":
                base = self.path(expr.index.base)
                i = self.value(expr.index.index)
                return None if base is None or not isinstance(i, int) else (*base, i)
            case _:
                return None

    def lpath(self, lv: pb.LValue) -> Path | None:
        match lv.WhichOneof("kind"):
            case "var":
                return self.frame.root(lv.var)
            case "member":
                base = self.lpath(lv.member.base)
                return None if base is None else (*base, lv.member.field)
            case "index":
                base = self.lpath(lv.index.base)
                i = self.value(lv.index.index)
                return None if base is None or not isinstance(i, int) else (*base, i)
            case "next":
                base = self.lpath(lv.next.stack)
                if base is None:
                    return None
                size = self.lvalue_type(lv.next.stack).stack.size
                i = self.next_index.get(base, 0)
                if i >= size:
                    raise Stop  # StackOutOfBounds
                self.next_index[base] = i + 1
                return (*base, i)
            case _:
                return None

    def value(self, expr: pb.Expr) -> Source | None:
        """What the walk knows of `expr`: packet bits, a constant, or nothing."""
        match expr.WhichOneof("kind"):
            case "literal":
                return _literal_int(expr.literal)
            case "var" | "member" | "index":
                path = self.path(expr)
                return None if path is None else self.known.get(path)
            case "last_index":
                path = self.path(expr.last_index.stack)
                return None if path is None else self.next_index.get(path, 0) - 1
            case "slice":
                inner = self.value(expr.slice.operand)
                s = expr.slice
                if isinstance(inner, Slot):
                    return Slot(inner.offset + inner.width - 1 - s.hi, s.hi - s.lo + 1)
                if isinstance(inner, int):
                    return (inner >> s.lo) & ((1 << (s.hi - s.lo + 1)) - 1)
                return None
            case "cast":
                inner = self.value(expr.cast.operand)
                to = expr.cast.to
                if to.WhichOneof("kind") != "bits":
                    return None
                if isinstance(inner, Slot):
                    if to.bits > inner.width:
                        return None
                    return Slot(inner.offset + inner.width - to.bits, to.bits)
                if isinstance(inner, int):
                    return inner & ((1 << to.bits) - 1)
                return None
            case "lookahead":
                width = width_of(expr.lookahead.type, self.index)
                self.bits.ensure(self.cursor + width)
                return Slot(self.cursor, width)
            case _:
                return None

    def truth(self, expr: pb.Expr) -> bool | None:
        """The condition's value when the walk can decide it."""
        match expr.WhichOneof("kind"):
            case "literal" if expr.literal.WhichOneof("value") == "boolean":
                return expr.literal.boolean
            case "unary" if expr.unary.op == pb.UNARY_OP_NOT:
                inner = self.truth(expr.unary.operand)
                return None if inner is None else not inner
            case "binary":
                return self.compare(expr.binary)
            case _:
                return None

    def compare(self, b: pb.Binary) -> bool | None:
        if b.op in (pb.BINARY_OP_AND, pb.BINARY_OP_OR):
            left, right = self.truth(b.left), self.truth(b.right)
            if left is None or right is None:
                return None
            return (left and right) if b.op == pb.BINARY_OP_AND else (left or right)
        x, y = self.concrete(b.left), self.concrete(b.right)
        if x is None or y is None:
            return None
        match b.op:
            case pb.BINARY_OP_EQ:
                return x == y
            case pb.BINARY_OP_NE:
                return x != y
            case pb.BINARY_OP_LT:
                return x < y
            case pb.BINARY_OP_LE:
                return x <= y
            case pb.BINARY_OP_GT:
                return x > y
            case pb.BINARY_OP_GE:
                return x >= y
            case _:
                return None

    def concrete(self, expr: pb.Expr) -> int | None:
        source = self.value(expr)
        return self.bits.read(source) if isinstance(source, Slot) else source

    def lvalue_type(self, lv: pb.LValue) -> pb.Type:
        return type_of(_lvalue_expr(lv), self.index, self.frame.scope)


def _literal_int(literal: pb.Literal) -> int | None:
    match literal.WhichOneof("value"):
        case "bits":
            return int(literal.bits.value)
        case "boolean":
            return int(literal.boolean)
        case _:
            return None


def _lvalue_expr(lv: pb.LValue) -> pb.Expr:
    """The lvalue as an expression, for `type_of`; `next` types as element 0."""
    match lv.WhichOneof("kind"):
        case "var":
            return pb.Expr(var=lv.var)
        case "member":
            return pb.Expr(
                member=pb.Member(base=_lvalue_expr(lv.member.base), field=lv.member.field)
            )
        case "index":
            return pb.Expr(index=pb.Index(base=_lvalue_expr(lv.index.base), index=lv.index.index))
        case "next":
            zero = pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=32, value="0")))
            return pb.Expr(index=pb.Index(base=_lvalue_expr(lv.next.stack), index=zero))
        case kind:
            raise ValueError(f"lvalue of kind {kind!r}")
