# Assurance milestone 1

Accepted 2026-09-23. This is the active completion boundary, superseding the
open-ended proof/application expansion in `implementation.md` and
`verification.md`. It does not change the v0 wire format or announce protobuf
v1. Python and Lean remain the only authoring/interpreter packages in scope.

## Claim

For the documented current IR profile, the independent Python implementation
and executable Lean specification agree across a reproducible conformance
suite, independently checked examples and a reviewed catalogue of intentional
faults. Selected foundational properties are proved in Lean. Remaining trust
boundaries, known divergences and excluded features are explicit.

This is tested conformance, not a proof of Python equivalence. Test/proof counts
and mutation counts are not probabilities of correctness or completeness.

## Frozen scope

Start from the abstract syntax/runtime and v0 schema at `54e3c65`. The exact
supported constructors and P4 exclusions are those in `ir/P4bloIR/IR.lean`,
`ir/proto/p4blo/v0/p4blo.proto`, `docs/semantics.md` and `docs/coverage.md`.
The closeout evidence matrix must identify gaps within that existing surface;
adding new language features, architectures or applications is not required.
Lean is normative for abstract syntax and meaning; protobuf is wire syntax.
Keep wire representability, semantic validity and tested execution separate.

The flagship application scope is the existing complete forwarder and
persistent tutorial Bloom firewall, authored and run in both Python and Lean.
Existing eleven-program corpus and pinned P4 oracle profiles remain regression
gates. Preserve documented oracle disagreements and Bloom false positives;
do not relabel these programs as exact connection tracking or full P4 support.

Lean eDSL guarantees cover its documented typed fragment, not every raw IR
constructor used to assemble applications. Keep substantive existing lowering,
execution and application proofs, but no theorem is required merely because
it is the next composable one.

## Acceptance checklist

- [x] **Scope and trust boundaries:** one concise current profile states
  supported syntax/externs, input assumptions, wire/default/unknown-field
  behavior, error categories, resource limits and exclusions. An unproved
  validator or parser is labeled, not presented as a proved guarantee.
  Delivered in `profile.md` and independently reviewed in
  `notes/reviews/milestone-profile.md`; this checks the scope document, not
  the remaining implementation/release criteria.
- [ ] **Whole-program interchange:** direct independent Export/Program and
  host TableEntries/Entries fixtures cover complete fields, actual public
  Python/protobuf conversions, presence/defaults, malformed inputs and
  representability boundaries. Decode-, validation- or installation-rejected
  host configuration must not execute a packet or mutate persistent state.
  This does not promise transactional rollback after an execution error in
  an accepted program. Existing component evidence remains intact.
  Finish Export/Program proof composition only if straightforward; a difficult
  theorem cannot reopen this milestone or replace independent tests.
- [ ] **Evidence coverage:** a compact feature-to-evidence matrix maps each
  current semantic family to independent tests, generated comparisons,
  applicable oracle evidence and scoped proofs. Close meaningful holes or
  state narrowly justified exclusions; no unexplained implementation mismatch.
- [ ] **Repeatable adversarial acceptance:** select a finite, reviewed fault
  catalogue across Python, Lean, serialization and observers. A documented
  command replays the retained evidence and runs the selected sensitivity
  checks. No unexplained survivor; equivalent mutants and noncompiling setup
  failures are classified separately. Do not require rerunning every historical
  exploratory fault or invent a numerical mutation-score guarantee.
- [x] **Usable authoring paths:** clean-checkout documented commands let a
  new user author/run the two flagship examples in both languages. Review
  diagnostics, imports and API claims; repair concrete rough edges, not a
  speculative syntax redesign or complete frontend verification.
  Delivered in `quickstart.md`, exercised by its six snippet/API tests and
  reviewed in `notes/reviews/milestone-usability.md`. Final combined release
  gates remain a separate unchecked item below.
- [ ] **Final release evidence:** required Python/schema, both Lean/default
  audits/conformance and applicable P4-oracle gates pass on the final revision.
  Reconstruct and replay selected retained artifacts without depending on
  old temporary logs/worktrees. Record exact commands, revisions, reviewed
  exceptions and unresolved external availability separately in a short
  completion report. A skipped required check is not a pass.

The XDP compile-only experiment stays visible with its existing CI checks and
pins, but is not evidence for this milestone's P4 profile. Its current upstream
snapshot outage is reported separately, never silently skipped, disabled or
claimed green. No XDP kernel execution or new eBPF application is required.

## Explicit non-blockers

Universal Python correctness; all-P4 expressiveness or IR minimality proofs;
whole-program validator soundness/completeness or termination; full parser,
checksum, firewall or forwarding-pipeline proofs; general table-family proofs;
new application families; fully verified complete Lean frontend; correctness
of Lean/Python runtimes, compilers, JSON parser or protobuf implementation.

Further firewall readback and guarded-ingress proofs are parked, not release
blockers. Their worktrees and exact unfinished obligations are retained in
`status.md`; they must not be reported as landed guarantees. Already-reviewed
Action/Block codec commits are integrated as closeout, not a new proof ladder.

## Three bounded closeout batches

1. Integrate reviewed Action/Block work and finish the remaining whole-program
   interchange tests; optional simple top-level proof composition.
2. Audit semantic coverage and consolidate a finite reproducible adversarial
   acceptance command; fix demonstrated gaps without expanding the profile.
3. Complete the two-language usability pass, clean-checkout gates and final
   current handoff/report.

Stop when this checklist is satisfied. Put additional improvements in a
separate future backlog rather than automatically extending the milestone.
Do not stop merely at an intermediate commit, and do not claim completion
while a required checkbox or unclassified discrepancy remains.
