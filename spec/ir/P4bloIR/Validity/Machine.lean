import P4bloIR.Validity.EvalLaws

/-!
# Well-formed machines

The invariant of `Execution.step`. A machine that is not unwinding a fault
runs in a context (`CtxOk`) whose frame is well formed (`FrameOk`), and
its continuation stack is typed from that context on (`StackOk`): each
pending item is typed in the context that will be current when it runs,
which changes only at an action's or a block's return, where the item
itself carries what the context returns to. A machine that is unwinding
carries a parser error of the program, and only the block returns on its
stack are typed (`UnwindOk`), since unwinding skips everything else.
-/

namespace P4bloIR.Validity

open Execution

/-- The arguments copy-back writes through: every `out` or `inout`
argument, resolved at copy-in, is an lvalue of the caller of the
parameter's type. -/
inductive CopyOk (c : Ctx) : List Param → List Arg → Prop
  | nil : CopyOk c [] []
  | out : isOut q.direction = true → LvOk c lv q.type → CopyOk c qs as →
      CopyOk c (q :: qs) (.lvalue lv :: as)
  | skip : isOut q.direction = false → CopyOk c qs as → CopyOk c (q :: qs) (a :: as)

/-- A callee's scope declares each param at its type. -/
def ParamsIn (sc : BlockScope) (params : List Param) : Prop :=
  ∀ q ∈ params, ∃ d, sc.vars[q.name]? = some d ∧ d.type = q.type

mutual
/-- The continuation stack, typed from context `c` on. -/
def StackOk (G : Global) : Ctx → List Work → Prop
  | _, [] => True
  | c, .statements body :: rest => StmtsTyped c body ∧ StackOk G c rest
  | c, .statement s :: rest => StmtTyped c s ∧ StackOk G c rest
  | c, .table name hit :: rest =>
    c.kind = .control ∧ c.action = none ∧ (∃ t, c.scope.tables[name]? = some t) ∧
      (∀ lv, hit = some lv → LValueTyped c lv .boolean) ∧ StackOk G c rest
  | c, .writeHit target _ :: rest =>
    (∀ lv, target = some lv → LValueTyped c lv .boolean) ∧ StackOk G c rest
  | c, .tableAction call :: rest =>
    c.action = none ∧ (∃ act, c.scope.actions[call.action]? = some act ∧
      DataOk c.index call.args act.params) ∧ StackOk G c rest
  | c, .action name args :: rest =>
    (∃ act, c.scope.actions[name]? = some act ∧ ArgsTyped c args act.params) ∧ StackOk G c rest
  | c, .actionReturn outer copy :: rest =>
    ∃ a c', c.action = some a ∧ CtxOk G c' ∧ c'.scope = c.scope ∧
      LayerOk c'.index c'.action outer.actionVars ∧
      (∀ ps as, copy = some (ps, as) → ps = a.params ∧ CopyOk c' ps as) ∧ StackOk G c' rest
  | c, .block name args :: rest =>
    (∃ b, c.index.blocks[name]? = some b ∧ b.kind = c.kind ∧ ArgsTyped c args b.params) ∧
      StackOk G c rest
  | c, .runBlock b :: rest => c.scope.block = b ∧ c.action = none ∧ StackOk G c rest
  | c, .states b :: rest =>
    c.scope.block = b ∧ c.action = none ∧ b.kind = .parser ∧ StackOk G c rest
  | c, .state sc st :: rest =>
    c.scope = sc ∧ c.action = none ∧ (∃ n : String, sc.states[n]? = some st) ∧ StackOk G c rest
  | c, .transition sc tr :: rest =>
    c.scope = sc ∧ c.action = none ∧ TransitionTyped c tr ∧ StackOk G c rest
  | c, .blockReturn caller params args :: rest =>
    c.action = none ∧ ParamsIn c.scope params ∧
      ∃ c', CtxOk G c' ∧ FrameOk c' caller ∧ CopyOk c' params args ∧ StackOk G c' rest
end

/-- The continuation stack while a fault unwinds: only block returns run,
each typed as in `StackOk`. -/
def UnwindOk (G : Global) : BlockScope → List Work → Prop
  | _, [] => True
  | sc, .blockReturn caller params args :: rest =>
    ParamsIn sc params ∧
      ∃ c', CtxOk G c' ∧ FrameOk c' caller ∧ CopyOk c' params args ∧ UnwindOk G c'.scope rest
  | sc, _ :: rest => UnwindOk G sc rest

/-- A parser error the program declares. -/
def Documented (G : Global) (f : Fault) : Prop := ∃ e, f = .parse e ∧ e ∈ G.p.errors

/-- The invariant of the step machine. -/
structure MachineOk (G : Global) (m : Machine) : Prop where
  run : RunOk G m.run
  mode : match m.fault with
    | none => ∃ c, CtxOk G c ∧ FrameOk c m.run.frame ∧ StackOk G c m.work
    | some f => Documented G f ∧
        ∃ c, CtxOk G c ∧ FrameOk c m.run.frame ∧ UnwindOk G c.scope m.work

/-- A typed stack, once a fault starts unwinding it, is typed for
unwinding. -/
theorem StackOk.unwind : ∀ {c : Ctx} {w : List Work}, StackOk G c w → UnwindOk G c.scope w
  | _, [], _ => trivial
  | c, .statements _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2
  | c, .statement _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2
  | c, .table _ _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2.2.2.2
  | c, .writeHit _ _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2
  | c, .tableAction _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2.2
  | c, .action _ _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2
  | c, .actionReturn _ _ :: rest, h => by
    simp only [StackOk] at h
    obtain ⟨_, c', _, _, hsc, _, _, hr⟩ := h
    simp only [UnwindOk]
    rw [← hsc]
    exact StackOk.unwind hr
  | c, .block _ _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2
  | c, .runBlock _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2.2
  | c, .states _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2.2.2
  | c, .state _ _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2.2.2
  | c, .transition _ _ :: rest, h => by
    simp only [StackOk] at h; simp only [UnwindOk]; exact StackOk.unwind h.2.2.2
  | c, .blockReturn _ _ _ :: rest, h => by
    simp only [StackOk] at h
    obtain ⟨_, hp, c', hc', hf', hcopy, hr⟩ := h
    simp only [UnwindOk]
    exact ⟨hp, c', hc', hf', hcopy, StackOk.unwind hr⟩

end P4bloIR.Validity
