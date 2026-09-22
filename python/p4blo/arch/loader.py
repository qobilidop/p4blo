"""Loading a program for an architecture.

`load` does everything that happens once per program rather than once per
packet: validation, binding every extern instance to its implementation,
and checking `M` against the metadata contract. What it returns is the
world an architecture runs packets in. Extern state lives in
`Loaded.externs` and persists for as long as the `Loaded` does, which is
what makes a register stateful across packets.
"""

from __future__ import annotations

from dataclasses import dataclass

from p4blo import validator
from p4blo.arch.contract import CONTRACT, Contract, Metadata
from p4blo.externs import Registry, default_registry
from p4blo.interp import ExternBinding
from p4blo.interp.tables import InstalledEntries
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


@dataclass(frozen=True)
class Loaded:
    index: Index
    externs: dict[str, ExternBinding]
    metadata: Metadata

    def block(self, role: str) -> str:
        """The name of the block the program exports under `role`."""
        return self.index.exported(role).name

    def entries(self, host: pb.Entries | None = None) -> InstalledEntries:
        """The program's const entries and defaults, then the host's."""
        return InstalledEntries.build(self.index, host)


def load(
    program: pb.Program, registry: Registry | None = None, contract: Contract = CONTRACT
) -> Loaded:
    """Validate, bind externs, check the contract.

    Raises `ValidationError`, `BindError` or `ContractError` respectively.
    """
    index = validator.check(program)
    if registry is None:
        registry = default_registry()
    return Loaded(index, registry.bind(index), contract.view(index))
