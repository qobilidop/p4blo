"""Extern types and extern instances.

An extern type declares its constructor parameters and methods, and an
instance supplies constant constructor arguments (EXTERN_ARGS). Calls to
an instance's methods are checked with the other calls.
"""

from __future__ import annotations

from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    EXTERN_ARGS,
)
from p4blo.validator.names import (
    BLOCK_PARAM_DIRECTIONS,
)
from p4blo.validator.types import (
    TypeChecks,
)


class ExternChecks(TypeChecks):
    """Extern type declarations and the instances of them."""

    def check_extern_types(self) -> None:
        for i, ext in enumerate(self.program.extern_types):
            path = f"extern_types[{i}]"
            self.check_names(
                [p.name for p in ext.constructor_params], f"{path}.constructor_params", "param"
            )
            self.check_params(
                ext.constructor_params,
                frozenset({pb.DIRECTION_IN}),
                f"{path}.constructor_params",
                "constructor",
            )
            self.check_names([m.name for m in ext.methods], f"{path}.methods", "method")
            for j, m in enumerate(ext.methods):
                mpath = f"{path}.methods[{j}]"
                self.check_names([p.name for p in m.params], f"{mpath}.params", "param")
                self.check_params(m.params, BLOCK_PARAM_DIRECTIONS, f"{mpath}.params", "method")
                if m.HasField("returns"):
                    self.check_type(m.returns, f"{mpath}.returns")

    def check_extern_instances(self) -> None:
        for i, inst in enumerate(self.program.extern_instances):
            path = f"extern_instances[{i}]"
            ext = self.resolve(
                inst.extern_type, self.idx.extern_types, "extern type", f"{path}.extern_type"
            )
            if ext is not None:
                self.check_literal_args(
                    inst.args, ext.constructor_params, f"{path}.args", EXTERN_ARGS
                )
