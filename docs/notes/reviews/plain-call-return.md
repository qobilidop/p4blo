# Normal plain-root call-return review

Final review: clear; chronological investigation follows below.

2026-09-23. Independent read-only review of all candidate files in
`/Users/qobilidop/my/work/p4blo-plain-call-return` against `ac69759`, following
the committed normal-return plan. No candidate source edits or rebuilds by
reviewer; execution began only after the owner released stable binaries.

## Exact operational boundary

The core reduces the existing copyBack loop for the actual fixed params/args,
not a second executor. The three callee reads supply arbitrary operational
Values. Caller BlockFrame and three existing original caller bindings are
explicit sufficient premises for writeVar_block. Input route has no read or
write premise. There is no hidden Index, global argument typing, reachability,
callee action compatibility or whole-copyback callback assumption.

dispatch_return captures the current callee frame, restores the saved caller
frame and performs its three root writes. The exact result preserves the
current callee-after Run's entire non-frame state, not an old entry Run.
Separate one-step and Steps laws leave arbitrary continuation pending and
explicitly require normal, nonfaulted machine state. Scope/action absence and
every outside lookup/absence follow from the closed returnedFrame expression.
This is neither a body/observer theorem nor fault-unwind/rollback correctness.

Ordered loop reduction is checked against actual copyBack. Since the three
distinct final inserts commute, final-state equality alone is not an order
trace theorem; the note recognizes that limit, and the Python delegating spy
independently requires source_hdr, source_meta, hdr in order.

## Fixtures and observation boundaries

Arbitrary-value native cases cover absent input route and required binding
failures without incorrectly asserting global validity. The constructive
aggregate witness reuses the real-built callee declarations and all four
validity pairs. Operational destination decoys make a skipped frame restore
an observable wrong-success case rather than only an early missing-name error.
Current packet/emitter/register/entries/visits differ from the old fixture;
installed entries are nonempty and caller/callee values asymmetric.

Strict native snapshots compare complete map/index/scope/frame/shared-state
projections with independently constructed Python values. Compound keys use
unambiguous JSON pair encoding. Expected Python snapshots and entire index /
scope dataclasses are detached before actual copy_back; identities are only
additional checks. Callee route omission/value and caller route/scratch/
unrelated preservation are independently exercised. These are boundary known
answers, not packet-level DRT or a proof of Python equivalence.

## Independently reproduced alias survivors

The original follow-up mutation wrote only source_hdr.ethernet.dst. Read-only
process-local probes delegated to actual copy_back, then individually aliased:

- returned source_meta to callee meta;
- returned hdr to callee observer;
- returned Headers' IPv4 member to the callee's IPv4 member.

Each probe hit exactly once and passed the entire original observer, including
strict snapshots and the Ethernet follow-up. Baseline focused tests also
passed all 37. This is a real test-coverage gap, not a theorem failure: value
equality cannot expose those selective mutable aliases until a relevant later
mutation or explicit isolation check occurs. Requested member-write checks
across every aggregate branch plus recursive mutable-container/list
detachment, with permanent selective-alias regressions. The implementer owns
the tests-only correction; final results follow below.

## Independent checks already executed

- Fresh pinned queries: all eight generic and one concrete audit roots have
  exactly `[propext, Classical.choice, Quot.sound]`.
- Fresh four-case native aggregate run and full compiled userTests exit 0.
- Full compiled specification test driver exits 0, including six new return
  checks. No independent uncached build is claimed.
- Initial focused Python file: 37 passed, exit 0 (0.34 s), before the new
  selective-alias correction.

Final restoration logs, correction and final disposition will be appended.

## Final correction and evidence review

The observer now collects every mutable Struct/Header object and fields-list
identity across all three copied values and all three original callee values,
and requires the sets disjoint. Immutable leaf sharing remains allowed; this
fixture check does not claim Stack or cyclic object coverage. Subsequent real
member writes exercise Ethernet, IPv4, Metadata and H.Result independently,
checking the complete expected caller and frozen callee after each mutation.
All three selective aliases and a shared-fields-list fault are permanent
regressions. Independently reran the exact three earlier survivor probes:
each now fails at the intended mutable-container isolation assertion, after
one actual delegated copyback. Final focused file: **41 passed**, exit 0
(0.36 s). No Lean or production runtime change was required.

Inspected four actual Exec mutation pairs: each actual runtime module builds,
then correspondence rejects wrong destination, skipped restoration, input
copyback or cleared current visits. The skipped-restoration log includes
unused-simp diagnostics only after the genuine unequal-Run failure. These
are proof rejections, not falsely counted native semantic tests. Separately
inspected the actual Python cursor-source fault's four executed whole-state
failures, the surviving declaration control, and restored 37-test gate from
that earlier checkpoint. The later tests-only refinement accounts for the
new final count. The paired exported argument/result remapping is correctly
labeled a retained independent fixture challenge, not an actual compiled
proof-surviving source mutant.

Restored Exec.lean and stmt.py hashes independently match the note and their
runtime diffs are empty. Full independent native spec execution contains
494 successful checks. Registrations preserve package layering and require
the exporter/default audits. Whitespace check passes. Owner's repeated
607-case required runs and full two-package builds are attributed; combined
integration gates remain the parent's responsibility.

No remaining blocking finding. Clear for the fixed-profile normal-return
theorem, constructive witnesses and boundary tests. Python direct copy_back
observations still do not prove Lean frame restoration by themselves, and
the checkpoint makes no reachability, whole-wrapper, parser/action or
fault-unwind claim.
