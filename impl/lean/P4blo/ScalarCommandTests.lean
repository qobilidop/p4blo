import P4blo.ScalarCommandExamples
import P4bloArch.Externs

namespace P4blo.ScalarCommandTests

open Scalar ScalarCommandExamples

private def inputModes : Modes [("x", .bits 8)] := .cons (.param .«in») .nil
private def dataModes : Modes [("x", .bits 8)] := .cons (.param .none) .nil
private def outputModes : Modes [("x", .bits 8)] := .cons (.param .out) .nil
private def inoutModes : Modes [("x", .bits 8)] := .cons (.param .inout) .nil

example : Place outputModes (.bits 8) := ⟨.here, rfl⟩
example : Place inoutModes (.bits 8) := ⟨.here, rfl⟩
example : True := by
  fail_if_success have bad : Place inputModes (.bits 8) := ⟨.here, by decide⟩
  trivial
example : True := by
  fail_if_success have bad : Place dataModes (.bits 8) := ⟨.here, by decide⟩
  trivial
example : True := by
  fail_if_success have bad : Cmd modes := Cmd.assign x (.boolean true)
  trivial
example : True := by
  fail_if_success have bad : Cmd modes := Cmd.ite (.read x.ref) .done .done
  trivial

private def observations (env : Env context) : Nat × Nat × Bool :=
  ((env.get x.ref).val, (env.get y.ref).val, env.get flag.ref)

private def runtimeObservations (frame : P4bloIR.Frame) : Option (Nat × Nat × Bool) := do
  let .bits a ← frame.read? "x" | none
  let .bits b ← frame.read? "y" | none
  let .bool c ← frame.read? "flag" | none
  pure (a.value, b.value, c)

private def initial (env : Env context) : P4bloIR.Run :=
  let index : P4bloIR.Index := { program := { (default : P4bloIR.BlockLibrary) with name := "untouched" } }
  { index
    frame := { modes.frame env with vars := env.values.insert "unrelated" (.bits (P4bloIR.Bits.wrap 8 165)) }
    packet := some { data := ⟨#[0xab, 0xcd]⟩, value := 0xabcd, cursor := 3 }
    emitter := some { value := 5, width := 3 }
    entries := some { index, defaults := (({} : Std.HashMap P4bloIR.TableRef (Option P4bloIR.ActionCall)).insert
      ("untouched", "table") (some ⟨"action", []⟩)) }
    externs := { model := P4bloArch.model, instances := (({} : Std.HashMap String P4bloIR.ExternState).insert
      "untouched-register" (.register 8 #[3, 9, 27])) }
    visits := ({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 13 }

-- The nonempty, unrelated initial state used below really meets the theorem's
-- premises, including declaration agreement and no active action layer.
example (env : Env context) : FrameMatches env (initial env).frame := by
  intro t ref
  have hn : ref.name ≠ "unrelated" := by
    cases ref with
    | here => decide
    | there ref => cases ref with
      | here => decide
      | there ref => cases ref with
        | here => decide
        | there ref => cases ref
  simpa [initial, P4bloIR.Frame.read?, Modes.frame, Env.frame,
    Std.HashMap.getElem?_insert, Ne.symm hn] using env.values_get (by decide) ref

example : ¬P4bloIR.ScalarStatements.BlockFrame
    { modes.frame (.cons 0 (.cons 0 (.cons false .nil))) with action := some "active" } := by
  simp [P4bloIR.ScalarStatements.BlockFrame]

private def faultingContinuation : List P4bloIR.Execution.Work :=
  [.statement (.verify (.literal (.boolean false)) "continuation-must-not-run")]

example (env : Env context) : ∃ final,
    P4bloIR.Execution.Steps
      { work := .statements update.lower :: faultingContinuation, run :=
        { index := default, frame := modes.frame env } }
      { work := faultingContinuation, run := final } ∧
    FrameMatches (update.denote env) final.frame := by
  obtain ⟨final, trace, hm, _, _⟩ := update.steps env
    { index := default, frame := modes.frame env } faultingContinuation (by decide)
    (modes.frame_matches env (by decide)) ⟨rfl, rfl⟩
  exact ⟨final, trace, hm⟩

def run : IO Unit := do
  let expected := [(0, 7, true), (4, 11, false), (255, 1, false), (1, 1, false),
    (10, 17, true), (12, 19, false), (1, 0, true), (19, 7, true), (19, 7, false)]
  unless cases.length == expected.length do
    throw (IO.userError "statement fixtures and independent answers differ in length")
  for (c, answer) in cases.zip expected do
    unless observations (c.command.denote c.environment) == answer do
      throw (IO.userError s!"statement source known answer failed: {c.name}")
    let before := initial c.environment
    let (outcome, after) := (P4bloIR.execute c.command.lower).run before
    unless outcome matches .ok () do
      throw (IO.userError s!"statement execution failed: {c.name}")
    unless runtimeObservations after.frame == some answer do
      throw (IO.userError s!"statement runtime known answer failed: {c.name}")
    unless after.index.program.name == "untouched" &&
        (after.frame.read? "unrelated").any (· == .bits (P4bloIR.Bits.wrap 8 165)) &&
        after.frame.scope.block == before.frame.scope.block && after.frame.action.isNone &&
        after.frame.actionVars.isNone &&
        after.packet.any (fun p => p.data == ⟨#[0xab, 0xcd]⟩ && p.value == 0xabcd && p.cursor == 3) &&
        after.emitter.any (fun e => e.width == 3 && e.value == 5) &&
        after.entries.any (fun e => e.defaults[("untouched", "table")]? == some (some ⟨"action", []⟩)) &&
        (after.externs.instances["untouched-register"]?).any (fun state => state.register? == some (8, #[3, 9, 27])) &&
        after.visits[("parser", "state")]? == some 13 do
      throw (IO.userError s!"statement noninterference failed: {c.name}")
  -- Exercise real Index.build/Frame.forBlock rather than only the custom
  -- witness constructor. Its initialization should be zero, not the inputs
  -- installed by the packet test wrapper.
  let block := modes.scope.block
  let index ← IO.ofExcept (P4bloIR.Index.build { (default : P4bloIR.BlockLibrary) with blocks := [block] })
  let frame ← IO.ofExcept (P4bloIR.Frame.forBlock index block)
  unless runtimeObservations frame == some (0, 0, false) do
    throw (IO.userError "Frame.forBlock must initialize declared scalar locals to zero")
  let (continuationOutcome, _) := (P4bloIR.Execution.run faultingContinuation).run
    { index, frame }
  unless continuationOutcome matches .error (.parse "continuation-must-not-run") do
    throw (IO.userError "the prefix theorem's continuation must genuinely fault if executed")
  for direction in [P4bloIR.Direction.«in», .out, .inout] do
    let declared : Modes [("x", .bits 8)] := .cons (.param direction) .nil
    let b := declared.scope.block
    let i ← IO.ofExcept (P4bloIR.Index.build { (default : P4bloIR.BlockLibrary) with blocks := [b] })
    let f ← IO.ofExcept (P4bloIR.Frame.forBlock i b)
    unless (f.read? "x").any (· == .bits (P4bloIR.Bits.wrap 8 0)) do
      throw (IO.userError "Frame.forBlock parameter construction failed")
    if h : (declared.get (.here : Ref [("x", .bits 8)] (.bits 8))).writable = true then
      let target : Place declared (.bits 8) := ⟨.here, h⟩
      let command := Cmd.assign target (bitsIn 8 9)
      let (outcome, after) := (P4bloIR.execute command.lower).run { index := i, frame := f }
      unless outcome matches .ok () do
        throw (IO.userError "writable parameter command faulted")
      unless (after.frame.read? "x").any (· == .bits (P4bloIR.Bits.wrap 8 9)) do
        throw (IO.userError "writable out/inout parameter must receive the exact assigned value")
  IO.println s!"{expected.length} scalar command answers/noninterference cases, 4 negative typing checks and declaration initialization passed"

end P4blo.ScalarCommandTests
