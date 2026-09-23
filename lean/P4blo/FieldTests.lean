import P4blo.FieldExpressions

namespace P4blo.FieldTests

open Fields
open scoped Scalar

private def headerFields : Layout :=
  .cons "left" (.scalar (.bits 8)) (.cons "right" (.scalar (.bits 9)) .nil)
private def header : Shape := .aggregate .header "H" headerFields
private def packetFields : Layout :=
  .cons "header" header (.cons "sibling" (.scalar (.bits 16)) .nil)
private def packet : Shape := .aggregate .struct "Packet" packetFields
private def metaFields : Layout :=
  .cons "port" (.scalar (.bits 9)) (.cons "flag" (.scalar .boolean) .nil)
private def metadata : Shape := .aggregate .struct "M" metaFields
private def roots : Layout := .cons "hdr" packet (.cons "meta" metadata .nil)

private def left : Ref roots (.bits 8) :=
  .mk .here (.field .here (.field .here .scalar))
private def right : Ref roots (.bits 9) :=
  .mk .here (.field .here (.field (.there .here) .scalar))
private def port : Ref roots (.bits 9) :=
  .mk (.there .here) (.field .here .scalar)
private def flag : Ref roots .boolean :=
  .mk (.there .here) (.field (.there .here) .scalar)

private def store (valid : Bool) : Store roots :=
  .cons (.aggregate () (.cons (.aggregate valid
    (.cons (.scalar 171) (.cons (.scalar 257) .nil)))
    (.cons (.scalar 4660) .nil)))
    (.cons (.aggregate () (.cons (.scalar 3) (.cons (.scalar true) .nil))) .nil)

private def index : P4bloIR.Index :=
  { program := default,
    headerTypes := ({} : Std.HashMap String P4bloIR.HeaderType).insert "H" ⟨"H", headerFields.fields⟩,
    structTypes := (({} : Std.HashMap String P4bloIR.StructType).insert
      "Packet" ⟨"Packet", packetFields.fields⟩).insert "M" ⟨"M", metaFields.fields⟩ }

private def scope : P4bloIR.BlockScope :=
  { block := default, vars := (({} : Std.HashMap String P4bloIR.VarDecl).insert
      "hdr" (.var ⟨"hdr", packet.toIR⟩)).insert "meta" (.var ⟨"meta", metadata.toIR⟩) }

private theorem declares : RootDeclares roots scope := by
  intro shape root
  cases root with
  | here => exact ⟨.var ⟨"hdr", packet.toIR⟩, by simp [scope, Slot.name,
      P4bloIR.BlockScope.var?, Std.HashMap.getElem_insert], rfl, rfl⟩
  | there root => cases root with
    | here => exact ⟨.var ⟨"meta", metadata.toIR⟩, by simp [scope, Slot.name,
        P4bloIR.BlockScope.var?], rfl, rfl⟩
    | there root => cases root

private theorem agrees : roots.IndexAgrees index := by
  simp [roots, Layout.IndexAgrees, Shape.IndexAgrees, packet, header, metadata,
    packetFields, headerFields, metaFields, P4bloIR.FieldLaws.Declared,
    P4bloIR.FieldLaws.NamesWellFormed, index, Layout.fields, Shape.toIR,
    Std.HashMap.getElem_insert]

private theorem localWF : roots.LocallyWellFormed := by
  simp [roots, Layout.LocallyWellFormed, Shape.LocallyWellFormed, packet, header, metadata,
    packetFields, headerFields, metaFields, P4bloIR.FieldLaws.NamesWellFormed,
    Layout.fields, Shape.toIR, Layout.Scalars]

private theorem rootWF : RootWellFormed roots := ⟨by decide, by decide, localWF⟩

example : ¬RootDeclares roots { block := default, vars := {} } := by
  intro hd
  obtain ⟨decl, h, _, _⟩ := hd .here
  simp [P4bloIR.BlockScope.var?, Slot.name] at h

structure ExprCase where
  name : String
  type : Scalar.Ty
  expression : Expr roots type
  valid : Bool

def expressionCases : List ExprCase :=
  [⟨"field-add-valid", .bits 8, .read left + bits[8, 85], true⟩,
   ⟨"field-add-invalid", .bits 8, .read left + bits[8, 85], false⟩,
   ⟨"field-right", .bits 9, .read right, false⟩,
   ⟨"field-port", .bits 9, .read port + bits[9, 5], true⟩,
   ⟨"field-mux", .bits 9, .mux (.read flag) (.read right) bits[9, 511], false⟩,
   ⟨"field-equal", .boolean, .read port === bits[9, 3], true⟩,
   ⟨"field-no", .bits 9, .mux (.boolean false) (.read right) bits[9, 511], false⟩]

example (c : ExprCase) : P4bloIR.FieldTyping.Typed index scope (lower c.expression) c.type :=
  lower_typed c.expression rootWF agrees declares

example : True := by
  fail_if_success have bad : Expr roots (.bits 9) := by exact (.read left : Expr roots (.bits 8)) + bits[8, 1]
  trivial
example : True := by
  fail_if_success have bad : Expr roots (.bits 8) := bits[8, 256]
  trivial

-- Reusing one coherent nominal type is admissible at multiple roots.
example : (Layout.cons "first" header (.cons "second" header .nil)).IndexAgrees index := by
  have h : header.IndexAgrees index := agrees.1.2.1
  exact ⟨h, h, trivial⟩

private def differentHeader : Shape :=
  .aggregate .header "H" (.cons "left" (.scalar (.bits 7)) (.cons "right" (.scalar (.bits 9)) .nil))
private def incompatibleRoots : Layout := .cons "first" header (.cons "second" differentHeader .nil)

example : incompatibleRoots.LocallyWellFormed := by
  simp [incompatibleRoots, differentHeader, header, headerFields, Layout.LocallyWellFormed,
    Shape.LocallyWellFormed, P4bloIR.FieldLaws.NamesWellFormed, Layout.fields, Layout.Scalars]

-- Even though every individual shape is locally valid, no index can
-- assign two different declarations to the same nominal header name.
example (actual : P4bloIR.Index) : ¬incompatibleRoots.IndexAgrees actual := by
  intro h
  have bad := nominal_fields_unique h.1.1 h.2.1.1
  simp [headerFields, Layout.fields,
    Shape.toIR, Scalar.Ty.toIR] at bad

example (actual : P4bloIR.Index) :
    ¬(Layout.cons "first" header
      (.cons "second" (.aggregate .struct "H" headerFields) .nil)).IndexAgrees actual := by
  intro h
  have bad := nominal_kind_unique h.1.1 h.2.1.1
  contradiction

example : ¬(Shape.scalar (.bits 0)).LocallyWellFormed := by simp [Shape.LocallyWellFormed]
example : ¬(Shape.aggregate .header "bad" (.cons "nested" header .nil)).LocallyWellFormed := by
  simp [Shape.LocallyWellFormed, Layout.Scalars, header]
example : ¬(Shape.aggregate .struct "bad"
    (.cons "x" (.scalar (.bits 8)) (.cons "x" (.scalar (.bits 8)) .nil))).LocallyWellFormed := by
  simp [Shape.LocallyWellFormed, P4bloIR.FieldLaws.NamesWellFormed, Layout.fields]
example : True := by
  fail_if_success have bad : Ref roots (.bits 8) := port
  trivial
example : True := by
  fail_if_success have bad : Data packet := .scalar false
  trivial
example : True := by
  fail_if_success have bad : Slot headerFields (.scalar .boolean) := .there (.there .here)
  trivial

private def initial (valid : Bool) : P4bloIR.Run :=
  { index, frame := { (store valid).frame with
      vars := (store valid).bindings.insert "outside" (.header "Outside" false [.bool true]) },
    packet := some { data := ⟨#[0xab]⟩, value := 171, cursor := 3 },
    emitter := some { value := 5, width := 3 },
    visits := ({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 13 }

private theorem initial_matches (valid : Bool) : FrameMatches (store valid) (initial valid).frame := by
  intro shape root
  have hn : root.name ≠ "outside" := by
    cases root with
    | here => decide
    | there root => cases root with
      | here => decide
      | there root => cases root
  simpa [initial, Record.frame, P4bloIR.Frame.read?, Std.HashMap.getElem?_insert, Ne.symm hn]
    using (store valid).bindings_get root (by decide)

example (valid : Bool) : (P4bloIR.evaluate left.expr).run (initial valid) =
    (.ok (.bits (P4bloIR.Bits.wrap 8 171)), initial valid) := by
  exact left.evaluate (store valid) (initial valid) agrees (initial_matches valid)

-- Concrete frame/index witnesses instantiate the full nested-write bridge,
-- not only the weaker primitive return-value law.
example (valid : Bool) : ∃ final,
    (P4bloIR.writeLValue right.lvalue (Scalar.toValue (t := .bits 9) 7)).run (initial valid) =
      (.ok (), final) ∧ FrameMatches (right.set (store valid) 7) final.frame ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars (initial valid) final ∧
      P4bloIR.ScalarStatements.PreservesOutside [right.rootName] (initial valid) final := by
  exact right.write_matches (store valid) 7 (initial valid) agrees (initial_matches valid)
    (by decide) ⟨rfl, rfl⟩

private def expectedPacket (valid : Bool) (a b : Nat) : P4bloIR.Value :=
  .struct "Packet" [.header "H" valid [.bits (P4bloIR.Bits.wrap 8 a), .bits (P4bloIR.Bits.wrap 9 b)],
    .bits (P4bloIR.Bits.wrap 16 4660)]

def run : IO Unit := do
  let expressionAnswers : List P4bloIR.Value :=
    [.bits (P4bloIR.Bits.wrap 8 0), .bits (P4bloIR.Bits.wrap 8 0),
      .bits (P4bloIR.Bits.wrap 9 257), .bits (P4bloIR.Bits.wrap 9 8),
      .bits (P4bloIR.Bits.wrap 9 257), .bool true, .bits (P4bloIR.Bits.wrap 9 511)]
  unless expressionCases.length == expressionAnswers.length do
    throw (IO.userError "field expression fixtures/answers differ")
  for (c, expected) in expressionCases.zip expressionAnswers do
    unless Scalar.toValue (denote (store c.valid) c.expression) == expected do
      throw (IO.userError s!"independent field expression answer: {c.name}")
    let (result, _) := (P4bloIR.evaluate (lower c.expression)).run (initial c.valid)
    unless result.toOption == some expected do
      throw (IO.userError s!"lowered field expression answer: {c.name}")
  for valid in [false, true] do
    let source := store valid
    unless (left.get source).val == 171 && (right.get source).val == 257 do
      throw (IO.userError "independent source path read")
    let changed := port.set (right.set (left.set source 7) 511) 19
    unless changed.toValues == [expectedPacket valid 7 511,
        .struct "M" [.bits (P4bloIR.Bits.wrap 9 19), .bool true]] do
      throw (IO.userError "independent source path update, siblings and validity")
    unless changed.validities == [valid] do
      throw (IO.userError "all source validity bits preserved")
    let before := initial valid
    let (read, _) := (P4bloIR.evaluate right.expr).run before
    match read with
    | .ok (.bits value) => unless value.width == 9 && value.value == 257 do
        throw (IO.userError "actual nested field read")
    | _ => throw (IO.userError "actual nested field read failed")
    let (outcome, final) := (P4bloIR.writeLValue right.lvalue (.bits (P4bloIR.Bits.wrap 9 7))).run before
    match outcome with
    | .error _ => throw (IO.userError "actual nested field write failed")
    | .ok () => pure ()
    unless final.frame.read? "hdr" == some (expectedPacket valid 171 7) &&
        final.frame.read? "meta" == some (.struct "M" [.bits (P4bloIR.Bits.wrap 9 3), .bool true]) &&
        final.frame.read? "outside" == some (.header "Outside" false [.bool true]) &&
        final.packet.map (·.cursor) == some 3 && final.emitter.map (·.value) == some 5 &&
        final.visits[("parser", "state")]? == some 13 do
      throw (IO.userError "actual nested field write changed aggregate or unrelated state")
  IO.println "Aggregate source/path answers, 7 field expressions, nested writes and negative shape/type checks passed"

end P4blo.FieldTests
