import P4bloIR.Index
import Std.Data.HashMap.Lemmas
import Std.Data.HashSet.Lemmas

/-!
# What `Index.build` guarantees

`Index.build` is written with private helpers, so this module restates it
publicly as `Build.index`, word for word, and proves the two equal by `rfl`.
The laws below read the index's maps back into the program's lists: a
declaration found by name is one of the program's and carries that name,
program-level names are shared by one namespace, and a block's scope is
built from that block.

These are the only facts about `Index.build` that validity and progress
use. They do not state that the index is complete in every direction; each
law states the direction a later proof needs.
-/

namespace P4bloIR.Build

open Std (HashMap HashSet)

/-- `Index.add`, restated. -/
def add (table : HashMap String α) (name : String) (decl : α) (taken : HashSet String)
    (where_ : String) : Except String (HashMap String α × HashSet String) := do
  if name.isEmpty then throw s!"empty name in {where_}"
  if taken.contains name then throw s!"'{name}' declared twice in {where_}"
  pure (table.insert name decl, taken.insert name)

/-- `Index.addAll`, restated. -/
def addAll (table : HashMap String α) (decls : List α) (name : α → String)
    (taken : HashSet String) (where_ : String) :
    Except String (HashMap String α × HashSet String) :=
  decls.foldlM (fun (table, taken) d => add table (name d) d taken where_) (table, taken)

/-- One pass of `Index.buildScope`'s loop over a block's actions: add the
action's name, then index its parameters against the names taken so far. -/
def actionStep (where_ : String) (a : Action)
    (s : HashMap String Action × HashMap String (HashMap String Param) × HashSet String) :
    Except String (ForInStep
      (HashMap String Action × HashMap String (HashMap String Param) × HashSet String)) := do
  let (actions, taken) ← add s.1 a.name a s.2.2 where_
  let (params, _) ← addAll {} a.params Param.name taken s!"action '{a.name}' of {where_}"
  pure (.yield (actions, s.2.1.insert a.name params, taken))

/-- `Index.buildScope`, restated with its loop body named. -/
def scope (b : Block) (top : HashSet String) : Except String BlockScope := do
  let where_ := s!"block '{b.name}'"
  let (vars, taken) ← addAll {} (b.params.map VarDecl.param) VarDecl.name top where_
  let (vars, taken) ← addAll vars (b.locals.map VarDecl.var) VarDecl.name taken where_
  let (actions, actionParams, taken) ← forIn b.actions ({}, {}, taken) (actionStep where_)
  let (tables, taken') ← addAll {} b.tables Table.name taken where_
  let (states, _) ← addAll {} b.states State.name taken' where_
  pure { block := b, vars, actions, actionParams, tables, states }

/-- One pass of `Index.build`'s loop over the error names. -/
def errorStep (x : String × Nat) (errors : HashMap String Nat) :
    Except String (ForInStep (HashMap String Nat)) := do
  if x.1.isEmpty || errors.contains x.1 then throw s!"error '{x.1}' at {x.2}"
  pure (.yield (errors.insert x.1 x.2))

/-- One pass of `Index.build`'s loop over the blocks. -/
def scopeStep (top : HashSet String) (b : Block) (scopes : HashMap String BlockScope) :
    Except String (ForInStep (HashMap String BlockScope)) := do
  pure (.yield (scopes.insert b.name (← scope b top)))

/-- `Index.build`, restated with its loop bodies named. -/
def index (program : Program) : Except String Index := do
  let where_ := "program"
  let (headerTypes, top) ← addAll {} program.headerTypes HeaderType.name {} where_
  let (structTypes, top) ← addAll {} program.structTypes StructType.name top where_
  let (enumTypes, top) ← addAll {} program.enumTypes EnumType.name top where_
  let (externTypes, top) ← addAll {} program.externTypes ExternType.name top where_
  let (externInstances, top) ← addAll {} program.externInstances ExternInstance.name top where_
  let (blocks, top) ← addAll {} program.blocks Block.name top where_
  let errors ← forIn program.errors.zipIdx {} errorStep
  let scopes ← forIn program.blocks {} (scopeStep top)
  pure { program, headerTypes, structTypes, enumTypes, externTypes, externInstances, blocks,
         scopes, programNames := top, errors }

/-- The restatement is the definition itself. -/
theorem index_eq (p : Program) : Index.build p = index p := rfl

-- ---------------------------------------------------------------------------
-- addAll
-- ---------------------------------------------------------------------------

section addAll

variable {α : Type} {name : α → String} {w : String}

theorem add_ok {t t' : HashMap String α} {taken taken' : HashSet String}
    (h : add t n d taken w = .ok (t', taken')) :
    n ∉ taken ∧ t' = t.insert n d ∧ taken' = taken.insert n := by
  unfold add at h
  by_cases he : n.isEmpty = true
  · simp [he] at h; cases h
  · by_cases hc : taken.contains n = true
    · simp [he, hc] at h; cases h
    · simp [he, hc] at h
      obtain ⟨rfl, rfl⟩ := h
      exact ⟨fun hm => hc (Std.HashSet.mem_iff_contains.mp hm), rfl, rfl⟩

/-- Everything `addAll` learns about the table and the taken names. -/
structure AddAll (t : HashMap String α) (ds : List α) (name : α → String)
    (taken : HashSet String) (t' : HashMap String α) (taken' : HashSet String) : Prop where
  /-- An entry is old or one of the declarations, under its own name. -/
  origin : ∀ k d, t'[k]? = some d → t[k]? = some d ∨ (d ∈ ds ∧ name d = k)
  /-- A name already taken keeps its entry. -/
  keep : ∀ k, k ∈ taken → t'[k]? = t[k]?
  /-- Taken names stay taken. -/
  grow : ∀ k, k ∈ taken → k ∈ taken'
  /-- Every declaration's name is taken afterwards. -/
  covers : ∀ d ∈ ds, name d ∈ taken'
  /-- Every declaration is found under its name. -/
  found : ∀ d ∈ ds, t'[name d]? = some d
  /-- No declaration reused a name taken before. -/
  fresh : ∀ d ∈ ds, name d ∉ taken
  /-- The declarations' names are distinct. -/
  nodup : (ds.map name).Nodup

theorem addAll_ok {t t' : HashMap String α} {taken taken' : HashSet String} {ds : List α}
    (h : addAll t ds name taken w = .ok (t', taken')) : AddAll t ds name taken t' taken' := by
  induction ds generalizing t taken with
  | nil =>
    unfold addAll at h
    rw [List.foldlM_nil] at h
    cases h
    exact ⟨fun _ _ h => .inl h, fun _ _ => rfl, fun _ h => h, by simp, by simp, by simp, by simp⟩
  | cons d ds ih =>
    unfold addAll at h
    simp only [List.foldlM_cons] at h
    cases hadd : add t (name d) d taken w with
    | error e => simp [hadd, bind, Except.bind] at h
    | ok r =>
      obtain ⟨t1, taken1⟩ := r
      simp only [hadd, bind, Except.bind] at h
      obtain ⟨hn, rfl, rfl⟩ := add_ok hadd
      have r := ih (show addAll _ ds name _ w = _ from h)
      refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
      · intro k x hx
        rcases r.origin k x hx with hx | ⟨hm, hk⟩
        · rw [Std.HashMap.getElem?_insert] at hx
          split at hx
          · cases hx; right; exact ⟨by simp, by simp_all⟩
          · exact .inl hx
        · exact .inr ⟨List.mem_cons_of_mem _ hm, hk⟩
      · intro k hk
        have hk1 : k ∈ taken.insert (name d) := Std.HashSet.mem_insert.mpr (.inr hk)
        rw [r.keep k hk1, Std.HashMap.getElem?_insert]
        have : (name d == k) = false := by
          simp only [beq_eq_false_iff_ne]; rintro rfl; exact hn hk
        simp [this]
      · intro k hk; exact r.grow k (Std.HashSet.mem_insert.mpr (.inr hk))
      · intro x hx
        rcases List.mem_cons.mp hx with rfl | hx
        · exact r.grow _ (Std.HashSet.mem_insert.mpr (.inl (by simp)))
        · exact r.covers x hx
      · intro x hx
        rcases List.mem_cons.mp hx with rfl | hx
        · rw [r.keep _ (Std.HashSet.mem_insert.mpr (.inl (by simp)))]; simp
        · exact r.found x hx
      · intro x hx
        rcases List.mem_cons.mp hx with rfl | hx
        · exact hn
        · intro hin; exact r.fresh x hx (Std.HashSet.mem_insert.mpr (.inr hin))
      · simp only [List.map_cons, List.nodup_cons]
        refine ⟨?_, r.nodup⟩
        intro hm
        obtain ⟨x, hx, hxn⟩ := List.mem_map.mp hm
        exact r.fresh x hx (Std.HashSet.mem_insert.mpr (.inl (by simp [hxn])))

end addAll

-- ---------------------------------------------------------------------------
-- The loops
-- ---------------------------------------------------------------------------

theorem actionLoop_ok {acts : List Action}
    {s s' : HashMap String Action × HashMap String (HashMap String Param) × HashSet String}
    (h : forIn acts s (actionStep w) = .ok s') :
    (∀ (x : String) (a : Action), s'.1[x]? = some a → s.1[x]? = some a ∨ (a ∈ acts ∧ a.name = x)) ∧
    (∀ k : String, k ∈ s.2.2 → k ∈ s'.2.2) ∧
    (∀ a ∈ acts, ∃ tk : HashSet String, (∀ k : String, k ∈ s.2.2 → k ∈ tk) ∧
      ∃ w' r, addAll (∅ : HashMap String Param) a.params Param.name tk w' = .ok r) := by
  induction acts generalizing s with
  | nil =>
    simp only [List.forIn_nil, pure, Except.pure, Except.ok.injEq] at h
    subst h
    exact ⟨fun _ _ h => .inl h, fun _ h => h, by simp⟩
  | cons a as ih =>
    simp only [List.forIn_cons] at h
    obtain ⟨actions, aps, taken⟩ := s
    cases hadd : add actions a.name a taken w with
    | error e => simp [actionStep, hadd, bind, Except.bind] at h
    | ok r1 =>
      obtain ⟨actions1, taken1⟩ := r1
      obtain ⟨hn, rfl, rfl⟩ := add_ok hadd
      cases hps : addAll (∅ : HashMap String Param) a.params Param.name (taken.insert a.name)
          s!"action '{a.name}' of {w}" with
      | error e => simp [actionStep, hadd, hps, bind, Except.bind] at h
      | ok r2 =>
        simp only [actionStep, hadd, hps, bind, Except.bind, pure, Except.pure] at h
        obtain ⟨hA, hT, hP⟩ := ih h
        refine ⟨?_, ?_, ?_⟩
        · intro x b hb
          rcases hA x b hb with hb | ⟨hm, hx⟩
          · simp only [Std.HashMap.getElem?_insert] at hb
            split at hb
            · cases hb; right; exact ⟨by simp, by simp_all⟩
            · exact .inl hb
          · exact .inr ⟨List.mem_cons_of_mem _ hm, hx⟩
        · intro k hk; exact hT k (Std.HashSet.mem_insert.mpr (.inr hk))
        · intro b hb
          rcases List.mem_cons.mp hb with rfl | hb
          · exact ⟨_, fun k hk => Std.HashSet.mem_insert.mpr (.inr hk), _, _, hps⟩
          · obtain ⟨tk, htk, rest⟩ := hP b hb
            exact ⟨tk, fun k hk => htk k (Std.HashSet.mem_insert.mpr (.inr hk)), rest⟩

theorem scopeLoop_ok {bs : List Block} {s s' : HashMap String BlockScope}
    (h : forIn bs s (scopeStep top) = .ok s') :
    (∀ (n : String) (sc : BlockScope), s'[n]? = some sc →
      s[n]? = some sc ∨ ∃ b ∈ bs, b.name = n ∧ scope b top = .ok sc) ∧
    (∀ b ∈ bs, s'[b.name]? ≠ none) ∧ (∀ n : String, s[n]? ≠ none → s'[n]? ≠ none) := by
  induction bs generalizing s with
  | nil =>
    simp only [List.forIn_nil, pure, Except.pure, Except.ok.injEq] at h
    subst h
    exact ⟨fun _ _ h => .inl h, by simp, fun _ h => h⟩
  | cons b bs ih =>
    simp only [List.forIn_cons] at h
    cases hs : scope b top with
    | error e => simp [scopeStep, hs, bind, Except.bind] at h
    | ok sc =>
      simp only [scopeStep, hs, bind, Except.bind, pure, Except.pure] at h
      obtain ⟨hO, hF, hK⟩ := ih h
      refine ⟨?_, ?_, ?_⟩
      · intro n x hx
        rcases hO n x hx with hx | ⟨b', hb', hn, hsc⟩
        · simp only [Std.HashMap.getElem?_insert] at hx
          split at hx
          · cases hx; right; exact ⟨b, by simp, by simp_all, hs⟩
          · exact .inl hx
        · exact .inr ⟨b', List.mem_cons_of_mem _ hb', hn, hsc⟩
      · intro b' hb'
        rcases List.mem_cons.mp hb' with rfl | hb'
        · exact hK _ (by simp)
        · exact hF b' hb'
      · intro n hn
        apply hK
        simp only [Std.HashMap.getElem?_insert]
        split <;> simp_all

-- ---------------------------------------------------------------------------
-- A block's scope
-- ---------------------------------------------------------------------------

/-- What a block's scope holds, read back into the block. -/
structure ScopeLaws (b : Block) (sc : BlockScope) : Prop where
  block : sc.block = b
  /-- A variable is one of the block's params or locals, under its name. -/
  varOrigin : ∀ (x : String) (d : VarDecl), sc.vars[x]? = some d →
    d.name = x ∧ ((∃ p ∈ b.params, d = .param p) ∨ (∃ v ∈ b.locals, d = .var v))
  /-- Every param is found under its name. -/
  paramFound : ∀ p ∈ b.params, sc.vars[p.name]? = some (.param p)
  actionOrigin : ∀ (x : String) (a : Action), sc.actions[x]? = some a → a ∈ b.actions ∧ a.name = x
  /-- An action's params have distinct names, none of them a variable's. -/
  actionParams : ∀ a ∈ b.actions,
    (a.params.map Param.name).Nodup ∧ ∀ q ∈ a.params, sc.vars[q.name]? = none
  tableOrigin : ∀ (x : String) (t : Table), sc.tables[x]? = some t → t ∈ b.tables ∧ t.name = x
  stateOrigin : ∀ (x : String) (st : State), sc.states[x]? = some st → st ∈ b.states ∧ st.name = x

theorem scope_ok (h : scope b top = .ok sc) : ScopeLaws b sc := by
  unfold scope at h
  simp only [bind, Except.bind] at h
  split at h
  · cases h
  rename_i r1 h1
  obtain ⟨vars1, taken1⟩ := r1
  simp only at h
  split at h
  · cases h
  rename_i r2 h2
  obtain ⟨vars2, taken2⟩ := r2
  simp only at h
  split at h
  · cases h
  rename_i r3 h3
  obtain ⟨actions, aps, taken3⟩ := r3
  simp only at h
  split at h
  · cases h
  rename_i r4 h4
  obtain ⟨tables, taken4⟩ := r4
  simp only at h
  split at h
  · cases h
  rename_i r5 h5
  obtain ⟨states, taken5⟩ := r5
  simp only [pure, Except.pure, Except.ok.injEq] at h
  subst h
  have A1 := addAll_ok h1
  have A2 := addAll_ok h2
  obtain ⟨L1, L2, L3⟩ := actionLoop_ok h3
  have A4 := addAll_ok h4
  have A5 := addAll_ok h5
  -- every variable name is taken after the locals
  have varTaken : ∀ (k : String) (d : VarDecl), vars2[k]? = some d → k ∈ taken2 := by
    intro k d hk
    rcases A2.origin k d hk with hk | ⟨hm, rfl⟩
    · rcases A1.origin k d hk with hk | ⟨hm, rfl⟩
      · simp at hk
      · exact A2.grow _ (A1.covers d hm)
    · exact A2.covers d hm
  refine ⟨rfl, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro x d hx
    rcases A2.origin x d hx with hx | ⟨hm, rfl⟩
    · rcases A1.origin x d hx with hx | ⟨hm, rfl⟩
      · simp at hx
      · obtain ⟨p, hp, rfl⟩ := List.mem_map.mp hm
        exact ⟨rfl, .inl ⟨p, hp, rfl⟩⟩
    · obtain ⟨v, hv, rfl⟩ := List.mem_map.mp hm
      exact ⟨rfl, .inr ⟨v, hv, rfl⟩⟩
  · intro p hp
    have hm : VarDecl.param p ∈ b.params.map VarDecl.param := List.mem_map_of_mem hp
    show vars2[(VarDecl.param p).name]? = _
    rw [A2.keep _ (A1.covers _ hm)]
    exact A1.found _ hm
  · intro x a hx
    rcases L1 x a hx with hx | h
    · simp at hx
    · exact h
  · intro a ha
    obtain ⟨tk, htk, w', r, hr⟩ := L3 a ha
    have R := addAll_ok hr
    refine ⟨R.nodup, fun q hq => ?_⟩
    cases hv : vars2[q.name]? with
    | none => rfl
    | some d => exact absurd (htk _ (varTaken _ _ hv)) (R.fresh q hq)
  · intro x t hx
    rcases A4.origin x t hx with hx | h
    · simp at hx
    · exact h
  · intro x st hx
    rcases A5.origin x st hx with hx | h
    · simp at hx
    · exact h

-- ---------------------------------------------------------------------------
-- The index
-- ---------------------------------------------------------------------------

/-- What the index holds, read back into the program. -/
structure IndexLaws (p : Program) (idx : Index) : Prop where
  program : idx.program = p
  header : ∀ (n : String) (h : HeaderType), idx.headerTypes[n]? = some h → h ∈ p.headerTypes ∧ h.name = n
  struct_ : ∀ (n : String) (s : StructType), idx.structTypes[n]? = some s → s ∈ p.structTypes ∧ s.name = n
  enum : ∀ (n : String) (e : EnumType), idx.enumTypes[n]? = some e → e ∈ p.enumTypes ∧ e.name = n
  externType : ∀ (n : String) (e : ExternType), idx.externTypes[n]? = some e → e ∈ p.externTypes ∧ e.name = n
  externInstance : ∀ (n : String) (e : ExternInstance), idx.externInstances[n]? = some e →
    e ∈ p.externInstances ∧ e.name = n
  block : ∀ (n : String) (b : Block), idx.blocks[n]? = some b → b ∈ p.blocks ∧ b.name = n
  /-- Program-level names share one namespace: no name is both a header and
  a struct type. -/
  headerNotStruct : ∀ n : String, idx.headerTypes[n]? ≠ none → idx.structTypes[n]? = none
  blockFound : ∀ b ∈ p.blocks, idx.blocks[b.name]? = some b
  /-- Every indexed block has its scope, built from it. -/
  scope : ∀ (n : String) (b : Block), idx.blocks[n]? = some b → ∃ sc, idx.scopes[n]? = some sc ∧ ScopeLaws b sc
  /-- Every scope is an indexed block's. -/
  scopeOrigin : ∀ (n : String) (sc : BlockScope), idx.scopes[n]? = some sc →
    idx.blocks[n]? = some sc.block ∧ ScopeLaws sc.block sc

theorem index_ok (h : index p = .ok idx) : IndexLaws p idx := by
  unfold index at h
  simp only [bind, Except.bind] at h
  split at h
  · cases h
  rename_i r1 h1
  obtain ⟨hs, top1⟩ := r1
  simp only at h
  split at h
  · cases h
  rename_i r2 h2
  obtain ⟨ss, top2⟩ := r2
  simp only at h
  split at h
  · cases h
  rename_i r3 h3
  obtain ⟨es, top3⟩ := r3
  simp only at h
  split at h
  · cases h
  rename_i r4 h4
  obtain ⟨xts, top4⟩ := r4
  simp only at h
  split at h
  · cases h
  rename_i r5 h5
  obtain ⟨xis, top5⟩ := r5
  simp only at h
  split at h
  · cases h
  rename_i r6 h6
  obtain ⟨bs, top6⟩ := r6
  simp only at h
  split at h
  · cases h
  split at h
  · cases h
  rename_i scopes h8
  simp only [pure, Except.pure, Except.ok.injEq] at h
  subst h
  have A1 := addAll_ok h1
  have A2 := addAll_ok h2
  have A3 := addAll_ok h3
  have A4 := addAll_ok h4
  have A5 := addAll_ok h5
  have A6 := addAll_ok h6
  obtain ⟨S1, S2, _⟩ := scopeLoop_ok h8
  have origin {α : Type} {ds : List α} {nm : α → String} {tk tk'}
      {t'} (A : AddAll (∅ : HashMap String α) ds nm tk t' tk') :
      ∀ (n : String) (x : α), t'[n]? = some x → x ∈ ds ∧ nm x = n := by
    intro n x hx
    rcases A.origin n x hx with hx | h
    · simp at hx
    · exact h
  have blockScope : ∀ (n : String) (b : Block), bs[n]? = some b → ∃ sc, scopes[n]? = some sc ∧ ScopeLaws b sc := by
    intro n b hb
    obtain ⟨hmem, rfl⟩ := origin A6 n b hb
    cases hsc : scopes[b.name]? with
    | none => exact absurd hsc (S2 b hmem)
    | some sc =>
      rcases S1 _ sc hsc with hx | ⟨b0, hb0, hn, hscope⟩
      · simp at hx
      · have : b0 = b := by
          have := A6.found b0 hb0
          rw [hn, hb] at this
          exact (Option.some.inj this).symm
        subst this
        exact ⟨sc, rfl, scope_ok hscope⟩
  refine ⟨rfl, origin A1, origin A2, origin A3, origin A4, origin A5, origin A6, ?_,
    A6.found, blockScope, ?_⟩
  · intro n hn
    cases hsn : ss[n]? with
    | none => rfl
    | some s =>
      exfalso
      obtain ⟨hm, rfl⟩ := origin A2 _ _ hsn
      apply A2.fresh s hm
      cases hh : hs[s.name]? with
      | none => exact absurd hh hn
      | some x =>
        obtain ⟨hx, hxn⟩ := origin A1 _ _ hh
        rw [← hxn]
        exact A1.covers x hx
  · intro n sc hsc
    rcases S1 n sc hsc with hx | ⟨b, hb, rfl, hscope⟩
    · simp at hx
    · have L := scope_ok hscope
      rw [L.block]
      exact ⟨A6.found b hb, L⟩

/-- `IndexLaws` for the real `Index.build`. -/
theorem build_ok (h : Index.build p = .ok idx) : IndexLaws p idx :=
  index_ok (by rw [← index_eq]; exact h)

end P4bloIR.Build
