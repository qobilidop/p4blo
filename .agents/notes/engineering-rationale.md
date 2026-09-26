# Engineering rationale

[AGENTS](../../AGENTS.md) owns policy, [workflows](../../docs/workflows.md)
commands/pins, [design](../../docs/design.md) package layout and
[tests](../../tests/README.md) test ownership. These are original reasons and
revisit points, retained as durable rationale and consolidated on 2026-09-26, not duplicate specifications.

## Environment and layout

- **Ordinary commands, optional Nix** (2026-09-24): uv/Python setup stays in
  README; the flake pins tools for Nix/direnv/CI. Elan avoids nixpkgs' Lean lag;
  oracle-only OCaml stays in devShells.oracle. Historical transcripts stay as
  written. No devcontainer: uv serves non-Nix users and a non-flake container
  would drift; revisit for Windows without WSL2. Pure Python/3.13 was free to
  impose early and costly to reopen (both 2026-09-22).
- **Native p4c/BMv2 images** (2026-09-22): qobilidop/p4lang-builds supplies
  amd64/arm64 because official p4c crashed under ARM emulation. Immutable
  versions/index digests live in the workflow pins. Optional local Docker
  typechecking avoids disproportionate p4c builds. Pin every external input
  for reproducibility; workflows owns image/Actions/opam/source identities.
- **Lean layout** (2026-09-24; schema exception 2026-09-25): Mathlib/Batteries
  import/test separation and singular RootTest avoid global Tests collisions;
  keep acronyms capitalized. The layout guard prevents unregistered probes/
  executable-root sprawl. Retiring
  Lean authoring focuses resources on core IR (2026-09-25).
- **Python concerns** (2026-09-25): one validator groups rules; validator.typer
  serves interpreter/printer/STF because a top-level typer would cycle through
  diagnostic codes. The architecture-free printer has five binding hooks;
  frontend bridges P4-SpecTec IL.
- **Public examples versus verification:** discoverable source stays separate
  from test machinery (assets 2026-09-23; examples 2026-09-24). Explicit-marker
  test reorganization preserves all cases/independent answers and excluded spec/
  (2026-09-25; stale layout wording removed 2026-09-26).
- **Generated deliverables:** committed bindings support regeneration checks
  (2026-09-22; architecture path 2026-09-25). In-place regeneration misses new,
  untracked and stale outputs, hence clean inventory/byte comparison against
  index and worktree, one local/CI checker and negative tests. The 5 MiB budget
  follows p4-spectec-lean as prevention, not a hosting limit; staging, lossless
  snapshots/raw checksums and no unauthorized history rewrites follow AGENTS
  (2026-09-25).
- **Website** (2026-09-24): static/dependency-free Pages, generated walkthrough
  from the tested VLAN gateway; the source remains the checked owner.

## CI choices and revisit points

Fresh Lean builds after moves avoid shadowing stale modules; build before tests
consume the binary (2026-09-23). Main's lib/ir cache, excluding bin, avoids cold
builds while Lake rejects deleted source imports. Revisit if gates query outside
lake build/test (2026-09-25). Two hash shards with load scheduling preserve every
selected case once; both build/audit and only shard 1 saves main's cache. Grouping
would serialize unrelated tests. Confidence high for coverage, no timing guarantee;
revisit shard count if runner overhead dominates (2026-09-25).

User-delegated narrative-only specialist skipping avoids repeated expensive gates
without reducing executable-change cases. Python/schema always run; workflows
owns the narrow allowlist, parsed-doc exclusions, uncertain-input/mode/history/
classifier-failure fallback, whole-PR comparison and cancellation policy (cancel
superseded PR runs, never main). Revisit the allowlist when a heavy gate gains a
documentation input (2026-09-25).

## Integration lessons

Independent review identifies the actual integrated revision, reproducers and
limits; fix findings before integration (2026-09-25). Reviews now live with their
topics (approved 2026-09-26). PR rationale/disclosure follows Git/Google/GitHub and
p4-spectec-lean without boilerplate; verified agent/model attribution is distinct
from human review (2026-09-25). Sources and adoption limits are archived as
`.agents/notes/engineering-practices.md` at
`9fc6c19febf839fa56873be10788b515c4e29ae9`; AGENTS owns the current requirements.

A successful tail once hid a failed gate; structural smoke missed codec paths.
Recorded exits, scoped builder checks and a full integration-batch gate avoid
both lost coverage and duplicated work (2026-09-24, 2026-09-25). Keep at most two
heavy local jobs. Owned/verified Docker containers and own-artifact-only cleanup
prevent disk pressure becoming global pruning permission (2026-09-23).

Fragile untracked drafts and falsely unique branches motivated pushed WIP,
main-content comparison, deletion of merged/identical branches and archival before
worktree removal (2026-09-24). Record uncertainty's confidence/revisit trigger
(2026-09-23). The public-doc link boundary, archive-first claim-preserving reviewed
compaction, no tags, and one skills location via Claude's symlink avoid competing
instructions and stale diaries while git retains every byte (2026-09-24).
