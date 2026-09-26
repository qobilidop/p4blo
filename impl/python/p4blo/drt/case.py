"""One test case, and its rendering as an STF vector.

A case is what both interpreters receive: the host's entries, an ingress
port and a packet. `case_to_stf` writes it in the vector format of
`p4blo.stf` so that a divergence found at random becomes a file under
`tests/programs/corpus/` that every runner, human and oracle can be pointed at. The
outputs each side produced go in as comments: the vector states the
question, and whoever attributes the divergence writes the `expect` lines.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from p4blo import stf
from p4blo.interp.tables import InstalledEntries
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb

type Outputs = Sequence[tuple[int, bytes]]


@dataclass(frozen=True)
class Case:
    entries: pb.Entries
    ingress_port: int
    packet: bytes


def case_to_stf(
    index: Index,
    case: Case,
    *,
    comments: Mapping[str, Outputs | str] | None = None,
) -> str:
    """Render a case as STF: `add` and `setdefault` lines, then `packet`.

    `comments` maps a label ("python", "lean") to the outputs that side
    produced, or to a line of text such as `error: ...` or `str(outcome)`;
    each becomes a commented `expect` block after the packet, ready to be
    uncommented once attributed.
    Raises `ValueError` on what STF cannot write: an empty packet, or action
    data that is not `bit<N>`.
    """
    if not case.packet:
        raise ValueError("STF cannot write an empty packet")
    installed = InstalledEntries(index)
    lines: list[str] = []
    for te in case.entries.tables:
        ref = (te.block, te.table)
        table = installed.table(ref)
        widths = installed.key_widths(ref)
        for entry in te.entries:
            lines.append(_add_line(index, te.block, table, widths, entry))
        if te.HasField("default_action"):
            call = _call(index, te.block, te.default_action)
            lines.append(f"setdefault {te.block}.{te.table} {call}")
    if lines:
        lines.append("")
    lines.append(f"packet {case.ingress_port} {case.packet.hex()}")
    for label, outputs in (comments or {}).items():
        lines.append(f"# {label}:")
        if isinstance(outputs, str):
            lines.append(f"#   {outputs}")
        elif not outputs:
            lines.append("# no_packet")
        else:
            for port, data in outputs:
                lines.append(f"# expect {port} {data.hex()} $")
    return "\n".join(lines) + "\n"


def _add_line(index: Index, block: str, table: pb.Table, widths: list[int], entry: pb.Entry) -> str:
    parts = [f"add {block}.{table.name}"]
    if any(k.match_kind == pb.MATCH_KIND_TERNARY for k in table.keys):
        parts.append(str(entry.priority))
    for key, kv, width in zip(table.keys, entry.keys, widths, strict=True):
        parts.append(f"{stf.key_name(key)}:{_key_value(kv, width)}")
    parts.append(_call(index, block, entry.action))
    return " ".join(parts)


def _call(index: Index, block: str, call: pb.ActionCall) -> str:
    action = index.scopes[block].actions[call.action]
    args: list[str] = []
    for param, arg in zip(action.params, call.args, strict=True):
        if arg.WhichOneof("value") != "bits":
            raise ValueError(f"STF cannot write a {arg.WhichOneof('value')} argument")
        args.append(f"{param.name}:{arg.bits.value}")
    return f"{call.action}({', '.join(args)})"


def _number(value: int, width: int) -> str:
    """Hex when the width is whole nibbles, since STF fixes a hex number's
    width by its digits; decimal otherwise, which takes the key's width."""
    if width % 4 == 0:
        return f"0x{value:0{width // 4}x}"
    return str(value)


def _key_value(kv: pb.KeyValue, width: int) -> str:
    match kv.WhichOneof("kind"):
        case "exact":
            return _number(int(kv.exact), width)
        case "lpm":
            return f"{_number(int(kv.lpm.value), width)}/{kv.lpm.prefix_len}"
        case "ternary":
            return _masked(int(kv.ternary.value), int(kv.ternary.mask), width)
        case kind:
            raise ValueError(f"key value of kind {kind!r}")


def _masked(value: int, mask: int, width: int) -> str:
    """A ternary value as STF writes it: `*` digits where the mask is clear.

    A full mask is a plain number. A mask of whole nibbles is written in
    hex; any other mask needs binary, where a digit is one bit.
    """
    full = (1 << width) - 1
    if mask == full:
        return _number(value, width)
    if width % 4 == 0 and all(((mask >> i) & 0xF) in (0, 0xF) for i in range(0, width, 4)):
        digits = [
            f"{(value >> i) & 0xF:x}" if (mask >> i) & 0xF else "*"
            for i in range(width - 4, -1, -4)
        ]
        return "0x" + "".join(digits)
    bits = [str((value >> i) & 1) if (mask >> i) & 1 else "*" for i in range(width - 1, -1, -1)]
    return "0b" + "".join(bits)
