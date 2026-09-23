import P4blo.Scalar
import P4bloIR.ScalarStatements

/-! One finite command language, parameterized only at typed reads/writes.
Source meaning never calls the IR interpreter. The generic operational
proof is a composition lemma; concrete public APIs discharge its leaf laws. -/

namespace P4blo.Scalar

inductive CmdWith (Reads Places : Ty → Type)
  | done
  | write {t : Ty} (place : Places t) (value : ExprWith Reads t) (next : CmdWith Reads Places)
  | branch (condition : ExprWith Reads .boolean) (yes no next : CmdWith Reads Places)

namespace CmdWith

variable {Reads Places : Ty → Type} {Source : Type}

def assign (place : Places t) (value : ExprWith Reads t) : CmdWith Reads Places :=
  .write place value .done

def ite (condition : ExprWith Reads .boolean) (yes no : CmdWith Reads Places) : CmdWith Reads Places :=
  .branch condition yes no .done

def seq : CmdWith Reads Places → CmdWith Reads Places → CmdWith Reads Places
  | .done, second => second
  | .write place value next, second => .write place value (next.seq second)
  | .branch condition yes no next, second => .branch condition yes no (next.seq second)

def denoteWith (read : Source → {t : Ty} → Reads t → Meaning t)
    (write : Source → {t : Ty} → Places t → Meaning t → Source)
    (cmd : CmdWith Reads Places) (store : Source) : Source :=
  match cmd with
  | .done => store
  | .write place value next =>
    next.denoteWith read write (write store place (Scalar.denoteWith (read store) value))
  | .branch condition yes no next =>
    next.denoteWith read write
      (if Scalar.denoteWith (read store) condition then
        yes.denoteWith read write store else no.denoteWith read write store)

def lowerWith (read : {t : Ty} → Reads t → P4bloIR.Expr)
    (place : {t : Ty} → Places t → P4bloIR.LValue) : CmdWith Reads Places → List P4bloIR.Stmt
  | .done => []
  | .write target value next =>
    .assign (place target) (Scalar.lowerWith read value) :: next.lowerWith read place
  | .branch condition yes no next =>
    .conditional (Scalar.lowerWith read condition) (yes.lowerWith read place)
      (no.lowerWith read place) :: next.lowerWith read place

def targetsWith (root : {t : Ty} → Places t → String) : CmdWith Reads Places → List String
  | .done => []
  | .write place _ next => root place :: next.targetsWith root
  | .branch _ yes no next => yes.targetsWith root ++ no.targetsWith root ++ next.targetsWith root

theorem denoteWith_seq (read : Source → {t : Ty} → Reads t → Meaning t)
    (write : Source → {t : Ty} → Places t → Meaning t → Source)
    (first second : CmdWith Reads Places) (store : Source) :
    (first.seq second).denoteWith read write store =
      second.denoteWith read write (first.denoteWith read write store) := by
  induction first generalizing store with
  | done => rfl
  | write place value next ih => exact ih _
  | branch condition yes no next _ _ ih => exact ih _

theorem lowerWith_seq (read : {t : Ty} → Reads t → P4bloIR.Expr)
    (place : {t : Ty} → Places t → P4bloIR.LValue) (first second : CmdWith Reads Places) :
    (first.seq second).lowerWith read place = first.lowerWith read place ++ second.lowerWith read place := by
  induction first with
  | done => rfl
  | write target value next ih => simp [seq, lowerWith, ih]
  | branch condition yes no next _ _ ih => simp [seq, lowerWith, ih]

open P4bloIR.ScalarStatements (BlockFrame ChangesOnlyVars PreservesOutside)
open P4bloIR.Execution (Steps)

/-- Exact finite execution through the existing machine. Assumptions concern
only individual reads/writes at related states, never whole commands. -/
theorem steps_with (cmd : CmdWith Reads Places)
    (read : Source → {t : Ty} → Reads t → Meaning t)
    (write : Source → {t : Ty} → Places t → Meaning t → Source)
    (lowerRead : {t : Ty} → Reads t → P4bloIR.Expr)
    (lowerPlace : {t : Ty} → Places t → P4bloIR.LValue)
    (root : {t : Ty} → Places t → String)
    (Matches : Source → P4bloIR.Run → Prop)
    (read_ok : ∀ store run, Matches store run → ∀ {t} (ref : Reads t),
      (P4bloIR.evaluate (lowerRead ref)).run run = (.ok (toValue (read store ref)), run))
    (write_ok : ∀ {t} (place : Places t) store (value : Meaning t) run,
      Matches store run → BlockFrame run.frame → ∃ final,
        (P4bloIR.writeLValue (lowerPlace place) (toValue value)).run run = (.ok (), final) ∧
        Matches (write store place value) final ∧ ChangesOnlyVars run final ∧
        PreservesOutside [root place] run final)
    (store : Source) (initial : P4bloIR.Run) (continuation : List P4bloIR.Execution.Work)
    (hm : Matches store initial) (hb : BlockFrame initial.frame) :
    ∃ final, Steps { work := .statements (cmd.lowerWith lowerRead lowerPlace) :: continuation, run := initial }
        { work := continuation, run := final } ∧
      Matches (cmd.denoteWith read write store) final ∧ ChangesOnlyVars initial final ∧
      PreservesOutside (cmd.targetsWith root) initial final := by
  induction cmd generalizing store initial continuation with
  | done =>
    refine ⟨initial, .next rfl .refl, hm, .refl _, ?_⟩
    intro name _
    rfl
  | write place value next ih =>
    let result := Scalar.denoteWith (read store) value
    obtain ⟨middle, hwrite, hmiddle, hchange, hwriteOutside⟩ := write_ok place store result initial hm hb
    obtain ⟨final, tail, hfinal, hfields, houtside⟩ :=
      ih (write store place result) middle continuation hmiddle (hchange.blockFrame hb)
    have dispatch : (P4bloIR.Execution.dispatch
        (.statement (.assign (lowerPlace place) (Scalar.lowerWith lowerRead value)))).run initial =
        (.ok [], middle) := by
      simp [P4bloIR.Execution.dispatch, P4bloIR.ScalarTyping.run_bind,
        P4bloIR.ScalarTyping.run_map,
        evaluate_lower_with value (read store) lowerRead initial (read_ok store initial hm),
        hwrite, result]
    refine ⟨final, .next rfl (.next ?_ tail), hfinal, hchange.trans hfields, ?_⟩
    · simp [P4bloIR.Execution.step, dispatch]
    · intro name hname
      have hn : name ≠ root place ∧ name ∉ next.targetsWith root := by
        simpa [targetsWith] using hname
      rw [houtside name hn.2]
      exact hwriteOutside name (by simpa using hn.1)
  | branch condition yes no next hy hn ht =>
    let chosen := if Scalar.denoteWith (read store) condition then yes else no
    have hc : ∃ middle,
        Steps { work := .statements (chosen.lowerWith lowerRead lowerPlace) ::
            .statements (next.lowerWith lowerRead lowerPlace) :: continuation, run := initial }
          { work := .statements (next.lowerWith lowerRead lowerPlace) :: continuation, run := middle } ∧
        Matches (chosen.denoteWith read write store) middle ∧ ChangesOnlyVars initial middle ∧
        PreservesOutside (chosen.targetsWith root) initial middle := by
      cases hcondition : Scalar.denoteWith (read store) condition
      · simpa [chosen, hcondition] using hn store initial
          (.statements (next.lowerWith lowerRead lowerPlace) :: continuation) hm hb
      · simpa [chosen, hcondition] using hy store initial
          (.statements (next.lowerWith lowerRead lowerPlace) :: continuation) hm hb
    obtain ⟨middle, branchTrace, hmiddle, hchange, hbranchOutside⟩ := hc
    obtain ⟨final, tail, hfinal, hfields, houtside⟩ :=
      ht (chosen.denoteWith read write store) middle continuation hmiddle (hchange.blockFrame hb)
    have dispatch : (P4bloIR.Execution.dispatch (.statement (.conditional
        (Scalar.lowerWith lowerRead condition) (yes.lowerWith lowerRead lowerPlace)
        (no.lowerWith lowerRead lowerPlace)))).run initial =
        (.ok [.statements (chosen.lowerWith lowerRead lowerPlace)], initial) := by
      have hbool (b : Bool) : P4bloIR.expectBool (.bool b) = pure b := rfl
      cases hcondition : Scalar.denoteWith (read store) condition <;>
        simp [P4bloIR.Execution.dispatch, P4bloIR.ScalarTyping.run_bind,
          evaluate_lower_with condition (read store) lowerRead initial (read_ok store initial hm),
          toValue, hbool, chosen, hcondition]
    refine ⟨final, .next rfl (.next ?_ (branchTrace.trans tail)), ?_, hchange.trans hfields, ?_⟩
    · simp [P4bloIR.Execution.step, dispatch]
    · cases hcondition : Scalar.denoteWith (read store) condition <;>
        simpa [denoteWith, chosen, hcondition] using hfinal
    · intro name hname
      have hnames : name ∉ yes.targetsWith root ∧ name ∉ no.targetsWith root ∧
          name ∉ next.targetsWith root := by simpa [targetsWith] using hname
      rw [houtside name hnames.2.2]
      apply hbranchOutside
      cases hcondition : Scalar.denoteWith (read store) condition <;> simp_all [chosen]

end CmdWith
end P4blo.Scalar
