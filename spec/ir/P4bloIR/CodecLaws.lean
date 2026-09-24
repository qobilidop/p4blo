import P4bloIR.Json
import Init.Data.Nat.ToString
import Init.Data.String.Lemmas

/-!
Laws for actual leaf, expression, lvalue, argument and statement codecs. Representability is
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

/-- Syntax representability, without typing, name resolution or slice validity. -/
def ExprRepresentable : Expr → Prop
  | .literal value => LiteralRepresentable value
  | .var _ => True
  | .member base _ | .lastIndex base | .unary _ base | .isValid base => ExprRepresentable base
  | .index base index | .binary _ base index => ExprRepresentable base ∧ ExprRepresentable index
  | .cast type operand => TypeRepresentable type ∧ ExprRepresentable operand
  | .slice operand hi lo => ExprRepresentable operand ∧ UInt32 hi ∧ UInt32 lo
  | .mux condition then_ otherwise =>
      ExprRepresentable condition ∧ ExprRepresentable then_ ∧ ExprRepresentable otherwise
  | .lookahead type => TypeRepresentable type

private theorem expr_object (value : Expr) : ∃ fields, value.toJson = Lean.Json.obj fields := by
  cases value <;> exact ⟨_, rfl⟩

private theorem literal_object (value : Literal) : ∃ fields, value.toJson = Lean.Json.obj fields := by
  cases value <;> exact ⟨_, rfl⟩

private theorem type_object (value : Ty) : ∃ fields, value.toJson = Lean.Json.obj fields := by
  cases value <;> exact ⟨_, rfl⟩

theorem expr_var (path name : String) : Expr.decode path (Expr.var name).toJson = .ok (.var name) := by
  rw [Expr.decode_unfold]
  rfl

theorem expr_literal (path : String) (value : Literal) (h : LiteralRepresentable value) :
    Expr.decode path (Expr.literal value).toJson = .ok (.literal value) := by
  obtain ⟨fields, obj⟩ := literal_object value
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, obj]
  change (Expr.literal <$> Literal.decode (Decode.sub path "literal") (Lean.Json.obj fields)) = _
  rw [← obj, literal_roundtrip _ _ h]
  rfl

theorem expr_member (path field : String) (base : Expr)
    (ih : ∀ p, Expr.decode p base.toJson = .ok base) :
    Expr.decode path (Expr.member base field).toJson = .ok (.member base field) := by
  obtain ⟨fields, obj⟩ := expr_object base
  rw [Expr.decode_unfold]
  by_cases empty : field.isEmpty = true
  all_goals simp only [Expr.toJson, Encode.ofStr, empty, ↓reduceIte, obj]
  · have zero : field = "" := String.isEmpty_iff.mp empty
    subst field
    change ((fun value => Expr.member value "") <$> Expr.decode _ (Lean.Json.obj fields)) = _
    rw [← obj, ih]
    rfl
  · change ((fun value => Expr.member value field) <$> Expr.decode _ (Lean.Json.obj fields)) = _
    rw [← obj, ih]
    rfl

theorem expr_index (path : String) (base index : Expr)
    (hb : ∀ p, Expr.decode p base.toJson = .ok base)
    (hi : ∀ p, Expr.decode p index.toJson = .ok index) :
    Expr.decode path (Expr.index base index).toJson = .ok (.index base index) := by
  obtain ⟨bf, bo⟩ := expr_object base
  obtain ⟨ixf, ixo⟩ := expr_object index
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, bo, ixo]
  change (do
    let b ← Expr.decode _ (.obj bf)
    let i ← Expr.decode _ (.obj ixf)
    pure (Expr.index b i)) = _
  rw [← bo, hb]
  change (Expr.index base <$> Expr.decode _ (.obj ixf)) = _
  rw [← ixo, hi]
  rfl

theorem expr_lastIndex (path : String) (stack : Expr)
    (ih : ∀ p, Expr.decode p stack.toJson = .ok stack) :
    Expr.decode path (Expr.lastIndex stack).toJson = .ok (.lastIndex stack) := by
  obtain ⟨fields, obj⟩ := expr_object stack
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, obj]
  change (Expr.lastIndex <$> Expr.decode _ (.obj fields)) = _
  rw [← obj, ih]
  rfl

theorem expr_unary (path : String) (op : UnaryOp) (operand : Expr)
    (ih : ∀ p, Expr.decode p operand.toJson = .ok operand) :
    Expr.decode path (Expr.unary op operand).toJson = .ok (.unary op operand) := by
  obtain ⟨fields, obj⟩ := expr_object operand
  rw [Expr.decode_unfold]
  cases op
  all_goals simp only [Expr.toJson, obj]
  all_goals change (Expr.unary _ <$> Expr.decode _ (.obj fields)) = _
  all_goals rw [← obj, ih]; rfl

theorem expr_binary (path : String) (op : BinaryOp) (left right : Expr)
    (hl : ∀ p, Expr.decode p left.toJson = .ok left)
    (hr : ∀ p, Expr.decode p right.toJson = .ok right) :
    Expr.decode path (Expr.binary op left right).toJson = .ok (.binary op left right) := by
  obtain ⟨lf, lo⟩ := expr_object left
  obtain ⟨rf, ro⟩ := expr_object right
  rw [Expr.decode_unfold]
  cases op
  all_goals simp only [Expr.toJson, lo, ro]
  all_goals change (do
    let l ← Expr.decode _ (.obj lf)
    let r ← Expr.decode _ (.obj rf)
    pure (Expr.binary _ l r)) = _
  all_goals rw [← lo, hl]
  all_goals change (Expr.binary _ left <$> Expr.decode _ (.obj rf)) = _
  all_goals rw [← ro, hr]; rfl

theorem expr_cast (path : String) (type : Ty) (operand : Expr)
    (ht : TypeRepresentable type) (ih : ∀ p, Expr.decode p operand.toJson = .ok operand) :
    Expr.decode path (Expr.cast type operand).toJson = .ok (.cast type operand) := by
  obtain ⟨tf, to⟩ := type_object type
  obtain ⟨fields, obj⟩ := expr_object operand
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, to, obj]
  change (do
    let t ← Ty.decode _ (.obj tf)
    let e ← Expr.decode _ (.obj fields)
    pure (Expr.cast t e)) = _
  rw [← to, type_roundtrip _ _ ht]
  change (Expr.cast type <$> Expr.decode _ (.obj fields)) = _
  rw [← obj, ih]
  rfl

theorem expr_isValid (path : String) (header : Expr)
    (ih : ∀ p, Expr.decode p header.toJson = .ok header) :
    Expr.decode path (Expr.isValid header).toJson = .ok (.isValid header) := by
  obtain ⟨fields, obj⟩ := expr_object header
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, obj]
  change (Expr.isValid <$> Expr.decode _ (.obj fields)) = _
  rw [← obj, ih]
  rfl

theorem expr_lookahead (path : String) (type : Ty) (h : TypeRepresentable type) :
    Expr.decode path (Expr.lookahead type).toJson = .ok (.lookahead type) := by
  obtain ⟨fields, obj⟩ := type_object type
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, obj]
  change (Expr.lookahead <$> Ty.decode _ (.obj fields)) = _
  rw [← obj, type_roundtrip _ _ h]
  rfl

theorem expr_slice (path : String) (operand : Expr) (hi lo : Nat)
    (ih : ∀ p, Expr.decode p operand.toJson = .ok operand) (hh : UInt32 hi) (hl : UInt32 lo) :
    Expr.decode path (Expr.slice operand hi lo).toJson = .ok (.slice operand hi lo) := by
  obtain ⟨fields, obj⟩ := expr_object operand
  rw [Expr.decode_unfold]
  by_cases hz : hi = 0 <;> by_cases lz : lo = 0
  all_goals simp only [Expr.toJson, Encode.ofNat, beq_iff_eq, hz, lz, ↓reduceIte, obj]
  all_goals try subst hi
  all_goals try subst lo
  · change ((fun e => Expr.slice e 0 0) <$> Expr.decode _ (.obj fields)) = _
    rw [← obj, ih]
    rfl
  · change (do
      let e ← Expr.decode _ (.obj fields)
      let l ← Decode.uint32 _ (Lean.toJson lo)
      pure (Expr.slice e 0 l)) = _
    rw [← obj, ih]
    change ((fun l => Expr.slice operand 0 l) <$> Decode.uint32 _ (Lean.toJson lo)) = _
    rw [uint32_toJson _ _ hl]
    rfl
  · change (do
      let e ← Expr.decode _ (.obj fields)
      let h ← Decode.uint32 _ (Lean.toJson hi)
      pure (Expr.slice e h 0)) = _
    rw [← obj, ih]
    change ((fun h => Expr.slice operand h 0) <$> Decode.uint32 _ (Lean.toJson hi)) = _
    rw [uint32_toJson _ _ hh]
    rfl
  · change (do
      let e ← Expr.decode _ (.obj fields)
      let h ← Decode.uint32 _ (Lean.toJson hi)
      let l ← Decode.uint32 _ (Lean.toJson lo)
      pure (Expr.slice e h l)) = _
    rw [← obj, ih]
    change (do
      let h ← Decode.uint32 _ (Lean.toJson hi)
      let l ← Decode.uint32 _ (Lean.toJson lo)
      pure (Expr.slice operand h l)) = _
    rw [uint32_toJson _ _ hh]
    change (Expr.slice operand hi <$> Decode.uint32 _ (Lean.toJson lo)) = _
    rw [uint32_toJson _ _ hl]
    rfl

theorem expr_mux (path : String) (condition then_ otherwise : Expr)
    (hc : ∀ p, Expr.decode p condition.toJson = .ok condition)
    (ht : ∀ p, Expr.decode p then_.toJson = .ok then_)
    (ho : ∀ p, Expr.decode p otherwise.toJson = .ok otherwise) :
    Expr.decode path (Expr.mux condition then_ otherwise).toJson = .ok (.mux condition then_ otherwise) := by
  obtain ⟨cf, co⟩ := expr_object condition
  obtain ⟨tf, to⟩ := expr_object then_
  obtain ⟨of_, oo⟩ := expr_object otherwise
  rw [Expr.decode_unfold]
  simp only [Expr.toJson, co, to, oo]
  change (do
    let c ← Expr.decode _ (.obj cf)
    let t ← Expr.decode _ (.obj tf)
    let o ← Expr.decode _ (.obj of_)
    pure (Expr.mux c t o)) = _
  rw [← co, hc]
  change (do
    let t ← Expr.decode _ (.obj tf)
    let o ← Expr.decode _ (.obj of_)
    pure (Expr.mux condition t o)) = _
  rw [← to, ht]
  change (Expr.mux condition then_ <$> Expr.decode _ (.obj of_)) = _
  rw [← oo, ho]
  rfl

/-- All representable expressions round-trip through the actual recursive codec. -/
theorem expr_roundtrip (path : String) (value : Expr) (h : ExprRepresentable value) :
    Expr.decode path value.toJson = .ok value := by
  induction value generalizing path with
  | literal value => exact expr_literal path value h
  | var name => exact expr_var path name
  | member base field ih => exact expr_member path field base (fun p => ih p h)
  | index base index ihb ihi =>
    exact expr_index path base index
      (fun p => ihb p h.1) (fun p => ihi p h.2)
  | lastIndex stack ih => exact expr_lastIndex path stack (fun p => ih p h)
  | unary op operand ih => exact expr_unary path op operand (fun p => ih p h)
  | binary op left right ihl ihr =>
    exact expr_binary path op left right
      (fun p => ihl p h.1) (fun p => ihr p h.2)
  | cast type operand ih => exact expr_cast path type operand h.1 (fun p => ih p h.2)
  | slice operand hi lo ih => exact expr_slice path operand hi lo (fun p => ih p h.1) h.2.1 h.2.2
  | isValid header ih => exact expr_isValid path header (fun p => ih p h)
  | mux condition then_ otherwise ihc iht iho =>
    exact expr_mux path condition then_ otherwise
      (fun p => ihc p h.1) (fun p => iht p h.2.1) (fun p => iho p h.2.2)
  | lookahead type => exact expr_lookahead path type h

/-- Only nested index expressions add wire bounds; names need not resolve. -/
def LValueRepresentable : LValue → Prop
  | .var _ => True
  | .member base _ | .next base => LValueRepresentable base
  | .index base index => LValueRepresentable base ∧ ExprRepresentable index

def ArgRepresentable : Arg → Prop
  | .expr value => ExprRepresentable value
  | .lvalue value => LValueRepresentable value

private theorem lvalue_object (value : LValue) : ∃ fields, value.toJson = Lean.Json.obj fields := by
  cases value <;> exact ⟨_, rfl⟩

theorem lvalue_var (path name : String) :
    LValue.decode path (LValue.var name).toJson = .ok (.var name) := by
  rw [LValue.decode_unfold]
  rfl

theorem lvalue_member (path field : String) (base : LValue)
    (ih : ∀ p, LValue.decode p base.toJson = .ok base) :
    LValue.decode path (LValue.member base field).toJson = .ok (.member base field) := by
  obtain ⟨fields, obj⟩ := lvalue_object base
  rw [LValue.decode_unfold]
  by_cases empty : field.isEmpty = true
  all_goals simp only [LValue.toJson, Encode.ofStr, empty, ↓reduceIte, obj]
  · have zero : field = "" := String.isEmpty_iff.mp empty
    subst field
    change ((fun value => LValue.member value "") <$> LValue.decode _ (Lean.Json.obj fields)) = _
    rw [← obj, ih]
    rfl
  · change ((fun value => LValue.member value field) <$> LValue.decode _ (Lean.Json.obj fields)) = _
    rw [← obj, ih]
    rfl

theorem lvalue_index (path : String) (base : LValue) (index : Expr)
    (hb : ∀ p, LValue.decode p base.toJson = .ok base) (hi : ExprRepresentable index) :
    LValue.decode path (LValue.index base index).toJson = .ok (.index base index) := by
  obtain ⟨bf, bo⟩ := lvalue_object base
  obtain ⟨ixf, ixo⟩ := expr_object index
  rw [LValue.decode_unfold]
  simp only [LValue.toJson, bo, ixo]
  change (do
    let b ← LValue.decode _ (.obj bf)
    let i ← Expr.decode _ (.obj ixf)
    pure (LValue.index b i)) = _
  rw [← bo, hb]
  change (LValue.index base <$> Expr.decode _ (.obj ixf)) = _
  rw [← ixo, expr_roundtrip _ _ hi]
  rfl

theorem lvalue_next (path : String) (stack : LValue)
    (ih : ∀ p, LValue.decode p stack.toJson = .ok stack) :
    LValue.decode path (LValue.next stack).toJson = .ok (.next stack) := by
  obtain ⟨fields, obj⟩ := lvalue_object stack
  rw [LValue.decode_unfold]
  simp only [LValue.toJson, obj]
  change (LValue.next <$> LValue.decode _ (.obj fields)) = _
  rw [← obj, ih]
  rfl

/-- Every representable LValue round-trips through its actual total decoder. -/
theorem lvalue_roundtrip (path : String) (value : LValue) (h : LValueRepresentable value) :
    LValue.decode path value.toJson = .ok value := by
  induction value generalizing path with
  | var name => exact lvalue_var path name
  | member base field ih => exact lvalue_member path field base (fun p => ih p h)
  | index base index ih => exact lvalue_index path base index (fun p => ih p h.1) h.2
  | next stack ih => exact lvalue_next path stack (fun p => ih p h)

theorem arg_expr (path : String) (value : Expr) (h : ExprRepresentable value) :
    Arg.decode path (Arg.expr value).toJson = .ok (.expr value) := by
  obtain ⟨fields, obj⟩ := expr_object value
  simp only [Arg.toJson, obj]
  change (Arg.expr <$> Expr.decode _ (.obj fields)) = _
  rw [← obj, expr_roundtrip _ _ h]
  rfl

theorem arg_lvalue (path : String) (value : LValue) (h : LValueRepresentable value) :
    Arg.decode path (Arg.lvalue value).toJson = .ok (.lvalue value) := by
  obtain ⟨fields, obj⟩ := lvalue_object value
  simp only [Arg.toJson, obj]
  change (Arg.lvalue <$> LValue.decode _ (.obj fields)) = _
  rw [← obj, lvalue_roundtrip _ _ h]
  rfl

/-- Argument syntax representability does not assert call-direction validity. -/
theorem arg_roundtrip (path : String) (value : Arg) (h : ArgRepresentable value) :
    Arg.decode path value.toJson = .ok value := by
  cases value with
  | expr value => exact arg_expr path value h
  | lvalue value => exact arg_lvalue path value h

/-- Ordered encoded arrays, using a per-member law at every diagnostic path. -/
theorem array_encoded_roundtrip (path : String) (xs : List α)
    (encode : α → Lean.Json) (decode : String → Lean.Json → Decode.Dec α)
    (h : ∀ x ∈ xs, ∀ p, decode p (encode x) = .ok x) :
    Decode.array path (.arr (xs.map encode).toArray) decode = .ok xs := by
  have go (ys : List α) (acc : Array α)
      (hy : ∀ x ∈ ys, ∀ p, decode p (encode x) = .ok x) :
      List.mapIdxM.go (fun i x => decode (Decode.at_ path i) x) (ys.map encode) acc =
        .ok (acc.toList ++ ys) := by
    induction ys generalizing acc with
    | nil => simp [List.mapIdxM.go, pure, Except.pure]
    | cons head tail ih =>
      simp only [List.map_cons, List.mapIdxM.go, hy head (by simp), bind, Except.bind]
      simpa using ih (acc.push head) (fun x hx => hy x (by simp [hx]))
  simp only [Decode.array]
  rw [Array.toList_mapIdxM]
  simpa [List.mapIdxM] using go xs #[] h

/-- Wire restrictions only: no name, direction, arity or execution validity. -/
def StmtRepresentable : Stmt → Prop
  | .assign target value => LValueRepresentable target ∧ ExprRepresentable value
  | .conditional condition yes no => ExprRepresentable condition ∧
      (∀ s ∈ yes, StmtRepresentable s) ∧ (∀ s ∈ no, StmtRepresentable s)
  | .apply _ hit => ∀ value ∈ hit, LValueRepresentable value
  | .callAction _ args | .callBlock _ args => ∀ value ∈ args, ArgRepresentable value
  | .callExtern _ _ args result => (∀ value ∈ args, ArgRepresentable value) ∧
      (∀ value ∈ result, LValueRepresentable value)
  | .setValid header | .setInvalid header | .extract header => LValueRepresentable header
  | .push stack count | .pop stack count => LValueRepresentable stack ∧ UInt32 count
  | .advance value | .verify value _ | .emit value => ExprRepresentable value

theorem stmt_assign (path : String) (target : LValue) (value : Expr)
    (ht : LValueRepresentable target) (hv : ExprRepresentable value) :
    Stmt.decode path (Stmt.assign target value).toJson = .ok (.assign target value) := by
  obtain ⟨tf, tobj⟩ := lvalue_object target
  obtain ⟨vf, vobj⟩ := expr_object value
  rw [Stmt.decode_unfold]
  simp only [Stmt.toJson, tobj, vobj]
  change (do
    let t ← LValue.decode _ (.obj tf)
    let v ← Expr.decode _ (.obj vf)
    pure (Stmt.assign t v)) = _
  rw [← tobj, lvalue_roundtrip _ _ ht]
  change (Stmt.assign target <$> Expr.decode _ (.obj vf)) = _
  rw [← vobj, expr_roundtrip _ _ hv]
  rfl

theorem stmt_setValid (path : String) (header : LValue) (h : LValueRepresentable header) :
    Stmt.decode path (Stmt.setValid header).toJson = .ok (.setValid header) := by
  obtain ⟨fields, obj⟩ := lvalue_object header
  rw [Stmt.decode_unfold]
  simp only [Stmt.toJson, obj]
  change (Stmt.setValid <$> LValue.decode _ (.obj fields)) = _
  rw [← obj, lvalue_roundtrip _ _ h]
  rfl

theorem stmt_setInvalid (path : String) (header : LValue) (h : LValueRepresentable header) :
    Stmt.decode path (Stmt.setInvalid header).toJson = .ok (.setInvalid header) := by
  obtain ⟨fields, obj⟩ := lvalue_object header
  rw [Stmt.decode_unfold]
  simp only [Stmt.toJson, obj]
  change (Stmt.setInvalid <$> LValue.decode _ (.obj fields)) = _
  rw [← obj, lvalue_roundtrip _ _ h]
  rfl

theorem stmt_extract (path : String) (target : LValue) (h : LValueRepresentable target) :
    Stmt.decode path (Stmt.extract target).toJson = .ok (.extract target) := by
  obtain ⟨fields, obj⟩ := lvalue_object target
  rw [Stmt.decode_unfold]
  simp only [Stmt.toJson, obj]
  change (Stmt.extract <$> LValue.decode _ (.obj fields)) = _
  rw [← obj, lvalue_roundtrip _ _ h]
  rfl

theorem stmt_advance (path : String) (value : Expr) (h : ExprRepresentable value) :
    Stmt.decode path (Stmt.advance value).toJson = .ok (.advance value) := by
  obtain ⟨fields, obj⟩ := expr_object value
  rw [Stmt.decode_unfold]
  simp only [Stmt.toJson, obj]
  change (Stmt.advance <$> Expr.decode _ (.obj fields)) = _
  rw [← obj, expr_roundtrip _ _ h]
  rfl

theorem stmt_emit (path : String) (value : Expr) (h : ExprRepresentable value) :
    Stmt.decode path (Stmt.emit value).toJson = .ok (.emit value) := by
  obtain ⟨fields, obj⟩ := expr_object value
  rw [Stmt.decode_unfold]
  simp only [Stmt.toJson, obj]
  change (Stmt.emit <$> Expr.decode _ (.obj fields)) = _
  rw [← obj, expr_roundtrip _ _ h]
  rfl

theorem stmt_verify (path error : String) (value : Expr) (h : ExprRepresentable value) :
    Stmt.decode path (Stmt.verify value error).toJson = .ok (.verify value error) := by
  obtain ⟨fields, obj⟩ := expr_object value
  rw [Stmt.decode_unfold]
  by_cases empty : error.isEmpty = true
  all_goals simp only [Stmt.toJson, Encode.ofStr, empty, ↓reduceIte, obj]
  · have zero : error = "" := String.isEmpty_iff.mp empty
    subst error
    change ((fun v => Stmt.verify v "") <$> Expr.decode _ (.obj fields)) = _
    rw [← obj, expr_roundtrip _ _ h]
    rfl
  · change ((fun v => Stmt.verify v error) <$> Expr.decode _ (.obj fields)) = _
    rw [← obj, expr_roundtrip _ _ h]
    rfl

theorem stmt_push (path : String) (stack : LValue) (count : Nat)
    (hs : LValueRepresentable stack) (hc : UInt32 count) :
    Stmt.decode path (Stmt.push stack count).toJson = .ok (.push stack count) := by
  obtain ⟨fields, obj⟩ := lvalue_object stack
  rw [Stmt.decode_unfold]
  by_cases zero : count = 0
  · subst count
    simp only [Stmt.toJson, obj]
    change ((fun s => Stmt.push s 0) <$> LValue.decode _ (.obj fields)) = _
    rw [← obj, lvalue_roundtrip _ _ hs]
    rfl
  · simp only [Stmt.toJson, Encode.ofNat, beq_iff_eq, zero, ↓reduceIte, obj]
    change (do
      let s ← LValue.decode _ (.obj fields)
      let n ← Decode.uint32 _ (Lean.toJson count)
      pure (Stmt.push s n)) = _
    rw [← obj, lvalue_roundtrip _ _ hs]
    change (Stmt.push stack <$> Decode.uint32 _ (Lean.toJson count)) = _
    rw [uint32_toJson _ _ hc]
    rfl

theorem stmt_pop (path : String) (stack : LValue) (count : Nat)
    (hs : LValueRepresentable stack) (hc : UInt32 count) :
    Stmt.decode path (Stmt.pop stack count).toJson = .ok (.pop stack count) := by
  obtain ⟨fields, obj⟩ := lvalue_object stack
  rw [Stmt.decode_unfold]
  by_cases zero : count = 0
  · subst count
    simp only [Stmt.toJson, obj]
    change ((fun s => Stmt.pop s 0) <$> LValue.decode _ (.obj fields)) = _
    rw [← obj, lvalue_roundtrip _ _ hs]
    rfl
  · simp only [Stmt.toJson, Encode.ofNat, beq_iff_eq, zero, ↓reduceIte, obj]
    change (do
      let s ← LValue.decode _ (.obj fields)
      let n ← Decode.uint32 _ (Lean.toJson count)
      pure (Stmt.pop s n)) = _
    rw [← obj, lvalue_roundtrip _ _ hs]
    change (Stmt.pop stack <$> Decode.uint32 _ (Lean.toJson count)) = _
    rw [uint32_toJson _ _ hc]
    rfl

theorem stmt_conditional (path : String) (condition : Expr) (yes no : List Stmt)
    (hc : ExprRepresentable condition)
    (hy : ∀ s ∈ yes, ∀ p, Stmt.decode p s.toJson = .ok s)
    (hn : ∀ s ∈ no, ∀ p, Stmt.decode p s.toJson = .ok s) :
    Stmt.decode path (Stmt.conditional condition yes no).toJson =
      .ok (.conditional condition yes no) := by
  obtain ⟨fields, obj⟩ := expr_object condition
  have body : Stmt.decode path (Stmt.conditional condition yes no).toJson = (do
      let c ← Expr.decode (Decode.sub (Decode.sub path "conditional") "condition") condition.toJson
      let y ← Decode.array (Decode.sub (Decode.sub path "conditional") "then")
        (.arr (yes.map Stmt.toJson).toArray) Stmt.decode
      let n ← Decode.array (Decode.sub (Decode.sub path "conditional") "otherwise")
        (.arr (no.map Stmt.toJson).toArray) Stmt.decode
      pure (Stmt.conditional c y n)) := by
    rw [Stmt.decode_unfold]
    cases yes <;> cases no <;> simp only [Stmt.toJson, obj] <;> rfl
  rw [body, expr_roundtrip _ _ hc]
  change (do
    let y ← Decode.array _ (.arr (yes.map Stmt.toJson).toArray) Stmt.decode
    let n ← Decode.array _ (.arr (no.map Stmt.toJson).toArray) Stmt.decode
    pure (Stmt.conditional condition y n)) = _
  rw [array_encoded_roundtrip _ _ _ _ hy]
  change (Stmt.conditional condition yes <$>
    Decode.array _ (.arr (no.map Stmt.toJson).toArray) Stmt.decode) = _
  rw [array_encoded_roundtrip _ _ _ _ hn]
  rfl

private theorem optional_lvalue_roundtrip (path : String) (value : Option LValue)
    (h : ∀ v ∈ value, LValueRepresentable v) :
    (value.map (fun v => some <$> LValue.decode path v.toJson)).getD (.ok none) =
      (Except.ok value : Decode.Dec (Option LValue)) := by
  cases value with
  | none => rfl
  | some v =>
    change (some <$> LValue.decode path v.toJson) = _
    rw [lvalue_roundtrip _ _ (h v (by simp))]
    rfl

theorem stmt_apply (path table : String) (hit : Option LValue)
    (h : ∀ v ∈ hit, LValueRepresentable v) :
    Stmt.decode path (Stmt.apply table hit).toJson = .ok (.apply table hit) := by
  have body : Stmt.decode path (Stmt.apply table hit).toJson =
      (Stmt.apply table <$> (hit.map (fun v =>
        some <$> LValue.decode (Decode.sub (Decode.sub path "apply") "hit") v.toJson)).getD (.ok none)) := by
    rw [Stmt.decode_unfold]
    by_cases empty : table.isEmpty = true
    · have zero : table = "" := String.isEmpty_iff.mp empty
      subst table
      cases hit with
      | none => simp only [Stmt.toJson]; rfl
      | some v => obtain ⟨fields, obj⟩ := lvalue_object v; simp only [Stmt.toJson, Option.map, obj]; rfl
    · cases hit with
      | none => simp only [Stmt.toJson, Encode.ofStr, empty]; rfl
      | some v =>
        obtain ⟨fields, obj⟩ := lvalue_object v
        simp only [Stmt.toJson, Encode.ofStr, empty, Option.map, obj]
        rfl
  rw [body, optional_lvalue_roundtrip _ _ h]
  rfl

theorem stmt_callAction (path action : String) (args : List Arg)
    (h : ∀ a ∈ args, ArgRepresentable a) :
    Stmt.decode path (Stmt.callAction action args).toJson = .ok (.callAction action args) := by
  have body : Stmt.decode path (Stmt.callAction action args).toJson =
      (Stmt.callAction action <$> Decode.array (Decode.sub (Decode.sub path "call_action") "args")
        (.arr (args.map Arg.toJson).toArray) Arg.decode) := by
    rw [Stmt.decode_unfold]
    by_cases empty : action.isEmpty = true
    · have zero : action = "" := String.isEmpty_iff.mp empty
      subst action
      cases args <;> simp only [Stmt.toJson] <;> rfl
    · cases args <;> simp only [Stmt.toJson, Encode.ofStr, empty] <;> rfl
  rw [body, array_encoded_roundtrip _ _ _ _ (fun a ha p => arg_roundtrip p a (h a ha))]
  rfl

theorem stmt_callBlock (path block : String) (args : List Arg)
    (h : ∀ a ∈ args, ArgRepresentable a) :
    Stmt.decode path (Stmt.callBlock block args).toJson = .ok (.callBlock block args) := by
  have body : Stmt.decode path (Stmt.callBlock block args).toJson =
      (Stmt.callBlock block <$> Decode.array (Decode.sub (Decode.sub path "call_block") "args")
        (.arr (args.map Arg.toJson).toArray) Arg.decode) := by
    rw [Stmt.decode_unfold]
    by_cases empty : block.isEmpty = true
    · have zero : block = "" := String.isEmpty_iff.mp empty
      subst block
      cases args <;> simp only [Stmt.toJson] <;> rfl
    · cases args <;> simp only [Stmt.toJson, Encode.ofStr, empty] <;> rfl
  rw [body, array_encoded_roundtrip _ _ _ _ (fun a ha p => arg_roundtrip p a (h a ha))]
  rfl

theorem stmt_callExtern (path inst method : String) (args : List Arg) (result : Option LValue)
    (ha : ∀ a ∈ args, ArgRepresentable a) (hr : ∀ v ∈ result, LValueRepresentable v) :
    Stmt.decode path (Stmt.callExtern inst method args result).toJson =
      .ok (.callExtern inst method args result) := by
  have body : Stmt.decode path (Stmt.callExtern inst method args result).toJson = (do
      let a ← Decode.array (Decode.sub (Decode.sub path "call_extern") "args")
        (.arr (args.map Arg.toJson).toArray) Arg.decode
      let r ← (result.map (fun v => some <$>
        LValue.decode (Decode.sub (Decode.sub path "call_extern") "result") v.toJson)).getD (.ok none)
      pure (Stmt.callExtern inst method a r)) := by
    rw [Stmt.decode_unfold]
    by_cases ei : inst.isEmpty = true
    all_goals by_cases em : method.isEmpty = true
    all_goals try (have zero : inst = "" := String.isEmpty_iff.mp ei; subst inst)
    all_goals try (have zero : method = "" := String.isEmpty_iff.mp em; subst method)
    all_goals cases args <;> cases result with
      | none => simp only [Stmt.toJson, Encode.ofStr, ei, em]; rfl
      | some v =>
        obtain ⟨fields, obj⟩ := lvalue_object v
        simp only [Stmt.toJson, Encode.ofStr, ei, em, Option.map, obj]
        rfl
  rw [body, array_encoded_roundtrip _ _ _ _ (fun a h p => arg_roundtrip p a (ha a h))]
  change (Stmt.callExtern inst method args <$>
    (result.map (fun v => some <$> LValue.decode _ v.toJson)).getD (.ok none)) = _
  rw [optional_lvalue_roundtrip _ _ hr]
  rfl

/-- Every finite representable statement round-trips through the actual decoder. -/
theorem stmt_roundtrip (path : String) (value : Stmt) (h : StmtRepresentable value) :
    Stmt.decode path value.toJson = .ok value := by
  induction value using Stmt.rec
      (motive_2 := fun xs => ∀ s ∈ xs, ∀ p, StmtRepresentable s →
        Stmt.decode p s.toJson = .ok s) generalizing path
  all_goals try simp only [StmtRepresentable] at h
  case assign target value => exact stmt_assign path target value h.1 h.2
  case conditional condition yes no ihy ihn =>
    exact stmt_conditional path condition yes no h.1
      (fun s hs p => ihy s hs p (h.2.1 s hs))
      (fun s hs p => ihn s hs p (h.2.2 s hs))
  case apply table hit => exact stmt_apply path table hit h
  case callAction action args => exact stmt_callAction path action args h
  case callBlock block args => exact stmt_callBlock path block args h
  case callExtern inst method args result => exact stmt_callExtern path inst method args result h.1 h.2
  case setValid header => exact stmt_setValid path header h
  case setInvalid header => exact stmt_setInvalid path header h
  case push stack count => exact stmt_push path stack count h.1 h.2
  case pop stack count => exact stmt_pop path stack count h.1 h.2
  case extract target => exact stmt_extract path target h
  case advance value => exact stmt_advance path value h
  case verify value error => exact stmt_verify path error value h
  case emit value => exact stmt_emit path value h
  case nil s hs p h => cases hs
  case cons head tail ih iht s hs p h =>
    rcases List.mem_cons.mp hs with rfl | hs
    · exact ih p h
    · exact iht s hs p h

end P4bloIR.CodecLaws
