"""Self-contained differential experiments, including cross-packet state.

    python -m p4blo.drt.replay failure.json [--lean PATH | --fake]

The bundle contains the exact program and all requests from fresh extern
state. Each request replaces host table entries, just as the DRT pipe does;
this avoids STF's accumulating entries and limited literal vocabulary.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from google.protobuf import json_format

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt._json import loads as strict_json_loads
from p4blo.drt.case import Case
from p4blo.drt.run import (
    ProtocolError,
    Report,
    compare_program,
    default_lean_binary,
    request_json,
)
from p4blo.v0 import p4blo_pb2 as pb


def save(report: Report, path: Path) -> None:
    """Save concrete inputs, not a recipe depending on the generator."""
    if report.program_ir is None:
        raise ValueError("report has no program to replay")
    path.write_text(
        json.dumps(
            {
                "format": "p4blo.drt",
                "version": 1,
                "program": json_format.MessageToDict(
                    report.program_ir, preserving_proto_field_name=True
                ),
                "ports": report.ports,
                "seed": report.seed,
                "requests": [json.loads(request_json(case)) for case in report.inputs],
                "divergences": [d.number for d in report.divergences],
                "completed_requests": report.cases,
                "protocol_error": report.protocol_error,
            },
            indent=2,
        )
        + "\n"
    )


def load(path: Path) -> tuple[apb.BlockAssembly, list[Case], int, int]:
    data = strict_json_loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("replay must be an object")
    if (
        data.get("format") != "p4blo.drt"
        or type(data.get("version")) is not int
        or data["version"] != 1
    ):
        raise ValueError("not a version 1 p4blo differential replay")
    ports, seed = data.get("ports"), data.get("seed")
    if type(ports) is not int or ports <= 0 or type(seed) is not int:
        raise ValueError("replay ports must be positive and seed must be an integer")
    raw_program = data.get("program")
    if not isinstance(raw_program, dict):
        raise ValueError("replay program must be an object")
    try:
        program = json_format.ParseDict(raw_program, apb.BlockAssembly())
    except json_format.ParseError as error:
        raise ValueError(f"invalid replay program protobuf JSON: {error}") from error
    cases: list[Case] = []
    requests = data.get("requests")
    if not isinstance(requests, list):
        raise ValueError("replay requests must be an array")
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("replay request must be an object")
        ingress = request.get("ingress_port")
        if type(ingress) is not int:
            raise ValueError("ingress_port must be an integer")
        raw_entries = request.get("entries")
        if not isinstance(raw_entries, dict):
            raise ValueError("replay entries must be an object")
        packet = request.get("packet")
        if not isinstance(packet, str):
            raise ValueError("replay packet must be a hex string")
        try:
            entries = json_format.ParseDict(raw_entries, pb.Entries())
        except json_format.ParseError as error:
            raise ValueError(f"invalid replay entries protobuf JSON: {error}") from error
        cases.append(Case(entries, ingress, bytes.fromhex(packet)))
    return program, cases, ports, seed


def replay(path: Path, command: Sequence[str | Path]) -> Report:
    program, cases, ports, seed = load(path)
    return compare_program(program, cases, ports, command, seed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--lean", type=Path, default=default_lean_binary())
    modes.add_argument("--fake", action="store_true")
    args = parser.parse_args(argv)
    command = [sys.executable, "-m", "p4blo.drt.fake_lean"] if args.fake else [args.lean]
    try:
        report = replay(args.bundle, command)
    except (ProtocolError, ValueError, KeyError, TypeError, OSError) as e:
        print(f"replay failed: {e}", file=sys.stderr)
        return 2
    print(report.summary())
    for d in report.divergences[:3]:
        print(d.describe())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
