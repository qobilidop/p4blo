# Status

Where the work stands, by build-order step from
[design.md](design.md#build-order), and what is open. Updated at every
checkpoint. To resume the work, read this, then
[decisions.md](decisions.md), then [workflows.md](workflows.md).

Last updated: 2026-09-23, implementing the accepted Python/Lean architecture,
verified scalar commands and independently tested firewall state. The original prototype's
steps are complete. The stronger assurance work is in progress; its
acceptance criteria and trust boundaries are in [verification.md](verification.md).

## Latest checked checkpoint

Field-primitive integration at `792a029`, including typed commands and
generated firewall flows: both Lean package gates/audits pass, with **392
spec checks**, 21 expression answers/nine negative checks, nine command
answers/four negative checks, real parameter writes and the continuation
witness. Required real-Lean DRT: **246 passed**. Full Python/schema/oracle
gate: **1447 passed / 5 precise expected discrepancies / no skips**, plus
formatting, lint, types, schema generation/no drift and workflow checks;
all commands exited 0. Independent reviews: `notes/reviews/typed-statements.md`,
`field-primitives.md`, `firewall-boundaries.md` and `firewall-generated.md`.

All four remote workflows passed for checkpoint `eb3ff02`; newer CI must be
checked separately. The five retained semantic-fault bundles have tracked
reconstruction recipes and ignored concrete copies under `.artifacts/drt`.
Earlier exact counts and experiments remain in named review/assurance
reports and git history, not competing current instructions below.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | existing constructs and explicit extern contracts; no application escape hatch | green: eleven corpus programs fit; firewall adds no core construct; coverage table published |
| 2. Supports the tested real programs | corpus packets and original firewall packet/state prefixes | 17 vector files, 11 programs; one strict BMv2 register divergence; separate CRC/mask probes expose four precise pinned SpecTec discrepancies |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT and named checked properties | green: 392 spec checks plus user-package tests; corpus and typed generated-program DRT with extern-state comparison; packing, contextual scalar soundness/completeness, exact scalar expression/command lowering, field primitive reconstruction, finite-trace execution and bounded-checker soundness proofs; no universal Python equivalence claim |

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

- **Verified Lean authoring: typed scalar commands integrated.**
  Closed bits/bools/addition/equality/mux and context-indexed variable reads
  share one AST and independent Fin/Bool source semantics. Exact lowering
  preserves the source value and the entire Run under actual action-first
  frame agreement. A constructive frame witness rules out vacuous premises.
  The scoped IR checker validates unique nonempty names/positive widths and
  has soundness and completeness for its scalar relation.
  Assignment/sequence/if use independent source-state updates and lower to
  finite prefixes of actual execution. Exact source values, unrelated Run
  fields and names outside the target set are preserved. Constructive
  permission/declaration/frame witnesses rule out vacuous premises.
  No validated global initialization, complete program or verified codec
  claim follows; action layers remain excluded from writable bodies.

  Twenty-one independently expected authored expressions include eight
  variable cases; malformed contexts/references, missing/wrong-width frames
  and action shadowing are tested. Mutation evidence distinguishes proof
  rejection, compiled-but-wrong surface accessors, corrupted input fixtures
  and a replayed actual Python-read mismatch. Exact obligations, axioms,
  decisions, commands and exclusions: `lean/ASSURANCE.md`; independent
  review: `notes/reviews/typed-frames.md`.
  Commands add nine independent whole-state answers and four negative typing
  cases, real out/inout writes and a faulting-continuation witness. Six
  adversarial changes separate proof rejection, compiled wrong source intent
  and an actual Python-write mismatch saved/replayed live and restored.
  Review: `notes/reviews/typed-statements.md`; exact scope in `lean/ASSURANCE.md`.
  Next: typed packet/metadata fields, not every remaining scalar operator.
  `notes/typed-fields-plan.md` requires actual Index agreement and full
  sibling/validity preservation. Primitive field bridges are integrated
  from `ddb9f0e`: exact nominal declaration/shape premises, stored invalid-
  header fields, validity and siblings, with three actual setter proof faults
  rejected. Review: `notes/reviews/field-primitives.md`. These return rebuilt
  containers, not persistent nested-frame writes. Independent aggregate
  stores/paths are active in isolated `work/typed-fields`, based on that
  committed interface.

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
  Byte-truncation coverage is integrated from `d547a61`: all 55 cuts of one
  TCP frame, 54 valid-malformed-valid persistence sequences and 41 additional
  unchanged-original BMv2 prefix observations. Atomic-extract errors, validity
  and retained payload have independent expectations; the instrumented parser
  observer is explicitly distinct from the original oracle. An actual Python
  cursor fault creates two payload-only mismatches, automatically saves its
  five-request bundle and agrees after restoration. Review and full recipes:
  `notes/reviews/firewall-boundaries.md`, `notes/firewall-boundaries.md`.
  Generated `tcp-flow-policy-v1` is integrated from `b7f59a1`: forty shrinking
  examples per engine, full-cell independent GF(2)/zlib expectations,
  mid-sequence host policy replacement and targeted Bloom correlations.
  Three unchanged-original BMv2 scenarios add eleven prefix observations;
  host changes within one sequence remain Python/Lean-only evidence.
  An actual table-hit fault shrinks to one absent-rule SYN: packets match
  but two wrong cells expose it. The complete saved replay fails live and
  passes restored; inputs are promoted into a tracked named regression.
  See `notes/firewall-generated.md` and `notes/reviews/firewall-generated.md`.
  The external job selects this suite. Lean authoring/application proofs
  and broader profiles remain open.

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
  general assignment preservation, tables/nested calls/parser-fault generation,
  further extern contracts and application properties.

- **Interchange is tested, not verified.**
  Real encoder/decoder defects were fixed without adapter normalization:
  zero literals now emit decimal `"0"`; missing/null decimal string fields
  no longer become numeric zero. Forty-two wire cases include persistent
  valid/malformed/valid requests with counters exactly 1/1/2. Reviews:
  `notes/reviews/zero-encoding.md`, `decimal-wire-defaults.md`.
  Versioned representability, codec proofs, resource limits, duplicate input
  keys and unknown-field policy remain open.
  A read-only audit reproduced duplicate reply keys erasing a packet and
  replay envelope versions accepting booleans/floats. Narrow harness
  hardening is queued in isolated `work/wire-harness`, based on `602d349`;
  preserve intentionally invalid IR replays rather than applying semantic
  validation at the artifact boundary. This is distinct from a codec proof.

- **XDP and later examples: compile-only infrastructure in review.**
  `notes/xdp-preflight.md` pins the authentic Ethernet-allow xdp-filter
  build and libbpf, complete per-CPU observations and an FD-only non-attaching
  oracle design. Main's accepted evidence remains preflight; compile-only
  work is isolated on `work/xdp-build`. Capability-bearing
  execution and redistribution licensing need explicit handling.
  Do not treat Docker availability or skipped kernel tests as an oracle pass.
  Flowlet time/randomness and the bounded Katran profile still require audit.
  The pinned object and open-only native metadata inspector build and run
  without added capabilities; final offline acceptance is not yet complete
  and no kernel execution is claimed. Docker VM disk capacity
  blocked an additional build dependency. Only exact own rebuildable cache
  entries and the own temporary image were removed; the image has a verified
  host recovery export. The isolated `docs/notes/xdp-build-progress.md`
  records recovery/hash, tested versus untested files and next steps.
  Unrelated images/volumes are not authorized cleanup targets. A dedicated
  workflow now tests the isolated branch on a clean GitHub runner. First CI
  compiled/repeated the original and passed baseline syscall tracing and
  map-capacity rejection; an ambiguous BTF test anchor and unreadable public
  source archives were fixed in small follow-ups. Final rerun/review remains
  required before integration. The main worktree does not depend on this
  pending infrastructure; Python/Lean proof work continues independently.

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
