import P4bloIR.ExecutionCertificate
import P4bloArch.Externs

/-!
# The fixed execution-certificate experiment

`P4bloIR.ExecutionCertificate` proves that an accepted bounded check binds
the supplied initial machine, observation and claim to the actual runner,
for any observation. This module supplies the one concrete experiment the
`p4blo-lean` endpoint exposes: a control fragment that reads and writes a
register and counts a counter, so it needs the reference extern families
(docs/assurance.md, "Execution certificates").
-/

namespace P4bloArch.Certificate.Example

open P4bloIR

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

/-- The real declarations checked by `Index.build` and `P4bloArch.bind`. -/
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
  let externs ← P4bloArch.bind index
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
    register := run.externs.instances["r"]?.bind (·.register?) |>.map fun (width, cells) =>
      (width, cells.toList),
    counter := run.externs.instances["k"]?.bind (·.counter?) |>.map (·.toList),
    localValue := match run.frame.read? "value" with
      | some (.bits b) => some (b.width, b.value)
      | _ => none }

end P4bloArch.Certificate.Example
