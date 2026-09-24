#!/usr/bin/env bash
# Every check CI runs, in order, stopping at the first failure.
# Run with the development tools from README.md#development on PATH.
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --locked --quiet
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -q
buf lint
buf generate
git diff --exit-code -- impl/python/p4blo/v0
actionlint
echo "all checks passed"
