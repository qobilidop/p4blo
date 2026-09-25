import P4bloIR.Validity.Invariants
import P4bloIR.Validity.ValueLaws
import P4bloIR.Validity.FrameLaws

/-!
# What installation guarantees

`Installed.build` checks every entry it installs and every default a host
sets. `build_installedOk`: for a valid program, a successful installation
satisfies `InstalledOk`, the premise the progress proof asks of the
entries, so installation leaves nothing for the run to trip on.
-/

namespace P4bloIR.Validity

open Std (HashMap)

/-- An action call a table of block `ref.1` may make: an action of that
block's scope with data of its parameters' types. -/
def ActionAt (idx : Index) (ref : TableRef) (call : ActionCall) : Prop :=
  ∀ sc, idx.scopes[ref.1]? = some sc →
    ∃ act, sc.actions[call.action]? = some act ∧ DataOk idx call.args act.params

/-- Every installed entry and default is an `ActionAt` call. -/
def InstOk (idx : Index) (i : Installed) : Prop :=
  i.index = idx ∧
    (∀ ref, ∀ e ∈ (i.entries.getD ref #[]).toList, ActionAt idx ref e.action) ∧
    (∀ ref call, i.defaults.getD ref none = some call → ActionAt idx ref call)

theorem except_bind_ok {x : Except ε α} {f : α → Except ε β} :
    x >>= f = .ok b ↔ ∃ a, x = .ok a ∧ f a = .ok b := by
  cases x <;> simp [bind, Except.bind]

/-- A loop whose every pass succeeds succeeds. -/
theorem forIn_total {l : List α} {b : β} {f : α → β → Except ε (ForInStep β)}
    (h : ∀ x b, ∃ s, f x b = .ok s) : ∃ b', forIn l b f = .ok b' := by
  induction l generalizing b with
  | nil => exact ⟨b, rfl⟩
  | cons x xs ih =>
    obtain ⟨s, hs⟩ := h x b
    rw [List.forIn_cons, hs]
    cases s with
    | done b' => exact ⟨b', rfl⟩
    | yield b' => exact ih

/-- An invariant kept by every pass of an `Except` loop holds at its end. -/
theorem forIn_inv {l : List α} {f : α → β → Except ε (ForInStep β)} (P : β → Prop)
    (h0 : P b) (hstep : ∀ x ∈ l, ∀ b s, P b → f x b = .ok s → P s.value)
    (h : forIn l b f = .ok b') : P b' := by
  induction l generalizing b with
  | nil => simp [pure, Except.pure] at h; subst h; exact h0
  | cons x xs ih =>
    rw [List.forIn_cons, except_bind_ok] at h
    obtain ⟨s, hs, hrest⟩ := h
    have hp := hstep x (by simp) b s h0 hs
    cases s with
    | done b'' => simp [pure, Except.pure] at hrest; subst hrest; exact hp
    | yield b'' =>
      exact ih hp (fun y hy => hstep y (List.mem_cons_of_mem _ hy)) hrest

/-- Every pass of a successful `Except` loop that never stops early
succeeds. -/
theorem forIn_each {l : List α} {f : α → PUnit → Except ε (ForInStep PUnit)}
    (hy : ∀ x s, f x PUnit.unit = .ok s → s = .yield PUnit.unit)
    (h : forIn l PUnit.unit f = .ok u) : ∀ x ∈ l, f x PUnit.unit = .ok (.yield PUnit.unit) := by
  induction l with
  | nil => simp
  | cons x xs ih =>
    rw [List.forIn_cons, except_bind_ok] at h
    obtain ⟨s, hs, hrest⟩ := h
    have hs' := hy x s hs
    subst hs'
    intro y hmem
    rcases List.mem_cons.mp hmem with rfl | hmem
    · exact hs
    · exact ih hrest y hmem

theorem literalFits_value (h : Installed.literalFits a t = true) :
    ValueHas idx (literalValue a) t := by
  cases a <;> cases t <;> simp_all [Installed.literalFits, literalValue, Literal.toValue, Bits.wrap]

/-- What a successful `checkAction` establishes: the action is one of the
block's, with data of its parameters' types. -/
theorem checkAction_data (h : Installed.checkAction i ref decl call = .ok u) :
    ∃ act, (i.index.scopes[ref.1]?.bind (·.actions[call.action]?)) = some act ∧
      DataOk i.index call.args act.params := by
  unfold Installed.checkAction at h
  try simp only at h
  split at h
  · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at h
  split at h
  case h_2 => simp [throw, throwThe, MonadExceptOf.throw] at h
  rename_i act hact
  refine ⟨act, hact, ?_⟩
  try simp only at h
  split at h
  · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at h
  try simp only at h
  split at h
  · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at h
  rename_i hlen
  have hlen : call.args.length = act.params.length := by simpa using hlen
  rw [except_bind_ok] at h
  obtain ⟨_, hloop, -⟩ := h
  have heach := forIn_each ?_ hloop
  · clear hloop
    unfold DataOk
    suffices key : ∀ (ps : List Param) (as : List Literal), as.length = ps.length →
        (∀ x ∈ ps.zip as, Installed.literalFits x.2 x.1.type = true) →
        Forall2 (fun a (q : Param) => ValueHas i.index (literalValue a) q.type) as ps by
      refine key _ _ hlen fun x hx => ?_
      have hb := heach x hx
      obtain ⟨q, a⟩ := x
      try simp only at hb
      split at hb
      · split at hb
        · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at hb
        · try simp only at hb
          split at hb
          · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at hb
          · simpa using ‹¬(!Installed.literalFits _ _) = true›
      · try simp only at hb
        split at hb
        · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at hb
        · simpa using ‹¬(!Installed.literalFits _ _) = true›
    intro ps
    induction ps with
    | nil => intro as hl _; cases as <;> simp at hl ⊢; exact .nil
    | cons q qs ih =>
      intro as hl hf
      cases as with
      | nil => simp at hl
      | cons a as =>
        exact .cons (literalFits_value (hf (q, a) (by simp)))
          (ih as (by simpa using hl) fun x hx => hf x (List.mem_cons_of_mem _ hx))
  · intro x st hst
    obtain ⟨q, a⟩ := x
    try simp only at hst
    split at hst
    · split at hst
      · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at hst
      · try simp only at hst
        split at hst
        · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at hst
        · simp [pure, Except.pure] at hst; exact hst.symm
    · try simp only at hst
      split at hst
      · simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw] at hst
      · simp [pure, Except.pure] at hst; exact hst.symm

theorem throw_ne {x : String} {f : Unit → Except String β} :
    (throw x >>= f : Except String β) ≠ .ok b := by
  simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw]

/-- An installed entry: only the table's entry list grows, by an entry
whose action passed `checkAction`. -/
theorem install_ok (h : Installed.install i ref e = .ok i') :
    i'.index = i.index ∧ i'.defaults = i.defaults ∧
      i'.entries = i.entries.insert ref ((i.entries.getD ref #[]).push e) ∧
      ∃ act, (i.index.scopes[ref.1]?.bind (·.actions[e.action.action]?)) = some act ∧
        DataOk i.index e.action.args act.params := by
  unfold Installed.install at h
  rw [except_bind_ok] at h
  obtain ⟨decl, -, h⟩ := h
  rw [except_bind_ok] at h
  obtain ⟨ws, -, h⟩ := h
  try simp only at h
  split at h
  · exact absurd h throw_ne
  rw [except_bind_ok] at h
  obtain ⟨_, -, h⟩ := h
  rw [except_bind_ok] at h
  obtain ⟨_, hca, h⟩ := h
  obtain ⟨act, hact, hdata⟩ := checkAction_data hca
  try simp only at h
  split at h
  · exact absurd h throw_ne
  rw [except_bind_ok] at h
  obtain ⟨_, -, h⟩ := h
  simp only [pure, Except.pure, Except.ok.injEq] at h
  subst h
  exact ⟨rfl, rfl, rfl, act, hact, hdata⟩

/-- A default a host sets: only the table's default changes, to a call
that passed `checkAction`. -/
theorem setDefault_ok (h : Installed.setDefault i ref (some call) = .ok i') :
    i'.index = i.index ∧ i'.entries = i.entries ∧
      i'.defaults = i.defaults.insert ref (some call) ∧
      ∃ act, (i.index.scopes[ref.1]?.bind (·.actions[call.action]?)) = some act ∧
        DataOk i.index call.args act.params := by
  unfold Installed.setDefault at h
  rw [except_bind_ok] at h
  obtain ⟨decl, -, h⟩ := h
  try simp only at h
  split at h
  · exact absurd h throw_ne
  rw [except_bind_ok] at h
  obtain ⟨_, hca, h⟩ := h
  obtain ⟨act, hact, hdata⟩ := checkAction_data hca
  simp only [pure, Except.pure, Except.ok.injEq, bind, Except.bind] at h
  subst h
  exact ⟨rfl, rfl, rfl, act, hact, hdata⟩

theorem actionAt_of {i : Installed} {ref : TableRef} {call : ActionCall} (hi : i.index = idx)
    (h : ∃ act, (i.index.scopes[ref.1]?.bind (·.actions[call.action]?)) = some act ∧
      DataOk i.index call.args act.params) : ActionAt idx ref call := by
  obtain ⟨act, hact, hdata⟩ := h
  intro sc hsc
  rw [hi, hsc] at hact
  exact ⟨act, by simpa using hact, hi ▸ hdata⟩

theorem InstOk.install (hok : InstOk idx i) (h : Installed.install i ref e = .ok i') :
    InstOk idx i' := by
  obtain ⟨hidx, hent, hdef⟩ := hok
  obtain ⟨h1, h2, h3, h4⟩ := install_ok h
  refine ⟨h1.trans hidx, ?_, by rw [h2]; exact hdef⟩
  intro ref' e' he'
  rw [h3] at he'
  simp only [Std.HashMap.getD_insert] at he'
  split at he'
  · rename_i heq
    simp only [beq_iff_eq] at heq
    subst heq
    simp only [Array.toList_push, List.mem_append, List.mem_singleton] at he'
    rcases he' with he' | rfl
    · exact hent _ e' he'
    · exact actionAt_of hidx h4
  · exact hent ref' e' he'

theorem InstOk.setDefault (hok : InstOk idx i) (h : Installed.setDefault i ref (some call) = .ok i') :
    InstOk idx i' := by
  obtain ⟨hidx, hent, hdef⟩ := hok
  obtain ⟨h1, h2, h3, h4⟩ := setDefault_ok h
  refine ⟨h1.trans hidx, by rw [h2]; exact hent, ?_⟩
  intro ref' call' hc
  rw [h3] at hc
  simp only [Std.HashMap.getD_insert] at hc
  split at hc
  · rename_i heq
    simp only [beq_iff_eq] at heq
    subst heq
    cases hc
    exact actionAt_of hidx h4
  · exact hdef ref' call' hc

theorem LitArgsTyped.data (h : LitArgsTyped idx as ps) : DataOk idx as ps := by
  induction h with
  | nil => exact .nil
  | cons ha _ ih => exact .cons ha.value ih

/-- A program's own default action is an `ActionAt` call. -/
theorem programDefault (G : Global) (hb : b ∈ G.p.blocks) (ht : t ∈ b.tables)
    (hd : t.defaultAction = some call) : ActionAt G.idx (b.name, t.name) call := by
  obtain ⟨sc, hsc, hbt⟩ := G.valid.blocks b hb
  intro sc' hsc'
  simp only at hsc'
  rw [hsc] at hsc'
  cases hsc'
  obtain ⟨-, act, hact, hargs⟩ := (hbt.tables t ht).defaultAction call hd
  exact ⟨act, hact, hargs.data⟩

theorem build_instOk (G : Global) (h : Installed.build G.idx host = .ok inst) : InstOk G.idx inst := by
  unfold Installed.build at h
  try simp only at h
  rw [except_bind_ok] at h
  obtain ⟨i1, hloop, h⟩ := h
  have hi1 : InstOk G.idx i1 := by
    refine forIn_inv (InstOk G.idx) ⟨rfl, by simp, by simp⟩ ?_ hloop
    intro b hb s st hs hstep
    rw [G.laws.program] at hb
    rw [except_bind_ok] at hstep
    obtain ⟨s', hinner, hst⟩ := hstep
    simp only [pure, Except.pure, Except.ok.injEq] at hst
    subst hst
    refine forIn_inv (InstOk G.idx) hs ?_ hinner
    intro t ht s2 st2 hs2 hstep2
    rw [except_bind_ok] at hstep2
    obtain ⟨s3, hents, hst2⟩ := hstep2
    simp only [pure, Except.pure, Except.ok.injEq] at hst2
    subst hst2
    refine forIn_inv (InstOk G.idx) ?_ ?_ hents
    · obtain ⟨hidx, hent, hdef⟩ := hs2
      refine ⟨hidx, ?_, ?_⟩
      · intro ref e he
        simp only [Std.HashMap.getD_insert] at he
        split at he
        · simp at he
        · exact hent ref e he
      · intro ref call hc
        simp only [Std.HashMap.getD_insert] at hc
        split at hc
        · rename_i heq
          simp only [beq_iff_eq] at heq
          subst heq
          exact programDefault G hb ht hc
        · exact hdef ref call hc
    · intro e _ s4 st4 hs4 hstep4
      rw [except_bind_ok] at hstep4
      obtain ⟨s5, hins, hst4⟩ := hstep4
      simp only [pure, Except.pure, Except.ok.injEq] at hst4
      subst hst4
      exact hs4.install hins
  split at h
  · rename_i hostEntries
    rw [except_bind_ok] at h
    obtain ⟨i2, hloop2, h⟩ := h
    simp only [pure, Except.pure, Except.ok.injEq] at h
    subst h
    refine forIn_inv (InstOk G.idx) hi1 ?_ hloop2
    intro te _ s st hs hstep
    rw [except_bind_ok] at hstep
    obtain ⟨s', hents, hst⟩ := hstep
    have hs' : InstOk G.idx s' := by
      refine forIn_inv (InstOk G.idx) hs ?_ hents
      intro e _ s4 st4 hs4 hstep4
      rw [except_bind_ok] at hstep4
      obtain ⟨s5, hins, hst4⟩ := hstep4
      simp only [pure, Except.pure, Except.ok.injEq] at hst4
      subst hst4
      exact hs4.install hins
    split at hst
    · rename_i hsome
      obtain ⟨call, hcall⟩ := Option.isSome_iff_exists.mp hsome
      rw [except_bind_ok] at hst
      obtain ⟨s6, hset, hst⟩ := hst
      simp only [pure, Except.pure, Except.ok.injEq] at hst
      subst hst
      rw [hcall] at hset
      exact hs'.setDefault hset
    · simp only [pure, Except.pure, Except.ok.injEq] at hst
      subst hst
      exact hs'
  · simp only [pure, Except.pure, Except.ok.injEq] at h
    subst h
    exact hi1

/-- A loop whose every pass succeeds does not fail. -/
theorem forIn_ne_error {l : List α} {b : β} {f : α → β → Except ε (ForInStep β)}
    (h : ∀ x b, ∃ s, f x b = .ok s) : forIn l b f ≠ .error e := by
  obtain ⟨b', hb'⟩ := forIn_total (l := l) (b := b) h
  rw [hb']
  exact fun h => nomatch h

/-- What a lookup selects: an installed entry's action, or the default. -/
theorem lookup_action {inst : Installed} {ref : TableRef} {keys : List Bits} {m : Match}
    {call : ActionCall} (h : inst.lookup ref keys = .ok m) (hc : m.action = some call) :
    (∃ e ∈ (inst.entries.getD ref #[]).toList, e.action = call) ∨
      inst.defaults.getD ref none = some call := by
  unfold Installed.lookup at h
  rw [except_bind_ok] at h
  obtain ⟨decl, -, h⟩ := h
  try simp only at h
  split at h
  · exact absurd h (by simp [bind, Except.bind, throw, throwThe, MonadExceptOf.throw])
  simp only [bind, Except.bind] at h
  rw [← Array.forIn_toList] at h
  split at h
  · cases h
  rename_i best hbest
  have hin : ∀ e, best = some e → e ∈ (inst.entries.getD ref #[]).toList := by
    refine forIn_inv (fun (b : Option Entry) => ∀ e, b = some e →
      e ∈ (inst.entries.getD ref #[]).toList) (by simp) ?_ hbest
    intro x hx b st hb hst
    try simp only at hst
    split at hst
    · split at hst
      · simp only [pure, Except.pure, Except.ok.injEq] at hst
        subst hst
        intro e he
        cases he
        exact hx
      · split at hst
        · simp only [pure, Except.pure, Except.ok.injEq] at hst
          subst hst
          intro e he
          cases he
          exact hx
        · simp only [pure, Except.pure, Except.ok.injEq] at hst
          subst hst
          exact hb
    · simp only [pure, Except.pure, Except.ok.injEq] at hst
      subst hst
      exact hb
  cases best with
  | none =>
    simp only [pure, Except.pure, Except.ok.injEq] at h
    subst h
    exact .inr hc
  | some e =>
    simp only [pure, Except.pure, Except.ok.injEq] at h
    subst h
    simp only [Option.some.injEq] at hc
    exact .inl ⟨e, hin e rfl, hc⟩

/-- A lookup in a table of the program does not fail. -/
theorem lookup_succeeds {n tn : String} {sc : BlockScope} {t : Table} {keys : List Bits}
    {inst : Installed} (G : Global) (hidx : inst.index = G.idx) (hsc : G.idx.scopes[n]? = some sc)
    (ht : sc.tables[tn]? = some t) (hlen : keys.length = t.keys.length) :
    ∃ m, inst.lookup (sc.block.name, t.name) keys = .ok m := by
  have hname : sc.block.name = n := by
    obtain ⟨hb, -⟩ := G.laws.scopeOrigin n sc hsc
    exact (G.laws.block n sc.block hb).2
  have htname : t.name = tn := (Build.ScopeLaws.tableOrigin (G.laws.scopeOrigin n sc hsc).2 tn t ht).2
  have htable : inst.table? (sc.block.name, t.name) = .ok t := by
    simp [Installed.table?, hidx, hname, hsc, htname, ht, pure, Except.pure]
  match h : inst.lookup (sc.block.name, t.name) keys with
  | .ok m => exact ⟨m, rfl⟩
  | .error e =>
    exfalso
    unfold Installed.lookup at h
    rw [htable] at h
    simp only [bind, Except.bind] at h
    have hne : (keys.length != t.keys.length) = false := by simp [hlen]
    simp only [hne, Bool.false_eq_true, ↓reduceIte] at h
    rw [← Array.forIn_toList] at h
    split at h
    · rename_i err hfor
      refine forIn_ne_error ?_ hfor
      intro x b
      split
      · split
        · exact ⟨_, rfl⟩
        · split <;> exact ⟨_, rfl⟩
      · exact ⟨_, rfl⟩
    · split at h <;> cases h

/-- A successful installation of a valid program's entries satisfies
`InstalledOk`: every lookup in a table of the program succeeds and selects
an action of the table's block with data of its parameters' types.

Premises: `Installed.build` succeeded on the program's index.

It does not establish that installation succeeds; a host's entries may be
rejected. -/
theorem build_installedOk (G : Global) (h : Installed.build G.idx host = .ok inst) :
    InstalledOk G.idx inst := by
  have hok := build_instOk G h
  intro n sc tn t keys hsc ht hlen
  obtain ⟨m, hm⟩ := lookup_succeeds G hok.1 hsc ht hlen
  refine ⟨m, hm, fun call hcall => ?_⟩
  have hname : sc.block.name = n := by
    obtain ⟨hb, -⟩ := G.laws.scopeOrigin n sc hsc
    exact (G.laws.block n sc.block hb).2
  have hat : ActionAt G.idx (sc.block.name, t.name) call := by
    rcases lookup_action hm hcall with ⟨e, he, rfl⟩ | hd
    · exact hok.2.1 _ e he
    · exact hok.2.2 _ call hd
  exact hat sc (by simp [hname, hsc])

end P4bloIR.Validity
