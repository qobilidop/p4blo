#!/usr/bin/env bash
# Both Lake packages, in dependency order: the IR specification and the
# executable reference architecture. `lake build`
# builds each package's default targets, which include its <Root>Test library
# and so check every proof audit's `#guard_msgs` pins; `lake test` then runs
# the package's test driver.
set -euo pipefail
repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cmp "$repo_root/spec/ir/lean-toolchain" "$repo_root/spec/arch/lean-toolchain"
toolchain="$(<"$repo_root/spec/ir/lean-toolchain")"
# --wfail makes any warning fail the build, a `sorry` included, without
# rewriting the severities that #guard_msgs tests observe, which the
# warningAsError option would do.
for package in spec/ir spec/arch; do
  lake "+$toolchain" -d "$repo_root/$package" build --wfail
  # Lake's -d selects configuration but does not change the test process cwd.
  # Each test driver resolves its fixtures relative to its package root.
  (cd "$repo_root/$package" && lake "+$toolchain" test)
done
