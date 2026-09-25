"""Loading a program for an architecture.

`load` does everything that happens once per program rather than once per
packet: validation, binding every extern instance to the caller's registry,
checking `M` against the caller's metadata contract, and resolving the
blocks the architecture will ask for by role and kind. What it returns is
the world an architecture runs packets in. Extern state lives in `Loaded.externs` and
persists for as long as the `Loaded` does, which is what makes a register
stateful across packets.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from p4blo import validator
from p4blo.arch.contract import Contract, Metadata
from p4blo.arch.externs import Registry
from p4blo.interp import ExternBinding
from p4blo.interp.tables import InstalledEntries
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


class LoadError(Exception):
    """The program does not satisfy an architecture's export requirements."""


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
    *,
    registry: Registry,
    contract: Contract,
    roles: Mapping[str, int],
) -> Loaded:
    """Validate, bind externs, check the contract, resolve `roles`.

    Raises `ValidationError`, `BindError`, `ContractError` or `LoadError`
    respectively. `roles` maps architecture-specific export names to the
    required `pb.BlockKind`. No roles, metadata fields or extern families
    are assumed by this loader.
    """
    index = validator.check(program)
    blocks: dict[str, str] = {}
    for role, kind in roles.items():
        try:
            block = index.exported(role)
        except KeyError:
            raise LoadError(f"the program exports no {role!r} block") from None
        if block.kind != kind:
            want = pb.BlockKind.Name(kind)
            got = pb.BlockKind.Name(block.kind)
            raise LoadError(f"export {role!r} must be {want}, got {got}")
        blocks[role] = block.name
    return Loaded(index, registry.bind(index), contract.view(index), MappingProxyType(blocks))
