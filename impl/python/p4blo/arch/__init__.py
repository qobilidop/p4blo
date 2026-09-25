"""Architectures: ordinary Python that runs a program's blocks.

This is the experiment for claim 3 of docs/design.md. The supplied packet
architectures take an ingress port and a packet, call the program's blocks,
and interpret their metadata to return egress ports and packets. Two are
here, a filter and a switch, and neither contains P4. Other architecture
compositions can use their own inputs and execution logic.

    contract.py   the metadata contract and the view of M it gives
    assembly.py   compose a block library with chosen H/M and exports
    loader.py     validate and bind with explicit registry, contract and
                  role kinds; once per program
    reference.py optional defaults for the supplied switch and filter
    filter.py     parser and control; the packet leaves as it came, or not
    switch.py     all three blocks; drop, flood or unicast over a few ports
    externs/      the extern families the architectures supply, and the
                  registry that binds them to a program
    v1model.py    the printer: IR to P4-16 under a v1model shim, so the P4
                  oracles can run a program; the only v1model support there is
"""

from __future__ import annotations

from typing import Protocol

from p4blo import stf
from p4blo.arch import reference
from p4blo.arch.assembly import assemble
from p4blo.arch.contract import CONTRACT, Contract, ContractError, Field, Metadata
from p4blo.arch.filter import Filter
from p4blo.arch.loader import Loaded, LoadError, load
from p4blo.arch.switch import Switch
from p4blo.interp.tables import InstalledEntries
from p4blo.v0 import p4blo_pb2 as pb


class Architecture(Protocol):
    """The packet-processing shape consumed by `stf_driver`."""

    diagnostics: list[str]

    def run(
        self, loaded: Loaded, entries: InstalledEntries, ingress_port: int, packet: bytes
    ) -> list[tuple[int, bytes]]: ...


def stf_driver(arch: Architecture, loaded: Loaded) -> stf.RunPacket:
    """Adapt an architecture to `stf.replay`'s `run_packet`.

    The host's entries are installed afresh for every packet, as the STF
    runner hands them over; extern state persists in `loaded` across the
    whole replay.
    """

    def run(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        return arch.run(loaded, loaded.entries(entries), port, packet)

    return run


__all__ = [
    "CONTRACT",
    "Architecture",
    "assemble",
    "Contract",
    "ContractError",
    "Field",
    "Filter",
    "LoadError",
    "Loaded",
    "Metadata",
    "Switch",
    "load",
    "reference",
    "stf_driver",
]
