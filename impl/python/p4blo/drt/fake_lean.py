"""A stand-in for `p4blo-lean run`, backed by the Python interpreter.

    python -m p4blo.drt.fake_lean run <program.json> [--ports N] [--flip]
    python -m p4blo.drt.fake_lean coverage-inventory

It speaks the pipe protocol of `p4blo.drt.run` exactly, so the harness can
be exercised end to end without Lean: Python against Python through the
pipe must report no divergence, and `--flip`, which corrupts the first
byte of the first output packet of every reply, must report one for every
case that produced output. Extern state lives in one `Loaded` for the life
of the process, as the protocol requires.

Rule coverage is the Lean semantics' own measure, and the Python interpreter
has no rule tags to approximate it honestly, so every reply carries an empty
`coverage` list and the inventory is empty: a campaign against the fake
measures nothing, and says so, rather than something that looks like the
criterion.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from google.protobuf import json_format

from p4blo import arch, ir
from p4blo.drt.state import encode, snapshot
from p4blo.v0 import p4blo_pb2 as pb


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fake_lean")
    parser.add_argument("mode", choices=["run", "coverage-inventory"])
    parser.add_argument("program", type=Path, nargs="?")
    parser.add_argument("--ports", type=int, default=4)
    parser.add_argument("--flip", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "coverage-inventory":
        # No rule tags: see the module docstring.
        return 0
    if args.program is None:
        parser.error("run needs a program")

    loaded = arch.load(ir.load_json(args.program.read_text()))
    switch = arch.Switch(args.ports)
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        entries = json_format.ParseDict(request["entries"], pb.Entries())
        packet = bytes.fromhex(request["packet"])
        switch.diagnostics.clear()
        try:
            outputs = switch.run(loaded, loaded.entries(entries), request["ingress_port"], packet)
        except Exception as e:  # noqa: BLE001 - reported to the other side
            reply: dict[str, object] = {"error": f"{type(e).__name__}: {e}"}
        else:
            if args.flip and outputs and outputs[0][1]:
                port, data = outputs[0]
                outputs[0] = (port, bytes([data[0] ^ 0xFF]) + data[1:])
            reply = {"outputs": [[port, data.hex()] for port, data in outputs]}
            if switch.diagnostics:
                reply["diagnostic"] = "; ".join(switch.diagnostics)
        reply["state"] = encode(snapshot(loaded))
        reply["coverage"] = []
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
