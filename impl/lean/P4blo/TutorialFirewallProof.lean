import P4blo.TutorialFirewall
import P4blo.SourceZero
import P4bloIR.FrameInitialization

/-! Actual initialization and a bounded property of the real firewall body.
No parser, positive filtering, CRC or complete pipeline theorem is implied. -/

namespace P4blo.TutorialFirewall

set_option maxRecDepth 8192

open P4bloIR P4bloIR.Execution

def index : Index := (Index.build program).toOption.getD default
def initialFrame : Frame := (Frame.forBlock index ingress).toOption.getD default
def scope : BlockScope := index.scopes["MyIngress"]?.getD default

theorem index_built : Index.build program = .ok index := by cbv
theorem scope_lookup : index.scopes[ingress.name]? = some scope := by cbv
theorem scope_block : scope.block = ingress := by cbv

private theorem type_maps :
    index.headerTypes = ((({} : Std.HashMap String HeaderType).insert "ethernet_t"
      ⟨"ethernet_t", Forwarder.ethernetFields.fields⟩).insert "ipv4_t"
      ⟨"ipv4_t", Forwarder.ipv4Fields.fields⟩).insert "tcp_t" ⟨"tcp_t", tcpFields.fields⟩ ∧
    index.structTypes = (({} : Std.HashMap String StructType).insert "headers"
      ⟨"headers", headersFields.fields⟩).insert "metadata"
      ⟨"metadata", Forwarder.metadataFields.fields⟩ := by cbv

theorem roots_agree : roots.IndexAgrees index := by
  simp [roots, headersFields, localFields, tcpFields, Forwarder.ethernetFields,
    Forwarder.ipv4Fields, Forwarder.metadataFields, Fields.Layout.IndexAgrees,
    Fields.Shape.IndexAgrees, FieldLaws.Declared, FieldLaws.NamesWellFormed,
    type_maps.1, type_maps.2, Fields.Layout.fields, Fields.Shape.toIR,
    Scalar.Ty.toIR, Std.HashMap.getElem_insert]

private theorem headers_zero : Value.zero (.struct "headers") index =
    .ok (Fields.Shape.aggregate .struct "headers" headersFields).zero.toValue := by
  apply Fields.Shape.zero_correct _ index roots_agree.1
  simp [headersFields, tcpFields, Forwarder.ethernetFields, Forwarder.ipv4Fields,
    Fields.Shape.zeroFuel, Fields.Layout.zeroFuel, type_maps.1, type_maps.2,
    Std.HashMap.size_insert]

private theorem zeroable : ∀ (name : String) (decl : VarDecl), scope.vars[name]? = some decl →
    ∃ value, Value.zero decl.type index = .ok value := by
  intro name decl hd
  cbv at hd
  simp only [Std.HashMap.getElem?_insert] at hd
  split at hd
  next _ => cases hd; exact ⟨_, rfl⟩
  next _ =>
    split at hd
    next _ => cases hd; exact ⟨_, rfl⟩
    next _ =>
      split at hd
      next _ => cases hd; exact ⟨_, rfl⟩
      next _ =>
        split at hd
        next _ => cases hd; exact ⟨_, rfl⟩
        next _ =>
          split at hd
          next _ => cases hd; exact ⟨_, rfl⟩
          next _ =>
            split at hd
            next _ => cases hd; exact ⟨_, rfl⟩
            next _ =>
              split at hd
              next _ => cases hd; exact ⟨_, rfl⟩
              next _ =>
                split at hd
                next _ => cases hd; exact ⟨_, by cbv⟩
                next _ =>
                  split at hd
                  next _ => cases hd; exact ⟨_, headers_zero⟩
                  next _ => simp at hd

private theorem initialized : ∃ frame, Frame.forBlock index ingress = .ok frame ∧
    frame.scope = scope ∧ frame.action = none ∧ frame.actionVars = none ∧
    ∀ (name : String), frame.vars[name]? =
      (scope.vars[name]?).bind (fun decl => (Value.zero decl.type index).toOption) :=
  Frame.forBlock_initialized index ingress scope scope_lookup zeroable

theorem frame_built : Frame.forBlock index ingress = .ok initialFrame := by
  obtain ⟨frame, hf, _⟩ := initialized
  simp [initialFrame, hf, Except.toOption]

theorem frame_scope : initialFrame.scope = scope := by
  obtain ⟨frame, hf, hs, _⟩ := initialized
  simpa [initialFrame, hf, Except.toOption] using hs

theorem frame_no_action : ScalarStatements.BlockFrame initialFrame := by
  obtain ⟨frame, hf, _, ha, hav, _⟩ := initialized
  simpa [initialFrame, hf, Except.toOption, ScalarStatements.BlockFrame] using And.intro ha hav

theorem frame_values (name : String) : initialFrame.vars[name]? =
    (scope.vars[name]?).bind (fun decl => (Value.zero decl.type index).toOption) := by
  obtain ⟨frame, hf, _, _, _, hv⟩ := initialized
  simpa [initialFrame, hf, Except.toOption] using hv name

/-- Independent scalar answers for every actual local, not an assumed
source-store match or an omitted-variable subset. -/
theorem frame_locals_zero :
    initialFrame.vars["reg_pos_one"]? = some (.bits ⟨32, 0, by decide⟩) ∧
    initialFrame.vars["reg_pos_two"]? = some (.bits ⟨32, 0, by decide⟩) ∧
    initialFrame.vars["reg_val_one"]? = some (.bits ⟨1, 0, by decide⟩) ∧
    initialFrame.vars["reg_val_two"]? = some (.bits ⟨1, 0, by decide⟩) ∧
    initialFrame.vars["direction"]? = some (.bits ⟨1, 0, by decide⟩) ∧
    initialFrame.vars["crc16_result"]? = some (.bits ⟨16, 0, by decide⟩) ∧
    initialFrame.vars["check_ports_hit"]? = some (.bool false) := by
  simp only [frame_values]
  cbv
  exact ⟨rfl, rfl, rfl, rfl, rfl, rfl, trivial⟩

/-- Only the IPv4 validity is constrained. Ethernet, TCP and stored IPv4
contents need not be well typed or initialized for this branch to skip them. -/
def invalidHeaders (ethernet tcp : Value) (ipv4Values : List Value) : Value :=
  .struct "headers" [ethernet, .header "ipv4_t" false ipv4Values, tcp]

def invalidFrame (ethernet tcp metadata : Value) (ipv4Values : List Value) : Frame :=
  { initialFrame with vars := (initialFrame.vars.insert "hdr"
      (invalidHeaders ethernet tcp ipv4Values)).insert "meta" metadata }

theorem invalid_frame_read (ethernet tcp metadata : Value) (ipv4Values : List Value) :
    (invalidFrame ethernet tcp metadata ipv4Values).read? "hdr" =
      some (invalidHeaders ethernet tcp ipv4Values) := by
  simp [invalidFrame, Frame.read?, frame_no_action.2, Std.HashMap.getElem_insert]

theorem invalid_guard (run : Run) (ethernet tcp : Value) (ipv4Values : List Value)
    (hi : run.index = index)
    (hh : run.frame.read? "hdr" = some (invalidHeaders ethernet tcp ipv4Values)) :
    (evaluate ipv4.expr).run run = (.ok (.bool false), run) := by
  have hp : run.index.fieldIndex? "headers" "ipv4" = some 1 := by rw [hi]; cbv
  have field := FieldLaws.fieldOf_pack (kind := .struct) (valid := false)
    (values := [ethernet, .header "ipv4_t" false ipv4Values, tcp]) run hp (by rfl)
  simp [ipv4, Fields.HeaderRef.expr, Fields.HeaderPath.expr, Fields.Slot.name,
    evaluate, ScalarTyping.run_bind, readVar, hh, invalidHeaders,
    FieldLaws.pack] at field ⊢
  rw [field]
  rfl

/-- Whole-Run identity of the actual body under its actual read premise.
All unused locals, metadata, action storage and shared state are arbitrary.
This does not assume that a newly initialized frame was supplied. -/
theorem invalid_ipv4_control_unchanged (run : Run) (ethernet tcp : Value)
    (ipv4Values : List Value) (hi : run.index = index)
    (hh : run.frame.read? "hdr" = some (invalidHeaders ethernet tcp ipv4Values)) :
    (execute ingress.body).run run = (.ok (), run) := by
  have guard := invalid_guard run ethernet tcp ipv4Values hi hh
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

/-- A constructive actual-initialized instance of the more general read-only
body theorem; no new whole-program or positive-filtering premise is hidden. -/
theorem initialized_invalid_body (ethernet tcp metadata : Value) (ipv4Values : List Value) :
    let run : Run := { index, frame := invalidFrame ethernet tcp metadata ipv4Values }
    (execute ingress.body).run run = (.ok (), run) :=
  invalid_ipv4_control_unchanged _ _ _ _ rfl (invalid_frame_read _ _ _ _)

end P4blo.TutorialFirewall
