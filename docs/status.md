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

Combined local integration at `58bb072`, including total Expr/LValue/Stmt codec proofs,
Arg wire laws, unified read-only header expressions, independent source zero,
actual/source frame-initialization proofs, readable command lists and forwarding
policy proofs, the separately named validity-guarded policy and exact flat-body
prefixes and actual body-bearing plain-root call entry: both Lean package gates and default audits pass, with
**520 spec checks**, all existing scalar/context/
command/path answers and negative checks, seven field-expression answers and
six additional field-expression kernel rejection examples, plus ten field-
command full-state answers and declaration/permission/continuation checks.
Named paths add 17 exact diagnostics and 11 rejected constructions; the
arbitrary-store policy adds seven independent policy/source/runtime answers.
Command lists retain exact previous ASTs/exports and independent order checks;
codec tests retain independent constructor observations and malformed errors.
Header primitives add opposite-validity/direct/empty-header answers; source
zero pins independent values, exact fuel limits and nominal boundaries.
Unified reads add 20 expressions and four commands with full post-read
observations; frame tests cover all entries, map keys and action absence.
The source-frame adapter adds kernel-checked actual-built forwarding
initialization, independent expected values and explicit extra declarations.
Flat-prefix proofs add four audited roots and 16 actual queue-boundary cases,
without changing runtime semantics or the former whole-body theorem APIs.
Guarded forwarding adds 64 independent Lean state answers and 32 exported
Python/Lean cases, including invalid headers and boundary TTLs.
Call entry adds seven spec checks, twelve default-audited roots and 23
focused Python checks, including independent full-state and strict JSON
observer regressions. Body-parametric entry adds six audited roots, twelve
native entry boundaries and eighteen Python checks comparing complete selected
block syntax and strictly typed snapshots. The old entry exporter remains
byte-identical; the new exporter matches the reviewed candidate exactly.
The actual local-initializer prefix adds five audited roots, sixteen native
boundaries and four missing-extra controls. An actual Python initializer fault
is caught, saved, replayed live and checked again after restoration.
Normal return adds six spec checks, nine audited roots and 41 focused Python
checks. Complete-state, ordered-write and recursive mutable-isolation observers
reject the independently reproduced selective-alias faults. The guarded call
prefix adds five audited roots, 192 native boundaries and 78 Python checks;
complete native Index/scope/shared comparisons and strict frozen Python state
reject independent observer faults. Its exporter is byte-identical to the
reviewed candidate. The independently reviewed statement-codec baseline adds
four spec checks and 107 Python checks, without changing the production
decoder. All 79 captured old statements replay with exact byte transcripts
and independent source-matched answers. The actual total statement decoder,
all-input ordinary-helper recurrence and universal representable statement
roundtrip are now integrated, with eight new audited roots and constructive
all-constructor witnesses. Two compiling faults are proof-rejected; four
other faults retain roundtrip proofs but fail independent wire/error answers.
All 25 saved campaign observations (20 distinct requests) replay restored.
The separately named observer-free whole control call adds nine audited roots, 192 native
profiles and 91 Python checks, including actual normal completion, full state,
all incoming/outgoing mutable copies and independent ordered-write controls.
Its exporter is byte-identical to the reviewed candidate.
The action-root prerequisite adds exact unshadowed block writes and action-hit
read/write laws, preserving the old block API. Four new audits, a genuine
active-frame kernel witness and eight native storage/error checks pass. Four
isolated compiling Env faults are proof-rejected; the runtime is unchanged.
The complete Lean-authored corpus forwarder now exactly matches the Python
builder and golden. Seven audited roots include actual initialization and
the invalid-IPv4 body's whole-Run identity; 24 native state profiles, two
post-drop checksum checks, four in-memory packet answers and 50 Python tests
cover the explicitly bounded port. Review found a state-only Python fault
surviving packet checks; strict complete-state checks now reject it. A new
actual TTL-underflow fault is retained and replayed live/restored.
The declaration baseline adds 14 native checks and 319 Python tests, without
changing production codecs. All 247 raw transcripts match source-pinned
expectations and exact bytes; 102 successful outputs pass public protobuf
wrappers. The action-layer field adapter adds four audited roots and a mixed
shadowed/unshadowed witness, preserving the old block-only APIs. A rejected
false theorem conclusion is not counted as a compiling runtime fault.
Nine declaration roundtrip laws now add ten default-audited roots with
constructive witnesses and overflow controls. All old bytes remain unchanged.
One actual encoder fault is proof-rejected; paired mapping/error-order faults
that preserve proofs produce 24 source-matched raw mismatches. Paired Python
fixture/Lean-observer corruption survives direct Python checks but fails
independent native anchors. All restored replays pass with reconstructed mutant
source hashes. The standalone next-table probe also passes independently;
it is unregistered and is not claimed as production Table coverage.
Required real-Lean DRT: **1114 passed**, no skips. Full gate:
**2750 passed / 5 precise expected discrepancies / 1 explicit skip**, plus
formatting, lint, types, schema generation/no drift and workflow checks;
all commands exited 0. The sole skip is the unavailable local XDP image;
required native XDP CI passes at `c550a6f`, including lifecycle regressions.
Latest reviews under `notes/reviews/`: `field-permissions.md`,
`command-seam.md`, `field-commands.md`, `keyvalue-codec.md` and `call-copy.md`.
Latest reviews also include `named-paths.md`, `forward-policy.md`,
`command-blocks.md`, `expr-codec.md`, `header-validity-primitives.md`,
`source-zero.md`, `lvalue-codec.md`, `frame-initialization.md` and
`header-validity-expressions.md`, `initial-source-frames.md` and
`guarded-forwarding.md`, `command-prefix.md`, `certificate-cleanup.md` and
`plain-call-entry.md`, `body-parametric-entry.md`, `call-initializers.md` and
`plain-call-return.md`, `guarded-call-prefix.md`, `stmt-codec-baseline.md` and
`guarded-control-call.md`, `stmt-codec.md`, `action-root-writes.md` and
`lean-forwarder.md`, `declaration-codec-baseline.md`, `field-action-writes.md`,
`declaration-codec.md` and `table-codec-next.md`.

All five remote workflows pass for `0d30fa0`; newer CI must be checked
separately. This closes the earlier macOS CI run `35922311964` failure at
`2bd65b8`: a redundant final process-group kill raised PermissionError after
timeout cleanup, masking its diagnostic. Reviewed fix `8438cbd`, integrated
at `5871da8`, attempts cleanup once, retains bounded reaping and fails closed
on cleanup denial. Six deterministic regressions and both live descendant
tests pass. The complete integrated certificate module passes all 61 cases
against the real Lean checker, without skips. Fresh remote CI run
`35924868471` passes; the closure is not merely a retry of the original commit.
Evidence: `notes/certificate-cleanup.md` and its independent review.
Eighteen retained execution-fault bundles and seventy-three raw codec
artifacts have tracked reconstruction recipes and byte-checked ignored
copies under `.artifacts/drt` and `.artifacts/codec` respectively.
All eighteen execution bundles replay successfully on this integration
(twenty-five requests), as do all seventy-three raw codec observations. The real
forwarder's new TTL0 bundle matches its current authored Program, tracked
edge input and fixed configuration. The new
statement campaigns contribute 25 observations of 20 distinct requests;
these counts are not independent-input counts. Declaration campaigns add 24
observations of 24 distinct requests; harness views are not additional inputs.
Header-read,
guarded and initializer bundles match their current exporter/wrapper and exact request. All fifteen
Expr/LValue/Arg fault inputs uniquely match tracked fixtures; all 59 Expr and
69 LValue/Arg and 79 Stmt source-matched pre-refactor transcripts retain byte-identical
stdout/stderr and exit status. Artifact
command metadata is never executed. Reconstruction recipes survive losing
local ignored artifacts and temporary logs. The 247 declaration baseline
transcripts additionally retain exact bytes, independent source-matched answers
and historical hashes at `21b0fec`; they are not fault observations.
Earlier exact counts and experiments remain in named review/assurance
reports and git history, not competing current instructions below.

## Claim matrix

| Claim | Experiment | Status |
|---|---|---|
| 1. The core is small and post-elaboration | existing constructs and explicit extern contracts; no application escape hatch | green: eleven corpus programs fit; firewall adds no core construct; coverage table published |
| 2. Supports the tested real programs | corpus packets and original firewall packet/state prefixes | 17 vector files, 11 programs; one strict BMv2 register divergence; separate CRC/mask probes expose four precise pinned SpecTec discrepancies |
| 3. A block is a function; an architecture is ordinary code | two ~50-line Python architectures, corpus unchanged under both | green: filter 45 lines, switch 50, no P4; every corpus program runs under both, and the filter's fate decisions match the switch's on every vector |
| 4. Mechanized and agrees with the reference | Lean interpreter, DRT and named checked properties | green: 520 spec checks plus user-package tests; corpus and typed generated-program DRT with extern-state comparison; contextual scalar checking, exact scalar/field expression and command lowering, header-read/source-zero correspondence, actual frame initialization and plain-root entry/normal return, representable leaf/Expr/LValue/Arg/Stmt and foundational declaration codecs and finite-trace execution proofs; no universal Python equivalence claim |

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
| forwarder | p4lang tutorial basic | Python and Lean sources equal the unchanged golden; direct Lean execution and invalid-control theorem; checksum16 computes hdrChecksum, verify deferred | 5 hand-derived STF files plus TTL0/1 and full invalid-control state checks, passing | 5/5 pass on both oracles, checksum included |
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

- **Verified Lean authoring: scalar and field commands integrated.**
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
  The next increment was typed packet/metadata fields rather than every
  remaining scalar operator; those results are recorded below.
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
  boundary. Root permission and integrated expression/command proofs were
  separate follow-up obligations, now implemented below. Review:
  `notes/reviews/aggregate-paths.md`.
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
  Command write factoring and actual root permissions followed in
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
  Concrete field modes/places and command proofs `9755077`/`7a4a05b` are
  integrated at `3f1efb6`: actual root permission, exact full source values,
  all validity bits, preserved declarations, unrelated runtime state and
  arbitrary continuations. Ten authored cases include a route-selected
  forwarding rewrite; real subcontrol directions and complete post-body
  snapshots constrain the unverified wrapper. Three generic proof faults
  fail; a compiled same-width wrong accessor passes generic proofs/DRT but
  fails independent expected bytes. Two actual authored-write validity/
  sibling faults save and replay live/restored. Review:
  `notes/reviews/field-commands.md`; recipes and scope: `lean/ASSURANCE.md`.
  The body theorem does not prove a router, initializer or call copying.
  Named paths `d47f8bc` and independent policy `d31f8bc` are integrated at
  `0dc7b08`. Names resolve unambiguously into existing typed references;
  spelling/permission soundness does not imply global schema validity.
  All six naming roots are default-audited; wrong slot, error diagnostic and
  valid-but-wrong requested intent faults are distinguished in
  `notes/named-paths.md` and its review.
  The forwarding theorem covers arbitrary source stores and actual reference
  execution against an independent complete-state hit/TTL policy. Five
  default-audited roots include lossless observation laws. Wrong destination
  and missing TTL guard faults fail the application proof; paired state
  relabeling still passes those proofs but fails independent mapping anchors.
  This does not establish parsing, checksum maintenance or architecture fate.
  Scope/review: `notes/forward-policy.md`, `notes/reviews/forward-policy.md`.
  Readable list sequencing `cf78144` is integrated at `5d0b74f`, preserving
  exact previous ASTs and exported bytes. Independent review is clear;
  both integrated Lean gates (including actual policy normalization/audit)
  and 23 focused authored-command checks pass. The combined full/required
  gates also pass at the latest checkpoint above.
  Scope: `notes/command-blocks.md`, `notes/reviews/command-blocks.md`.
  The reviewed header-validity plan/probe is committed at `cdb7a3c`:
  `notes/header-validity-plan.md`, `notes/reviews/header-validity-plan.md`.
  Primitive checkpoint 1 (`3cf11ee`/`c3ca9e6`) is integrated at `5d12252`:
  constrained header-only paths, concrete exact evaluation and authoritative
  scoped typing. Independent review is clear; both integrated Lean gates pass.
  Source constant/inversion faults fail the proof; a well-typed wrong sibling
  passes generic correctness but fails independent opposite-validity answers.
  Scope: `notes/header-validity-primitives.md` and its matching review.
  Checkpoint 2 (`edc12bd`/`078a9de`) is integrated at `2713999`: one shared
  read-family adapter preserves scalar writes and all four legacy exporter
  byte streams. Twenty expressions and four commands have independent full
  post-read observations. A weak pre-read snapshot misses a demonstrated
  correct-return side effect; the strengthened observer catches it. Actual
  Python wrong-return/side-effect faults save and replay the same complete
  witness, with restored agreement. Independent review is clear; scope and
  recipes: `notes/header-validity-expressions.md` and its matching review.
  Checkpoint 3 (`74ef437`/`fe17a77`) is integrated at `cffad0d`: a separately
  named both-valid-header policy, arbitrary-store proof, exact invalid-drop-only
  contract and concrete execution lift. Independent review is clear and combined
  gates pass above. Missing/inverted/paired guards fail the independent contract;
  exporting the old body passes generic proofs and engine agreement but fails
  independent answers. An actual Python bypass saves/live-replays divergence
  and agrees restored. Scope: `notes/guarded-forwarding.md` and its review.
  The old body's invalid-header contract and byte exports remain unchanged;
  parsing, route lookup, checksum and actual network drop remain unproved.
  An independent initialization review recommends the next premise-discharge
  bridge in `notes/initialization-bridge-plan.md` (committed `6ff0449`).
  Independent structural source zero and actual fuel-bounded Value.zero
  correspondence (`bcc4d27`/`f9d22ac`) are integrated at `c2bb0c8`. Exact
  nominal agreement and sufficient actual runtime budget remain explicit;
  mixed fixtures and existing forwarding roots discharge them constructively.
  Source-only/reference-only validity faults fail correspondence; a paired
  wrong model passes the proofs but fails independent kernel expected values.
  Review is clear, both integrated Lean gates pass; isolated full and required
  gates pass, including a fresh two-package build and 469 fresh-binary DRT
  checks after removing stale caches from the build search path. Scope:
  `notes/source-zero.md`, `notes/reviews/source-zero.md`.
  The actual Frame.forBlock theorem (`f00ca87`/`f1737b7`) is integrated at
  `db99dc2`. It accounts for every scope declaration, exact lookups/absence,
  the actual selected scope and no action overlay, without assuming scope
  block or stored declaration names match their lookup keys. Three compiling
  drop/name/overlay faults fail the exact theorem. Independent review is clear;
  both integrated Lean gates pass with 481 spec checks. Combined Python/DRT
  gates pass at the latest checkpoint above. Scope: `notes/frame-initialization.md`
  and its matching review.
  Source-zero/FrameMatches adapter `139e478`/`6c99835` is integrated at
  `c269994`: modeled zero values are discharged from independent source zero;
  unmodeled declarations retain explicit success obligations. A separate
  coverage condition justifies absent extras. Kernel-checked actual Index.build
  and forwarding-frame witnesses have only the standard three axioms, including
  independent expected values. Successful/failing extras are explicit local
  scope extensions, not the packet wrapper's actual observer layout. Independent
  review is clear; isolated fresh-cache Lean and 538 required DRT checks pass.
  Combined integration gates pass at the latest checkpoint above.
  Scope: `notes/initial-source-frames.md`
  and its matching review. Actual plain-root sub-control entry
  (`258ec14`/`0559c70`/`f8a0f61`) is integrated at `901c994`: actual four-root
  binding, complete Run frame replacement and exact captured caller/queue.
  The source bridge derives actual initialization for a kernel-built selected
  declaration program, including the real H/Result observer layout and extras.
  Its empty body and manually supplied caller remain explicit boundaries.
  Independent review is clear; twelve audit roots have only standard axioms,
  seven new spec checks and 23 focused Python checks pass. Five compiling
  actual-Exec faults are rejected by proofs; paired declaration corruption
  fails an independent syntax anchor. Actual Python cursor corruption fails
  entry-state answers. Eight state-survivor controls and eight JSON/type/case
  controls permanently reject demonstrated observer gaps. These internal
  snapshots are not packet-program replay bundles. Scope/review:
  `notes/plain-call-entry.md`, `notes/reviews/plain-call-entry.md`.
  Body-parametric entry (`db6b861`/`381e627`) is integrated at `dbfa37c`:
  one actual-built body family supplies lookup/scope and initialization while
  preserving the old empty API. The source proof is generalized once, not
  duplicated. Full selected guarded-block syntax matches the tracked Python
  wrapper, including both local assignments and the complete observer. Six
  audited roots, twelve native boundaries and 41 combined entry tests pass.
  A wrong empty index fails the proof; two wrong-but-compiling selected bodies
  fail independent syntax identity. No body execution is inferred from entry.
  Scope/review: `notes/body-parametric-entry.md` and its matching review.
  The next composition connected real local assignments and guarded
  forwarding to the exact pending observer suffix and return, as recorded below.
  Staged contract: `notes/call-body-prefix-plan.md`. Do not substitute the
  empty declaration witness, reshape the wrapper or claim copyback/global
  validity from a successful finite prefix.
  The disjoint local-assignment prerequisite (`70f5775`/`0d983ab`) is
  integrated at `21410b6`: the exact scratch19/unrelated165 prefix preserves
  full source agreement, outside names and arbitrary pending work. It does
  not itself assume or establish entry to an actual body-bearing call.
  Independent review and adversarial evidence: `notes/call-initializers.md`
  and its matching review. Composition (`dcbdf9c`/`101d2d7`) is independently
  reviewed and integrated at `b115c32`, including explicit initializer and
  selected-body syntax identity. It starts at actual call entry and proves
  full source-policy agreement plus exact non-frame preservation, while the
  arbitrary suffix and captured caller return remain pending. Five audit
  roots, 192 native profiles and 78 focused Python checks pass. Review exposed
  an int/float shared-state comparison survivor; recursive exact-type checks
  and complete native Index/scope/shared observations now reject it, with
  permanent corruption controls. A new actual local-write fault reuses the
  existing guarded packet input, so artifact counts do not increase. Scope:
  `notes/guarded-call-prefix.md`, `notes/reviews/guarded-call-prefix.md`.
  Normal return (`d019f64`/`16626b5`/`884a168`) is independently reviewed and
  integrated at `5061126`; contract:
  `notes/plain-call-return-plan.md`. It preserves the current post-callee Run
  outside the restored caller frame, not a historical entry Run. Review found three selective-alias
  observer gaps; recursive mutable-container detachment checks and four real
  branch writes now reject them, with permanent negative controls.
  All integrated gates and retained replays pass; exact scope and evidence:
  `notes/plain-call-return.md` and its matching review. With the guarded prefix
  landed, follow committed `notes/guarded-call-plan.md` for a separately named
  observer-free whole control call. That result (`1a0bf48`/`e8a584c`) is now
  independently reviewed and integrated at `9e53f4b`: actual empty-list pop
  and normal return complete `callBlock`, with exact independent source-policy
  results and original caller/shared-state preservation. Nine audits, 192
  native cases and 91 Python checks pass. Complete values alone cannot detect
  commuting writes or skipped same-value observer copyback; explicit weak/
  strong ordered-write controls demonstrate that gap. A separate observed
  packet wrapper exposes a genuine live/restored copyback mismatch on the
  same retained guarded input. Evidence/review: `notes/guarded-control-call.md`
  and its matching review. It keeps the observer parameter as
  pass-through but does not execute the seventeen observation assignments or
  claim parsing, lookup, checksum, architecture fate or full packet execution.
  Actual forwarder authoring (`0b157ff`/`2f92dad`) is independently reviewed
  and integrated at `f1493d8`, following `notes/lean-forwarder-next.md`.
  Complete Program equality preserves TTL wrap, old-destination MAC ordering,
  default drop, post-drop checksum and non-IPv4 pass-through. Both decoded
  DRT and direct public in-memory execution pass existing vectors and literal
  edge answers. Actual initialization and whole-Run invalid-control identity
  have seven default-audited roots. Review found a metadata-write survivor
  under packet-only tests; 24 strict Python complete-state profiles and
  permanent corruption controls now expose it. Four compiled wrong-intent
  source changes fail identity, and actual saturating Python subtraction
  has a new saved live/restored corpus mismatch. Evidence/review:
  `notes/lean-forwarder.md` and its matching report. Ordinary parser/action/
  table/extern assembly remains explicitly unverified; no full-pipeline
  theorem is implied. Next work is active in `work/forwarder-action`, based
  on committed `f1493d8`. The target-only unshadowed field adapter is now
  integrated from `0da36db` at `77b9890`, preserving other modeled
  action-shadowed roots and the old APIs. Its four audited roots, mixed-layer
  witness and narrow false-conclusion challenge are independently reviewed:
  `notes/field-action-writes.md` and its matching report.
  The reviewed next plan `notes/forwarder-action-next.md` targets actual
  selected table-action execution: an unshadowed block-write bridge, exact
  old-destination/TTL-wrap policy, and action-layer restoration in eleven
  transitions. Implement it against the committed real port interface;
  it does not prove table selection, checksum or complete forwarding.
  The small operational root prerequisite is independently reviewed and
  committed at `01d8b09`: actual active-map absence permits a block write
  without dropping action storage; action-hit reads/writes prefer and change
  only that layer. The old BlockFrame API remains a corollary. A constructive
  active witness, four new default audits and eight native controls accompany
  four compiling actual-frame faults rejected by the proofs. This does not
  broaden source permissions or prove an action body/return. Scope/review:
  `notes/action-root-writes.md` and its matching independent report.
  Its proof-only flat-suffix prerequisite (`ea87e2f`/`5d706de`) is integrated
  at `45fe743`: the same command induction now retains the exact pending
  suffix/continuation and full source/noninterference facts. Old whole-body
  signatures are derived unchanged; no AST, runtime or wrapper changes.
  Independent review is clear, four audit roots have only standard axioms,
  16 native boundaries and isolated 564 required checks pass. False consumed-
  suffix/admin-step proofs are rejected; an actual compiled executor fault
  also produces a clean live/restored mismatch on the existing dependent-next
  bundle (not an extra distinct witness). Combined local gates pass above;
  the separately corrected certificate-cleanup failure is recorded above. Scope:
  `notes/command-prefix.md`, `notes/reviews/command-prefix.md`.

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

- **Interchange has scoped leaf/Expr proofs, not a verified program codec.**
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
  Expr implementation `cb68f91`/`2226ebe`/`858f82a` is integrated at `e2f2849`.
  The actual decoder uses well-founded recursion over finite JSON, with
  arbitrary-input helper erasure/unfolding laws and a universal representable
  Expr roundtrip. No parallel proof-only decoder or fuel cutoff is involved;
  wire representability deliberately includes semantically invalid syntax.
  Fifty-nine pre-refactor transcripts preserve exact output/errors/status.
  Paired index remapping and an actual shared NOT/NEGATE name-table fault
  pass roundtrip proofs, but independent decoded-constructor answers reject
  them. The shared operator fault initially survived all tests, prompting
  an observer fix and native anchor. Five full raw mismatches replay restored;
  subprocess failures retain inputs before failing. Review is clear:
  `notes/reviews/expr-codec.md`; recipes/scope: `notes/expr-codec.md`.
  LValue/Arg increment `58051cc`/`8f3fa77` is integrated at `b868100`:
  actual LValue decoding is total with the old-body unfolding law, and every
  representable LValue/Arg roundtrip uses the production codecs. Arg needed
  no implementation change. All 69 original transcripts preserve exact bytes,
  errors and status. Paired operand/argument-label faults preserve roundtrip
  proofs and encoded wires but fail independent constructor/error answers;
  ten raw faults replay restored. Review is clear, isolated full/required
  gates pass; combined integration is checked separately above. Scope:
  `notes/lvalue-codec.md`, `notes/reviews/lvalue-codec.md`.
  Statement arrays are now integrated from `work/stmt-codec`,
  based on committed `1d1168c`. There is no mutual decoder recursion: only
  conditional branch lists recurse into Stmt. An independently checked
  unregistered probe proves attached-array traversal erasure, field bounds,
  repeated-field erasure and generic array roundtrip. Plan and review:
  `notes/stmt-codec-plan.md`, `notes/reviews/stmt-codec-plan.md`; probe:
  `ir/StmtCodecProbe.lean`. The production decoder now uses those bounded
  helpers, with erasure preserving the old ordinary-helper recurrence.
  Independently reviewed baseline `5cbbc85` is integrated at `8f62b31`:
  direct constructor observations, 28 canonical, 42 malformed/order and nine
  normalization requests, with four native anchors. All 79 source-matched
  raw transcripts are retained/replayed; old source hashes are pinned to
  `5cbbc85`, not expected to equal future refactored files. Reproduction
  refuses a changed old decoder or overwriting retained evidence. Scope:
  `notes/stmt-codec.md`, `notes/reviews/stmt-codec-baseline.md`.
  Totality, original-body unfolding and universal statement roundtrip
  (`dcbcf96`/`4564b66`/`70ef3e8`) are independently reviewed and integrated
  at `dcbf392`. Eight new audited roots, constructive all-constructor witnesses
  and overflow controls accompany the proof. All 79 old transcripts remain
  byte-identical; six compiling challenges distinguish proof kills from
  paired mapping/default/diagnostic faults that retain roundtrip proofs.
  All 25 retained live observations (20 distinct inputs) match tracked
  fixtures and replay restored. Evidence: `notes/stmt-codec.md`; final review:
  `notes/reviews/stmt-codec.md`. The next declaration slice has an accepted,
  independently checked plan/probe: `notes/program-codec-next.md` and its
  matching review, with `ir/DeclarationCodecProbe.lean` left unregistered.
  The separately reviewed baseline `21b0fec` is integrated: 247 exact raw
  transcripts, 102 public protobuf successes, 145 errors and 14 native anchors.
  Nine universal laws and ten audit roots are integrated at `20ce06f`, with
  production codec bytes unchanged. A one-sided encoder reversal is rejected
  by its law; three paired/order faults preserve all roundtrip proofs but
  fail 24 independent raw observations. Deliberately corrupting either Python
  expectations or the Lean observer hides the Direction fault from Python
  checks, while independent native anchors still reject it. Faulty packet
  preflight is explicitly not counted as direct codec detection. Scope and
  final review: `notes/declaration-codec.md` and its matching report.
  The next four-law table slice is independently planned/reviewed in
  `notes/table-codec-next.md`, with an unregistered three-law feasibility
  probe and six actual missing/null/empty-action kernel anchors. It is active
  in `work/table-codec` at `/Users/qobilidop/my/work/p4blo-table-codec`, based
  on `58bb072`; freeze independent baselines before the four production laws.
  Full Program remains a later obligation.
  Text parsing, semantic-version policy, whole-program codecs and general
  runtime resource limits remain separate obligations.

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
