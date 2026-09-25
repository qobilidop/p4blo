"""Optional loader defaults for this repository's switch and filter.

The generic loader accepts an architecture's registry, metadata contract
and named role kinds explicitly. This module supplies the choices shared
by :class:`p4blo.arch.Switch` and :class:`p4blo.arch.Filter`.
"""

from __future__ import annotations

from collections.abc import Iterable

from p4blo.arch.contract import CONTRACT, Contract
from p4blo.arch.externs import Registry, supplied_registry
from p4blo.arch.loader import Loaded, LoadError
from p4blo.arch.loader import load as load_explicit
from p4blo.v0 import p4blo_pb2 as pb

ROLE_KINDS: dict[str, int] = {
    "parser": pb.BLOCK_KIND_PARSER,
    "control": pb.BLOCK_KIND_CONTROL,
    "deparser": pb.BLOCK_KIND_DEPARSER,
}
ROLES: tuple[str, ...] = tuple(ROLE_KINDS)


def load(
    program: pb.Program,
    *,
    registry: Registry | None = None,
    contract: Contract = CONTRACT,
    roles: Iterable[str] = ROLES,
) -> Loaded:
    """Load a program for the supplied switch or filter.

    `roles` is the subset this architecture will run. A switch uses all
    three; a filter uses ``("parser", "control")``. Callers may supply a
    registry with their own extern implementations.
    """
    required: dict[str, int] = {}
    for role in roles:
        try:
            required[role] = ROLE_KINDS[role]
        except KeyError:
            raise LoadError(f"the reference architecture has no {role!r} role") from None
    return load_explicit(
        program,
        registry=registry if registry is not None else supplied_registry(),
        contract=contract,
        roles=required,
    )


__all__ = ["ROLE_KINDS", "ROLES", "load"]
