"""The control entry point: `H x M x Entries -> H x M`.

Both parameters are `inout`: copied in, the body run once, copied out. The
control has no other effect (docs/ir-semantics.md, "Controls"); tables read
the installed entries, and externs are the state the caller passed in.
"""

from __future__ import annotations

from p4blo.interp.api import Externs, InterpError
from p4blo.interp.env import Env
from p4blo.interp.expr import expect_struct
from p4blo.interp.stmt import execute
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Struct, copy
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


def run_control(
    index: Index,
    block: str,
    headers: Struct,
    metadata: Struct,
    entries: InstalledEntries,
    externs: Externs,
) -> tuple[Struct, Struct]:
    """Run control `block` and return the new headers and metadata."""
    decl = index.blocks[block]
    if decl.kind != pb.BLOCK_KIND_CONTROL or len(decl.params) != 2:
        raise InterpError(f"block {block!r} is not a control of (inout H, inout M)")
    headers_param, metadata_param = decl.params
    env = Env.for_block(index, decl, externs, entries=entries)
    env.vars[headers_param.name] = copy(headers)
    env.vars[metadata_param.name] = copy(metadata)
    execute(decl.body, env)
    return expect_struct(env.vars[headers_param.name]), expect_struct(env.vars[metadata_param.name])
