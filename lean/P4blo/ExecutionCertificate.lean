import P4blo.Exec

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
equivalence with Python. `Example` provides a reusable stateful experiment
whose observation distinguishes success and both fault kinds.
-/

namespace P4blo.ExecutionCertificate

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

namespace Example

/-- Fault tags are part of this experiment's observation, so a matching
register/counter snapshot alone cannot conceal an internal or parser error. -/
inductive Completion
  | success
  | interp (message : String)
  | parse (error : String)
  deriving Repr, BEq, DecidableEq

structure Observation where
  completion : Completion
  register : Option (Nat × List Nat)
  counter : Option (List Nat)
  localValue : Option (Nat × Nat)
  deriving Repr, BEq, DecidableEq

/-- Read one register cell, increment and store it, then increment a counter.
All effects use the same extern-call statements as ordinary programs. -/
def block : Block := { (default : Block) with
  name := "C", kind := .control,
  locals := [{ name := "value", type := .bits 8 }],
  body := [
    .callExtern "r" "read" [.lvalue (.var "value"), .expr (.literal (.bits 32 0))] none,
    .assign (.var "value") (.binary .add (.var "value") (.literal (.bits 8 1))),
    .callExtern "r" "write" [.expr (.literal (.bits 32 0)), .expr (.var "value")] none,
    .callExtern "k" "count" [.expr (.literal (.bits 32 0))] none] }

/-- The real declarations checked by `Index.build` and `Externs.bind`. -/
def program : Program := { (default : Program) with
  name := "execution-certificate",
  externTypes := [
    { name := "register", constructorParams := [{ name := "size", type := .bits 32, direction := .«in» }],
      methods := [
        { name := "read", params := [
            { name := "result", type := .bits 8, direction := .out },
            { name := "index", type := .bits 32, direction := .«in» }], returns := none },
        { name := "write", params := [
            { name := "index", type := .bits 32, direction := .«in» },
            { name := "data", type := .bits 8, direction := .«in» }], returns := none }] },
    { name := "counter", constructorParams := [{ name := "size", type := .bits 32, direction := .«in» }],
      methods := [{ name := "count", params := [
        { name := "index", type := .bits 32, direction := .«in» }], returns := none }] }],
  externInstances := [
    { name := "r", externType := "register", args := [.bits 32 1] },
    { name := "k", externType := "counter", args := [.bits 32 1] }],
  blocks := [block] }

/-- Bind the example, then install the caller's initial register and counter
contents. An out-of-width initial register value is rejected, not truncated. -/
def initial (registerValue counterValue : Nat) : Except String Execution.Machine := do
  if registerValue ≥ 256 then throw "initial register value does not fit bit<8>"
  let index ← Index.build program
  let frame ← Frame.forBlock index block
  let externs ← Externs.bind index
  let externs := { externs with instances :=
    (externs.instances.insert "r" (.register 8 #[registerValue])).insert "k" (.counter #[counterValue]) }
  pure { work := [.statements block.body], run := { index, frame, externs } }

/-- Include exact fault class/message, register width/cells, counter cells,
and the local's width/value. Missing or wrongly shaped state remains visible. -/
def observe (outcome : Execution.Outcome) : Observation :=
  let completion := match outcome.1 with
    | .ok () => Completion.success
    | .error (.interp msg) => .interp msg
    | .error (.parse err) => .parse err
  let run := outcome.2
  { completion,
    register := match run.externs.instances["r"]? with
      | some (.register width cells) => some (width, cells.toList)
      | _ => none,
    counter := match run.externs.instances["k"]? with
      | some (.counter cells) => some cells.toList
      | _ => none,
    localValue := match run.frame.read? "value" with
      | some (.bits b) => some (b.width, b.value)
      | _ => none }

end Example
end P4blo.ExecutionCertificate
