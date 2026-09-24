import P4bloIR.Exec

/-!
# Bounded reexecution certificates

The checker reexecutes the actual `Execution.step`, with a budget supplied by
the checker caller. Exhaustion is a separate verdict, never a semantic fault
or `ParserTimeout`. An accepted claim is proved about the actual unbounded
`Execution.drive` on the exact initial machine passed to the checker.

This is a certificate prototype based on reexecution, not a faster execution
engine. It proves only the observation explicitly supplied by the caller; a
projection that omits state or fault tags cannot certify them. It does not
establish termination of all valid programs, correctness of a serializer, or
equivalence with Python. The fixed stateful experiment that exercises it,
whose observation distinguishes success and both fault kinds, lives with
the reference architecture, since it needs concrete externs.
-/

namespace P4bloIR.ExecutionCertificate

inductive Verdict
  | exhausted
  | finished (outcome : Execution.Outcome)

/-- At most `fuel` machine transitions, including the final terminal step. -/
def bounded : Nat → Execution.Machine → Verdict
  | 0, _ => .exhausted
  | fuel + 1, machine =>
    match Execution.step machine with
    | .inl result => .finished result
    | .inr next => bounded fuel next

/-- A finished bounded run gives a finite trace of the actual semantics. -/
theorem bounded_finishes (h : bounded fuel initial = .finished result) :
    Execution.Finishes initial result := by
  induction fuel generalizing initial with
  | zero => cases h
  | succ fuel ih =>
    cases step : Execution.step initial with
    | inl outcome =>
      simp [bounded, step] at h
      exact .done (h ▸ step)
    | inr next =>
      exact .next step (ih (by simpa [bounded, step] using h))

/-- Successful bounded reexecution equals the actual interpreter's runner. -/
theorem bounded_sound (h : bounded fuel initial = .finished result) :
    Execution.drive initial = result :=
  (bounded_finishes h).sound

/-- Check one claimed observation against the complete supplied initial
machine. A semantic fault remains an outcome for `observe` to distinguish. -/
def check {α : Type} [DecidableEq α] (fuel : Nat) (initial : Execution.Machine)
    (observe : Execution.Outcome → α) (claim : α) : Bool :=
  match bounded fuel initial with
  | .exhausted => false
  | .finished result => decide (observe result = claim)

/-- Acceptance binds the fuel, initial machine, observation function, and
claimed result; none is replaced by a seed or omitted replay prefix. -/
theorem check_sound {α : Type} [DecidableEq α]
    (fuel : Nat) (initial : Execution.Machine) (observe : Execution.Outcome → α) (claim : α)
    (accepted : check fuel initial observe claim = true) :
    observe (Execution.drive initial) = claim := by
  cases finished : bounded fuel initial with
  | exhausted => simp [check, finished] at accepted
  | finished result =>
    have observed : observe result = claim := by simpa [check, finished] using accepted
    rw [bounded_sound finished]
    exact observed

end P4bloIR.ExecutionCertificate
