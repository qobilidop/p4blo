import P4bloIR.Env
import Std.Data.HashMap.Lemmas

/-! Exact initialization by the production `Frame.forBlock` loop. Scope lookup
and successful zeroing of every scope declaration are explicit premises. -/

namespace P4bloIR.Frame

open Std (HashMap)

private theorem initialize_list (index : Index) (zeros : String → Value)
    (decls : List (String × VarDecl))
    (hz : ∀ name decl, (name, decl) ∈ decls → Value.zero decl.type index = .ok (zeros name))
    (vars : HashMap String Value) :
    ∃ result, (forIn decls vars fun (name, decl) vars => do
      pure (.yield (vars.insert name (← Value.zero decl.type index)))) =
        (Except.ok result : Except String (HashMap String Value)) ∧
      ∀ name, result[name]? =
        if name ∈ decls.map Prod.fst then some (zeros name) else vars[name]? := by
  classical
  induction decls generalizing vars with
  | nil => exact ⟨vars, rfl, by simp⟩
  | cons entry rest ih =>
    obtain ⟨name, decl⟩ := entry
    obtain ⟨result, hr, hv⟩ := ih
      (fun key d h => hz key d (List.mem_cons_of_mem _ h))
      (vars.insert name (zeros name))
    refine ⟨result, ?_, ?_⟩
    · simp [hz name decl (by simp)]
      simp at hr
      exact hr
    · intro key
      rw [hv, Std.HashMap.getElem?_insert]
      by_cases he : name = key
      · subst key
        simp
      · simp [List.map_cons, he, Ne.symm he]

/-- Exact scope and storage, including absent names, with no action overlay.
The requested block need not equal the block stored in the selected scope. -/
theorem forBlock_correct (index : Index) (block : Block) (scope : BlockScope)
    (hs : index.scopes[block.name]? = some scope) (zeros : String → Value)
    (hz : ∀ (name : String) (decl : VarDecl), scope.vars[name]? = some decl →
      Value.zero decl.type index = .ok (zeros name)) :
    ∃ frame, forBlock index block = .ok frame ∧ frame.scope = scope ∧
      frame.action = none ∧ frame.actionVars = none ∧
      ∀ name, frame.vars[name]? = (scope.vars[name]?).map (fun _ => zeros name) := by
  obtain ⟨vars, hr, hv⟩ := initialize_list index zeros scope.vars.toList
    (fun name decl h => hz name decl (Std.HashMap.mem_toList_iff_getElem?_eq_some.mp h)) {}
  refine ⟨{ scope, vars }, ?_, rfl, rfl, rfl, ?_⟩
  · simp at hr
    simp [forBlock, hs, hr]
    rfl
  · intro name
    rw [hv]
    have hm : name ∈ scope.vars.toList.map Prod.fst ↔ ∃ decl, scope.vars[name]? = some decl := by
      simp only [List.mem_map, Prod.exists, Std.HashMap.mem_toList_iff_getElem?_eq_some]
      constructor
      · rintro ⟨key, decl, hd, rfl⟩
        exact ⟨decl, hd⟩
      · rintro ⟨decl, hd⟩
        exact ⟨name, decl, hd, rfl⟩
    cases hd : scope.vars[name]? with
    | none =>
      have hn : ¬ name ∈ scope.vars.toList.map Prod.fst := by simp only [hm, hd]; simp
      simp only [hn, ↓reduceIte, Std.HashMap.getElem?_empty, Option.map_none]
    | some decl =>
      have hy : name ∈ scope.vars.toList.map Prod.fst := hm.mpr ⟨decl, hd⟩
      simp only [hy, ↓reduceIte, Option.map_some]

/-- Successful zeroing is required for every actual map entry, including any
declarations outside a user model. No global validity or fuel bound is inferred. -/
theorem forBlock_initialized (index : Index) (block : Block) (scope : BlockScope)
    (hs : index.scopes[block.name]? = some scope)
    (hz : ∀ (name : String) (decl : VarDecl), scope.vars[name]? = some decl →
      ∃ value, Value.zero decl.type index = .ok value) :
    ∃ frame, forBlock index block = .ok frame ∧ frame.scope = scope ∧
      frame.action = none ∧ frame.actionVars = none ∧
      ∀ (name : String), frame.vars[name]? =
        (scope.vars[name]?).bind (fun decl => (Value.zero decl.type index).toOption) := by
  let zeros := fun (name : String) => ((scope.vars[name]?).bind
    (fun decl => (Value.zero decl.type index).toOption)).getD default
  have hz' : ∀ (name : String) (decl : VarDecl), scope.vars[name]? = some decl →
      Value.zero decl.type index = .ok (zeros name) := by
    intro name decl hd
    obtain ⟨value, hv⟩ := hz name decl hd
    simp [zeros, hd, hv, Except.toOption]
  obtain ⟨frame, hf, hscope, ha, hav, hvars⟩ := forBlock_correct index block scope hs zeros hz'
  refine ⟨frame, hf, hscope, ha, hav, ?_⟩
  intro name
  rw [hvars]
  cases hd : scope.vars[name]? with
  | none => rfl
  | some decl =>
    obtain ⟨value, hv⟩ := hz name decl hd
    simp [zeros, hd, hv, Except.toOption]

theorem forBlock_missing (index : Index) (block : Block)
    (hs : index.scopes[block.name]? = none) :
    forBlock index block = .error s!"unknown block '{block.name}'" := by
  simp [forBlock, hs]
  rfl

end P4bloIR.Frame
