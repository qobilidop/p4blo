"""Mutable low-level builder for an architecture's flat assembly envelope."""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.arch.bindings import assembly_of
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl.core.blocks import Block, Control, Deparser, Parser
from p4blo.edsl.core.library import LibraryBuilder
from p4blo.edsl.core.types import EdslError, ParamSpec, StructType


class AssemblyBuilder(LibraryBuilder):
    """Collect declarations, H/M roots and role labels in one context."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._headers: StructType | None = None
        self._metadata: StructType | None = None
        self._exports: list[tuple[str, str]] = []

    @property
    def headers(self) -> StructType | None:
        return self._headers

    @headers.setter
    def headers(self, struct: StructType) -> None:
        self._headers = self._own_struct(struct, "headers")

    @property
    def metadata(self) -> StructType | None:
        return self._metadata

    @metadata.setter
    def metadata(self, struct: StructType) -> None:
        self._metadata = self._own_struct(struct, "metadata")

    def set_headers(self, struct: StructType) -> None:
        self.headers = struct

    def set_metadata(self, struct: StructType) -> None:
        self.metadata = struct

    def _own_struct(self, struct: StructType, what: str) -> StructType:
        if not isinstance(struct, StructType) or self.types.structs.get(struct.name) is not struct:
            raise EdslError(f"{what} must be a struct declared by this program")
        return struct

    def _default_params(self, name: str, spec: Sequence[tuple[str, str]]) -> list[ParamSpec]:
        params: list[ParamSpec] = []
        for pname, direction in spec:
            struct = self._headers if pname == "hdr" else self._metadata
            if struct is None:
                raise EdslError(
                    f"block {name}: set the program's headers and metadata structs first, "
                    "or give params explicitly"
                )
            params.append((pname, direction, struct))
        return params

    def parser(self, name: str, params: Sequence[ParamSpec] | None = None) -> Parser:
        if params is None:
            params = self._default_params(name, [("hdr", "out"), ("meta", "inout")])
        return super().parser(name, params)

    def control(self, name: str, params: Sequence[ParamSpec] | None = None) -> Control:
        if params is None:
            params = self._default_params(name, [("hdr", "inout"), ("meta", "inout")])
        return super().control(name, params)

    def deparser(self, name: str, params: Sequence[ParamSpec] | None = None) -> Deparser:
        if params is None:
            params = self._default_params(name, [("hdr", "in")])
        return super().deparser(name, params)

    def export(self, role: str, block: Block | str) -> None:
        if not role:
            raise EdslError("an export needs a role")
        if any(r == role for r, _ in self._exports):
            raise EdslError(f"role {role!r} is exported twice")
        name = self.block(block.name if isinstance(block, Block) else block).name
        self._exports.append((role, name))

    def build(self) -> apb.BlockAssembly:
        bindings = apb.BlockBindings(
            headers=self._headers.name if self._headers is not None else "",
            metadata=self._metadata.name if self._metadata is not None else "",
        )
        for role, block in self._exports:
            bindings.exports.add(role=role, block=block)
        return assembly_of(self.build_library(), bindings)


__all__ = ["AssemblyBuilder"]
