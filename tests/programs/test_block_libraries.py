"""Application blocks compile before an architecture selects their roles."""

from __future__ import annotations

import pytest

from examples.firewall import program as firewall
from examples.load_balancer import program as load_balancer
from examples.router import program as router
from p4blo import edsl


@pytest.mark.parametrize("application", [router, firewall, load_balancer])
def test_application_library_preserves_assembled_block_bodies(application) -> None:
    compiled = application.blocks.compile()
    assembled = application.build()
    assert list(compiled.blocks) == list(assembled.blocks)
    assert list(compiled.extern_instances) == list(assembled.extern_instances)
    assert list(compiled.extern_types) == list(assembled.extern_types)
    assert not hasattr(compiled, "exports")
    assert not hasattr(compiled, "headers")
    assert not hasattr(compiled, "metadata")


def test_public_authoring_api_does_not_call_a_library_a_program() -> None:
    assert not hasattr(edsl, "Program")
