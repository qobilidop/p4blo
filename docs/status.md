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

Combined integration at `ba274f3`, including shared command factoring, actual
KeyValue codec laws and call-copy conformance: both Lean package gates and
default audits pass, with **444 spec checks**, all existing scalar/context/
command/path answers and negative checks, seven field-expression answers and
six additional kernel rejection examples. Required real-Lean DRT:
**393 passed**, no skips. Full gate:
**1724 passed / 5 precise expected discrepancies / 1 explicit skip**, plus
formatting, lint, types, schema generation/no drift and workflow checks;
all commands exited 0. The sole skip is the unavailable local XDP image;
required native XDP CI passes at `8829000`, including lifecycle regressions.
Latest reviews under `notes/reviews/`: `field-permissions.md`,
`command-seam.md`, `keyvalue-codec.md` and `call-copy.md`.

All five remote workflows pass for `8829000`; newer CI must be checked
separately. Twelve retained execution-fault bundles and nine raw leaf-codec
artifacts have tracked reconstruction recipes and byte-checked ignored
copies under `.artifacts/drt` and `.artifacts/codec` respectively.
All twelve execution bundles replay successfully on the integrated binaries
(nineteen requests), as do all nine raw codec inputs after fault restoration.
Earlier exact counts and experiments remain in named review/assurance
reports and git history, not competing current instructions below.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | existing constructs and explicit extern contracts; no application escape hatch | green: eleven corpus programs fit; firewall adds no core construct; coverage table published |
| 2. Supports the tested real programs | corpus packets and original firewall packet/state prefixes | 17 vector files, 11 programs; one strict BMv2 register divergence; separate CRC/mask probes expose four precise pinned SpecTec discrepancies |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT and named checked properties | green: 444 spec checks plus user-package tests; corpus and typed generated-program DRT with extern-state comparison; contextual scalar checking, exact scalar/field expression and scalar command lowering, aggregate path correspondence, representable leaf codecs and finite-trace execution proofs; no universal Python equivalence claim |

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
  rejected. Review: `notes/reviews/field-primitives.md`. The next aggregate
  checkpoint `7a2ad91` is integrated at `d2a1921`: independent finite source
  shapes/stores and scalar paths now correspond to actual nested reads and
  persistent writes, preserving validity, siblings, unrelated roots and
  non-value Run fields. Local shape checks do not imply nominal coherence;
  positive witnesses and impossible conflicting-layout examples expose that
  boundary. No root permission or integrated expression/command proof is
  claimed yet. Review: `notes/reviews/aggregate-paths.md`.
  `a271370`/`a3f3537` are integrated at `d8e2341`: one shared `ExprWith`
  operator AST now serves scalar references and aggregate paths. Concrete
  field typing uses actual declarations/Index, and evaluation returns the
  exact independent source value with the entire Run unchanged. Seven
  authored field expressions and six kernel rejection examples complement
  old scalar fixtures. Review `notes/reviews/field-expressions.md` found and
  fixed pre-expression snapshots: a real read-side effect survived the old
  observer but fails after evaluation is observed first. Three actual Python
  read/setter faults have retained live/restored replay evidence; proof and
  compiled surface faults are separately recorded in `lean/ASSURANCE.md`.
  Next: command write factoring and actual root permissions, active in
  isolated `work/field-commands`, based on committed `d8e2341`, following
  `notes/field-commands-plan.md` (committed `480eef4`).
  First specification increment `8b39c06` is integrated: writable member
  paths inherit actual root declaration permission, and scalar assignment/
  conditional/body relations reuse the field-expression typing boundary.
  Constructive local/out/inout witnesses and six kernel rejection examples
  cover readonly/missing/empty roots, wrong nominal kind and width mismatch.
  Both Lean gates/default audits pass after integration. This adds no runtime
  behavior or total checker. Review: `notes/reviews/field-permissions.md`.
  Generic command factoring `cd34e83` is integrated: `CmdWith` now owns the
  sole command AST, independent denotation, lowering and exact-prefix proof.
  The scalar API/theorems are preserved through concrete adapters, with all
  prior authored fixtures unchanged. Both Lean gates and 62 authored/call
  focused checks pass. Review: `notes/reviews/command-seam.md`.
  Concrete field modes/places and the actual aggregate command theorem are
  next in `work/field-commands`; the generic leaf-law theorem alone does not
  establish that instance.

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

  Local aggregate-copy profile `30a23b0` is integrated: sixteen header/struct,
  validity and width boundaries plus forty shrinking examples observe all
  source/target/unrelated stored fields after writes. Actual Python copy
  alias faults fail and replay live, then pass restored; independently
  expected bytes remain a separate gate. It does not establish stack or call
  copyback correctness. Scope, recipes and review: `notes/aggregate-copy.md`,
  `notes/reviews/aggregate-copy.md`.
  Bounded action/sub-control copy-in/out profile `2aa8864` is integrated:
  twelve boundaries and forty shrinking examples expose permitted overlapping
  input/inout snapshots, out-zero initialization and complete post-call values,
  validity, unrelated storage and untouched payload. Six real Python faults
  exercise argument aliasing, bad out defaults and skipped copyback, save the
  exact inputs and replay divergent/live then agreeing/restored. They yield
  two distinct retained input bundles. Overlapping writable arguments and
  action/local name collisions remain validator errors, not generated valid
  cases; no call proof follows. Scope and review: `notes/call-copy.md`,
  `notes/reviews/call-copy.md`.

- **Interchange has scoped leaf proofs, not a verified program codec.**
  Real encoder/decoder defects were fixed without adapter normalization:
  zero literals now emit decimal `"0"`; missing/null decimal string fields
  no longer become numeric zero. Forty-two wire cases include persistent
  valid/malformed/valid requests with counters exactly 1/1/2. Reviews:
  `notes/reviews/zero-encoding.md`, `decimal-wire-defaults.md`.
  Versioned representability, codec proofs, resource limits, duplicate input
  keys and unknown-field policy remain open.
  Harness hardening `44beaba` is integrated at `4ce3798`: duplicate keys and
  nonstandard constants are rejected recursively; replay envelope/version
  types and error diagnostics are checked without rejecting semantically
  invalid IR inputs. Actual lossy peers previously erased packets/state and
  falsely agreed; regressions now retain protocol-failure replays. All five
  prior concrete mutation bundles still replay through the stricter loader.
  Evidence/review: `notes/wire-harness.md`, `notes/reviews/wire-harness.md`.
  This is not general codec equivalence, semantic alias/unknown-field policy
  or a resource budget. `3fca173` plus default registration `1f69a58` prove
  actual decimal/uint32 and all Literal/Ty round trips over JSON values under
  v0 representability; semantic validity is deliberately not a premise.
  Thirty-six native checks and 94 focused checks include 48 required native
  interoperability probes. A paired wrong wire key still passes universal
  round trips but fails three independent protobuf answers. Review also fixed
  a false/zero observer ambiguity with type-sensitive JSON comparisons.
  Three raw leaf artifacts and tracked recipes preserve this boundary:
  `notes/codec-proof.md`, `notes/reviews/codec-leaves.md`.
  KeyValue increment `b2e5ef2` is integrated at `ba274f3`: every actual key
  constructor has a JSON-value round-trip law, bounding only uint32 prefix
  lengths. Arbitrary values/masks and semantically invalid keys remain in
  scope. Six paired value/mask remappings preserve round trips and encoded
  payloads but fail independent decoded-value answers; exact raw artifacts
  all replay restored. The focused codec suite now has 170 checks and native
  codec driver 52. Review: `notes/reviews/keyvalue-codec.md`; exact source
  recipes and proof boundary: `notes/keyvalue-codec.md`.
  Next investigate proof-visible recursion in the actual recursive decoder,
  isolated `work/codec-recursion` at `ba274f3`; a parallel proof-only decoder
  would not close the boundary. Text parsing and semantic-version policy
  remain separate obligations.

- **XDP and later examples: compile-only profile integrated.**
  `notes/xdp-preflight.md` pins the authentic Ethernet-allow xdp-filter
  build and libbpf, complete per-CPU observations and an FD-only non-attaching
  oracle design. `980c642` integrates the pinned original feature build,
  offline ELF/BTF/map inspection, syscall tracing and negative fixtures.
  Required clean-runner CI `35900039992` at `63ec6d1` passes all ten checks
  without skips. Independent review verified the downloaded repeated object,
  source archive hashes and compiler provenance. Exact evidence and limits:
  `tests/oracle/xdp/README.md`, `notes/reviews/xdp-build.md`.
  No kernel load/run or p4blo behavioral equivalence is established.
  Capability-bearing execution and port redistribution licensing still need
  explicit handling.
  Do not treat Docker availability or skipped kernel tests as an oracle pass.
  Flowlet time/randomness and the bounded Katran profile still require audit.
  The runtime remains non-root, capability-free, network-free and read-only;
  no security restriction was relaxed to obtain a pass. Native CI is now a
  fifth required workflow, retaining objects/provenance/corresponding sources
  for 14 days. The local final image is unavailable because of Docker VM
  capacity: its one skip is not native evidence. Only exact own rebuildable
  cache/image data was removed, with a verified host recovery export. The
  capacity incident, failed fixture/permission checks and recovery are in
  `notes/xdp-build-progress.md`; unrelated Docker data is not a cleanup target.
  Next: an FD-only strict adapter and explicit capability-scoped execution
  preflight, independently of the ongoing Lean authoring work.
  Observer-lifecycle fix `1fecd97` is integrated: Docker client timeout had
  left a daemon-owned container alive. The helper uses a unique owned name,
  bounded cleanup and successful exact-name absence verification. Seven pure
  failure-path regressions and live normal/timeout probes pass. Review:
  `notes/reviews/xdp-cleanup.md`. Daemon outages, forced interpreter death
  and late creation races remain outside the scoped cleanup guarantee.
  No kernel or semantic claim follows.

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
