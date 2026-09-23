import P4blo.CallEntry

/-! Exact execution of the two actual local assignments before the authored
body. This does not establish call lookup, runBlock expansion or copyback. -/

namespace P4blo.CallInitializers
open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements
open Fields FieldCommandExamples

def assignByte (name : String) (value : Nat) : Stmt :=
  .assign (.var name) (.literal (.bits 8 value))

def body : List Stmt := [assignByte "scratch" 19, assignByte "unrelated" 165]

/-- Constructor-based independent source state after local initialization. -/
def bodyStore (hdr : Data headers) (metaData : Data metadata) (routeData : Data route) : Store roots :=
  .cons hdr (.cons metaData (.cons routeData (.cons (.scalar 19) .nil)))

/-- Exact map result, not another executable initializer. -/
def finalRun (initial : Run) : Run :=
  { initial with frame := { initial.frame with
    vars := (initial.frame.vars.insert "scratch" (.bits (Bits.wrap 8 19))).insert
      "unrelated" (.bits (Bits.wrap 8 165)) } }

private theorem byte_dispatch (initial : Run) (name : String) (value : Nat)
    (old : Value) (hb : BlockFrame initial.frame)
    (found : initial.frame.read? name = some old) :
    (dispatch (.statement (assignByte name value))).run initial =
      (.ok [], { initial with frame := { initial.frame with
        vars := initial.frame.vars.insert name (.bits (Bits.wrap 8 value)) } }) := by
  have hw := writeVar_block initial hb found (value := .bits (Bits.wrap 8 value))
  simp [dispatch, assignByte, evaluate, literalValue, Literal.toValue,
    P4bloIR.ScalarTyping.run_map, writeLValue, hw]

/-- Four actual transitions consume exactly two flat-list assignments. -/
theorem steps (initial : Run) (scratchOld unrelatedOld : Value)
    (suffix : List Stmt) (continuation : List Work)
    (hb : BlockFrame initial.frame)
    (hs : initial.frame.read? "scratch" = some scratchOld)
    (hu : initial.frame.read? "unrelated" = some unrelatedOld) :
    Steps { work := .statements (body ++ suffix) :: continuation, run := initial }
      { work := .statements suffix :: continuation, run := finalRun initial } := by
  let middle : Run := { initial with frame := { initial.frame with
    vars := initial.frame.vars.insert "scratch" (.bits (Bits.wrap 8 19)) } }
  have hm : BlockFrame middle.frame := hb
  have hu' : middle.frame.read? "unrelated" = some unrelatedOld := by
    simpa [middle, Frame.read?, hb.2, Std.HashMap.getElem?_insert] using hu
  have h₁ := byte_dispatch initial "scratch" 19 scratchOld hb hs
  have h₂ := byte_dispatch middle "unrelated" 165 unrelatedOld hm hu'
  apply Steps.trans (b := { work := .statements (assignByte "unrelated" 165 :: suffix) :: continuation, run := middle })
  · refine .next rfl (.next ?_ .refl)
    simp [step, h₁, middle]
  · refine .next rfl (.next ?_ .refl)
    simp [step, h₂, finalRun, middle]

theorem changes (initial : Run) : ChangesOnlyVars initial (finalRun initial) := ⟨_, rfl⟩

theorem outside (initial : Run) :
    PreservesOutside ["scratch", "unrelated"] initial (finalRun initial) := by
  intro name hn
  simp only [List.mem_cons, List.mem_nil_iff, or_false, not_or] at hn
  simp [finalRun, Std.HashMap.getElem?_insert, Ne.symm hn.1, Ne.symm hn.2]

theorem source_matches (initial : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (hb : BlockFrame initial.frame)
    (hf : FrameMatches (CallEntry.entryStore hdr metaData routeData) initial.frame) :
    FrameMatches (bodyStore hdr metaData routeData) (finalRun initial).frame := by
  intro shape root
  cases root with
  | here =>
    have h := hf .here
    change initial.frame.read? "hdr" = some hdr.toValue at h
    change (finalRun initial).frame.read? "hdr" = some hdr.toValue
    simpa [Frame.read?, finalRun, hb.2, Std.HashMap.getElem?_insert] using h
  | there root => cases root with
    | here =>
      have h := hf (.there .here)
      change initial.frame.read? "meta" = some metaData.toValue at h
      change (finalRun initial).frame.read? "meta" = some metaData.toValue
      simpa [Frame.read?, finalRun, hb.2, Std.HashMap.getElem?_insert] using h
    | there root => cases root with
      | here =>
        have h := hf (.there (.there .here))
        change initial.frame.read? "route" = some routeData.toValue at h
        change (finalRun initial).frame.read? "route" = some routeData.toValue
        simpa [Frame.read?, finalRun, hb.2, Std.HashMap.getElem?_insert] using h
      | there root => cases root with
        | here =>
          change (finalRun initial).frame.read? "scratch" = some (.bits (Bits.wrap 8 19))
          simp [Frame.read?, finalRun, hb.2, Std.HashMap.getElem_insert]
        | there root => cases root

/-- Declaration permission is a separate obligation from runtime existence. -/
theorem body_typed (index : Index) (scope : BlockScope)
    (hs : scope.var? "scratch" = some (.var ⟨"scratch", .bits 8⟩))
    (hu : scope.var? "unrelated" = some (.var ⟨"unrelated", .bits 8⟩)) :
    P4bloIR.FieldTyping.BodyTyped index scope body := by
  refine .cons (.assign (t := .bits 8) ?_ (.bits 8 19 (by decide) (by decide)))
    (.cons (.assign (t := .bits 8) ?_ (.bits 8 165 (by decide) (by decide))) .nil)
  · exact .var "scratch" (.var ⟨"scratch", .bits 8⟩) (by decide) hs rfl rfl
  · exact .var "unrelated" (.var ⟨"unrelated", .bits 8⟩) (by decide) hu rfl rfl

/-- Source initialization through the actual flat-list prefix; suffix and
continuation are left untouched. No successful execution of either is assumed. -/
theorem source_steps (initial : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (unrelatedOld : Value) (suffix : List Stmt)
    (continuation : List Work) (hb : BlockFrame initial.frame)
    (hf : FrameMatches (CallEntry.entryStore hdr metaData routeData) initial.frame)
    (hu : initial.frame.read? "unrelated" = some unrelatedOld) :
    Steps { work := .statements (body ++ suffix) :: continuation, run := initial }
      { work := .statements suffix :: continuation, run := finalRun initial } ∧
    FrameMatches (bodyStore hdr metaData routeData) (finalRun initial).frame ∧
    (finalRun initial).frame.read? "unrelated" = some (.bits (Bits.wrap 8 165)) ∧
    ChangesOnlyVars initial (finalRun initial) ∧
    PreservesOutside ["scratch", "unrelated"] initial (finalRun initial) := by
  refine ⟨steps initial _ unrelatedOld suffix continuation hb
    (hf (.there (.there (.there .here)))) hu, source_matches initial hdr metaData routeData hb hf,
    ?_, changes initial, outside initial⟩
  simp [finalRun, Frame.read?, hb.2]

end P4blo.CallInitializers
