# Statement-codec feasibility review

2026-09-23. Clear for the proposed implementation slice, not a completed
statement codec proof. Root independently read the entire plan and probe from
`work/stmt-codec-plan` at baseline `fddab8e`, then checked them against the
actual production helpers, Stmt decoder/encoder and generated recursor.

The only recursive decoder calls are the two conditional branch lists.
The attached-array traversal erases to the actual indexed Except traversal,
including callback errors; the accumulator-generalized induction preserves
its index progression. Repeated-field erasure includes missing/null fields,
non-object payloads and non-array failures. Its strict enclosing bound is
sufficient for the actual oneof payload; no synthesized array default is
mistaken for a child. Ordinary message defaults remain unchanged.

The generic array roundtrip has an explicit per-member, all-path premise.
The plan correctly requires discharging it with actual argument laws or
statement induction, not exposing a whole-statement correctness assumption
in the public result. The printed Stmt/List recursor supports that induction.
All fourteen constructors and their representability restrictions match the
current encoder. No semantic validity restriction is smuggled into the wire
profile; totality and physical resource limits are kept separate.

Independently ran the absolute unregistered probe with pinned
`lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true` from main's IR
package using its already-built dependencies: exit 0. No native executable
was rebuilt. Log: `/tmp/p4blo-stmt-plan-independent-probe.log`. Six fresh audit
queries have only standard axioms or subsets; the four actual-old-decoder
observations agree with the recorded first-error/null behavior. They are
runtime observations of the partial decoder, not kernel proofs about it.

Acceptance remains conditional on the implementation work: capture actual
pre-refactor transcripts, prove bounded-helper erasure and the original-body
unfolding law, prove universal representable Stmt roundtrip, independently
anchor constructors/wire/order/errors and exercise compiling paired faults.
The original opaque partial constant cannot serve as a logical equivalence
oracle. Exact old/new transcripts provide bounded compatibility evidence.
No production refactor, full-program law or Python equivalence is claimed.
