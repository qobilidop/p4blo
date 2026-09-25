import P4bloIR.Validity.StmtLaws

/-!
# One step of the machine keeps it well formed

`dispatch_ok`: on a well-formed run, a typed work item either succeeds,
leaving a context in which the new frame is well formed and the new stack
typed (`StepQ`), or stops with a parser error of the program, leaving the
unwinding invariant (`StepE`). `blockReturn_unwind` is the same for the
one item that runs while a fault unwinds.
-/

namespace P4bloIR.Validity

open Std (HashMap)
open Execution
open ScalarTyping (run_bind run_pure run_map)

/-- After a successful step: some context holds the frame and types the
new stack. -/
def StepQ (G : Global) (rest next : List Work) (r' : Run) : Prop :=
  RunOk G r' ∧ ∃ c', CtxOk G c' ∧ FrameOk c' r'.frame ∧ StackOk G c' (next ++ rest)

/-- After a fault: a parser error of the program, and the rest of the stack
typed for unwinding. -/
def StepE (G : Global) (rest : List Work) (f : Fault) (r' : Run) : Prop :=
  Documented G f ∧ RunOk G r' ∧ ∃ c', CtxOk G c' ∧ FrameOk c' r'.frame ∧ UnwindOk G c'.scope rest

section
variable {G : Global} {c : Ctx} {r : Run}

theorem ErrQ.step (hc : CtxOk G c) (hrest : StackOk G c rest) (h : ErrQ G c f r') :
    StepE G rest f r' := ⟨h.1, h.2.1, c, hc, h.2.2, hrest.unwind⟩

theorem OkQ.step (hc : CtxOk G c) (hnext : StackOk G c (next ++ rest)) (h : OkQ G c r') :
    StepQ G rest next r' := ⟨h.1, c, hc, h.2, hnext⟩

/-- A step that stays in its context and pushes nothing. -/
theorem stay (hc : CtxOk G c) (hrest : StackOk G c rest)
    (h : Triple m r (fun _ r' => OkQ G c r') (ErrQ G c)) :
    Triple (m >>= fun _ => (pure [] : M (List Work))) r (StepQ G rest) (StepE G rest) :=
  Triple.bind (Triple.mono h (fun _ _ h => h) (fun _ _ h => h.step hc hrest))
    (fun _ _ h => Triple.pure' (h.step hc hrest))

/-- A context without an action is its block's. -/
theorem CtxOk.ofBlock (hc : CtxOk G c) (ha : c.action = none) :
    c = Ctx.ofBlock G.idx c.scope c.scope.block := by
  obtain ⟨index, scope, kind, action⟩ := c
  simp only at ha
  subst ha
  have h1 : index = G.idx := hc.index
  have h2 : kind = scope.block.kind := hc.kind.trans hc.blockKind.symm
  subst h1 h2
  rfl

theorem CtxOk.withAction_eq (hc : CtxOk G c) :
    { c with action := some a } = { Ctx.ofBlock G.idx c.scope c.scope.block with action := some a } := by
  obtain ⟨index, scope, kind, action⟩ := c
  have h1 : index = G.idx := hc.index
  have h2 : kind = scope.block.kind := hc.kind.trans hc.blockKind.symm
  subst h1 h2
  rfl

theorem dispatch_statement (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StmtTyped c s) (hrest : StackOk G c rest) :
    Triple (dispatch (.statement s)) r (StepQ G rest) (StepE G rest) := by
  have ev := fun {e t} (he : ExprTyped c e t) => Triple.evalErr hc hf hr he
  cases hs with
  | assign hl he =>
    simp only [dispatch]
    refine Triple.bind (Triple.mono (ev he) (fun _ _ h => h) (fun _ _ h => h.step hc hrest)) ?_
    rintro v r' ⟨rfl, hv⟩
    exact stay hc hrest (Triple.mono (writeLValue_ok hc hf hr hl.lvOk hv) (fun _ _ h => h.okQ hr)
      (fun _ _ h => Short.errQ hr hf h))
  | conditional he hy hn =>
    simp only [dispatch]
    refine Triple.bind (Triple.mono (ev he) (fun _ _ h => h) (fun _ _ h => h.step hc hrest)) ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bool b =>
      simp only [expectBool_bool, pure_bind]
      refine Triple.pure' (OkQ.step hc ?_ ⟨hr, hf⟩)
      cases b <;> exact ⟨by simpa using ‹StmtsTyped c _›, hrest⟩
    | _ => simp [ValueHas] at hv
  | apply hk ha ht hh =>
    exact Triple.pure' (OkQ.step hc ⟨hk, ha, ⟨_, ht⟩, hh, hrest⟩ ⟨hr, hf⟩)
  | callAction _ hact hargs _ =>
    exact Triple.pure' (OkQ.step hc ⟨⟨_, hact, hargs⟩, hrest⟩ ⟨hr, hf⟩)
  | callBlock _ hb hk hargs _ =>
    exact Triple.pure' (OkQ.step hc ⟨⟨_, hb, hk, hargs⟩, hrest⟩ ⟨hr, hf⟩)
  | callExtern hi het hm hargs _ hres =>
    simp only [dispatch]
    exact stay hc hrest (callExtern_ok hc hf hr hi het hm hargs hres)
  | setValid hl =>
    simp only [dispatch]
    exact stay hc hrest (setValidity_ok hc hf hr hl)
  | setInvalid hl =>
    simp only [dispatch]
    exact stay hc hrest (setValidity_ok hc hf hr hl)
  | push hl _ =>
    have hty := stack_header_tyOk (hc.lvTy hl.lvOk)
    simp only [dispatch]
    refine Triple.bind (Triple.mono (readLValue_ok hc hf hr hl.lvOk) (fun _ _ h => h)
      (fun _ _ h => (Short.errQ hr hf h).step hc hrest)) ?_
    rintro v r' ⟨rfl, hv⟩
    refine Triple.bind (Triple.getIndex' (Q := fun a r'' => r'' = _ ∧ a = G.idx) ⟨rfl, hr.index⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    obtain ⟨v', hv', hvt⟩ := pushFront_ok (n := ‹Nat›) G.laws hv hty
    refine Triple.bind (Triple.liftExcept' hv' (Q := fun a r'' => r'' = _ ∧ a = v') ⟨rfl, rfl⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    exact stay hc hrest (Triple.mono (writeLValue_ok hc hf hr hl.lvOk hvt) (fun _ _ h => h.okQ hr)
      (fun _ _ h => Short.errQ hr hf h))
  | pop hl _ =>
    have hty := stack_header_tyOk (hc.lvTy hl.lvOk)
    simp only [dispatch]
    refine Triple.bind (Triple.mono (readLValue_ok hc hf hr hl.lvOk) (fun _ _ h => h)
      (fun _ _ h => (Short.errQ hr hf h).step hc hrest)) ?_
    rintro v r' ⟨rfl, hv⟩
    refine Triple.bind (Triple.getIndex' (Q := fun a r'' => r'' = _ ∧ a = G.idx) ⟨rfl, hr.index⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    obtain ⟨v', hv', hvt⟩ := popFront_ok (n := ‹Nat›) G.laws hv hty
    refine Triple.bind (Triple.liftExcept' hv' (Q := fun a r'' => r'' = _ ∧ a = v') ⟨rfl, rfl⟩) ?_
    rintro _ _ ⟨rfl, rfl⟩
    exact stay hc hrest (Triple.mono (writeLValue_ok hc hf hr hl.lvOk hvt) (fun _ _ h => h.okQ hr)
      (fun _ _ h => Short.errQ hr hf h))
  | extractNext hk hl =>
    simp only [dispatch]
    exact stay hc hrest (extract_ok hc hf hr (.extractNext hk hl))
  | extract hk hnot hl =>
    simp only [dispatch]
    exact stay hc hrest (extract_ok hc hf hr (.extract hk hnot hl))
  | advance hk he =>
    simp only [dispatch]
    exact stay hc hrest (advance_ok hc hf hr (hc.kind ▸ hk) he)
  | verify _ he herr =>
    simp only [dispatch]
    exact stay hc hrest (verify_ok hc hf hr he herr)
  | emit hk he hem =>
    simp only [dispatch]
    refine Triple.bind (Triple.mono (ev he) (fun _ _ h => h) (fun _ _ h => h.step hc hrest)) ?_
    rintro v r' ⟨rfl, hv⟩
    refine stay hc hrest (Triple.mono (emitValue_ok (c := c) (hc.kind ▸ hk) _ (hc.index ▸ hem) hv hr)
      ?_ (fun _ _ h => h))
    rintro _ r'' ⟨hr'', hfr⟩
    exact ⟨hr'', hfr ▸ hf⟩

-- ---------------------------------------------------------------------------
-- Binding parameters
-- ---------------------------------------------------------------------------

/-- A map holding a typed value for exactly the named params. -/
def MapOk (idx : Index) (ps : List Param) (m : HashMap String Value) : Prop :=
  ∀ x, match ps.find? (·.name == x) with
    | some q => ∃ v, m[x]? = some v ∧ ValueHas idx v q.type
    | none => m[x]? = none

theorem MapOk.nil : MapOk idx [] ∅ := by intro x; simp

theorem MapOk.snoc (h : MapOk idx pre m) (hn : p.name ∉ pre.map Param.name)
    (hv : ValueHas idx v p.type) : MapOk idx (pre ++ [p]) (m.insert p.name v) := by
  intro x
  have hx := h x
  rw [List.find?_append]
  by_cases hpx : p.name = x
  · subst hpx
    have hnone : pre.find? (·.name == p.name) = none := by
      rw [List.find?_eq_none]
      intro q hq hqn
      exact hn (List.mem_map.mpr ⟨q, hq, by simpa using hqn⟩)
    simp [hnone, hv]
  · have hne : (p.name == x) = false := by simpa using hpx
    cases hf : pre.find? (·.name == x) with
    | some q =>
      rw [hf] at hx
      simpa [Std.HashMap.getElem?_insert, hpx] using hx
    | none =>
      rw [hf] at hx
      simp [hne, Std.HashMap.getElem?_insert, hx]

theorem MapOk.layer (h : MapOk idx a.params m) : LayerOk idx (some a) (some m) := ⟨m, rfl, h⟩

theorem find_of_nodup {ps : List Param} {q : Param} (hn : (ps.map Param.name).Nodup) (hq : q ∈ ps) :
    ps.find? (·.name == q.name) = some q := by
  induction ps with
  | nil => simp at hq
  | cons p ps ih =>
    simp only [List.map_cons, List.nodup_cons] at hn
    rcases List.mem_cons.mp hq with rfl | hq
    · simp
    · have hne : p.name ≠ q.name := fun h => hn.1 (h ▸ List.mem_map.mpr ⟨q, hq, rfl⟩)
      simp [hne, ih hn.2 hq]

theorem map_fst_zip_eq {ps : List Param} {as : List Arg} (h : ps.length = as.length) :
    (ps.zip as).map Prod.fst = ps := List.map_fst_zip (by omega)

theorem Forall2.append {R : α → β → Prop} (h1 : Forall2 R a b) (h2 : R x y) :
    Forall2 R (a ++ [x]) (b ++ [y]) := by
  induction h1 with
  | nil => exact .cons h2 .nil
  | cons h _ ih => exact .cons h ih

/-- Copy-in results aligned with the params give the copy-back arguments. -/
theorem copyOk_of {ps : List Param} {as : List Arg} {res : List Arg} (hlen : ps.length = as.length)
    (h : Forall2 (fun (x : Param × Arg) a' => ArgOk c x.1 a') (ps.zip as) res) : CopyOk c ps res := by
  induction ps generalizing as res with
  | nil => cases h; exact .nil
  | cons q qs ih =>
    cases as with
    | nil => simp at hlen
    | cons a as =>
      cases h with
      | cons hy hrest =>
        rename_i a' res
        by_cases hq : isOut q.direction = true
        · obtain ⟨lv, rfl, hl⟩ := hy hq
          exact .out hq hl (ih (by simpa using hlen) hrest)
        · exact .skip (by simpa using hq) (ih (by simpa using hlen) hrest)

/-- The action layer a table action gets: its params bound to its data. -/
theorem foldl_params (hn : (ps.map Param.name).Nodup) (hl : DataOk idx args ps) :
    MapOk idx ps ((ps.zip args).foldl (fun m x => match x with
      | (p, a) => m.insert p.name (literalValue a)) ∅) := by
  suffices h : ∀ pre m, MapOk idx pre m → ((pre ++ ps).map Param.name).Nodup →
      MapOk idx (pre ++ ps) ((ps.zip args).foldl (fun m x => match x with
        | (p, a) => m.insert p.name (literalValue a)) m) by
    simpa using h [] ∅ MapOk.nil (by simpa using hn)
  induction hl with
  | nil => intro pre m hm _; simpa using hm
  | @cons x q xs qs ha _ ih =>
    intro pre m hm hnd
    simp only [List.zip_cons_cons, List.foldl_cons]
    have hp : q.name ∉ pre.map Param.name := by
      intro hin
      simp only [List.map_append, List.map_cons] at hnd
      exact (List.nodup_append.mp hnd).2.2 _ hin _ (by simp) rfl
    have := ih (List.nodup_cons.mp (by simpa using hn)).2 (pre ++ [q]) _ (hm.snoc hp ha)
      (by simpa using hnd)
    simpa using this

-- ---------------------------------------------------------------------------
-- What a context's scope declares
-- ---------------------------------------------------------------------------

theorem CtxOk.table {n : String} {t : Table} (hc : CtxOk G c) (ht : c.scope.tables[n]? = some t) :
    TableTyped (Ctx.ofBlock G.idx c.scope c.scope.block) t :=
  hc.typed.tables t (hc.laws.tableOrigin n t ht).1

theorem CtxOk.action' {n : String} {a : Action} (hc : CtxOk G c) (ha : c.scope.actions[n]? = some a) :
    a ∈ c.scope.block.actions ∧ ActionTyped (Ctx.ofBlock G.idx c.scope c.scope.block) a :=
  ⟨(hc.laws.actionOrigin n a ha).1, hc.typed.actions a (hc.laws.actionOrigin n a ha).1⟩

theorem CtxOk.state {n : String} {st : State} (hc : CtxOk G c) (hs : c.scope.states[n]? = some st) :
    StateTyped (Ctx.ofBlock G.idx c.scope c.scope.block) st :=
  hc.typed.states st (hc.laws.stateOrigin n st hs).1

-- ---------------------------------------------------------------------------
-- Work items that stay in their context
-- ---------------------------------------------------------------------------

theorem dispatch_writeHit (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.writeHit target hit :: rest)) :
    Triple (dispatch (.writeHit target hit)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨ht, hrest⟩ := hs
  simp only [dispatch]
  cases target with
  | none => exact Triple.pure' (OkQ.step hc hrest ⟨hr, hf⟩)
  | some lv =>
    simp only
    exact stay hc hrest (Triple.mono (writeLValue_ok hc hf hr (ht lv rfl).lvOk (by simp))
      (fun _ _ h => h.okQ hr) (fun _ _ h => Short.errQ hr hf h))

theorem dispatch_runBlock (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.runBlock b :: rest)) :
    Triple (dispatch (.runBlock b)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨hb, ha, hrest⟩ := hs
  subst hb
  simp only [dispatch]
  refine Triple.pure' (OkQ.step hc ?_ ⟨hr, hf⟩)
  by_cases hk : c.scope.block.kind = .parser
  · simp only [hk, beq_self_eq_true, ↓reduceIte, List.cons_append, List.nil_append]
    exact ⟨rfl, ha, hk, hrest⟩
  · have : (c.scope.block.kind == .parser) = false := by simpa using hk
    simp only [this, Bool.false_eq_true, ↓reduceIte, List.cons_append, List.nil_append]
    refine ⟨?_, hrest⟩
    rw [hc.ofBlock ha]
    exact hc.typed.body

theorem dispatch_states (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.states b :: rest)) :
    Triple (dispatch (.states b)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨hb, ha, hk, hrest⟩ := hs
  subst hb
  have hshape := hc.typed.shape
  unfold ShapeOk at hshape
  rw [hk] at hshape
  obtain ⟨_, hstart, -⟩ := hshape
  obtain ⟨st, hst⟩ := Option.ne_none_iff_exists'.mp hstart
  simp only [dispatch]
  refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
  rintro _ r' ⟨rfl, rfl⟩
  simp only [hf.scope, hst]
  exact Triple.pure' (OkQ.step hc ⟨rfl, ha, ⟨_, hst⟩, hrest⟩ ⟨hr, hf⟩)

theorem dispatch_state (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.state sc st :: rest)) :
    Triple (dispatch (.state sc st)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨rfl, ha, ⟨n, hst⟩, hrest⟩ := hs
  have hk : G.kind = .parser := by
    have := hc.typed.shape
    have hmem := (hc.laws.stateOrigin n st hst).1
    unfold ShapeOk at this
    rw [← hc.blockKind]
    cases hkb : c.scope.block.kind <;> rw [hkb] at this <;> simp_all
  have htyped := hc.state hst
  rw [← hc.ofBlock ha] at htyped
  simp only [dispatch]
  refine Triple.bind (Triple.mono (enterState_ok (c := c) (st := st) hr hf hk) (fun _ _ h => h)
    (fun _ _ h => h.step hc hrest)) ?_
  rintro _ r' hok
  exact Triple.pure' (OkQ.step hc ⟨htyped.1, rfl, ha, htyped.2, hrest⟩ hok)

theorem dispatch_transition (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.transition sc tr :: rest)) :
    Triple (dispatch (.transition sc tr)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨rfl, ha, htr, hrest⟩ := hs
  have ht : Triple (transition tr) r (fun t r' => OkQ G c r' ∧ TargetOk c t) (ErrQ G c) := by
    cases htr with
    | direct ht => exact Triple.pure' ⟨⟨hr, hf⟩, ht⟩
    | select _ hk hcases => exact select_ok hc hf hr hk hcases
  simp only [dispatch]
  refine Triple.bind (Triple.mono ht (fun _ _ h => h) (fun _ _ h => h.step hc hrest)) ?_
  rintro t r' ⟨hok, htarget⟩
  cases t with
  | state n =>
    obtain ⟨st, hst⟩ := Option.ne_none_iff_exists'.mp htarget
    simp only [hst]
    exact Triple.pure' (OkQ.step hc ⟨rfl, ha, ⟨n, hst⟩, hrest⟩ hok)
  | accept => exact Triple.pure' (OkQ.step hc hrest hok)
  | reject =>
    exact Triple.throwParse' (ErrQ.step (f := .parse "NoError") hc hrest
      ⟨documented G (by simp [coreErrors]), hok⟩)

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

theorem KeysTyped.mem (h : KeysTyped c keys ws) : ∀ k ∈ keys, ∃ w, ExprTyped c k.expr (.bits w) := by
  induction h with
  | nil => simp
  | cons he _ ih =>
    intro k hk
    rcases List.mem_cons.mp hk with rfl | hk
    · exact ⟨_, he⟩
    · exact ih k hk

theorem Forall2.length {R : α → β → Prop} (h : Forall2 R a b) : a.length = b.length := by
  induction h with
  | nil => rfl
  | cons _ _ ih => simp [ih]

theorem requireEntries_run (h : r.entries = some e) : requireEntries.run r = (.ok e, r) := by
  simp [requireEntries, run_bind, h]

theorem dispatch_table (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.table name hit :: rest)) :
    Triple (dispatch (.table name hit)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨hk, ha, ⟨t, ht⟩, hh, hrest⟩ := hs
  have htt := hc.table ht
  rw [← hc.ofBlock ha] at htt
  obtain ⟨ws, hkeys, -⟩ := htt.widths
  obtain ⟨inst, hinst, hok⟩ := hr.entries (hc.kind ▸ hk)
  simp only [dispatch]
  refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
  rintro _ r0 ⟨rfl, rfl⟩
  simp only [hf.scope, ht]
  refine Triple.bind (Triple.mono (Triple.mapM' (fun _ _ => True) (fun r' => r' = r0) rfl ?_)
    (fun _ _ h => h) (fun _ _ h => (Short.errQ hr hf h).step hc hrest)) ?_
  · intro k hk' r' hr'
    subst hr'
    obtain ⟨w, he⟩ := hkeys.mem k hk'
    refine Triple.bind (evaluate_ok hc hf hr he) ?_
    rintro v r' ⟨rfl, hv⟩
    cases v with
    | bits b => exact Triple.pure' ⟨trivial, rfl⟩
    | _ => simp [ValueHas] at hv
  rintro keys r' ⟨hlen, rfl⟩
  obtain ⟨m, hm, hacts⟩ := hok _ c.scope name t keys hc.scope ht hlen.length.symm
  refine Triple.bind (Triple.of_run (requireEntries_run hinst) (Q := fun a r'' => r'' = _ ∧ a = inst)
    ⟨rfl, rfl⟩) ?_
  rintro e0 _ ⟨rfl, he0⟩
  subst he0
  simp only [Frame.block, hf.scope]
  refine Triple.bind (Triple.liftExcept' hm (Q := fun a r'' => r'' = _ ∧ a = m) ⟨rfl, rfl⟩) ?_
  rintro m0 _ ⟨rfl, hm0⟩
  subst hm0
  refine Triple.pure' (OkQ.step hc ?_ ⟨hr, hf⟩)
  cases hma : m0.action with
  | none => exact ⟨hh, hrest⟩
  | some call =>
    obtain ⟨act, hact, hargs⟩ := hacts call hma
    exact ⟨ha, ⟨act, hact, hc.index ▸ hargs⟩, hh, hrest⟩

-- ---------------------------------------------------------------------------
-- Actions
-- ---------------------------------------------------------------------------

theorem dispatch_tableAction (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.tableAction call :: rest)) :
    Triple (dispatch (.tableAction call)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨ha, ⟨act, hact, hargs⟩, hrest⟩ := hs
  obtain ⟨hmem, htyped⟩ := hc.action' hact
  have hnodup := (hc.laws.actionParams act hmem).1
  simp only [dispatch]
  refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
  rintro _ r0 ⟨rfl, rfl⟩
  have hlen : (call.args.length != act.params.length) = false := by simp [Forall2.length hargs]
  simp only [hf.scope, hact, hlen, Bool.false_eq_true, ↓reduceIte]
  have hc' : CtxOk G { c with action := some act } := hc.withAction hmem
  refine Triple.bind (Triple.setFrame' (Q := fun _ r' => OkQ G { c with action := some act } r')
    ⟨hr.frame, ⟨rfl, hf.vars, (foldl_params hnodup (hc.index ▸ hargs)).layer⟩⟩) ?_
  rintro _ r1 hok
  refine Triple.pure' (OkQ.step hc' ?_ hok)
  refine ⟨?_, act, c, rfl, hc, rfl, hf.layer, (fun _ _ h => by cases h), hrest⟩
  rw [hc.withAction_eq]
  exact htyped.2.2

theorem outsIn_of_params (hc : CtxOk G c) (hf : FrameOk c f) (hp : ParamsIn c.scope params) :
    OutsIn G params f := by
  intro q hq _
  obtain ⟨d, hd, hdt⟩ := hp q hq
  have hvar : c.var? q.name = some d := by
    unfold Ctx.var?
    cases ha : c.action with
    | none => simpa using hd
    | some a =>
      have hmem := hc.action a ha
      have hnone : a.params.find? (·.name == q.name) = none := by
        rw [List.find?_eq_none]
        intro q' hq' heq
        have := (hc.laws.actionParams a hmem).2 q' hq'
        rw [show q'.name = q.name by simpa using heq, hd] at this
        cases this
      simp [hnone, hd]
  obtain ⟨v, hv, hvt⟩ := hf.read hvar
  exact ⟨v, hv, by rw [← hdt, ← hc.index]; exact hvt⟩

theorem dispatch_actionReturn (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.actionReturn outer copy :: rest)) :
    Triple (dispatch (.actionReturn outer copy)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨a, c', ha, hc', hsc, hlayer, hcopy, hrest⟩ := hs
  have hmem := hc.action a ha
  have hnodup := (hc.laws.actionParams a hmem).1
  have hidx : c'.index = c.index := hc'.index.trans hc.index.symm
  let fr : Frame := ⟨r.frame.scope, r.frame.vars, outer.action, outer.actionVars⟩
  have hf' : FrameOk c' fr := ⟨hf.scope.trans hsc.symm, by rw [hsc, hidx]; exact hf.vars, hlayer⟩
  simp only [dispatch]
  refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
  rintro _ r0 ⟨rfl, rfl⟩
  refine Triple.bind (Triple.setFrame' (Q := fun _ r' => OkQ G c' r') ⟨hr.frame, hf'⟩) ?_
  rintro _ r1 hok
  cases copy with
  | none => exact Triple.pure' (OkQ.step hc' hrest hok)
  | some pa =>
    obtain ⟨ps, as⟩ := pa
    obtain ⟨rfl, hcp⟩ := hcopy ps as rfl
    simp only
    have houts : OutsIn G a.params r0.frame := by
      intro q hq _
      have hvar : c.var? q.name = some (.param q) := by
        simp [Ctx.var?, ha, find_of_nodup hnodup hq]
      obtain ⟨v, hv, hvt⟩ := hf.read hvar
      exact ⟨v, hv, hc.index ▸ hvt⟩
    refine Triple.bind (Triple.mono (copyBack_ok hc' hok.2 hok.1 hcp houts) (fun _ _ h => h)
      (fun _ _ h => h.step hc' hrest)) ?_
    rintro _ r2 hok2
    exact Triple.pure' (OkQ.step hc' hrest hok2)

-- ---------------------------------------------------------------------------
-- Block return
-- ---------------------------------------------------------------------------

/-- A block return: restore the caller, copy back. -/
theorem blockReturn_core (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hp : ParamsIn c.scope params) (hc' : CtxOk G c') (hf' : FrameOk c' caller)
    (hcopy : CopyOk c' params args) :
    Triple (dispatch (.blockReturn caller params args)) r
      (fun next r' => next = [] ∧ OkQ G c' r') (ErrQ G c') := by
  have houts := outsIn_of_params hc hf hp
  simp only [dispatch]
  refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
  rintro _ r0 ⟨rfl, rfl⟩
  refine Triple.bind (Triple.setFrame' (Q := fun _ r' => OkQ G c' r') ⟨hr.frame, hf'⟩) ?_
  rintro _ r1 hok
  refine Triple.bind (copyBack_ok hc' hok.2 hok.1 hcopy houts) ?_
  rintro _ r2 hok2
  exact Triple.pure' ⟨rfl, hok2⟩

theorem dispatch_blockReturn (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.blockReturn caller params args :: rest)) :
    Triple (dispatch (.blockReturn caller params args)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨_, hp, c', hc', hf', hcopy, hrest⟩ := hs
  refine Triple.mono (blockReturn_core hc hf hr hp hc' hf' hcopy) ?_ (fun _ _ h => h.step hc' hrest)
  rintro next r' ⟨rfl, h⟩
  exact OkQ.step hc' hrest h

/-- The one item that runs while a fault unwinds. -/
theorem blockReturn_unwind (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : UnwindOk G c.scope (.blockReturn caller params args :: rest)) :
    Triple (dispatch (.blockReturn caller params args)) r
      (fun next r' => next = [] ∧ RunOk G r' ∧ ∃ c', CtxOk G c' ∧ FrameOk c' r'.frame ∧
        UnwindOk G c'.scope rest)
      (StepE G rest) := by
  simp only [UnwindOk] at hs
  obtain ⟨hp, c', hc', hf', hcopy, hrest⟩ := hs
  refine Triple.mono (blockReturn_core hc hf hr hp hc' hf' hcopy) ?_
    (fun _ _ h => ⟨h.1, h.2.1, c', hc', h.2.2, hrest⟩)
  rintro next r' ⟨rfl, h⟩
  exact ⟨rfl, h.1, c', hc', h.2, hrest⟩

-- ---------------------------------------------------------------------------
-- Calls with copy-in loops
-- ---------------------------------------------------------------------------

theorem nodup_prefix {ps : List Param} {as : List Arg} {pre rem : List (Param × Arg)}
    (hlen : ps.length = as.length) (hn : (ps.map Param.name).Nodup)
    (hsplit : ps.zip as = pre ++ (q, a) :: rem) : q.name ∉ (pre.map Prod.fst).map Param.name := by
  have hps : ps = pre.map Prod.fst ++ q :: rem.map Prod.fst := by
    rw [← map_fst_zip_eq hlen, hsplit]; simp
  rw [hps] at hn
  simp only [List.map_append, List.map_cons, List.nodup_append] at hn
  intro hin
  exact hn.2.2 _ hin _ (by simp) rfl

theorem dispatch_action (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.action name args :: rest)) :
    Triple (dispatch (.action name args)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨⟨act, hact, hargs⟩, hrest⟩ := hs
  obtain ⟨hmem, htyped⟩ := hc.action' hact
  have hnodup := (hc.laws.actionParams act hmem).1
  have hlen := hargs.length
  have hpty : ∀ q ∈ act.params, TyOk G.idx q.type := htyped.2.1
  simp only [dispatch]
  refine Triple.bind (Triple.getFrame' (Q := fun a r' => r' = r ∧ a = r.frame) ⟨rfl, rfl⟩) ?_
  rintro _ r0 ⟨rfl, rfl⟩
  have hlen' : (args.length != act.params.length) = false := by simp [hlen]
  simp only [hf.scope, hact, hlen', Bool.false_eq_true, ↓reduceIte]
  refine Triple.bind (Triple.forIn'
    (I := fun rem acc r' => r' = r0 ∧ ∃ pre, act.params.zip args = pre ++ rem ∧
      MapOk G.idx (pre.map Prod.fst) acc.1 ∧
      Forall2 (fun (x : Param × Arg) a' => ArgOk c x.1 a') pre acc.2)
    (Q := fun acc r' => r' = r0 ∧ MapOk G.idx act.params acc.1 ∧ CopyOk c act.params acc.2)
    ⟨rfl, [], by simp, MapOk.nil, .nil⟩ ?_ ?_) ?_
  · rintro ⟨q, a⟩ xs acc r' ⟨hr', pre, hsplit, hmap, hres⟩
    subst hr'
    have hx : (q, a) ∈ act.params.zip args := by rw [hsplit]; simp
    have hq : q ∈ act.params := (List.of_mem_zip hx).1
    refine Triple.bind (Triple.mono (copyIn_ok hc hf hr (hargs.mem _ hx) (hpty q hq))
      (fun _ _ h => h) (fun _ _ h => (Short.errQ hr hf h).step hc hrest)) ?_
    rintro ⟨v, a'⟩ r' ⟨hr', hv, hok⟩
    subst hr'
    refine Triple.pure' ⟨rfl, pre ++ [(q, a)], by simp [hsplit], ?_, hres.append hok⟩
    simpa using hmap.snoc (nodup_prefix hlen.symm hnodup hsplit) hv
  · rintro acc r' ⟨hr', pre, hsplit, hmap, hres⟩
    simp only [List.append_nil] at hsplit
    subst hsplit
    refine ⟨hr', ?_, copyOk_of hlen.symm hres⟩
    rwa [map_fst_zip_eq hlen.symm] at hmap
  · rintro acc r' ⟨hr', hmap, hcopy⟩
    subst hr'
    have hc' : CtxOk G { c with action := some act } := hc.withAction hmem
    have hfr : FrameOk { c with action := some act }
        ⟨c.scope, r'.frame.vars, some act.name, some acc.1⟩ := by
      refine ⟨rfl, hf.vars, ?_⟩
      show LayerOk c.index (some act) (some acc.1)
      rw [hc.index]
      exact hmap.layer
    refine Triple.bind (Triple.setFrame' (Q := fun _ r' => OkQ G { c with action := some act } r')
      ⟨hr.frame, hfr⟩) ?_
    rintro _ r1 hok
    refine Triple.pure' (OkQ.step hc' ?_ hok)
    refine ⟨?_, act, c, rfl, hc, rfl, hf.layer, ?_, hrest⟩
    · rw [hc.withAction_eq]
      exact htyped.2.2
    · intro ps as h
      cases h
      exact ⟨rfl, hcopy⟩

/-- The variables of a scope, each at a value of its type. -/
def VarsOk (idx : Index) (sc : BlockScope) (vars : HashMap String Value) : Prop :=
  ∀ (x : String) (d : VarDecl), sc.vars[x]? = some d → ∃ v, vars[x]? = some v ∧ ValueHas idx v d.type

theorem dispatch_block (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (.block name args :: rest)) :
    Triple (dispatch (.block name args)) r (StepQ G rest) (StepE G rest) := by
  simp only [StackOk] at hs
  obtain ⟨⟨b, hb, hk, hargs⟩, hrest⟩ := hs
  rw [hc.index] at hb
  obtain ⟨sc, hsc, hscb, hcb⟩ := G.blockCtx hb (hk.trans hc.kind)
  have hlaws : Build.ScopeLaws b sc := hscb ▸ hcb.laws
  have hbt : BlockTyped G.idx sc b := hscb ▸ hcb.typed
  have hlen := hargs.length
  have hpty : ∀ q ∈ b.params, TyOk G.idx q.type := fun q hq => (hbt.params q hq).2
  have hvty : ∀ (x : String) (d : VarDecl), sc.vars[x]? = some d → TyOk G.idx d.type := by
    intro x d hd
    obtain ⟨_, hsrc⟩ := hlaws.varOrigin x d hd
    rcases hsrc with ⟨q, hq, rfl⟩ | ⟨v, hv, rfl⟩
    · exact (hbt.params q hq).2
    · exact hbt.locals v hv
  obtain ⟨callee, hfb, hcs, hcav, hcvars⟩ := forBlock_ok G.laws (b := b) hsc hvty
  simp only [dispatch]
  refine Triple.bind (Triple.getIndex' (Q := fun a r' => r' = r ∧ a = G.idx) ⟨rfl, hr.index⟩) ?_
  rintro _ r0 ⟨rfl, rfl⟩
  have hlen' : (args.length != b.params.length) = false := by simp [hlen]
  simp only [hb, hlen', Bool.false_eq_true, ↓reduceIte]
  refine Triple.bind (Triple.liftExcept' hfb (Q := fun a r' => r' = r0 ∧ a = callee) ⟨rfl, rfl⟩) ?_
  rintro _ r1 ⟨hr1, rfl⟩
  subst hr1
  refine Triple.bind (Triple.forIn'
    (I := fun rem acc r3 => r3 = r1 ∧ ∃ pre, b.params.zip args = pre ++ rem ∧
      acc.1.scope = sc ∧ acc.1.actionVars = none ∧ VarsOk G.idx sc acc.1.vars ∧
      Forall2 (fun (x : Param × Arg) a' => ArgOk c x.1 a') pre acc.2)
    (Q := fun acc r3 => r3 = r1 ∧ acc.1.scope = sc ∧ acc.1.actionVars = none ∧
      VarsOk G.idx sc acc.1.vars ∧ CopyOk c b.params acc.2)
    ⟨rfl, [], by simp, hcs, hcav, hcvars, .nil⟩ ?_ ?_) ?_
  · rintro ⟨q, a⟩ xs acc r' ⟨hr', pre, hsplit, hs', hav, hvars, hres⟩
    subst hr'
    have hx : (q, a) ∈ b.params.zip args := by rw [hsplit]; simp
    have hq : q ∈ b.params := (List.of_mem_zip hx).1
    refine Triple.bind (Triple.mono (copyIn_ok hc hf hr (hargs.mem _ hx) (hpty q hq))
      (fun _ _ h => h) (fun _ _ h => (Short.errQ hr hf h).step hc hrest)) ?_
    rintro ⟨v, a'⟩ r' ⟨hr', hv, hok⟩
    subst hr'
    refine Triple.pure' ⟨rfl, pre ++ [(q, a)], by simp [hsplit], hs', hav, ?_, hres.append hok⟩
    intro y d hd
    by_cases hqy : q.name = y
    · subst hqy
      rw [hlaws.paramFound q hq] at hd
      cases hd
      exact ⟨v, by simp, hv⟩
    · simpa [Std.HashMap.getElem?_insert, hqy] using hvars y d hd
  · rintro acc r' ⟨hr', pre, hsplit, hs', hav, hvars, hres⟩
    simp only [List.append_nil] at hsplit
    subst hsplit
    exact ⟨hr', hs', hav, hvars, copyOk_of hlen.symm hres⟩
  · rintro acc r' ⟨hr', hs', hav, hvars, hcopy⟩
    subst hr'
    refine Triple.bind (Triple.getFrame' (Q := fun a r'' => r'' = r' ∧ a = r'.frame) ⟨rfl, rfl⟩) ?_
    rintro _ r4 ⟨hr4, rfl⟩
    subst hr4
    have hcb' : CtxOk G { index := G.idx, scope := sc, kind := G.kind } := hcb
    have hfc : FrameOk { index := G.idx, scope := sc, kind := G.kind } acc.1 :=
      ⟨hs', hvars, by simp [LayerOk, hav]⟩
    refine Triple.bind (Triple.setFrame'
      (Q := fun _ r' => OkQ G { index := G.idx, scope := sc, kind := G.kind } r') ⟨hr.frame, hfc⟩) ?_
    rintro _ r2 hok
    refine Triple.pure' (OkQ.step hcb' ⟨hscb, rfl, rfl, ?_, c, hc, hf, hcopy, hrest⟩ hok)
    intro q hq
    exact ⟨_, hlaws.paramFound q hq, rfl⟩

/-- Every typed work item steps safely. -/
theorem dispatch_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hs : StackOk G c (w :: rest)) :
    Triple (dispatch w) r (StepQ G rest) (StepE G rest) := by
  cases w with
  | statements body =>
    simp only [StackOk] at hs
    obtain ⟨hb, hrest⟩ := hs
    cases hb with
    | nil => exact Triple.pure' (OkQ.step hc hrest ⟨hr, hf⟩)
    | cons hs hss => exact Triple.pure' (OkQ.step hc ⟨hs, hss, hrest⟩ ⟨hr, hf⟩)
  | statement st =>
    simp only [StackOk] at hs
    exact dispatch_statement hc hf hr hs.1 hs.2
  | table => exact dispatch_table hc hf hr hs
  | tableAction => exact dispatch_tableAction hc hf hr hs
  | action => exact dispatch_action hc hf hr hs
  | block => exact dispatch_block hc hf hr hs
  | runBlock => exact dispatch_runBlock hc hf hr hs
  | states => exact dispatch_states hc hf hr hs
  | state => exact dispatch_state hc hf hr hs
  | transition => exact dispatch_transition hc hf hr hs
  | writeHit => exact dispatch_writeHit hc hf hr hs
  | actionReturn => exact dispatch_actionReturn hc hf hr hs
  | blockReturn => exact dispatch_blockReturn hc hf hr hs

end

end P4bloIR.Validity
