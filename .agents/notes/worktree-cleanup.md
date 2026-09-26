# Local worktree cleanup

Completed 2026-09-24 at the user's request, starting from main `e0b59b4`.
The inventory contained 92 worktrees occupying about 88.10 GiB by `du -sk`.
Removed 86 obsolete checkouts: 50 clean merged trees and 36 old review/fault
campaign trees with local changes. Their checkout/build data totaled about
82.47 GiB; this is a summed allocation estimate, not a physical free-space
claim on APFS or shared/hardlinked caches. Six worktrees remain.

## Preserved worktrees

Later on 2026-09-24 the five non-main trees below were converted to
pushed branches and removed; only `p4blo` remains registered. Their
contents and gaps are in [parked-proofs.md](parked-proofs.md). The table
records what was retained at the time of the cleanup.

All paths below were under `/Users/qobilidop/my/work/`.

| Worktree | Reason retained |
|---|---|
| `p4blo` | Main checkout and published website |
| `p4blo-firewall-readback` | Documented unfinished proof/Python draft |
| `p4blo-forwarder-ingress` | Documented unfinished proof/Python draft |
| `p4blo-firewall-adversarial` | Unique local commit; not assumed obsolete |
| `p4blo-program-codec-next` | Unique local commit; not assumed obsolete |
| `p4blo-naming-review` | Uncommitted reviews, including parked-work reviews; its tip is patch-equivalent to a main commit |

No local or remote branches were deleted. Independent review found one
additional commit existing only in a removed tree's private HEAD reflog:
`21378e4e9d620a7e3c7ef1400890025c1bf29b99`. It is now retained by the local
ref `refs/archive/worktree-cleanup-2026-09-24/lvalue-codec`. This reference
and the recovery archives are local, not published to GitHub.

## Recovery archives

Location:
`/Users/qobilidop/my/work/p4blo/.artifacts/worktree-cleanup/2026-09-23/`.
The date names the initial inventory directory; completion crossed midnight.

- `inventory.json`: original paths, HEADs, branches, statuses and sizes.
- `archives.json`: archive paths, original HEADs and individual SHA-256 hashes.
- `archives/<worktree-name>.tar.gz`: 86 verified archives, totaling
  283,873,510 bytes (270.72 MiB), preserving 971 file/symlink entries.
- `removed.json`: exact 86 removed paths; each was verified absent by a
  filesystem listing, and the final registration count was checked against
  the original inventory.
- `cleanup.py`: the one-off procedure, including preflight checks.

Each archive contains `metadata.json`, `staged.patch`, `unstaged.patch` and
`files/`. Together they preserve local tracked edits, untracked files and
non-cache ignored experiment artifacts, including the release evidence.
Rebuildable `.lake`, `.venv`, Python bytecode, Hypothesis, pytest and Ruff
caches were excluded. Original committed source remains reachable on `main`
and existing branches. No build, proof or runtime claim depends on keeping
these obsolete checkout directories.

To recover a snapshot, first check the archive against `archives.json`,
then unpack it into a separate empty recovery directory. Add a new detached
worktree at the full `head` from `metadata.json`. Apply a nonempty
`staged.patch` with `git apply --index`, then a nonempty `unstaged.patch`
with `git apply`. Overlay `files/` into that new worktree, preserving modes
and symlinks. The metadata describes deleted paths and per-file hashes for
verification. Never restore archived intentional faults into `main`.

The SHA-256 of the completed `archives.json` manifest is:

`c2f5f7dd5f596f8c3bfa3b3854b906e077bef63a8ec8bf438c90f249c3caf20c`

## Checks and next step

Independent review (`notes/reviews/worktree-cleanup.md`, archived) verified all archive hashes,
contents, modes and patches, and inspected index flags and private HEAD
reflogs. Its sole history finding was fixed before removal. Fresh source,
index, HEAD and status checks gated each deletion. No active process cwd or
Docker bind mount referenced the targets; exact stale read-only VirtioFS
printer-golden handles were classified separately, without changing Docker.
All retained non-main HEADs and statuses match the initial inventory.

No project implementation changed, so Python/schema, Lean, oracle and
adversarial runtime gates were not rerun. `git diff --check` covers the
handoff edits. The five non-main trees were subsequently removed after
unique contents were preserved as documented above. The cleanup is complete;
there is no instruction to resume proof development or delete those drafts.
