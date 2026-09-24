# Status

Where the work stands now. Updated at every checkpoint and compacted at
milestone boundaries, so this file holds current state only; history up
to the last compaction is in git at tag `agents-archive/2026-09-24`.

Last updated: 2026-09-24. Nothing is active. Both finite scopes below are
complete, and no next implementation step is authorized by them.

## Current state

| Scope | Result | Revision | Evidence |
|---|---|---|---|
| Assurance milestone 1 | complete 2026-09-23 | `3148a52` (code gate) | [release evidence](../docs/assurance.md#release-evidence) |
| Python application collection: router, firewall, load balancer | complete 2026-09-24 | `c94336d` | [examples](../examples/README.md); checks below |
| Project website with the VLAN gateway walkthrough | published | `38d740e` | <https://qobilidop.github.io/p4blo/> |

The four claims of [design.md](../docs/design.md):

| Claim | Status |
|---|---|
| 1. The core is small and post-elaboration | green: twelve corpus programs and three applications fit without a new core construct; coverage table published |
| 2. Supports the tested real programs | green with explicit exceptions: every corpus and example vector passes both P4 oracles except one strict BMv2 register divergence; separate original-source CRC/mask probes expose four exact pinned SpecTec discrepancies, all classified |
| 3. A block is a function; an architecture is ordinary code | green: filter 45 lines, switch 50, no P4 in either; every program runs under both |
| 4. Mechanized and agrees with the reference | green within the stated profile: proof-visible Lean interpreter, audited scoped proofs, corpus and generated-program differential tests with extern-state comparison; no universal Python equivalence claim |

## Last checked evidence

At implementation revision `c94336d`, sequentially in the pinned
environment, each exiting 0:

- `scripts/check-lean.sh`: the Lean packages, proof audits, native/API checks.
- `P4BLO_REQUIRE_LEAN=1 scripts/check.sh`: 4837 passed, one skipped (the
  optional local XDP image), five xfailed (the classified oracle
  discrepancies); Ruff, Pyright, schema drift and actionlint pass.
- Standalone uv-managed Python with no development tools on PATH: all
  three demos and 17 example tests pass.
- Ten application source faults are each rejected by both interpreters'
  independent expected-answer tests; baselines and restorations pass.

All five required workflows and the website workflow passed at that
revision: [CI](https://github.com/qobilidop/p4blo/actions/runs/36036851165),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36036851322),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36036851210),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/36036851183),
[XDP](https://github.com/qobilidop/p4blo/actions/runs/36036851205),
[website](https://github.com/qobilidop/p4blo/actions/runs/36036851222).
Local logs and mutation artifacts under `.artifacts/` are untracked and
not evidence anyone else can check.

The 2026-09-24 documentation reorganization (this directory, the
compaction and the promoted contracts under `docs/`) changed no runtime
source beyond path strings in comments. `scripts/check.sh` passes at
`2a5638d` with 4839 passed, the same one skip and five xfails, plus the
new link test; the later review-fix commits touch Markdown only. The Lean
gate was not rerun: its only change is a doc comment in `Switch.lean`.

**IR and architecture separation (2026-09-24).** The repository is now
`spec/ir/` (the IR specification, nothing architectural), `spec/arch/`
(the reference architecture: switch, extern families, certificate
example, the `p4blo-lean` endpoint), `impl/lean/` and `impl/python/`
(with `p4blo.arch` holding the extern families and the v1model printer);
`docs/ir-semantics.md` describes the IR alone and `docs/arch-supports.md`
what the supplied architectures decide. The IR carries extern state as
data and takes the model from the architecture at load. No golden, wire
byte or protocol message changed. At `d2c9400`: `scripts/check-lean.sh`
passes all three packages with their audits and tests;
`scripts/check.sh` passes with 4843 tests, the same one skip and five
xfails; `scripts/check-assurance.py` passes all 28 phases with the split
scratch builds. The independent review is
`reviews/spec-split-2026-09-24.md`; its two runner findings are fixed.
The two parked draft worktrees predate the layout and need rebasing
before use, as `notes/parked-proofs.md` now says.

A second pass the same day reduced `docs/` to six reference files
(design, semantics, coverage, assurance, quickstart, workflows), folding
the firewall notes into the corpus README and archiving the rest in git.
`scripts/check.sh` passes at `093dc26` with the same counts; the two
review-fix commits after it touch Markdown and a ruff exclusion only,
rechecked with the link test and `ruff format --check`. The independent
review is `reviews/docs-consolidation-2026-09-24.md`.

## Open threads

These are parked or backlog, not tasks. Resuming any of them needs a new
scope from the user.

- **Parked proof drafts** for firewall readback and guarded forwarding
  ingress live in local worktrees, not on `main`; their exact state is in
  [parked-proofs.md](notes/parked-proofs.md). Five non-main worktrees
  remain intentionally; see [worktree-cleanup.md](notes/worktree-cleanup.md)
  before treating any of them or the local archives as disposable.
- **Research backlog** beyond the completed milestone is the
  [roadmap](roadmap.md): Lean surface and validator extensions,
  whole-program codecs, xdp-filter, flowlet switching, bounded Katran.
- **Verification open items:** whole-program validity, soundness and
  termination; general assignment preservation; further extern contracts;
  application properties beyond the proved initialization, Bloom insertion
  and forwarding laws.
- **Interchange open items:** text parsing, semantic-version policy,
  whole-program codec proofs, resource limits, unknown-field policy.
- **XDP:** an FD-only strict adapter and capability-scoped execution
  preflight; flowlet time/randomness and the Katran profile still need an
  audit. Nothing about the kernel is established.
- **Unconfirmed review points** never judged by an oracle: checksum16
  padding for data widths not a multiple of 16; sub-block instance names
  `<block>_inst` are not checked against the caller's scope; a case with
  both a bad entry and a bad port reports different first errors on Python
  and Lean.
- **Three type checkers** compute expression types (the validator,
  `interp/widths.py`, the printer's `_Typer`); they must agree and one
  would do. The typed eDSL is a fourth at a different level.
- **The p4c backend is deferred behind verification**; it is the experiment
  that would test claim 1 and the elaborated-but-unexercised coverage rows
  (functions, newtypes, constructor parameters, named arguments), which are
  rulings, not performed rewrites.
- **BMv2 cannot see `flood`** until a corpus program declares it.

## Blocked

Nothing.
