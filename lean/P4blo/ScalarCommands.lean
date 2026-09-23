import P4blo.Scalar
import P4blo.ScalarPlaces

namespace P4blo.Scalar

def Env.set {ctx : Context} {t : Ty} : Env ctx → Ref ctx t → Meaning t → Env ctx
  | .cons _ rest, .here, value => .cons value rest
  | .cons head rest, .there ref, value => .cons head (rest.set ref value)

theorem Env.get_set (env : Env ctx) (ref : Ref ctx t) (value : Meaning t) :
    (env.set ref value).get ref = value := by
  induction ref with
  | here => cases env; rfl
  | there ref ih => cases env; exact ih _ value

theorem Env.get_set_value (env : Env ctx) (ref : Ref ctx t) (value : Meaning t)
    (other : Ref ctx u) (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) :
    toValue ((env.set ref value).get other) =
      if other.name = ref.name then toValue value else toValue (env.get other) := by
  induction ref with
  | @here name t rest =>
    cases env with
    | cons head tail =>
      cases other with
      | here => simp [Env.set, Env.get]
      | there other =>
        have hn : other.name ≠ name := by
          intro h
          exact (List.nodup_cons.mp hw.1).1
            (h ▸ List.mem_map.mpr ⟨_, other.mem, rfl⟩)
        simp [Env.set, Env.get, Ref.name, hn]
  | @there rest t binding ref ih =>
    have hn : ref.name ≠ binding.1 := by
      intro h
      exact (List.nodup_cons.mp hw.1).1
        (h ▸ List.mem_map.mpr ⟨_, ref.mem, rfl⟩)
    cases env with
    | cons head tail =>
      cases other with
      | here => simp [Env.set, Env.get, Ref.name, Ne.symm hn]
      | there other =>
        simpa [Env.set, Env.get, Ref.name] using ih tail value other (context_tail hw)

theorem FrameMatches.set {env : Env ctx} (hf : FrameMatches env frame)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx)
    (hb : P4bloIR.ScalarStatements.BlockFrame frame) (ref : Ref ctx t) (value : Meaning t) :
    FrameMatches (env.set ref value)
      { frame with vars := frame.vars.insert ref.name (toValue value) } := by
  intro u other
  rw [Env.get_set_value env ref value other hw]
  have h := hf other
  simp only [P4bloIR.Frame.read?, hb.2, Option.bind_none] at h ⊢
  simp only [Std.HashMap.getElem?_insert]
  by_cases he : other.name = ref.name
  · simp [he]
  · simp [he, Ne.symm he, h]

variable {ctx : Context} {modes : Modes ctx}

/-- Structured command lists with explicit tails. Public assignment,
conditional and sequencing combinators below hide that representation;
lowering introduces no synthetic IR statement to implement sequencing. -/
inductive Cmd {ctx : Context} (modes : Modes ctx)
  | done
  | write {t : Ty} (place : Place modes t) (value : ExprIn ctx t) (next : Cmd modes)
  | branch (condition : ExprIn ctx .boolean) (yes no next : Cmd modes)

def Cmd.assign (place : Place modes t) (value : ExprIn ctx t) : Cmd modes :=
  .write place value .done

def Cmd.ite (condition : ExprIn ctx .boolean) (yes no : Cmd modes) : Cmd modes :=
  .branch condition yes no .done

def Cmd.seq : Cmd modes → Cmd modes → Cmd modes
  | .done, second => second
  | .write place value next, second => .write place value (next.seq second)
  | .branch condition yes no next, second => .branch condition yes no (next.seq second)

def Cmd.denote (cmd : Cmd modes) (env : Env ctx) : Env ctx :=
  match cmd with
  | .done => env
  | .write place value next => next.denote (env.set place.ref (denoteIn env value))
  | .branch condition yes no next =>
    next.denote (if denoteIn env condition then yes.denote env else no.denote env)

def Cmd.lower : Cmd modes → List P4bloIR.Stmt
  | .done => []
  | .write place value next => .assign (.var place.ref.name) (Scalar.lower value) :: next.lower
  | .branch condition yes no next =>
    .conditional (Scalar.lower condition) yes.lower no.lower :: next.lower

def Cmd.targets : Cmd modes → List String
  | .done => []
  | .write place _ next => place.ref.name :: next.targets
  | .branch _ yes no next => yes.targets ++ no.targets ++ next.targets

theorem Cmd.denote_seq (first second : Cmd modes) (env : Env ctx) :
    (first.seq second).denote env = second.denote (first.denote env) := by
  induction first generalizing env with
  | done => rfl
  | write place value next ih => exact ih _
  | branch condition yes no next _ _ ih => exact ih _

theorem Cmd.lower_seq (first second : Cmd modes) :
    (first.seq second).lower = first.lower ++ second.lower := by
  induction first with
  | done => rfl
  | write place value next ih => simp [Cmd.seq, Cmd.lower, ih]
  | branch condition yes no next _ _ ih => simp [Cmd.seq, Cmd.lower, ih]

theorem Cmd.lower_typed {modes : Modes ctx} (cmd : Cmd modes)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) (hd : modes.Agrees scope) :
    P4bloIR.ScalarStatements.BodyTyped ctx scope cmd.lower := by
  induction cmd with
  | done => exact .nil
  | write place value next ih =>
    exact .cons (.assign (place.canAssign hw hd) (lower_typed_in value hw)) ih
  | branch condition yes no next hy hn hnext =>
    exact .cons (.conditional (lower_typed_in condition hw) hy hn) hnext

open P4bloIR.ScalarStatements (BlockFrame ChangesOnlyVars PreservesOutside)
open P4bloIR.Execution (Steps)

/-- Finite execution of precisely this body, leaving an arbitrary continuation
unexecuted. The source result is exact, all unrelated Run fields are unchanged,
and every runtime name outside the possible target set keeps its value. -/
theorem Cmd.steps (cmd : Cmd modes) (env : Env ctx) (initial : P4bloIR.Run)
    (continuation : List P4bloIR.Execution.Work)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx)
    (hf : FrameMatches env initial.frame) (hb : BlockFrame initial.frame) :
    ∃ final, Steps { work := .statements cmd.lower :: continuation, run := initial }
        { work := continuation, run := final } ∧
      FrameMatches (cmd.denote env) final.frame ∧ ChangesOnlyVars initial final ∧
      PreservesOutside cmd.targets initial final := by
  induction cmd generalizing env initial continuation with
  | done =>
    refine ⟨initial, .next rfl .refl, hf, .refl _, ?_⟩
    intro name _
    rfl
  | write place value next ih =>
    let result := denoteIn env value
    let middle : P4bloIR.Run := { initial with frame := { initial.frame with
      vars := initial.frame.vars.insert place.ref.name (toValue result) } }
    have hm : FrameMatches (env.set place.ref result) middle.frame := hf.set hw hb place.ref result
    have hchange : ChangesOnlyVars initial middle := ⟨_, rfl⟩
    obtain ⟨final, tail, hfinal, hfields, houtside⟩ :=
      ih (env.set place.ref result) middle continuation hm (hchange.blockFrame hb)
    have dispatch : (P4bloIR.Execution.dispatch
        (.statement (.assign (.var place.ref.name) (Scalar.lower value)))).run initial =
        (.ok [], middle) := by
      simp [P4bloIR.Execution.dispatch, P4bloIR.ScalarTyping.run_bind,
        P4bloIR.ScalarTyping.run_map,
        evaluate_lower_in value env initial hf, P4bloIR.writeLValue,
        P4bloIR.ScalarStatements.writeVar_block initial hb (hf place.ref), middle, result]
    refine ⟨final, .next rfl (.next ?_ tail), hfinal, hchange.trans hfields, ?_⟩
    · simp [P4bloIR.Execution.step, dispatch]
    · intro name hname
      have hn : name ≠ place.ref.name ∧ name ∉ next.targets := by
        simpa [Cmd.targets] using hname
      rw [houtside name hn.2]
      simp [middle, Std.HashMap.getElem?_insert, Ne.symm hn.1]
  | branch condition yes no next hy hn ht =>
    let chosen := if denoteIn env condition then yes else no
    have hc : ∃ middle,
        Steps { work := .statements chosen.lower :: .statements next.lower :: continuation, run := initial }
          { work := .statements next.lower :: continuation, run := middle } ∧
        FrameMatches (chosen.denote env) middle.frame ∧ ChangesOnlyVars initial middle ∧
        PreservesOutside chosen.targets initial middle := by
      cases hcondition : denoteIn env condition
      · simpa [chosen, hcondition] using hn env initial (.statements next.lower :: continuation) hf hb
      · simpa [chosen, hcondition] using hy env initial (.statements next.lower :: continuation) hf hb
    obtain ⟨middle, branchTrace, hmiddle, hchange, hbranchOutside⟩ := hc
    obtain ⟨final, tail, hfinal, hfields, houtside⟩ :=
      ht (chosen.denote env) middle continuation hmiddle (hchange.blockFrame hb)
    have dispatch : (P4bloIR.Execution.dispatch (.statement (.conditional (Scalar.lower condition)
        yes.lower no.lower))).run initial = (.ok [.statements chosen.lower], initial) := by
      have hbool (b : Bool) : P4bloIR.expectBool (.bool b) = pure b := rfl
      cases hcondition : denoteIn env condition <;>
        simp [P4bloIR.Execution.dispatch, P4bloIR.ScalarTyping.run_bind,
          evaluate_lower_in condition env initial hf, toValue, hbool,
          chosen, hcondition]
    refine ⟨final, .next rfl (.next ?_ (branchTrace.trans tail)), ?_, hchange.trans hfields, ?_⟩
    · simp [P4bloIR.Execution.step, dispatch]
    · intro t ref
      cases hcondition : denoteIn env condition <;>
        simpa [Cmd.denote, chosen, hcondition] using hfinal ref
    · intro name hname
      have hnames : name ∉ yes.targets ∧ name ∉ no.targets ∧ name ∉ next.targets := by
        simpa [Cmd.targets] using hname
      rw [houtside name hnames.2.2]
      apply hbranchOutside
      cases hcondition : denoteIn env condition <;>
        simp_all [chosen]

/-- Actual reference execution, not an alternative source evaluator. The
declaration premise supplies statement typing; operational preservation uses
the runtime's own write behavior and exact source value correspondence. -/
theorem Cmd.execute_correct (cmd : Cmd modes) (env : Env ctx) (initial : P4bloIR.Run)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) (hd : modes.Agrees initial.frame.scope)
    (hf : FrameMatches env initial.frame) (hb : BlockFrame initial.frame) :
    P4bloIR.ScalarStatements.BodyTyped ctx initial.frame.scope cmd.lower ∧
    ∃ final, (P4bloIR.execute cmd.lower).run initial = (.ok (), final) ∧
      FrameMatches (cmd.denote env) final.frame ∧
      P4bloIR.ScalarTyping.FrameTyped ctx final.frame ∧ modes.Agrees final.frame.scope ∧
      ChangesOnlyVars initial final ∧ PreservesOutside cmd.targets initial final := by
  obtain ⟨final, trace, hm, hc, ho⟩ := cmd.steps env initial [] hw hf hb
  refine ⟨cmd.lower_typed hw hd, final, trace.execute, hm, hm.typed, ?_, hc, ho⟩
  rw [hc.scope]
  exact hd

end P4blo.Scalar
