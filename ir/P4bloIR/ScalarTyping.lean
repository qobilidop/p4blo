import P4bloIR.Eval

/-!
# Sound and complete scoped scalar checking

This is an incremental validity boundary, not a whole-program validator.
The checker accepts bits and boolean literals, every scalar unary and binary
operator, the permitted scalar casts, slices, muxes, and variables declared in
a valid finite context. It rejects containers, enum/error literals and packet lookahead, including such nodes in
unselected branches. Widths must be positive, literals must fit, and slices and
casts follow the schema's restrictions.

`checkIn` rejects malformed contexts, including unused duplicate/empty names
and nonpositive widths. Its soundness requires explicitly type-related runtime
bindings, respecting action-layer shadowing. Completeness is relative to the
syntax-directed fragment, not all IR programs. The empty-context `check`,
`infer` and `Typed` interfaces preserve the closed fragment.

`check` produces typing evidence without evaluating values. `check_sound`
connects that evidence to the actual `P4bloIR.evaluate`: for every initial run,
evaluation succeeds with exactly the inferred scalar type and preserves the
entire run. It assumes neither a valid program nor a well-formed run. There is
no second evaluator here and no theorem about Python, statements, or programs.
-/

namespace P4bloIR.ScalarTyping

inductive ScalarTy
  | bits (width : Nat)
  | boolean
  deriving BEq, DecidableEq, Repr

/-- A finite scoped environment, independently checked before inference. -/
abbrev Context := List (String × ScalarTy)

def ScalarTy.Valid : ScalarTy → Prop
  | .bits width => 0 < width
  | .boolean => True

instance (t : ScalarTy) : Decidable t.Valid := by cases t <;> unfold ScalarTy.Valid <;> infer_instance

def Context.WellFormed (ctx : Context) : Prop :=
  (ctx.map Prod.fst).Nodup ∧ ∀ binding ∈ ctx, binding.1 ≠ "" ∧ binding.2.Valid

instance (ctx : Context) : Decidable ctx.WellFormed := by
  unfold Context.WellFormed
  infer_instance

def Context.lookup : Context → String → Option ScalarTy
  | [], _ => none
  | (name, ty) :: rest, key => if key = name then some ty else Context.lookup rest key

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
inductive TypedIn (ctx : Context) : Expr → ScalarTy → Prop
  | bits (width value : Nat) (positive : 0 < width) (fits : value < 2 ^ width) :
      TypedIn ctx (.literal (.bits width value)) (.bits width)
  | boolean (value : Bool) : TypedIn ctx (.literal (.boolean value)) .boolean
  | var {name t} : Context.lookup ctx name = some t → TypedIn ctx (.var name) t
  | unary {e a b} (op : UnaryOp) :
      TypedIn ctx e a → unaryType op a = some b → TypedIn ctx (.unary op e) b
  | binary {left right a b c} (op : BinaryOp) :
      TypedIn ctx left a → TypedIn ctx right b → binaryType op a b = some c →
      TypedIn ctx (.binary op left right) c
  | cast {e a b} (to : Ty) :
      TypedIn ctx e a → castType to a = some b → TypedIn ctx (.cast to e) b
  | slice {e n} (hi lo : Nat) :
      TypedIn ctx e (.bits n) → lo ≤ hi → hi < n →
      TypedIn ctx (.slice e hi lo) (.bits (hi - lo + 1))
  | mux {cond left right t} :
      TypedIn ctx cond .boolean → TypedIn ctx left t → TypedIn ctx right t →
      TypedIn ctx (.mux cond left right) t

/-- The original closed judgment is the empty-context specialization. -/
abbrev Typed := TypedIn []

/-- A total executable checker. Proofs erase at runtime; only types are
computed. `none` includes both malformed and unsupported expressions. -/
private def checkCore (ctx : Context) : (e : Expr) → Option { t : ScalarTy // TypedIn ctx e t }
  | .literal (.bits n v) =>
    if hp : 0 < n then
      if hv : v < 2 ^ n then some ⟨.bits n, .bits n v hp hv⟩ else none
    else none
  | .literal (.boolean b) => some ⟨.boolean, .boolean b⟩
  | .var name => match h : Context.lookup ctx name with
    | some t => some ⟨t, .var h⟩
    | none => none
  | .unary op e => do
    let ⟨a, ha⟩ ← checkCore ctx e
    match h : unaryType op a with
    | some b => some ⟨b, .unary op ha h⟩
    | none => none
  | .binary op left right => do
    let ⟨a, ha⟩ ← checkCore ctx left
    let ⟨b, hb⟩ ← checkCore ctx right
    match h : binaryType op a b with
    | some c => some ⟨c, .binary op ha hb h⟩
    | none => none
  | .cast to e => do
    let ⟨a, ha⟩ ← checkCore ctx e
    match h : castType to a with
    | some b => some ⟨b, .cast to ha h⟩
    | none => none
  | .slice e hi lo => do
    let ⟨.bits n, hn⟩ ← checkCore ctx e | none
    if hl : lo ≤ hi then
      if hh : hi < n then some ⟨.bits (hi - lo + 1), .slice hi lo hn hl hh⟩
      else none
    else none
  | .mux cond left right => do
    let ⟨.boolean, hc⟩ ← checkCore ctx cond | none
    let ⟨a, ha⟩ ← checkCore ctx left
    let ⟨b, hb⟩ ← checkCore ctx right
    if h : a = b then some ⟨a, .mux hc ha (h ▸ hb)⟩ else none
  | .literal (.enumMember ..) | .literal (.error ..)
  | .member .. | .index .. | .lastIndex ..
  | .isValid .. | .lookahead .. => none

/-- Acceptance checks the entire finite context, including unused bindings. -/
def checkIn (ctx : Context) (e : Expr) : Option { t : ScalarTy // TypedIn ctx e t } :=
  if ctx.WellFormed then checkCore ctx e else none

def inferIn (ctx : Context) (e : Expr) : Option ScalarTy := (checkIn ctx e).map Subtype.val

def check (e : Expr) : Option { t : ScalarTy // Typed e t } := checkIn [] e

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
  | var h => simp [Context.lookup] at h
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

private theorem checkCore_complete (h : TypedIn ctx e t) :
    checkCore ctx e = some ⟨t, h⟩ := by
  induction h with
  | bits n v hp hv => simp [checkCore, hp, hv]
  | boolean b => rfl
  | var h => simp only [checkCore]; split <;> grind
  | unary op _ ht ih => simp [checkCore, ih]; split <;> grind
  | binary op _ _ ht ihl ihr =>
    simp [checkCore, ihl, ihr]; split <;> grind
  | cast to _ ht ih => simp [checkCore, ih]; split <;> grind
  | slice hi lo _ hlo hhi ih => simp [checkCore, ih, hlo, hhi]
  | mux _ _ _ ihc ihl ihr => simp [checkCore, ihc, ihl, ihr]

/-- Completeness is relative to this syntax-directed scalar fragment and a
valid finite context, not all valid IR programs. -/
theorem checkIn_complete (hw : ctx.WellFormed) (h : TypedIn ctx e t) :
    inferIn ctx e = some t := by
  simp [inferIn, checkIn, hw, checkCore_complete h]

/-- The public checker cannot accept an invalid context, even for a literal
which never reads its malformed or duplicate bindings. -/
theorem checkIn_typed (h : inferIn ctx e = some t) :
    ctx.WellFormed ∧ TypedIn ctx e t := by
  unfold inferIn checkIn at h
  split at h
  next hw =>
    cases hc : checkCore ctx e with
    | none => simp [hc] at h
    | some checked =>
      simp [hc] at h
      exact ⟨hw, h ▸ checked.property⟩
  next => simp at h

theorem check_complete (h : Typed e t) : infer e = some t := by
  exact checkIn_complete (by simp [Context.WellFormed]) h

/-- Type agreement follows the actual action-first frame lookup. It neither
validates declarations nor assumes that a name missing at runtime is zero. -/
def FrameTyped (ctx : Context) (frame : Frame) : Prop :=
  ∀ name t, Context.lookup ctx name = some t →
    ∃ value, frame.read? name = some value ∧ HasType value t

def RunTyped (m : M Value) (t : ScalarTy) (run : Run) : Prop :=
  ∃ value, m.run run = (.ok value, run) ∧ HasType value t

@[simp] theorem run_pure (a : α) (run : Run) :
    (pure a : M α).run run = (.ok a, run) := rfl

theorem run_bind (m : M α) (f : α → M β) (run : Run) :
    (m >>= f).run run = match m.run run with
      | (.ok a, next) => (f a).run next
      | (.error fault, next) => (.error fault, next) := by
  unfold M.run ExceptT.run StateT.run Id.run
  simp only [bind, ExceptT.bind, ExceptT.mk, StateT.bind, ExceptT.bindCont]
  cases m run with
  | mk result next => cases result <;> rfl

theorem run_map (f : α → β) (m : M α) (run : Run) :
    (f <$> m).run run = match m.run run with
      | (.ok a, next) => (.ok (f a), next)
      | (.error fault, next) => (.error fault, next) := by
  unfold M.run ExceptT.run StateT.run Id.run
  simp only [Functor.map, ExceptT.map, ExceptT.mk, bind, StateT.bind]
  cases m run with
  | mk result next => cases result <;> rfl

@[simp] theorem run_getFrame (run : Run) : getFrame.run run = (.ok run.frame, run) := rfl

private theorem unary_run_sound (op : UnaryOp) (he : RunTyped (evaluate e) a run)
    (ht : unaryType op a = some b) : RunTyped (evaluate (.unary op e)) b run := by
  obtain ⟨v, he, hv⟩ := he
  cases hv <;> cases op <;> simp [unaryType] at ht <;> subst b
  all_goals
    simp [RunTyped, evaluate, run_bind, he, expectBits_bits, expectBool_bool]
    constructor

private theorem binary_run_sound (op : BinaryOp)
    (hl : RunTyped (evaluate left) a run) (hr : RunTyped (evaluate right) b run)
    (ht : binaryType op a b = some c) :
    RunTyped (evaluate (.binary op left right)) c run := by
  obtain ⟨lv, hl, hltype⟩ := hl
  obtain ⟨rv, hr, hrtype⟩ := hr
  cases op <;> cases hltype <;> cases hrtype <;> simp [binaryType] at ht
  all_goals
    first | obtain ⟨_, rfl⟩ := ht | obtain rfl := ht
    simp [RunTyped, evaluate, run_bind, run_map, hl, hr,
      expectBits_bits, expectBool_bool, bitsBinary]
    first
    | exact .bits _
    | exact .boolean _
    | split <;> first
      | exact .bits _
      | exact .boolean _
      | (simp [run_bind, hr, expectBool_bool]; constructor)

private theorem cast_run_sound (to : Ty) (he : RunTyped (evaluate e) a run)
    (ht : castType to a = some b) : RunTyped (evaluate (.cast to e)) b run := by
  obtain ⟨v, he, hv⟩ := he
  cases hv <;> cases to <;> simp [castType] at ht
  all_goals
    obtain ⟨_, rfl⟩ := ht
    simp [RunTyped, evaluate, run_bind, he, castValue, expectBits_bits]
    constructor

/-- Open scalar evaluation preserves every Run component, including when
values are supplied by an active action layer. The frame premise is explicit. -/
theorem TypedIn.sound_run (h : TypedIn ctx e t) (hf : FrameTyped ctx run.frame) :
    RunTyped (evaluate e) t run := by
  induction h with
  | bits n v _ _ => exact ⟨_, rfl, .bits (Bits.wrap n v)⟩
  | boolean b => exact ⟨_, rfl, .boolean b⟩
  | @var name ty found =>
    obtain ⟨v, hv, ht⟩ := hf _ _ found
    refine ⟨v, ?_, ht⟩
    simp [evaluate, readVar, run_bind, hv]
  | unary op _ ht ih => exact unary_run_sound op ih ht
  | binary op _ _ ht ihl ihr => exact binary_run_sound op ihl ihr ht
  | cast to _ ht ih => exact cast_run_sound to ih ht
  | slice hi lo _ hlo _ ih =>
    obtain ⟨v, he, hv⟩ := ih
    cases hv
    simp [RunTyped, evaluate, run_bind, he, expectBits_bits, Nat.not_lt_of_ge hlo]
    constructor
  | mux _ _ _ ihc ihl ihr =>
    obtain ⟨v, hc, hv⟩ := ihc
    cases hv with
    | boolean b =>
      cases b <;> simpa [RunTyped, evaluate, run_bind, hc, expectBool_bool] using
        (show RunTyped (evaluate _) _ run from by assumption)

theorem checkIn_sound (h : inferIn ctx e = some t) (hf : FrameTyped ctx run.frame) :
    RunTyped (evaluate e) t run := (checkIn_typed h).2.sound_run hf

end P4bloIR.ScalarTyping
