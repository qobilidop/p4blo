"""Pin the fail-closed specialist-job boundary, including failed scope jobs."""

from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"
SPECIALIST_WORKFLOWS = ("lean.yml", "oracle.yml", "oracle-bmv2.yml", "xdp-build.yml")
# Keep one reviewed expression: a post-step failure may leave a false output
# behind, so output alone is insufficient to authorize skipping specialist CI.
REQUIRED_GUARD = (
    "if: ${{ always() && !cancelled() && "
    "(needs.scope.result != 'success' || needs.scope.outputs.full != 'false') }}"
)


def assert_scope_boundary(source: str) -> None:
    assert source.count("uses: ./.github/workflows/ci-scope.yml") == 1
    assert source.count("    needs: scope\n") == 1
    assert source.count("    " + REQUIRED_GUARD + "\n") == 1


@pytest.mark.parametrize("name", SPECIALIST_WORKFLOWS, ids=("lean", "spectec", "switch", "xdp"))
def test_specialist_job_requires_successful_scope_before_skipping(name: str) -> None:
    assert_scope_boundary((WORKFLOWS / name).read_text())


def test_boundary_rejects_guard_that_trusts_failed_scope_output() -> None:
    source = (WORKFLOWS / "lean.yml").read_text()
    unsafe = source.replace(
        REQUIRED_GUARD,
        "if: ${{ always() && !cancelled() && needs.scope.outputs.full != 'false' }}",
    )
    assert unsafe != source
    with pytest.raises(AssertionError):
        assert_scope_boundary(unsafe)
