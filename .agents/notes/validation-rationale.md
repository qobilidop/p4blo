# Validation rationale

[Assurance](../../docs/assurance.md) owns guarantees/exclusions,
[workflows](../../docs/workflows.md) the gates, and
[oracle discrepancies](../../docs/oracle-discrepancies.md) the case dispositions.
These durable reasons and constraints were consolidated on 2026-09-26; this
note authorizes no campaign and does not replace those contracts.

## Oracle interfaces

- **Primary reference** (2026-09-24): P4-SpecTec mechanizes P4; BMv2 independently
  checks CRC/mask defects and simulator limits (real lpm, const/runtime ternary
  priorities, shifts above 2048). Printed P4, block simulation and bridge IL
  give three comparison levels. The governing contract, not an oracle vote,
  decides correctness (2026-09-25).
- **Block visibility** (2026-09-24): pipeline observations hid register cells,
  motivating p4blo.watsup and patch 0001 on explicit headers/metadata/entries/
  extern state. The [oracle guide](../../tests/oracles/README.md) owns the
  protocol and patch-digest build stamps. Families use v1model implementations;
  refuse STF entries needing its name maps until a corpus need exists. Accept
  checked models of exact defects, not tags. Offer upstream when stable; both
  patches may move to p4-spectec-lean, which already forks P4-SpecTec.
- **IL bridge** (2026-09-25): fused controls hid architecture boundaries, so
  patch 0002's instantiated-program import preserves six roles, renames fields
  colliding with intrinsics and rejects native verify_checksum pending
  checksum_error support. Original comparisons account for authored schedules;
  roundtrips test stage structure/state rather than byte identity. The
  [architecture profile](../../docs/arch-supports.md) owns the saved destination/
  pre-egress zero request, with distinct P4-SpecTec outputs retained as exact
  regressions, not architecture-wide exceptions. The frontend is not verified.
- **STF/printer limits** (2026-09-22): the STF module owns the dialect.
  P4-SpecTec needs prefix priorities supplied because it lacks longest-prefix
  selection; BMv2 checks real lpm and priority. Printed ternary entries are not
  const because p4c 1.2.5 rejects const priorities. Const lpm priorities remain
  missing from the printer, so overlaps fail on P4-SpecTec.
- **Independent originals** (corpus 2026-09-22; firewall 2026-09-23): STF-bearing
  p4c cases plus own programs; the unchanged firewall's scoped BMv2 barrier reads
  all 8192 cells, valid for pinned single-ingress FIFO. Revisit before
  recirculation/asynchronous externs. Preserve native inputs; exact strict
  discrepancies need passing controls and vector/status/mismatch matching;
  strict XPASS detects stale exceptions (2026-09-23).

## Verification method

- **Cedar** (2026-09-23): executable model, property proofs, typed generators
  and component comparison, with independent implementations sharing wire syntax
  only; this is not universal equivalence.
- **Coverage rather than counts** (2026-09-24, 2026-09-25): assurance owns Lean
  rule witness pairs, retained coverage/unhit inventory and P4-SpecTec's scope.
  Keep unhit reasons and the shrinking-only Lean exclusion list. Guidance must
  help measurably; the pair-reward term did not and was removed. P4-SpecTec's
  8-dynamic rules/functions and 3-operations functions include builtins, measured
  over corpus/examples/fixed greedy seeds (2026-09-24). Outside calls report
  called_in_scope without enforcement to avoid eight exclusions for unions,
  compound assignment and overload helpers. Regenerate the inventory at pin bumps.
- **Fixed Lean answers** (2026-09-24): [conformance](../../tests/conformance/README.md)
  owns canonical answer/provenance/format-2 contracts and rejected-install,
  unicast/drop/port/egress fixtures. Refresh reanswers tracked inputs, export
  adds them; rejecting stale binaries (Lake no-build, time fallback) prevents
  false provenance. Change the semantic contract before refreshing answers.
- **Replay and mutation** (2026-09-23): workflow replay retains complete programs/
  request sequences from fresh state and hex extern state after every request;
  missing state fails. Both implementations are challenged, survivors retained,
  build failures excluded from semantic kills; the catalogue is finite, not a
  mutation-score guarantee. Generated scalar/typed-expression/stateful/host-change
  campaigns use independent register/counter bounds, type-preserving shrinking,
  reject invalid programs rather than filter them and retain failures under
  .artifacts/drt/. Host changes within a sequence remain Python/Lean-only:
  original BMv2 cannot replace rules mid-sequence. Revisit before claiming
  original-oracle host-change coverage.
- **Independent observation** (2026-09-23): paired faults preserve laws;
  adversarial observer review and independent known answers/constructor anchors
  are necessary even for roundtrips. Total decoders recurse over finite JSON,
  with no proof-only duplicate. Fixed-application checks stay separate from
  generic replay: exact state/numeric contracts supplement packets; exhaust
  named malformed profiles before broad random traffic.
- **Proof scope** (2026-09-24; library split/simplification 2026-09-25): assurance
  owns indexed checker soundness, generic extern/machine/installation premises,
  DECODE versus validity, and open completeness/termination. Architecture tests
  give no soundness/discharge/non-vacuity proof. Runtime deviation theorems stop
  at evaluator meaning, excluding installation/binding/architecture (2026-09-24).
  Axiom audits catch imported axioms/native shortcuts, not wrong theorem intent
  (2026-09-23); --wfail preserves guard_msgs severities while failing warnings
  (adopted from p4-spectec-lean, 2026-09-25).

## Retirement reasons

Lean authoring/application/architecture proofs were retired, not declared correct;
keep Python examples and independent behavior/fault/oracle checks (2026-09-25).
Sources remain at `5ee52d90f19d5d5a81bf972a115298ae167e691b`; recovery owns unique
drafts. Execution certificates packaged bounded reexecution of one example,
adding no general Python correctness claim; ordinary comparison/core proofs
suffice. Revisit only for a concrete checked-execution consumer (2026-09-25).
XDP compilation neither executed upstream nor validated a p4blo application, so
maintenance bought no P4 claim. User-requested retirement has high confidence:
no interpreter/schema dependency. Revisit only for a concrete application and
independent execution oracle; historical files/evidence remain at b7860a5
(2026-09-25).
