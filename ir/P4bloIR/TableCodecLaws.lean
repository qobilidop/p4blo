import P4bloIR.CodecLaws
import P4bloIR.CodecObjectLaws

/-!
# Wire-only table declaration roundtrips

The actual total codecs compose existing Expr/Literal/KeyValue/list laws.
Only embedded numeric wire bounds are premises. Names, match-kind combinations,
arity, canonical masks, const/default combinations and positivity are unrestricted.
These are not table-selection, semantic-validation or Program codec theorems.
-/

namespace P4bloIR.CodecLaws
open Lean
open CodecObject

def KeyRepresentable (key : Key) : Prop := ExprRepresentable key.expr
def ActionCallRepresentable (call : ActionCall) : Prop :=
  ∀ arg ∈ call.args, LiteralRepresentable arg
def EntryRepresentable (entry : Entry) : Prop :=
  (∀ key ∈ entry.keys, KeyValueRepresentable key) ∧
  ActionCallRepresentable entry.action ∧ UInt32 entry.priority
def TableRepresentable (table : Table) : Prop :=
  (∀ key ∈ table.keys, KeyRepresentable key) ∧
  (∀ call ∈ table.defaultAction, ActionCallRepresentable call) ∧
  (∀ entry ∈ table.constEntries, EntryRepresentable entry) ∧ UInt32 table.size

theorem key_roundtrip (path : String) (key : Key) (h : KeyRepresentable key) :
    Key.decode path key.toJson = .ok key := by
  cases key with | mk expr kind name =>
    have object : ∃ fields, expr.toJson = Json.obj fields := by
      cases expr <;> exact ⟨_, rfl⟩
    obtain ⟨fields, obj⟩ := object
    have body : Key.decode path (Key.mk expr kind name).toJson =
        ((fun e => Key.mk e kind name) <$> Expr.decode (Decode.sub path "expr") expr.toJson) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases kind <;> simp only [Key.toJson, obj] <;> rfl
      · cases kind <;> simp only [Key.toJson, Encode.ofStr, empty, obj] <;> rfl
    rw [body, expr_roundtrip _ _ h]
    rfl

theorem actionCall_roundtrip (path : String) (call : ActionCall)
    (h : ActionCallRepresentable call) : ActionCall.decode path call.toJson = .ok call := by
  cases call with | mk name args =>
    have body : ActionCall.decode path (ActionCall.mk name args).toJson =
        (ActionCall.mk name <$> Decode.array (Decode.sub path "args")
          (.arr (args.map Literal.toJson).toArray) Literal.decode) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases args <;> rfl
      · cases args <;> simp only [ActionCall.toJson, Encode.ofStr, empty] <;> rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun arg ha p => literal_roundtrip p arg (h arg ha))]
    rfl

theorem entry_roundtrip (path : String) (entry : Entry) (h : EntryRepresentable entry) :
    Entry.decode path entry.toJson = .ok entry := by
  cases entry with | mk keys action priority =>
    have object : ∃ fields, action.toJson = Json.obj fields := ⟨_, rfl⟩
    obtain ⟨fields, obj⟩ := object
    have body : Entry.decode path (Entry.mk keys action priority).toJson = (do
        let ks ← Decode.array (Decode.sub path "keys")
          (.arr (keys.map KeyValue.toJson).toArray) KeyValue.decode
        let a ← ActionCall.decode (Decode.sub path "action") action.toJson
        let n ← if priority == 0 then .ok 0 else
          Decode.uint32 (Decode.sub path "priority") (Lean.toJson priority)
        pure (Entry.mk ks a n)) := by
      cases keys <;> by_cases zero : priority == 0 <;>
        simp only [Entry.toJson, Encode.ofNat, zero, obj] <;> rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun key hk p => keyValue_roundtrip p key (h.1 key hk))]
    change (do
      let a ← ActionCall.decode (Decode.sub path "action") action.toJson
      let n ← if priority == 0 then .ok 0 else
        Decode.uint32 (Decode.sub path "priority") (Lean.toJson priority)
      pure (Entry.mk keys a n)) = _
    rw [actionCall_roundtrip _ _ h.2.1]
    by_cases zero : priority == 0
    · have hz : priority = 0 := by simpa using zero
      subst priority
      rfl
    · simp only [zero, Bool.false_eq_true, ↓reduceIte, uint32_toJson _ _ h.2.2]
      rfl

private theorem lookup_opt (key name : String) (value : Option Json) :
    fieldLookup key (Encode.ofOpt name value) =
      if compare name key = .eq then value else none := by
  cases value <;> simp [fieldLookup, Encode.ofOpt]

private theorem lookup_bool (key name : String) (value : Bool) :
    fieldLookup key (Encode.ofBool name value) =
      if compare name key = .eq then (if value then some (.bool true) else none) else none := by
  cases value <;> simp [fieldLookup, Encode.ofBool]

private theorem lookup_nat (key name : String) (value : Nat) :
    fieldLookup key (Encode.ofNat name value) =
      if compare name key = .eq then (if value == 0 then none else some (Lean.toJson value))
      else none := by
  by_cases zero : value == 0 <;> simp [fieldLookup, Encode.ofNat, zero]

private theorem optional_action (path : String) (action : Option ActionCall) :
    (match withoutNull (action.map ActionCall.toJson) with
     | none => Except.ok none | some v => some <$> ActionCall.decode path v) =
      (action.map (fun a => some <$> ActionCall.decode path a.toJson)).getD (.ok none) := by
  cases action <;> rfl

private theorem omitted_bool (path : String) (value : Bool) :
    (match withoutNull (if value then some (.bool true) else none) with
     | none => Except.ok false | some v => Decode.bool path v) = .ok value := by
  cases value <;> rfl

private theorem omitted_nat (path : String) (value : Nat) :
    (match withoutNull (if value = 0 then none else some (Lean.toJson value)) with
     | none => Except.ok 0 | some v => Decode.uint32 path v) =
      if value = 0 then .ok 0 else Decode.uint32 path (Lean.toJson value) := by
  by_cases zero : value = 0 <;> simp only [zero, ↓reduceIte] <;> rfl

theorem table_roundtrip (path : String) (table : Table) (h : TableRepresentable table) :
    Table.decode path table.toJson = .ok table := by
  cases table with | mk name keys actions defaultAction constDefaultAction constEntries size =>
    have body : Table.decode path
        (Table.mk name keys actions defaultAction constDefaultAction constEntries size).toJson = (do
        let ks ← Decode.array (Decode.sub path "keys")
          (.arr (keys.map Key.toJson).toArray) Key.decode
        let names ← Decode.array (Decode.sub path "actions")
          (.arr (actions.map Json.str).toArray) Decode.str
        let default ← (defaultAction.map (fun a =>
          some <$> ActionCall.decode (Decode.sub path "default_action") a.toJson)).getD (.ok none)
        let es ← Decode.array (Decode.sub path "const_entries")
          (.arr (constEntries.map Entry.toJson).toArray) Entry.decode
        let n ← if size == 0 then .ok 0 else
          Decode.uint32 (Decode.sub path "size") (Lean.toJson size)
        pure (Table.mk name ks names default constDefaultAction es n)) := by
      simp only [Table.decode, Decode.strField, Decode.listField, Decode.optField,
        Decode.boolField, Decode.uint32Field, Table.toJson, Encode.obj, get_mkObj,
        List.flatten_cons, List.flatten_nil, fieldLookup_append, fieldLookup_nil,
        lookup_str, lookup_list, lookup_opt, lookup_bool, lookup_nat]
      simp only [bind, Except.bind, pure, Except.pure]
      simp
      unfold Decode.strField.match_1
      have hs := omitted_string (Decode.sub path "name") name
      have hk := omitted_array (Decode.sub path "keys") keys Key.toJson Key.decode
      have ha := omitted_array (Decode.sub path "actions") actions Json.str Decode.str
      have hd := optional_action (Decode.sub path "default_action") defaultAction
      have hb := omitted_bool (Decode.sub path "const_default_action") constDefaultAction
      have he := omitted_array (Decode.sub path "const_entries") constEntries Entry.toJson Entry.decode
      have hn := omitted_nat (Decode.sub path "size") size
      unfold omitted_string.match_1 at hs hk ha hd hb he hn
      unfold optional_action.match_1 at hd hb hn
      rw [hs, hk, ha, hd, hb, he, hn]
      by_cases zero : size = 0 <;> simp [zero]
    have default_roundtrip : (defaultAction.map (fun a =>
        some <$> ActionCall.decode (Decode.sub path "default_action") a.toJson)).getD (.ok none) =
        .ok defaultAction := by
      cases defaultAction with
      | none => rfl
      | some a =>
        simp only [Option.map, Option.getD]
        rw [actionCall_roundtrip _ _ (h.2.1 a (by simp))]
        rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun key hk p => key_roundtrip p key (h.1 key hk)),
      array_encoded_roundtrip _ actions Json.str Decode.str (fun _ _ _ => rfl),
      default_roundtrip,
      array_encoded_roundtrip _ _ _ _ (fun e he p => entry_roundtrip p e (h.2.2.1 e he))]
    by_cases zero : size == 0
    · have hz : size = 0 := by simpa using zero
      subst size
      rfl
    · simp only [zero, Bool.false_eq_true, ↓reduceIte, uint32_toJson _ _ h.2.2.2]
      rfl

end P4bloIR.CodecLaws
