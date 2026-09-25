"""The parser entry point: `Packet x M -> H x M x consumed x accepted x error`.

The headers value starts at zero, the metadata is copied in, and the states
run from `start_state` (see `stmt.run_states`). A raised error or an
explicit `reject` stops the run; the outcome then carries the headers and
metadata as they were at that moment (docs/ir-semantics.md, "Parsers").
"""

from __future__ import annotations

from p4blo.arch.entry.outcome import ParseOutcome
from p4blo.interp.api import Externs, InterpError
from p4blo.interp.env import Env
from p4blo.interp.errors import ParseError
from p4blo.interp.expr import expect_struct
from p4blo.interp.packet import Packet
from p4blo.interp.stmt import run_states
from p4blo.interp.values import NO_ERROR, Struct, copy
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


def run_parser(
    index: Index,
    block: str,
    packet: bytes,
    metadata: Struct,
    externs: Externs,
) -> ParseOutcome:
    """Run parser `block` over `packet` with an initial metadata value.

    The headers value starts as the zero value of the program's headers type.
    """
    decl = index.blocks[block]
    if decl.kind != pb.BLOCK_KIND_PARSER or len(decl.params) != 2:
        raise InterpError(f"block {block!r} is not a parser of (out H, inout M)")
    headers_param, metadata_param = decl.params
    data = Packet(packet)
    env = Env.for_block(index, decl, externs, packet=data)
    env.vars[metadata_param.name] = copy(metadata)
    accepted = True
    error = NO_ERROR
    try:
        run_states(decl, env)
    except ParseError as e:
        accepted = False
        error = e.error
    return ParseOutcome(
        expect_struct(env.vars[headers_param.name]),
        expect_struct(env.vars[metadata_param.name]),
        data.cursor,
        accepted,
        error,
    )
