import P4bloIR.CodecLaws

/-!
# Wire-only roundtrips for foundational declarations

These laws compose the actual total declaration codecs with the existing
type/literal/array laws. They do not validate declarations: empty, duplicate
and unresolved names, aggregate header fields, all directions and unconstrained
extern argument lists are included. Only embedded numeric wire bounds matter.
No Program, text/binary codec, or Python equivalence theorem is asserted here.
-/

namespace P4bloIR.CodecLaws
open Lean

def FieldRepresentable (f : Field) : Prop := TypeRepresentable f.type
def HeaderTypeRepresentable (t : HeaderType) : Prop :=
  ∀ f ∈ t.fields, FieldRepresentable f
def StructTypeRepresentable (t : StructType) : Prop :=
  ∀ f ∈ t.fields, FieldRepresentable f
def EnumTypeRepresentable (_ : EnumType) : Prop := True
def VarRepresentable (v : Var) : Prop := TypeRepresentable v.type
def ParamRepresentable (p : Param) : Prop := TypeRepresentable p.type
def MethodRepresentable (m : Method) : Prop :=
  (∀ p ∈ m.params, ParamRepresentable p) ∧ (∀ t ∈ m.returns, TypeRepresentable t)
def ExternTypeRepresentable (t : ExternType) : Prop :=
  (∀ p ∈ t.constructorParams, ParamRepresentable p) ∧
  (∀ m ∈ t.methods, MethodRepresentable m)
def ExternInstanceRepresentable (i : ExternInstance) : Prop :=
  ∀ a ∈ i.args, LiteralRepresentable a

private theorem declaration_type_object (type : Ty) :
    ∃ fields, type.toJson = Json.obj fields := by
  cases type <;> exact ⟨_, rfl⟩

theorem field_roundtrip (path : String) (f : Field) (h : FieldRepresentable f) :
    Field.decode path f.toJson = .ok f := by
  cases f with | mk name type =>
    obtain ⟨fields, obj⟩ := declaration_type_object type
    have body : Field.decode path (Field.mk name type).toJson =
        (Field.mk name <$> Ty.decode (Decode.sub path "type") type.toJson) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        simp only [Field.toJson, obj]
        rfl
      · simp only [Field.toJson, Encode.ofStr, empty, obj]
        rfl
    rw [body, type_roundtrip _ _ h]
    rfl

theorem headerType_roundtrip (path : String) (t : HeaderType)
    (h : HeaderTypeRepresentable t) : HeaderType.decode path t.toJson = .ok t := by
  cases t with | mk name fields =>
    have body : HeaderType.decode path (HeaderType.mk name fields).toJson =
        (HeaderType.mk name <$> Decode.array (Decode.sub path "fields")
          (.arr (fields.map Field.toJson).toArray) Field.decode) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases fields <;> rfl
      · cases fields <;> simp only [HeaderType.toJson, Encode.ofStr, empty] <;> rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun f hf q => field_roundtrip q f (h f hf))]
    rfl

theorem structType_roundtrip (path : String) (t : StructType)
    (h : StructTypeRepresentable t) : StructType.decode path t.toJson = .ok t := by
  cases t with | mk name fields =>
    have body : StructType.decode path (StructType.mk name fields).toJson =
        (StructType.mk name <$> Decode.array (Decode.sub path "fields")
          (.arr (fields.map Field.toJson).toArray) Field.decode) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases fields <;> rfl
      · cases fields <;> simp only [StructType.toJson, Encode.ofStr, empty] <;> rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun f hf q => field_roundtrip q f (h f hf))]
    rfl

/-- All enum declarations are wire-representable, with no member restrictions. -/
theorem enumType_roundtrip (path : String) (t : EnumType) :
    EnumType.decode path t.toJson = .ok t := by
  cases t with | mk name members =>
    have body : EnumType.decode path (EnumType.mk name members).toJson =
        (EnumType.mk name <$> Decode.array (Decode.sub path "members")
          (.arr (members.map Json.str).toArray) Decode.str) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases members <;> rfl
      · cases members <;> simp only [EnumType.toJson, Encode.ofStr, empty] <;> rfl
    rw [body, array_encoded_roundtrip _ members Json.str Decode.str (fun _ _ _ => rfl)]
    rfl

theorem var_roundtrip (path : String) (v : Var) (h : VarRepresentable v) :
    Var.decode path v.toJson = .ok v := by
  cases v with | mk name type =>
    obtain ⟨fields, obj⟩ := declaration_type_object type
    have body : Var.decode path (Var.mk name type).toJson =
        (Var.mk name <$> Ty.decode (Decode.sub path "type") type.toJson) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        simp only [Var.toJson, obj]
        rfl
      · simp only [Var.toJson, Encode.ofStr, empty, obj]
        rfl
    rw [body, type_roundtrip _ _ h]
    rfl

theorem param_roundtrip (path : String) (p : Param) (h : ParamRepresentable p) :
    Param.decode path p.toJson = .ok p := by
  cases p with | mk name type direction =>
    obtain ⟨fields, obj⟩ := declaration_type_object type
    have body : Param.decode path (Param.mk name type direction).toJson =
        ((fun t => Param.mk name t direction) <$> Ty.decode (Decode.sub path "type") type.toJson) := by
      by_cases empty : name.isEmpty = true
      · have zero : name = "" := String.isEmpty_iff.mp empty
        subst name
        cases direction <;> simp only [Param.toJson, obj] <;> rfl
      · cases direction <;> simp only [Param.toJson, Encode.ofStr, empty, obj] <;> rfl
    rw [body, type_roundtrip _ _ h]
    rfl

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
          | some t =>
            obtain ⟨fields, obj⟩ := declaration_type_object t
            simp only [Method.toJson, Option.map, obj]
            rfl
      · cases params <;> cases returns with
          | none => simp only [Method.toJson, Encode.ofStr, empty]; rfl
          | some t =>
            obtain ⟨fields, obj⟩ := declaration_type_object t
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

theorem externInstance_roundtrip (path : String) (i : ExternInstance)
    (h : ExternInstanceRepresentable i) : ExternInstance.decode path i.toJson = .ok i := by
  cases i with | mk name externType args =>
    have body : ExternInstance.decode path (ExternInstance.mk name externType args).toJson =
        (ExternInstance.mk name externType <$> Decode.array (Decode.sub path "args")
          (.arr (args.map Literal.toJson).toArray) Literal.decode) := by
      by_cases emptyName : name.isEmpty = true <;>
        by_cases emptyType : externType.isEmpty = true
      all_goals
        try have zero := String.isEmpty_iff.mp emptyName; subst name
        try have zero := String.isEmpty_iff.mp emptyType; subst externType
        cases args <;> simp only [ExternInstance.toJson, Encode.ofStr, *] <;> rfl
    rw [body, array_encoded_roundtrip _ _ _ _ (fun a ha q => literal_roundtrip q a (h a ha))]
    rfl

end P4bloIR.CodecLaws
