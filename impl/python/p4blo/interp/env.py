"""The run-time environment: variable storage for one block activation.

Names are block-scoped (proto header, "Names"), so each activation of a block
has its own store of parameters and locals, created at their zero values
(docs/ir-semantics.md, "Uninitialized variables"). While an action runs, its
parameters are layered on top of the block's store, because an action body
sees both. The packet, the emitter, the installed entries, the extern
bindings and the parser's revisit bookkeeping belong to the run and are
shared by every activation in it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from p4blo.interp.api import Externs, InterpError
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Value, zero
from p4blo.ir import BlockScope, Index
from p4blo.v0 import p4blo_pb2 as pb


@dataclass(slots=True)
class Env:
    index: Index
    scope: BlockScope
    externs: Externs
    vars: dict[str, Value]
    action: str | None = None
    action_vars: dict[str, Value] | None = None
    entries: InstalledEntries | None = None
    packet: Packet | None = None
    emitter: Emitter | None = None
    # (block name, state name) -> the cursor when that state was last entered.
    visits: dict[tuple[str, str], int] = field(default_factory=dict)

    @classmethod
    def for_block(
        cls,
        index: Index,
        block: pb.Block,
        externs: Externs,
        *,
        entries: InstalledEntries | None = None,
        packet: Packet | None = None,
        emitter: Emitter | None = None,
        visits: dict[tuple[str, str], int] | None = None,
    ) -> Env:
        """A fresh activation of `block`, every parameter and local at zero."""
        scope = index.scopes[block.name]
        store = {name: zero(decl.type, index) for name, decl in scope.vars.items()}
        return cls(
            index,
            scope,
            externs,
            store,
            entries=entries,
            packet=packet,
            emitter=emitter,
            visits={} if visits is None else visits,
        )

    @property
    def block(self) -> pb.Block:
        return self.scope.block

    def enter_block(self, block: pb.Block) -> Env:
        """A fresh activation of a called block that shares the run's state."""
        return Env.for_block(
            self.index,
            block,
            self.externs,
            entries=self.entries,
            packet=self.packet,
            emitter=self.emitter,
            visits=self.visits,
        )

    def enter_action(self, action: str, params: dict[str, Value]) -> Env:
        """This activation with an action's parameters layered on top."""
        return Env(
            self.index,
            self.scope,
            self.externs,
            self.vars,
            action,
            params,
            self.entries,
            self.packet,
            self.emitter,
            self.visits,
        )

    def read(self, name: str) -> Value:
        if self.action_vars is not None and name in self.action_vars:
            return self.action_vars[name]
        if name not in self.vars:
            raise InterpError(f"unknown variable {name!r} in block {self.block.name!r}")
        return self.vars[name]

    def write(self, name: str, value: Value) -> None:
        if self.action_vars is not None and name in self.action_vars:
            self.action_vars[name] = value
        elif name in self.vars:
            self.vars[name] = value
        else:
            raise InterpError(f"unknown variable {name!r} in block {self.block.name!r}")

    def require_packet(self) -> Packet:
        if self.packet is None:
            raise InterpError(f"block {self.block.name!r} has no packet")
        return self.packet

    def require_emitter(self) -> Emitter:
        if self.emitter is None:
            raise InterpError(f"block {self.block.name!r} has no packet to emit to")
        return self.emitter

    def require_entries(self) -> InstalledEntries:
        if self.entries is None:
            raise InterpError(f"block {self.block.name!r} has no table entries")
        return self.entries
