import P4bloIR.Validity.ValueLaws

/-!
# Contexts, types and frames

What a well-formed context knows: its program's index laws, the types it
sees are well formed, and a frame of it reads and writes every variable
the context sees at its declared type.
-/

namespace P4bloIR.Validity

open Std (HashMap)

namespace Global

variable (G : Global)

/-- The index laws of the program. -/
theorem laws : Build.IndexLaws G.p G.idx := Build.build_ok G.valid.index

/-- A declared header's fields are scalar. -/
theorem headerScalar {n : String} {hd : HeaderType} (hh : G.idx.headerTypes[n]? = some hd) :
    ∀ fl ∈ hd.fields, scalarField fl.type = true :=
  (G.valid.headers hd (G.laws.header n hd hh).1).2

/-- A struct is not a header. -/
theorem structNotHeader {n : String} {s : StructType} (hs : G.idx.structTypes[n]? = some s) : G.idx.headerTypes[n]? = none := by
  cases hh : G.idx.headerTypes[n]? with
  | none => rfl
  | some h => exact absurd hs (by rw [G.laws.headerNotStruct n (by simp [hh])]; simp)

/-- Every indexed block is a well-formed context. -/
theorem blockCtx {n : String} {b : Block} (hb : G.idx.blocks[n]? = some b) (hk : b.kind = G.kind) :
    ∃ sc, G.idx.scopes[b.name]? = some sc ∧ sc.block = b ∧
      CtxOk G { index := G.idx, scope := sc, kind := G.kind } := by
  obtain ⟨hmem, rfl⟩ := G.laws.block n b hb
  obtain ⟨sc, hsc, hl⟩ := G.laws.scope _ b hb
  obtain ⟨sc', hsc', ht⟩ := G.valid.blocks b hmem
  rw [hsc] at hsc'
  cases hsc'
  refine ⟨sc, hsc, hl.block, ?_⟩
  refine ⟨rfl, rfl, by rw [hl.block]; exact hb, by rw [hl.block]; exact hsc,
    by rw [hl.block]; exact hl, by rw [hl.block]; exact ht,
    by rw [hl.block]; exact hk, ?_⟩
  simp

end Global

theorem binaryType_tyOk (h : binaryType op a b = some t) (ha : TyOk idx a) : TyOk idx t := by
  cases op <;> cases a <;> cases b <;> simp only [binaryType] at h <;> (try split at h) <;>
    (try simp only [Option.some.injEq, reduceCtorEq] at h) <;> (try subst h) <;>
    first
    | exact ha
    | exact tyOk_boolean
    | exact tyOk_bits (by have := tyOk_bits_pos ha; omega)
    | exact absurd h (by simp)

namespace CtxOk

variable {G : Global} {c : Ctx} (hc : CtxOk G c)
include hc

/-- The context with a different action of the same block. -/
theorem withAction (ha : a ∈ c.scope.block.actions) : CtxOk G { c with action := some a } :=
  { hc with action := fun a' h => by cases h; exact ha }

theorem withoutAction : CtxOk G { c with action := none } :=
  { hc with action := fun _ h => by cases h }

/-- The declared type of a variable the context sees is well formed. -/
theorem varTy (hd : c.var? x = some d) : TyOk G.idx d.type := by
  unfold Ctx.var? at hd
  split at hd
  · rename_i q hq
    cases hd
    obtain ⟨a, ha, hfind⟩ := Option.bind_eq_some_iff.mp hq
    have hmem := hc.action a ha
    exact (hc.typed.actions a hmem).2.1 q (List.mem_of_find?_eq_some hfind)
  · obtain ⟨_, hsrc⟩ := hc.laws.varOrigin x d hd
    rcases hsrc with ⟨q, hq, rfl⟩ | ⟨v, hv, rfl⟩
    · exact (hc.typed.params q hq).2
    · exact hc.typed.locals v hv

theorem litTy (h : LitTyped c.index lit t) : TyOk G.idx t := by
  rw [hc.index] at h
  cases h with
  | bits hw _ => exact tyOk_bits hw
  | boolean => exact tyOk_boolean
  | enumMember he hm =>
    unfold TyOk
    obtain ⟨k, hk⟩ : ∃ k, fuel G.idx = k + 1 := ⟨fuel G.idx - 1, by have := fuel_pos G.idx; omega⟩
    rw [hk]
    simp only [tyDeep, he, Bool.not_eq_true', List.isEmpty_eq_false_iff]
    exact List.ne_nil_of_mem hm
  | error _ => exact tyOk_error

/-- Every expression the context types has a well-formed type. -/
theorem exprTy (he : ExprTyped c e t) : TyOk G.idx t := by
  induction he with
  | literal h => exact hc.litTy h
  | var hd => exact hc.varTy hd
  | member _ hf ih => exact fieldType_tyOk ih (hc.index ▸ hf)
  | index _ _ ih _ => exact stack_header_tyOk ih
  | lastIndex _ _ _ => exact tyOk_bits (by decide)
  | not _ _ => exact tyOk_boolean
  | complement _ ih => exact ih
  | negate _ ih => exact ih
  | binary _ _ ht ihl _ => exact binaryType_tyOk ht ihl
  | cast _ hto _ _ => exact hc.index ▸ hto
  | slice _ _ _ _ => exact tyOk_bits (by omega)
  | isValid _ _ => exact tyOk_boolean
  | mux _ _ _ _ iha _ => exact iha
  | lookahead _ hty _ => exact hc.index ▸ hty

/-- Every lvalue the context types has a well-formed type. -/
theorem lvTy (hl : LvOk c lv t) : TyOk G.idx t := by
  induction hl with
  | var hd => exact hc.varTy hd
  | member _ hf ih => exact fieldType_tyOk ih (hc.index ▸ hf)
  | index _ _ ih => exact stack_header_tyOk ih

end CtxOk

-- ---------------------------------------------------------------------------
-- Frames
-- ---------------------------------------------------------------------------

theorem LitTyped.value (h : LitTyped idx lit t) : ValueHas idx (literalValue lit) t := by
  cases h <;> simp [literalValue, Literal.toValue, Bits.wrap]

/-- A variable the context sees reads as a value of its declared type. -/
theorem FrameOk.read (hf : FrameOk c f) (hd : c.var? x = some d) :
    ∃ v, f.read? x = some v ∧ ValueHas c.index v d.type := by
  have hl := hf.layer
  unfold Ctx.var? at hd
  split at hd
  · rename_i q hq
    cases hd
    obtain ⟨a, ha, hfind⟩ := Option.bind_eq_some_iff.mp hq
    rw [ha] at hl
    obtain ⟨m, hm, hall⟩ := hl
    have := hall x
    rw [hfind] at this
    obtain ⟨v, hv, ht⟩ := this
    exact ⟨v, by simp [Frame.read?, hm, hv], ht⟩
  · rename_i hnone
    obtain ⟨v, hv, ht⟩ := hf.vars x d hd
    refine ⟨v, ?_, ht⟩
    cases ha : c.action with
    | none =>
      rw [ha] at hl
      simp [LayerOk] at hl
      simp [Frame.read?, hl, hv]
    | some a =>
      rw [ha] at hl hnone
      obtain ⟨m, hm, hall⟩ := hl
      have hfind : a.params.find? (·.name == x) = none := by simpa using hnone
      have := hall x
      rw [hfind] at this
      simp [Frame.read?, hm, this, hv]

/-- Writing a value of a variable's declared type keeps the frame typed. -/
theorem FrameOk.write (hf : FrameOk c f) (hd : c.var? x = some d)
    (hv : ValueHas c.index v d.type) :
    ∃ f', f.write? x v = some f' ∧ FrameOk c f' := by
  have hl := hf.layer
  unfold Ctx.var? at hd
  split at hd
  · rename_i q hq
    cases hd
    obtain ⟨a, ha, hfind⟩ := Option.bind_eq_some_iff.mp hq
    rw [ha] at hl
    obtain ⟨m, hm, hall⟩ := hl
    have hx := hall x
    rw [hfind] at hx
    obtain ⟨v0, hv0, _⟩ := hx
    have hc : m.contains x = true := by
      rw [Std.HashMap.contains_eq_isSome_getElem?, hv0]; rfl
    refine ⟨{ f with actionVars := some (m.insert x v) }, by simp [Frame.write?, hm, hc], ?_⟩
    refine ⟨hf.scope, hf.vars, ?_⟩
    rw [ha]
    refine ⟨_, rfl, fun y => ?_⟩
    by_cases hxy : x = y
    · subst hxy
      rw [hfind]
      exact ⟨v, by simp, hv⟩
    · split <;> rename_i heq <;> have hy := hall y <;> rw [heq] at hy <;>
        simpa [Std.HashMap.getElem?_insert, hxy] using hy
  · rename_i hnone
    obtain ⟨v0, hv0, _⟩ := hf.vars x d hd
    have hcv : f.vars.contains x = true := by
      rw [Std.HashMap.contains_eq_isSome_getElem?, hv0]; rfl
    have newVars : ∀ (y : String) (d' : VarDecl), c.scope.vars[y]? = some d' →
        ∃ w, (f.vars.insert x v)[y]? = some w ∧ ValueHas c.index w d'.type := by
      intro y d' hy
      by_cases hxy : x = y
      · subst hxy
        rw [hd] at hy
        cases hy
        exact ⟨v, by simp, hv⟩
      · simpa [Std.HashMap.getElem?_insert, hxy] using hf.vars y d' hy
    cases hact : f.actionVars with
    | none =>
      refine ⟨{ f with vars := f.vars.insert x v }, by simp [Frame.write?, hact, hcv], hf.scope,
        newVars, ?_⟩
      simpa [hact] using hf.layer
    | some m =>
      cases ha : c.action with
      | none =>
        have := hf.layer
        rw [ha] at this
        simp [LayerOk, hact] at this
      | some a =>
        rw [ha] at hl hnone
        obtain ⟨m', hm', hall⟩ := hl
        rw [hact] at hm'
        cases hm'
        have hfind : a.params.find? (·.name == x) = none := by simpa using hnone
        have hx := hall x
        rw [hfind] at hx
        have hnc : m.contains x = false := by
          rw [Std.HashMap.contains_eq_isSome_getElem?, hx]; rfl
        refine ⟨{ f with vars := f.vars.insert x v }, by simp [Frame.write?, hact, hnc, hcv],
          hf.scope, newVars, ?_⟩
        have := hf.layer
        simpa [hact] using this

end P4bloIR.Validity
