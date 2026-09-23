import P4blo.ScalarContext

/-!
# Typed scalar construction

One source AST over typed reads, with independent Fin/Bool meanings.
`Expr` and `denote` retain the closed interface as specializations. Open
lowering preserves exact source meaning under explicit value agreement;
neither value agreement nor scalar typing certifies an entire program.
-/

namespace P4blo.Scalar

inductive ExprWith (Reads : Ty → Type) : Ty → Type
  | bits {width : Nat} (positive : 0 < width) (value : Fin (2 ^ width)) :
      ExprWith Reads (.bits width)
  | boolean (value : Bool) : ExprWith Reads .boolean
  | read : Reads t → ExprWith Reads t
  | add {width : Nat} : ExprWith Reads (.bits width) → ExprWith Reads (.bits width) → ExprWith Reads (.bits width)
  | eqBits {width : Nat} : ExprWith Reads (.bits width) → ExprWith Reads (.bits width) → ExprWith Reads .boolean
  | mux {t : Ty} : ExprWith Reads .boolean → ExprWith Reads t → ExprWith Reads t → ExprWith Reads t

abbrev ExprIn (ctx : Context) := ExprWith (Ref ctx)

namespace ExprIn
abbrev bits {ctx : Context} := @ExprWith.bits (Ref ctx)
abbrev boolean {ctx : Context} := @ExprWith.boolean (Ref ctx)
abbrev read {ctx : Context} := @ExprWith.read (Ref ctx)
abbrev add {ctx : Context} := @ExprWith.add (Ref ctx)
abbrev eqBits {ctx : Context} := @ExprWith.eqBits (Ref ctx)
abbrev mux {ctx : Context} := @ExprWith.mux (Ref ctx)
end ExprIn

abbrev Expr := ExprIn []

namespace Expr
abbrev bits := @ExprWith.bits (Ref [])
abbrev boolean := @ExprWith.boolean (Ref [])
abbrev add := @ExprWith.add (Ref [])
abbrev eqBits := @ExprWith.eqBits (Ref [])
abbrev mux := @ExprWith.mux (Ref [])
end Expr

def denoteWith (read : {u : Ty} → Reads u → Meaning u) : ExprWith Reads t → Meaning t
  | .bits _ value => value
  | .boolean value => value
  | .read ref => read ref
  | .add left right =>
    ⟨((denoteWith read left).val + (denoteWith read right).val) % 2 ^ _,
      Nat.mod_lt _ (Nat.two_pow_pos _)⟩
  | .eqBits left right => (denoteWith read left).val == (denoteWith read right).val
  | .mux condition yes no => if denoteWith read condition = true then denoteWith read yes else denoteWith read no

def denoteIn (env : Env ctx) (e : ExprIn ctx t) : Meaning t :=
  denoteWith (fun ref => env.get ref) e

def denote (e : Expr t) : Meaning t := denoteIn .nil e

def lowerWith (read : {u : Ty} → Reads u → P4bloIR.Expr) : ExprWith Reads t → P4bloIR.Expr
  | .bits (width := width) _ value => .literal (.bits width value.val)
  | .boolean value => .literal (.boolean value)
  | .read ref => read ref
  | .add left right => .binary .add (lowerWith read left) (lowerWith read right)
  | .eqBits left right => .binary .eq (lowerWith read left) (lowerWith read right)
  | .mux condition yes no => .mux (lowerWith read condition) (lowerWith read yes) (lowerWith read no)

def lower (e : ExprIn ctx t) : P4bloIR.Expr := lowerWith (fun ref => .var ref.name) e

theorem lower_typed_in (e : ExprIn ctx t)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) :
    P4bloIR.ScalarTyping.TypedIn ctx (lower e) t := by
  induction e with
  | bits positive value => exact .bits _ _ positive value.isLt
  | boolean value => exact .boolean value
  | read ref => exact .var (ref.lookup hw)
  | add _ _ hl hr => exact .binary .add hl hr (by simp [P4bloIR.ScalarTyping.binaryType])
  | eqBits _ _ hl hr => exact .binary .eq hl hr (by simp [P4bloIR.ScalarTyping.binaryType])
  | mux _ _ _ hc hl hr => exact .mux hc hl hr

theorem lower_typed (e : Expr t) : P4bloIR.ScalarTyping.Typed (lower e) t :=
  lower_typed_in e (by simp [P4bloIR.ScalarTyping.Context.WellFormed])

/-- One compositional operator proof. Concrete public instances discharge
the leaf law with actual frame/path correspondence, not an arbitrary
assumption of correctness for the whole expression. -/
theorem evaluate_lower_with (e : ExprWith Reads t)
    (read : {u : Ty} → Reads u → Meaning u)
    (lowerRead : {u : Ty} → Reads u → P4bloIR.Expr) (run : P4bloIR.Run)
    (hr : ∀ {u} (ref : Reads u), (P4bloIR.evaluate (lowerRead ref)).run run =
      (.ok (toValue (read ref)), run)) :
    (P4bloIR.evaluate (lowerWith lowerRead e)).run run =
      (.ok (toValue (denoteWith read e)), run) := by
  have hb (b : P4bloIR.Bits) : P4bloIR.expectBits (.bits b) = pure b := rfl
  have hbool (b : Bool) : P4bloIR.expectBool (.bool b) = pure b := rfl
  induction e with
  | bits positive value =>
    simp [lowerWith, P4bloIR.evaluate, P4bloIR.literalValue, P4bloIR.Literal.toValue,
      P4bloIR.ScalarTyping.run_pure, P4bloIR.Bits.wrap, denoteWith, toValue,
      Nat.mod_eq_of_lt value.isLt]
  | boolean value => rfl
  | read ref => exact hr ref
  | add left right hl hr =>
    simp [lowerWith, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind,
      hl, hr, toValue, hb, P4bloIR.bitsBinary,
      denoteWith, P4bloIR.Bits.wrap]
  | eqBits left right hl hr =>
    simp [lowerWith, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind,
      P4bloIR.ScalarTyping.run_map, hl, hr,
      denoteWith, toValue]
  | mux condition yes no hc hl hr =>
    cases h : denoteWith read condition <;>
      simp [lowerWith, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind, hc,
        hl, hr, hbool, denoteWith, toValue, h]

/-- Exact source value and the entire Run under real action-first frame
agreement. Declarations and whole-program validity remain separate. -/
theorem evaluate_lower_in (e : ExprIn ctx t) (env : Env ctx) (run : P4bloIR.Run)
    (hf : FrameMatches env run.frame) :
    (P4bloIR.evaluate (lower e)).run run = (.ok (toValue (denoteIn env e)), run) := by
  apply evaluate_lower_with
  intro u ref
  simp [P4bloIR.evaluate, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind, hf ref]

/-- The original closed computation equality follows from the same open
theorem; there is no second closed evaluator or parallel source AST. -/
theorem evaluate_lower (e : Expr t) :
    P4bloIR.evaluate (lower e) = pure (toValue (denote e)) := by
  funext run
  have h := evaluate_lower_in e .nil run (by intro t ref; cases ref)
  simpa [P4bloIR.M.run, ExceptT.run, StateT.run, Id.run, denote,
    pure, ExceptT.pure, ExceptT.mk, StateT.pure] using h

theorem evaluate_lower_run (e : Expr t) (run : P4bloIR.Run) :
    (P4bloIR.evaluate (lower e)).run run = (.ok (toValue (denote e)), run) := by
  rw [evaluate_lower]
  rfl

def bitsIn {ctx : Context} (width value : Nat) (positive : 0 < width := by decide)
    (fits : value < 2 ^ width := by decide) : ExprIn ctx (.bits width) :=
  .bits positive ⟨value, fits⟩

def bits (width value : Nat) (positive : 0 < width := by decide)
    (fits : value < 2 ^ width := by decide) : Expr (.bits width) :=
  bitsIn width value positive fits

def bits? (width value : Nat) : Option (Expr (.bits width)) :=
  if hp : 0 < width then
    if hv : value < 2 ^ width then some (.bits hp ⟨value, hv⟩) else none
  else none

def bitsWith {Reads : Ty → Type} (width value : Nat) (positive : 0 < width := by decide)
    (fits : value < 2 ^ width := by decide) : ExprWith Reads (.bits width) :=
  .bits positive ⟨value, fits⟩

instance : Add (ExprWith Reads (.bits width)) := ⟨ExprWith.add⟩

scoped syntax "bits[" term "," term "]" : term
scoped macro_rules
  | `(bits[$width, $value]) => `(P4blo.Scalar.bitsWith $width $value)

scoped infix:50 " === " => ExprWith.eqBits

end P4blo.Scalar
