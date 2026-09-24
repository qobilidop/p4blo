"""Discover public program sources and their separate verification assets."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]
NAMES = sorted(path.parent.name for path in (ROOT / "examples").glob("*/program.py"))
DATA = ROOT / "tests/examples"


def build(name: str) -> pb.Program:
    return import_module(f"examples.{name}.program").build()
