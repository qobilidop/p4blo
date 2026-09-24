import P4blo.CallBodyEntry
import P4blo.CallInitializers

namespace P4blo.GuardedCallPrefix
open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements
open Fields FieldCommandExamples
open P4bloIR.PlainCallEntry

/-- The separately reviewed initializer really is the selected wrapper pair. -/
theorem initializers_eq : CallBodyEntry.initializers = CallInitializers.body := rfl

def body (suffix : List Stmt) : List Stmt :=
  CallInitializers.body ++ GuardedForwardPolicy.guardedForward.lower ++ suffix

theorem selected_body : body CallBodyEntry.observerSuffix = CallBodyEntry.body := rfl

/-- Permission/type evidence for actual locals, not inferred from map writes. -/
theorem locals_typed (suffix : List Stmt) :
    FieldTyping.BodyTyped (CallEntry.WithBody.index (body suffix))
      (CallEntry.WithBody.scope (body suffix)) CallInitializers.body :=
  CallInitializers.body_typed _ _ (by cbv) (by cbv)

/-- Actual call entry, control expansion, local assignments and guarded body,
stopping before arbitrary observer statements and captured caller return.
The arbitrary caller lookup/index premises remain explicit. -/
theorem source_prefix (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value) (suffix : List Stmt) (continuation : List Work)
    (hi : run.index = CallEntry.WithBody.index (body suffix))
    (hb : BlockFrame run.frame)
    (hh : run.frame.read? "source_hdr" = some hdr.toValue)
    (hm : run.frame.read? "source_meta" = some metaData.toValue)
    (hr : run.frame.read? "source_route" = some routeData.toValue)
    (ho : run.frame.read? "hdr" = some observer) :
    ∃ finalFrame,
      Steps { work := .block "RewriteBody" args :: continuation, run }
        { work := .statements suffix ::
            .blockReturn run.frame (CallEntry.WithBody.block (body suffix)).params args :: continuation,
          run := { run with frame := finalFrame } } ∧
      finalFrame.scope = CallEntry.WithBody.scope (body suffix) ∧
      BlockFrame finalFrame ∧
      FrameMatches (ForwardPolicy.restore (GuardedForwardPolicy.policy
        (ForwardPolicy.observe (CallInitializers.bodyStore hdr metaData routeData)))) finalFrame ∧
      finalFrame.read? "observer" = some observer ∧
      finalFrame.read? "unrelated" = some (.bits (Bits.wrap 8 165)) ∧
      modes.Agrees finalFrame.scope ∧
      FieldTyping.BodyTyped run.index finalFrame.scope CallInitializers.body ∧
      FieldTyping.BodyTyped run.index finalFrame.scope GuardedForwardPolicy.guardedForward.lower := by
  obtain ⟨zero, _, hs, heBlock, heSource, heObserver, heExtra, _, entry⟩ :=
    CallEntry.source_entry_with_body (body suffix) run hdr metaData routeData observer continuation hi hb hh hm hr ho
  let entered := { run with frame := boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer }
  let tail := .blockReturn run.frame (CallEntry.WithBody.block (body suffix)).params args :: continuation
  have expand : Steps
      { work := .runBlock (CallEntry.WithBody.block (body suffix)) :: tail, run := entered }
      { work := .statements (body suffix) :: tail, run := entered } := .next rfl .refl
  obtain ⟨initTrace, hstore, hextra, hcInit, _⟩ :=
    CallInitializers.source_steps entered hdr metaData routeData _
      (GuardedForwardPolicy.guardedForward.lower ++ suffix) tail heBlock heSource heExtra
  let ready := CallInitializers.finalRun entered
  have readyScope : ready.frame.scope = CallEntry.WithBody.scope (body suffix) := hs
  have readyBlock : BlockFrame ready.frame := hcInit.blockFrame heBlock
  have readyModes : modes.Agrees ready.frame.scope := by
    rw [readyScope]
    exact CallEntry.WithBody.modes_agree _
  have readyIndex : roots.IndexAgrees ready.index := by
    change roots.IndexAgrees run.index
    rw [hi]
    exact CallEntry.WithBody.roots_agree _
  obtain ⟨typed, final, authored, hfinal, changes, outside⟩ :=
    GuardedForwardPolicy.guardedForward.steps_prefix (CallInitializers.bodyStore hdr metaData routeData)
      ready suffix tail rootWF readyIndex readyModes hstore readyBlock
  have initializedTrace : Steps
      { work := .statements (body suffix) :: tail, run := entered }
      { work := .statements (GuardedForwardPolicy.guardedForward.lower ++ suffix) :: tail,
        run := ready } := by
    simpa [body, List.append_assoc] using initTrace
  have whole : Steps { work := .block "RewriteBody" args :: continuation, run }
      { work := .statements suffix :: tail, run := final } :=
    entry.trans (expand.trans (initializedTrace.trans authored))
  have finalRun : final = { run with frame := final.frame } := by
    obtain ⟨vars, h⟩ := changes
    rw [h]
    rfl
  have finalScope : final.frame.scope = CallEntry.WithBody.scope (body suffix) :=
    changes.scope.trans readyScope
  have finalBlock := changes.blockFrame readyBlock
  have preserved (name : String) (hn : name ∉ GuardedForwardPolicy.guardedForward.targets) :
      final.frame.read? name = ready.frame.read? name := by
    simpa [Frame.read?, finalBlock.2, readyBlock.2] using outside name hn
  have observerReady : ready.frame.read? "observer" = some observer := by
    simpa [ready, CallInitializers.finalRun, Frame.read?, heBlock.2,
      Std.HashMap.getElem?_insert, entered] using heObserver
  change FieldTyping.BodyTyped run.index ready.frame.scope _ at typed
  refine ⟨final.frame, ?_, finalScope, finalBlock,
    GuardedForwardPolicy.source_policy _ ▸ hfinal, ?_, ?_, ?_, ?_, ?_⟩
  · simpa only [← finalRun] using whole
  · exact (preserved "observer" (by decide)).trans observerReady
  · exact (preserved "unrelated" (by decide)).trans hextra
  · rw [finalScope]
    exact CallEntry.WithBody.modes_agree _
  · rw [finalScope, hi]
    exact locals_typed suffix
  · simpa only [changes.scope] using typed

end P4blo.GuardedCallPrefix
