"""STF vectors: parse, resolve against a program, replay.

STF is the Simple Test Framework format that p4c and P4-SpecTec already use,
so the same file can drive the reference interpreter and an oracle. p4blo
reads the subset below and gives it a stricter meaning than p4c's runner
does; the difference is deliberate and is spelled out under "Replay".

## Statements

One per line, `#` starts a comment, blank lines are ignored, and the leading
keyword is case-insensitive.

    add <table> [<priority>] <key>:<value> ... <action>(<param>:<value>, ...)
    setdefault <table> <action>(<param>:<value>, ...)
    packet <port> <hex bytes>
    expect <port> <hex bytes, `*` nibbles are don't-care> [$]
    no_packet
    wait

`<table>` and `<action>` are declaration names. They may be written
qualified, as p4c's vectors write them (`ingress.setb1`); only the last
component is matched, against the unqualified name in the program.

`<key>` is a key expression rendered as a dotted path of names, exactly as
the program's key expression reads: `hdr.ipv4.dstAddr`.

`<priority>` is required on a table with a ternary key and rejected on one
without. Larger wins, as docs/ir-semantics.md says.

`<port>` is a decimal number that fits `bit<9>`, the width of a port in the
metadata contract; whether it is a port of the architecture replaying the
vector is the architecture's to say.

## Numbers

A number is decimal (`42`), hexadecimal (`0x2a`) or binary (`0b101010`). A
hex or binary number may carry `*` in place of a digit, meaning don't-care:
`0x****0202` is a value of `0x00000202` under the mask `0x0000ffff`. A hex
digit covers four bits and a binary digit one, so the written form also
fixes the number's width; a decimal number has no width of its own and takes
the width of whatever it is matched against.

A key value may carry a prefix length, `10.0.1.0/24` written numerically as
`0x0a000100/24`, which is how an lpm key is given.

Which form a key value may take follows the key's match kind:

  - exact: a plain number.
  - lpm: `value/prefixlen`, or a plain number, which is a full-width prefix.
  - ternary: a masked number, or a plain number, which means an exact match
    (a mask of all ones).

## Packets and expectations

`packet` and `expect` take whitespace-separated hex, which is joined before
it is read, so `00 11 22` and `001122` are the same bytes. An `expect` may
write `*` for a nibble, which matches any value there. A `packet` may not:
an input packet is fully determined. As in p4c's runner, the bytes of an
`expect` are a prefix of the output: a longer output still matches, unless
the line ends in `$`, which demands the exact length. p4c's own vectors
depend on this, since many name only the header bytes.

## Replay

Every `add` and `setdefault` before a `packet` is installed before that
packet runs. `wait` does nothing; it exists so that p4c's vectors parse.

The outputs of a `packet` must equal, exactly and in order, the `expect`
statements that follow it, up to the next `packet`. `no_packet` asserts that
the preceding `packet` produced nothing. An output that no `expect` claims
and an `expect` that no output satisfies are both failures, and so is an
output on the right port with the wrong bytes. A `packet` with no `expect`
after it therefore already asserts that nothing came out; `no_packet` says
the same thing in writing, so that a drop looks deliberate.

This is stricter than p4c's runner, which collects expectations per port and
tolerates unclaimed output. p4blo is a semantics project: an output packet
nobody predicted is exactly the kind of divergence the vectors exist to
catch.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from p4blo import ir
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator import ValidationError
from p4blo.validator.typer import expr_type

__all__ = [
    "Add",
    "ActionArg",
    "Expect",
    "Failure",
    "Key",
    "NoPacket",
    "Packet",
    "ReplayFailed",
    "RunPacket",
    "SetDefault",
    "StfError",
    "Statement",
    "Wait",
    "assert_replay",
    "parse",
    "replay",
    "to_entries",
]


class StfError(Exception):
    """A vector file that cannot be read, or cannot be resolved against a
    program. Carries the line number when there is one."""


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Key:
    """One `<key>:<value>` of an `add`.

    `name` is the dotted path of the key expression. `mask` is `None` unless
    the value carried `*` digits, `prefix_len` is `None` unless it carried
    `/n`, and `width` is the width the written form implies, `None` for a
    decimal number.
    """

    name: str
    value: int
    mask: int | None = None
    prefix_len: int | None = None
    width: int | None = None


@dataclass(frozen=True, slots=True)
class ActionArg:
    """One `<param>:<value>` of an action call."""

    name: str
    value: int
    width: int | None = None


@dataclass(frozen=True, slots=True)
class Add:
    line: int
    table: str
    action: str
    keys: tuple[Key, ...] = ()
    args: tuple[ActionArg, ...] = ()
    priority: int | None = None


@dataclass(frozen=True, slots=True)
class SetDefault:
    line: int
    table: str
    action: str
    args: tuple[ActionArg, ...] = ()


@dataclass(frozen=True, slots=True)
class Packet:
    line: int
    port: int
    data: bytes


@dataclass(frozen=True, slots=True)
class Expect:
    """An expected output packet.

    `mask` has one byte per byte of `data`, with a nibble of `f` where the
    vector wrote a hex digit and `0` where it wrote `*`.
    """

    line: int
    port: int
    data: bytes
    mask: bytes
    # True when the line ended in `$`: the output must not be longer.
    exact: bool = False

    def matches(self, packet: bytes) -> bool:
        if len(packet) < len(self.data) or (self.exact and len(packet) != len(self.data)):
            return False
        return all(
            (b & m) == (d & m) for b, d, m in zip(packet, self.data, self.mask, strict=False)
        )


@dataclass(frozen=True, slots=True)
class NoPacket:
    line: int


@dataclass(frozen=True, slots=True)
class Wait:
    line: int


type Statement = Add | SetDefault | Packet | Expect | NoPacket | Wait


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

# A declaration name as STF writes it: qualified, indexed anywhere along the
# path (`extra[0].h`), and `$` is a name character because p4c's own vectors
# use it for generated names.
NAME = r"[A-Za-z_][A-Za-z0-9_.$]*(?:\[[0-9]+\][A-Za-z0-9_.$]*)*"

_HEX_DIGITS = "0123456789abcdefABCDEF"


@dataclass(frozen=True, slots=True)
class _Number:
    value: int
    mask: int | None
    width: int | None


def _parse_number(text: str, line: int) -> _Number:
    """Read an STF number: decimal, `0x` hex or `0b` binary, with `*` digits
    standing for don't-care in the two written-width forms."""
    body = text
    if body[:2].lower() == "0x":
        return _parse_digits(body[2:], 4, _HEX_DIGITS, text, line)
    if body[:2].lower() == "0b":
        return _parse_digits(body[2:], 1, "01", text, line)
    if "*" in body:
        raise StfError(f"line {line}: `*` needs a 0x or 0b number, got {text!r}")
    if not body or not all(c.isdigit() for c in body):
        raise StfError(f"line {line}: {text!r} is not a number")
    return _Number(int(body), None, None)


def _parse_digits(digits: str, bits: int, alphabet: str, text: str, line: int) -> _Number:
    if not digits:
        raise StfError(f"line {line}: {text!r} has no digits")
    value = 0
    mask = 0
    for digit in digits:
        value <<= bits
        mask <<= bits
        if digit == "*":
            continue
        if digit not in alphabet:
            raise StfError(f"line {line}: {text!r} is not a number")
        value |= int(digit, 1 << bits)
        mask |= (1 << bits) - 1
    width = bits * len(digits)
    return _Number(value, None if mask == (1 << width) - 1 else mask, width)


def _parse_hex_bytes(text: str, line: int, *, wildcards: bool) -> tuple[bytes, bytes]:
    """Read whitespace-separated hex into a value and a per-byte mask."""
    digits = "".join(text.split())
    if not digits:
        raise StfError(f"line {line}: expected hex bytes")
    if len(digits) % 2:
        raise StfError(f"line {line}: {len(digits)} hex digits is not whole bytes")
    value = bytearray()
    mask = bytearray()
    for i in range(0, len(digits), 2):
        byte = 0
        care = 0
        for digit in digits[i : i + 2]:
            byte <<= 4
            care <<= 4
            if digit == "*":
                if not wildcards:
                    raise StfError(f"line {line}: `*` is not allowed in a packet")
                continue
            if digit not in _HEX_DIGITS:
                raise StfError(f"line {line}: {digit!r} is not a hex digit")
            byte |= int(digit, 16)
            care |= 0xF
        value.append(byte)
        mask.append(care)
    return bytes(value), bytes(mask)


# ---------------------------------------------------------------------------
# The parser
# ---------------------------------------------------------------------------

_CALL_RE = re.compile(rf"({NAME})\s*\(([^)]*)\)\s*$")
_PAIR_RE = re.compile(rf"({NAME})\s*:\s*(\S+)")
_PRIORITY_RE = re.compile(r"^([0-9]+)\s*")
_INT_RE = re.compile(r"^[0-9]+$")


def parse(text: str) -> list[Statement]:
    """Read a vector file into statements, in order."""
    statements: list[Statement] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        keyword, _, rest = line.partition(" ")
        statements.append(_parse_statement(keyword.lower(), rest.strip(), number))
    return statements


def _parse_statement(keyword: str, rest: str, line: int) -> Statement:
    match keyword:
        case "add":
            return _parse_add(rest, line)
        case "setdefault":
            return _parse_setdefault(rest, line)
        case "packet":
            port, data = _parse_port_and_hex(rest, line, wildcards=False)
            return Packet(line, port, data[0])
        case "expect":
            exact = rest.rstrip().endswith("$")
            if exact:
                rest = rest.rstrip()[:-1]
            port, data = _parse_port_and_hex(rest, line, wildcards=True)
            return Expect(line, port, data[0], data[1], exact)
        case "no_packet":
            _expect_empty(keyword, rest, line)
            return NoPacket(line)
        case "wait":
            _expect_empty(keyword, rest, line)
            return Wait(line)
        case _:
            raise StfError(f"line {line}: unknown statement {keyword!r}")


def _expect_empty(keyword: str, rest: str, line: int) -> None:
    if rest:
        raise StfError(f"line {line}: {keyword} takes no arguments, got {rest!r}")


def _parse_port_and_hex(
    rest: str, line: int, *, wildcards: bool
) -> tuple[int, tuple[bytes, bytes]]:
    port_text, _, hex_text = rest.partition(" ")
    if not _INT_RE.match(port_text):
        raise StfError(f"line {line}: {port_text!r} is not a port")
    port = int(port_text)
    if port >= 2**9:
        # Ports are bit<9> everywhere a program can see them (the metadata
        # contract), so a wider one is the vector's mistake, not a packet's.
        raise StfError(f"line {line}: port {port} does not fit in bit<9>")
    return port, _parse_hex_bytes(hex_text, line, wildcards=wildcards)


def _split_call(rest: str, line: int) -> tuple[str, tuple[ActionArg, ...], str]:
    """Split a trailing `action(args)` off, returning it and what precedes."""
    call = _CALL_RE.search(rest)
    if call is None:
        raise StfError(f"line {line}: expected a trailing action(...)")
    args = tuple(
        ActionArg(name, number.value, number.width)
        for name, number in _parse_pairs(call.group(2), line)
    )
    return call.group(1), args, rest[: call.start()].strip()


def _parse_pairs(text: str, line: int) -> list[tuple[str, _Number]]:
    """Read `name:value` pairs, rejecting anything else in between."""
    pairs: list[tuple[str, _Number]] = []
    position = 0
    for match in _PAIR_RE.finditer(text):
        between = text[position : match.start()].strip(" \t,")
        if between:
            raise StfError(f"line {line}: cannot read {between!r}")
        pairs.append((match.group(1), _parse_number(match.group(2).rstrip(","), line)))
        position = match.end()
    trailing = text[position:].strip(" \t,")
    if trailing:
        raise StfError(f"line {line}: cannot read {trailing!r}")
    return pairs


def _parse_keys(text: str, line: int) -> tuple[int | None, tuple[Key, ...]]:
    priority: int | None = None
    match = _PRIORITY_RE.match(text)
    if match is not None:
        priority = int(match.group(1))
        text = text[match.end() :]
    keys: list[Key] = []
    for name, value_text in _parse_pairs_raw(text, line):
        value, _, prefix = value_text.partition("/")
        number = _parse_number(value, line)
        prefix_len: int | None = None
        if prefix:
            if not _INT_RE.match(prefix):
                raise StfError(f"line {line}: {prefix!r} is not a prefix length")
            prefix_len = int(prefix)
        keys.append(Key(name, number.value, number.mask, prefix_len, number.width))
    return priority, tuple(keys)


def _parse_pairs_raw(text: str, line: int) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    position = 0
    for match in _PAIR_RE.finditer(text):
        between = text[position : match.start()].strip()
        if between:
            raise StfError(f"line {line}: cannot read {between!r}")
        pairs.append((match.group(1), match.group(2)))
        position = match.end()
    trailing = text[position:].strip()
    if trailing:
        raise StfError(f"line {line}: cannot read {trailing!r}")
    return pairs


def _parse_add(rest: str, line: int) -> Add:
    action, args, head = _split_call(rest, line)
    table, _, key_text = head.partition(" ")
    if not table:
        raise StfError(f"line {line}: add needs a table name")
    priority, keys = _parse_keys(key_text.strip(), line)
    return Add(line, table, action, keys, args, priority)


def _parse_setdefault(rest: str, line: int) -> SetDefault:
    action, args, head = _split_call(rest, line)
    table = head.strip()
    if not table or " " in table:
        raise StfError(f"line {line}: setdefault takes a table and an action")
    return SetDefault(line, table, action, args)


# ---------------------------------------------------------------------------
# Name resolution
# ---------------------------------------------------------------------------


def dotted(expr: pb.Expr) -> str:
    """The dotted path a vector writes for a key expression (see ir.dotted_path)."""
    path = ir.dotted_path(expr)
    if path is None:
        raise StfError(
            f"a {expr.WhichOneof('kind')} key expression has no dotted name; name the key"
        )
    return path


def key_name(key: pb.Key) -> str:
    name = ir.key_name(key)
    if name is None:
        raise StfError("a key without a dotted path needs a name")
    return name


def _key_width(index: Index, block: str, key: pb.Key) -> int:
    try:
        width = expr_type(key.expr, index, index.scopes[block]).bits
    except ValidationError as e:
        raise StfError(f"key {key_name(key)!r}: {e}") from None
    if width == 0:
        raise StfError(f"key {key_name(key)!r} is not a bit<N>")
    return width


def _find_table(index: Index, written: str, line: int) -> tuple[str, pb.Table]:
    """Find the block that declares a table, by the table's unqualified name.

    Tables are block-scoped, so a name that two blocks declare is ambiguous
    unless the vector wrote it qualified with the block.
    """
    simple = written.rsplit(".", 1)[-1]
    found = [
        (block, scope.tables[simple])
        for block, scope in index.scopes.items()
        if simple in scope.tables
    ]
    if len(found) > 1:
        qualifiers = set(written.split(".")[:-1])
        narrowed = [pair for pair in found if pair[0] in qualifiers]
        if len(narrowed) == 1:
            return narrowed[0]
        blocks = ", ".join(sorted(block for block, _ in found))
        raise StfError(f"line {line}: table {simple!r} is declared in {blocks}")
    if not found:
        raise StfError(f"line {line}: no table named {simple!r}")
    return found[0]


def _find_action(index: Index, block: str, table: pb.Table, written: str, line: int) -> pb.Action:
    """Resolve an action name against the actions the table may invoke.

    p4c's vectors write the action qualified by its control, `ingress.setb1`,
    so only the last component is matched.
    """
    simple = written.rsplit(".", 1)[-1]
    if simple not in table.actions:
        allowed = ", ".join(table.actions)
        raise StfError(f"line {line}: {table.name} cannot run {simple!r}; it has {allowed}")
    return index.scopes[block].actions[simple]


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------


def _fits(value: int, width: int, what: str, line: int) -> str:
    if not 0 <= value < (1 << width):
        raise StfError(f"line {line}: {what} does not fit in {width} bits")
    return str(value)


def _key_value(key: pb.Key, width: int, written: Key, line: int) -> pb.KeyValue:
    """One entry key, in the form the table's match kind asks for."""
    if written.width is not None and written.width > width:
        raise StfError(f"line {line}: {written.name} is wider than its {width}-bit key")
    value = _fits(written.value, width, f"{written.name}={written.value}", line)
    match key.match_kind:
        case pb.MATCH_KIND_EXACT:
            if written.mask is not None or written.prefix_len is not None:
                raise StfError(f"line {line}: {written.name} is an exact key")
            return pb.KeyValue(exact=value)
        case pb.MATCH_KIND_LPM:
            if written.mask is not None:
                raise StfError(f"line {line}: an lpm key takes value/prefixlen, not a mask")
            prefix = width if written.prefix_len is None else written.prefix_len
            if prefix > width:
                raise StfError(f"line {line}: prefix /{prefix} exceeds the {width}-bit key")
            # Entries are canonical (docs/ir-semantics.md, "Tables"): a set bit
            # below the prefix would be rejected at installation, where the
            # line is gone, so it is rejected here.
            if written.value & ((1 << (width - prefix)) - 1):
                raise StfError(f"line {line}: {written.name} has bits below its /{prefix} prefix")
            return pb.KeyValue(lpm=pb.LpmValue(value=value, prefix_len=prefix))
        case pb.MATCH_KIND_TERNARY:
            if written.prefix_len is not None:
                raise StfError(f"line {line}: a ternary key takes a mask, not a prefix")
            # A plain number on a ternary key is an exact match.
            mask = (1 << width) - 1 if written.mask is None else written.mask
            if written.value & ~mask:
                raise StfError(f"line {line}: {written.name} has bits outside its mask")
            return pb.KeyValue(
                ternary=pb.TernaryValue(value=value, mask=_fits(mask, width, "the mask", line))
            )
        case _:
            raise StfError(f"line {line}: key {written.name!r} has no match kind")


def _action_call(action: pb.Action, args: Sequence[ActionArg], line: int) -> pb.ActionCall:
    """Put the written arguments in parameter order, at the declared widths."""
    written = {arg.name: arg for arg in args}
    if len(written) != len(args):
        raise StfError(f"line {line}: {action.name} has a repeated argument")
    call = pb.ActionCall(action=action.name)
    for param in action.params:
        arg = written.pop(param.name, None)
        if arg is None:
            raise StfError(f"line {line}: {action.name} needs an argument {param.name!r}")
        if not param.type.bits:
            raise StfError(f"line {line}: {action.name}.{param.name} is not a bit<N>")
        value = _fits(arg.value, param.type.bits, f"{param.name}={arg.value}", line)
        call.args.add().bits.CopyFrom(pb.BitsLiteral(width=param.type.bits, value=value))
    if written:
        extra = ", ".join(sorted(written))
        raise StfError(f"line {line}: {action.name} has no parameter {extra}")
    return call


def _entry(index: Index, block: str, table: pb.Table, add: Add) -> pb.Entry:
    written = {key.name: key for key in add.keys}
    if len(written) != len(add.keys):
        raise StfError(f"line {add.line}: a key is given twice")
    entry = pb.Entry()
    for key in table.keys:
        name = key_name(key)
        value = written.pop(name, None)
        if value is None:
            raise StfError(f"line {add.line}: {table.name} needs a key {name!r}")
        entry.keys.append(_key_value(key, _key_width(index, block, key), value, add.line))
    if written:
        extra = ", ".join(sorted(written))
        raise StfError(f"line {add.line}: {table.name} has no key {extra}")
    ternary = any(key.match_kind == pb.MATCH_KIND_TERNARY for key in table.keys)
    if ternary and add.priority is None:
        raise StfError(f"line {add.line}: {table.name} is ternary, so an entry needs a priority")
    if not ternary and add.priority is not None:
        raise StfError(f"line {add.line}: {table.name} has no ternary key, so a priority is noise")
    entry.priority = add.priority or 0
    action = _find_action(index, block, table, add.action, add.line)
    entry.action.CopyFrom(_action_call(action, add.args, add.line))
    return entry


def to_entries(index: Index, statements: Iterable[Statement]) -> pb.Entries:
    """Resolve every `add` and `setdefault` against a program.

    Names become the names the IR uses, values take their keys' widths, and
    each table's entries stay in the order the file installed them. Anything
    else in `statements` is ignored, so a whole file can be handed over.
    """
    entries = pb.Entries()
    tables: dict[tuple[str, str], pb.TableEntries] = {}

    def table_entries(written: str, line: int) -> tuple[str, pb.Table, pb.TableEntries]:
        block, table = _find_table(index, written, line)
        found = tables.get((block, table.name))
        if found is None:
            found = entries.tables.add(block=block, table=table.name)
            tables[block, table.name] = found
        return block, table, found

    for statement in statements:
        match statement:
            case Add():
                block, table, into = table_entries(statement.table, statement.line)
                into.entries.append(_entry(index, block, table, statement))
            case SetDefault():
                block, table, into = table_entries(statement.table, statement.line)
                action = _find_action(index, block, table, statement.action, statement.line)
                into.default_action.CopyFrom(_action_call(action, statement.args, statement.line))
            case _:
                pass
    return entries


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Failure:
    """One way a vector file did not hold, with the line that claimed it."""

    line: int
    message: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.message}"


class ReplayFailed(AssertionError):
    """One or more expectations did not hold."""


# Given the entries installed so far, an ingress port and a packet, return
# the packets the architecture emitted, as (port, bytes) in order.
type RunPacket = Callable[[pb.Entries, int, bytes], list[tuple[int, bytes]]]


@dataclass(slots=True)
class _Run:
    """One `packet` and everything claimed about its output."""

    packet: Packet
    entries: pb.Entries
    expects: list[Expect] = field(default_factory=list)
    no_packet: NoPacket | None = None


def _runs(index: Index, statements: Sequence[Statement]) -> tuple[list[_Run], list[Failure]]:
    """Group the statements into one run per `packet`, with the entries
    installed before it and the expectations that follow it."""
    runs: list[_Run] = []
    failures: list[Failure] = []
    installed: list[Add | SetDefault] = []
    for statement in statements:
        match statement:
            case Add() | SetDefault():
                installed.append(statement)
            case Packet():
                runs.append(_Run(statement, to_entries(index, installed)))
            case Expect():
                if not runs:
                    failures.append(Failure(statement.line, "expect before any packet"))
                else:
                    runs[-1].expects.append(statement)
            case NoPacket():
                if not runs:
                    failures.append(Failure(statement.line, "no_packet before any packet"))
                elif runs[-1].expects:
                    failures.append(Failure(statement.line, "no_packet after an expect"))
                else:
                    runs[-1].no_packet = statement
            case Wait():
                pass
    return runs, failures


def replay(index: Index, statements: Sequence[Statement], run_packet: RunPacket) -> list[Failure]:
    """Replay a vector file against `run_packet`, collecting every failure.

    Nothing is raised: a caller that wants an exception uses `assert_replay`.
    """
    runs, failures = _runs(index, statements)
    for run in runs:
        outputs = run_packet(run.entries, run.packet.port, run.packet.data)
        failures.extend(_compare(run, outputs))
    return failures


def _compare(run: _Run, outputs: Sequence[tuple[int, bytes]]) -> list[Failure]:
    failures: list[Failure] = []
    for expect, output in zip(run.expects, outputs, strict=False):
        port, data = output
        if port != expect.port:
            failures.append(
                Failure(expect.line, f"expected output on port {expect.port}, got port {port}")
            )
        elif not expect.matches(data):
            failures.append(
                Failure(expect.line, f"expected {_hex(expect.data, expect.mask)}, got {data.hex()}")
            )
    for expect in run.expects[len(outputs) :]:
        failures.append(Failure(expect.line, "no output packet"))
    for port, data in outputs[len(run.expects) :]:
        line = run.no_packet.line if run.no_packet is not None else run.packet.line
        failures.append(Failure(line, f"unexpected output on port {port}: {data.hex()}"))
    return failures


def _hex(data: bytes, mask: bytes) -> str:
    """Render an expectation the way the vector wrote it, `*` and all."""
    out: list[str] = []
    for byte, care in zip(data, mask, strict=True):
        high = f"{byte >> 4:x}" if care & 0xF0 else "*"
        low = f"{byte & 0xF:x}" if care & 0x0F else "*"
        out.append(high + low)
    return "".join(out)


def assert_replay(index: Index, statements: Sequence[Statement], run_packet: RunPacket) -> None:
    """Replay, and raise `ReplayFailed` listing every failure if any held."""
    failures = replay(index, statements, run_packet)
    if failures:
        listed = "\n".join(f"  {failure}" for failure in failures)
        raise ReplayFailed(f"{len(failures)} expectation(s) failed:\n{listed}")
