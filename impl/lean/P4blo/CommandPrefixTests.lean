import P4blo.CommandBlockTests

namespace P4blo.CommandPrefixTests

open Fields FieldCommandExamples
open scoped Scalar
open P4bloIR.Execution

/-- Constructive premises for every source store, suffix and continuation.
This is an initialized-body witness, not a caller-initialization theorem. -/
theorem prefix_correct (cmd : Cmd modes) (source : Store roots)
    (suffix : List P4bloIR.Stmt) (continuation : List Work) :
    ∃ final, Steps
      { work := .statements (cmd.lower ++ suffix) :: continuation, run := initial source }
      { work := .statements suffix :: continuation, run := final } ∧
      FrameMatches (cmd.denote source) final.frame ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars (initial source) final ∧
      P4bloIR.ScalarStatements.PreservesOutside cmd.targets (initial source) final := by
  exact (cmd.steps_prefix source (initial source) suffix continuation rootWF indexAgrees
    (modes.scope_agrees rootWF) (initial_matches source) ⟨rfl, rfl⟩).2

private def advance : Nat → Machine → Except String Machine
  | 0, machine => .ok machine
  | n + 1, machine => match step machine with
    | .inl _ => .error "machine finished before the independent prefix boundary"
    | .inr next => advance n next

private def suffix : List P4bloIR.Stmt :=
  [.assign (.var "scratch") (.literal (.bits 8 200)),
   .verify (.literal (.boolean false)) "suffix-must-stay-pending"]

private def continuationFault : P4bloIR.Stmt :=
  .verify (.literal (.boolean false)) "continuation-must-stay-pending"

def run : IO Unit := do
  for hit in [false, true] do
    let source := store 64 false true hit
    let before := initial source
    let caller := { before.frame with
      vars := before.frame.vars.insert "callerOnly" (.bits (P4bloIR.Bits.wrap 8 91)) }
    let continuation : List Work := [.blockReturn caller [] [], .statement continuationFault]
    -- Independent step counts and scratch answers, not derived from a proof,
    -- the source denotation or an executable command-cost function.
    let profiles : List (String × Cmd modes × Nat × Nat) :=
      [("empty", .done, 0, 19),
       ("assignment", Cmd.assign scratch bits[8, 10], 2, 10),
       ("empty-branches", Cmd.ite (.read routeHit) .done .done, 3, 19),
       ("branch-shared-tail", Cmd.block CommandBlockTests.statements, 9, if hit then 14 else 15)]
    for (name, command, count, expected) in profiles do
      for trailing in [[], suffix] do
        let after ← IO.ofExcept (advance count
          { work := .statements (command.lower ++ trailing) :: continuation, run := before })
        unless after.fault.isNone do
          throw (IO.userError s!"prefix faulted before its endpoint: {name}")
        match after.work with
        | [.statements pending, .blockReturn saved [] [], .statement last] =>
          unless pending == trailing && last == continuationFault &&
              saved.read? "callerOnly" == some (.bits (P4bloIR.Bits.wrap 8 91)) &&
              saved.read? "scratch" == some (.bits (P4bloIR.Bits.wrap 8 19)) &&
              saved.scope.block == caller.scope.block && saved.action.isNone &&
              saved.actionVars.isNone do
            throw (IO.userError s!"prefix changed the pending suffix/return/continuation: {name}")
        | _ => throw (IO.userError s!"prefix lost its exact queue boundary: {name}")
        unless after.run.frame.read? "scratch" == some (.bits (P4bloIR.Bits.wrap 8 expected)) do
          throw (IO.userError s!"prefix scratch answer/order: {name}")
        for root in ["hdr", "meta", "route", "outside", "callerOnly"] do
          unless after.run.frame.read? root == before.frame.read? root do
            throw (IO.userError s!"prefix changed an unrelated root: {name}/{root}")
        unless after.run.index.program == before.index.program &&
            after.run.frame.scope.block == before.frame.scope.block &&
            after.run.frame.action.isNone && after.run.frame.actionVars.isNone &&
            after.run.packet.any (fun p => p.data == ⟨#[0xde, 0xad, 0xbe, 0xef]⟩ &&
              p.value == 0xdeadbeef && p.cursor == 3) &&
            after.run.emitter.any (fun e => e.width == 3 && e.value == 5) &&
            after.run.entries.any (fun e =>
              e.defaults[("untouched", "table")]? == some (some ⟨"action", []⟩)) &&
            (after.run.externs.instances["untouched-register"]?).any (fun state => match state with
              | .register width cells => width == 8 && cells == #[3, 9, 27]
              | _ => false) && after.run.visits[("parser", "state")]? == some 13 do
          throw (IO.userError s!"prefix changed non-variable Run state: {name}")
        -- A real negative control: the pending work does fault if executed.
        -- For the nonempty suffix it first overwrites scratch; it must not
        -- have run as part of the authored prefix above.
        if !trailing.isEmpty then
          let premature ← IO.ofExcept (advance 2 after)
          unless premature.run.frame.read? "scratch" == some (.bits (P4bloIR.Bits.wrap 8 200)) do
            throw (IO.userError "pending suffix must have an observable write")
        let (result, _) := (P4bloIR.Execution.run after.work).run after.run
        let message := if trailing.isEmpty then "continuation-must-stay-pending"
          else "suffix-must-stay-pending"
        unless (match result with
            | .error (.parse found) => found == message
            | _ => false) do
          throw (IO.userError "pending suffix/continuation must fault if executed")
  IO.println "16 flat-prefix boundaries, independent step/order answers and pending fault controls passed"

end P4blo.CommandPrefixTests
