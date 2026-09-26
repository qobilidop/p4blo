# Recovery and retired work

Durable recovery inventory, consolidated 2026-09-26. Retained to locate unique
retired drafts, historical evidence and local-only snapshots. Nothing here is
an instruction to resume research or remove backups.

## Committed history

Pre-reorganization archive: `de6aa7d9437ffc65c413b0adda7d3f8c558f84f6`.
It contains the previous status/decision registers, all four resolved reports
under historical `.agents/reviews/`, the original two recovery notes and the
public release transcript in `docs/assurance.md#release-evidence`.
Recover with `git show <commit>:<original-path>`; Git history, not a new archive
directory or tag, is the historical record. Original review paths are historical
identifiers, not current navigation.

Earlier compaction archives remain:

- `3c3ed799dc01c0113b8dbcb0f0862d4fb0f1b6dd`: completed test reorganization,
  plan, reviews, exact input/case audits, local/remote checks and mutation repairs.
- `d2f9dbd6fefacc80da40d4f6fba294c819cd4d28`
- `34ce204e4a8be7633133a715e10c9ac6a8b891b1`
- `9fc6c19febf839fa56873be10788b515c4e29ae9`
- `26c93485861bc5442076a1060fcc8d1743952702`
- `9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`: the first archive; notes then
  lived in `docs/notes/`, and the chronological register was `docs/decisions.md`.

Retired Lean authoring/application/architecture proofs and execution-certificate
sources remain at `5ee52d90f19d5d5a81bf972a115298ae167e691b`. XDP's compile-only
experiment is recoverable at `b7860a5`. Neither supplies a current guarantee.
[Validation evidence](validation-evidence.md) identifies completed scopes and
finite experiments without requiring their logs for ordinary resumption.

## Unique parked branches

Core-only assurance retired these extensions on 2026-09-25. Drafts from
2026-09-23 were converted to pushed branches on 2026-09-24; all three remain on
origin. They predate the then-new `spec/ir`, `spec/arch`, `impl/lean` layout and
generic extern state. They need rebasing and extern construction changes toward
`P4bloArch` before building, and are not evidence for landed claims.

| Branch | Tip | What it holds | Missing or unreliable |
|---|---|---|---|
| `work/firewall-readback` | `75fdcf6` | actual two-read Bloom prefix in Lean: copyback, exact remaining queue and unrelated-state preservation; standalone compilation and clean theorem queries; Python draft | package/audit registration, review and fault campaign; Python test never ran and has wrong protobuf accessors. Plan: historical `docs/notes/firewall-readback-next.md` at `9e8f7d47`; review on `work/parked-reviews` |
| `work/forwarder-ingress` | `231e981` | actual table apply composed with first ingress guard; owner-reported Lean checks; Python/export drafts; historical `docs/notes/forwarder-ingress.md` plan | Python gates never ran; Pyright reports a wrong test field; review and checksum step missing; not a complete forwarding proof |
| `work/parked-reviews` | `d18436b` | reviews of those drafts and eight variant review versions whose final forms are archived | reference only; not implementation evidence |

Another 74 review files matched archived notes and were not duplicated.
`work/firewall-adversarial` and `work/program-codec-next` contained only material
byte-identical to integrated main and were deleted on 2026-09-24.

## Local-only recovery snapshots

The 2026-09-24 cleanup began at `e0b59b4`: 92 worktrees, about 88.10 GiB summed
`du -sk` allocation. It removed 86 checkouts (50 clean merged, 36 review/fault
campaign trees with changes), about 82.47 GiB summed allocation. APFS/shared
caches mean these are not physical freed-space claims. Initially six remained;
the five non-main trees were then converted to branches and removed. Only the
main checkout was retained; temporary worktrees for new tasks are separate.
No refs were deleted in the initial removal; the two redundant branch deletions
above occurred afterwards.

One unique commit found only in a removed worktree's private HEAD reflog,
`21378e4e9d620a7e3c7ef1400890025c1bf29b99`, survives at local ref
`refs/archive/worktree-cleanup-2026-09-24/lvalue-codec`. It is not published to
GitHub. The snapshots are also local, under
`/Users/qobilidop/my/work/p4blo/.artifacts/worktree-cleanup/2026-09-23/`;
that directory date is the initial inventory date, before completion crossed midnight.

- `inventory.json`: original paths, HEADs, branches, statuses and sizes.
- `archives.json`: archive paths, original HEADs and individual SHA-256s.
- `archives/<worktree-name>.tar.gz`: 86 verified archives, 283,873,510 bytes
  (270.72 MiB), preserving 971 file/symlink entries.
- `removed.json`: the 86 exact removed paths, each checked absent and recounted.
- `cleanup.py`: the one-off preflight/removal procedure.

Manifest SHA-256:
`c2f5f7dd5f596f8c3bfa3b3854b906e077bef63a8ec8bf438c90f249c3caf20c`.
Each archive contains `metadata.json`, `staged.patch`, `unstaged.patch` and
`files/`: tracked edits, untracked files and non-cache ignored experiment data,
including release evidence. Rebuildable Lean/Python/Hypothesis/pytest/Ruff caches
were excluded. Git retains the committed sources. These local snapshots matter
for retired draft recovery, not for reproducing the current project guarantees.

Verify the archive against the manifest, unpack into an empty recovery location,
and create a detached worktree at metadata's full HEAD. Apply a nonempty staged
patch with `git apply --index`, then a nonempty unstaged patch with `git apply`.
Overlay `files/`, preserving modes/symlinks; check metadata's deleted paths and
per-file hashes. Never restore deliberate faults into main.

Historical independent review (original `notes/reviews/worktree-cleanup.md`,
archived) checked hashes, contents, modes, patches, index flags and private
reflogs. Its sole history finding was fixed before deletion. Preflight confirmed
no live cwd or Docker mount used the targets; stale read-only printer VirtioFS
handles were classified separately, without changing Docker. No implementation
changed, so that cleanup ran whitespace checks, not runtime/Lean/oracle gates.
