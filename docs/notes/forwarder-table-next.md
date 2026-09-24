# Next forwarder proof: bounded real table application

2026-09-23. Design investigation at committed `783cbba`, after the exact
selected-action result in `ForwarderAction`. This is a plan, not completed
table/application coverage. Only this note and its unregistered feasibility
probe change; runtime, Program, goldens and registered tests are untouched.

## Smallest useful next result

Prove real `applyTable "ipv4_lpm" none` for a small **actual-installed** IPv4
route family, then lift it to the first conditional of the actual MyIngress
body, leaving its checksum conditional pending. This closes route selection
and default execution for a useful bounded configuration, rather than adding
another theorem that assumes a selected action is correct.

Keep the current program exactly: IPv4 validity alone guards application;
Ethernet validity and TTL do not guard it; TTL0 wraps on forwarding; source
MAC gets old destination; prior drop is not cleared; checksum remains old
at this prefix. Do not substitute the synthetic guarded-forwarding policy.

Start with these five installation sequences:

- no entries;
- `10.0.2.0/24` only;
- `10.0.2.2/32` only;
- `/24` then `/32`;
- `/32` then `/24`.

Each route has independent arbitrary fitting destination-MAC and port data
(`Fin (2^48)` and `Fin 512`). The query is every `Fin (2^32)`, not just packet
examples. Define selection independently using equality with `0x0a000202`
and the numeric interval `[0x0a000200, 0x0a000300)`, preferring the host route
when present. Do not call `Installed.lookup`, `keyValueMatches`, `beats`,
authored accessors or the executor from that source decision.

Cover three actual host default choices: absent (the program's `drop`),
explicit `NoAction`, and explicit `ipv4_forward` with separate arbitrary
fitting data. A default forwarding action is still a **miss**, not a hit.
The bounded family is a deliberate first checkpoint, not a general LPM
theorem for arbitrary prefixes, route lists, mixed keys or ternary tables.

## Existing semantics that constrain the proof

`Installed.build Forwarder.index (some host)` checks the actual declaration,
key widths/canonicality, zero nonternary priority, duplicate prefixes, action
membership, directionless literal arity/width/range. It also installs the real
default. Prove this build succeeds and characterize its complete relevant
maps; do not silently take a `getD` fallback or manually fabricate the public
installed witness. `Forwarder.index_built`, actual scope and initialization
already provide the other constructive premises.

`Installed.lookup` scans the entry array, replacing the current best only
when a matching entry has a strictly longer prefix. Thus both install orders
must give the same selected route. Equal canonical prefixes are rejected at
installation; they are not an application tie-breaking policy. Explicitly
test duplicate `/24` and `/32`, noncanonical `/24`, prefix33, wrong key arity,
nonzero priority, wrong action/parameter width and an unknown scoped table.

The two indexes are separate values: `Run.index` and `Installed.index` must
both be the real Forwarder index. The table is looked up through the current
frame scope, while installed lookup uses `(frame.block.name, table.name)`.
Retain actual scope/block identity, not just a table with the same key list.

Actual `Execution.dispatch (.table name target)` evaluates keys once,
requires entries, runs lookup, then queues the optional selected action
followed by `.writeHit target match.hit`. Even `target = none` still leaves
a writeHit administrative step. Action return and writeHit are success-only.
The public Python counterpart is `stmt.apply`, not a test-created call to
`run_action_call` that bypasses selection.

Distinguish three defaults precisely:

- absent host override keeps the actual program's explicit drop;
- explicit `NoAction` invokes a real empty action, with entry/return steps;
- runtime `Match.action = none` invokes no action at all.

The third case is representable in generic table semantics but cannot be
produced by valid host configuration of this unchanged Forwarder. `setDefault
none` restores its drop; it does not remove it. Keep an optional-action
dispatch lemma/control separate, without pretending it has a constructive
original-program installation witness. No Program change to force that case.

## Three review-sized implementation checkpoints

1. **Installation and selection.** A small source configuration/decision
   type and raw IR entry builder, actual-build success, exact table/key/map
   identity, universal independent selection theorem for every address and
   route-data value in the bounded family, both orderings. Separate matching
   arithmetic from array-fold reasoning. `/0` catch-all and max-address `/32`
   should have independent operational controls, but arbitrary-prefix and
   arbitrary-list proofs can wait. Installation negatives are executable
   evidence unless separately proved; do not imply validator completeness.
2. **Actual application.** Prove real key evaluation from full source
   `FrameMatches`; use the proved selection theorem, not a lookup-correctness
   callback. Reuse `ForwarderAction.source_steps` for forwarding. Add the
   actual one-assignment drop action and empty NoAction normal-return laws.
   Compose table dispatch, selected action and writeHit to exact arbitrary
   `K`, then derive the actual public `applyTable` result for `K=[]` using
   existing `Finishes.sound`. Keep the outer action-free frame premise;
   active action layers remain governed by the committed action theorem.
3. **Real ingress prefix.** Start with `.statements Forwarder.ingress.body`
   and finish with `.statements [actualChecksumConditional] :: K`, including
   the real empty-branch-list pop. Invalid IPv4 does not inspect or require
   installed entries and preserves the entire Run; valid IPv4 uses the
   bounded installation contract. The second actual conditional remains
   untouched even after default drop. Prove exact syntax decomposition by
   `rfl`; never replace the body with an equivalent simplified program.

The final application result should specify complete source state using the
independent `ForwarderAction.Snapshot`: forward invokes its independent policy;
drop changes only drop to true; NoAction is identity. Hit is a separate source
decision field. Exact Run formulas retain actual ordered map inserts, scope,
original action layers, installed entries, externs, packet, emitter and visits;
outside names are preserved. Do not assert structural map equality to a
fresh reconstruction when only the operational insert sequence is justified.

The literal transition expectations starting at `.table ...` are 13 for
forward, 7 for drop and 5 for explicit NoAction (2 for optional absent action
in the separate lower-level control). From the actual first-conditional list
entry through its branch pop, expect 18/12/10, or 3 for invalid IPv4. Derive
these again from actual queues during implementation; `Execution.Steps` is
unindexed, so distinguish explicit proof chains/native counts from a numeric
theorem conclusion. One transition short must retain writeHit for application,
and the branch-pop boundary for the lifted prefix.

## Independent executable acceptance

Build native fixtures from the real Index.build, Frame.forBlock and
Installed.build. Observe the entire before/after Run using the existing
complete map/state helpers, retaining asymmetric nonzero source fields,
both validities, prior drop, TTL0/1/255, checksum, nonempty installed state,
packet cursor/payload, emitter, extern cells, visits and unrelated block vars.
Inspect exact pending `K` and a subsequent genuinely modifying/faulting `K`.

Boundary addresses include just below network, network base, host-1, host,
host+1, network end-1, network end, zero and `2^32-1`. Compare every profile
to an independently named expected winner/hit/action-data record, not merely
to another maximum-prefix implementation. Use distinct MACs/ports for the two
routes and forwarding default. Preserve a literal actual Program/table/key/
action/first-conditional anchor and all previous exporter bytes.

Python runs real `InstalledEntries.build` and `stmt.apply` normally. Delegating
hooks record actual key evaluation count/value (exactly one), selected call,
full active action state, restored outer state and completion. Expected state
is detached/type-sensitive and computed before runtime effects. Compare complete
installed maps before and after, not just the chosen action. Snapshot the full
state after each observed stage; a later write must not repair an earlier
corruption unnoticed. Validate the exporter once per module, with a separately
callable full checker for malformed JSON/case/count/binding/type negatives.

The original apply has no hit target. Add a clearly labeled lower-level
operational control `.apply "ipv4_lpm" (some Forwarder.dropFlag.lvalue)`:
on a default-drop miss, drop first becomes true, then hit overwrites it false.
This distinguishes hit-after-action order and exact false-on-default behavior;
it is not the unchanged original body. A throwing selected-action control
must skip hit writes; for example, manually supply a wrong-arity action entry
to the lower-level runtime. Label that fixture installer-rejected, not a valid
host configuration, and keep it outside the successful application theorem.

Adversarial acceptance must distinguish:

- actual lookup first-match / shortest-prefix / reversed `beats` edits;
- wrong key field (`ipSrc` instead of `ipDst`), chosen action/data or host
  order in an authored fixture that still satisfies generic action proofs;
- treating default execution as hit, ignoring host default, or conflating
  explicit NoAction with absent optional action;
- skipped/early hit write, duplicate key evaluation, or read-side mutation
  of sibling/validity/shared/installed state with an unchanged selected call;
- reintroduced full-outer restoration or active-layer leakage;
- a paired source-policy/fixture error challenged by literal address/winner
  anchors and original corpus packet outputs.

At least one actual compiling Python lookup/default fault must fail the
strong internal observer and create a clean packet mismatch on the unchanged
Program with an explicit overlapping-route or miss configuration. Save the
complete real request before independent answer assertions; replay live and
restored. Preserve ProtocolError reports, strict JSON and nonempty case-set
guards. Runtime errors alone, proof rejection, wrong-intent fixture rejection,
and genuine semantic DRT mismatch are separate evidence categories. Reusing
an existing exact input is fine but is not an additional distinct witness.

Use the existing immutable BMv2 image for a small overlap/order/default packet
profile when available. P4-SpecTec's adapter maps LPM length into priority;
agreement there is not independent evidence for longest-prefix selection.
No Docker builds/global cleanup or silently weakened unavailable-oracle gate.

## Feasibility evidence and decisions

The unregistered `probes/ForwarderTable.lean` uses the unchanged real Forwarder
index. It checks actual successful installation in both orders and literal
host/network/miss lookup answers with fixed route payloads. Its separate
arithmetic lemma connects the runtime `/24` shift test to the independent
numeric interval for every natural query reduced modulo `2^32`. Build-success
equations establish that the probe's `getD` fallback is never used. This is
not a registered production application proof or Python assurance.

An attempted symbolic full-lookup proof reduced the real two-entry loop by
`simp` and arithmetic case splits, but the resulting term hit the kernel's
recursion limit at 4096 and 8192. A larger-limit exploration was stopped after
roughly 75 seconds, not counted as success. The final probe contains no
incomplete full-lookup theorem or admitted proof. The next implementation
must factor small actual monadic/array step equations before composing them;
simple giant unfolding is not yet a demonstrated scalable proof strategy.
All-address selection, reverse-order symbolic lookup, arbitrary route data,
remaining installation shapes/defaults and application execution remain the
planned obligations, not facts established by this probe.

Confidence: high in the concrete selection/action composition and default
distinctions; medium in full-lookup proof engineering and keeping a five-shape
installation family as the most useful lasting interface. Revisit generic
finite-route maximum/installation
invariants when a second routing configuration needs another prefix family,
not by hiding lookup correctness in a premise. If symbolic payload build
proofs grow disproportionately, split actual install lemmas from lookup rather
than freeze all payloads or weaken the all-address contract without review.

No new syntax, second interpreter, fuel semantics, table authoring framework,
ternary theorem, arbitrary-list LPM, parser/checksum/architecture fate, whole
ingress completion, whole-program validity or universal Python equivalence
is claimed. General schema codec work is orthogonal and owned separately.

## Checked investigation and handoff

From this worktree's `lean/` working directory, against fresh build caches:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.ForwarderAction
nix develop -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true /Users/qobilidop/my/work/p4blo-forwarder-table-next/docs/notes/probes/ForwarderTable.lean
```

Both commands exited 0. Logs: `/tmp/p4blo-forwarder-table-probe-deps.log`
and `/tmp/p4blo-forwarder-table-probe-final.log`. All seven printed roots have
exactly `[propext, Classical.choice, Quot.sound]`. No production source,
default audit or test registration changes, no runtime mutation, no Docker
operation and no Python/full-gate result are part of this design checkpoint.
The probe is intentionally unregistered; the exact command above reruns it.
Independent architecture review is **CLEAR** for this plan/probe checkpoint:
`docs/notes/reviews/forwarder-table-next.md`. The reviewer independently ran
the pinned probe with warnings as errors (exit 0, all seven exact standard
axiom sets), checked actual Tables/Exec/Python apply behavior and literal
queue counts, and accepted the explicit remaining symbolic-proof risk. This
is design clearance, not implementation-theorem clearance.
