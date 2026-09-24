import P4bloIR.DeclarationCodecLaws
import P4bloIR.TableCodecLaws
import P4bloIR.ParserCodecLaws

/-!
Actual Action/Block JSON-value roundtrips with inherited numeric wire bounds.
Kinds impose no semantic shape, direction, name-resolution or execution premise.
-/
namespace P4bloIR.CodecLaws
open Lean CodecObject

def ActionRepresentable (a : Action) : Prop :=
  (∀ p ∈ a.params, ParamRepresentable p) ∧ (∀ s ∈ a.body, StmtRepresentable s)
def BlockRepresentable (b : Block) : Prop :=
  (∀ p ∈ b.params, ParamRepresentable p) ∧
  (∀ v ∈ b.locals, VarRepresentable v) ∧
  (∀ a ∈ b.actions, ActionRepresentable a) ∧
  (∀ t ∈ b.tables, TableRepresentable t) ∧
  (∀ s ∈ b.states, StateRepresentable s) ∧
  (∀ s ∈ b.body, StmtRepresentable s)

theorem action_roundtrip (path : String) (a : Action) (h : ActionRepresentable a) :
    Action.decode path a.toJson = .ok a := by
  cases a with | mk name params statements =>
    have body : Action.decode path (Action.mk name params statements).toJson = (do
        let ps ← Decode.array (Decode.sub path "params")
          (.arr (params.map Param.toJson).toArray) Param.decode
        let ss ← Decode.array (Decode.sub path "body")
          (.arr (statements.map Stmt.toJson).toArray) Stmt.decode
        pure (Action.mk name ps ss)) := by
      simp only [Action.decode, Decode.strField, Decode.listField, Action.toJson, Encode.obj,
        get_mkObj, List.flatten_cons, List.flatten_nil, fieldLookup_append, fieldLookup_nil,
        lookup_str, lookup_list]
      simp only [bind, Except.bind, pure, Except.pure]
      simp
      unfold Decode.strField.match_1
      have hn := omitted_string (Decode.sub path "name") name
      have hp := omitted_array (Decode.sub path "params") params Param.toJson Param.decode
      have hs := omitted_array (Decode.sub path "body") statements Stmt.toJson Stmt.decode
      unfold omitted_string.match_1 at hn hp hs
      rw [hn, hp, hs]
    rw [body, array_encoded_roundtrip _ _ _ _ (fun p hp path => param_roundtrip path p (h.1 p hp)),
      array_encoded_roundtrip _ _ _ _ (fun s hs path => stmt_roundtrip path s (h.2 s hs))]
    rfl

private theorem lookup_enum (key name value : String) :
    fieldLookup key (Encode.ofEnum name value) =
      if compare name key = .eq then some (.str value) else none := by
  simp [fieldLookup, Encode.ofEnum]

theorem block_roundtrip (path : String) (b : Block) (h : BlockRepresentable b) :
    Block.decode path b.toJson = .ok b := by
  cases b with | mk name kind params locals actions tables states start statements =>
    have body : Block.decode path
        (Block.mk name kind params locals actions tables states start statements).toJson = (do
        let ps ← Decode.array (Decode.sub path "params")
          (.arr (params.map Param.toJson).toArray) Param.decode
        let vs ← Decode.array (Decode.sub path "locals")
          (.arr (locals.map Var.toJson).toArray) Var.decode
        let as ← Decode.array (Decode.sub path "actions")
          (.arr (actions.map Action.toJson).toArray) Action.decode
        let ts ← Decode.array (Decode.sub path "tables")
          (.arr (tables.map Table.toJson).toArray) Table.decode
        let ss ← Decode.array (Decode.sub path "states")
          (.arr (states.map State.toJson).toArray) State.decode
        let bs ← Decode.array (Decode.sub path "body")
          (.arr (statements.map Stmt.toJson).toArray) Stmt.decode
        pure (Block.mk name kind ps vs as ts ss start bs)) := by
      simp only [Block.decode, Decode.strField, Decode.enumField, Decode.listField,
        Block.toJson, Encode.obj, get_mkObj, List.flatten_cons, List.flatten_nil,
        fieldLookup_append, fieldLookup_nil, lookup_str, lookup_list, lookup_enum]
      simp only [bind, Except.bind, pure, Except.pure]
      simp
      unfold Decode.strField.match_1
      have hn := omitted_string (Decode.sub path "name") name
      have hp := omitted_array (Decode.sub path "params") params Param.toJson Param.decode
      have hv := omitted_array (Decode.sub path "locals") locals Var.toJson Var.decode
      have ha := omitted_array (Decode.sub path "actions") actions Action.toJson Action.decode
      have ht := omitted_array (Decode.sub path "tables") tables Table.toJson Table.decode
      have hs := omitted_array (Decode.sub path "states") states State.toJson State.decode
      have hi := omitted_string (Decode.sub path "start_state") start
      have hb := omitted_array (Decode.sub path "body") statements Stmt.toJson Stmt.decode
      unfold omitted_string.match_1 at hn hp hv ha ht hs hi hb
      rw [hn, hp, hv, ha, ht, hs, hi, hb]
      cases kind <;> rfl
    rw [body,
      array_encoded_roundtrip _ _ _ _ (fun p hp path => param_roundtrip path p (h.1 p hp)),
      array_encoded_roundtrip _ _ _ _ (fun v hv path => var_roundtrip path v (h.2.1 v hv)),
      array_encoded_roundtrip _ _ _ _ (fun a ha path => action_roundtrip path a (h.2.2.1 a ha)),
      array_encoded_roundtrip _ _ _ _ (fun t ht path => table_roundtrip path t (h.2.2.2.1 t ht)),
      array_encoded_roundtrip _ _ _ _ (fun s hs path => state_roundtrip path s (h.2.2.2.2.1 s hs)),
      array_encoded_roundtrip _ _ _ _ (fun s hs path => stmt_roundtrip path s (h.2.2.2.2.2 s hs))]
    rfl

end P4bloIR.CodecLaws
