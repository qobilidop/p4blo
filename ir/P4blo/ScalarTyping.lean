import P4blo.Eval

/-!
# A sound checker for closed scalar expressions

This is an incremental validity boundary, not a whole-program validator.
The checker accepts bits and boolean literals, every scalar unary and binary
operator, the permitted scalar casts, slices, and muxes. It rejects variables,
containers, enum/error literals, and packet lookahead, including such nodes in
unselected branches. Widths must be positive, literals must fit, and slices and
casts follow the schema's restrictions.

`check` produces typing evidence without evaluating values. `check_sound`
connects that evidence to the actual `P4blo.evaluate`: for every initial run,
evaluation succeeds with exactly the inferred scalar type and preserves the
entire run. It assumes neither a valid program nor a well-formed run. There is
no second evaluator here and no theorem about Python, statements, or programs.
-/

namespace P4blo.ScalarTyping

inductive ScalarTy
  | bits (width : Nat)
  | boolean
  deriving BEq, DecidableEq, Repr

/-- Exact value shape and width; `Bits.isLt` already enforces the range. -/
inductive HasType : Value → ScalarTy → Prop
  | bits (b : Bits) : HasType (.bits b) (.bits b.width)
  | boolean (b : Bool) : HasType (.bool b) .boolean

def unaryType : UnaryOp → ScalarTy → Option ScalarTy
  | .not, .boolean => some .boolean
  | .complement, .bits n | .negate, .bits n => some (.bits n)
  | _, _ => none

def binaryType (op : BinaryOp) (left right : ScalarTy) : Option ScalarTy :=
  match op, left, right with
  | .and, .boolean, .boolean | .or, .boolean, .boolean => some .boolean
  | .eq, a, b | .ne, a, b => if a = b then some .boolean else none
  | .concat, .bits n, .bits m => some (.bits (n + m))
  | .shl, .bits n, .bits _ | .shr, .bits n, .bits _ => some (.bits n)
  | .lt, .bits n, .bits m | .le, .bits n, .bits m
  | .gt, .bits n, .bits m | .ge, .bits n, .bits m =>
    if n = m then some .boolean else none
  | .add, .bits n, .bits m | .sub, .bits n, .bits m
  | .mul, .bits n, .bits m | .addSat, .bits n, .bits m
  | .subSat, .bits n, .bits m | .bitAnd, .bits n, .bits m
  | .bitOr, .bits n, .bits m | .bitXor, .bits n, .bits m =>
    if n = m then some (.bits n) else none
  | _, _, _ => none

def castType : Ty → ScalarTy → Option ScalarTy
  | .bits n, .bits _ => if 0 < n then some (.bits n) else none
  | .bits n, .boolean => if n = 1 then some (.bits n) else none
  | .boolean, .bits n => if n = 1 then some .boolean else none
  | _, _ => none

/-- Syntax-directed evidence for precisely the supported fragment. -/
inductive Typed : Expr → ScalarTy → Prop
  | bits (width value : Nat) (positive : 0 < width) (fits : value < 2 ^ width) :
      Typed (.literal (.bits width value)) (.bits width)
  | boolean (value : Bool) : Typed (.literal (.boolean value)) .boolean
  | unary {e a b} (op : UnaryOp) :
      Typed e a → unaryType op a = some b → Typed (.unary op e) b
  | binary {left right a b c} (op : BinaryOp) :
      Typed left a → Typed right b → binaryType op a b = some c →
      Typed (.binary op left right) c
  | cast {e a b} (to : Ty) :
      Typed e a → castType to a = some b → Typed (.cast to e) b
  | slice {e n} (hi lo : Nat) :
      Typed e (.bits n) → lo ≤ hi → hi < n →
      Typed (.slice e hi lo) (.bits (hi - lo + 1))
  | mux {cond left right t} :
      Typed cond .boolean → Typed left t → Typed right t →
      Typed (.mux cond left right) t

/-- A total executable checker. Proofs erase at runtime; only types are
computed. `none` includes both malformed and unsupported expressions. -/
def check : (e : Expr) → Option { t : ScalarTy // Typed e t }
  | .literal (.bits n v) =>
    if hp : 0 < n then
      if hv : v < 2 ^ n then some ⟨.bits n, .bits n v hp hv⟩ else none
    else none
  | .literal (.boolean b) => some ⟨.boolean, .boolean b⟩
  | .unary op e => do
    let ⟨a, ha⟩ ← check e
    match h : unaryType op a with
    | some b => some ⟨b, .unary op ha h⟩
    | none => none
  | .binary op left right => do
    let ⟨a, ha⟩ ← check left
    let ⟨b, hb⟩ ← check right
    match h : binaryType op a b with
    | some c => some ⟨c, .binary op ha hb h⟩
    | none => none
  | .cast to e => do
    let ⟨a, ha⟩ ← check e
    match h : castType to a with
    | some b => some ⟨b, .cast to ha h⟩
    | none => none
  | .slice e hi lo => do
    let ⟨.bits n, hn⟩ ← check e | none
    if hl : lo ≤ hi then
      if hh : hi < n then some ⟨.bits (hi - lo + 1), .slice hi lo hn hl hh⟩
      else none
    else none
  | .mux cond left right => do
    let ⟨.boolean, hc⟩ ← check cond | none
    let ⟨a, ha⟩ ← check left
    let ⟨b, hb⟩ ← check right
    if h : a = b then some ⟨a, .mux hc ha (h ▸ hb)⟩ else none
  | .literal (.enumMember ..) | .literal (.error ..)
  | .var .. | .member .. | .index .. | .lastIndex ..
  | .isValid .. | .lookahead .. => none

/-- Type-only interface, convenient for callers and tests. -/
def infer (e : Expr) : Option ScalarTy := (check e).map Subtype.val

/-- Stronger than state preservation for one run: the computation itself
is pure and its result has the exact type. -/
def PureTyped (m : M Value) (t : ScalarTy) : Prop :=
  ∃ v, m = pure v ∧ HasType v t

private theorem expectBits_bits (b : Bits) : expectBits (.bits b) = pure b := rfl
private theorem expectBool_bool (b : Bool) : expectBool (.bool b) = pure b := rfl

private theorem unary_sound (op : UnaryOp) (he : PureTyped (evaluate e) a)
    (ht : unaryType op a = some b) : PureTyped (evaluate (.unary op e)) b := by
  obtain ⟨v, he, hv⟩ := he
  cases hv <;> cases op <;> simp [unaryType] at ht <;> subst b
  all_goals
    simp [evaluate, he, expectBits, expectBool, Value.expectBits, Value.expectBool, liftExcept]
    exact ⟨_, rfl, by constructor⟩

private theorem binary_sound (op : BinaryOp)
    (hl : PureTyped (evaluate left) a) (hr : PureTyped (evaluate right) b)
    (ht : binaryType op a b = some c) :
    PureTyped (evaluate (.binary op left right)) c := by
  obtain ⟨lv, hl, hltype⟩ := hl
  obtain ⟨rv, hr, hrtype⟩ := hr
  cases op <;> cases hltype <;> cases hrtype <;> simp [binaryType] at ht
  all_goals
    first | obtain ⟨_, rfl⟩ := ht | obtain rfl := ht
    simp [evaluate, hl, hr, expectBits_bits, expectBool_bool, bitsBinary]
    first
    | exact ⟨_, rfl, by constructor⟩
    | split <;> exact ⟨_, rfl, by constructor⟩

private theorem cast_sound (to : Ty) (he : PureTyped (evaluate e) a)
    (ht : castType to a = some b) : PureTyped (evaluate (.cast to e)) b := by
  obtain ⟨v, he, hv⟩ := he
  cases hv <;> cases to <;> simp [castType] at ht
  all_goals
    obtain ⟨_, rfl⟩ := ht
    simp [evaluate, he, castValue, expectBits_bits]
    exact ⟨_, rfl, by constructor⟩

/-- Typing evidence implies successful, pure evaluation in the real
interpreter, with the precise result type. -/
theorem Typed.sound (h : Typed e t) : PureTyped (evaluate e) t := by
  induction h with
  | bits n v _ _ => exact ⟨_, rfl, .bits (Bits.wrap n v)⟩
  | boolean b => exact ⟨_, rfl, .boolean b⟩
  | unary op _ ht ih => exact unary_sound op ih ht
  | binary op _ _ ht ihl ihr => exact binary_sound op ihl ihr ht
  | cast to _ ht ih => exact cast_sound to ih ht
  | slice hi lo _ hlo _ ih =>
    obtain ⟨v, he, hv⟩ := ih
    cases hv
    simp [evaluate, he, expectBits_bits, Nat.not_lt_of_ge hlo]
    exact ⟨_, rfl, by constructor⟩
  | mux _ _ _ ihc ihl ihr =>
    obtain ⟨v, hc, hv⟩ := ihc
    cases hv with
    | boolean b =>
      cases b <;> simp [evaluate, hc, expectBool_bool]
      · exact ihr
      · exact ihl

/-- Acceptance certifies an exactly typed result, absence of either kind
of fault, and preservation of every component of the initial run. -/
theorem check_sound (h : infer e = some t) (run : Run) :
    ∃ v, (evaluate e).run run = (.ok v, run) ∧ HasType v t := by
  unfold infer at h
  cases hc : check e with
  | none => simp [hc] at h
  | some checked =>
    simp [hc] at h
    obtain ⟨v, hv, ht⟩ := checked.property.sound
    exact ⟨v, by rw [hv]; rfl, h ▸ ht⟩

end P4blo.ScalarTyping
