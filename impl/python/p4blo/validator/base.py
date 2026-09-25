"""The state a validator run keeps, and how it reports.

Every rule class of this package builds on `Checker`: the program being
checked, its `ir.Index` once built, the diagnostics found so far, and what
the later rules learn from the earlier ones (the header and metadata types,
where each block is, and the call graph).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import Diagnostic


@dataclass
class Checker:
    program: pb.Program
    diagnostics: list[Diagnostic] = field(default_factory=list)
    index: ir.Index | None = None
    # The types of H and M once they are known to be structs.
    headers: pb.Type | None = None
    metadata: pb.Type | None = None
    block_paths: dict[str, str] = field(default_factory=dict)
    # Block call graph: caller name -> [(callee name, path of the call)].
    calls: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # The same for the actions of the block being checked, reset per block.
    action_calls: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def report(self, code: str, message: str, path: str) -> None:
        self.diagnostics.append(Diagnostic(code, message, path))

    @property
    def idx(self) -> ir.Index:
        assert self.index is not None
        return self.index
