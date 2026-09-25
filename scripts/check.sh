#!/usr/bin/env bash
# Every check CI runs, in order, stopping at the first failure.
# Run with the development tools from README.md#development on PATH.
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --locked --quiet
uv run ruff format --check .
uv run ruff check .
uv run pyright
# The oracle-driven suites (marker `oracle`, see tests/conftest.py) take a
# quarter of an hour on a built local oracle and have their own workflows.
# The rest run in parallel: about two minutes on eight cores against nine
# in series, with the same result (2026-09-25).
# --dist loadgroup keeps the modules tests/conftest.py groups on one worker
# each, so an expensive module fixture runs once, and spreads the rest.
if [ "${P4BLO_ALL_TESTS:-}" = "1" ]; then uv run pytest -q -n auto --dist loadgroup; else uv run pytest -q -m "not oracle" -n auto --dist loadgroup; fi
buf lint
buf generate
git diff --exit-code -- impl/python/p4blo/v0
actionlint
echo "all checks passed"
