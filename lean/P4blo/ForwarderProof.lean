import P4blo.Forwarder
import P4blo.SourceZero
import P4bloIR.FrameInitialization

/-! A deliberately bounded property of the actual corpus control body.
This is not a parser, table, checksum, action or whole-pipeline proof. -/

namespace P4blo.Forwarder

set_option maxRecDepth 4096

open P4bloIR P4bloIR.Execution

def index : Index := (Index.build program).toOption.getD default
def initialFrame : Frame := (Frame.forBlock index ingress).toOption.getD default
def scope : BlockScope := index.scopes["MyIngress"]?.getD default

theorem index_built : Index.build program = .ok index := by cbv
theorem scope_lookup : index.scopes[ingress.name]? = some scope := by cbv
theorem scope_block : scope.block = ingress := by cbv

private theorem type_maps :
    index.headerTypes = (({} : Std.HashMap String HeaderType).insert "ethernet_t"
      ⟨"ethernet_t", ethernetFields.fields⟩).insert "ipv4_t" ⟨"ipv4_t", ipv4Fields.fields⟩ ∧
    index.structTypes = (({} : Std.HashMap String StructType).insert "headers"
      ⟨"headers", headersFields.fields⟩).insert "metadata" ⟨"metadata", metadataFields.fields⟩ := by cbv

theorem roots_agree : roots.IndexAgrees index := by
  simp [roots, headersFields, ethernetFields, ipv4Fields, metadataFields,
    Fields.Layout.IndexAgrees, Fields.Shape.IndexAgrees, FieldLaws.Declared,
    FieldLaws.NamesWellFormed, type_maps.1, type_maps.2, Fields.Layout.fields,
    Fields.Shape.toIR, Scalar.Ty.toIR, Std.HashMap.getElem_insert]

private theorem headers_zero : Value.zero (.struct "headers") index =
    .ok (Fields.Shape.aggregate .struct "headers" headersFields).zero.toValue := by
  apply Fields.Shape.zero_correct _ index roots_agree.1
  simp [headersFields, ethernetFields, ipv4Fields, Fields.Shape.zeroFuel,
    Fields.Layout.zeroFuel, type_maps.1, type_maps.2, Std.HashMap.size_insert]

private theorem zeroable : ∀ (name : String) (decl : VarDecl), scope.vars[name]? = some decl →
    ∃ value, Value.zero decl.type index = .ok value := by
  intro name decl hd
  cbv at hd
  simp only [Std.HashMap.getElem?_insert] at hd
  split at hd
  · cases hd
    exact ⟨(Fields.Shape.aggregate .struct "metadata" metadataFields).zero.toValue, by cbv⟩
  · split at hd
    · cases hd
      exact ⟨(Fields.Shape.aggregate .struct "headers" headersFields).zero.toValue, headers_zero⟩
    · simp at hd

private theorem initialized : ∃ frame, Frame.forBlock index ingress = .ok frame ∧
    frame.scope = scope ∧ frame.action = none ∧ frame.actionVars = none := by
  obtain ⟨frame, hf, hs, ha, hav, _⟩ :=
    Frame.forBlock_initialized index ingress scope scope_lookup zeroable
  exact ⟨frame, hf, hs, ha, hav⟩

theorem frame_built : Frame.forBlock index ingress = .ok initialFrame := by
  obtain ⟨frame, hf, _⟩ := initialized
  simp [initialFrame, hf, Except.toOption]

theorem frame_block : initialFrame.block = ingress := by
  obtain ⟨frame, hf, hs, _⟩ := initialized
  simpa [initialFrame, hf, Except.toOption, Frame.block, hs] using scope_block

theorem frame_no_action : ScalarStatements.BlockFrame initialFrame := by
  obtain ⟨frame, hf, _, ha, hav⟩ := initialized
  simpa [initialFrame, hf, Except.toOption, ScalarStatements.BlockFrame] using And.intro ha hav

/-- Independent invalid-header input, not an authored guard/accessor result.
Stored IPv4 fields are arbitrary, since this path must not inspect them.
Ethernet may itself be valid or invalid. No global value-validity is asserted. -/
def invalidHeaders (ethernet : Value) (ipv4Values : List Value) : Value :=
  .struct "headers" [ethernet, .header "ipv4_t" false ipv4Values]

/-- Populate the real initialized control frame. Metadata is arbitrary and
must remain unchanged; it is NOT reset or assigned drop by this body. -/
def invalidFrame (ethernet : Value) (ipv4Values : List Value) (metadata : Value) : Frame :=
  { initialFrame with vars := (initialFrame.vars.insert "hdr" (invalidHeaders ethernet ipv4Values)).insert "meta" metadata }

theorem invalid_frame_read (ethernet : Value) (ipv4Values : List Value) (metadata : Value) :
    (invalidFrame ethernet ipv4Values metadata).read? "hdr" =
      some (invalidHeaders ethernet ipv4Values) := by
  simp [invalidFrame, Frame.read?, frame_no_action.2, Std.HashMap.getElem_insert]

theorem invalid_guard (run : Run) (ethernet : Value) (ipv4Values : List Value)
    (hi : run.index = index)
    (hh : run.frame.read? "hdr" = some (invalidHeaders ethernet ipv4Values)) :
    (evaluate ipv4.expr).run run = (.ok (.bool false), run) := by
  have hp : run.index.fieldIndex? "headers" "ipv4" = some 1 := by rw [hi]; cbv
  have field := FieldLaws.fieldOf_pack (kind := .struct) (valid := false)
    (values := [ethernet, .header "ipv4_t" false ipv4Values]) run hp (by rfl)
  simp [ipv4, Fields.HeaderRef.expr, Fields.HeaderPath.expr, Fields.Slot.name,
    evaluate, ScalarTyping.run_bind, readVar, hh, invalidHeaders,
    FieldLaws.pack] at field ⊢
  rw [field]
  rfl

/-- Actual body completion for every shared Run state. Both false guards
skip their table/checksum branches; no callback claims those branches correct.
The frame premise is constructive (`frame_built`), not an arbitrary scope. -/
theorem invalid_ipv4_control_unchanged (run : Run) (ethernet : Value)
    (ipv4Values : List Value) (metadata : Value)
    (hi : run.index = index)
    (hf : run.frame = invalidFrame ethernet ipv4Values metadata) :
    (execute ingress.body).run run = (.ok (), run) := by
  have guard := invalid_guard run ethernet ipv4Values hi
    (hf ▸ invalid_frame_read ethernet ipv4Values metadata)
  have conditional (yes : List Stmt) :
      (dispatch (.statement (.conditional ipv4.expr yes []))).run run =
        (.ok [.statements []], run) := by
    simp [dispatch, ScalarTyping.run_bind, guard, expectBool, Value.expectBool, P4bloIR.liftExcept]
    rfl
  have conditionalStep (yes : List Stmt) (rest : List Work) :
      step { work := .statement (.conditional ipv4.expr yes []) :: rest, run } =
        .inr { work := .statements [] :: rest, run } := by
    simp [step, conditional]
  have trace : Finishes { work := [.statements ingress.body], run } (.ok (), run) := by
    exact .next rfl (.next (conditionalStep _ _) (.next rfl
      (.next rfl (.next (conditionalStep _ _) (.next rfl (.next rfl (.done rfl)))))))
  exact trace.sound

end P4blo.Forwarder
