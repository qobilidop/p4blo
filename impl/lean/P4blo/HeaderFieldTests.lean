import P4blo.HeaderFields
import P4blo.FieldCommandExamples
import P4bloArch.Externs

namespace P4blo.HeaderFieldTests

open Fields FieldCommandExamples

def ethernetValidity : HeaderRef roots := .mk .here (.field .here .here)
def ipv4Validity : HeaderRef roots := .mk .here (.field (.there .here) .here)

example : ethernetValidity.expr = .isValid (.member (.var "hdr") "ethernet") := rfl
example : ipv4Validity.expr = .isValid (.member (.var "hdr") "ipv4") := rfl

example (ref : HeaderRef roots) :
    P4bloIR.FieldTyping.Typed index modes.scope ref.expr .boolean :=
  ref.typed rootWF indexAgrees (Modes.Agrees.declares (modes.scope_agrees rootWF))

example (ref : HeaderRef roots) (source : Store roots) :
    (P4bloIR.evaluate ref.expr).run (initial source) = (.ok (.bool (ref.get source)), initial source) :=
  ref.evaluate source (initial source) indexAgrees (initial_matches source)

private def emptyHeader : Shape := .aggregate .header "Empty" .nil
private def emptyRoots : Layout := .cons "empty" emptyHeader .nil
private def inputModes : Modes emptyRoots := .cons (.param .«in») .nil
private def emptyRef : HeaderRef emptyRoots := .mk .here .here
private def emptyStore (valid : Bool) : Store emptyRoots := .cons (.aggregate valid .nil) .nil
private def emptyProgram : P4bloIR.Program :=
  { (default : P4bloIR.Program) with
    name := "header-validity",
    headerTypes := [⟨"Empty", []⟩], blocks := [inputModes.scope.block] }
private def emptyIndex : P4bloIR.Index :=
  { program := emptyProgram,
    headerTypes := ({} : Std.HashMap String P4bloIR.HeaderType).insert "Empty" ⟨"Empty", []⟩ }
private theorem emptyWF : RootWellFormed emptyRoots := by
  refine ⟨by decide, by decide, ?_⟩
  simp [emptyRoots, emptyHeader, Layout.LocallyWellFormed, Shape.LocallyWellFormed,
    P4bloIR.FieldLaws.NamesWellFormed, Layout.fields, Layout.Scalars]
private theorem emptyAgrees : emptyRoots.IndexAgrees emptyIndex := by
  simp [emptyRoots, emptyHeader, Layout.IndexAgrees, Shape.IndexAgrees, emptyIndex,
    P4bloIR.FieldLaws.Declared, P4bloIR.FieldLaws.NamesWellFormed, Layout.fields]

-- Constructive source store, exact nominal index, input declaration and frame.
example (valid : Bool) :
    P4bloIR.FieldTyping.Typed emptyIndex inputModes.scope emptyRef.expr .boolean ∧
    (P4bloIR.evaluate emptyRef.expr).run
        { index := emptyIndex, frame := inputModes.frame (emptyStore valid) } =
      (.ok (.bool valid), { index := emptyIndex, frame := inputModes.frame (emptyStore valid) }) := by
  refine ⟨emptyRef.typed emptyWF emptyAgrees (Modes.Agrees.declares (inputModes.scope_agrees emptyWF)), ?_⟩
  exact emptyRef.evaluate (emptyStore valid) _ emptyAgrees (inputModes.frame_matches _ emptyWF)

example : True := by
  fail_if_success have bad : HeaderPath (.aggregate .struct "NotHeader" .nil) := .here
  trivial
example : True := by
  fail_if_success have bad : HeaderPath (.scalar .boolean) := .here
  trivial
example : True := by
  fail_if_success have bad : HeaderPath (.scalar (.bits 8)) := .here
  trivial
example : True := by
  fail_if_success have bad : Ref roots .boolean := ethernetValidity
  trivial
example : True := by
  fail_if_success have bad : Place modes .boolean := ⟨ethernetValidity, by decide⟩
  trivial

def run : IO Unit := do
  for (ev, iv) in [(false, false), (false, true), (true, false), (true, true)] do
    let source := store 64 ev iv true
    for (ref, expected) in [(ethernetValidity, ev), (ipv4Validity, iv)] do
      unless ref.get source == expected do
        throw (IO.userError "independent source header validity")
      let before := initial source
      let (result, after) := (P4bloIR.evaluate ref.expr).run before
      unless result matches .ok (.bool _) do
        throw (IO.userError "header validity actual result type")
      unless result.toOption == some (.bool expected) do
        throw (IO.userError "independent actual header validity")
      unless (["hdr", "meta", "route", "scratch", "outside"].map after.frame.read?) ==
          (["hdr", "meta", "route", "scratch", "outside"].map before.frame.read?) &&
          after.index.program == before.index.program &&
          after.frame.scope.block == before.frame.scope.block &&
          after.frame.action.isNone && after.frame.actionVars.isNone &&
          after.packet.any (fun p => p.data == ⟨#[0xde, 0xad, 0xbe, 0xef]⟩ && p.value == 0xdeadbeef && p.cursor == 3) &&
          after.emitter.any (fun e => e.width == 3 && e.value == 5) &&
          after.entries.any (fun e => e.defaults[("untouched", "table")]? == some (some ⟨"action", []⟩)) &&
          (after.externs.instances["untouched-register"]?).any (fun state => state.register? == some (8, #[3, 9, 27])) && after.visits[("parser", "state")]? == some 13 do
        throw (IO.userError "header validity must preserve all observed Run state")
  -- Real production initialization remains a finite witness, not a universal
  -- theorem. An input empty header starts invalid and is readable, not writable.
  let built ← IO.ofExcept (P4bloIR.Index.build emptyProgram)
  let frame ← IO.ofExcept (P4bloIR.Frame.forBlock built inputModes.scope.block)
  let (result, final) := (P4bloIR.evaluate emptyRef.expr).run { index := built, frame }
  unless result.toOption == some (.bool false) &&
      final.frame.read? "empty" == some (.header "Empty" false []) do
    throw (IO.userError "initialized input empty header validity")
  for valid in [false, true] do
    let (result, _) := (P4bloIR.evaluate emptyRef.expr).run
      { index := emptyIndex, frame := inputModes.frame (emptyStore valid) }
    unless result.toOption == some (.bool valid) do
      throw (IO.userError "direct empty header source validity")
  IO.println "Header validity: 8 nested, 2 direct and real initialization answers; 5 rejected constructors passed"

end P4blo.HeaderFieldTests
