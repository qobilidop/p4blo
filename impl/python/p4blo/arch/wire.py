"""Text, binary and JSON transport for architectural assemblies."""

from __future__ import annotations

from pathlib import Path

from google.protobuf import json_format, text_format

from p4blo.arch.v0 import assembly_pb2 as apb


def load_text(source: str | Path) -> apb.BlockAssembly:
    text = source.read_text() if isinstance(source, Path) else source
    return text_format.Parse(text, apb.BlockAssembly())


def dump_text(assembly: apb.BlockAssembly) -> str:
    return text_format.MessageToString(assembly)


def load_binary(data: bytes) -> apb.BlockAssembly:
    return apb.BlockAssembly.FromString(data)


def dump_binary(assembly: apb.BlockAssembly) -> bytes:
    return assembly.SerializeToString(deterministic=True)


def load_json(text: str) -> apb.BlockAssembly:
    return json_format.Parse(text, apb.BlockAssembly())


def dump_json(assembly: apb.BlockAssembly) -> str:
    return json_format.MessageToJson(assembly, preserving_proto_field_name=True)
