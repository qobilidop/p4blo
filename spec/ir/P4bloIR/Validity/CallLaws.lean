import P4bloIR.Validity.Machine

/-!
# Calls do not get stuck

Copy-in of a typed argument gives a value of the parameter's type and, for
`out` and `inout`, an lvalue of the caller of that type (`copyIn_ok`);
copy-back of such lvalues from values of their types writes only the frame
(`copyBack_ok`); a fresh activation of a block of the program has every
variable at a value of its type (`forBlock_ok`); an extern call obeying
the contract keeps the run well formed (`callExtern_ok`).
-/

namespace P4bloIR.Validity

open Std (HashMap)
open ScalarTyping (run_bind run_pure run_map)

/-- What the machine keeps after a step that stays in its context: a
well-formed run and frame. -/
def OkQ (G : Global) (c : Ctx) (r' : Run) : Prop := RunOk G r' ∧ FrameOk c r'.frame

/-- A fault the machine may meet: a parser error of the program, with the
run and frame still well formed. -/
def ErrQ (G : Global) (c : Ctx) (f : Fault) (r' : Run) : Prop :=
  Documented G f ∧ OkQ G c r'

theorem Global.core (G : Global) (h : e ∈ coreErrors) : e ∈ G.p.errors := by
  have hp := G.valid.errors
  obtain ⟨t, ht⟩ := List.isPrefixOf_iff_prefix.mp hp
  rw [← ht]
  exact List.mem_append_left _ h

theorem Short.errQ (hr : RunOk G r) (hf : FrameOk c r.frame) (h : Short r f r') : ErrQ G c f r' := by
  obtain ⟨rfl, rfl⟩ := h
  exact ⟨⟨_, rfl, G.core (by simp [coreErrors])⟩, hr, hf⟩

theorem WriteQ.okQ (hr : RunOk G r) (h : WriteQ c r u r') : OkQ G c r' := by
  obtain ⟨f', rfl, hf'⟩ := h
  exact ⟨hr.frame, hf'⟩

theorem isOut_iff : isOut d = true ↔ (d == .out || d == .inout) = true := by
  cases d <;> decide

-- ---------------------------------------------------------------------------
-- Copy-in
-- ---------------------------------------------------------------------------

/-- The argument copy-back will use: for `out` and `inout`, an lvalue of
the caller of the parameter's type. -/
def ArgOk (c : Ctx) (q : Param) (a : Arg) : Prop :=
  isOut q.direction = true → ∃ lv, a = .lvalue lv ∧ LvOk c lv q.type

section
variable {G : Global} {c : Ctx} {r : Run}

theorem copyIn_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (ha : ArgTyped c arg q) (hq : TyOk G.idx q.type) :
    Triple (copyIn q arg) r
      (fun p r' => r' = r ∧ ValueHas G.idx p.1 q.type ∧ ArgOk c q p.2) (Short r) := by
  unfold copyIn
  cases ha with
  | input hin he =>
    have hnout : (q.direction == .out) = false := by
      cases hd : q.direction <;> simp_all [isOut]
    have hninout : (q.direction == .inout) = false := by
      cases hd : q.direction <;> simp_all [isOut]
    simp only [resolveArg, argumentValue, hnout, hninout, Bool.or_false, Bool.false_eq_true,
      ↓reduceIte, pure_bind]
    refine Triple.bind (evaluate_ok hc hf hr he) ?_
    rintro v r' ⟨rfl, hv⟩
    exact Triple.pure' ⟨rfl, hv, fun h => by simp [hin] at h⟩
  | output hout hl =>
    have hyes : (q.direction == .out || q.direction == .inout) = true := isOut_iff.mp hout
    simp only [resolveArg, hyes, ↓reduceIte]
    refine Triple.bind (Triple.bind (resolveLValue_ok hc hf hr hl.lvOk) (fun lv' r' h =>
      Triple.pure' (Q := fun a r'' => r'' = r ∧ ∃ lv', a = Arg.lvalue lv' ∧ LvOk c lv' q.type)
        ⟨h.1, lv', rfl, h.2⟩)) ?_
    rintro a r' ⟨rfl, lv', rfl, hl'⟩
    unfold argumentValue
    by_cases hd : (q.direction == .out) = true
    · simp only [hd, ↓reduceIte]
      obtain ⟨z, hz, hzt⟩ := zero_ok G.laws hq
      have hrun : (do let i ← getIndex; liftExcept (Value.zero q.type i) : M Value).run r' =
          (.ok z, r') := by
        simp [run_bind, hr.index, hz, liftExcept]
      refine Triple.bind (Triple.of_run hrun (Q := fun a r'' => r'' = r' ∧ a = z) ⟨rfl, rfl⟩) ?_
      rintro _ _ ⟨rfl, rfl⟩
      exact Triple.pure' ⟨rfl, hzt, fun _ => ⟨lv', rfl, hl'⟩⟩
    · simp only [hd, Bool.false_eq_true, ↓reduceIte]
      refine Triple.bind (readLValue_ok hc hf hr hl') ?_
      rintro v r' ⟨rfl, hv⟩
      exact Triple.pure' ⟨rfl, hv, fun _ => ⟨lv', rfl, hl'⟩⟩

-- ---------------------------------------------------------------------------
-- Copy-back
-- ---------------------------------------------------------------------------

/-- The out parameters' values a callee's frame holds. -/
def OutsIn (G : Global) (params : List Param) (values : Frame) : Prop :=
  ∀ q ∈ params, isOut q.direction = true → ∃ v, values.read? q.name = some v ∧ ValueHas G.idx v q.type

theorem CopyOk.mem (h : CopyOk c ps as) :
    ∀ q a, (q, a) ∈ ps.zip as → ArgOk c q a := by
  induction h with
  | nil => simp
  | out hout hl _ ih =>
    intro q a hm
    rcases List.mem_cons.mp hm with h | hm
    · cases h; exact fun _ => ⟨_, rfl, hl⟩
    · exact ih q a hm
  | skip hin _ ih =>
    intro q a hm
    rcases List.mem_cons.mp hm with h | hm
    · cases h; exact fun h => by simp [hin] at h
    · exact ih q a hm

/-- Copy-back writes typed values through typed lvalues: only the frame
changes, and it stays well formed. -/
theorem copyBack_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hcopy : CopyOk c params args) (hvals : OutsIn G params values) :
    Triple (copyBack params args values) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  unfold copyBack
  have hmem := hcopy.mem
  refine Triple.bind (Triple.forIn'
    (I := fun rem _ r' => OkQ G c r' ∧ ∀ x ∈ rem, x ∈ params.zip args)
    (Q := fun _ r' => OkQ G c r') ⟨⟨hr, hf⟩, fun x hx => hx⟩ ?_ (fun _ _ h => h.1)) ?_
  · rintro ⟨q, a⟩ xs b r' ⟨⟨hr', hf'⟩, hin⟩
    have hqa := hin (q, a) (by simp)
    have hq : q ∈ params := (List.of_mem_zip hqa).1
    simp only
    split
    · rename_i hd
      obtain ⟨lv, rfl, hl⟩ := hmem q a hqa (isOut_iff.mpr hd)
      obtain ⟨v, hv, hvt⟩ := hvals q hq (isOut_iff.mpr hd)
      simp only [hv]
      refine Triple.bind (Triple.mono (writeLValue_ok hc hf' hr' hl hvt) (fun _ _ h => h)
        (fun _ _ h => Short.errQ hr' hf' h)) ?_
      rintro _ r'' hw
      exact Triple.pure' ⟨hw.okQ hr', fun x hx => hin x (List.mem_cons_of_mem _ hx)⟩
    · exact Triple.pure' ⟨⟨hr', hf'⟩, fun x hx => hin x (List.mem_cons_of_mem _ hx)⟩
  · rintro _ r' h
    exact Triple.pure' h

-- ---------------------------------------------------------------------------
-- A fresh activation
-- ---------------------------------------------------------------------------

theorem zeroLoop {idx : Index} (L : List (String × VarDecl))
    (hL : ∀ p ∈ L, ∃ v, Value.zero p.2.type idx = .ok v ∧ ValueHas idx v p.2.type)
    (acc : HashMap String Value) :
    ∃ vars, forIn L acc (fun (x : String × VarDecl) (s : HashMap String Value) => match x with
        | (name, decl) => do
          let z ← Value.zero decl.type idx
          pure (ForInStep.yield (s.insert name z))) = .ok vars ∧
      (∀ (k : String) (v : Value), vars[k]? = some v →
        acc[k]? = some v ∨ ∃ d : VarDecl, (k, d) ∈ L ∧ ValueHas idx v d.type) ∧
      (∀ p ∈ L, vars[p.1]? ≠ none) ∧ (∀ k : String, acc[k]? ≠ none → vars[k]? ≠ none) := by
  induction L generalizing acc with
  | nil => exact ⟨acc, rfl, fun _ _ h => .inl h, by simp, fun _ h => h⟩
  | cons p ps ih =>
    obtain ⟨name, decl⟩ := p
    obtain ⟨z, hz, hzt⟩ := hL (name, decl) (by simp)
    obtain ⟨vars, hvars, hk, hin, hkeep⟩ :=
      ih (fun q hq => hL q (List.mem_cons_of_mem _ hq)) (acc.insert name z)
    refine ⟨vars, ?_, ?_, ?_, ?_⟩
    · rw [List.forIn_cons]
      simp only [hz, bind, Except.bind, pure, Except.pure]
      exact hvars
    · intro k v hv
      rcases hk k v hv with h | ⟨d, hd, ht⟩
      · rw [Std.HashMap.getElem?_insert] at h
        split at h
        · rename_i heq
          cases h
          exact .inr ⟨decl, by simp_all, hzt⟩
        · exact .inl h
      · exact .inr ⟨d, List.mem_cons_of_mem _ hd, ht⟩
    · intro q hq
      rcases List.mem_cons.mp hq with rfl | hq
      · exact hkeep _ (by simp)
      · exact hin q hq
    · intro k hk'
      apply hkeep
      rw [Std.HashMap.getElem?_insert]
      split <;> simp_all

/-- A fresh activation of a block holds a value of every variable's type. -/
theorem forBlock_ok {b : Block} {sc : BlockScope} (L : Build.IndexLaws p idx)
    (hsc : idx.scopes[b.name]? = some sc)
    (hty : ∀ (x : String) (d : VarDecl), sc.vars[x]? = some d → TyOk idx d.type) :
    ∃ f, Frame.forBlock idx b = .ok f ∧ f.scope = sc ∧ f.actionVars = none ∧
      ∀ (x : String) (d : VarDecl), sc.vars[x]? = some d →
        ∃ v, f.vars[x]? = some v ∧ ValueHas idx v d.type := by
  obtain ⟨vars, hvars, hk, hin, -⟩ := zeroLoop (idx := idx) sc.vars.toList
    (fun q hq => zero_ok L (hty q.1 q.2 (Std.HashMap.mem_toList_iff_getElem?_eq_some.mp hq))) {}
  refine ⟨{ scope := sc, vars }, ?_, rfl, rfl, ?_⟩
  · unfold Frame.forBlock
    rw [hsc]
    simp only
    rw [hvars]
    rfl
  · intro x d hd
    have hm : (x, d) ∈ sc.vars.toList := Std.HashMap.mem_toList_iff_getElem?_eq_some.mpr hd
    cases hv : vars[x]? with
    | none => exact absurd hv (hin _ hm)
    | some v =>
      rcases hk x v hv with h | ⟨d', hd', ht⟩
      · simp at h
      · have := Std.HashMap.mem_toList_iff_getElem?_eq_some.mp hd'
        rw [hd] at this
        cases this
        exact ⟨v, rfl, ht⟩

-- ---------------------------------------------------------------------------
-- Extern calls
-- ---------------------------------------------------------------------------

theorem ArgsTyped.length (h : ArgsTyped c as ps) : as.length = ps.length := by
  induction h with
  | nil => rfl
  | cons _ _ ih => simp [ih]

theorem ArgsTyped.mem (h : ArgsTyped c as ps) : ∀ x ∈ ps.zip as, ArgTyped c x.2 x.1 := by
  induction h with
  | nil => simp
  | cons ha _ ih =>
    intro x hx
    rcases List.mem_cons.mp hx with rfl | hx
    · exact ha
    · exact ih x hx

/-- One copied-in argument: a value of the parameter's type and the
argument copy-back uses. -/
def CopiedOk (G : Global) (c : Ctx) (x : Param × Arg) (y : Value × Arg) : Prop :=
  ValueHas G.idx y.1 x.1.type ∧ ArgOk c x.1 y.2

/-- The arguments an extern call writes back: the resolved `out` and
`inout` ones, in order. -/
def written (ps : List Param) (as : List Arg) : List Arg :=
  (ps.zip as).filterMap fun x => match x with
    | (p, a) => if (p.direction == .out || p.direction == .inout) = true then some a else none

theorem copied_ok {ps : List Param} {as : List Arg} {copied : List (Value × Arg)}
    (hlen : ps.length = as.length) (h : Forall2 (CopiedOk G c) (ps.zip as) copied) :
    ValuesHave G.idx (copied.map Prod.fst) (ps.map (·.type)) ∧
      CopyOk c ps (copied.map Prod.snd) ∧ (copied.map Prod.snd).length = ps.length ∧
      ∀ outs, ValuesHave G.idx outs ((ps.filter (isOut ·.direction)).map (·.type)) →
        (written ps (copied.map Prod.snd)).length = outs.length ∧
        ∀ a v, (a, v) ∈ (written ps (copied.map Prod.snd)).zip outs →
          ∃ lv t, a = .lvalue lv ∧ LvOk c lv t ∧ ValueHas G.idx v t := by
  induction ps generalizing as copied with
  | nil =>
    cases h
    refine ⟨.nil, .nil, rfl, fun outs ho => ?_⟩
    cases ho
    simp [written]
  | cons q qs ih =>
    cases as with
    | nil => simp at hlen
    | cons a as =>
      cases h with
      | cons hy hrest =>
        rename_i y copied
        obtain ⟨hv, hargok⟩ := hy
        obtain ⟨h1, h2, h3, h4⟩ := ih (by simpa using hlen) hrest
        have hwr : written (q :: qs) (y.2 :: copied.map Prod.snd) =
            (if isOut q.direction then [y.2] else []) ++ written qs (copied.map Prod.snd) := by
          unfold written
          simp only [List.zip_cons_cons, List.filterMap_cons]
          by_cases hq : isOut q.direction = true
          · simp [isOut_iff.mp hq, hq]
          · have : (q.direction == .out || q.direction == .inout) = false := by
              rw [← Bool.not_eq_true, ← isOut_iff]; exact hq
            simp [this, hq]
        refine ⟨.cons hv h1, ?_, by simp [h3], ?_⟩
        · by_cases hq : isOut q.direction = true
          · obtain ⟨lv, hlv, hl⟩ := hargok hq
            simp only [List.map_cons]
            rw [hlv]
            exact .out hq hl h2
          · exact .skip (by simpa using hq) h2
        · intro outs ho
          simp only [List.map_cons] at ⊢
          rw [hwr]
          by_cases hq : isOut q.direction = true
          · simp only [List.filter_cons, hq, ↓reduceIte, List.map_cons] at ho
            cases ho with
            | cons ho1 ho2 =>
              rename_i o outs
              obtain ⟨hl1, hl2⟩ := h4 outs ho2
              refine ⟨by simp [hq, hl1], ?_⟩
              intro a' v hm
              simp only [hq, ↓reduceIte, List.singleton_append, List.zip_cons_cons,
                List.mem_cons] at hm
              rcases hm with h | hm
              · cases h
                obtain ⟨lv, hlv, hl⟩ := hargok hq
                exact ⟨lv, q.type, hlv, hl, ho1⟩
              · exact hl2 a' v hm
          · have hq' : isOut q.direction = false := by simpa using hq
            simp only [List.filter_cons, hq', Bool.false_eq_true, ↓reduceIte] at ho
            obtain ⟨hl1, hl2⟩ := h4 outs ho
            refine ⟨by simp [hq', hl1], ?_⟩
            simpa [hq'] using hl2

theorem ValuesHave.length (h : ValuesHave idx vs ts) : vs.length = ts.length := by
  induction h with
  | nil => rfl
  | cons _ _ ih => simp [ih]

theorem RunOk.externs' (hr : RunOk G r) (he : G.externs.inv e) : RunOk G { r with externs := e } :=
  ⟨hr.index, hr.packet, hr.emitter, hr.entries, he⟩

/-- An extern call of a typed statement keeps the run well formed. -/
theorem callExtern_ok (hc : CtxOk G c) (hf : FrameOk c r.frame) (hr : RunOk G r)
    (hi : c.index.externInstances[inst]? = some i) (het : c.index.externTypes[i.externType]? = some et)
    (hm : et.methods.find? (·.name == m) = some meth) (hargs : ArgsTyped c args meth.params)
    (hres : ResultTyped c meth.returns result) :
    Triple (callExtern inst m args result) r (fun _ r' => OkQ G c r') (ErrQ G c) := by
  rw [hc.index] at hi het
  have hmeth : meth ∈ et.methods := List.mem_of_find?_eq_some hm
  have hname : meth.name = m := by simpa using List.find?_some hm
  have hetOk := G.valid.externTypes et (G.laws.externType _ et het).1
  have hpty : ∀ q ∈ meth.params, TyOk G.idx q.type := fun q hq => ((hetOk.2.2.2 meth hmeth).2.1 q hq).2
  have hlen := hargs.length
  unfold callExtern
  -- the result lvalue, resolved first
  refine Triple.bind (Q := fun _ r' => OkQ G c r')
    (P := fun res r' => r' = r ∧ ∀ lv', res = some lv' → ∃ t, meth.returns = some t ∧ LvOk c lv' t)
    ?_ ?_
  · generalize hmr : meth.returns = mr at hres
    cases hres with
    | none => exact Triple.pure' ⟨rfl, by simp⟩
    | some hl =>
      simp only [Option.mapM]
      refine Triple.bind (Triple.mono (resolveLValue_ok hc hf hr hl.lvOk) (fun _ _ h => h)
        (fun _ _ h => Short.errQ hr hf h)) ?_
      rintro lv' r' ⟨rfl, hl'⟩
      exact Triple.pure' ⟨rfl, fun x hx => by cases hx; exact ⟨_, by first | rfl | exact hmr, hl'⟩⟩
  rintro res r' ⟨hr', hresOk⟩
  subst hr'
  refine Triple.bind (Triple.getIndex' (Q := fun a r'' => r'' = _ ∧ a = G.idx) ⟨rfl, hr.index⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  simp only [hi, het, hm]
  have hne : (args.length != meth.params.length) = false := by simp [hlen]
  simp only [hne, Bool.false_eq_true, ↓reduceIte]
  -- copy-in
  refine Triple.bind (Triple.mono (Triple.mapM' (CopiedOk G c) (fun r'' => r'' = _) rfl ?_)
    (fun a r'' h => h) (fun f r'' h => Short.errQ hr hf h)) ?_
  · rintro ⟨q, a⟩ hx r'' rfl
    have hq : q ∈ meth.params := (List.of_mem_zip hx).1
    refine Triple.mono (copyIn_ok hc hf hr (hargs.mem _ hx) (hpty q hq)) ?_ (fun _ _ h => h)
    rintro ⟨v, a'⟩ r3 ⟨rfl, hv, hok⟩
    exact ⟨⟨hv, hok⟩, rfl⟩
  rintro copied r'' ⟨hcopied, hr''⟩
  subst hr''
  obtain ⟨hvals, hcopy, hcl, hwr⟩ := copied_ok (by rw [hlen]) hcopied
  obtain ⟨e', res', hcall, hinv, houts, hret⟩ :=
    G.externs.call _ inst i et meth _ hr.externs hi het hmeth hvals
  rw [hname] at hcall
  refine Triple.bind (Triple.get' (Q := fun a r3 => r3 = _ ∧ a = r3) ⟨rfl, rfl⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  refine Triple.bind (Triple.liftExcept' hcall (Q := fun a r3 => r3 = _ ∧ a = (e', res'))
    ⟨rfl, rfl⟩) ?_
  rintro _ _ ⟨rfl, rfl⟩
  simp only
  refine Triple.bind (Triple.modify' (Q := fun _ r3 => OkQ G c r3) ⟨hr.externs' hinv, hf⟩) ?_
  rintro _ r1 ⟨hr1, hf1⟩
  obtain ⟨hwlen, hwpairs⟩ := hwr res'.outs houts
  have hne2 : (res'.outs.length != (written meth.params (copied.map Prod.snd)).length) = false := by
    simp [hwlen]
  unfold written at hne2 hwpairs
  simp only [hne2, Bool.false_eq_true, ↓reduceIte]
  -- copy the out values back
  refine Triple.bind (Triple.forIn'
    (I := fun rem _ r3 => OkQ G c r3 ∧ ∀ y ∈ rem, y ∈ ((meth.params.zip (copied.map Prod.snd)).filterMap
      fun x => match x with
        | (p, a) => if (p.direction == .out || p.direction == .inout) = true then some a else none).zip res'.outs)
    (Q := fun _ r3 => OkQ G c r3) ⟨⟨hr1, hf1⟩, fun y hy => hy⟩ ?_ (fun _ _ h => h.1)) ?_
  · rintro ⟨a, v⟩ ys b r3 ⟨⟨hr3, hf3⟩, hin⟩
    obtain ⟨lv, t, rfl, hl, hv⟩ := hwpairs a v (hin _ (by simp))
    simp only
    refine Triple.bind (Triple.mono (writeLValue_ok hc hf3 hr3 hl hv) (fun _ _ h => h)
      (fun _ _ h => Short.errQ hr3 hf3 h)) ?_
    rintro _ r4 hw
    exact Triple.pure' ⟨hw.okQ hr3, fun y hy => hin y (List.mem_cons_of_mem _ hy)⟩
  rintro _ r3 ⟨hr3, hf3⟩
  cases hres' : res with
  | none => exact Triple.pure' ⟨hr3, hf3⟩
  | some lv' =>
    obtain ⟨t, hrt, hl⟩ := hresOk lv' hres'
    obtain ⟨v, hv, hvt⟩ := hret t hrt
    simp only [hv]
    exact Triple.mono (writeLValue_ok hc hf3 hr3 hl hvt) (fun _ _ h => h.okQ hr3)
      (fun _ _ h => Short.errQ hr3 hf3 h)

end

end P4bloIR.Validity
