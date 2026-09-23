# Actual body-parametric call entry

2026-09-23; based on committed `ac69759`. Implements checkpoint 1 of
[call-body-prefix-plan.md](call-body-prefix-plan.md), not body-prefix execution.

## Real indexed identity, one set of proofs

`CallEntry.WithBody` parameterizes the selected RewriteBody block, program,
actual `Index.build`, looked-up scope and all declaration/zero/initialization
proofs by an arbitrary `List Stmt`. Statement syntax is retained verbatim in
the indexed block **and** its scope.block. Kernel theorems establish successful
actual build, exact block/scope lookup, scope.block identity, unchanged variable
declarations and actual Frame.forBlock initialization for every body. The
index still checks names only; none of this validates the body's statements.

The old empty-body names specialize this single family at `[]`. Existing
theorem types/source APIs and exporter behavior are retained; proof aliases
delegate rather than duplicate their proof. `source_entry_with_body` reuses the
same actual fixed-four-argument dispatch/entry lemmas and the once-generalized
initialization witness. `source_entry` is its original empty-body theorem
signature with a one-line specialization. No second binder or interpreter and
no arbitrary whole-correctness callback is introduced.

The public entry result quantifies arbitrary source hdr/meta/route data,
observer Value, caller Run and continuation. Its index-equality premise names
the **actual body-bearing built index**, not the old empty-body one. Actual
caller lookups and caller BlockFrame remain explicit premises. Initialization
is discharged from the real declarations and zero facts, including extras.
The exact resulting whole Run changes only its frame; queue is exactly
`runBlock actualBlock :: blockReturn originalCaller actualParams args :: K`.
The callee scope contains that same actualBlock. Scratch and unrelated remain
zero; observer is the entire caller input. No initializer, body, observer,
return or continuation has executed. Arbitrary observer Value is preserved,
not implicitly proved to have type H.

Confidence is high in this bounded identity/entry contract, medium in retaining
a fixed body-parametric declaration family as the best future API. Body
parameterization checked directly without changing the binder or repeating
the proofs. Revisit when a second real call signature needs reuse; retain the
concrete built-index obligations. No new global-validity, packet/caller,
initialization-sequence, parser, copyback, failure-unwind or whole-program
correctness claim follows. Next is the separately scoped real local-assignment
and guarded flat-body prefix composition, not execution of this observer.

## The actual selected guarded wrapper

`CallBodyEntry` supplies the complete selected body: scratch:=19,
unrelated:=165, guardedForward.lower and 17 actual observation assignments.
The observation expressions include both exact identity-mux validity reads,
casts, names, widths and order from the tracked guarded wrapper. This module
records syntax; no theorem claims that the observer implements a specification.

The new `callBodyEntry` default exporter emits its actual-built selected
program, exact args and twelve actual single-step snapshots: empty body,
guarded body and intentionally faulting body, each for every validity pair.
The concrete kernel witness is universal in body and validity pair; native
answers separately check pending actual block/scope identity, original caller,
zero locals, nonzero asymmetric observer and absence of faults.

`tests/test_lean_call_body_entry.py` rebuilds the **real tracked**
`guarded_program` wrapper using the separate guardedForward syntax exporter.
It compares the complete selected protobuf Block, with no body projection:
both initializers, guarded command and entire observer must match exactly.
Nominal declaration order alone is ignored; exact ordered fields, declarations
and args remain checked. Thus this is not a second disconnected declaration
fixture. It is an executable complete selected-body identity check, not a
kernel wire/full-program/caller-construction theorem. The selected program
contains only this body-bearing block and its types, not the whole packet
wrapper. Existing guarded-policy proofs/independent answers establish the
authored command's intent separately from this syntax comparison.

The Python runtime test reuses the independently reviewed immutable entry
observer at actual `run_block` entry: real binder/initializer execute, body
does not. Frozen caller/index/shared contents are checked, not only object
identity. The new native snapshots check complete pending block syntax and
source values using independent constructor answers. Bool/int distinctions,
exact keys and complete unique profile/validity sets are checked explicitly.

Permanent negatives reject omitted/changed initializers, removed/reordered/
same-width-wrong-field observers, empty body, wrong pending queue body,
corrupted observer, zero-as-Bool, Bool-as-int, duplicate/missing snapshots.
These are identity/known-answer checks, not claimed packet-level DRT.

## Gates and adversarial record

Clean baseline and candidate both-package/default-audit/native gates pass.
Combined new/existing entry Python suites: 41 passed. The previous callEntry
export remains byte-identical (11649 bytes), independently compared with the
integrator's baseline and our pre-refactor capture:
SHA256 `b81ffabafa5375d95be65a7a0b56d85485eac9e014b24a2ff47784caf50f87b2`.
Candidate baseline files are ignored under `.artifacts/body-entry-baseline/`;
reconstruct by building parent `ac69759` and running `callEntry`.

Six new default audit roots cover arbitrary-body build, block lookup,
scope.block, initialization, public source entry and concrete application;
all have exactly `[propext, Classical.choice, Quot.sound]`. Existing empty
audit roots remain unchanged. Ruff/format/Pyright checks pass. Required real-
Lean gate: **607 passed**, 1462 deselected, no skips, exit 0. Candidate logs:
`/tmp/p4blo-body-entry-{baseline,family,source,lean,focused,drt}.log`.
Final independent review is **CLEAR**:
[reviews/body-parametric-entry.md](reviews/body-parametric-entry.md). The
reviewer independently ran the 41 combined tests, native suites and six
audit queries, checked arbitrary-body/empty alias equations, verified the
old exporter and restored new exporter/source bytes, and inspected each
campaign. The integrator copies the independently owned review report.

### Isolated faults

The candidate was never mutated. A separate worktree `p4blo-body-entry-mutants`
at `ac69759` received the candidate files and a clean two-package/default/
native build; no old caches were copied. Three separate actual source edits:

1. In `CallEntryDeclarations.WithBody.index`, replace
   `Index.build (program body)` with `Index.build (program (body.take 0))`.
   This retains the arbitrary body parameter while using an empty-body index.
   Building `P4blo.CallEntryDeclarations` exits 1 with genuine unsolved actual
   build, block-lookup and scope.block equations. This is **proof rejection**,
   not a runtime test detecting interpreter disagreement. No out-of-memory,
   timeout or missing-parameter elaboration failure is counted as a kill.
2. Restore the Index, then change `CallBodyEntry.initializers`' actual scratch
   literal from 19 to 20. Full default build and audits pass: the generic entry
   proof correctly permits arbitrary pending bodies. The complete selected-
   body test exits 1 at `complete selected body differs` against the unchanged
   tracked Python guarded wrapper. This is a **compiled wrong-intent syntax
   identity kill**, not a packet differential mismatch.
3. Restore scratch, then make the actual observer's `dst` entry read header
   `src` instead of `dst`, both width 48. Again the full default build/audits
   pass, and the independent complete-body test exits 1. This tests a
   well-typed but wrong observer mapping without changing paired declaration
   widths. Permanent corrupted-export cases additionally cover missing,
   reordered and malformed observations and strict snapshot representations.

For fault 1, from the mutant's lean directory run the pinned environment:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.CallEntryDeclarations
```

For faults 2/3, build normal default targets from lean and run the exact
tracked reconstruction/check from the repository working directory:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build
# Repository working directory for the next command:
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_lean_call_body_entry.py::test_lean_agrees_on_complete_call_body -q
```

Temporary logs `/tmp/p4blo-body-entry-mutant-` record `baseline.log`,
`empty-index.log`, `local-build.log`, `local-test.log`, `observer-build.log`,
`observer-test.log`, `restored-build.log` and `restored-focused.log`.
Mutated declaration/observer sources were restored byte-identical to the
untouched candidate. Restored both-package/default/native gates exit 0;
combined new/existing entry tests pass all 41, exit 0. The old callEntry bytes
again equal the integrator baseline. Restored new callBodyEntry bytes equal
the candidate, SHA256
`da016fb8436517a04b1c55eca15ace874124c83589ab9d89a85a3daeaa5c1318`.
Both actual IR and Python runtime source diffs remain empty.

No production IR/Python runtime changed; no packet mismatch replay is claimed
for entry snapshots or declaration identity tests. Any future runtime fault
with packet-level disagreement must save/live-replay/restore the complete
input separately. Full integration/schema/oracle gates remain root-owned.
