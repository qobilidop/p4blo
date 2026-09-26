"""Compile all six printer goldens with the pinned native p4c image."""

import pytest

from tests.support.printer import GOLDEN_DIR, GOLDENS
from tests.support.printer_runtime import p4test


@pytest.mark.parametrize("name", [*GOLDENS, "forwarder", "port_parser"])
def test_golden_compiles(name: str) -> None:
    p4test(GOLDEN_DIR / f"{name}.p4")
