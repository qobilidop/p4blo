"""The deparser entry point: `H -> Packet`.

The headers are copied in as the `in` parameter and every `emit` appends to
one bit buffer, which is padded to a byte at the end (docs/semantics.md,
"Deparsers"). The caller appends the payload it kept after parsing.
"""

from __future__ import annotations

from p4blo.interp.api import Externs, InterpError
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter
from p4blo.interp.stmt import execute
from p4blo.interp.values import Struct, copy
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


def run_deparser(
    index: Index,
    block: str,
    headers: Struct,
    externs: Externs,
) -> bytes:
    """Run deparser `block` and return the emitted bytes, zero-padded to a
    byte boundary."""
    decl = index.blocks[block]
    if decl.kind != pb.BLOCK_KIND_DEPARSER or len(decl.params) != 1:
        raise InterpError(f"block {block!r} is not a deparser of (in H)")
    (headers_param,) = decl.params
    emitter = Emitter()
    env = Env.for_block(index, decl, externs, emitter=emitter)
    env.vars[headers_param.name] = copy(headers)
    execute(decl.body, env)
    return emitter.to_bytes()
