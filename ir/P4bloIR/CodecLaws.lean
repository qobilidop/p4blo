import P4bloIR.Json
import Init.Data.Nat.ToString
import Init.Data.String.Lemmas

/-!
Laws for the actual leaf codec. Wire representability is deliberately
weaker than semantic validity. These are JSON-value laws, not text-parser
or general recursive-program codec theorems.
-/

namespace P4bloIR.CodecLaws

/-- The actual decimal decoder recovers every canonically printed natural. -/
theorem decimal_toString (path : String) (n : Nat) :
    Decode.decimal path (toString n) = .ok n := by
  have nonempty : (toString n).isEmpty = false := by
    apply String.isEmpty_eq_false_iff.mpr
    exact Nat.repr_ne_empty
  have digits : (toString n).all Char.isDigit = true := by
    rw [String.all_bool_eq, Nat.toString_eq_repr, Nat.toList_repr, List.all_eq_true]
    intro c hc
    exact Nat.isDigit_of_mem_toDigits (by decide) (by decide) hc
  simp only [Decode.decimal, nonempty, Bool.false_eq_true, ↓reduceIte, digits]
  rw [String.foldl_eq_foldl_toList, Nat.toString_eq_repr, Nat.toList_repr]
  change Except.ok ((Nat.toDigits 10 n).foldl
    (fun n c => n * 10 + (c.toNat - '0'.toNat)) 0) = Except.ok n
  congr 1
  simpa [Nat.ofDigitChars_eq_foldl, Nat.mul_comm] using
    (Nat.ofDigitChars_ten_toDigits (n := n))

/-- Exactly the numeric restriction imposed by the protobuf field type. -/
def UInt32 (n : Nat) : Prop := n < 2 ^ 32

/-- All type names, including empty/unresolved names, are representable. -/
def TypeRepresentable : Ty → Prop
  | .bits width => UInt32 width
  | .stack _ size => UInt32 size
  | _ => True

/-- Values need not fit their widths: that is semantic validation, not wire syntax. -/
def LiteralRepresentable : Literal → Prop
  | .bits width _ => UInt32 width
  | _ => True

theorem uint32_toJson (path : String) (n : Nat) (h : UInt32 n) :
    Decode.uint32 path (Lean.toJson n) = .ok n := by
  change (if n < 2 ^ 32 then Except.ok n else
    Decode.fail path s!"{n} does not fit in uint32") = Except.ok n
  simp only [show n < 2 ^ 32 from h, ↓reduceIte]

theorem uint32_toJson_reject (path : String) (n : Nat) (h : ¬ UInt32 n) :
    Decode.uint32 path (Lean.toJson n) =
      .error s!"{path}: {n} does not fit in uint32" := by
  change (if n < 2 ^ 32 then Except.ok n else
    Decode.fail path s!"{n} does not fit in uint32") = _
  simp [show ¬ n < 2 ^ 32 from h, Decode.fail, String.append_assoc]
  rfl

theorem literal_boolean (path : String) (b : Bool) :
    Literal.decode path (Literal.boolean b).toJson = .ok (.boolean b) := by
  rfl

theorem literal_error (path name : String) :
    Literal.decode path (Literal.error name).toJson = .ok (.error name) := by
  rfl

theorem type_bits (path : String) (width : Nat) (h : UInt32 width) :
    Ty.decode path (Ty.bits width).toJson = .ok (.bits width) := by
  change (Ty.bits <$> Decode.uint32 (Decode.sub path "bits") (Lean.toJson width)) = _
  rw [uint32_toJson _ _ h]
  rfl

theorem literal_bits (path : String) (width value : Nat) (h : UInt32 width) :
    Literal.decode path (Literal.bits width value).toJson = .ok (.bits width value) := by
  by_cases zero : width = 0
  · subst width
    change (do
      let value ← Decode.decimal (Decode.sub (Decode.sub path "bits") "value") (toString value)
      pure (Literal.bits 0 value)) = _
    rw [decimal_toString]
    rfl
  · simp only [Literal.toJson, Encode.ofNat, beq_iff_eq, zero, ↓reduceIte]
    change (do
      let width ← Decode.uint32 (Decode.sub (Decode.sub path "bits") "width") (Lean.toJson width)
      let value ← Decode.decimal (Decode.sub (Decode.sub path "bits") "value") (toString value)
      pure (Literal.bits width value)) = _
    rw [uint32_toJson _ _ h]
    change (do
      let value ← Decode.decimal (Decode.sub (Decode.sub path "bits") "value") (toString value)
      pure (Literal.bits width value)) = _
    rw [decimal_toString]
    rfl

theorem literal_enumMember (path enumType member : String) :
    Literal.decode path (Literal.enumMember enumType member).toJson =
      .ok (.enumMember enumType member) := by
  by_cases he : enumType.isEmpty = true <;> by_cases hm : member.isEmpty = true
  all_goals simp only [Literal.toJson, Encode.ofStr, he, hm, ↓reduceIte]
  all_goals simp only [String.isEmpty_iff] at he hm
  all_goals try subst enumType
  all_goals try subst member
  all_goals rfl

/-- Every wire-representable literal round-trips through the production codec. -/
theorem literal_roundtrip (path : String) (value : Literal) (h : LiteralRepresentable value) :
    Literal.decode path value.toJson = .ok value := by
  cases value with
  | bits width value => exact literal_bits path width value h
  | boolean value => exact literal_boolean path value
  | enumMember enumType member => exact literal_enumMember path enumType member
  | error name => exact literal_error path name

theorem type_stack (path header : String) (size : Nat) (h : UInt32 size) :
    Ty.decode path (Ty.stack header size).toJson = .ok (.stack header size) := by
  by_cases empty : header.isEmpty = true <;> by_cases zero : size = 0
  all_goals simp only [Ty.toJson, Encode.ofStr, Encode.ofNat, beq_iff_eq, empty, zero, ↓reduceIte]
  all_goals simp only [String.isEmpty_iff] at empty
  all_goals try subst header
  all_goals try subst size
  all_goals try rfl
  all_goals
    change (do
      let size ← Decode.uint32 (Decode.sub (Decode.sub path "stack") "size") (Lean.toJson size)
      pure (Ty.stack _ size)) = _
    rw [uint32_toJson _ _ h]
    rfl

/-- Empty names and zero widths/sizes remain in the wire domain. -/
theorem type_roundtrip (path : String) (type : Ty) (h : TypeRepresentable type) :
    Ty.decode path type.toJson = .ok type := by
  cases type with
  | bits width => exact type_bits path width h
  | stack header size => exact type_stack path header size h
  | boolean | header _ | struct _ | enumType _ | error => rfl

/-- Key validity is separate: only the numeric protobuf prefix field is bounded. -/
def KeyValueRepresentable : KeyValue → Prop
  | .lpm _ prefixLen => UInt32 prefixLen
  | _ => True

theorem keyValue_exact (path : String) (value : Nat) :
    KeyValue.decode path (KeyValue.exact value).toJson = .ok (.exact value) := by
  change (KeyValue.exact <$> Decode.decimal (Decode.sub path "exact") (toString value)) = _
  rw [decimal_toString]
  rfl

theorem keyValue_lpm (path : String) (value prefixLen : Nat) (h : UInt32 prefixLen) :
    KeyValue.decode path (KeyValue.lpm value prefixLen).toJson = .ok (.lpm value prefixLen) := by
  by_cases zero : prefixLen = 0
  · subst prefixLen
    change (do
      let value ← Decode.decimal (Decode.sub (Decode.sub path "lpm") "value") (toString value)
      pure (KeyValue.lpm value 0)) = _
    rw [decimal_toString]
    rfl
  · simp only [KeyValue.toJson, Encode.ofNat, beq_iff_eq, zero, ↓reduceIte]
    change (do
      let value ← Decode.decimal (Decode.sub (Decode.sub path "lpm") "value") (toString value)
      let prefixLen ← Decode.uint32 (Decode.sub (Decode.sub path "lpm") "prefix_len")
        (Lean.toJson prefixLen)
      pure (KeyValue.lpm value prefixLen)) = _
    rw [decimal_toString]
    change (do
      let prefixLen ← Decode.uint32 (Decode.sub (Decode.sub path "lpm") "prefix_len")
        (Lean.toJson prefixLen)
      pure (KeyValue.lpm value prefixLen)) = _
    rw [uint32_toJson _ _ h]
    rfl

theorem keyValue_ternary (path : String) (value mask : Nat) :
    KeyValue.decode path (KeyValue.ternary value mask).toJson = .ok (.ternary value mask) := by
  -- Infer the actual diagnostic paths: successful roundtrip does not prove
  -- the intended wire field names. Independent wire vectors check that.
  change (do
    let value ← Decode.decimal _ (toString value)
    let mask ← Decode.decimal _ (toString mask)
    pure (KeyValue.ternary value mask)) = _
  rw [decimal_toString]
  change (do
    let mask ← Decode.decimal _ (toString mask)
    pure (KeyValue.ternary value mask)) = _
  rw [decimal_toString]
  rfl

/-- All representable keys round-trip, including semantically noncanonical keys. -/
theorem keyValue_roundtrip (path : String) (key : KeyValue) (h : KeyValueRepresentable key) :
    KeyValue.decode path key.toJson = .ok key := by
  cases key with
  | exact value => exact keyValue_exact path value
  | lpm value prefixLen => exact keyValue_lpm path value prefixLen h
  | ternary value mask => exact keyValue_ternary path value mask

end P4bloIR.CodecLaws
