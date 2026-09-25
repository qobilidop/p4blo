"""Assembly and loader choices for this repository's switch and filter.

The generic assembler takes a block library and explicit export mapping;
the generic loader takes a registry, metadata contract and role kinds.
This module supplies the roles shared by :class:`p4blo.arch.Switch` and
:class:`p4blo.arch.Filter`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from p4blo.arch.assembly import assemble as assemble_explicit
from p4blo.arch.contract import CONTRACT, Contract
from p4blo.arch.externs import Registry, supplied_registry
from p4blo.arch.loader import Loaded, LoadError
from p4blo.arch.loader import load as load_explicit
from p4blo.edsl.blocks import Control, Deparser, Parser
from p4blo.edsl.library import BlockLibrary
from p4blo.edsl.views import Struct
from p4blo.v0 import p4blo_pb2 as pb

ROLE_KINDS: dict[str, int] = {
    "parser": pb.BLOCK_KIND_PARSER,
    "control": pb.BLOCK_KIND_CONTROL,
    "deparser": pb.BLOCK_KIND_DEPARSER,
}
ROLES: tuple[str, ...] = tuple(ROLE_KINDS)


def assemble(
    library: BlockLibrary,
    *,
    name: str,
    headers: type[Struct],
    metadata: type[Struct],
    parser: type[Parser[Any, Any]],
    control: type[Control[Any, Any]],
    deparser: type[Deparser[Any]],
) -> pb.Program:
    """Assemble the supplied switch's three block roles from a library."""
    for role, cls, kind in (
        ("parser", parser, Parser),
        ("control", control, Control),
        ("deparser", deparser, Deparser),
    ):
        if not (isinstance(cls, type) and issubclass(cls, kind)):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"{role} must be a {kind.__name__} class, got {cls!r}")
    return assemble_explicit(
        library,
        name=name,
        headers=headers,
        metadata=metadata,
        exports={"parser": parser, "control": control, "deparser": deparser},
    )


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


__all__ = ["ROLE_KINDS", "ROLES", "assemble", "load"]
