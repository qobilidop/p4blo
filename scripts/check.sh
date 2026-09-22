#!/usr/bin/env bash
# Every check CI runs, in order, stopping at the first failure.
# Run inside the flake: `nix develop -c scripts/check.sh` (or with direnv).
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --locked --quiet
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -q
buf lint
buf generate
git diff --exit-code -- python/p4blo/v0
echo "all checks passed"
