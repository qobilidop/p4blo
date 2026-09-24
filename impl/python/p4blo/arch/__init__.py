"""Architectures: ordinary Python that runs a program's blocks.

This is the experiment for claim 3 of docs/design.md. An architecture is a
function of one shape, from an ingress port and a packet to egress ports
and packets, that calls the program's blocks and acts on the metadata they
leave. Two are here, a filter and a switch, and neither contains P4.

    contract.py   the metadata contract and the view of M it gives
    loader.py     validate, bind externs, check the contract, resolve the
                  exported roles; once per program
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
from p4blo.arch.contract import CONTRACT, Contract, ContractError, Field, Metadata
from p4blo.arch.filter import Filter
from p4blo.arch.loader import ROLES, Loaded, LoadError, load
from p4blo.arch.switch import Switch
from p4blo.interp.tables import InstalledEntries
from p4blo.v0 import p4blo_pb2 as pb


class Architecture(Protocol):
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
    "Contract",
    "ContractError",
    "Field",
    "Filter",
    "LoadError",
    "Loaded",
    "Metadata",
    "ROLES",
    "Switch",
    "load",
    "stf_driver",
]
