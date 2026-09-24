import P4bloIR.CodecLaws

/- Unregistered feasibility probe for table declarations, not production coverage. -/
namespace TableCodecProbe
open Lean P4bloIR P4bloIR.CodecLaws

def KeyRepresentable (key : Key) : Prop := ExprRepresentable key.expr
def ActionCallRepresentable (call : ActionCall) : Prop :=
  ∀ arg ∈ call.args, LiteralRepresentable arg
def EntryRepresentable (entry : Entry) : Prop :=
  (∀ key ∈ entry.keys, KeyValueRepresentable key) ∧
  ActionCallRepresentable entry.action ∧ UInt32 entry.priority

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

def unusual : Entry := ⟨[.lpm (2 ^ 100) (2 ^ 32 - 1), .ternary 5 (2 ^ 90), .exact 7],
  ⟨"", [.bits 0 (2 ^ 100), .enumMember "missing" "", .boolean false]⟩, 2 ^ 32 - 1⟩

theorem unusual_representable : EntryRepresentable unusual := by
  simp [unusual, EntryRepresentable, ActionCallRepresentable, KeyValueRepresentable,
    LiteralRepresentable, CodecLaws.UInt32]

theorem unusual_roundtrip (path : String) :
    Entry.decode path unusual.toJson = .ok unusual := entry_roundtrip path unusual unusual_representable

example : ¬ EntryRepresentable ⟨[], ⟨"", []⟩, 2 ^ 32⟩ := by
  simp [EntryRepresentable, CodecLaws.UInt32]
example : ¬ EntryRepresentable ⟨[.lpm 0 (2 ^ 32)], ⟨"", []⟩, 0⟩ := by
  simp [EntryRepresentable, KeyValueRepresentable, CodecLaws.UInt32]

-- Actual accepted defaults: non-optional Entry.action differs from Table.defaultAction.
example : Entry.decode "e" (Json.mkObj []) = .ok ⟨[], ⟨"", []⟩, 0⟩ := by rfl
example : Entry.decode "e" (Json.mkObj [("action", Json.null)]) =
    .ok ⟨[], ⟨"", []⟩, 0⟩ := by rfl
example : Entry.decode "e" (Json.mkObj [("action", Json.mkObj [])]) =
    .ok ⟨[], ⟨"", []⟩, 0⟩ := by rfl
example : Table.decode "t" (Json.mkObj []) = .ok ⟨"", [], [], none, false, [], 0⟩ := by rfl
example : Table.decode "t" (Json.mkObj [("default_action", Json.null)]) =
    .ok ⟨"", [], [], none, false, [], 0⟩ := by rfl
example : Table.decode "t" (Json.mkObj [("default_action", Json.mkObj [])]) =
    .ok ⟨"", [], [], some ⟨"", []⟩, false, [], 0⟩ := by rfl

#print axioms key_roundtrip
#print axioms actionCall_roundtrip
#print axioms entry_roundtrip
#print axioms unusual_roundtrip
end TableCodecProbe
