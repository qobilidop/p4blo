"""Package checks without native oracle dependencies."""

import pytest

from p4blo.arch import v1model
from tests.support.extern_families import family_program


@pytest.mark.parametrize("suffix", ["", ".8", ".multiple.dots"])
def test_python_dispatches_existing_families(suffix: str) -> None:
    assert set(v1model.load(family_program(suffix)).externs) == {"r", "c", "s"}
