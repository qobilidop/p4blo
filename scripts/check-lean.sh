#!/usr/bin/env bash
# Both Lake packages, including all default proof audit targets and tests.
set -euo pipefail
repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cmp "$repo_root/ir/lean-toolchain" "$repo_root/lean/lean-toolchain"
toolchain="$(<"$repo_root/ir/lean-toolchain")"
lake "+$toolchain" -d "$repo_root/ir" build
# Lake's -d selects configuration but does not change the test process cwd.
# Each test driver resolves its fixtures relative to its package root.
(cd "$repo_root/ir" && lake "+$toolchain" test)
lake "+$toolchain" -d "$repo_root/lean" build
(cd "$repo_root/lean" && lake "+$toolchain" test)
