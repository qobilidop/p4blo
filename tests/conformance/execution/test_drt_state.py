"""Real Lean execution conformance."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.drt_state import wide_register_roundtrip


@pytest.mark.lean
def test_lean_agrees_on_wide_register_state(tmp_path: Path, lean_binary: Path) -> None:
    wide_register_roundtrip(tmp_path, [lean_binary])
