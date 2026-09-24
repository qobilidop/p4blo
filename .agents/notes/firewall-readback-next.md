# Actual firewall two-read prefix

2026-09-23. Continue the reviewed insertion boundary from `3372d45`, using
committed main interfaces at `25064ab`. Worktree: `p4blo-firewall-readback`,
branch `work/firewall-readback`. Runtime, actual Program and golden stay fixed.
The independent design review (`notes/reviews/firewall-readback-next.md`, archived) specifies
the exact scope, storage cases, observations and adversarial acceptance.

Prove four actual machine transitions from `.statements checkBloom :: K` to
the existing conditional still pending before K. Include an explicit first
read/copy-back boundary and a constructive initialized-frame instance. This
is not a decision, drop action, hash, control or whole-pipeline theorem.
Each call resolves the actual index/instance/method, zero-initializes the out
argument, evaluates the actual position, reads the actual register and copies
back into the correct action-first storage. Destination existence is required;
its old value need not be well typed. Support all four destination-layer pairs
and independent position shadows, without evaluator/write-success callbacks.

The independent cell answer is an existing natural cell modulo two, or zero
out of bounds. Prove agreement with actual Bits.wrap 1. Noncanonical natural
cells are native-only; never bypass Python Bits invariants. Preserve full Run
with exact ordered register-map reinsertions and appropriate frame updates,
then derive pointwise extern and unrelated-root preservation. Do not assume
structural extern-map identity just because a read leaves its cells unchanged.

Python must observe complete detached state after actual call_extern returns,
not merely after Register.call before copy-back. Supply intended positions
and destination layers independently; never call Env.read for expected values.
Compare both intermediate and final complete state, with normal completion,
exact call counts/order and retained pending native continuation. Include
zero/one/asymmetric/OOB cases, raw 2/3/7 native cells, old wrong-type destinations
and absent-destination failure controls. Challenge wrong returns/positions,
omitted or wrong-layer copy-back, reordered calls, wrapping, read side effects
and the previously discovered position-alias expectation coupling.

Require default axiom audits, constructive witnesses, both package gates before
consumers, independent native/Python answers, actual compiling source/runtime
faults in a separate worktree, exact restoration and independent read-only
review. Internal Env-only failures are not fabricated packet DRT mismatches.
Retain any genuine packet mismatch before assertion and deduplicate its full
input/configuration against all retained evidence recursively.

Confidence: high in the semantic boundary and storage lemmas, medium in the
application-local helper surface. Revisit generalization only for the later
decision/drop client. Initial unregistered feasibility work compiles a generic
actual read/copy-back lemma using explicit action-first setRoot and the existing
operational root-write laws (`/tmp/p4blo-readback-call-final.log`, exit 0).
The probe is not yet the two-read theorem or a registered assurance claim.
Its early record-layout and monadic simplification failures were development
issues, not deliberate fault detections; no runtime or limit change fixed them.
