import P4blo.CallInitializers
import P4blo.CallEntryTests
import P4bloArch.Externs

namespace P4blo.CallInitializerTests
open P4bloIR P4bloIR.Execution P4bloIR.PlainCallEntry
open Fields CallEntryTests

/-- A real-built entry supplies the local prefix premises, for all source
validity pairs and arbitrary pending work. This is not body-bearing lookup. -/
theorem concrete_prefix (ev iv : Bool) (suffix : List Stmt) (continuation : List Work) :
    ∃ zero, Frame.forBlock CallEntry.index CallEntry.block = .ok zero ∧
      let start := { initial ev iv with frame := boundFrame zero (hdr ev iv).toValue (metadataValue ev iv).toValue (routeValue ev iv).toValue observer }
      Steps { work := .statements (CallInitializers.body ++ suffix) :: continuation, run := start }
        { work := .statements suffix :: continuation, run := CallInitializers.finalRun start } ∧
      FrameMatches (CallInitializers.bodyStore (hdr ev iv) (metadataValue ev iv) (routeValue ev iv))
        (CallInitializers.finalRun start).frame := by
  obtain ⟨zero, hz, _, hb, hf, _, hu, _, _⟩ :=
    CallEntry.source_entry (initial ev iv) (hdr ev iv) (metadataValue ev iv) (routeValue ev iv)
      observer continuation rfl ⟨rfl, rfl⟩
      (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
      (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
      (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
      (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
  refine ⟨zero, hz, ?_⟩
  have h := CallInitializers.source_steps
    { initial ev iv with frame := boundFrame zero (hdr ev iv).toValue (metadataValue ev iv).toValue (routeValue ev iv).toValue observer }
    (hdr ev iv) (metadataValue ev iv) (routeValue ev iv) _ suffix continuation hb hf hu
  exact ⟨h.1, h.2.1⟩

theorem concrete_typed :
    P4bloIR.FieldTyping.BodyTyped CallEntry.index CallEntry.scope CallInitializers.body :=
  CallInitializers.body_typed _ _ (by cbv) (by cbv)

private def advance : Nat → Machine → Except String Machine
  | 0, machine => .ok machine
  | n + 1, machine => match step machine with
    | .inl _ => .error "initializer finished before its exact prefix boundary"
    | .inr next => advance n next

private def suffix : List Stmt :=
  [.assign (.var "scratch") (.literal (.bits 8 200)),
   .verify (.literal (.boolean false)) "pending-initializer-suffix"]

private def matchesFault : Except Fault Unit → Fault → Bool
  | .error (.interp a), .interp b => a == b
  | .error (.parse a), .parse b => a == b
  | _, _ => false

def run : IO Unit := do
  for ev in [false, true] do
    for iv in [false, true] do
      let entry := (entered ev iv).run
      for oldExtra in [0, 87] do
        let before := { entry with frame := { entry.frame with
          vars := entry.frame.vars.insert "unrelated" (.bits (Bits.wrap 8 oldExtra)) } }
        let saved := caller ev iv
        let tail : List Work := [.blockReturn saved params args, .block "mustRemainPending" []]
        for trailing in [[], suffix] do
          let after ← IO.ofExcept (advance 4 {
            work := .statements (CallInitializers.body ++ trailing) :: tail, run := before })
          unless after.fault.isNone do
            throw (IO.userError "initializer prefix faulted")
          match after.work with
          | [.statements pending, .blockReturn original ps actuals, .block stop []] =>
            unless pending == trailing && ps == params && actuals == args &&
                stop == "mustRemainPending" && original.vars.toList == saved.vars.toList &&
                original.scope.block == saved.scope.block && original.action.isNone &&
                original.actionVars.isNone do
              throw (IO.userError "initializer changed pending suffix, caller or continuation")
          | _ => throw (IO.userError "initializer stopped at the wrong queue boundary")
          -- Literal answers are intentionally independent of finalRun/bodyStore.
          unless after.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 19)) &&
              after.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 165)) &&
              after.run.frame.vars.size == 6 do
            throw (IO.userError "initializer independent local answers differ")
          for name in ["hdr", "meta", "route", "observer", "caller_only"] do
            unless after.run.frame.read? name == before.frame.read? name do
              throw (IO.userError s!"initializer changed preserved root {name}")
          unless after.run.frame.scope.block == before.frame.scope.block &&
              after.run.frame.action.isNone && after.run.frame.actionVars.isNone &&
              after.run.index.program == before.index.program &&
              after.run.packet.any (fun p => p.data == ⟨#[0xde, 0xad, 0xbe, 0xef]⟩ &&
                p.value == 0xdeadbeef && p.cursor == 3) &&
              after.run.emitter.any (fun e => e.width == 3 && e.value == 5) &&
              after.run.entries.any (fun e => e.entries.size == 0 && e.defaults.size == 1 &&
                e.defaults[("untouched", "table")]? == some (some ⟨"sentinelAction", []⟩)) &&
              after.run.externs.instances.size == 1 &&
              (after.run.externs.instances["sentinel"]?).any (fun state => state.register? == some (8, #[3, 9, 27])) && after.run.visits.size == 1 &&
              after.run.visits[("parser", "state")]? == some 13 do
            throw (IO.userError "initializer changed non-value sentinels")
          if !trailing.isEmpty then
            let premature ← IO.ofExcept (advance 2 after)
            unless premature.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 200)) do
              throw (IO.userError "pending suffix must have a visible write")
          let (outcome, _) := (Execution.run after.work).run after.run
          let expected := if trailing.isEmpty then Fault.interp "unknown block 'mustRemainPending'"
            else Fault.parse "pending-initializer-suffix"
          unless matchesFault outcome expected do
            throw (IO.userError "pending suffix/continuation must fault when executed")
      -- Absence violates an actual existence premise: the first write remains
      -- visible when the second write fails. No atomic rollback is claimed.
      let missing := { entry with frame := { entry.frame with vars := entry.frame.vars.erase "unrelated" } }
      let (outcome, stopped) := (execute CallInitializers.body).run missing
      unless matchesFault outcome (.interp "unknown variable 'unrelated' in block 'RewriteBody'") &&
          stopped.frame.read? "scratch" == some (.bits (Bits.wrap 8 19)) do
        throw (IO.userError "missing-extra premise or partial-write behavior differs")
  IO.println "16 actual local-initializer prefixes and four missing-extra controls passed"

end P4blo.CallInitializerTests
