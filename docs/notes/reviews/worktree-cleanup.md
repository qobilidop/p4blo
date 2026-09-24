# Worktree cleanup review

2026-09-24. Independent read-only review in
`/private/tmp/p4blo-cleanup-review`, based on `e0b59b4`. The reviewer inspected
the proposed cleanup script, initial inventory and completed recovery archives.

## Finding and resolution

The first plan protected each worktree's current HEAD but omitted its private
HEAD reflog. The reviewer found exactly one commit outside `main` and without
a containing branch across all 86 removal targets:
`21378e4e9d620a7e3c7ef1400890025c1bf29b99`, “Plan constrained header-validity
reads”, in `p4blo-lvalue-codec`. Removal would discard that private reflog.

Before deletion, the integrator created and verified the local recovery ref
`refs/archive/worktree-cleanup-2026-09-24/lvalue-codec` at that exact commit.
It is not merged, published, or counted as implementation evidence.

The reviewer also suggested checking fresh staged/unstaged patch hashes to
detect an index-only change that preserves status text. The integrator added
both checks to the full preflight and immediately before each removal.

## Independent checks

- All 86 targets have zero unique current-HEAD commits relative to `main`;
  six intended trees are retained, including the two parked proof drafts.
- All 86 archive SHA-256 values, 971 stored file/symlink contents and modes,
  staged/unstaged patch hashes and manifest identities match.
- Index flags are normal; no assume-unchanged or skip-worktree entries hide
  local edits. No additional unprotected commit was found in target reflogs.

## Integrator process checks

The initial open-file preflight stopped on 260 read-only handles held by
Apple Virtualization for old printer-golden mounts in 26 worktrees. None
were working-directory, executable or write handles. Docker's only running
container was an unrelated BMv2 build with a named `/nix` volume and no
target bind mount. The final preflight permits only those exact observed
read-only cache descriptors, checks current running Docker bind mounts for
overlap, and rejects every other target handle. No Docker container, image,
volume or daemon was stopped or changed.

Source and index state are rechecked against the verified archives before
deletion; each deletion is verified by listing its parent directory. The
completed removal recount and retained-worktree checks are recorded in
[the cleanup report](../worktree-cleanup.md). No runtime implementation was
changed; Python/Lean/oracle tests were not rerun for this filesystem cleanup.
