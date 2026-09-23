import P4blo.CallEntryDeclarations

namespace P4blo.CallEntry
open Fields FieldCommandExamples
open P4bloIR.PlainCallEntry

/-- Independent source state at entry, before either local initializer runs. -/
def entryStore (hdr : Data headers) (metaData : Data metadata) (routeData : Data route) : Store roots :=
  .cons hdr (.cons metaData (.cons routeData (.cons (.scalar 0) .nil)))

/-- Actual entry with a source store and separately preserved observer. The
caller reads are premises; caller construction and argument validity are not
claimed. The entire arbitrary continuation is left pending. -/
theorem source_entry (run : P4bloIR.Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : P4bloIR.Value)
    (continuation : List P4bloIR.Execution.Work)
    (hi : run.index = CallEntry.index)
    (_callerBlockFrame : P4bloIR.ScalarStatements.BlockFrame run.frame)
    (hh : run.frame.read? "source_hdr" = some hdr.toValue)
    (hm : run.frame.read? "source_meta" = some metaData.toValue)
    (hr : run.frame.read? "source_route" = some routeData.toValue)
    (ho : run.frame.read? "hdr" = some observer) :
    ∃ zero, P4bloIR.Frame.forBlock CallEntry.index block = .ok zero ∧
      (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).scope = scope ∧
      P4bloIR.ScalarStatements.BlockFrame (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer) ∧
      FrameMatches (entryStore hdr metaData routeData)
        (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer) ∧
      (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).read? "observer" = some observer ∧
      (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).read? "unrelated" =
        some (.bits ⟨8, 0, by decide⟩) ∧
      (P4bloIR.Execution.dispatch (.block "RewriteBody" args)).run run =
        (.ok [.runBlock block, .blockReturn run.frame block.params args],
         { run with frame := boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer }) ∧
      P4bloIR.Execution.Steps { work := .block "RewriteBody" args :: continuation, run }
        { work := .runBlock block :: .blockReturn run.frame block.params args :: continuation,
          run := { run with frame := boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer } } := by
  obtain ⟨zero, hz, hs, hb, hsource, hv⟩ := initialized
  have hbound : P4bloIR.ScalarStatements.BlockFrame
      (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer) := hb
  refine ⟨zero, hz, hs, hbound, ?_, ?_, ?_, ?_, ?_⟩
  · intro shape root
    cases root with
    | here =>
      change (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).read? "hdr" = some hdr.toValue
      simp [P4bloIR.Frame.read?, boundFrame, hb.2, Std.HashMap.getElem_insert]
    | there root => cases root with
      | here =>
        change (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).read? "meta" = some metaData.toValue
        simp [P4bloIR.Frame.read?, boundFrame, hb.2, Std.HashMap.getElem_insert]
      | there root => cases root with
        | here =>
          change (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).read? "route" = some routeData.toValue
          simp [P4bloIR.Frame.read?, boundFrame, hb.2, Std.HashMap.getElem_insert]
        | there root => cases root with
          | here =>
            have hscratch := hsource (.there (.there (.there .here)))
            change zero.read? "scratch" = some (.bits ⟨8, 0, by decide⟩) at hscratch
            change (boundFrame zero hdr.toValue metaData.toValue routeData.toValue observer).read? "scratch" = some (.bits ⟨8, 0, by decide⟩)
            simpa [P4bloIR.Frame.read?, boundFrame, hb.2, Std.HashMap.getElem?_insert] using hscratch
          | there root => cases root
  · simp [P4bloIR.Frame.read?, boundFrame, hb.2]
  · have hunrelated : scope.vars["unrelated"]? = some (.var ⟨"unrelated", .bits 8⟩) := by cbv
    simp [P4bloIR.Frame.read?, boundFrame, hb.2, Std.HashMap.getElem?_insert,
      hv, hunrelated, P4bloIR.VarDecl.type, P4bloIR.Value.zero, P4bloIR.Value.zeroWith, Except.toOption]
    rfl
  · exact dispatch_entry run "RewriteBody" block zero hdr.toValue metaData.toValue routeData.toValue observer
      (by simpa [hi] using block_lookup) rfl (by simpa [hi] using hz) hh hm hr ho
  · exact entry_steps run "RewriteBody" block zero hdr.toValue metaData.toValue routeData.toValue observer continuation
      (by simpa [hi] using block_lookup) rfl (by simpa [hi] using hz) hh hm hr ho

end P4blo.CallEntry
