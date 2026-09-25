# Status

Current truth and resumable work. Earlier history is archived at
`26c93485861bc5442076a1060fcc8d1743952702` (2026-09-25), and previously at
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6` (2026-09-24).

Last updated: 2026-09-25. **Active: example-guided Python eDSL ergonomics.**
Branch `work/edsl-ergonomics`, original base `80eba84`; [PR #2](https://github.com/qobilidop/p4blo/pull/2)
is open. Pushed head `03c35e7` failed only CI's P4-SpecTec job: `ea1ef89`
put p4blo imports at module level in `tests/oracle/coverage.py`, whose
`build` step CI runs with a bare `python3`. Fixed at `a6fb0ef` and pinned
by a structural test of the bare-interpreter scripts (`b43147d` adds the
XDP check found by [review](reviews/edsl-final-fixes.md)). The uncommitted
closure-audit prose sweep from the interrupted Codex session was committed
as `07409ad` and `7082a48`, with `c1bcc39` from review. Before pushing:
`P4BLO_REQUIRE_LEAN=1 scripts/check.sh` exited 0 (5198 passed, the optional
XDP image skipped, 4 xfailed), and the CI coverage steps ran locally, each
exiting 0: `nix develop .#oracle -c python3 tests/oracle/coverage.py build`,
then `test_spectec_coverage.py` with `P4BLO_REQUIRE_SPECTEC_COVERAGE=1`,
9 passed, the committed report matching a fresh measurement.
The user extended the separation through the protobuf and Lean types;
[wire-boundary plan](notes/edsl-wire-boundary.md) records the accepted design.

Implementation is complete at `37356009137d7f1bad5a284c01d59eace1841726`:

- Typed Python BlockLibrary compiles directly to core protobuf BlockLibrary;
  Lean uses the same abstraction. It holds arbitrary blocks and declarations,
  with no global H/M roots, exports or fixed count of any block kind.
- Architecture BlockBindings owns roots and exports. An optional flat
  BlockAssembly transport preserves existing payloads; architecture code
  supplies invocation policy, host contracts and explicit extern binding.
- Core validity/progress remains proved over libraries. Binding validity and
  its sound checker, fixed H/M entry helpers and existing entry theorems now
  live in architecture support. Wrong signatures and role kinds fail at load.
- The three applications retain exact text/binary goldens and behavior;
  ordinary aliases/helpers improve readability. A custom extern and a library
  with two blocks of each kind exercise composition beyond the supplied switch.

Checked local evidence on that implementation tree, all exiting 0:

- All three packages through `scripts/check-lean.sh`, including proof audits.
- `P4BLO_REQUIRE_LEAN=1 scripts/check.sh`: 5195 passed, one optional local XDP
  image skip, four expected failures; lint/types/schema/generation pass.
- `python -m p4blo.conformance check-lean`: all 89 retained fixtures reproduce
  unchanged answers; the original fixture provenance is retained and the new
  semantics-source digest is reported explicitly, not treated as answer drift.
- On equivalent oracle-adapter commit `f6ec9ef`: P4-SpecTec block suite
  67 passed/3 expected failures; frontend suite 98 passed; main corpus 35 passed.
- At frozen `70b51cdd28b331832fc9a6182b60218e68be38a6`, main P4-SpecTec/BMv2
  corpus suites passed 79 tests with two documented expected failures.
- At that same frozen revision, `scripts/check-assurance.py` exited 0:
  Python fault catalogue, Lean CRC fault, paired codec/observer faults,
  independent anchors and restored baselines all checked.

Independent review approved exact implementation `70b51cd` with no confirmed
defects and 43 final focused passes; see
[boundary review](reviews/library-boundary.md). It checked preserved theorem
premises, scalar/six-block core acceptance, projection isolation and nine
malformed bindings against Python and Lean. The earlier typed-compiler review
found the local-only declaration-closure bug, fixed at `c150d31`; its report
is [here](reviews/edsl-implementation.md). Independent review also approved
metadata head `33215d2`; its full local gate exited 0 with the same counts.
Library source settings remain reassignable; bypassing constructor checks by
assignment is a nonblocking consistency observation, not a shown runtime bug.

Next: push, update PR #2, pass all remote CI on its exact head and merge. Then
close the scope, finalize the [reflection](notes/edsl-reflection.md), compact
state and remove integrated worktrees/branches. Do not resume roadmap work.
The prior successful assurance at `58275b8` covered the pre-extension API;
it is not evidence for this final split. Its first attempt was invalidated
by concurrent tracked documentation edits and never counted as a pass.

Engineering-practice maintenance is merged on `main` at `264fd63` through
[PR #1](https://github.com/qobilidop/p4blo/pull/1), from base `045f3de`.
Three semantic scopes remain complete and frozen.
The user authorized learning from local `p4-spectec-lean` and external
engineering guidance, then improving this repository; P4-SpecTec
integration and coverage changes are not part of it.

## Engineering checkpoint

- Adopted PR-default integration, final-revision review/CI, durable PR
  descriptions and verified AI attribution from `p4-spectec-lean`.
- Added a 5 MiB index/working-tree artifact guard and closed a confirmed
  protobuf drift-check gap: `git diff` after in-place generation misses
  new untracked outputs. Sources and boundaries are in
  [engineering-practices.md](notes/engineering-practices.md).
- Artifact guards committed as `cd04ba2`. An isolated implementation agent
  supplied the generation checker and tests; independent review found one
  conflict in the compaction skill's direct-to-main workflow, corrected
  and re-reviewed. The skill also no longer treats every same-day archive
  as an unfinished compaction. See the
  [review report](reviews/engineering-practices.md).
- Local full `scripts/check.sh`: 5,157 passed, 1 skipped (optional XDP
  image unavailable), 4 expected failures; formatting, lint, types, schema,
  real pinned Buf generation and workflow lint passed. The 18 guard tests
  pass, including deliberately invalid candidates; targeted Pyright on
  both scripts and their tests reports no errors or warnings.
- Independent review cleared final PR revision `77f7a24`; all seven remote
  jobs passed before merge: [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36186415433),
  [Lean and assurance](https://github.com/qobilidop/p4blo/actions/runs/36186415310),
  [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36186415484),
  [BMv2](https://github.com/qobilidop/p4blo/actions/runs/36186415285) and
  [required XDP](https://github.com/qobilidop/p4blo/actions/runs/36186415307).
  Merge `264fd63` has the same tree. Lean, assurance and external oracle
  specialist gates were not rerun locally; prior semantic evidence below
  is retained unchanged. Post-merge main CI is a separate run, not the
  evidence cited here.
- Rewrote the PR after comparing the user's preferred p4-spectec-lean
  examples: a specific title, problem/approach/validation/review focus,
  explicit tradeoffs and one attribution sentence, without appended
  progress updates.
- Temporary implementation/review worktrees and completed branches were
  removed after verifying their content was integrated. No neighboring
  repository was modified. This scope is closed; the newly authorized eDSL
  scope above is active. The roadmap remains backlog.

## Current state

| Scope | Result | Revision | Evidence |
|---|---|---|---|
| Assurance milestone 1 | complete 2026-09-23 | `3148a52` | [release evidence](../docs/assurance.md#release-evidence) |
| Python application collection: router, firewall, load balancer | complete 2026-09-24 | `c94336d` | [examples](../examples/README.md) |
| Project website with the VLAN gateway walkthrough | published | `38d740e` | <https://qobilidop.github.io/p4blo/> |
| The architecture-free IR semantics scope (2026-09-24 to 2026-09-25) | complete | `26c9348` | [assurance.md](../docs/assurance.md), [ir-semantics.md](../docs/ir-semantics.md), [ledger-xref.md](../docs/ledger-xref.md), [p4-spec-coverage.md](../docs/p4-spec-coverage.md) |

The four claims of [design.md](../docs/design.md):

| Claim | Status |
|---|---|
| 1. The core is small and post-elaboration | green: twelve corpus programs and three applications fit without a new core construct; P4 source now enters through P4-SpecTec's typing and instantiation (`p4blo.frontend`), six corpus goldens reproduce byte for byte from their P4 originals, and 98 of the 191 pinned v1model programs with vectors run from source (`tests/oracle/frontend-census.json`) |
| 2. Supports the tested real programs | green with explicit exceptions: every corpus and example vector passes both P4 oracles at the pipeline level except the strict BMv2 register and priority divergences and SpecTec's strict mask failure on the printed tutorial firewall, and block by block on SpecTec except three strict expected failures behind checked models; the original-source probes expose the pinned SpecTec CRC and mask defects, all classified; generated programs on SpecTec pass with two classified simulator defects |
| 3. A block is a function; an architecture is ordinary code | green, frozen: filter 45 lines, switch 50, no P4 in either; every program runs under both |
| 4. Mechanized and agrees with the reference | green within the stated profile: core library validity decided by a checker proved sound and architecture bindings checked separately with a sound checker; progress (no reachable interpreter error for a valid library under the stated execution premises) with the extern contract discharged for the reference families, 63 deviation and helper laws, every one of the 157 rule tags of the Lean machine hit by retained differential campaigns, a conformance corpus of 89 fixtures; no universal Python equivalence claim, no termination theorem |

## What the IR semantics scope established

Each of the ten semantic items was built by a sub-agent in its own
worktree, reviewed independently, and its review's defects fixed on
`main`; the reviews are archived at the archive commit under
`.agents/reviews/`. The reorganization, the priority ruling, the eDSL
re-zeroing and the gate speed-ups were integrated without a separate
review.

- **The deviation ledger** (`docs/ir-semantics.md`): 56 closed behaviors,
  each citing the P4 section, the SpecTec rule at the pin, the Lean
  definitions and theorems, the Python function and the tests, classed
  same, refines undefined, deviates or not representable; classes pinned
  in `tests/ledger-classes.json`; `docs/ledger-xref.md` generated and
  checked for drift.
- **Rule coverage on both sides**: `P4bloIR.Coverage` names 157 rules,
  an observer over the proof-visible machine reports them in every
  reply, witness pairs pin each rule's condition from both sides, and
  the retained campaigns hit all 157 (`tests/drt-coverage-parts/`,
  `tests/drt-unhit-tags.json` empty); SpecTec's own rules measured by an
  OCaml probe over the corpus and 18 generated seeds, two in-scope rules
  unhit and both confirmed reachable
  (`tests/oracle/spectec-coverage-exclusions.json`).
- **Generation**: two menu-driven families aimed at the rules and a
  guided driver whose benefit over uniform choice is measured
  (`tests/drt-guided-measurement.json`); about 26,000 requests on Lean
  and 3,000 vectors on SpecTec with no unexplained disagreement.
- **SpecTec at the block level**: a `p4blo` architecture patch runs one
  block on the architecture-free rules; three strict expected failures
  behind checked models (the CRC padding defect on the firewall's
  register cells, invisible through the pipeline; the push/pop
  deviation).
- **The conformance corpus**: 89 fixtures, 523 recorded Lean answers,
  Python checked in seconds, Lean by `refresh` with digest and binary
  guards.
- **The IL bridge**: `p4blo.frontend` translates SpecTec's instantiated
  IL construct by construct as the coverage page prescribes.
- **Proofs**: `Validity/` (rules, `Validity.check`, `check_sound`),
  `Progress.lean` with `ExternContract` proved for the reference
  families and a kernel-checked non-vacuity instance on csum16,
  `KindLaws` and `EntryLaws`, `DeviationLaws` (63 theorems); every
  advertised theorem audited on the three standard axioms.
- **Organization**: Lean roots follow the `<Root>Test` convention with
  one `p4blo` executable; `p4blo.validator` is a package, one expression
  typer, the printer apart from the v1model shim; tests grouped by the
  question they answer under `tests/`; the gate script runs in under a
  minute.

Semantic findings of the scope, all from reading SpecTec's rules and
running its simulator: both interpreters resolved `out`/`inout` targets
at copy-back rather than copy-in (fixed, class same); the validator
accepted `hs.lastIndex` in controls (fixed); const-entry priorities
followed p4c's inverted numbering (re-derived as the specification
numbers them; BMv2 classified); hoisted state and action locals kept
their values across entries (re-zeroed by the eDSL and the bridge); the
`hs.last` elaboration deviates on an empty stack (recorded); SpecTec's
header equality and `pop_front` contradict the P4 specification
(recorded, upstream-report candidates); the simulator refuses shift
amounts above 2048 and joins the payload at the bit level (recorded as
oracle differences).

## Last checked evidence

At `26c9348`, in the pinned environment, each exiting 0:

- `scripts/check-lean.sh`: the three packages with `--wfail`, every
  audit and test library.
- `P4BLO_REQUIRE_LEAN=1 scripts/check.sh`: 5139 passed, one skipped
  (the optional local XDP image), four xfailed, in 43 s of tests and 50 s
  in all; the oracle suites are deselected locally.
- `scripts/check-assurance.py` at `dd491cf`, the `--wfail` change being
  the last to touch its inputs.
- The oracle suites on the shared simulator with both patches, on the
  compaction tree (the tests of `26c9348` unchanged): 360 passed and
  6 xfailed (`-m oracle -k "not bmv2"`); BMv2 161 passed and 2 xfailed
  at `35f16b6`.

All six workflows passed at `26c9348`:
[CI](https://github.com/qobilidop/p4blo/actions/runs/36110812077),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36110812032),
[Oracle](https://github.com/qobilidop/p4blo/actions/runs/36110811991),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/36110812029),
[XDP](https://github.com/qobilidop/p4blo/actions/runs/36110812036),
[website](https://github.com/qobilidop/p4blo/actions/runs/36110812061). Local logs and artifacts under `.artifacts/`
are untracked and not evidence anyone else can check.

## Open threads

These are parked or backlog, not tasks; resuming any needs a scope.

- **The joint milestone with `p4-spectec-lean`** (`docs/design.md`,
  "Relation to p4-spectec-lean"): when its executable rendering exists,
  it answers every conformance fixture and block request as the OCaml
  simulator does; then the simulation theorem. Two alignments wait on
  that project: its P4-SpecTec pin (`8c8e0c6f`, on the Nano-P4 branch)
  differs from ours (`2730cfd9`), and its program export replaces patch
  `0002` when it exists.
- **Termination (C2)** under the acyclic-calls and revisit discipline,
  and **codec composition through BlockLibrary and architecture Export and
  BlockAssembly (C3)**, are the two
  proof items the scope left as backlog (`roadmap.md`).
- **Printer declaration order.** An action that calls one declared after
  it prints P4 that SpecTec's typing rejects; either the printer orders
  actions by call dependency or the validator requires that order.
- **Two SpecTec rules in scope stay unhit** and are reachable:
  `Expr_eval/non-default-abort` and `Copy_in_arg/abort`; the exclusions
  file says which input reaches each.
- **Module headers** in a few Lean and Python files still cite the
  semantics page by its former section names rather than entry names.
- **Parked proof drafts** for firewall readback and guarded forwarding
  ingress are on pushed `work/*` branches; their state and gaps are in
  [parked-proofs.md](notes/parked-proofs.md), the local recovery archives
  of the 2026-09-24 cleanup in [worktree-cleanup.md](notes/worktree-cleanup.md).
- **Unconfirmed review points** never judged by an oracle: checksum16
  padding for data widths not a multiple of 16; sub-block instance names
  `<block>_inst` are not checked against the caller's scope; a case with
  both a bad entry and a bad port reports different first errors on Python
  and Lean.
- **Verification open items** beyond the roadmap's proof entries:
  general assignment preservation; further extern contracts; application
  properties beyond the proved initialization, Bloom insertion and
  forwarding laws; generated table-invoked actions and parser-error
  copyback across sequences.
- **Interchange open items:** text parsing, semantic-version policy,
  whole-program codec proofs, resource limits, unknown-field policy.
- **XDP** stays a compile-only profile: an FD-only strict adapter and a
  capability-scoped execution preflight; the flowlet time/randomness
  and the Katran profile still need an audit; nothing about the kernel
  is established. **BMv2 cannot see `flood`** until a corpus program
  declares it. **The p4c backend** is deferred behind verification; it
  is the experiment that would test claim 1 and the elaborated rows the
  bridge does not yet perform.

## Blocked

Nothing.
