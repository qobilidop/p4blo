import P4bloIR.Progress

/-!
# Parser errors come only from parser runs

`progress` shows that a valid program's run ends in success or in a parser
error the program declares, whatever the block kind. This module refines
that by kind: a control or deparser run ends in success.

Parser errors are raised by `throwParse` alone, and only in parser
statements (`extract`, `advance`, `verify`), `lookahead`, and the parser's
own work items (`enterState` in `.state`, `select` and `reject` in
`.transition`). Outside a parser the typing rules forbid the first two, and
the machine never holds the third: `.states` needs a parser block, and
`.state` and `.transition` are only produced from it. So the invariant
`MachineOkNP` adds to `MachineOk` that no fault is pending and no parser
state or transition is on the stack.

The proof is by a second, weaker triple on each step: `NP` says an action
raises no parser error from any run, and `dispatch_np` shows it for every
work item outside a parser, from the typing `StackOk` already carries.
Lookahead-freedom (`lfE`, `lfL`, `lfA`) is the syntactic fact the typing
gives. Together with `dispatch_ok`, whose faults are all parser errors, a
step outside a parser cannot fail at all.

What is not established: termination, as for `progress`.
-/

namespace P4bloIR.Validity

open Execution
open ScalarTyping (run_bind run_pure run_map)

-- ---------------------------------------------------------------------------
-- Actions that raise no parser error
-- ---------------------------------------------------------------------------

/-- A fault that is not a parser error. -/
def NotParse (f : Fault) (_ : Run) : Prop := ∀ e, f ≠ .parse e

/-- An action that raises no parser error, from any run. -/
structure NP (m : M α) : Prop where
  run : ∀ r, Triple m r (fun _ _ => True) NotParse

namespace NP

theorem pure {a : α} : NP (Pure.pure a : M α) := ⟨fun _ => Triple.pure' trivial⟩

theorem bind {m : M α} {f : α → M β} (hm : NP m) (hf : ∀ a, NP (f a)) : NP (m >>= f) :=
  ⟨fun r => Triple.bind (hm.run r) (fun a r' _ => (hf a).run r')⟩

theorem map {m : M α} {f : α → β} (hm : NP m) : NP (f <$> m) :=
  ⟨fun r => Triple.map (hm.run r) (fun _ _ _ => trivial)⟩

theorem throwInterp {s : String} : NP (P4bloIR.throwInterp s : M α) :=
  ⟨fun _ => Triple.throw' (fun _ h => by cases h)⟩

theorem throw {s : String} : NP (MonadExcept.throw (Fault.interp s) : M α) :=
  ⟨fun _ => Triple.throw' (fun _ h => by cases h)⟩

theorem liftExcept {x : Except String α} : NP (P4bloIR.liftExcept x) := by
  cases x with
  | ok a => exact pure
  | error e => exact throwInterp

theorem get : NP (MonadState.get : M Run) := ⟨fun _ => Triple.get' trivial⟩
theorem getThe : NP (MonadStateOf.get : M Run) := ⟨fun _ => Triple.get' trivial⟩

theorem modify {g : Run → Run} : NP (_root_.modify g : M PUnit) :=
  ⟨fun _ => Triple.of_run rfl trivial⟩

theorem modifyGet {g : Run → α × Run} : NP (MonadState.modifyGet g : M α) :=
  ⟨fun _ => Triple.of_run rfl trivial⟩

theorem set {r' : Run} : NP (MonadStateOf.set r' : M PUnit) :=
  ⟨fun _ => Triple.of_run rfl trivial⟩

theorem ite {c : Prop} [Decidable c] {t e : M α} (ht : NP t) (he : NP e) :
    NP (if c then t else e) := by
  by_cases h : c <;> simp [h, ht, he]

theorem forIn {l : List α} {b : β} {f : α → β → M (ForInStep β)} (h : ∀ x ∈ l, ∀ b, NP (f x b)) :
    NP (ForIn.forIn l b f) := by
  induction l generalizing b with
  | nil => exact pure
  | cons x xs ih =>
    rw [List.forIn_cons]
    refine bind (h x (by simp) b) (fun s => ?_)
    cases s with
    | done b' => exact pure
    | yield b' => exact ih (fun y hy => h y (List.mem_cons_of_mem _ hy))

theorem mapM {l : List α} {f : α → M β} (h : ∀ x ∈ l, NP (f x)) : NP (l.mapM f) := by
  induction l with
  | nil => exact pure
  | cons x xs ih =>
    rw [List.mapM_cons]
    exact bind (h x (by simp)) (fun _ => bind (ih (fun y hy => h y (List.mem_cons_of_mem _ hy)))
      (fun _ => pure))

end NP

/-- Decompose an action into the pieces `NP` has rules for. -/
syntax "np" : tactic
macro_rules
  | `(tactic| np) => `(tactic| repeat' (first
      | assumption
      | exact NP.pure
      | exact NP.throwInterp
      | exact NP.throw
      | exact NP.liftExcept
      | exact NP.get
      | exact NP.getThe
      | exact NP.modify
      | exact NP.modifyGet
      | exact NP.set
      | apply NP.bind
      | apply NP.map
      | apply NP.ite
      | (intro _)
      | (split)))

theorem readVar_np : NP (readVar x) := by unfold readVar getFrame; np
theorem writeVar_np : NP (writeVar x v) := by unfold writeVar getFrame setFrame; np
theorem getIndex_np : NP getIndex := by unfold getIndex; np
theorem getFrame_np : NP getFrame := by unfold getFrame; np
theorem setFrame_np : NP (setFrame f) := by unfold setFrame; np
theorem fieldOf_np : NP (fieldOf v f) := by unfold fieldOf getIndex; np
theorem setField_np : NP (setField c f v) := by unfold setField getIndex; np
theorem elementOf_np : NP (elementOf h es i) := by unfold elementOf getIndex; np
theorem bitsBinary_np : NP (bitsBinary op x y) := by unfold bitsBinary; np
theorem castValue_np : NP (castValue t v) := by unfold castValue expectBits; np

-- ---------------------------------------------------------------------------
-- Lookahead-free expressions and lvalues
-- ---------------------------------------------------------------------------

/-- No `lookahead` anywhere in the expression. -/
def lfE : Expr → Bool
  | .literal _ | .var _ => true
  | .member b _ => lfE b
  | .index b i => lfE b && lfE i
  | .lastIndex s => lfE s
  | .unary _ e => lfE e
  | .binary _ l r => lfE l && lfE r
  | .cast _ e => lfE e
  | .slice e _ _ => lfE e
  | .isValid h => lfE h
  | .mux c a b => lfE c && lfE a && lfE b
  | .lookahead _ => false

/-- No `lookahead` in any index of the lvalue. -/
def lfL : LValue → Bool
  | .var _ => true
  | .member b _ => lfL b
  | .index b i => lfL b && lfE i
  | .next s => lfL s

/-- No `lookahead` in the argument. -/
def lfA : Arg → Bool
  | .expr e => lfE e
  | .lvalue lv => lfL lv

theorem evaluate_np : ∀ {e : Expr}, lfE e = true → NP (evaluate e)
  | .literal _, _ => by simp only [evaluate]; np
  | .var _, _ => by simp only [evaluate]; exact readVar_np
  | .member b _, h => by
    have := evaluate_np (e := b) (by simpa [lfE] using h)
    simp only [evaluate]; exact NP.bind this (fun _ => fieldOf_np)
  | .index b i, h => by
    simp only [lfE, Bool.and_eq_true] at h
    have hb := evaluate_np h.1
    have hi := evaluate_np h.2
    simp only [evaluate, expectStack, expectBits]
    np; exact elementOf_np
  | .lastIndex s, h => by
    have := evaluate_np (e := s) (by simpa [lfE] using h)
    simp only [evaluate, expectStack]; np
  | .unary _ e, h => by
    have := evaluate_np (e := e) (by simpa [lfE] using h)
    simp only [evaluate, expectBool, expectBits]; np
  | .binary _ l r, h => by
    simp only [lfE, Bool.and_eq_true] at h
    have hl := evaluate_np h.1
    have hr := evaluate_np h.2
    simp only [evaluate, expectBool, expectBits]
    np <;> exact bitsBinary_np
  | .cast _ e, h => by
    have := evaluate_np (e := e) (by simpa [lfE] using h)
    simp only [evaluate]; exact NP.bind this (fun _ => castValue_np)
  | .slice e _ _, h => by
    have := evaluate_np (e := e) (by simpa [lfE] using h)
    simp only [evaluate, expectBits]; np
  | .isValid e, h => by
    have := evaluate_np (e := e) (by simpa [lfE] using h)
    simp only [evaluate, expectHeader]; np
  | .mux c a b, h => by
    simp only [lfE, Bool.and_eq_true] at h
    have hc := evaluate_np h.1.1
    have ha := evaluate_np h.1.2
    have hb := evaluate_np h.2
    simp only [evaluate, expectBool]; np
  | .lookahead _, h => by simp [lfE] at h

theorem readLValue_np : ∀ {lv : LValue}, lfL lv = true → NP (readLValue lv)
  | .var _, _ => by simp only [readLValue]; exact readVar_np
  | .member b _, h => by
    have := readLValue_np (lv := b) (by simpa [lfL] using h)
    simp only [readLValue]; exact NP.bind this (fun _ => fieldOf_np)
  | .index b i, h => by
    simp only [lfL, Bool.and_eq_true] at h
    have hb := readLValue_np h.1
    have hi := evaluate_np h.2
    simp only [readLValue, expectStack, expectBits]
    np; exact elementOf_np
  | .next _, _ => by simp only [readLValue]; np

theorem writeLValue_np : ∀ {lv : LValue}, lfL lv = true → ∀ v, NP (writeLValue lv v)
  | .var _, _, _ => by simp only [writeLValue]; exact writeVar_np
  | .member b _, h, _ => by
    have hb : lfL b = true := by simpa [lfL] using h
    have hr := readLValue_np hb
    have hw := writeLValue_np hb
    simp only [writeLValue]
    exact NP.bind hr (fun _ => NP.bind setField_np (fun _ => hw _))
  | .index b i, h, _ => by
    simp only [lfL, Bool.and_eq_true] at h
    have hr := readLValue_np h.1
    have hw := writeLValue_np h.1
    have hi := evaluate_np h.2
    simp only [writeLValue, expectStack, expectBits, expectHeader]
    np
    exact hw _
  | .next _, _, _ => by simp only [writeLValue]; np

/-- `resolveLValue` raises no parser error and leaves a lookahead-free
lvalue. -/
theorem resolveLValue_lf : ∀ {lv : LValue}, lfL lv = true →
    ∀ r, Triple (resolveLValue lv) r (fun lv' _ => lfL lv' = true) NotParse
  | .var _, _, _ => by simp only [resolveLValue]; exact Triple.pure' rfl
  | .member b _, h, r => by
    have hb := resolveLValue_lf (lv := b) (by simpa [lfL] using h)
    simp only [resolveLValue]
    exact Triple.bind (hb r) (fun _ _ h' => Triple.pure' (by simpa [lfL] using h'))
  | .index b i, h, r => by
    simp only [lfL, Bool.and_eq_true] at h
    have hb := resolveLValue_lf h.1
    have hi := evaluate_np h.2
    simp only [resolveLValue, expectBits]
    refine Triple.bind (hb r) (fun _ r1 h1 => Triple.bind (hi.run r1) (fun _ r2 _ =>
      Triple.bind (NP.liftExcept.run r2) (fun _ _ _ => Triple.pure' ?_)))
    simp [lfL, lfE, h1]
  | .next _, h, _ => by simp only [resolveLValue]; exact Triple.pure' h

-- ---------------------------------------------------------------------------
-- Typing outside a parser rules out lookahead
-- ---------------------------------------------------------------------------

theorem ExprTyped.lf (h : ExprTyped c e t) (hk : c.kind ≠ .parser) : lfE e = true := by
  induction h with
  | lookahead hp => exact absurd hp hk
  | _ => simp_all [lfE]

theorem LValueTyped.lf (h : LValueTyped c lv t) (hk : c.kind ≠ .parser) : lfL lv = true := by
  induction h with
  | var => rfl
  | member _ _ ih => exact ih
  | index _ hi ih => simp [lfL, ih, hi.lf hk]

theorem LvOk.lf (h : LvOk c lv t) (hk : c.kind ≠ .parser) : lfL lv = true := by
  induction h with
  | var => rfl
  | member _ _ ih => exact ih
  | index _ hi ih =>
    rcases hi with ⟨_, hi⟩ | ⟨_, _, rfl⟩
    · simp [lfL, ih, hi.lf hk]
    · simp [lfL, lfE, ih]

theorem ArgTyped.lf (h : ArgTyped c a q) (hk : c.kind ≠ .parser) : lfA a = true := by
  cases h with
  | input _ he => exact he.lf hk
  | output _ hl => exact hl.lf hk

theorem ArgsTyped.lf (h : ArgsTyped c as ps) (hk : c.kind ≠ .parser) : ∀ a ∈ as, lfA a = true := by
  induction h with
  | nil => simp
  | cons ha _ ih =>
    intro x hx
    rcases List.mem_cons.mp hx with rfl | hx
    · exact ha.lf hk
    · exact ih x hx

/-- What copy-back needs of its arguments: every one written through is a
lookahead-free lvalue. -/
def CopyLF (ps : List Param) (as : List Arg) : Prop :=
  ∀ q a, (q, a) ∈ ps.zip as → (q.direction == .out || q.direction == .inout) = true →
    ∀ lv, a = .lvalue lv → lfL lv = true

theorem CopyOk.lf (h : CopyOk c ps as) (hk : c.kind ≠ .parser) : CopyLF ps as := by
  intro q a hm hout lv hlv
  obtain ⟨lv', rfl, hl⟩ := h.mem q a hm (isOut_iff.mpr hout)
  cases hlv
  exact hl.lf hk

-- ---------------------------------------------------------------------------
-- Calls
-- ---------------------------------------------------------------------------

theorem copyIn_lf (ha : lfA a = true) :
    ∀ r, Triple (copyIn q a) r (fun p _ => lfA p.2 = true) NotParse := by
  intro r
  unfold copyIn resolveArg argumentValue
  refine Triple.bind (P := fun a' _ => lfA a' = true) ?_ (fun a' r1 h1 => ?_)
  · split
    · split
      · rename_i lv
        exact Triple.bind (resolveLValue_lf ha r) (fun _ _ h => Triple.pure' h)
      · exact Triple.pure' ha
    · exact Triple.pure' ha
  · refine Triple.bind (P := fun _ _ => True) ?_ (fun _ _ _ => Triple.pure' h1)
    split
    · exact (NP.bind getIndex_np (fun _ => NP.liftExcept)).run r1
    · split
      · exact (evaluate_np (by simpa [lfA] using h1)).run r1
      · exact (readLValue_np (by simpa [lfA] using h1)).run r1

theorem copyBack_np (h : CopyLF ps as) : NP (copyBack ps as vals) := by
  unfold copyBack
  refine NP.bind (NP.forIn fun x hx b => ?_) (fun _ => NP.pure)
  obtain ⟨q, a⟩ := x
  simp only
  split
  · rename_i hout
    split
    · rename_i lv
      split
      · exact NP.bind (writeLValue_np (h q _ hx hout lv rfl) _) (fun _ => NP.pure)
      · np
    · np
  · np

theorem Forall2.mem_right {R : α → β → Prop} (h : Forall2 R as bs) :
    ∀ y ∈ bs, ∃ x ∈ as, R x y := by
  induction h with
  | nil => simp
  | cons hr _ ih =>
    intro y hy
    rcases List.mem_cons.mp hy with rfl | hy
    · exact ⟨_, by simp, hr⟩
    · obtain ⟨x, hx, h⟩ := ih y hy
      exact ⟨x, List.mem_cons_of_mem _ hx, h⟩

theorem Triple.and {m : M α} {Q1 Q2 : α → Run → Prop} {E1 E2 : Fault → Run → Prop}
    (h1 : Triple m r Q1 E1) (h2 : Triple m r Q2 E2) :
    Triple m r (fun a r' => Q1 a r' ∧ Q2 a r') (fun f r' => E1 f r' ∧ E2 f r') := by
  unfold Triple at *
  revert h1 h2
  cases m.run r with
  | mk res r' => cases res <;> simp_all

theorem callExtern_np {G : Global} {c : Ctx} {r : Run} (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hkind : G.kind ≠ .parser)
    (hi : c.index.externInstances[inst]? = some i) (het : c.index.externTypes[i.externType]? = some et)
    (hm : et.methods.find? (·.name == m) = some meth) (hargs : ArgsTyped c args meth.params)
    (hres : ResultTyped c meth.returns result) :
    Triple (callExtern inst m args result) r (fun _ _ => True) NotParse := by
  have hk : c.kind ≠ .parser := by rw [hc.kind]; exact hkind
  have hlen := hargs.length
  have hlf := hargs.lf hk
  rw [hc.index] at hi het
  unfold callExtern
  refine Triple.bind (P := fun res r' => r' = r ∧ ∀ lv, res = some lv → lfL lv = true) ?_ ?_
  · generalize meth.returns = mr at hres
    cases hres with
    | none => exact Triple.pure' ⟨rfl, by simp⟩
    | some hl =>
      simp only [Option.mapM]
      have hl' := hl.lvOk
      refine Triple.bind (Triple.mono (Triple.and (resolveLValue_ok hc hf hr hl')
        (resolveLValue_lf (hl'.lf hk) r)) (fun _ _ h => h) (fun _ _ h => h.2)) ?_
      rintro lv' r' ⟨⟨rfl, _⟩, hlf2⟩
      exact Triple.pure' ⟨rfl, fun x hx => by cases hx; exact hlf2⟩
  rintro res r' ⟨rfl, hresLF⟩
  refine Triple.bind (Triple.getIndex' (Q := fun a _ => a = G.idx) hr.index) ?_
  rintro _ _ rfl
  simp only [hi, het, hm]
  have hne : (args.length != meth.params.length) = false := by simp [hlen]
  simp only [hne, Bool.false_eq_true, ↓reduceIte]
  refine Triple.bind (Triple.mapM' (l := meth.params.zip args)
    (fun (_ : Param × Arg) (y : Value × Arg) => lfA y.2 = true) (fun _ => True) trivial ?_)
    (fun copied r4 hc4 => ?_)
  · rintro ⟨p, a⟩ hx r' _
    exact Triple.mono (copyIn_lf (hlf a (List.of_mem_zip hx).2) r') (fun _ _ h => ⟨h, trivial⟩)
      (fun _ _ h => h)
  obtain ⟨hcop, -⟩ := hc4
  have hsnd : ∀ a ∈ copied.map Prod.snd, lfA a = true := by
    intro a ha
    obtain ⟨y, hy, rfl⟩ := List.mem_map.mp ha
    obtain ⟨_, _, h⟩ := hcop.mem_right y hy
    exact h
  have hwritten : ∀ a ∈ (meth.params.zip (copied.map Prod.snd)).filterMap (fun x => match x with
      | (p, a) => if (p.direction == .out || p.direction == .inout) = true then some a else none),
      lfA a = true := by
    intro a ha
    obtain ⟨⟨p, a'⟩, hm, he⟩ := List.mem_filterMap.mp ha
    simp only at he
    split at he
    · cases he; exact hsnd _ (List.of_mem_zip hm).2
    · cases he
  refine (NP.bind NP.getThe fun _ => NP.bind NP.liftExcept fun x => ?_).run r4
  obtain ⟨externs, res2⟩ := x
  simp only
  refine NP.bind NP.modify fun _ => ?_
  apply NP.ite
  all_goals (try refine NP.bind NP.throwInterp fun _ => ?_)
  all_goals
    refine NP.bind (NP.forIn fun x hx _ => ?_) fun _ => ?_
    · obtain ⟨a, v⟩ := x
      have ha := hwritten a (List.of_mem_zip hx).1
      simp only
      split
      · rename_i lv
        exact NP.bind (writeLValue_np (by simpa [lfA] using ha) _) (fun _ => NP.pure)
      · np
    · split
      · rename_i lv
        split
        · exact writeLValue_np (hresLF lv rfl) _
        · np
      · np

theorem setValidity_np (h : lfL lv = true) : NP (setValidity lv valid) := by
  unfold setValidity expectHeader
  exact NP.bind (readLValue_np h) fun _ => NP.bind NP.liftExcept fun _ => writeLValue_np h _

mutual
theorem emitValue_np : ∀ v : Value, NP (emitValue v)
  | .header _ _ _ => by
    simp only [emitValue]
    np
  | .struct _ fs => by simp only [emitValue]; exact emitList_np fs
  | .stack _ es _ => by simp only [emitValue]; exact emitList_np es
  | .bits _ => by simp only [emitValue]; np
  | .bool _ => by simp only [emitValue]; np
  | .enum _ _ => by simp only [emitValue]; np
  | .error _ => by simp only [emitValue]; np

theorem emitList_np : ∀ vs : List Value, NP (emitList vs)
  | [] => by simp only [emitList]; exact NP.pure
  | v :: vs => by simp only [emitList]; exact NP.bind (emitValue_np v) fun _ => emitList_np vs
end

-- ---------------------------------------------------------------------------
-- Work items
-- ---------------------------------------------------------------------------

/-- A work item that is not a parser state or transition. -/
def parserFree : Work → Bool
  | .states _ | .state _ _ | .transition _ _ => false
  | _ => true

/-- An action that raises no parser error and returns only values that
satisfy `Q`, from any run. -/
structure NPQ (m : M α) (Q : α → Prop) : Prop where
  run : ∀ r, Triple m r (fun a _ => Q a) NotParse

namespace NPQ

theorem pure {a : α} {Q : α → Prop} (h : Q a) : NPQ (Pure.pure a : M α) Q :=
  ⟨fun _ => Triple.pure' h⟩

theorem bind {m : M α} {f : α → M β} {Q : β → Prop} (hm : NP m) (hf : ∀ a, NPQ (f a) Q) :
    NPQ (m >>= f) Q :=
  ⟨fun r => Triple.bind (hm.run r) (fun a r' _ => (hf a).run r')⟩

theorem throwInterp {s : String} {Q : α → Prop} : NPQ (P4bloIR.throwInterp s : M α) Q :=
  ⟨fun _ => Triple.throw' (fun _ h => by cases h)⟩

theorem ite {c : Prop} [Decidable c] {t e : M α} {Q : α → Prop} (ht : NPQ t Q) (he : NPQ e Q) :
    NPQ (if c then t else e) Q := by
  by_cases h : c <;> simp [h, ht, he]

end NPQ

/-- `np` for actions that return work items. -/
syntax "npq" : tactic
macro_rules
  | `(tactic| npq) => `(tactic| repeat' (first
      | assumption
      | (apply NPQ.pure; simp [parserFree]; done)
      | exact NPQ.throwInterp
      | apply NPQ.bind
      | apply NPQ.ite
      | exact NP.pure
      | exact NP.throwInterp
      | exact NP.throw
      | exact NP.liftExcept
      | exact NP.get
      | exact NP.getThe
      | exact NP.modify
      | exact NP.modifyGet
      | exact NP.set
      | apply NP.bind
      | apply NP.map
      | apply NP.ite
      | (intro _)
      | (split)))

theorem requireEntries_np : NP requireEntries := by
  unfold requireEntries currentBlock getFrame; np

theorem copyIn_np (ha : lfA a = true) : NP (copyIn q a) :=
  ⟨fun r => Triple.mono (copyIn_lf ha r) (fun _ _ _ => trivial) (fun _ _ h => h)⟩

attribute [local irreducible] copyBack in
/-- Outside a parser, a typed work item that is not a parser state or
transition raises no parser error and pushes none.

Premises: the step's context, frame and run are well formed, the run is not
a parser's, and the item heads a typed stack.

It does not establish that the item succeeds; `dispatch_ok` gives that its
faults are parser errors, and the two together rule out every fault. -/
theorem dispatch_np {G : Global} {c : Ctx} {r : Run} (hc : CtxOk G c) (hf : FrameOk c r.frame)
    (hr : RunOk G r) (hkind : G.kind ≠ .parser) (hs : StackOk G c (w :: rest))
    (hw : parserFree w = true) :
    Triple (dispatch w) r (fun next _ => ∀ x ∈ next, parserFree x = true) NotParse := by
  have hk : c.kind ≠ .parser := by rw [hc.kind]; exact hkind
  cases w with
  | statements body =>
    cases body <;> simp only [dispatch] <;> exact Triple.pure' (by simp [parserFree])
  | statement st =>
    simp only [StackOk] at hs
    obtain ⟨hst, -⟩ := hs
    cases hst with
    | assign hl he =>
      have h1 := evaluate_np (he.lf hk)
      have h2 := writeLValue_np (hl.lf hk)
      simp only [dispatch]
      refine (?_ : NPQ _ _).run r
      npq
      all_goals exact h2 _
    | conditional he _ _ =>
      have h1 := evaluate_np (he.lf hk)
      simp only [dispatch]
      refine (?_ : NPQ _ _).run r
      npq
    | apply => simp only [dispatch]; exact Triple.pure' (by simp [parserFree])
    | callAction => simp only [dispatch]; exact Triple.pure' (by simp [parserFree])
    | callBlock => simp only [dispatch]; exact Triple.pure' (by simp [parserFree])
    | callExtern hi het hm hargs _ hres =>
      simp only [dispatch]
      exact Triple.bind (callExtern_np hc hf hr hkind hi het hm hargs hres)
        (fun _ _ _ => Triple.pure' (by simp))
    | setValid hl =>
      simp only [dispatch]
      exact Triple.bind ((setValidity_np (hl.lf hk)).run r) (fun _ _ _ => Triple.pure' (by simp))
    | setInvalid hl =>
      simp only [dispatch]
      exact Triple.bind ((setValidity_np (hl.lf hk)).run r) (fun _ _ _ => Triple.pure' (by simp))
    | push hl _ =>
      have h1 := readLValue_np (hl.lf hk)
      have h2 := writeLValue_np (hl.lf hk)
      simp only [dispatch]
      refine (?_ : NPQ _ _).run r
      npq
      all_goals first | exact getIndex_np | exact h2 _
    | pop hl _ =>
      have h1 := readLValue_np (hl.lf hk)
      have h2 := writeLValue_np (hl.lf hk)
      simp only [dispatch]
      refine (?_ : NPQ _ _).run r
      npq
      all_goals first | exact getIndex_np | exact h2 _
    | extractNext hp => exact absurd hp hk
    | extract hp => exact absurd hp hk
    | advance hp => exact absurd hp hk
    | verify hp => exact absurd hp hk
    | emit _ he _ =>
      have h1 := evaluate_np (he.lf hk)
      simp only [dispatch]
      refine (?_ : NPQ _ _).run r
      npq
      all_goals exact emitValue_np _
  | table name hit =>
    simp only [StackOk] at hs
    obtain ⟨_, ha, ⟨t, ht⟩, _, _⟩ := hs
    have htt := hc.table ht
    rw [← hc.ofBlock ha] at htt
    obtain ⟨ws, hkeys, -⟩ := htt.widths
    have hre := requireEntries_np
    simp only [dispatch]
    refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
    rintro _ r0 ⟨hr0, rfl⟩
    subst hr0
    simp only [hf.scope, ht]
    refine (?_ : NPQ _ _).run r0
    refine NPQ.bind (NP.mapM fun k hk' => ?_) fun _ => ?_
    · obtain ⟨w, he⟩ := hkeys.mem k hk'
      have := evaluate_np (he.lf hk)
      unfold expectBits
      np
    · npq
      exact NPQ.pure (by
        intro x hx
        simp only [List.mem_append, List.mem_map, List.mem_singleton] at hx
        rcases hx with ⟨_, _, rfl⟩ | rfl <;> rfl)
  | tableAction call =>
    have h1 := getFrame_np
    simp only [dispatch]
    refine (?_ : NPQ _ _).run r
    npq
    all_goals exact setFrame_np
  | action name args =>
    simp only [StackOk] at hs
    obtain ⟨⟨_, _, hargs⟩, _⟩ := hs
    have hlf := hargs.lf hk
    have h1 := getFrame_np
    simp only [dispatch]
    refine (?_ : NPQ _ _).run r
    npq
    all_goals first
      | exact setFrame_np
      | exact NP.forIn fun x hx b => by
          obtain ⟨q, a⟩ := x
          have := copyIn_np (q := q) (hlf a (List.of_mem_zip hx).2)
          np
  | block name args =>
    simp only [StackOk] at hs
    obtain ⟨⟨_, _, _, hargs⟩, _⟩ := hs
    have hlf := hargs.lf hk
    have h1 := getFrame_np
    have h2 := getIndex_np
    simp only [dispatch]
    refine (?_ : NPQ _ _).run r
    npq
    all_goals first
      | exact setFrame_np
      | exact NP.forIn fun x hx b => by
          obtain ⟨q, a⟩ := x
          have := copyIn_np (q := q) (hlf a (List.of_mem_zip hx).2)
          np
  | runBlock b =>
    simp only [StackOk] at hs
    obtain ⟨rfl, _, _⟩ := hs
    have : (c.scope.block.kind == .parser) = false := by
      simpa [hc.blockKind] using hkind
    simp only [dispatch, this, Bool.false_eq_true, ↓reduceIte]
    exact Triple.pure' (by simp [parserFree])
  | states => simp [parserFree] at hw
  | state => simp [parserFree] at hw
  | transition => simp [parserFree] at hw
  | writeHit target hit =>
    simp only [StackOk] at hs
    obtain ⟨ht, _⟩ := hs
    simp only [dispatch]
    cases target with
    | none => exact Triple.pure' (by simp)
    | some lv =>
      simp only
      exact Triple.bind ((writeLValue_np ((ht lv rfl).lf hk) _).run r)
        (fun _ _ _ => Triple.pure' (by simp))
  | actionReturn outer copy =>
    simp only [StackOk] at hs
    obtain ⟨_, c', _, hc', _, _, hcopy, _⟩ := hs
    have hk' : c'.kind ≠ .parser := by rw [hc'.kind]; exact hkind
    simp only [dispatch]
    refine (?_ : NPQ _ _).run r
    have h1 := getFrame_np
    npq
    all_goals first
      | exact setFrame_np
      | exact copyBack_np ((hcopy _ _ rfl).2.lf hk')
  | blockReturn caller params args =>
    simp only [StackOk] at hs
    obtain ⟨_, _, c', hc', _, hcopy, _⟩ := hs
    have hk' : c'.kind ≠ .parser := by rw [hc'.kind]; exact hkind
    simp only [dispatch]
    refine (?_ : NPQ _ _).run r
    have h1 := getFrame_np
    npq
    all_goals first
      | exact setFrame_np
      | exact copyBack_np (hcopy.lf hk')

-- ---------------------------------------------------------------------------
-- The machine outside a parser
-- ---------------------------------------------------------------------------

/-- The invariant of a control or deparser run: a well-formed machine that
carries no fault and has no parser state or transition on its stack. -/
structure MachineOkNP (G : Global) (m : Machine) : Prop where
  ok : MachineOk G m
  fault : m.fault = none
  free : ∀ x ∈ m.work, parserFree x = true

/-- One step of a well-formed control or deparser machine finishes with
success or yields another such machine.

Premises: `MachineOkNP G m` and a run that is not a parser's.

It does not establish that the machine finishes. -/
theorem progress_outside_parser {G : Global} {m : Machine} (hm : MachineOkNP G m)
    (hk : G.kind ≠ .parser) :
    match step m with
    | .inl (result, _) => result = .ok ()
    | .inr m' => MachineOkNP G m' := by
  obtain ⟨⟨hr, hmode⟩, hfault, hfree⟩ := hm
  obtain ⟨work, run, fault⟩ := m
  simp only at hfault hr hmode hfree
  subst hfault
  cases work with
  | nil => simp [step]
  | cons task rest =>
    obtain ⟨c, hc, hf, hs⟩ := hmode
    have hnp := dispatch_np hc hf hr hk hs (hfree task (by simp))
    have hp := progress (m := { work := task :: rest, run, fault := none }) ⟨hr, ⟨c, hc, hf, hs⟩⟩
    unfold Triple at hnp
    simp only [step, Option.isSome_none, Bool.false_and, Bool.false_eq_true, ↓reduceIte] at hp ⊢
    revert hp hnp
    cases (dispatch task).run run with
    | mk res run' =>
      cases res with
      | ok next =>
        intro hnp hp
        refine ⟨hp, rfl, fun x hx => ?_⟩
        rcases List.mem_append.mp hx with hx | hx
        · exact hnp x hx
        · exact hfree x (List.mem_cons_of_mem _ hx)
      | error f =>
        intro hnp hp
        obtain ⟨_, ⟨e, rfl, _⟩, _⟩ := hp
        exact absurd rfl (hnp e)

/-- Every machine reachable from a well-formed control or deparser machine
is again one.

Premises: a trace of `step` and `MachineOkNP` at its start, outside a
parser. -/
theorem Steps.machineOkNP {G : Global} {m m' : Machine} (h : Steps m m') (hm : MachineOkNP G m)
    (hk : G.kind ≠ .parser) : MachineOkNP G m' := by
  induction h with
  | refl => exact hm
  | next hstep _ ih =>
    have := progress_outside_parser hm hk
    rw [hstep] at this
    exact ih this

/-- A finite run of a well-formed control or deparser machine ends in
success.

Premises: a finite trace and `MachineOkNP` at its start, outside a parser.

It does not establish that the trace exists; that is termination. -/
theorem finishes_outside_parser {G : Global} {m : Machine} {o : Outcome} (h : Finishes m o)
    (hm : MachineOkNP G m) (hk : G.kind ≠ .parser) : o.1 = .ok () := by
  induction h with
  | done hstep =>
    have := progress_outside_parser hm hk
    rw [hstep] at this
    exact this
  | next hstep _ ih =>
    have := progress_outside_parser hm hk
    rw [hstep] at this
    exact ih this

/-- `ResultOk` refined by block kind: success, or a declared parser error
of a parser run. -/
def ResultOkKind (G : Global) (result : Except Fault Unit) : Prop :=
  ResultOk G result ∧ (G.kind ≠ .parser → result = .ok ())

/-- A finite run of a valid program ends in success or in a declared
parser error, and in the error only when the run is a parser's.

Premises: a finite trace from a `MachineOk` machine with no pending fault
and no parser state or transition on its stack, as every machine an entry
point starts is (`initial_ok`).

It does not establish that the trace exists; that is termination. -/
theorem finishes_kind {G : Global} {m : Machine} {o : Outcome} (h : Finishes m o)
    (hm : MachineOk G m) (hfault : m.fault = none) (hfree : ∀ x ∈ m.work, parserFree x = true) :
    ResultOkKind G o.1 :=
  ⟨finishes_documented h hm, fun hk => finishes_outside_parser h ⟨hm, hfault, hfree⟩ hk⟩

/-- A parser error can only end a parser run.

Premises: those of `finishes_kind`, and a run that ends in a parser error.

It does not establish anything about which parser errors occur. -/
theorem parse_error_is_parser {G : Global} {m : Machine} {o : Outcome} (h : Finishes m o)
    (hm : MachineOk G m) (hfault : m.fault = none) (hfree : ∀ x ∈ m.work, parserFree x = true)
    (he : o.1 = .error (.parse e)) : G.kind = .parser := by
  cases hk : G.kind with
  | parser => rfl
  | _ =>
    rw [(finishes_kind h hm hfault hfree).2 (by rw [hk]; simp)] at he
    cases he

end P4bloIR.Validity
