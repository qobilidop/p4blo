"""Shared drt replay fixtures and campaign helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb

ROOT = Path(__file__).resolve().parents[2]

FAKE = [sys.executable, "-m", "p4blo.drt.fake_lean"]


def register_program() -> apb.BlockAssembly:
    return arch_wire.load_text(ROOT / "tests/programs/corpus/register_bounds/register_bounds.txtpb")


def envelope(**changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "format": "p4blo.drt",
        "version": 1,
        "program": {},
        "ports": 4,
        "seed": 0,
        "requests": [],
    }
    result.update(changes)
    return result
