#!/usr/bin/env bash
# All three Lake packages, in dependency order, including every default proof
# audit target and each package's tests: the IR specification, the reference
# architecture specification, and the user library.
set -euo pipefail
repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cmp "$repo_root/spec/ir/lean-toolchain" "$repo_root/spec/arch/lean-toolchain"
cmp "$repo_root/spec/ir/lean-toolchain" "$repo_root/impl/lean/lean-toolchain"
toolchain="$(<"$repo_root/spec/ir/lean-toolchain")"
for package in spec/ir spec/arch impl/lean; do
  lake "+$toolchain" -d "$repo_root/$package" build
  # Lake's -d selects configuration but does not change the test process cwd.
  # Each test driver resolves its fixtures relative to its package root.
  (cd "$repo_root/$package" && lake "+$toolchain" test)
done
