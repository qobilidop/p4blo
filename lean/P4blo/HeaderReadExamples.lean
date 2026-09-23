import P4blo.FieldCommands

namespace P4blo.HeaderReadExamples

open Fields
open scoped Scalar

def headerFields : Layout := .cons "byte" (.scalar (.bits 8)) .nil
def header : Shape := .aggregate .header "ReadHeader" headerFields
def empty : Shape := .aggregate .header "ReadEmpty" .nil
def packetFields : Layout := .cons "first" header (.cons "second" header
  (.cons "sentinel" (.scalar (.bits 16)) .nil))
def packet : Shape := .aggregate .struct "ReadPacket" packetFields
def roots : Layout := .cons "packet" packet (.cons "direct" header (.cons "empty" empty
  (.cons "result" (.scalar (.bits 8)) (.cons "flag" (.scalar .boolean) .nil))))
def modes : Modes roots := .cons (.param .«in») (.cons (.param .«in»)
  (.cons (.param .«in») (.cons (.param .out) (.cons (.param .out) .nil))))

def first : HeaderRef roots := .mk .here (.field .here .here)
def second : HeaderRef roots := .mk .here (.field (.there .here) .here)
def direct : HeaderRef roots := .mk (.there .here) .here
def emptyRef : HeaderRef roots := .mk (.there (.there .here)) .here
def firstByte : Ref roots (.bits 8) := .mk .here (.field .here (.field .here .scalar))
def directByte : Ref roots (.bits 8) := .mk (.there .here) (.field .here .scalar)
def result : Place modes (.bits 8) := ⟨.mk (.there (.there (.there .here))) .scalar, rfl⟩
def flag : Place modes .boolean := ⟨.mk (.there (.there (.there (.there .here)))) .scalar, rfl⟩

def mixed : Expr roots (.bits 8) := .mux first.isValid (.read firstByte + bits[8, 85]) (.read directByte)
def command : Cmd modes := Cmd.block [
  Cmd.assign flag second.isValid,
  Cmd.ite first.isValid (Cmd.assign result (.read directByte + bits[8, 1]))
    (Cmd.assign result bits[8, 19])]

def store (a b : Bool) : Store roots :=
  .cons (.aggregate () (.cons (.aggregate a (.cons (.scalar 171) .nil))
    (.cons (.aggregate b (.cons (.scalar 57) .nil)) (.cons (.scalar 4660) .nil))))
  (.cons (.aggregate (!a) (.cons (.scalar 204) .nil))
  (.cons (.aggregate b .nil) (.cons (.scalar 0) (.cons (.scalar false) .nil))))

def index : P4bloIR.Index :=
  { program := default,
    headerTypes := (({} : Std.HashMap String P4bloIR.HeaderType).insert
      "ReadHeader" ⟨"ReadHeader", headerFields.fields⟩).insert "ReadEmpty" ⟨"ReadEmpty", []⟩,
    structTypes := ({} : Std.HashMap String P4bloIR.StructType).insert
      "ReadPacket" ⟨"ReadPacket", packetFields.fields⟩ }

theorem rootWF : RootWellFormed roots := by
  refine ⟨by decide, by decide, ?_⟩
  simp [roots, packet, packetFields, header, headerFields, empty,
    Layout.LocallyWellFormed, Shape.LocallyWellFormed, P4bloIR.FieldLaws.NamesWellFormed,
    Layout.fields, Shape.toIR, Layout.Scalars]

theorem indexAgrees : roots.IndexAgrees index := by
  simp [roots, packet, packetFields, header, headerFields, empty,
    Layout.IndexAgrees, Shape.IndexAgrees, P4bloIR.FieldLaws.Declared,
    P4bloIR.FieldLaws.NamesWellFormed, index, Layout.fields, Shape.toIR, Std.HashMap.getElem_insert]

def initial (source : Store roots) : P4bloIR.Run :=
  { index, frame := modes.frame source,
    packet := some { data := ⟨#[0xde, 0xad, 0xbe, 0xef]⟩, value := 0xdeadbeef, cursor := 0 },
    emitter := some { value := 5, width := 3 },
    visits := ({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 13 }

structure ExprCase where
  name : String
  type : Scalar.Ty
  expression : Expr roots type
  a : Bool
  b : Bool

def expressionCases : List ExprCase :=
  [("00", false, false), ("01", false, true), ("10", true, false), ("11", true, true)].flatMap
    (fun (suffix, a, b) => [
      ⟨"first-" ++ suffix, .boolean, first.isValid, a, b⟩,
      ⟨"second-" ++ suffix, .boolean, second.isValid, a, b⟩,
      ⟨"direct-" ++ suffix, .boolean, direct.isValid, a, b⟩,
      ⟨"empty-" ++ suffix, .boolean, emptyRef.isValid, a, b⟩,
      ⟨"mixed-" ++ suffix, .bits 8, mixed, a, b⟩])

example (c : ExprCase) : P4bloIR.FieldTyping.Typed index modes.scope (lower c.expression) c.type :=
  lower_typed c.expression rootWF indexAgrees (Modes.Agrees.declares (modes.scope_agrees rootWF))

example (c : ExprCase) : (P4bloIR.evaluate (lower c.expression)).run (initial (store c.a c.b)) =
    (.ok (Scalar.toValue (denote (store c.a c.b) c.expression)), initial (store c.a c.b)) :=
  evaluate_lower c.expression _ _ indexAgrees (modes.frame_matches _ rootWF)

example (a b : Bool) : ∃ final,
    (P4bloIR.execute command.lower).run (initial (store a b)) = (.ok (), final) ∧
      FrameMatches (command.denote (store a b)) final.frame ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars (initial (store a b)) final := by
  obtain ⟨_, final, h, hm, _, _, hc, _⟩ := command.execute_correct (store a b) (initial (store a b)) rootWF indexAgrees
    (modes.scope_agrees rootWF) (modes.frame_matches _ rootWF) ⟨rfl, rfl⟩
  exact ⟨final, h, hm, hc⟩

example : True := by
  fail_if_success have bad : Place modes .boolean := ⟨first, by decide⟩
  trivial
example : True := by
  fail_if_success have bad : Cmd modes := Cmd.assign result first.isValid
  trivial
example : True := by
  fail_if_success have bad : Expr roots (.bits 8) := first.isValid
  trivial

def run : IO Unit := do
  for (a, b) in [(false, false), (false, true), (true, false), (true, true)] do
    let source := store a b
    for (expression, expected) in [(first.isValid, a), (second.isValid, b),
        (direct.isValid, !a), (emptyRef.isValid, b)] do
      unless denote source expression == expected do
        throw (IO.userError "independent validity expression answer")
      let (outcome, after) := (P4bloIR.evaluate (lower expression)).run (initial source)
      unless outcome.toOption == some (.bool expected) &&
          (["packet", "direct", "empty", "result", "flag"].map after.frame.read?) == source.toValues.map some do
        throw (IO.userError "validity expression exact value and stored state")
    unless (denote source mixed).val == (if a then 0 else 204) do
      throw (IO.userError "validity/scalar mixed expression")
    let finalSource := command.denote source
    unless (result.ref.get finalSource).val == (if a then 205 else 19) &&
        flag.ref.get finalSource == b && finalSource.validities == source.validities do
      throw (IO.userError "validity assignment RHS and conditional answer")
    let (outcome, after) := (P4bloIR.execute command.lower).run (initial source)
    unless outcome matches .ok () do
      throw (IO.userError "validity command execution")
    unless after.frame.read? "result" == some (.bits (P4bloIR.Bits.wrap 8 (if a then 205 else 19))) &&
        after.frame.read? "flag" == some (.bool b) &&
        (["packet", "direct", "empty"].map after.frame.read?) ==
          (["packet", "direct", "empty"].map (initial source).frame.read?) &&
        after.packet.any (fun p => p.data == ⟨#[0xde, 0xad, 0xbe, 0xef]⟩ && p.cursor == 0) &&
        after.emitter.any (fun e => e.width == 3 && e.value == 5) &&
        after.visits[("parser", "state")]? == some 13 do
      throw (IO.userError "validity command full stored values and unrelated Run")
  IO.println "20 unified validity expressions and 4 conditional/RHS commands passed"

end P4blo.HeaderReadExamples
