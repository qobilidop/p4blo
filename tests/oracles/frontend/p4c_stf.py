"""p4c's own STF vectors, replayed with p4c's runner semantics.

p4blo's replay (`p4blo.stf.replay`) pairs each packet with the `expect`
lines after it; p4c's runner queues expectations per port instead, so its
files may write `expect` before `packet`. Its files also name keys by p4c's
control-plane names, which drop the header-struct parameter
(`data.f1` for `hdrs.data.f1`) and write a stack index as `$0`. This
adapter reads a p4c file unchanged and replays it the p4c way: every
output on a port is matched in order against that port's expectations, and
an output nobody expected, or an expectation nothing produced, fails.

The architecture is p4blo's switch with 64 ports, so that v1model's drop
port 511 is out of range and drops, as it does in BMv2.
"""

from __future__ import annotations

import dataclasses
import re
from collections import defaultdict

from p4blo import arch, ir, stf
from p4blo.arch import v1model
from p4blo.arch.v0 import assembly_pb2 as apb

PORTS = 64


def _key_names(index: ir.Index) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for block in index.program.blocks:
        for table in block.tables:
            for key in table.keys:
                name = ir.key_name(key)
                if name is not None:
                    names.setdefault(table.name, []).append(name)
    return names


def _resolve_keys(index: ir.Index, statements: list[stf.Statement]) -> list[stf.Statement]:
    """Rename each `add` key to the program's key it names, matched as p4c
    matches it: the whole name, or a suffix after a dot."""
    names = _key_names(index)
    out: list[stf.Statement] = []
    for s in statements:
        if isinstance(s, stf.Add):
            table = s.table.rsplit(".", 1)[-1]
            keys = []
            for k in s.keys:
                found = [
                    n
                    for n in names.get(table, [])
                    if n == k.name or n.endswith("." + k.name) or k.name.endswith("." + n)
                ]
                keys.append(dataclasses.replace(k, name=found[0]) if len(found) == 1 else k)
            s = dataclasses.replace(s, keys=tuple(keys))
        out.append(s)
    return out


def replay(program: apb.BlockAssembly, text: str) -> list[str]:
    """Replay a p4c STF file on `program`; the problems found, if any."""
    loaded = v1model.load(program)
    run = arch.stf_driver(v1model.V1Model(ports=PORTS), loaded)
    statements = _resolve_keys(loaded.index, stf.parse(re.sub(r"\$([0-9]+)", r"[\1]", text)))
    installed: list[stf.Add | stf.SetDefault] = []
    expected: dict[int, list[stf.Expect]] = defaultdict(list)
    received: dict[int, list[bytes]] = defaultdict(list)
    for s in statements:
        if isinstance(s, stf.Add | stf.SetDefault):
            installed.append(s)
        elif isinstance(s, stf.Expect):
            expected[s.port].append(s)
        elif isinstance(s, stf.Packet):
            for port, data in run(stf.to_entries(loaded.index, installed), s.port, s.data):
                received[port].append(data)
    problems: list[str] = []
    for port in sorted(set(expected) | set(received)):
        wants, gots = expected.get(port, []), received.get(port, [])
        for want, got in zip(wants, gots, strict=False):
            if not want.matches(got):
                problems.append(f"line {want.line}: port {port} got {got.hex()}")
        for want in wants[len(gots) :]:
            problems.append(f"line {want.line}: nothing came out on port {port}")
        for got in gots[len(wants) :]:
            problems.append(f"port {port}: unexpected {got.hex()}")
    return problems
