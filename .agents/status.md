# Status

Where the work stands now. Updated at every checkpoint and compacted at
milestone boundaries, so this file holds current state only; history up
to the last compaction is in git at tag `agents-archive/2026-09-24`.

Last updated: 2026-09-24. **Active: the architecture-free IR semantics
plan**, [ir-semantics-plan.md](notes/ir-semantics-plan.md), adopted by the
user on 2026-09-24. Phase 0 (decisions, the SpecTec rule inventory
fixture, the ledger citation test) is done; Phase 1 is next. The two
finite scopes below stay complete and frozen.

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

**Repository reorganization (2026-09-24), revision `2c7632e`.** The
same day, in order: agent state moved under `.agents/` with a first
compaction; `docs/` was reduced to seven reference pages; the tree was
split into `spec/ir/` (the IR specification, nothing architectural),
`spec/arch/` (the reference architecture: switch, extern families,
certificate example, the `p4blo-lean` endpoint), `impl/lean/` and
`impl/python/`; the IR now carries extern state as data and takes the
model from the architecture at load; and the parked drafts moved from
worktrees to pushed `work/*` branches, with every merged or duplicate
branch deleted. No golden, wire byte or protocol message changed. At
`d2c9400`, `scripts/check-lean.sh` passes all three packages with their
audits and tests, `scripts/check.sh` passes with 4843 tests and the same
one skip and five xfails, and `scripts/check-assurance.py` passes all 28
phases with the split scratch builds. The three independent reviews are
under `reviews/`; every finding is fixed.

## Active plan progress

| Item | State |
|---|---|
| Phase 0: decisions recorded, `tests/oracle/spectec-rules.json` and `scripts/spectec-rules.py`, `tests/test_spectec_rules.py` | done |
| Phase 1: A1 generated programs on SpecTec, A2 SpecTec rule coverage, A3 the ledger, B1 Lean rule tags, C4 deviation theorems | next |
| Phases 2 to 4 | see the plan |

## Open threads

These are parked or backlog, not tasks. Resuming any of them needs a new
scope from the user.

- **Parked proof drafts** for firewall readback and guarded forwarding
  ingress are on pushed `work/*` branches, not on `main`; their exact
  state and gaps are in [parked-proofs.md](notes/parked-proofs.md). No
  non-main worktree remains; the local recovery archives of the earlier
  cleanup are described in [worktree-cleanup.md](notes/worktree-cleanup.md).
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
