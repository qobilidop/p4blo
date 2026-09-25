# Status

Where the work stands now. Updated at every checkpoint and compacted at
milestone boundaries, so this file holds current state only; history up
to the last compaction is in git at the archive commit
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`.

Last updated: 2026-09-24. **Active: the architecture-free IR semantics
plan**, [ir-semantics-plan.md](notes/ir-semantics-plan.md), adopted by the
user on 2026-09-24. Phase 0 is done and Phase 1 is in progress; the table
below says which item stands where. The two finite scopes below stay
complete and frozen.

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
| Phase 0: decisions recorded, `tests/oracle/spectec-rules.json` and `scripts/spectec-rules.py`, `tests/test_spectec_rules.py` | done, `eb0a440` |
| A3 the ledger: 56 entries, each citing P4, SpecTec, Lean, Python and tests, classes pinned in `tests/ledger-classes.json`; reviewed (`reviews/2026-09-24-ledger.md`), corrections merged | done, `6ac46b2` |
| B1 Lean rule tags: 157 tags, observer over the step machine, `coverage` in every reply, `tests/drt-unhit-tags.json` (34 unhit); reviewed (`reviews/2026-09-24-lean-coverage.md`) | merged, `0db270b`; the review's six defects are being fixed on `work/coverage-fixes` with witness pairs |
| A2 SpecTec rule coverage: OCaml probe, `tests/oracle/spectec-coverage.json`, hand-written exclusions, counts on the coverage page, oracle CI step; reviewed (`reviews/2026-09-24-spectec-coverage.md`): measurement sound, two exclusions wrong, generated inputs not yet measured, fixes routed to B2 | done, `94cd629` |
| A1 generated programs on SpecTec: six deterministic families, sixty seeds in CI, 1,100-seed local campaign with no unexplained disagreement; reviewed (`reviews/2026-09-24-generated-programs.md`): the table-mask classifier needs a control model, fix routed to B2 | done, `4a3504a` |
| Copy-back resolution at copy-in (both interpreters, proofs unchanged, 17 cases confirmed on SpecTec) and parser-only `lastIndex` in the validator | done, `2192fac` |
| Lean coverage review fixes: the six defects and the doubtful conditions, copy-back classified through the resolved lvalues, witness pairs for all 157 tags (135 requests, replies anchored to the reference interpreter), nine mutants caught, 33 tags still unhit | done, `495268d` |
| C4 deviation theorems: `P4bloIR.DeviationLaws`, 39 audited theorems over the production definitions for the ten run-time closed behaviors, a general longest-prefix and priority law over `Installed.lookup`, the revisit check of the parser loop bound; nine evaluator mutants each rejected at a named theorem; not proved: that a non-consuming loop always reaches the revisit check | merged, `bc4b8bc`; review pending |
| B2 coverage-guided generation (reviewed, `reviews/2026-09-24-guided-generation.md`, fixes merged: the table-mask explanation now requires a winner change computed without the matcher, the guidance claim is measured and recorded in `tests/drt-guided-measurement.json` with the pair-rewarding term removed, and the stack clamps are observable through `lastIndex` in the parser family): two menu-driven families aimed at the rule tags, a guided driver with JESTfs's one-feature-sensitive criterion, every one of the 157 Lean rule tags hit (the unhit list is empty), SpecTec in-scope rules unhit down to 2 with 18 generated seeds measured; the table-mask classifier gained a control model; the exclusion and probe corrections from both Phase 1 reviews; about 26,000 Lean requests and 3,000 SpecTec vectors with no disagreement | merged, `6a9e83d` |
| Theorem review follow-up (merged, `8c674fc`..): 63 audited theorems now; laws pin `prefixLength`, `keyValueMatches` and `Value.equalList` (the review's three surviving mutants now fail), `!=` negates `==`, the cursor never moves back and a revisit without consumption times out across a sub-parser boundary; every theorem instantiated in the test module | merged, gate pending |
| B3 exported conformance corpus: 89 fixtures, 523 recorded Lean answers under `tests/conformance/` (format 2, sparse cells, 1.1 MB), Python checked in two seconds, Lean by `refresh`, corruption, truncation, drift and stale-binary guards, four Python mutants and one Lean mutant recorded; reviewed (`reviews/2026-09-24-conformance.md`), fixes merged | done, `5ee25ce` |
| A4 single-block SpecTec runner: a `p4blo` architecture patch (1,296 lines) for the simulator, `tests/oracle/block.py`, block-by-block comparison of every corpus and example vector with extern state carried across; three strict expected failures behind checked models (CRC padding on the firewall's register cells, which the pipeline oracle could not see; the push/pop deviation on the stacks vector); reviewed (`reviews/2026-09-24-single-block.md`), fixes merged; the plugin validates incoming values and ties state to the program; `-trace` for the N+1 work | done, `687251e` |
| A5 the IL bridge: SpecTec `il-export` patch, `p4blo.frontend`, six corpus goldens byte-identical from source, 14 of 15 goldens round-trip through the printer, five new p4c programs and fourteen probe programs pass vectors of SpecTec's exact output from source; the census over the 191 pinned v1model programs is `tests/oracle/frontend_census.py` with its tracked result (98 pass, 74 excluded, 12 not translated); reviewed (`reviews/2026-09-24-il-bridge.md`), the four defects fixed, v1model's drop translated as v1model decides it; `tests/oracle/p4blo.watsup` is now a standalone file for the SpecTec-to-Lean project | done, merged |
| eDSL re-zeroes state and action locals at every entry, mirroring the bridge; no golden changed (subparser_stack's source now declares its parser-level local where the P4 does); Lean-agreeing tests for both cases | done, `b89ca45` |
| Const-entry priority ruling: the `priority` program is numbered by position as the specification does (the annotation is not read), its vectors follow SpecTec's outputs, p4c's inversion on BMv2 is a strict classified disagreement, the ledger and bridge follow, and the golden is now byte-identical from source (six goldens are) | done, `e1a783e` |
| Division of labor with `p4-spectec-lean` (the user's project, started 2026-09-25): A6 superseded, the oracle machinery frozen at maintenance, the bridge frozen at the corpus, `tests/oracle/p4blo.watsup` published as the block contract, the five consumed interfaces listed in the plan with their formats | recorded in the plan and the register |
| C1 whole-program validity and progress: `Validity/` (rules, checker, soundness, index laws), `Progress.lean` (no reachable interpreter error for a valid program; every finite run ends in success or a declared parser error; installation premise discharged), `p4blo-lean check`, 175 valid and 308 validator-test programs agreeing with Python with corresponding codes, four mutants each rejected; reviewed (`reviews/2026-09-24-validity.md`): no defects, the premises are real, two rules (`noAlias`, `writable`) are needed only for the Python correspondence and not for progress | merged, `40846a6`; follow-ups merged at `789ef4e`: the extern contract proved for the five reference families (`P4bloArch.Contract.bind_contract`, audited in `ArchProofAudit`), a kernel-checked non-vacuity instance on csum16 without `native_decide`, control and deparser runs proved to end in success (`KindLaws`), entry-point corollaries on the real entry functions (`EntryLaws`), the three validator tests now reaching their Lean rule |
| D, Lean layout: `P4bloIRTest`, `P4bloArchTest`, `P4bloTest` libraries hold tests and audits, one `p4blo` executable with sixteen subcommands, the three unregistered probes deleted with their useful lemmas already in the laws, roots pinned by `tests/test_package_layout.py` | merged, `4d660be` |
| D, Python consolidation: `p4blo.validator` is a package by category, `p4blo.validator.typer` is the one expression typer (the interpreter, the printer and the STF reader call it; a fourth copy in the STF reader went too), `p4blo.printer` is the P4 printer with the architectures binding it through five hooks; goldens byte for byte, diagnostics identical on every recorded program, a seam test of 95 programs | merged, `831cd20` |
| D, test directory regrouping and the ledger cross-reference table | building on `work/test-layout` |
| Compaction of `.agents/` at the end of this scope | next, after the regrouping merges |
| Phases 2 to 4 otherwise | see the plan |

The coverage page was renamed `docs/p4-spec-coverage.md` at `bc014a2`.

Semantic findings of this phase, all from reading SpecTec's rules and
running its simulator: both interpreters resolved `out`/`inout` targets
at copy-back rather than copy-in (fixed at `2192fac`, now class *same*);
the validator accepted `hs.lastIndex` in controls (fixed there); the
simulator joins the payload at the bit level where the IR pads the
deparser's bits to a byte (recorded); the `hs.last`
elaboration deviates on an empty stack (recorded); SpecTec's header
equality and `pop_front` contradict the P4 specification (recorded,
upstream-report candidates); the simulator refuses shift amounts above
2048 (recorded as an oracle limit).

## Open threads

- **State-local variables: decided.** The elaboration re-zeroes a local
  declared without an initializer at every entry of its state, action or
  inlined function (`decisions.md`, 2026-09-24). The bridge is being
  fixed on `work/bridge-fixes`; the eDSL's hoisting still needs the same
  zeroing and the ledger and coverage page entries need the ruling.
- **Unhit rule tags** (`tests/drt-unhit-tags.json`) and unhit SpecTec
  rules (`tests/oracle/spectec-coverage-exclusions.json`, category
  `unhit`) are the work lists for coverage-guided generation, plan item B2.
- **Printer declaration order.** The printer emits actions in IR order,
  and an action that calls one declared after it prints P4 that
  SpecTec's typing rejects (`CallableType_ok`). Either the printer
  orders actions by call dependency or the validator requires that
  order; the generated control family declares callees first meanwhile.
- **Two SpecTec rules in scope stay unhit** and are reachable:
  `Expr_eval/non-default-abort` needs a checksum or CRC call in a parser
  whose data holds a lookahead, and `Copy_in_arg/abort` needs a
  sub-parser with an `inout` header parameter called with a stack element
  indexed by a lookahead.
- **Ledger citations in code.** Tag docstrings and some module headers
  cite the semantics page by its old section names; the coverage-fix
  branch updates the tags, and workstream D does the rest.

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
- **The p4c backend is deferred behind verification**; it is the experiment
  that would test claim 1 and the elaborated-but-unexercised coverage rows
  (functions, newtypes, constructor parameters, named arguments), which are
  rulings, not performed rewrites.
- **BMv2 cannot see `flood`** until a corpus program declares it.

## Blocked

Nothing.
