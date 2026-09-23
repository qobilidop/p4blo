import P4bloIR.ScalarStatements

/-! Exact entry of the existing four-parameter plain-root RewriteBody call.
This stops before runBlock, observer execution or copyback. -/

namespace P4bloIR.PlainCallEntry
open ScalarTyping Execution

def params : List Param :=
  [⟨"hdr", .struct "Headers", .inout⟩, ⟨"meta", .struct "Metadata", .inout⟩,
   ⟨"route", .struct "Route", .in⟩, ⟨"observer", .struct "H", .inout⟩]

def args : List Arg :=
  [.lvalue (.var "source_hdr"), .lvalue (.var "source_meta"),
   .expr (.var "source_route"), .lvalue (.var "hdr")]

/-- The exact four ordered inserts in the result, not an executable binder. -/
def boundFrame (zero : Frame) (hdr metadata route observer : Value) : Frame :=
  { zero with
    vars := (((zero.vars.insert "hdr" hdr).insert "meta" metadata).insert "route" route).insert
      "observer" observer }

theorem argument_in (run : Run) (name paramName : String) (ty : Ty) (value : Value)
    (h : run.frame.read? name = some value) :
    (argumentValue ⟨paramName, ty, .in⟩ (.expr (.var name))).run run = (.ok value, run) := by
  change (readVar name).run run = _
  simp [readVar, run_bind, h]

theorem argument_inout (run : Run) (name paramName : String) (ty : Ty) (value : Value)
    (h : run.frame.read? name = some value) :
    (argumentValue ⟨paramName, ty, .inout⟩ (.lvalue (.var name))).run run = (.ok value, run) := by
  change (readVar name).run run = _
  simp [readVar, run_bind, h]

/-- An out argument is ignored even when it would fail to evaluate. -/
theorem argument_out (run : Run) (paramName : String) (ty : Ty) (arg : Arg) (value : Value)
    (h : Value.zero ty run.index = .ok value) :
    (argumentValue ⟨paramName, ty, .out⟩ arg).run run = (.ok value, run) := by
  change (liftExcept (Value.zero ty run.index)).run run = _
  rw [h]
  rfl

private theorem run_get (run : Run) : (get : M Run).run run = (.ok run, run) := rfl

private theorem run_modify (f : Run → Run) (run : Run) :
    (modify f : M Unit).run run = (.ok (), f run) := rfl

theorem dispatch_entry (run : Run) (name : String) (block : Block) (zero : Frame)
    (hdr metadata route observer : Value)
    (hb : run.index.blocks[name]? = some block) (hp : block.params = params)
    (hz : Frame.forBlock run.index block = .ok zero)
    (hh : run.frame.read? "source_hdr" = some hdr)
    (hm : run.frame.read? "source_meta" = some metadata)
    (hr : run.frame.read? "source_route" = some route)
    (ho : run.frame.read? "hdr" = some observer) :
    (dispatch (.block name args)).run run =
      (.ok [.runBlock block, .blockReturn run.frame block.params args],
       { run with frame := boundFrame zero hdr metadata route observer }) := by
  simp only [dispatch, run_bind, getIndex, run_get, run_pure, hb]
  have ah := argument_inout run "source_hdr" "hdr" (.struct "Headers") hdr hh
  have am := argument_inout run "source_meta" "meta" (.struct "Metadata") metadata hm
  have ar := argument_in run "source_route" "route" (.struct "Route") route hr
  have ao := argument_inout run "hdr" "observer" (.struct "H") observer ho
  simp [hp, params, args, hz, liftExcept, List.foldlM, run_bind, run_map, run_get, run_modify,
    ah, am, ar, ao, getFrame, setFrame, boundFrame]

theorem entry_steps (run : Run) (name : String) (block : Block) (zero : Frame)
    (hdr metadata route observer : Value) (continuation : List Work)
    (hb : run.index.blocks[name]? = some block) (hp : block.params = params)
    (hz : Frame.forBlock run.index block = .ok zero)
    (hh : run.frame.read? "source_hdr" = some hdr)
    (hm : run.frame.read? "source_meta" = some metadata)
    (hr : run.frame.read? "source_route" = some route)
    (ho : run.frame.read? "hdr" = some observer) :
    Steps { work := .block name args :: continuation, run }
      { work := .runBlock block :: .blockReturn run.frame block.params args :: continuation,
        run := { run with frame := boundFrame zero hdr metadata route observer } } := by
  apply Steps.next ?_ Steps.refl
  simp [step, dispatch_entry run name block zero hdr metadata route observer hb hp hz hh hm hr ho]

theorem unknown_block (run : Run) (name : String) (arguments : List Arg)
    (hb : run.index.blocks[name]? = none) :
    (dispatch (.block name arguments)).run run =
      (.error (.interp s!"unknown block '{name}'"), run) := by
  simp only [dispatch, run_bind, getIndex, run_get, run_pure, hb]
  rfl

theorem wrong_arity (run : Run) (name : String) (block : Block) (arguments : List Arg)
    (hb : run.index.blocks[name]? = some block) (ha : arguments.length ≠ block.params.length) :
    (dispatch (.block name arguments)).run run =
      (.error (.interp s!"block '{block.name}' takes {block.params.length} arguments"), run) := by
  simp only [dispatch, run_bind, getIndex, run_get, run_pure, hb]
  simp [ha, throwInterp]
  rfl

end P4bloIR.PlainCallEntry
