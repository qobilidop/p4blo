import P4blo.FieldPlaces
import P4blo.SourceZero
import P4bloIR.FrameInitialization

namespace P4blo.Fields

theorem Slot.zero_get (root : Slot roots shape) : roots.zero.get root = shape.zero := by
  induction root with
  | here => rfl
  | there root ih => exact ih

theorem Slot.zeroFuel_le (root : Slot roots shape) : shape.zeroFuel ≤ roots.zeroFuel := by
  induction root with
  | here => exact Nat.le_max_left _ _
  | there root ih => exact Nat.le_trans ih (Nat.le_max_right _ _)

/-- Every actual scope entry belongs to a modeled root. Declaration agreement
alone does not establish this: scopes may contain extra locals or parameters. -/
def Layout.Covers (roots : Layout) (scope : P4bloIR.BlockScope) : Prop :=
  ∀ (name : String) (decl : P4bloIR.VarDecl), scope.vars[name]? = some decl →
    ∃ shape, ∃ root : Slot roots shape, root.name = name

theorem Layout.Covers.absent (coverage : roots.Covers scope) (name : String)
    (hn : ∀ shape (root : Slot roots shape), root.name ≠ name) : scope.vars[name]? = none := by
  cases hd : scope.vars[name]? with
  | none => rfl
  | some decl =>
    obtain ⟨shape, root, hr⟩ := coverage name decl hd
    exact False.elim (hn shape root hr)

/-- Initialize the independent zero store through the actual IR frame loop.
Only unmodeled declarations need separate zeroability evidence; modeled roots
use exact declarations, nominal agreement and the explicit production budget. -/
theorem Layout.initialize (roots : Layout) (index : P4bloIR.Index)
    (block : P4bloIR.Block) (scope : P4bloIR.BlockScope)
    (hs : index.scopes[block.name]? = some scope) (hd : RootDeclares roots scope)
    (hi : roots.IndexAgrees index)
    (hf : roots.zeroFuel ≤ index.headerTypes.size + index.structTypes.size + 2)
    (extras : ∀ (name : String) (decl : P4bloIR.VarDecl), scope.vars[name]? = some decl →
      (∀ shape (root : Slot roots shape), root.name ≠ name) →
      ∃ value, P4bloIR.Value.zero decl.type index = .ok value) :
    ∃ frame, P4bloIR.Frame.forBlock index block = .ok frame ∧ frame.scope = scope ∧
      P4bloIR.ScalarStatements.BlockFrame frame ∧ FrameMatches roots.zero frame ∧
      ∀ (name : String), frame.vars[name]? =
        (scope.vars[name]?).bind (fun decl => (P4bloIR.Value.zero decl.type index).toOption) := by
  classical
  have zeros : ∀ (name : String) (decl : P4bloIR.VarDecl), scope.vars[name]? = some decl →
      ∃ value, P4bloIR.Value.zero decl.type index = .ok value := by
    intro name decl hdecl
    by_cases hroot : ∃ shape, ∃ root : Slot roots shape, root.name = name
    · obtain ⟨shape, root, rfl⟩ := hroot
      obtain ⟨actual, ha, _, ht⟩ := hd root
      have he : actual = decl := by simpa [P4bloIR.BlockScope.var?, hdecl] using ha.symm
      subst actual
      exact ⟨shape.zero.toValue, ht ▸ shape.zero_correct index (root.indexAgrees hi)
        (Nat.le_trans root.zeroFuel_le hf)⟩
    · exact extras name decl hdecl (by simpa using hroot)
  obtain ⟨frame, he, hscope, ha, hav, hv⟩ :=
    P4bloIR.Frame.forBlock_initialized index block scope hs zeros
  refine ⟨frame, he, hscope, ⟨ha, hav⟩, ?_, hv⟩
  intro shape root
  obtain ⟨decl, hdecl, _, ht⟩ := hd root
  have hz := shape.zero_correct index (root.indexAgrees hi) (Nat.le_trans root.zeroFuel_le hf)
  have hlookup : scope.vars[root.name]? = some decl := by
    simpa [P4bloIR.BlockScope.var?] using hdecl
  simp [P4bloIR.Frame.read?, hav, hv, hlookup, ht, hz, Except.toOption, root.zero_get]

theorem Modes.scope_covers (modes : Modes roots) : roots.Covers modes.scope := by
  intro name decl hd
  induction modes with
  | nil => simp [Modes.scope, Modes.declarations] at hd
  | @cons rest headName headShape mode modes ih =>
    simp only [Modes.scope, Modes.declarations, Std.HashMap.getElem?_insert] at hd
    split at hd
    next he =>
      exact ⟨headShape, .here, by simpa [Slot.name] using he⟩
    next _ =>
      obtain ⟨shape, root, hr⟩ := ih hd
      exact ⟨shape, .there root, hr⟩

/-- Fully modeled scopes discharge every entry, with no extra-variable premise. -/
theorem Modes.initialize (modes : Modes roots) (index : P4bloIR.Index) (block : P4bloIR.Block)
    (hs : index.scopes[block.name]? = some modes.scope) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index)
    (hf : roots.zeroFuel ≤ index.headerTypes.size + index.structTypes.size + 2) :
    ∃ frame, P4bloIR.Frame.forBlock index block = .ok frame ∧ frame.scope = modes.scope ∧
      P4bloIR.ScalarStatements.BlockFrame frame ∧ FrameMatches roots.zero frame ∧
      ∀ (name : String), frame.vars[name]? =
        (modes.scope.vars[name]?).bind (fun decl => (P4bloIR.Value.zero decl.type index).toOption) := by
  apply roots.initialize index block modes.scope hs (Modes.Agrees.declares (modes.scope_agrees hw)) hi hf
  intro name decl hd hn
  obtain ⟨shape, root, hr⟩ := modes.scope_covers name decl hd
  exact False.elim (hn shape root hr)

end P4blo.Fields
