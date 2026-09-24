"""Loading a program for an architecture.

`load` does everything that happens once per program rather than once per
packet: validation, binding every extern instance to its implementation,
checking `M` against the metadata contract, and resolving the blocks the
architecture will ask for by role. What it returns is the world an
architecture runs packets in. Extern state lives in `Loaded.externs` and
persists for as long as the `Loaded` does, which is what makes a register
stateful across packets.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from p4blo import validator
from p4blo.arch.contract import CONTRACT, Contract, Metadata
from p4blo.arch.externs import Registry, default_registry
from p4blo.interp import ExternBinding
from p4blo.interp.tables import InstalledEntries
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb

# The roles the switch runs; the filter needs the first two.
ROLES: tuple[str, ...] = ("parser", "control", "deparser")


class LoadError(Exception):
    """The program exports no block under a role the architecture needs."""


@dataclass(frozen=True)
class Loaded:
    index: Index
    externs: dict[str, ExternBinding]
    metadata: Metadata
    # Role to block name, for the roles `load` was asked to resolve.
    blocks: Mapping[str, str]

    def block(self, role: str) -> str:
        """The name of the block the program exports under `role`."""
        return self.blocks[role]

    def entries(self, host: pb.Entries | None = None) -> InstalledEntries:
        """The program's const entries and defaults, then the host's."""
        return InstalledEntries.build(self.index, host)


def load(
    program: pb.Program,
    registry: Registry | None = None,
    contract: Contract = CONTRACT,
    roles: Iterable[str] = ROLES,
) -> Loaded:
    """Validate, bind externs, check the contract, resolve `roles`.

    Raises `ValidationError`, `BindError`, `ContractError` or `LoadError`
    respectively; the last names the first role the program does not
    export. `roles` defaults to the three the switch runs; a program for
    the filter alone may be loaded with `("parser", "control")`.
    """
    index = validator.check(program)
    if registry is None:
        registry = default_registry()
    blocks: dict[str, str] = {}
    for role in roles:
        try:
            blocks[role] = index.exported(role).name
        except KeyError:
            raise LoadError(f"the program exports no {role!r} block") from None
    return Loaded(index, registry.bind(index), contract.view(index), MappingProxyType(blocks))
