# Body-parametric call-entry review

Final review: clear; chronological investigation follows below.

2026-09-23. Independent read-only review of candidate
`/Users/qobilidop/my/work/p4blo-body-parametric-entry` against `ac69759`.
Implementation sources remain owned by the implementer. No candidate rebuild
or source edits were performed by this reviewer.

## Contract and compatibility

The declaration family genuinely calls the existing Index.build on the
body-bearing program. It does not substitute a new runBlock under the old
empty index. Arbitrary-body build success, block lookup, scope lookup,
scope.block identity and unchanged variable declarations are kernel facts.
The total fallback definitions do not hide failure: explicit successful-build
and exact lookup theorems discharge those cases. Successful index construction
still does not imply statement validity, as the deliberately faulting body
illustrates.

The former declaration/nominal/zero/initialization proofs are generalized
once. Empty-body names specialize that family. The actual source-entry proof
is likewise moved to source_entry_with_body; its original signature is a
one-line specialization. The new theorem quantifies arbitrary source data,
observer Value, Run and continuation, retaining actual caller-read, index and
no-action-layer premises. Actual raw dispatch and entry-step lemmas supply the
four binds and exact pending queue, without a new binder or whole-correctness
callback. The whole Run is exactly the caller Run with the bound frame only;
scratch/unrelated remain zero and the observer is preserved. This proves
entry, not local assignment/body/observer execution or copyback.

The selected guarded syntax is the complete twenty-statement block: two
initializing assignments, the authored guarded conditional and seventeen
observer assignments. Ordered fields, type declarations and actual arguments
are compared with the existing tracked Python wrapper. No body projection
remains in this new identity check. The separate guardedForward exporter is
still a source of authored command syntax, not an independent policy oracle;
its already established policy/known-answer tests supply that separate
obligation. The selected program is not claimed identical to the full caller
and packet wrapper.

## Observations and independent checks

Twelve actual one-step snapshots cover empty, selected guarded and faulting
bodies crossed with all four validity pairs. Tests reject extra keys,
incorrect profile/case sets, duplicate/missing cases and non-Boolean case or
fault flags. Independently constructed source/caller values are compared by
type-sensitive canonical JSON. Scope and queued block both retain complete
expected syntax, including the faulting body, and locals/observer demonstrate
that no body has executed. The new JSON snapshot is deliberately narrower
than a full Run: non-frame preservation remains the universal exact-Run
theorem and the reused Python observer's immutable full index/caller/shared
state checks, not a newly claimed complete Lean JSON export.

Independently executed against stable candidate binaries:

- Combined new and existing entry suites: **41 passed**, exit 0 (1.39 s).
- Full compiled userTests: exit 0, including all previous suites and the
  twelve new body-entry answers.
- Fresh pinned Lean query: all six new advertised audit roots have exactly
  `[propext, Classical.choice, Quot.sound]`; fresh native twelve-case run
  succeeds. Additional kernel checks confirm arbitrary block.body identity
  and empty program/scope aliases by reflexivity.
- Fresh callEntry output is byte-identical to both retained pre/post-refactor
  captures: 11649 bytes, SHA256
  `b81ffabafa5375d95be65a7a0b56d85485eac9e014b24a2ff47784caf50f87b2`.
- Default exporter/audit/test-driver/public imports inspected; whitespace
  check passes. No IR or Python production-runtime source changes.

Both package builds/default audits and the 607-case required DRT gate are
implementer-reported checks, not an independent clean build by this reviewer.
Final adversarial/restoration details follow after their completion.

## Final campaign and restoration review

Inspected the completed note and retained actual fault logs. The first fault
builds the actual index using body.take 0 while retaining the arbitrary body
parameter. Its failure contains genuine false build/block/scope equations,
not merely an unused-parameter or syntax failure. This is appropriately
reported as proof rejection, not runtime differential detection.

The actual scratch initializer 19-to-20 edit and same-width observer dst-to-src
edit each pass full default proof/audit builds, then fail the complete selected
body test against the unchanged tracked Python wrapper. Generic entry proofs
should accept both pending bodies: they specify entry, not intended pending
syntax or its execution. These independent compiled syntax-identity kills
therefore close the intended observation gap without overstating a packet
interpreter mismatch. The note supplies exact edits, commands and baseline
reconstruction; no packet replay artifact is incorrectly claimed.

Inspected restored both-package/native success and restored 41-test logs.
Independently compared the two deliberately edited Lean files with the
candidate, exit 0 for each; production IR/Python diffs are empty. Executed
both candidate and restored callBodyEntry exporters: complete stdout bytes
are identical, stderr empty, successful exits. Verified 97269 bytes and SHA256
`da016fb8436517a04b1c55eca15ace874124c83589ab9d89a85a3daeaa5c1318`.

No blocking finding. Clear for this body-parameterized entry checkpoint with
the recorded proof/runtime/syntax distinctions and the integrator's combined
gate obligation. Executing the local assignment prefix, guarded command,
observer, return and continuation remains separate work.
