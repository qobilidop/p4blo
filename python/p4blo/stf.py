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
    expect <port> <hex bytes, `*` nibbles are don't-care>
    no_packet
    wait

`<table>` and `<action>` are declaration names. They may be written
qualified, as p4c's vectors write them (`ingress.setb1`); only the last
component is matched, against the unqualified name in the program.

`<key>` is a key expression rendered as a dotted path of names, exactly as
the program's key expression reads: `hdr.ipv4.dstAddr`.

`<priority>` is required on a table with a ternary key and rejected on one
without. Larger wins, as docs/semantics.md says.

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
an input packet is fully determined.

## Replay

Every `add` and `setdefault` before a `packet` is installed before that
packet runs. `wait` does nothing; it exists so that p4c's vectors parse.

The outputs of a `packet` must equal, exactly and in order, the `expect`
statements that follow it, up to the next `packet`. `no_packet` asserts that
the preceding `packet` produced nothing. An output that no `expect` claims
and an `expect` that no output satisfies are both failures, and so is an
output on the right port with the wrong bytes.

This is stricter than p4c's runner, which collects expectations per port and
tolerates unclaimed output. p4blo is a semantics project: an output packet
nobody predicted is exactly the kind of divergence the vectors exist to
catch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "Add",
    "ActionArg",
    "Expect",
    "Key",
    "NoPacket",
    "Packet",
    "SetDefault",
    "StfError",
    "Statement",
    "Wait",
    "parse",
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

    def matches(self, packet: bytes) -> bool:
        if len(packet) != len(self.data):
            return False
        return all((b & m) == (d & m) for b, d, m in zip(packet, self.data, self.mask, strict=True))


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

# A declaration name as STF writes it: qualified, indexed, and `$` is a name
# character because p4c's own vectors use it for generated names.
NAME = r"[A-Za-z_][A-Za-z0-9_.$]*(?:\[[0-9]+\])?"

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
            port, data = _parse_port_and_hex(rest, line, wildcards=True)
            return Expect(line, port, data[0], data[1])
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
    return int(port_text), _parse_hex_bytes(hex_text, line, wildcards=wildcards)


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
