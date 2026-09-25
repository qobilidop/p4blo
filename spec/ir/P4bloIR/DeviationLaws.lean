import P4bloIR.Exec
import P4bloIR.ScalarTyping
import P4bloIR.ScalarLaws
import P4bloIR.FieldLaws
import P4bloIR.Theorems

/-!
# Laws for the behaviors where p4blo closes or departs from P4

Each theorem here states what the actual evaluator, executor, table lookup
or emitter does on a case that docs/ir-semantics.md records as *deviates*
or *refines undefined*, or on a case the P4-SpecTec simulator cannot judge.
They are laws of the production definitions, in the style of `ScalarLaws`:
no second model, explicit premises, and results stated together with the
run they leave.

Evaluation laws are stated per run: a premise such as
`(evaluate e).run run = (.ok v, run')` is met by any expression that reads a
variable holding `v`, whereas a run-independent `evaluate e = pure v` would
be vacuous for header and stack values, which no literal denotes.

None of this is program validity. The premises name exactly the shapes and
declarations each result needs; a validated program is expected to supply
them, but nothing here proves that it does. Nothing here is about Python or
about P4-SpecTec: each theorem fixes the Lean side of a ledger entry, and the
entry's `Class:` line says how that compares with the other two.
-/

namespace P4bloIR.DeviationLaws

open ScalarTyping (run_pure run_bind run_map)

private theorem expectStack_stack (t : String) (e : List Value) (n : Nat) :
    expectStack (.stack t e n) = pure (t, e, n) := rfl
private theorem expectBits_bits (b : Bits) : expectBits (.bits b) = pure b := rfl
private theorem run_get (run : Run) : (get : M Run).run run = (.ok run, run) := rfl
private theorem run_throwInterp (msg : String) (run : Run) :
    (throwInterp msg : M α).run run = (.error (.interp msg), run) := rfl
private theorem run_modify (f : Run → Run) (run : Run) :
    (modify f : M Unit).run run = (.ok (), f run) := rfl

-- ---------------------------------------------------------------------------
-- Header equality (deviates)
-- ---------------------------------------------------------------------------

/-- Two invalid headers are equal whatever their stored fields.

No premise: the type names and the field lists are arbitrary, including
lists of different lengths. It does not establish that a validated program
only compares headers of one type. -/
theorem header_equal_invalid (s t : String) (fa fb : List Value) :
    Value.equal (.header s false fa) (.header t false fb) = true := by
  simp [Value.equal]

/-- A valid header is never equal to an invalid one, whatever the fields.

No premise. It does not establish anything about the types of the two
headers. -/
theorem header_equal_valid_invalid (s t : String) (fa fb : List Value) :
    Value.equal (.header s true fa) (.header t false fb) = false := by
  simp [Value.equal]

/-- An invalid header is never equal to a valid one, whatever the fields.

No premise; the mirror of `header_equal_valid_invalid`. -/
theorem header_equal_invalid_valid (s t : String) (fa fb : List Value) :
    Value.equal (.header s false fa) (.header t true fb) = false := by
  simp [Value.equal]

/-- Two valid headers are equal exactly when their fields are, fieldwise.

No premise. Field lists of different lengths are unequal by
`Value.equalList`. The type names are not compared; a validated program
compares headers of one type only, which this does not establish. -/
theorem header_equal_valid (s t : String) (fa fb : List Value) :
    Value.equal (.header s true fa) (.header t true fb) = Value.equalList fa fb := by
  simp [Value.equal]

/-- `==` evaluates its left operand, then its right, and compares them with
`Value.equal`, leaving the run the operands left.

Premises: the two operand evaluations in sequence, from any run. It does not
establish that either operand evaluation succeeds. -/
theorem evaluate_eq (left right : Expr) (run run₁ run₂ : Run) (a b : Value)
    (hl : (evaluate left).run run = (.ok a, run₁))
    (hr : (evaluate right).run run₁ = (.ok b, run₂)) :
    (evaluate (.binary .eq left right)).run run = (.ok (.bool (Value.equal a b)), run₂) := by
  simp [evaluate, run_bind, run_map, hl, hr]

/-- Comparing two invalid headers with `==` gives `true` through the actual
evaluator, whatever their fields.

Premises: the operands evaluate, in sequence, to invalid headers. It does
not establish that they have one type. -/
theorem evaluate_eq_invalid_headers (left right : Expr) (run run₁ run₂ : Run)
    (s t : String) (fa fb : List Value)
    (hl : (evaluate left).run run = (.ok (.header s false fa), run₁))
    (hr : (evaluate right).run run₁ = (.ok (.header t false fb), run₂)) :
    (evaluate (.binary .eq left right)).run run = (.ok (.bool true), run₂) := by
  rw [evaluate_eq left right run run₁ run₂ _ _ hl hr, header_equal_invalid]

/-- Comparing a valid and an invalid header with `==` gives `false` through
the actual evaluator, whatever their fields.

Premises: the operands evaluate, in sequence, to a valid and an invalid
header. -/
theorem evaluate_eq_valid_invalid (left right : Expr) (run run₁ run₂ : Run)
    (s t : String) (fa fb : List Value)
    (hl : (evaluate left).run run = (.ok (.header s true fa), run₁))
    (hr : (evaluate right).run run₁ = (.ok (.header t false fb), run₂)) :
    (evaluate (.binary .eq left right)).run run = (.ok (.bool false), run₂) := by
  rw [evaluate_eq left right run run₁ run₂ _ _ hl hr, header_equal_valid_invalid]

/-- `!=` evaluates its left operand, then its right, and gives the negation
of `Value.equal` on them, leaving the run the operands left.

Premises: the two operand evaluations in sequence, from any run. It does not
establish that either operand evaluation succeeds. -/
theorem evaluate_ne (left right : Expr) (run run₁ run₂ : Run) (a b : Value)
    (hl : (evaluate left).run run = (.ok a, run₁))
    (hr : (evaluate right).run run₁ = (.ok b, run₂)) :
    (evaluate (.binary .ne left right)).run run = (.ok (.bool (!Value.equal a b)), run₂) := by
  simp [evaluate, run_bind, run_map, hl, hr]

/-- `!=` is the negation of `==` on the same operands, whatever kind of value
they are: whenever `==` gives a boolean, `!=` gives its negation and leaves
the same run.

Premise: `==` evaluates, from this run, to `b`. No premise on the kind of
the operands, so it covers bits, booleans, enums, errors, headers, structs
and stacks alike. -/
theorem evaluate_ne_eq (left right : Expr) (run run' : Run) (b : Bool)
    (h : (evaluate (.binary .eq left right)).run run = (.ok (.bool b), run')) :
    (evaluate (.binary .ne left right)).run run = (.ok (.bool (!b)), run') := by
  simp only [evaluate, run_bind, run_pure] at h ⊢
  revert h
  rcases (evaluate left).run run with ⟨_ | a, run₁⟩
  · simp
  · simp only
    rcases (evaluate right).run run₁ with ⟨_ | c, run₂⟩
    · simp
    · simp only [Prod.mk.injEq, Except.ok.injEq, Value.bool.injEq]
      rintro ⟨rfl, rfl⟩
      exact ⟨rfl, rfl⟩

/-- `!=` fails exactly as `==` does on the same operands: with the same
fault and the same run.

Premise: `==` fails from this run with `fault`. -/
theorem evaluate_ne_eq_error (left right : Expr) (run run' : Run) (fault : Fault)
    (h : (evaluate (.binary .eq left right)).run run = (.error fault, run')) :
    (evaluate (.binary .ne left right)).run run = (.error fault, run') := by
  simp only [evaluate, run_bind, run_pure] at h ⊢
  revert h
  rcases (evaluate left).run run with ⟨_ | a, run₁⟩
  · simp
  · simp only
    rcases (evaluate right).run run₁ with ⟨_ | c, run₂⟩
    · simp
    · simp

-- ---------------------------------------------------------------------------
-- Equality of scalars and of field lists (pins `Value.equal`, `equalList`)
-- ---------------------------------------------------------------------------

/-- Two `bit<N>` values are equal exactly when they are the same value: the
same width and the same number.

No premise. It does not relate values of different kinds. -/
theorem equal_bits_iff (a b : Bits) : Value.equal (.bits a) (.bits b) = true ↔ a = b := by
  obtain ⟨wa, va, ha⟩ := a
  obtain ⟨wb, vb, hb⟩ := b
  simp only [Value.equal_bits, Bool.and_eq_true, beq_iff_eq, Bits.mk.injEq]

/-- Two booleans are equal exactly when they are the same boolean.

No premise. -/
theorem equal_bool_iff (a b : Bool) : Value.equal (.bool a) (.bool b) = true ↔ a = b := by
  simp

/-- Two values of the same scalar kind, both bits or both booleans, as two
fields in one position of a header type are. -/
def SameScalarKind : Value → Value → Prop
  | .bits _, .bits _ | .bool _, .bool _ => True
  | _, _ => False

/-- Two field lists of one length whose values have the same scalar kind in
every position, as the fields of two headers of one type do. -/
inductive SameScalarKinds : List Value → List Value → Prop
  | nil : SameScalarKinds [] []
  | cons {x y : Value} {xs ys : List Value} :
      SameScalarKind x y → SameScalarKinds xs ys → SameScalarKinds (x :: xs) (y :: ys)

/-- Field lists are compared position by position: equal heads and equal
tails.

No premise. It is the step `header_equal_valid` and the struct and stack
cases rest on; it does not say what `Value.equal` does on each field. -/
theorem equalList_cons (x y : Value) (xs ys : List Value) :
    Value.equalList (x :: xs) (y :: ys) = (Value.equal x y && Value.equalList xs ys) := by
  simp [Value.equalList]

/-- Two lists of bits and boolean fields, the same kind in each position,
are equal exactly when they are the same list: every field value counts.

Premise: the lists pair up position by position with the same scalar kind,
as the fields of two headers of one type do. It does not cover nested
compound values, nor lists of different kinds or lengths. -/
theorem equalList_scalar_iff (fa fb : List Value) (h : SameScalarKinds fa fb) :
    Value.equalList fa fb = true ↔ fa = fb := by
  induction h with
  | nil => simp [Value.equalList]
  | @cons x y xs ys hxy _ ih =>
    rw [equalList_cons, Bool.and_eq_true, ih, List.cons.injEq]
    have : Value.equal x y = true ↔ x = y := by
      cases x <;> cases y <;>
        first
        | rw [equal_bits_iff, Value.bits.injEq]
        | rw [equal_bool_iff, Value.bool.injEq]
        | exact (hxy : False).elim
    rw [this]

/-- Two valid headers whose fields are bits and booleans of the same kinds
are equal exactly when their field values are all the same.

Premise: the field lists pair up with the same scalar kind, as two headers of
one type do. The type names are not compared; that a validated program
compares headers of one type only is not established here. -/
theorem header_equal_valid_iff (s t : String) (fa fb : List Value)
    (h : SameScalarKinds fa fb) :
    Value.equal (.header s true fa) (.header t true fb) = true ↔ fa = fb := by
  rw [header_equal_valid, equalList_scalar_iff fa fb h]

-- ---------------------------------------------------------------------------
-- Zero values (Uninitialized variables; used by the stack laws)
-- ---------------------------------------------------------------------------

/-- The zero of a header field type: `0` at its width for bits, `false`
for a boolean. Other types never occur as header fields. -/
def fieldZero : Ty → Value
  | .bits n => .bits (Bits.wrap n 0)
  | _ => .bool false

/-- A type a header field may have: bits or a boolean. -/
def HeaderFieldTy : Ty → Prop
  | .bits _ | .boolean => True
  | _ => False

private theorem zeroWith_field (index : Index) (fuel : Nat) (ty : Ty) (h : HeaderFieldTy ty) :
    Value.zeroWith index (fuel + 1) ty = .ok (fieldZero ty) := by
  cases ty <;> simp_all [HeaderFieldTy, Value.zeroWith, fieldZero] <;> rfl

private theorem mapM_zeroWith_fields (index : Index) (fuel : Nat) (fields : List Field)
    (h : ∀ f ∈ fields, HeaderFieldTy f.type) :
    fields.mapM (fun f => Value.zeroWith index (fuel + 1) f.type) =
      .ok (fields.map (fieldZero ·.type)) := by
  induction fields with
  | nil => rfl
  | cons f rest ih =>
    simp only [List.mapM_cons, List.map_cons,
      zeroWith_field index fuel f.type (h f (by simp)),
      ih (fun g hg => h g (by simp [hg]))]
    rfl

/-- The zero header of a declared header type is invalid, and each of its
fields is zero bits or `false`.

Premises: the type is declared under `t`, and every field is bits or a
boolean. The result carries the declaration's own name. It does not
establish that the declaration is well formed otherwise. -/
theorem zeroHeader_eq (index : Index) (t : String) (decl : HeaderType)
    (hd : index.headerTypes[t]? = some decl) (hf : ∀ f ∈ decl.fields, HeaderFieldTy f.type) :
    Value.zeroHeader t index =
      .ok (.header decl.name false (decl.fields.map (fieldZero ·.type))) := by
  unfold Value.zeroHeader Value.zero
  show Value.zeroWith index ((index.headerTypes.size + index.structTypes.size + 1) + 1) _ = _
  rw [Value.zeroWith]
  simp only [hd]
  rw [mapM_zeroWith_fields index _ decl.fields hf]
  rfl

/-- An uninitialized `bit<N>` is `0` at width `N`.

No premise. With `Frame.forBlock_initialized`, a fresh activation reads it
there. It does not cover compound types beyond headers. -/
theorem zero_bits (index : Index) (n : Nat) :
    Value.zero (.bits n) index = .ok (.bits (Bits.wrap n 0)) := rfl

/-- An uninitialized boolean is `false`.

No premise. -/
theorem zero_boolean (index : Index) : Value.zero .boolean index = .ok (.bool false) := rfl

/-- An uninitialized error is `NoError`.

No premise. -/
theorem zero_error (index : Index) : Value.zero .error index = .ok Value.noError := rfl

-- ---------------------------------------------------------------------------
-- Index out of range (deviates)
-- ---------------------------------------------------------------------------

/-- Reading element `i` of a stack with `i` at or past its size gives the
zero invalid header of the element type, and changes nothing.

Premises: the element type is declared with bits and boolean fields. It does
not establish that the stack's elements have that type. -/
theorem elementOf_out_of_range (run : Run) (t : String) (elements : List Value) (i : Nat)
    (decl : HeaderType) (hlen : elements.length ≤ i)
    (hd : run.index.headerTypes[t]? = some decl) (hf : ∀ f ∈ decl.fields, HeaderFieldTy f.type) :
    (elementOf t elements i).run run =
      (.ok (.header decl.name false (decl.fields.map (fieldZero ·.type))), run) := by
  have hn : elements[i]? = none := List.getElem?_eq_none hlen
  simp [elementOf, hn, run_bind, zeroHeader_eq run.index t decl hd hf, liftExcept]

/-- The expression `hs[i]` with `i` at or past the stack's size evaluates to
the zero invalid header of the element type.

Premises: `hs` evaluates to a stack and then `i` to bits at least its size;
the element type is declared with bits and boolean fields. The run is the one
the two operand evaluations leave. It does not establish that `i` is
`bit<32>` or that the program is valid. -/
theorem evaluate_index_out_of_range (base idx : Expr) (run run₁ run₂ : Run) (t : String)
    (elements : List Value) (next : Nat) (i : Bits) (decl : HeaderType)
    (hb : (evaluate base).run run = (.ok (.stack t elements next), run₁))
    (hi : (evaluate idx).run run₁ = (.ok (.bits i), run₂))
    (hlen : elements.length ≤ i.value)
    (hd : run₂.index.headerTypes[t]? = some decl) (hf : ∀ f ∈ decl.fields, HeaderFieldTy f.type) :
    (evaluate (.index base idx)).run run =
      (.ok (.header decl.name false (decl.fields.map (fieldZero ·.type))), run₂) := by
  simp only [evaluate, run_bind, hb, hi, expectStack_stack, expectBits_bits, run_pure]
  exact elementOf_out_of_range run₂ t elements i.value decl hlen hd hf

/-- The lvalue `hs[i]` with `i` at or past the stack's size reads as the
zero invalid header of the element type.

Premises as in `evaluate_index_out_of_range`, with `hs` read as an lvalue. -/
theorem readLValue_index_out_of_range (base : LValue) (idx : Expr) (run run₁ run₂ : Run)
    (t : String) (elements : List Value) (next : Nat) (i : Bits) (decl : HeaderType)
    (hb : (readLValue base).run run = (.ok (.stack t elements next), run₁))
    (hi : (evaluate idx).run run₁ = (.ok (.bits i), run₂))
    (hlen : elements.length ≤ i.value)
    (hd : run₂.index.headerTypes[t]? = some decl) (hf : ∀ f ∈ decl.fields, HeaderFieldTy f.type) :
    (readLValue (.index base idx)).run run =
      (.ok (.header decl.name false (decl.fields.map (fieldZero ·.type))), run₂) := by
  simp only [readLValue, run_bind, hb, hi, expectStack_stack, expectBits_bits, run_pure]
  exact elementOf_out_of_range run₂ t elements i.value decl hlen hd hf

/-- Writing any value to `hs[i]` with `i` at or past the stack's size does
nothing: the run is the one reading `hs` and evaluating `i` left.

Premises: `hs` reads as a stack and then `i` evaluates to bits at least its
size. No premise on the written value, which need not even be a header. With
reads that preserve the run, as every read of a variable does, the write
leaves the run exactly as it was. -/
theorem writeLValue_index_out_of_range (base : LValue) (idx : Expr) (value : Value)
    (run run₁ run₂ : Run) (t : String) (elements : List Value) (next : Nat) (i : Bits)
    (hb : (readLValue base).run run = (.ok (.stack t elements next), run₁))
    (hi : (evaluate idx).run run₁ = (.ok (.bits i), run₂))
    (hlen : elements.length ≤ i.value) :
    (writeLValue (.index base idx) value).run run = (.ok (), run₂) := by
  simp only [writeLValue, run_bind, hb, hi, expectStack_stack, expectBits_bits, run_pure,
    Nat.not_lt.mpr hlen]
  rfl

/-- Writing a field of `hs[i]` with `i` at or past the stack's size does
nothing either: the run is unchanged.

Premises: reading `hs` and evaluating `i` preserve the run (the path is read
twice, once to fetch the container and once to store it back); the element
type is declared with bits and boolean fields and has the field. It does not
cover a read that changes the run. -/
theorem writeLValue_member_out_of_range (base : LValue) (idx : Expr) (field : String)
    (value : Value) (run : Run) (t : String) (elements : List Value) (next : Nat) (i : Bits)
    (decl : HeaderType) (j : Nat)
    (hb : (readLValue base).run run = (.ok (.stack t elements next), run))
    (hi : (evaluate idx).run run = (.ok (.bits i), run))
    (hlen : elements.length ≤ i.value)
    (hd : run.index.headerTypes[t]? = some decl) (hf : ∀ f ∈ decl.fields, HeaderFieldTy f.type)
    (hj : run.index.fieldIndex? decl.name field = some j) :
    (writeLValue (.member (.index base idx) field) value).run run = (.ok (), run) := by
  have hr := readLValue_index_out_of_range base idx run run run t elements next i decl hb hi
    hlen hd hf
  have hs := FieldLaws.setField_pack (kind := .header) (valid := false)
    (values := decl.fields.map (fieldZero ·.type)) (value := value) run hj
  have hw := writeLValue_index_out_of_range base idx
    (.header decl.name false ((decl.fields.map (fieldZero ·.type)).set j value))
    run run run t elements next i hb hi hlen
  simp only [FieldLaws.pack] at hs
  rw [writeLValue]
  simp only [run_bind, hr, hs, hw]

-- ---------------------------------------------------------------------------
-- hs.lastIndex and hs.last (deviates)
-- ---------------------------------------------------------------------------

/-- `hs.lastIndex` is `nextIndex - 1` computed in `bit<32>`, as
`nextIndex + 2^32 - 1` wrapped.

Premise: `hs` evaluates to a stack. It does not restrict where
`lastIndex` may appear; the validator's parser-only rule is not stated. -/
theorem evaluate_lastIndex (stack : Expr) (run run₁ : Run) (t : String)
    (elements : List Value) (next : Nat)
    (hs : (evaluate stack).run run = (.ok (.stack t elements next), run₁)) :
    (evaluate (.lastIndex stack)).run run =
      (.ok (.bits (Bits.wrap 32 (next + 2 ^ 32 - 1))), run₁) := by
  simp only [evaluate, run_bind, hs, expectStack_stack, run_pure]

/-- With `nextIndex = 0`, `hs.lastIndex` is `2^32 - 1`.

No premise; combine with `evaluate_lastIndex`. -/
theorem lastIndex_empty : (Bits.wrap 32 (0 + 2 ^ 32 - 1)).value = 2 ^ 32 - 1 := by
  simp [Bits.wrap]

/-- With `nextIndex ≥ 1`, `hs.lastIndex` is `nextIndex - 1` at 32 bits.

Premise: `0 < next`. The value is `(next - 1) mod 2^32`, which is
`next - 1` whenever `next ≤ 2^32`. -/
theorem lastIndex_nonempty (next : Nat) (h : 0 < next) :
    Bits.wrap 32 (next + 2 ^ 32 - 1) = Bits.wrap 32 (next - 1) := by
  have : next + 2 ^ 32 - 1 = (next - 1) + 2 ^ 32 := by omega
  simp only [Bits.wrap, this, Nat.add_mod_right]

/-- `hs.last` on an empty stack, elaborated as `hs[hs.lastIndex]`, reads the
zero invalid header and raises no error.

Premises: `hs` evaluates to a stack with `nextIndex = 0`, preserving the run
(it is evaluated twice); the stack has fewer than `2^32` elements; the
element type is declared with bits and boolean fields. It does not establish
that the eDSL or a frontend produces this elaboration. -/
theorem evaluate_last_empty (stack : Expr) (run : Run) (t : String) (elements : List Value)
    (decl : HeaderType)
    (hs : (evaluate stack).run run = (.ok (.stack t elements 0), run))
    (hsize : elements.length < 2 ^ 32)
    (hd : run.index.headerTypes[t]? = some decl) (hf : ∀ f ∈ decl.fields, HeaderFieldTy f.type) :
    (evaluate (.index stack (.lastIndex stack))).run run =
      (.ok (.header decl.name false (decl.fields.map (fieldZero ·.type))), run) :=
  evaluate_index_out_of_range stack (.lastIndex stack) run run run t elements 0 _ decl hs
    (evaluate_lastIndex stack run run t elements 0 hs)
    (by rw [lastIndex_empty]; omega) hd hf

/-- `hs.last` with `1 ≤ nextIndex ≤ size` reads element `nextIndex - 1`,
the case where the elaboration agrees with P4.

Premises: `hs` evaluates to such a stack, preserving the run; the stack has
fewer than `2^32` elements. -/
theorem evaluate_last_nonempty (stack : Expr) (run : Run) (t : String) (elements : List Value)
    (next : Nat) (hs : (evaluate stack).run run = (.ok (.stack t elements next), run))
    (hpos : 0 < next) (hle : next ≤ elements.length) (hsize : elements.length < 2 ^ 32) :
    (evaluate (.index stack (.lastIndex stack))).run run =
      (.ok (elements[next - 1]'(by omega)), run) := by
  have hl := evaluate_lastIndex stack run run t elements next hs
  rw [lastIndex_nonempty next hpos] at hl
  have hv : (Bits.wrap 32 (next - 1)).value = next - 1 := by
    simp only [Bits.wrap]; exact Nat.mod_eq_of_lt (by omega)
  rw [evaluate]
  simp only [run_bind, hs, hl, expectStack_stack, expectBits_bits, run_pure, elementOf,
    hv, List.getElem?_eq_getElem (show next - 1 < elements.length by omega)]

-- ---------------------------------------------------------------------------
-- push_front and pop_front (deviates)
-- ---------------------------------------------------------------------------

/-- `push_front(n)` is `n` fresh headers followed by the stack's elements
cut to its size, with `nextIndex` growing to at most the size; `n` above the
size acts as the size.

Premise: the zero header of the element type exists and is `z` (see
`zeroHeader_eq` for what it is). -/
theorem pushFront_eq (t : String) (elements : List Value) (next n : Nat) (index : Index)
    (z : Value) (hz : Value.zeroHeader t index = .ok z) :
    pushFront (.stack t elements next) n index =
      .ok (.stack t (List.replicate (min n elements.length) z ++
        elements.take (elements.length - min n elements.length))
        (min (next + n) elements.length)) := by
  simp only [pushFront, Value.expectStack, pure_bind, hz, Except.ok_bind]
  have : min (next + min n elements.length) elements.length =
      min (next + n) elements.length := by omega
  rw [this]
  rfl

/-- After `push_front(n)`, the size is unchanged, the first `n` elements are
the zero invalid header, element `i ≥ n` is the old element `i - n`, and
`nextIndex` is `min(nextIndex + n, size)`.

Premise: the zero header of the element type is `z`. The old fields of the
first `n` elements are not kept, which is where SpecTec differs. It does not
establish the effect through the statement executor. -/
theorem pushFront_spec (t : String) (elements : List Value) (next n : Nat) (index : Index)
    (z : Value) (hz : Value.zeroHeader t index = .ok z) :
    ∃ result, pushFront (.stack t elements next) n index =
        .ok (.stack t result (min (next + n) elements.length)) ∧
      result.length = elements.length ∧
      (∀ i, i < n → i < elements.length → result[i]? = some z) ∧
      (∀ i, n ≤ i → i < elements.length → result[i]? = elements[i - n]?) := by
  refine ⟨_, pushFront_eq t elements next n index z hz, ?_, ?_, ?_⟩
  · simp; omega
  · intro i hi hs
    rw [List.getElem?_append_left (by simp only [List.length_replicate]; omega),
      List.getElem?_replicate_of_lt (by omega)]
  · intro i hi hs
    have hm : min n elements.length = n := by omega
    rw [hm, List.getElem?_append_right (by simp only [List.length_replicate]; omega),
      List.length_replicate, List.getElem?_take_of_lt (by omega)]

/-- `push_front(n)` with `n` at least the size makes every element the zero
invalid header and sets `nextIndex` to the size.

Premises: the zero header is `z`; `size ≤ n`. -/
theorem pushFront_clamp (t : String) (elements : List Value) (next n : Nat) (index : Index)
    (z : Value) (hz : Value.zeroHeader t index = .ok z) (h : elements.length ≤ n) :
    pushFront (.stack t elements next) n index =
      .ok (.stack t (List.replicate elements.length z) elements.length) := by
  rw [pushFront_eq t elements next n index z hz]
  have h1 : min n elements.length = elements.length := by omega
  have h2 : min (next + n) elements.length = elements.length := by omega
  simp [h1, h2]

/-- `pop_front(n)` is the stack's elements after the first `n`, followed by
`n` fresh headers, with `nextIndex` shrinking by `n`; `n` above the size
acts as the size.

Premise: the zero header of the element type is `z`. -/
theorem popFront_eq (t : String) (elements : List Value) (next n : Nat) (index : Index)
    (z : Value) (hz : Value.zeroHeader t index = .ok z) :
    popFront (.stack t elements next) n index =
      .ok (.stack t (elements.drop (min n elements.length) ++
        List.replicate (min n elements.length) z) (next - min n elements.length)) := by
  simp only [popFront, Value.expectStack, pure_bind, hz, Except.ok_bind]
  rfl

/-- After `pop_front(n)`, the size is unchanged, element `i` is the old
element `i + n` while that exists, the last `n` elements are the zero invalid
header, and `nextIndex` is `max(nextIndex - n, 0)`.

Premises: the zero header is `z`; `nextIndex ≤ size`, the stack invariant,
without which `n > size` would leave `nextIndex - size` rather than `0`. The
vacated elements do not keep old fields, and `nextIndex` is not `size - n`,
which is where SpecTec differs. -/
theorem popFront_spec (t : String) (elements : List Value) (next n : Nat) (index : Index)
    (z : Value) (hz : Value.zeroHeader t index = .ok z) (hnext : next ≤ elements.length) :
    ∃ result, popFront (.stack t elements next) n index = .ok (.stack t result (next - n)) ∧
      result.length = elements.length ∧
      (∀ i, i + n < elements.length → result[i]? = elements[i + n]?) ∧
      (∀ i, elements.length ≤ i + n → i < elements.length → result[i]? = some z) := by
  have hk : next - min n elements.length = next - n := by omega
  refine ⟨_, hk ▸ popFront_eq t elements next n index z hz, ?_, ?_, ?_⟩
  · simp; omega
  · intro i hi
    have hm : min n elements.length = n := by omega
    rw [hm, List.getElem?_append_left (by simp; omega)]
    simp [List.getElem?_drop, Nat.add_comm]
  · intro i hi hs
    rw [List.getElem?_append_right (by simp only [List.length_drop]; omega), List.length_drop,
      List.getElem?_replicate_of_lt (by omega)]

/-- `pop_front(n)` with `n` at least the size makes every element the zero
invalid header and sets `nextIndex` to `0`.

Premises: the zero header is `z`; `size ≤ n`; `nextIndex ≤ size`. -/
theorem popFront_clamp (t : String) (elements : List Value) (next n : Nat) (index : Index)
    (z : Value) (hz : Value.zeroHeader t index = .ok z) (h : elements.length ≤ n)
    (hnext : next ≤ elements.length) :
    popFront (.stack t elements next) n index =
      .ok (.stack t (List.replicate elements.length z) 0) := by
  rw [popFront_eq t elements next n index z hz]
  have h1 : min n elements.length = elements.length := by omega
  have h2 : next - elements.length = 0 := by omega
  simp [h1, h2]

-- ---------------------------------------------------------------------------
-- Shifts by the width or more (same; beyond the simulator's reach above 2048)
-- ---------------------------------------------------------------------------

/-- `x << k` with `k` at least the width of `x` evaluates to zero at that
width, whatever the width of `k` and however large `k` is.

Premises: the operands evaluate in sequence to bits. It lifts
`ScalarLaws.shl_large` through the evaluator's dispatch. -/
theorem evaluate_shl_large (left right : Expr) (run run₁ run₂ : Run) (x amount : Bits)
    (hl : (evaluate left).run run = (.ok (.bits x), run₁))
    (hr : (evaluate right).run run₁ = (.ok (.bits amount), run₂))
    (large : x.width ≤ amount.value) :
    (evaluate (.binary .shl left right)).run run = (.ok (.bits (Bits.wrap x.width 0)), run₂) := by
  simp only [evaluate, run_bind, hl, hr, expectBits_bits, run_pure,
    ScalarLaws.shl_large x amount large]

/-- `x >> k` with `k` at least the width of `x` evaluates to zero at that
width, whatever the width of `k` and however large `k` is.

Premises: the operands evaluate in sequence to bits. -/
theorem evaluate_shr_large (left right : Expr) (run run₁ run₂ : Run) (x amount : Bits)
    (hl : (evaluate left).run run = (.ok (.bits x), run₁))
    (hr : (evaluate right).run run₁ = (.ok (.bits amount), run₂))
    (large : x.width ≤ amount.value) :
    (evaluate (.binary .shr left right)).run run = (.ok (.bits (Bits.wrap x.width 0)), run₂) := by
  simp only [evaluate, run_bind, hl, hr, expectBits_bits, run_pure,
    ScalarLaws.shr_large x amount large]

/-- The zero the large shifts return has numeric value `0`.

No premise. -/
theorem wrap_zero_value (width : Nat) : (Bits.wrap width 0).value = 0 := by
  simp [Bits.wrap]

-- ---------------------------------------------------------------------------
-- Bit alignment (refines undefined)
-- ---------------------------------------------------------------------------

/-- Appending `width` bits to the emitter puts them below the bits already
written, adds their width, and keeps every written value within its width.

Premises: the emitter's value fits its width, as it does for the empty
emitter (`0 < 2^0`), and the appended value fits its width. By induction
from the empty emitter, the premise of `toBytes_padded` holds for every
emitter reached by such writes. -/
theorem write_fits (e : Emitter) (width value : Nat) (he : e.value < 2 ^ e.width)
    (hv : value < 2 ^ width) :
    (e.write width value).value = e.value * 2 ^ width + value ∧
      (e.write width value).width = e.width + width ∧
      (e.write width value).value < 2 ^ (e.write width value).width := by
  have hv' : (e.write width value).value = e.value * 2 ^ width + value := by
    simp only [Emitter.write]; exact shiftLeft_or_eq e.value width value hv
  refine ⟨hv', rfl, ?_⟩
  rw [hv']
  show e.value * 2 ^ width + value < 2 ^ (e.width + width)
  rw [Nat.pow_add]
  have : (e.value + 1) * 2 ^ width ≤ 2 ^ e.width * 2 ^ width :=
    Nat.mul_le_mul_right _ he
  rw [Nat.add_mul, Nat.one_mul] at this
  omega

/-- The emitter's bytes are exactly the emitted bits followed by fewer than
eight zero bits: the byte count covers the bits, wastes less than a byte,
and the bytes read big-endian are the bits shifted up by the padding.

Premise: the emitter's value fits its width (see `write_fits`). It does not
establish what an architecture appends after these bytes. -/
theorem toBytes_padded (e : Emitter) (he : e.value < 2 ^ e.width) :
    e.width ≤ e.toBytes.size * 8 ∧ e.toBytes.size * 8 < e.width + 8 ∧
      bytesToNat e.toBytes = e.value * 2 ^ (e.toBytes.size * 8 - e.width) := by
  have hsize : e.toBytes.size * 8 = e.width + (8 - e.width % 8) % 8 := by
    simp only [Emitter.toBytes, size_natToBytes]
    omega
  refine ⟨by omega, by omega, ?_⟩
  rw [hsize, Nat.add_sub_cancel_left]
  simp only [Emitter.toBytes, bytesToNat_natToBytes, Nat.shiftLeft_eq]
  apply Nat.mod_eq_of_lt
  have h256 : (256 : Nat) ^ ((e.width + (8 - e.width % 8) % 8) / 8) =
      2 ^ (e.width + (8 - e.width % 8) % 8) := by
    rw [show (256 : Nat) = 2 ^ 8 from rfl, ← Nat.pow_mul]
    congr 1
    omega
  rw [h256, Nat.pow_add]
  exact Nat.mul_lt_mul_of_pos_right he (Nat.two_pow_pos _)

-- ---------------------------------------------------------------------------
-- Parser loop bound (refines undefined)
-- ---------------------------------------------------------------------------

/-- Entering a state whose last entry in this block recorded the current
cursor raises `ParserTimeout` and changes nothing.

Premises: a packet is present, and the run's revisit record for
`(block, state)` holds the packet's cursor. It does not establish that a
non-consuming loop reaches such an entry, which needs the body's effect on
the cursor and on the record. -/
theorem enterState_revisit (state : State) (run : Run) (packet : Packet)
    (hp : run.packet = some packet)
    (hv : run.visits[(run.frame.block.name, state.name)]? = some packet.cursor) :
    (enterState state).run run = (.error (.parse "ParserTimeout"), run) := by
  simp [enterState, run_bind, currentBlock, getFrame, requirePacket, run_get, hp, hv, throwParse]
  rfl

/-- Entering a state at a cursor other than the recorded one succeeds and
records the current cursor for `(block, state)`, changing nothing else.

Premises: a packet is present, and the record does not hold its cursor. -/
theorem enterState_first (state : State) (run : Run) (packet : Packet)
    (hp : run.packet = some packet)
    (hv : run.visits[(run.frame.block.name, state.name)]? ≠ some packet.cursor) :
    (enterState state).run run =
      (.ok (), { run with
        visits := run.visits.insert (run.frame.block.name, state.name) packet.cursor }) := by
  simp [enterState, run_bind, currentBlock, getFrame, requirePacket, run_get, hp, hv, run_modify]

/-- After any successful entry of a state, entering it again with nothing
changed in between raises `ParserTimeout`.

Premise: the first entry succeeded. It covers only the immediate re-entry
from the run that entry left; a body or other states in between are not
covered here. -/
theorem enterState_again (state : State) (run run' : Run)
    (h : (enterState state).run run = (.ok (), run')) :
    (enterState state).run run' = (.error (.parse "ParserTimeout"), run') := by
  cases hp : run.packet with
  | none =>
    simp [enterState, run_bind, currentBlock, getFrame, requirePacket, run_get, hp,
      run_throwInterp] at h
  | some packet =>
    by_cases hv : run.visits[(run.frame.block.name, state.name)]? = some packet.cursor
    · rw [enterState_revisit state run packet hp hv] at h
      cases h
    · rw [enterState_first state run packet hp hv] at h
      simp only [Prod.mk.injEq] at h
      obtain ⟨-, rfl⟩ := h
      exact enterState_revisit state _ packet hp (by simp)

/-- One step of the actual machine on a state revisited at the recorded
cursor starts unwinding with `ParserTimeout`, keeping the run.

Premises as in `enterState_revisit`, with no fault pending. It does not
establish the final outcome of the run, which also depends on the pending
block returns. -/
theorem step_state_revisit (scope : BlockScope) (state : State) (rest : List Execution.Work)
    (run : Run) (packet : Packet) (hp : run.packet = some packet)
    (hv : run.visits[(run.frame.block.name, state.name)]? = some packet.cursor) :
    Execution.step { work := .state scope state :: rest, run } =
      .inr { work := rest, run, fault := some (.parse "ParserTimeout") } := by
  have hd : (Execution.dispatch (.state scope state)).run run =
      (.error (.parse "ParserTimeout"), run) := by
    simp only [Execution.dispatch, run_bind, enterState_revisit state run packet hp hv]
  simp [Execution.step, hd]

-- ---------------------------------------------------------------------------
-- LPM and priority (refines undefined)
-- ---------------------------------------------------------------------------

open Installed in
/-- Every key of `entry` matches the lookup key in its position. -/
def Matches (entry : Entry) (keys : List Bits) : Prop :=
  ((entry.keys.zip keys).all fun x => keyValueMatches x.fst x.snd) = true

/-- What `Installed.beats` compares: the priority in a table with a ternary
key, the total prefix length otherwise. -/
def rank (ternary : Bool) (entry : Entry) : Nat :=
  if ternary then entry.priority else Installed.prefixLength entry

/-- The prefix length one key value contributes: its length for an `lpm`
value, nothing for an exact or ternary one. -/
def lpmLength : KeyValue → Nat
  | .lpm _ len => len
  | _ => 0

private theorem foldl_prefix (ks : List KeyValue) (n : Nat) :
    ks.foldl (fun n kv => match kv with | .lpm _ len => n + len | _ => n) n =
      n + (ks.map lpmLength).sum := by
  induction ks generalizing n with
  | nil => simp
  | cons kv rest ih =>
    rw [List.foldl_cons, ih]
    cases kv <;> simp [lpmLength] <;> omega

/-- The prefix length `Installed.prefixLength` ranks an entry by is the sum
of the lengths of its `lpm` key values as installed.

No premise. It does not establish that a table has at most one `lpm` key,
which is the validator's rule. -/
theorem prefixLength_eq (entry : Entry) :
    Installed.prefixLength entry = (entry.keys.map lpmLength).sum := by
  have := foldl_prefix entry.keys 0
  rw [Nat.zero_add] at this
  exact this

/-- An entry with one `lpm` key value and otherwise exact or ternary ones
has the prefix length of that value.

Premise: no other key value is an `lpm` one. -/
theorem prefixLength_single (pre post : List KeyValue) (value len : Nat) (action : ActionCall)
    (priority : Nat) (h : ∀ kv ∈ pre ++ post, lpmLength kv = 0) :
    Installed.prefixLength ⟨pre ++ .lpm value len :: post, action, priority⟩ = len := by
  have hz : ∀ l : List KeyValue, (∀ kv ∈ l, lpmLength kv = 0) → (l.map lpmLength).sum = 0 := by
    intro l hl
    induction l with
    | nil => rfl
    | cons kv rest ih =>
      simp only [List.map_cons, List.sum_cons, hl kv (by simp),
        ih (fun k hk => hl k (by simp [hk]))]
  rw [prefixLength_eq]
  simp only [List.map_append, List.map_cons, List.sum_append, List.sum_cons, lpmLength]
  rw [hz pre (fun kv hkv => h kv (by simp [hkv])), hz post (fun kv hkv => h kv (by simp [hkv]))]
  simp

/-- In a table without a ternary key, the rank `lookup_hit` compares is the
sum of the entry's `lpm` prefix lengths.

No premise. -/
theorem rank_lpm (entry : Entry) : rank false entry = (entry.keys.map lpmLength).sum := by
  simp [rank, prefixLength_eq]

/-- An exact key value matches exactly the key of that number.

No premise. -/
theorem keyValueMatches_exact (value : Nat) (key : Bits) :
    Installed.keyValueMatches (.exact value) key = true ↔ key.value = value := by
  simp [Installed.keyValueMatches]

/-- An `lpm` key value of length `len` matches exactly the keys that agree
with its value on their top `len` bits, bit by bit.

Premise: the value fits the key's width, as installation checks. A length
above the width compares every bit. It does not establish that the value is
canonical (zero below its prefix), which the lookup does not need. -/
theorem keyValueMatches_lpm (value len : Nat) (key : Bits) (hv : value < 2 ^ key.width) :
    Installed.keyValueMatches (.lpm value len) key = true ↔
      ∀ j, key.width - len ≤ j → j < key.width → key.value.testBit j = value.testBit j := by
  simp only [Installed.keyValueMatches, beq_iff_eq]
  constructor
  · intro h j hlo hhi
    have := congrArg (fun n => n.testBit (j - (key.width - len))) h
    simp only [Nat.testBit_shiftRight] at this
    rwa [Nat.add_sub_cancel' hlo] at this
  · intro h
    apply Nat.eq_of_testBit_eq
    intro i
    simp only [Nat.testBit_shiftRight]
    by_cases hi : key.width - len + i < key.width
    · exact h _ (Nat.le_add_right _ _) hi
    · have hw : 2 ^ key.width ≤ 2 ^ (key.width - len + i) :=
        Nat.pow_le_pow_right (by decide) (by omega)
      rw [Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le key.isLt hw),
        Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hv hw)]

/-- A ternary key value matches exactly the keys that agree with its value
on every bit its mask sets.

No premise. -/
theorem keyValueMatches_ternary (value mask : Nat) (key : Bits) :
    Installed.keyValueMatches (.ternary value mask) key = true ↔
      ∀ j, mask.testBit j = true → key.value.testBit j = value.testBit j := by
  simp only [Installed.keyValueMatches, beq_iff_eq]
  constructor
  · intro h j hm
    have := congrArg (fun n => n.testBit j) h
    simpa [Nat.testBit_and, hm] using this
  · intro h
    apply Nat.eq_of_testBit_eq
    intro j
    simp only [Nat.testBit_and]
    cases hm : mask.testBit j
    · simp
    · simp [h j hm]

private theorem beats_iff (e b : Entry) (ternary : Bool) :
    Installed.beats e b ternary = true ↔ rank ternary b < rank ternary e := by
  cases ternary <;> simp [Installed.beats, rank]

/-- The selection loop body of `Installed.lookup`, as a pure step. -/
private def selectStep (ternary : Bool) (keys : List Bits) (best : Option Entry)
    (entry : Entry) : Option Entry :=
  if ((entry.keys.zip keys).all fun x => Installed.keyValueMatches x.fst x.snd) = true then
    match best with
    | none => some entry
    | some b => if Installed.beats entry b ternary = true then some entry else best
  else best

private theorem forIn_yield {α β : Type} (l : List α) (init : β)
    (f : α → β → Except String (ForInStep β)) (g : β → α → β)
    (h : ∀ a b, f a b = .ok (.yield (g b a))) :
    forIn l init f = .ok (l.foldl g init) := by
  induction l generalizing init with
  | nil => rfl
  | cons a rest ih =>
    simp only [List.forIn_cons, List.foldl_cons, h]
    exact ih _

/-- The loop invariant: no entry seen matches, or the chosen one was seen,
matches, and ranks at least every matching entry seen. -/
private def Best (ternary : Bool) (keys : List Bits) (seen : List Entry) : Option Entry → Prop
  | none => ∀ e ∈ seen, ¬Matches e keys
  | some b => b ∈ seen ∧ Matches b keys ∧
      ∀ e ∈ seen, Matches e keys → rank ternary e ≤ rank ternary b

private theorem foldl_best (ternary : Bool) (keys : List Bits) (rest seen : List Entry)
    (init : Option Entry) (h : Best ternary keys seen init) :
    Best ternary keys (seen ++ rest) (rest.foldl (selectStep ternary keys) init) := by
  induction rest generalizing seen init with
  | nil => simpa using h
  | cons x rest ih =>
    rw [List.foldl_cons, show seen ++ x :: rest = (seen ++ [x]) ++ rest by simp]
    apply ih
    unfold selectStep
    by_cases hx : ((x.keys.zip keys).all fun x => Installed.keyValueMatches x.fst x.snd) = true
    · have hm : Matches x keys := hx
      simp only [hx, ite_true]
      cases init with
      | none =>
        refine ⟨by simp, hm, ?_⟩
        intro e he hme
        simp at he
        rcases he with he | rfl
        · exact absurd hme (h e he)
        · exact Nat.le_refl _
      | some b =>
        obtain ⟨hb, hbm, hmax⟩ := h
        simp only
        split
        · rename_i hbeat
          rw [beats_iff] at hbeat
          refine ⟨by simp, hm, ?_⟩
          intro e he hme
          simp at he
          rcases he with he | rfl
          · exact Nat.le_of_lt (Nat.lt_of_le_of_lt (hmax e he hme) hbeat)
          · exact Nat.le_refl _
        · rename_i hbeat
          rw [beats_iff] at hbeat
          refine ⟨by simp [hb], hbm, ?_⟩
          intro e he hme
          simp at he
          rcases he with he | rfl
          · exact hmax e he hme
          · exact Nat.le_of_not_lt hbeat
    · have hm : ¬Matches x keys := hx
      simp only [hx]
      cases init with
      | none =>
        intro e he
        simp at he
        rcases he with he | rfl
        · exact h e he
        · exact hm
      | some b =>
        obtain ⟨hb, hbm, hmax⟩ := h
        refine ⟨by simp [hb], hbm, ?_⟩
        intro e he hme
        simp at he
        rcases he with he | rfl
        · exact hmax e he hme
        · exact absurd hme hm

private theorem lookup_eq (i : Installed) (ref : TableRef) (keys : List Bits) (decl : Table)
    (ht : i.table? ref = .ok decl) (hk : keys.length = decl.keys.length) :
    i.lookup ref keys =
      match (i.entries.getD ref #[]).toList.foldl
          (selectStep (decl.keys.any (·.matchKind == .ternary)) keys) none with
      | none => .ok { action := i.defaults.getD ref none, hit := false }
      | some entry => .ok { action := some entry.action, hit := true } := by
  unfold Installed.lookup
  simp only [ht, bind, Except.bind, hk, bne_self_eq_false, Bool.false_eq_true, ite_false]
  rw [← Array.forIn_toList, forIn_yield _ _ _ (selectStep _ keys)]
  · cases (i.entries.getD ref #[]).toList.foldl _ none <;> rfl
  · intro e s
    unfold selectStep
    split
    · cases s with
      | none => rfl
      | some b => simp only []; split <;> rfl
    · rfl

/-- A hit runs the action of an installed entry that matches every key and
ranks at least every other matching entry: the longest total prefix, or the
largest priority in a table with a ternary key.

Premises: the table exists, the key count is right, and the lookup hit. It
says nothing of which entry wins a tie, which installation rules out, and it
does not establish that installation kept the entries canonical. -/
theorem lookup_hit (i : Installed) (ref : TableRef) (keys : List Bits) (decl : Table)
    (m : Match) (ht : i.table? ref = .ok decl) (hk : keys.length = decl.keys.length)
    (hl : i.lookup ref keys = .ok m) (hhit : m.hit = true) :
    ∃ e ∈ (i.entries.getD ref #[]).toList, Matches e keys ∧ m.action = some e.action ∧
      ∀ e' ∈ (i.entries.getD ref #[]).toList, Matches e' keys →
        rank (decl.keys.any (·.matchKind == .ternary)) e' ≤
          rank (decl.keys.any (·.matchKind == .ternary)) e := by
  have hb := foldl_best (decl.keys.any (·.matchKind == .ternary)) keys
    (i.entries.getD ref #[]).toList [] none (fun _ h => nomatch h)
  rw [lookup_eq i ref keys decl ht hk] at hl
  simp only [List.nil_append] at hb
  revert hb hl
  cases (i.entries.getD ref #[]).toList.foldl _ none with
  | none => intro hl _; simp only [Except.ok.injEq] at hl; subst hl; simp at hhit
  | some e =>
    intro hl hb
    simp only [Except.ok.injEq] at hl
    subst hl
    exact ⟨e, hb.1, hb.2.1, rfl, hb.2.2⟩

/-- A miss happens only when no installed entry matches, and then runs the
table's current default action.

Premises: the table exists, the key count is right, and the lookup missed.
Read contrapositively: whenever some installed entry matches, the lookup
hits. -/
theorem lookup_miss (i : Installed) (ref : TableRef) (keys : List Bits) (decl : Table)
    (m : Match) (ht : i.table? ref = .ok decl) (hk : keys.length = decl.keys.length)
    (hl : i.lookup ref keys = .ok m) (hmiss : m.hit = false) :
    (∀ e ∈ (i.entries.getD ref #[]).toList, ¬Matches e keys) ∧
      m.action = i.defaults.getD ref none := by
  have hb := foldl_best (decl.keys.any (·.matchKind == .ternary)) keys
    (i.entries.getD ref #[]).toList [] none (fun _ h => nomatch h)
  rw [lookup_eq i ref keys decl ht hk] at hl
  simp only [List.nil_append] at hb
  revert hb hl
  cases (i.entries.getD ref #[]).toList.foldl _ none with
  | none => intro hl hb; simp only [Except.ok.injEq] at hl; subst hl; exact ⟨hb, rfl⟩
  | some e => intro hl _; simp only [Except.ok.injEq] at hl; subst hl; simp at hmiss

/-- In a table without a ternary key, a hit runs the action of a matching
installed entry whose prefix is at least as long as that of every matching
installed entry: the longest prefix wins.

Premises: the table exists and has no ternary key, the key count is right,
and the lookup hit. The prefix length is the sum over the entry's `lpm`
keys; that a table has at most one is the validator's rule, not assumed. -/
theorem lookup_longest_prefix (i : Installed) (ref : TableRef) (keys : List Bits)
    (decl : Table) (m : Match) (ht : i.table? ref = .ok decl)
    (hk : keys.length = decl.keys.length)
    (hnt : decl.keys.any (·.matchKind == .ternary) = false)
    (hl : i.lookup ref keys = .ok m) (hhit : m.hit = true) :
    ∃ e ∈ (i.entries.getD ref #[]).toList, Matches e keys ∧ m.action = some e.action ∧
      ∀ e' ∈ (i.entries.getD ref #[]).toList, Matches e' keys →
        Installed.prefixLength e' ≤ Installed.prefixLength e := by
  have := lookup_hit i ref keys decl m ht hk hl hhit
  simpa [rank, hnt] using this

/-- In a table without a ternary key, a hit runs the action of a matching
installed entry whose `lpm` prefix lengths add up to at least those of every
matching installed entry: the longest prefix, counted as installed, wins.

Premises as in `lookup_longest_prefix`. With `prefixLength_single`, for a
table with one `lpm` key this is that key's prefix length. -/
theorem lookup_longest_lpm (i : Installed) (ref : TableRef) (keys : List Bits)
    (decl : Table) (m : Match) (ht : i.table? ref = .ok decl)
    (hk : keys.length = decl.keys.length)
    (hnt : decl.keys.any (·.matchKind == .ternary) = false)
    (hl : i.lookup ref keys = .ok m) (hhit : m.hit = true) :
    ∃ e ∈ (i.entries.getD ref #[]).toList, Matches e keys ∧ m.action = some e.action ∧
      ∀ e' ∈ (i.entries.getD ref #[]).toList, Matches e' keys →
        (e'.keys.map lpmLength).sum ≤ (e.keys.map lpmLength).sum := by
  simpa [prefixLength_eq] using lookup_longest_prefix i ref keys decl m ht hk hnt hl hhit

end P4bloIR.DeviationLaws
