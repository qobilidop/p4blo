import P4bloIR.CodecLaws

/- Unregistered planning probe: actual declarations, no decoder replacement. -/
namespace DeclarationCodecProbe
open Lean P4bloIR P4bloIR.CodecLaws

private theorem type_object (type : Ty) : ∃ fields, type.toJson = Json.obj fields := by
  cases type <;> exact ⟨_, rfl⟩

def ParamRepresentable (p : Param) : Prop := TypeRepresentable p.type

theorem param_roundtrip (path : String) (p : Param) (h : ParamRepresentable p) :
    Param.decode path p.toJson = .ok p := by
  cases p with | mk name type direction =>
    obtain ⟨fields, obj⟩ := type_object type
    have body : Param.decode path (Param.mk name type direction).toJson =
        ((fun t => Param.mk name t direction) <$> Ty.decode (Decode.sub path "type") type.toJson) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases direction <;> simp only [Param.toJson, obj] <;> rfl
      · cases direction <;> simp only [Param.toJson, Encode.ofStr, empty, obj] <;> rfl
    rw [body, type_roundtrip _ _ h]
    rfl

def MethodRepresentable (m : Method) : Prop :=
  (∀ p ∈ m.params, ParamRepresentable p) ∧ (∀ t ∈ m.returns, TypeRepresentable t)

theorem method_roundtrip (path : String) (m : Method) (h : MethodRepresentable m) :
    Method.decode path m.toJson = .ok m := by
  cases m with | mk name params returns =>
    have body : Method.decode path (Method.mk name params returns).toJson = (do
        let ps ← Decode.array (Decode.sub path "params")
          (.arr (params.map Param.toJson).toArray) Param.decode
        let result ← (returns.map (fun t => some <$> Ty.decode (Decode.sub path "returns") t.toJson)).getD (.ok none)
        pure (Method.mk name ps result)) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases params <;> cases returns with
          | none => rfl
          | some t => obtain ⟨fields, obj⟩ := type_object t; simp only [Method.toJson, Option.map, obj]; rfl
      · cases params <;> cases returns with
          | none => simp only [Method.toJson, Encode.ofStr, empty]; rfl
          | some t =>
            obtain ⟨fields, obj⟩ := type_object t
            simp only [Method.toJson, Encode.ofStr, empty, Option.map, obj]
            rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun p hp q => param_roundtrip q p (h.1 p hp))]
    cases returns with
    | none => rfl
    | some t =>
      change (do
        let result ← some <$> Ty.decode (Decode.sub path "returns") t.toJson
        pure (Method.mk name params result)) = _
      rw [type_roundtrip _ _ (h.2 t (by simp))]
      rfl

def ExternTypeRepresentable (t : ExternType) : Prop :=
  (∀ p ∈ t.constructorParams, ParamRepresentable p) ∧
  (∀ m ∈ t.methods, MethodRepresentable m)

theorem externType_roundtrip (path : String) (t : ExternType) (h : ExternTypeRepresentable t) :
    ExternType.decode path t.toJson = .ok t := by
  cases t with | mk name params methods =>
    have body : ExternType.decode path (ExternType.mk name params methods).toJson = (do
        let ps ← Decode.array (Decode.sub path "constructor_params")
          (.arr (params.map Param.toJson).toArray) Param.decode
        let ms ← Decode.array (Decode.sub path "methods")
          (.arr (methods.map Method.toJson).toArray) Method.decode
        pure (ExternType.mk name ps ms)) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases params <;> cases methods <;> rfl
      · cases params <;> cases methods <;>
          simp only [ExternType.toJson, Encode.ofStr, empty] <;> rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun p hp q => param_roundtrip q p (h.1 p hp))]
    change (ExternType.mk name params <$>
      Decode.array _ (.arr (methods.map Method.toJson).toArray) Method.decode) = _
    rw [array_encoded_roundtrip _ _ _ _ (fun m hm q => method_roundtrip q m (h.2 m hm))]
    rfl

def unusual : ExternType := .mk ""
  [⟨"duplicate", .bits 0, .none⟩, ⟨"duplicate", .stack "missing" 0, .inout⟩]
  [⟨"", [⟨"", .header "missing", .out⟩], some (.bits (2 ^ 32 - 1))⟩,
    ⟨"", [⟨"", .boolean, .«in»⟩], none⟩]

theorem unusual_representable : ExternTypeRepresentable unusual := by
  simp [unusual, ExternTypeRepresentable, MethodRepresentable, ParamRepresentable,
    TypeRepresentable, CodecLaws.UInt32]

theorem unusual_roundtrip (path : String) :
    ExternType.decode path unusual.toJson = .ok unusual :=
  externType_roundtrip path unusual unusual_representable

example : ¬ MethodRepresentable ⟨"", [], some (.bits (2 ^ 32))⟩ := by
  simp [MethodRepresentable, TypeRepresentable, CodecLaws.UInt32]

-- Concrete current acceptance, not a general Python/text codec theorem.
example : Param.decode "p" (Json.mkObj [("type", (Ty.bits 0).toJson)]) =
    .error "p.direction: unspecified" := by rfl
example : Method.decode "m" (Json.mkObj [("returns", Json.null)]) =
    .ok ⟨"", [], none⟩ := by rfl
example : Method.decode "m" (Json.mkObj [("returns", Json.mkObj [])]) =
    .error "m.returns: no kind set" := by rfl

#print axioms param_roundtrip
#print axioms method_roundtrip
#print axioms externType_roundtrip
#print axioms unusual_roundtrip
end DeclarationCodecProbe
