"""Architecture bindings, block entry helpers and scoped v1model execution."""

from __future__ import annotations

from typing import Protocol

from p4blo import stf
from p4blo.arch.assembly import assemble
from p4blo.arch.contract import CONTRACT, Contract, ContractError, Field, Metadata
from p4blo.arch.loader import Loaded, LoadError, load
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
    "LoadError",
    "Loaded",
    "Metadata",
    "load",
    "stf_driver",
]
