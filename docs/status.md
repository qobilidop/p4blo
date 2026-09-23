# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order), and what is open. Updated at every
checkpoint. To resume the work, read this, then
[decisions.md](decisions.md), then [workflows.md](workflows.md).

Last updated: 2026-09-23, starting the accepted Python/Lean architecture
implementation following the verification work. The original prototype's
steps are complete. The stronger assurance work is in progress; its
acceptance criteria and trust boundaries are in [verification.md](verification.md).

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | schema and contract fit in a few pages; no corpus escape hatch | green: ten corpus programs fit with named elaborations only; coverage table published |
| 2. Semantically complete for real programs | four corpus programs match the oracle packet for packet | green: every corpus vector passes on P4-SpecTec and on BMv2 (15 files, 10 programs), with one recorded divergence on an out-of-range register read |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT and named checked properties | green: 287 Lean checks; corpus plus typed generated-program DRT with extern-state comparison; packing, closed scalar soundness/value laws, finite-trace execution and bounded-checker soundness proofs; no universal Python equivalence claim |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | done: the forwarder's five vectors pass end to end |
| 2 | Extern registry, stateful program | done: registry with register, counter and checksum16; the stateful program and the forwarder's checksum |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | done: ten programs in the typed eDSL, both architectures, contract check |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | done: every program passes on both oracles, each with its own CI job |
| 5 | Lean interpreter, extern models, DRT, the theorem | done |
| 6 | Coverage table, README claim matrix, write-up | done: coverage table (177 rows, none undecided), README, `docs/writeup.md`; both reviews kept under docs/notes/reviews and their findings fixed |

## Corpus

| Program | Source | Rewritten | Vectors | Oracle |
|---|---|---|---|---|
| forwarder | p4lang tutorial basic | eDSL source rebuilds the golden; checksum16 computes hdrChecksum, verify deferred | 5 hand-derived STF files with correct IPv4 checksums, passing | 5/5 pass on both oracles, checksum included |
| acl | p4c `ternary2-bmv2` | eDSL, landed | p4c STF, 6 adds, 4 packets, passing | 4/4 pass on both oracles |
| stacks | p4c `header-stack-ops-bmv2` | eDSL, landed | p4c STF, 15 packets, all passing | 15/15 pass on both oracles |
| subparser_stack | p4c `subparser-with-header-stack-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | passes on both oracles |
| stateful | p4c `issue1097-2-bmv2` + own vectors | eDSL, landed; register and counter bound | p4c STF, 2 packets, plus 6 of ours across packets, passing | 8/8 pass on both oracles |
| csum16 | p4c `issue655-bmv2` | eDSL, landed; checksum16 bound | p4c STF, 6 packets, passing | 6/6 pass on both oracles |
| parser_error | p4c `parser_error-bmv2` | eDSL, landed | p4c STF, 2 packets, passing | pass on both oracles |
| verify_error | p4c `issue1824-bmv2` | eDSL, landed | p4c STF, 1 packet, passing | pass on both oracles |
| priority | p4c `table-entries-priority-bmv2` | eDSL, landed | p4c STF, 3 packets, passing | pass on both oracles |
| register_bounds | own program from the second review | eDSL, landed | 9 hand-derived packets, passing | passes on P4-SpecTec; two packets diverge on BMv2 by the recorded out-of-range register rule, carried as a strict xfail |

## Open threads

Things a resuming agent should know are in motion or deliberately left.

- **Architecture implementation: authorized and active.**
  Read [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md) before starting
  the next implementation step. Lean is to own abstract syntax, validity,
  and meaning; protobuf owns encoding, connected by explicitly specified
  conversion. The updated note also records the agreed separate Lean
  eDSL/interpreter package, typed core with verified lowering and selective
  proof-producing elaboration, reference-execution reuse before proved
  refinements, and prior-art lessons. It now includes the P4 expressiveness
  north star and agreed example progression: consolidate the existing
  corpus, then tutorial firewall, `xdp-filter`, conditional flowlet switching,
  and a bounded Katran configuration, with a common acceptance bar. Upstream
  pins and precise application profiles remain open. Rust is excluded. Bili has now
  authorized autonomous implementation and explicitly resumed small commits
  and pushes. Follow [implementation.md](implementation.md), recording low-
  confidence choices and revisit triggers rather than waiting for feedback.
  The specification and schema now live in `ir/` (`p4blo-ir`); the separate
  `lean/` package (`p4blo-lean`, `P4bloLean` imports) exposes reference block
  and switch execution, not a second engine or full validator. The typed
  eDSL is next. `scripts/check-lean.sh` explicitly builds and tests both
  packages with matching toolchains and the spec's proof audit; dependency
  compilation alone would omit that audit. Generated protobuf bindings and
  executable protocol are unchanged. The old executable path no longer exists.
  Independent review: `notes/reviews/package-boundary.md`; its wrong empty-
  packet expectation was fixed without changing semantics. New layout tests
  guard dependency direction, toolchains and descriptor/binary locations.
  Verification: both Lean package gates pass (287 spec checks and the API
  smoke tests), required DRT **95 passed**, schema generation has no drift.
  Full Python/schema/oracle gate: **1004 passed, 1 expected BMv2 divergence,
  no skips**, lint/typecheck/format/schema/workflow checks pass. Clean-worktree
  review also passed from no build caches and no active default toolchain:
  both Lean packages, 3 layout tests, 95 required DRT and Buf/no-drift checks.
  Shared corpus and oracle tooling now live under `tests/`, with unchanged
  source/golden/vector bytes and oracle pins. All three replay suites discover
  the same 10 programs/15 vector files, guarded by a layout regression. The
  migrated Docker context builds; oracle drivers now also pass pyright.
  Consolidation gates: both Lean packages and 95 required DRT pass; full gate
  **1005 passed, 1 expected divergence, no skips**. Independent review is in
  `notes/reviews/shared-verification-layout.md`; the strengthened discovery
  check separately passes. Next: verified typed scalar authoring, then typed references and
  statements for stage-0 examples. Package migration remote Lean/SpecTec/BMv2
  workflows passed at `931e47f`; Python/schema CI was still running when checked.

- **Verification program: active.** Follow `verification.md` in order.
  Required Lean CI, complete-sequence replay bundles and abstract extern
  state comparison landed. Independent reviews found descendant-pipe
  timeout, lost protocol-failure replay and wide-state decimal-limit gaps;
  all are fixed with regressions. Reviews live in `notes/reviews/`.
  The closed scalar checker and `ScalarTyping.check_sound` landed and were
  independently reviewed: accepted expressions evaluate with the inferred
  type and preserve any Run. This is not Python or whole-program soundness.
  Typed generated-program DRT covers scalar operators systematically,
  200 shrinking examples and faulting unselected parser branches. CI retains
  failure bundles for 14 days. Latest full gate at `0bb5659`: **1001 passed, 1 expected
  BMv2 divergence, no skips**, with the pinned SpecTec oracle built locally;
  build/audit and 287 Lean checks pass. Required DRT now includes 95 tests,
  including an old error-reason test that review found excluded by its name.
  All four remote workflows passed for the preceding checkpoint `836b194`.
  The statement interpreter now uses a total continuation step and an
  unfoldable actual runner, with a finite-trace soundness theorem. It was
  independently compared with the old executor on fault/copyback cases.
  Eleven scalar value/branch laws complement the type-safety theorem.
  First mutation round: four killed, two survived; the strengthened suite
  kills both survivors and two fresh faults. A third round kills all three
  eager branch mutants with replayable mismatches
  (`notes/mutations/2026-09-23.md`). Proof-integrity mutation tests separately
  reject `sorry` and a forged axiom. The reviewed bounded reexecution checker
  is integrated; its fixed-program JSON bridge passed independent review,
  including 58 CLI tamper probes (`notes/reviews/certificate-wire.md`). See
  `certificates.md` for its exact trust boundary.
  Building the Python producer exposed a real zero-literal serialization
  defect: Lean omitted numeric zero in protobuf string fields. The encoder
  now emits `"0"`; explicit tests and independent cross-language review pass
  (`notes/reviews/zero-encoding.md`). No adapter normalization hides the bug.
  Generated stateful programs passed independent review and 28 tests,
  including 100 shrinking campaigns and 247 deterministic comparisons.
  A reset-before-read fault shrinks to a two-request persistence witness
  and its complete replay works (`notes/reviews/stateful-generation.md`).
  The Python certificate producer is integrated with 55 focused tests.
  Independent adversarial review exposed stale-binding and malformed-cell
  false acceptance, successful-peer descendant leakage and duplicate keys;
  fixes and regressions pass locally and independent follow-up confirms them
  (`notes/reviews/python-certificate.md`). See `certificates.md` for the CLI.
  Fourth semantic round: Python and Lean counter-OOB mutations each survive
  the previous 27-test gate and fail the new stateful known-answer sequence
  on state alone. Both replays reproduce; restored code/replay and 28 new
  stateful tests pass. Exact patches, commands and results are preserved in
  `notes/mutations/2026-09-23.md`. State-only CLI diagnostics now show the
  actual differing cells, even when an input cannot be represented in STF.
  All sub-agent changes are integrated and reviewed; temporary worktrees
  were removed after confirming clean status and merged commits. No pending
  agent task or unmerged implementation is needed to resume.
  Still open: whole-program validity/soundness, validated-program termination,
  variables/aggregates and generation of tables, nested calls, parser faults
  and further extern families. Next concrete step: extend scalar checking to
  variables under an explicit typed-frame relation, then aggregate lvalues
  and assignment preservation. `verification.md` lists the bounded follow-on
  tasks. Neither finite traces nor matching test results prove universal
  Python equivalence.

- **eDSL v2: done** (2026-09-22, reviewed and fixed 2026-09-23). The
  typed surface is `p4blo.edsl`, the v1 builder is `p4blo.edsl.core`;
  all ten corpus programs are authored in v2 with byte-identical
  goldens, type-checked in CI; `tests/test_pyright.py` guards the
  static rules with must-pass and must-fail fixtures. The review is
  `notes/reviews/edsl-v2.md` and every finding is fixed.
- **BMv2 as a second oracle: done** (`tests/oracle/bmv2/`, its own CI job). It
  decides longest prefix, const-entry and ternary priorities without the
  translation P4-SpecTec needs. It cannot see `flood`, which no corpus
  program declares; a program that does would be the way to test it.
- **Playground** (Pyodide/marimo) was removed from the plan on
  2026-09-22; the pure-Python and Python 3.13 constraints keep it
  possible.
- **Unconfirmed review points left open**, from
  `notes/reviews/steps2-5.md`: checksum16 padding for data widths not
  a multiple of 16 has not been judged by the oracle; sub-block
  instance names `<block>_inst` are not checked against the caller's
  scope; a case with both a bad entry and a bad port reports different
  first errors on Python and Lean.
- **Three type checkers** compute expression types: the validator,
  `interp/widths.py`, and the printer's `_Typer`; they must agree, and
  one would do. The typed eDSL is a fourth, at a different level.
- **The p4c backend is deferred behind verification.** The design names it so
  that p4c's whole test suite becomes the corpus. It is the community
  version's first job and the experiment that would really test claim 1;
  `docs/writeup.md` section 5 and 4ward are the route.
- **Elaborated-but-unexercised rows** of `coverage.md` (functions,
  newtypes, constructor parameters, named arguments) are rulings, not
  performed rewrites; a p4c backend is the experiment that would test
  them.

## Blocked

Nothing.
