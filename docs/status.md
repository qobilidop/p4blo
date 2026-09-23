# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order), and what is open. Updated at every
checkpoint. To resume the work, read this, then
[decisions.md](decisions.md), then [workflows.md](workflows.md).

Last updated: 2026-09-23, implementing the accepted Python/Lean architecture,
verified scalar references and independently tested firewall state. The original prototype's
steps are complete. The stronger assurance work is in progress; its
acceptance criteria and trust boundaries are in [verification.md](verification.md).

## Latest checked checkpoint

Typed-context integration at `46893ff`: both Lean package gates and audits
pass, including **357 spec checks**, 21 user known answers and nine negative
typing checks. Required real-Lean DRT: **175 passed**. Full Python/schema/
oracle gate: **1180 passed, 5 precise expected discrepancies, no skips**;
formatting, lint, typechecking, schema generation and workflow checks pass.
The saved typed-read mutant bundle replays successfully after restoration.
Independent review: [notes/reviews/typed-frames.md](notes/reviews/typed-frames.md).
The authoring replay-retention follow-up passes **24 focused checks**,
**177 required DRT** and the full **1182 passed / 5 expected / no skips**
gate. A scoped actual Python-read fault now requires automatic replay
creation before the expected-output assertion, live replay divergence and
restored replay agreement. Shared wrong answers still fail independently.
Review: `notes/reviews/authoring-replay.md`. No Lean or production code changed.
All four remote workflows passed for checkpoint `50322dd`; the pushed
typed-frame checkpoint `0ad1b5b` was still running when last checked.
Earlier checkpoint evidence
remains in the named review/assurance reports and git history, not as competing
current instructions below.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | existing constructs and explicit extern contracts; no application escape hatch | green: eleven corpus programs fit; firewall adds no core construct; coverage table published |
| 2. Supports the tested real programs | corpus packets and original firewall packet/state prefixes | 17 vector files, 11 programs; one strict BMv2 register divergence; separate CRC/mask probes expose four precise pinned SpecTec discrepancies |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT and named checked properties | green: 357 spec checks plus user-package tests; corpus and typed generated-program DRT with extern-state comparison; packing, contextual scalar soundness/completeness, exact scalar eDSL lowering under frame agreement, finite-trace execution and bounded-checker soundness proofs; no universal Python equivalence claim |

## Steps

| Step | What | Status |
|---|---|---|
| 0 | Skeleton: flake, Python project, schema stub, CI, docs | done |
| 1 | Schema, validator, semantics, forwarder in text format, interpreter, STF runner | done: the forwarder's five vectors pass end to end |
| 2 | Extern registry, stateful program | done: registry with register, counter and checksum16; the stateful program and the forwarder's checksum |
| 3 | eDSL, four corpus programs, two architectures, metadata contract | done: eleven programs in the typed eDSL, both architectures, contract check |
| 4 | Printer, v1model shim, P4-SpecTec oracle job, STF replay both sides | done: corpus gates run on both oracles in separate CI jobs; precise expected discrepancies are recorded above |
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
| tutorial_firewall | pinned p4lang tutorial solution | typed Python eDSL, landed | connection establishment and Bloom false-positive vectors; six bounded profiles total | original BMv2 packets/all 8192 register cells at 30 prefix boundaries; SpecTec controls pass but exact CRC/mask probes disagree; Lean-authored port/proofs still open |

## Open threads

Things a resuming agent should know are in motion or deliberately left.

- **Architecture implementation: authorized and active.**
  Follow [implementation.md](implementation.md) and the agreed design in
  [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md). Python and Lean only;
  full architecture-independent P4 remains a north star. Small commits and
  pushes are authorized. Record uncertain choices and revisit triggers.

  Package boundaries and shared verification layout are complete:
  `ir/` owns `p4blo-ir` / `P4bloIR`, abstract meaning and the wire schema;
  `lean/` owns user-facing `p4blo` / `P4blo` and imports the spec one-way;
  `python/p4blo/` provides Python authoring and interpretation. Shared corpus
  and oracles live under `tests/`. Wire identities and generated bytes are
  preserved. Both Lean packages and their default proof audits are explicit
  gates. Independent reviews include clean builds without caches or an
  active default toolchain: `notes/reviews/package-boundary.md`,
  `shared-verification-layout.md` and `lean-public-names.md`.

- **Verified Lean authoring: typed scalar references integrated.**
  Closed bits/bools/addition/equality/mux and context-indexed variable reads
  share one AST and independent Fin/Bool source semantics. Exact lowering
  preserves the source value and the entire Run under actual action-first
  frame agreement. A constructive frame witness rules out vacuous premises.
  The scoped IR checker validates unique nonempty names/positive widths and
  has soundness and completeness for its scalar relation.
  Declaration agreement is separate: no validated block initialization,
  writable statement, complete program or verified codec claim follows.

  Twenty-one independently expected authored expressions include eight
  variable cases; malformed contexts/references, missing/wrong-width frames
  and action shadowing are tested. Mutation evidence distinguishes proof
  rejection, compiled-but-wrong surface accessors, corrupted input fixtures
  and a replayed actual Python-read mismatch. Exact obligations, axioms,
  decisions, commands and exclusions: `lean/ASSURANCE.md`; independent
  review: `notes/reviews/typed-frames.md`.
  Next: writable scalar assignment/sequence/if into existing
  `Execution.step`/`Finishes.sound`, per `notes/typed-frames-plan.md`.
  Then typed packet fields promptly, not every remaining arithmetic operator.
  Implementation is active in isolated `work/typed-statements`, based on
  committed `46893ff`; no unmerged statement proof is required to use main.

- **Tutorial firewall: bounded Python port and original-state oracle done.**
  The typed port adds no core IR construct. Independent packet and complete
  8192-cell expectations retain Bloom false positives. Original pinned BMv2
  matches 30 bounded prefix observations. CRC16/CRC32 services have explicit
  positive byte-aligned contracts, no hidden padding or range reduction.
  Exact strict probes expose pinned SpecTec's odd-byte CRC32 and table-mask
  defects; passing controls remain separate. Oracle CI discovers both sets.
  Scope, pins, observer barrier, exclusions and authoring costs:
  `notes/firewall-port.md`, `notes/crc-contract.md`.
  Reviews: `notes/reviews/firewall-port.md`, `crc-externs.md`.

  Four validator-accepted wrong ports fail both engines. Subsequent actual
  Python/Lean CRC XOR-one mutations pass packet-only gates but produce three
  state-only divergences in four requests. Strong known-answer/full-state
  gates kill both compiled mutants; all faults are restored. Proof audits
  do not certify CRC's intended external algorithm. Reproduction and review:
  `notes/mutations/firewall-hash-state.md`,
  `notes/reviews/firewall-hash-state.md`.
  Broader malformed coverage is active in isolated `work/firewall-boundaries`
  at `50322dd`; truncated Ethernet/IPv4 behavior and generated flow sequences
  are not yet claimed. Lean authoring/application proofs remain open.

- **Verification infrastructure is established; broader proofs remain open.**
  [verification.md](verification.md) records exact claims. Required real-Lean
  CI, complete-sequence failure replays, abstract extern-state comparison,
  timeout/process cleanup, typed generated scalar/stateful programs and
  shrinking are in place. Finite-trace execution soundness, scalar value
  laws and a bounded reexecution checker connect to actual production
  execution. The Python certificate producer is documented in
  [certificates.md](certificates.md); it is not universal equivalence or a
  standalone proof term. Reviews and fixes cover stale binding observations,
  malformed cells, duplicate responses and descendant process leakage.

  Earlier adversarial campaigns found and killed eager branches and
  state-only out-of-bounds/persistence faults; exact patches/replays are in
  `notes/mutations/2026-09-23.md`. Compiler/surface faults are additionally
  recorded in `lean/ASSURANCE.md`. A proof-integrity gate rejects `sorry`,
  forged axioms and unexpected transitive axioms; theorem statements still
  require review. Matching tests never prove universal Python equivalence.
  Still open: whole-program validity/soundness and termination, aggregates,
  assignment preservation, tables/nested calls/parser-fault generation,
  further extern contracts and application properties.

- **Interchange is tested, not verified.**
  Real encoder/decoder defects were fixed without adapter normalization:
  zero literals now emit decimal `"0"`; missing/null decimal string fields
  no longer become numeric zero. Forty-two wire cases include persistent
  valid/malformed/valid requests with counters exactly 1/1/2. Reviews:
  `notes/reviews/zero-encoding.md`, `decimal-wire-defaults.md`.
  Versioned representability, codec proofs, resource limits, duplicate input
  keys and unknown-field policy remain open.

- **XDP and later examples: source/environment preflight only.**
  `notes/xdp-preflight.md` pins the authentic Ethernet-allow xdp-filter
  build and libbpf, complete per-CPU observations and an FD-only non-attaching
  oracle design. No BPF compile/load/run evidence exists. A reproducible
  compile-only image is a safe next independent step; capability-bearing
  execution and redistribution licensing need explicit handling.
  Do not treat Docker availability or skipped kernel tests as an oracle pass.
  Flowlet time/randomness and the bounded Katran profile still require audit.
  Compile-only image implementation is active in isolated `work/xdp-build`
  based on `0ad1b5b`; no successful compilation or kernel execution is yet
  claimed. The main worktree does not depend on this pending infrastructure.

- **eDSL v2: done** (2026-09-22, reviewed and fixed 2026-09-23). The
  typed surface is `p4blo.edsl`, the v1 builder is `p4blo.edsl.core`;
  all eleven corpus programs are authored in v2 with byte-identical
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
