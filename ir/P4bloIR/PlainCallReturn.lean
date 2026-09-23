import P4bloIR.PlainCallEntry

/-! Normal return of the fixed plain-root call profile. No body, observer,
action, parser, pending-fault unwinding or global typing theorem is claimed. -/

namespace P4bloIR.PlainCallReturn
open PlainCallEntry ScalarTyping ScalarStatements Execution

/-- The three ordered result inserts into the originally captured caller. -/
def returnedFrame (caller : Frame) (hdr metadata observer : Value) : Frame :=
  { caller with
    vars := ((caller.vars.insert "source_hdr" hdr).insert "source_meta" metadata).insert "hdr" observer }

theorem copyBack_three (callee : Frame) (hdr metadata observer : Value)
    (hh : callee.read? "hdr" = some hdr)
    (hm : callee.read? "meta" = some metadata)
    (ho : callee.read? "observer" = some observer) :
    copyBack params args callee = (do
      writeVar "source_hdr" hdr
      writeVar "source_meta" metadata
      writeVar "hdr" observer) := by
  have io : (Direction.inout == Direction.out) = false := rfl
  have ii : (Direction.inout == Direction.inout) = true := rfl
  have ni : (Direction.in == Direction.inout) = false := rfl
  have no : (Direction.in == Direction.out) = false := rfl
  simp [copyBack, params, args, hh, hm, ho, writeLValue, io, ii, ni, no]

/-- Only original caller root existence is needed for operational writes.
The entire current callee-after Run is retained outside its replaced frame. -/
theorem dispatch_return (run : Run) (caller : Frame)
    (hdr metadata observer oldHdr oldMeta oldObserver : Value)
    (hb : BlockFrame caller)
    (ch : caller.read? "source_hdr" = some oldHdr)
    (cm : caller.read? "source_meta" = some oldMeta)
    (co : caller.read? "hdr" = some oldObserver)
    (hh : run.frame.read? "hdr" = some hdr)
    (hm : run.frame.read? "meta" = some metadata)
    (ho : run.frame.read? "observer" = some observer) :
    (dispatch (.blockReturn caller params args)).run run =
      (.ok [], { run with frame := returnedFrame caller hdr metadata observer }) := by
  let first : Frame := { caller with vars := caller.vars.insert "source_hdr" hdr }
  let second : Frame := { first with vars := first.vars.insert "source_meta" metadata }
  have wh := writeVar_block (value := hdr) { run with frame := caller } hb ch
  have wm := writeVar_block (value := metadata) { run with frame := first } hb
    (show first.read? "source_meta" = some oldMeta from by
      simpa [first, Frame.read?, hb.2, Std.HashMap.getElem?_insert] using cm)
  have wo := writeVar_block (value := observer) { run with frame := second } hb
    (show second.read? "hdr" = some oldObserver from by
      simpa [second, first, Frame.read?, hb.2, Std.HashMap.getElem?_insert] using co)
  have hg : getFrame.run run = (.ok run.frame, run) := rfl
  have hs : (setFrame caller).run run = (.ok (), { run with frame := caller }) := rfl
  dsimp only [first, second] at wm wo
  simp only [dispatch, run_bind, hg, hs, copyBack_three run.frame hdr metadata observer hh hm ho,
    wh, wm, wo, run_pure]
  rfl

theorem return_step (run : Run) (caller : Frame)
    (hdr metadata observer oldHdr oldMeta oldObserver : Value) (continuation : List Work)
    (hb : BlockFrame caller)
    (ch : caller.read? "source_hdr" = some oldHdr)
    (cm : caller.read? "source_meta" = some oldMeta)
    (co : caller.read? "hdr" = some oldObserver)
    (hh : run.frame.read? "hdr" = some hdr)
    (hm : run.frame.read? "meta" = some metadata)
    (ho : run.frame.read? "observer" = some observer) :
    step { work := .blockReturn caller params args :: continuation, run, fault := none } =
      .inr { work := continuation, run := { run with frame := returnedFrame caller hdr metadata observer }, fault := none } := by
  simp [step, dispatch_return run caller hdr metadata observer oldHdr oldMeta oldObserver hb ch cm co hh hm ho]

theorem return_steps (run : Run) (caller : Frame)
    (hdr metadata observer oldHdr oldMeta oldObserver : Value) (continuation : List Work)
    (hb : BlockFrame caller)
    (ch : caller.read? "source_hdr" = some oldHdr)
    (cm : caller.read? "source_meta" = some oldMeta)
    (co : caller.read? "hdr" = some oldObserver)
    (hh : run.frame.read? "hdr" = some hdr)
    (hm : run.frame.read? "meta" = some metadata)
    (ho : run.frame.read? "observer" = some observer) :
    Steps { work := .blockReturn caller params args :: continuation, run, fault := none }
      { work := continuation, run := { run with frame := returnedFrame caller hdr metadata observer }, fault := none } :=
  Steps.next (return_step run caller hdr metadata observer oldHdr oldMeta oldObserver continuation hb ch cm co hh hm ho) Steps.refl

theorem returned_scope (caller : Frame) (hdr metadata observer : Value) :
    (returnedFrame caller hdr metadata observer).scope = caller.scope := rfl

theorem returned_blockFrame (caller : Frame) (hdr metadata observer : Value)
    (hb : BlockFrame caller) : BlockFrame (returnedFrame caller hdr metadata observer) := hb

theorem returned_lookup (caller : Frame) (hdr metadata observer : Value)
    (hb : BlockFrame caller) (name : String) :
    (returnedFrame caller hdr metadata observer).read? name =
      if name = "hdr" then some observer
      else if name = "source_meta" then some metadata
      else if name = "source_hdr" then some hdr else caller.read? name := by
  by_cases h : name = "hdr"
  · subst name; simp [returnedFrame, Frame.read?, hb.2]
  by_cases m : name = "source_meta"
  · subst name; simp [returnedFrame, Frame.read?, hb.2, Std.HashMap.getElem_insert]
  by_cases s : name = "source_hdr"
  · subst name; simp [returnedFrame, Frame.read?, hb.2, Std.HashMap.getElem_insert]
  simp [returnedFrame, Frame.read?, hb.2, Std.HashMap.getElem?_insert, h, m, s,
    Ne.symm h, Ne.symm m, Ne.symm s]

theorem returned_preserves (caller : Frame) (hdr metadata observer : Value)
    (hb : BlockFrame caller) (name : String)
    (hn : name ∉ ["source_hdr", "source_meta", "hdr"]) :
    (returnedFrame caller hdr metadata observer).read? name = caller.read? name := by
  simp only [List.mem_cons, not_or] at hn
  simp [returned_lookup caller hdr metadata observer hb name, hn.1, hn.2.1, hn.2.2]

end P4bloIR.PlainCallReturn
