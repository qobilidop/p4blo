import P4bloIR.Exec
import P4bloIR.ScalarTyping
import P4bloIR.ScalarLaws
import P4bloIR.FieldLaws
import P4bloIR.Theorems
import Std.Data.HashMap.Lemmas

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
-- Parser loop bound across a whole execution: the cursor never moves back
-- ---------------------------------------------------------------------------

/-- What any stretch of execution does to the packet and the revisit record
going from `run` to `run'`. Without a packet, it gains none and leaves the
record as it was. With one, the packet stays, its cursor does not move back,
every recorded cursor is either an old record or one taken between the two
cursors, and no record is dropped. -/
def Advances (run run' : Run) : Prop :=
  match run.packet with
  | none => run'.packet = none ∧ run'.visits = run.visits
  | some p => ∃ p', run'.packet = some p' ∧ p.cursor ≤ p'.cursor ∧
      (∀ (k : String × String) (c : Nat), run'.visits[k]? = some c →
        run.visits[k]? = some c ∨ (p.cursor ≤ c ∧ c ≤ p'.cursor)) ∧
      (∀ k : String × String, (run.visits[k]?).isSome → (run'.visits[k]?).isSome)

private theorem advances_refl (run : Run) : Advances run run := by
  unfold Advances
  split
  · exact ⟨‹_›, rfl⟩
  · rename_i p hp
    exact ⟨p, hp, Nat.le_refl _, fun _ _ h => .inl h, fun _ h => h⟩

private theorem advances_trans {a b c : Run} (hab : Advances a b) (hbc : Advances b c) :
    Advances a c := by
  unfold Advances at *
  split at hab
  · rename_i ha
    obtain ⟨hb, hvb⟩ := hab
    rw [hb] at hbc
    obtain ⟨hc, hvc⟩ := hbc
    exact ⟨hc, hvc.trans hvb⟩
  · rename_i pa ha
    obtain ⟨pb, hb, hab1, hab2, hab3⟩ := hab
    rw [hb] at hbc
    obtain ⟨pc, hc, hbc1, hbc2, hbc3⟩ := hbc
    refine ⟨pc, hc, Nat.le_trans hab1 hbc1, ?_, fun k h => hbc3 k (hab3 k h)⟩
    intro k v hv
    rcases hbc2 k v hv with h | ⟨h1, h2⟩
    · rcases hab2 k v h with h' | ⟨h1', h2'⟩
      · exact .inl h'
      · exact .inr ⟨h1', Nat.le_trans h2' hbc1⟩
    · exact .inr ⟨Nat.le_trans hab1 h1, h2⟩

/-- Every run of `x`, successful or faulted, advances. -/
private def Mono (x : M α) : Prop := ∀ run, Advances run (x.run run).2

private theorem mono_pure (a : α) : Mono (pure a : M α) := fun run => advances_refl run

private theorem mono_bind {x : M α} {f : α → M β} (hx : Mono x) (hf : ∀ a, Mono (f a)) :
    Mono (x >>= f) := by
  intro run
  rw [run_bind]
  have h1 := hx run
  revert h1
  rcases x.run run with ⟨_ | a, run₁⟩
  · exact id
  · intro h1; exact advances_trans h1 (hf a run₁)

private theorem mono_throw (e : Fault) : Mono (throw e : M α) := fun run => advances_refl run

private theorem mono_get : Mono (get : M Run) := fun run => advances_refl run

private theorem mono_modify (f : Run → Run)
    (hf : ∀ r, (f r).packet = r.packet ∧ (f r).visits = r.visits) :
    Mono (modify f : M Unit) := by
  intro run
  show Advances run (f run)
  have ⟨h1, h2⟩ := hf run
  unfold Advances; split
  · exact ⟨h1.trans ‹_›, h2⟩
  · rename_i p hp
    refine ⟨p, h1.trans hp, Nat.le_refl _, ?_, ?_⟩
    · intro k c h; rw [h2] at h; exact .inl h
    · intro k h; rw [h2]; exact h

private theorem mono_map {x : M α} (f : α → β) (hx : Mono x) : Mono (f <$> x) := by
  intro run
  rw [run_map]
  have h1 := hx run
  revert h1
  rcases x.run run with ⟨_ | a, run₁⟩ <;> exact id

private theorem mono_forIn {l : List α} {init : β} {f : α → β → M (ForInStep β)}
    (h : ∀ a b, Mono (f a b)) : Mono (forIn l init f) := by
  induction l generalizing init with
  | nil => exact mono_pure _
  | cons a rest ih =>
    rw [List.forIn_cons]
    refine mono_bind (h a init) (fun r => ?_)
    cases r
    · exact mono_pure _
    · exact ih

private theorem mono_mapM {l : List α} {f : α → M β} (h : ∀ a, Mono (f a)) :
    Mono (l.mapM f) := by
  induction l with
  | nil => exact mono_pure _
  | cons a rest ih =>
    rw [List.mapM_cons]
    exact mono_bind (h a) (fun _ => mono_bind ih (fun _ => mono_pure _))

private theorem mono_allM {l : List α} {f : α → M Bool} (h : ∀ a, Mono (f a)) :
    Mono (l.allM f) := by
  induction l with
  | nil => exact mono_pure _
  | cons a rest ih =>
    rw [List.allM]
    refine mono_bind (h a) (fun b => ?_)
    cases b
    · exact mono_pure _
    · exact ih

private theorem mono_optionMapM {o : Option α} {f : α → M β} (h : ∀ a, Mono (f a)) :
    Mono (o.mapM f) := by
  cases o
  · exact mono_pure _
  · exact mono_map _ (h _)

/-- The leaves `advances_tac` knows; each proved lemma adds a rule. -/
local syntax "advances_leaf" : tactic
local macro_rules | `(tactic| advances_leaf) => `(tactic| fail "no leaf")

/-- Decompose a computation into binds, branches and leaves. -/
local syntax "advances_tac" : tactic
local macro_rules | `(tactic| advances_tac) => `(tactic| repeat' (first
    | with_reducible exact mono_pure _
    | with_reducible exact mono_throw _
    | with_reducible exact mono_get
    | with_reducible assumption
    | with_reducible advances_leaf
    | with_reducible refine mono_bind ?_ (fun _ => ?_)
    | with_reducible refine mono_map _ ?_
    | with_reducible refine mono_modify _ (fun _ => ⟨rfl, rfl⟩)
    | with_reducible refine mono_forIn (fun _ _ => ?_)
    | with_reducible refine mono_mapM (fun _ => ?_)
    | with_reducible refine mono_allM (fun _ => ?_)
    | with_reducible refine mono_optionMapM (fun _ => ?_)
    | split
    | dsimp only))

private theorem mono_throwInterp (msg : String) : Mono (throwInterp msg : M α) := mono_throw _
private theorem mono_throwParse (msg : String) : Mono (throwParse msg : M α) := mono_throw _
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_throwInterp _)
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_throwParse _)
private theorem mono_liftExcept (x : Except String α) : Mono (liftExcept x) := by
  unfold liftExcept; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_liftExcept _)

private theorem mono_getFrame : Mono getFrame := by unfold getFrame; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_getFrame)
private theorem mono_getIndex : Mono getIndex := by unfold getIndex; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_getIndex)
private theorem mono_currentBlock : Mono currentBlock := by unfold currentBlock; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_currentBlock)
private theorem mono_setFrame (f : Frame) : Mono (setFrame f) := by
  unfold setFrame; exact mono_modify _ (fun _ => ⟨rfl, rfl⟩)
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_setFrame _)
private theorem mono_setEmitter (e : Emitter) : Mono (setEmitter e) := by
  unfold setEmitter; exact mono_modify _ (fun _ => ⟨rfl, rfl⟩)
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_setEmitter _)
private theorem mono_readVar (n : String) : Mono (readVar n) := by unfold readVar; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_readVar _)
private theorem mono_writeVar (n : String) (v : Value) : Mono (writeVar n v) := by
  unfold writeVar; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_writeVar _ _)
private theorem mono_requirePacket : Mono requirePacket := by unfold requirePacket; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_requirePacket)
private theorem mono_requireEmitter : Mono requireEmitter := by unfold requireEmitter; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_requireEmitter)
private theorem mono_requireEntries : Mono requireEntries := by unfold requireEntries; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_requireEntries)
private theorem mono_expectBits (v : Value) : Mono (expectBits v) := mono_liftExcept _
private theorem mono_expectBool (v : Value) : Mono (expectBool v) := mono_liftExcept _
private theorem mono_expectHeader (v : Value) : Mono (expectHeader v) := mono_liftExcept _
private theorem mono_expectStack (v : Value) : Mono (expectStack v) := mono_liftExcept _
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_expectBits _)
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_expectBool _)
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_expectHeader _)
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_expectStack _)

private theorem mono_fieldOf (c : Value) (f : String) : Mono (fieldOf c f) := by
  unfold fieldOf; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_fieldOf _ _)

private theorem mono_setField (c : Value) (f : String) (v : Value) : Mono (setField c f v) := by
  unfold setField; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_setField _ _ _)
private theorem mono_elementOf (t : String) (es : List Value) (i : Nat) : Mono (elementOf t es i) := by
  unfold elementOf; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_elementOf _ _ _)
private theorem mono_bitsBinary (op : BinaryOp) (x y : Bits) : Mono (bitsBinary op x y) := by
  unfold bitsBinary; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_bitsBinary _ _ _)
private theorem mono_castValue (t : Ty) (v : Value) : Mono (castValue t v) := by
  unfold castValue; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_castValue _ _)
private theorem mono_lookaheadValue (t : Ty) : Mono (lookaheadValue t) := by
  unfold lookaheadValue; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_lookaheadValue _)

private theorem mono_evaluate (e : Expr) : Mono (evaluate e) := by
  induction e with
  | binary op left right ihl ihr => cases op <;> rw [evaluate] <;> advances_tac <;> (intro h; cases h)
  | _ => rw [evaluate]; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_evaluate _)

private theorem mono_readLValue (lv : LValue) : Mono (readLValue lv) := by
  induction lv <;> rw [readLValue] <;> advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_readLValue _)

private theorem mono_writeLValue (lv : LValue) (v : Value) : Mono (writeLValue lv v) := by
  induction lv generalizing v <;> rw [writeLValue] <;> advances_tac <;> apply_assumption
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_writeLValue _ _)

private theorem mono_resolveLValue (lv : LValue) : Mono (resolveLValue lv) := by
  induction lv <;> rw [resolveLValue] <;> advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_resolveLValue _)


private theorem run_requirePacket_some (run : Run) (p : Packet) (hp : run.packet = some p) :
    requirePacket.run run = (.ok p, run) := by
  cases run; subst hp; rfl

private theorem run_requirePacket_none (run : Run) (hp : run.packet = none) :
    ∃ f, requirePacket.run run = (.error f, run) := by
  cases run; subst hp; exact ⟨_, rfl⟩

/-- `requirePacket` followed by what may use the packet it found. -/
private theorem mono_requirePacket_bind {f : Packet → M β}
    (h : ∀ p run, run.packet = some p → Advances run ((f p).run run).2) :
    Mono (requirePacket >>= f) := by
  intro run
  rw [run_bind]
  cases hp : run.packet with
  | none =>
    obtain ⟨e, he⟩ := run_requirePacket_none run hp
    rw [he]; exact advances_refl run
  | some p =>
    rw [run_requirePacket_some run p hp]
    exact h p run hp

private theorem advances_setPacket (run : Run) (p p' : Packet) (hp : run.packet = some p)
    (hc : p.cursor ≤ p'.cursor) : Advances run ((setPacket p').run run).2 := by
  show Advances run { run with packet := some p' }
  unfold Advances
  rw [hp]
  exact ⟨p', rfl, hc, fun _ _ h => .inl h, fun _ h => h⟩

private theorem mono_packetRead (n : Nat) : Mono (packetRead n) := by
  unfold packetRead
  apply mono_requirePacket_bind
  intro p run hp
  split
  · rename_i raw p' hr
    rw [run_bind]
    have hc : p'.cursor = p.cursor + n := by
      simp only [Packet.read?, bind, Option.bind] at hr
      split at hr
      · cases hr
      · simp only [pure, Option.some.injEq, Prod.mk.injEq] at hr
        obtain ⟨-, rfl⟩ := hr; rfl
    have := advances_setPacket run p p' hp (by omega)
    revert this
    rcases (setPacket p').run run with ⟨_ | _, r⟩
    · exact id
    · intro h; exact h
  · exact advances_refl run
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_packetRead _)

private theorem mono_advance (bits : Expr) : Mono (advance bits) := by
  unfold advance
  refine mono_bind (mono_evaluate _) (fun v => mono_bind (mono_expectBits v) (fun n => ?_))
  apply mono_requirePacket_bind
  intro p run hp
  split
  · rename_i p' ha
    apply advances_setPacket run p p' hp
    simp only [Packet.advance?] at ha
    split at ha
    · cases ha
    · cases ha; exact Nat.le_add_right _ _
  · exact advances_refl run
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_advance _)

private theorem mono_enterState (state : State) : Mono (enterState state) := by
  intro run
  cases hp : run.packet with
  | none =>
    rcases run with ⟨index, entries, externs, frame, packet, emitter, visits⟩
    subst hp
    have h : ((enterState state).run ⟨index, entries, externs, frame, none, emitter, visits⟩).2 =
        ⟨index, entries, externs, frame, none, emitter, visits⟩ := rfl
    rw [h]; exact advances_refl _
  | some p =>
    by_cases hv : run.visits[(run.frame.block.name, state.name)]? = some p.cursor
    · rw [enterState_revisit state run p hp hv]; exact advances_refl run
    · rw [enterState_first state run p hp hv]
      unfold Advances
      simp only [hp]
      refine ⟨p, rfl, Nat.le_refl _, ?_, ?_⟩
      · intro k c h
        simp only [Std.HashMap.getElem?_insert] at h
        split at h
        · cases h; exact .inr ⟨Nat.le_refl _, Nat.le_refl _⟩
        · exact .inl h
      · intro k h
        simp only [Std.HashMap.getElem?_insert]
        split
        · rfl
        · exact h
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_enterState _)

private theorem mono_setValidity (lv : LValue) (b : Bool) : Mono (setValidity lv b) := by
  unfold setValidity; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_setValidity _ _)
private theorem mono_extract (lv : LValue) : Mono (extract lv) := by
  unfold extract; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_extract _)
private theorem mono_verify (c : Expr) (e : String) : Mono (verify c e) := by
  unfold verify; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_verify _ _)

mutual
private theorem mono_emitValue : (v : Value) → Mono (emitValue v)
  | .header _ _ _ => by rw [emitValue]; advances_tac
  | .struct _ fields => by rw [emitValue]; exact mono_emitList fields
  | .stack _ es _ => by rw [emitValue]; exact mono_emitList es
  | .bits _ => by rw [emitValue] <;> first | exact mono_throw _ | (intros; contradiction)
  | .bool _ => by rw [emitValue] <;> first | exact mono_throw _ | (intros; contradiction)
  | .enum _ _ => by rw [emitValue] <;> first | exact mono_throw _ | (intros; contradiction)
  | .error _ => by rw [emitValue] <;> first | exact mono_throw _ | (intros; contradiction)
private theorem mono_emitList : (vs : List Value) → Mono (emitList vs)
  | [] => by rw [emitList]; exact mono_pure _
  | v :: vs => by rw [emitList]; exact mono_bind (mono_emitValue v) (fun _ => mono_emitList vs)
end
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_emitValue _)

private theorem mono_keySetMatches (ks : KeySet) (k : Value) : Mono (keySetMatches ks k) := by
  unfold keySetMatches; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_keySetMatches _ _)
private theorem mono_select (keys : List Expr) (cases : List SelectCase) :
    Mono (select keys cases) := by
  unfold select; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_select _ _)
private theorem mono_transition (t : Transition) : Mono (transition t) := by
  unfold transition; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_transition _)

private theorem mono_argumentValue (p : Param) (a : Arg) : Mono (argumentValue p a) := by
  unfold argumentValue; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_argumentValue _ _)
private theorem mono_resolveArg (p : Param) (a : Arg) : Mono (resolveArg p a) := by
  unfold resolveArg; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_resolveArg _ _)
private theorem mono_copyIn (p : Param) (a : Arg) : Mono (copyIn p a) := by
  unfold copyIn; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_copyIn _ _)
private theorem mono_copyBack (ps : List Param) (as : List Arg) (f : Frame) :
    Mono (copyBack ps as f) := by
  unfold copyBack; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_copyBack _ _ _)
private theorem mono_callExtern (i m : String) (as : List Arg) (r : Option LValue) :
    Mono (callExtern i m as r) := by
  unfold callExtern; advances_tac
local macro_rules | `(tactic| advances_leaf) => `(tactic| exact mono_callExtern _ _ _ _)

private theorem mono_dispatch (w : Execution.Work) : Mono (Execution.dispatch w) := by
  cases w <;> unfold Execution.dispatch <;> advances_tac


/-- One step of the actual machine never moves the cursor back, never drops
a packet or a revisit record, and records only cursors it passed.

Premise: the step continues (it is not the final outcome). No premise on the
work item: statements, table applications, extern calls, block calls and
returns, and state entries alike. It does not establish that the machine
terminates. -/
theorem step_advances (m m' : Execution.Machine) (h : Execution.step m = .inr m') :
    Advances m.run m'.run := by
  unfold Execution.step at h
  split at h
  · cases h
  · split at h
    · cases h; exact advances_refl _
    · rename_i task rest _ _
      have hd := mono_dispatch task m.run
      split at h <;> rename_i heq <;> rw [heq] at hd <;> cases h <;> exact hd

/-- `Reaches m m'`: the actual machine goes from `m` to `m'` in zero or more
steps. -/
inductive Reaches : Execution.Machine → Execution.Machine → Prop
  | refl (m : Execution.Machine) : Reaches m m
  | step {m m' m'' : Execution.Machine} :
      Execution.step m = .inr m' → Reaches m' m'' → Reaches m m''

/-- Any number of steps of the actual machine advances, as one step does.

Premise: `m'` is reached from `m` by actual steps. -/
theorem reaches_advances {m m' : Execution.Machine} (h : Reaches m m') : Advances m.run m'.run := by
  induction h with
  | refl m => exact advances_refl _
  | step hs _ ih => exact advances_trans (step_advances _ _ hs) ih

/-- The cursor is non-decreasing along any execution: whatever runs between
two configurations, the packet is still there and its cursor is at least
where it was.

Premise: `m'` is reached from `m`, which has a packet. -/
theorem reaches_cursor_le {m m' : Execution.Machine} (h : Reaches m m') (p : Packet)
    (hp : m.run.packet = some p) : ∃ p', m'.run.packet = some p' ∧ p.cursor ≤ p'.cursor := by
  have := reaches_advances h
  unfold Advances at this
  rw [hp] at this
  obtain ⟨p', h1, h2, -⟩ := this
  exact ⟨p', h1, h2⟩

/-- Every cursor in the revisit record is at or before the current cursor. -/
def Recorded (run : Run) : Prop :=
  ∀ p, run.packet = some p → ∀ (k : String × String) (c : Nat),
    run.visits[k]? = some c → c ≤ p.cursor

/-- A run with an empty revisit record, as every parser run starts, meets
`Recorded`.

No premise beyond the empty record. -/
theorem recorded_empty (run : Run) (h : run.visits = {}) : Recorded run := by
  intro p _ k c hc
  rw [h] at hc
  simp at hc

/-- `Recorded` is kept by anything that advances.

Premises: the record is behind the cursor, and the run advances. -/
theorem recorded_of_advances {run run' : Run} (hr : Recorded run) (ha : Advances run run') :
    Recorded run' := by
  intro p' hp' k c hc
  unfold Advances at ha
  split at ha
  · rw [ha.1] at hp'; cases hp'
  · rename_i p hp
    obtain ⟨q, hq, hle, hvis, -⟩ := ha
    rw [hq] at hp'; cases hp'
    rcases hvis k c hc with h | ⟨-, h⟩
    · exact Nat.le_trans (hr p hp k c h) hle
    · exact h

/-- `Recorded` holds at every configuration the machine reaches from one
where it holds, in particular from the empty record of a fresh parser run.

Premises: `Recorded` at `m`, and `m'` reached from `m`. -/
theorem reaches_recorded {m m' : Execution.Machine} (h : Reaches m m') (hr : Recorded m.run) :
    Recorded m'.run :=
  recorded_of_advances hr (reaches_advances h)

/-- A state entered again without timing out finds the cursor strictly past
where it was at the state's last entry in this block: the cursor advanced.

Premises: the record is behind the cursor (`Recorded`, which every reached
configuration keeps by `reaches_recorded`), the state was entered before at
cursor `c`, and this entry succeeded. It does not establish how far the
cursor moved. -/
theorem enterState_advanced (state : State) (run run' : Run) (p : Packet) (c : Nat)
    (hr : Recorded run) (hp : run.packet = some p)
    (hv : run.visits[(run.frame.block.name, state.name)]? = some c)
    (h : (enterState state).run run = (.ok (), run')) : c < p.cursor := by
  have hle := hr p hp _ c hv
  rcases Nat.lt_or_eq_of_le hle with hlt | heq
  · exact hlt
  · subst heq
    rw [enterState_revisit state run p hp hv] at h
    cases h

/-- After a successful entry at cursor `p`, the record for that state holds
`p` again at any later run whose cursor is back at `p`. -/
private theorem visits_kept (state : State) (run run₀ run₁ : Run) (p p₁ : Packet)
    (hp : run.packet = some p) (h₀ : (enterState state).run run = (.ok (), run₀))
    (ha : Advances run₀ run₁) (hp₁ : run₁.packet = some p₁) (hc : p₁.cursor = p.cursor) :
    run₁.visits[(run.frame.block.name, state.name)]? = some p.cursor := by
  by_cases hv : run.visits[(run.frame.block.name, state.name)]? = some p.cursor
  · rw [enterState_revisit state run p hp hv] at h₀; cases h₀
  rw [enterState_first state run p hp hv] at h₀
  simp only [Prod.mk.injEq] at h₀
  obtain ⟨-, rfl⟩ := h₀
  unfold Advances at ha
  simp only [hp] at ha
  obtain ⟨q, hq, _, hvis, hkeep⟩ := ha
  rw [hp₁] at hq; cases hq
  have hin : ({ run with visits := run.visits.insert (run.frame.block.name, state.name) p.cursor } :
      Run).visits[(run.frame.block.name, state.name)]? = some p.cursor := by simp
  obtain ⟨c', hc'⟩ := Option.isSome_iff_exists.mp (hkeep _ (by rw [hin]; rfl))
  rcases hvis _ c' hc' with h | ⟨h1, h2⟩
  · rw [hin] at h; cases h; exact hc'
  · rw [hc'] ; congr 1; omega

/-- A state entered successfully and then entered again, in the same block
and with the cursor where it was at the first entry, times out, whatever ran
in between.

Premises: the first entry succeeded; everything between advances (as any
reached configuration does, by `reaches_advances`), including other states,
statements and sub-parser calls and returns; the second entry names the same
state in an activation of the same block, with the cursor unchanged. It does
not establish that a non-consuming loop reaches such a second entry. -/
theorem enterState_no_consumption (state state' : State) (run run₀ run₁ : Run) (p p₁ : Packet)
    (hp : run.packet = some p) (h₀ : (enterState state).run run = (.ok (), run₀))
    (ha : Advances run₀ run₁) (hp₁ : run₁.packet = some p₁) (hc : p₁.cursor = p.cursor)
    (hb : run₁.frame.block.name = run.frame.block.name) (hn : state'.name = state.name) :
    (enterState state').run run₁ = (.error (.parse "ParserTimeout"), run₁) := by
  apply enterState_revisit state' run₁ p₁ hp₁
  rw [hb, hn, hc]
  exact visits_kept state run run₀ run₁ p p₁ hp h₀ ha hp₁ hc

/-- On the actual machine, a state entered successfully and later reached
again in the same block with the cursor unchanged starts unwinding with
`ParserTimeout`, whatever steps ran in between. This covers a sub-parser
applied twice without consumption in between: the run keeps one revisit
record across the call boundary, so the sub-parser's start state is entered
twice at one cursor in activations of the sub-parser's block.

Premises: the first entry is the machine's next item, with no fault pending,
and succeeded; the second entry is reached from there, is the next item with
no fault pending, names the same state, and runs in an activation of the same
block with the cursor where it was. It does not establish that a
non-consuming loop reaches the second entry, nor the run's final outcome. -/
theorem reaches_state_revisit (scope scope' : BlockScope) (state state' : State)
    (rest rest' : List Execution.Work) (m₀ m₁ m₂ : Execution.Machine) (p p₂ : Packet)
    (hw₀ : m₀.work = .state scope state :: rest) (hf₀ : m₀.fault = none)
    (hp : m₀.run.packet = some p)
    (h₁ : Execution.step m₀ = .inr m₁) (hf₁ : m₁.fault = none) (hr : Reaches m₁ m₂)
    (hw₂ : m₂.work = .state scope' state' :: rest') (hf₂ : m₂.fault = none)
    (hp₂ : m₂.run.packet = some p₂) (hc : p₂.cursor = p.cursor)
    (hb : m₂.run.frame.block.name = m₀.run.frame.block.name) (hn : state'.name = state.name) :
    Execution.step m₂ =
      .inr { work := rest', run := m₂.run, fault := some (.parse "ParserTimeout") } := by
  obtain ⟨work₂, run₂, fault₂⟩ := m₂
  simp only at hw₂ hf₂ hp₂ hb ⊢
  subst hw₂ hf₂
  -- the first entry succeeded, leaving m₁.run
  have hentry : (enterState state).run m₀.run = (.ok (), m₁.run) := by
    obtain ⟨work₀, run₀, fault₀⟩ := m₀
    simp only at hw₀ hf₀ hp ⊢
    subst hw₀ hf₀
    unfold Execution.step at h₁
    simp only [Option.isSome_none, Bool.false_and, Bool.false_eq_true, ite_false] at h₁
    unfold Execution.dispatch at h₁
    rw [run_bind] at h₁
    revert h₁
    rcases (enterState state).run run₀ with ⟨_ | u, r⟩
    · intro h₁; cases h₁; cases hf₁
    · intro h₁; cases h₁; rfl
  have hv := visits_kept state m₀.run m₁.run run₂ p p₂ hp hentry (reaches_advances hr) hp₂ hc
  rw [← hb, ← hn, ← hc] at hv
  exact step_state_revisit scope' state' rest' run₂ p₂ hp₂ hv

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
