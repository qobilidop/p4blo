import P4blo.GuardedCallPrefix
import P4bloIR.PlainCallReturn

/-! One complete normal, already-parsed and route-selected control call.
There are no observer assignments; the existing observer argument passes
through unchanged. Caller construction and pending continuation execution
remain explicit boundaries, not whole-program claims. -/

namespace P4blo.GuardedControlCall
open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements
open Fields FieldCommandExamples P4bloIR.PlainCallEntry P4bloIR.PlainCallReturn

def body : List Stmt := CallInitializers.body ++ GuardedForwardPolicy.guardedForward.lower
def program : Program := CallEntry.WithBody.program body
def index : Index := CallEntry.WithBody.index body

theorem body_prefix : body = GuardedCallPrefix.body [] := by
  simp [body, GuardedCallPrefix.body]

theorem index_built : Index.build program = .ok index := CallEntry.WithBody.index_built body
theorem block_lookup : index.blocks["RewriteBody"]? = some (CallEntry.WithBody.block body) :=
  CallEntry.WithBody.block_lookup body

/-- Independent policy constructors and literal top-level slots, not authored
accessors, command denotation or interpreter output. -/
def resultStore (hdr : Data headers) (metaData : Data metadata) (routeData : Data route) : Store roots :=
  ForwardPolicy.restore (GuardedForwardPolicy.policy
    (ForwardPolicy.observe (CallInitializers.bodyStore hdr metaData routeData)))

def result (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value) : Run :=
  let values := resultStore hdr metaData routeData
  let frame := returnedFrame run.frame (values.get .here).toValue
    (values.get (.there .here)).toValue observer
  { run with frame }

/-- The continuation is arbitrary and remains untouched. The final caller
frame is the exact ordered three-insert return, while all shared state is
the original Run's state, not a reconstructed snapshot. -/
theorem source_steps (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value) (continuation : List Work)
    (hi : run.index = index) (hb : BlockFrame run.frame)
    (hh : run.frame.read? "source_hdr" = some hdr.toValue)
    (hm : run.frame.read? "source_meta" = some metaData.toValue)
    (hr : run.frame.read? "source_route" = some routeData.toValue)
    (ho : run.frame.read? "hdr" = some observer) :
    Steps { work := .block "RewriteBody" args :: continuation, run }
      { work := continuation, run := result run hdr metaData routeData observer } := by
  have hi' : run.index = CallEntry.WithBody.index (GuardedCallPrefix.body []) := by
    simpa only [index, body_prefix] using hi
  obtain ⟨frame, hprefix, _, _, values, preserved, _⟩ :=
    GuardedCallPrefix.source_prefix run hdr metaData routeData observer [] continuation hi' hb hh hm hr ho
  let after := { run with frame }
  have readHdr : after.frame.read? "hdr" = some ((resultStore hdr metaData routeData).get .here).toValue :=
    values .here
  have readMeta : after.frame.read? "meta" = some ((resultStore hdr metaData routeData).get (.there .here)).toValue :=
    values (.there .here)
  have pop : Steps
      { work := .statements [] :: .blockReturn run.frame params args :: continuation, run := after }
      { work := .blockReturn run.frame params args :: continuation, run := after } :=
    .next rfl .refl
  have returned := return_steps after run.frame _ _ observer hdr.toValue metaData.toValue observer
    continuation hb hh hm ho readHdr readMeta preserved
  exact hprefix.trans (pop.trans returned)

/-- Actual semantic callBlock completion, not just a bounded trace. -/
theorem call_correct (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value)
    (hi : run.index = index) (hb : BlockFrame run.frame)
    (hh : run.frame.read? "source_hdr" = some hdr.toValue)
    (hm : run.frame.read? "source_meta" = some metaData.toValue)
    (hr : run.frame.read? "source_route" = some routeData.toValue)
    (ho : run.frame.read? "hdr" = some observer) :
    (callBlock "RewriteBody" args).run run = (.ok (), result run hdr metaData routeData observer) :=
  ((source_steps run hdr metaData routeData observer [] hi hb hh hm hr ho).finishes (.done rfl)).sound

theorem changes_only_vars (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value) :
    ChangesOnlyVars run (result run hdr metaData routeData observer) := ⟨_, rfl⟩

theorem result_lookup (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value) (hb : BlockFrame run.frame) (name : String) :
    (result run hdr metaData routeData observer).frame.read? name =
      if name = "hdr" then some observer
      else if name = "source_meta" then some ((resultStore hdr metaData routeData).get (.there .here)).toValue
      else if name = "source_hdr" then some ((resultStore hdr metaData routeData).get .here).toValue
      else run.frame.read? name :=
  returned_lookup run.frame _ _ observer hb name

theorem preserves_outside (run : Run) (hdr : Data headers) (metaData : Data metadata)
    (routeData : Data route) (observer : Value) (hb : BlockFrame run.frame) (name : String)
    (hn : name ∉ ["source_hdr", "source_meta", "hdr"]) :
    (result run hdr metaData routeData observer).frame.read? name = run.frame.read? name :=
  returned_preserves run.frame _ _ observer hb name hn

end P4blo.GuardedControlCall
