import P4blo.Fields

/-! Operational field writes while an action layer is installed.
Only the written block root must be unshadowed. These laws do not supply
action-aware source typing, permissions, or a new command evaluator. -/

namespace P4blo.Fields

theorem FrameMatches.set_unshadowed {store : Store roots} (hf : FrameMatches store frame)
    (hw : (roots.fields.map P4bloIR.Field.name).Nodup)
    (root : Slot roots shape) (value : Data shape)
    (hu : frame.actionVars.bind (·[root.name]?) = none) :
    FrameMatches (store.set root value)
      { frame with vars := frame.vars.insert root.name value.toValue } := by
  intro otherShape other
  rw [Record.get_set_value store root value other hw]
  have h := hf other
  simp only [P4bloIR.Frame.read?] at h ⊢
  by_cases he : other.name = root.name
  · simp [he, hu]
  · simpa [Std.HashMap.getElem?_insert, he, Ne.symm he] using h

theorem Ref.write_unshadowed (root : Slot roots shape) (path : Path shape t)
    (store : Store roots) (value : Scalar.Meaning t) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame)
    (hu : run.frame.actionVars.bind (·[root.name]?) = none) :
    (P4bloIR.writeLValue (Ref.mk root path).lvalue (Scalar.toValue value)).run run =
      (.ok (), { run with frame := { run.frame with vars := (run.frame.vars.insert root.name
        (path.set (store.get root) value).toValue) } }) := by
  have hr : (P4bloIR.readLValue (.var root.name)).run run =
      (.ok (store.get root).toValue, run) := by
    simp [P4bloIR.readLValue, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind, hf root]
  rw [Ref.lvalue, path.writeLValue (store.get root) value run (root.indexAgrees hi) hr]
  apply P4bloIR.ScalarStatements.writeVar_block_unshadowed run hu
  simpa [P4bloIR.Frame.read?, hu] using hf root

/-- Exact whole-Run block update; arbitrary unrelated action bindings remain.
Do not infer source permission merely because runtime storage accepts it. -/
theorem Ref.write_matches_unshadowed (ref : Ref roots t) (store : Store roots)
    (value : Scalar.Meaning t) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame)
    (hw : (roots.fields.map P4bloIR.Field.name).Nodup)
    (hu : run.frame.actionVars.bind (·[ref.rootName]?) = none) :
    ∃ final, (P4bloIR.writeLValue ref.lvalue (Scalar.toValue value)).run run = (.ok (), final) ∧
      FrameMatches (ref.set store value) final.frame ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars run final ∧
      P4bloIR.ScalarStatements.PreservesOutside [ref.rootName] run final := by
  cases ref with
  | mk root path =>
    refine ⟨_, Ref.write_unshadowed root path store value run hi hf hu,
      hf.set_unshadowed hw root _ hu, ⟨_, rfl⟩, ?_⟩
    intro name hn
    simp only [Ref.rootName, List.mem_singleton] at hn
    simp [Std.HashMap.getElem?_insert, Ne.symm hn]

end P4blo.Fields
