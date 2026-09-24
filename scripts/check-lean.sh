#!/usr/bin/env bash
# Both Lake packages, including all default proof audit targets and tests.
set -euo pipefail
repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cmp "$repo_root/spec/ir/lean-toolchain" "$repo_root/impl/lean/lean-toolchain"
toolchain="$(<"$repo_root/spec/ir/lean-toolchain")"
lake "+$toolchain" -d "$repo_root/spec/ir" build
# Lake's -d selects configuration but does not change the test process cwd.
# Each test driver resolves its fixtures relative to its package root.
(cd "$repo_root/spec/ir" && lake "+$toolchain" test)
lake "+$toolchain" -d "$repo_root/impl/lean" build
(cd "$repo_root/impl/lean" && lake "+$toolchain" test)
