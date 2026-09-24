import P4blo.Commands
import P4blo.ScalarPlaces

namespace P4blo.Scalar

def Env.set {ctx : Context} {t : Ty} : Env ctx → Ref ctx t → Meaning t → Env ctx
  | .cons _ rest, .here, value => .cons value rest
  | .cons head rest, .there ref, value => .cons head (rest.set ref value)

theorem Env.get_set (env : Env ctx) (ref : Ref ctx t) (value : Meaning t) :
    (env.set ref value).get ref = value := by
  induction ref with
  | here => cases env; rfl
  | there ref ih => cases env; exact ih _ value

theorem Env.get_set_value (env : Env ctx) (ref : Ref ctx t) (value : Meaning t)
    (other : Ref ctx u) (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) :
    toValue ((env.set ref value).get other) =
      if other.name = ref.name then toValue value else toValue (env.get other) := by
  induction ref with
  | @here name t rest =>
    cases env with
    | cons head tail =>
      cases other with
      | here => simp [Env.set, Env.get]
      | there other =>
        have hn : other.name ≠ name := by
          intro h
          exact (List.nodup_cons.mp hw.1).1
            (h ▸ List.mem_map.mpr ⟨_, other.mem, rfl⟩)
        simp [Env.set, Env.get, Ref.name, hn]
  | @there rest t binding ref ih =>
    have hn : ref.name ≠ binding.1 := by
      intro h
      exact (List.nodup_cons.mp hw.1).1
        (h ▸ List.mem_map.mpr ⟨_, ref.mem, rfl⟩)
    cases env with
    | cons head tail =>
      cases other with
      | here => simp [Env.set, Env.get, Ref.name, Ne.symm hn]
      | there other =>
        simpa [Env.set, Env.get, Ref.name] using ih tail value other (context_tail hw)

theorem FrameMatches.set {env : Env ctx} (hf : FrameMatches env frame)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx)
    (hb : P4bloIR.ScalarStatements.BlockFrame frame) (ref : Ref ctx t) (value : Meaning t) :
    FrameMatches (env.set ref value)
      { frame with vars := frame.vars.insert ref.name (toValue value) } := by
  intro u other
  rw [Env.get_set_value env ref value other hw]
  have h := hf other
  simp only [P4bloIR.Frame.read?, hb.2, Option.bind_none] at h ⊢
  simp only [Std.HashMap.getElem?_insert]
  by_cases he : other.name = ref.name
  · simp [he]
  · simp [he, Ne.symm he, h]

variable {ctx : Context} {modes : Modes ctx}

/-- The scalar specialization of the single typed command language. -/
abbrev Cmd {ctx : Context} (modes : Modes ctx) := CmdWith (Ref ctx) (Place modes)

namespace Cmd
abbrev done {ctx : Context} {modes : Modes ctx} := @CmdWith.done (Ref ctx) (Place modes)
abbrev write {ctx : Context} {modes : Modes ctx} := @CmdWith.write (Ref ctx) (Place modes)
abbrev branch {ctx : Context} {modes : Modes ctx} := @CmdWith.branch (Ref ctx) (Place modes)
end Cmd

def Cmd.assign (place : Place modes t) (value : ExprIn ctx t) : Cmd modes := CmdWith.assign place value
def Cmd.ite (condition : ExprIn ctx .boolean) (yes no : Cmd modes) : Cmd modes := CmdWith.ite condition yes no
def Cmd.seq (first second : Cmd modes) : Cmd modes := CmdWith.seq first second
def Cmd.block (commands : List (Cmd modes)) : Cmd modes := CmdWith.block commands

def Cmd.denote (cmd : Cmd modes) (env : Env ctx) : Env ctx :=
  cmd.denoteWith (fun env {_} ref => env.get ref) (fun env {_} place value => env.set place.ref value) env

def Cmd.lower (cmd : Cmd modes) : List P4bloIR.Stmt :=
  cmd.lowerWith (fun ref => .var ref.name) (fun place => .var place.ref.name)

def Cmd.targets (cmd : Cmd modes) : List String := cmd.targetsWith (fun place => place.ref.name)

theorem Cmd.denote_seq (first second : Cmd modes) (env : Env ctx) :
    (first.seq second).denote env = second.denote (first.denote env) := by
  exact CmdWith.denoteWith_seq _ _ first second env

theorem Cmd.lower_seq (first second : Cmd modes) :
    (first.seq second).lower = first.lower ++ second.lower := by
  exact CmdWith.lowerWith_seq _ _ first second

theorem Cmd.denote_block (commands : List (Cmd modes)) (env : Env ctx) :
    (Cmd.block commands).denote env = commands.foldl (fun state cmd => cmd.denote state) env :=
  CmdWith.denoteWith_block _ _ commands env

theorem Cmd.lower_block (commands : List (Cmd modes)) :
    (Cmd.block commands).lower = commands.flatMap Cmd.lower :=
  CmdWith.lowerWith_block _ _ commands

theorem Cmd.lower_typed {modes : Modes ctx} (cmd : Cmd modes)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) (hd : modes.Agrees scope) :
    P4bloIR.ScalarStatements.BodyTyped ctx scope cmd.lower := by
  induction cmd with
  | done => exact .nil
  | write place value next ih =>
    exact .cons (.assign (place.canAssign hw hd) (lower_typed_in value hw)) ih
  | branch condition yes no next hy hn hnext =>
    exact .cons (.conditional (lower_typed_in condition hw) hy hn) hnext

open P4bloIR.ScalarStatements (BlockFrame ChangesOnlyVars PreservesOutside)
open P4bloIR.Execution (Steps)

/-- Finite execution of the authored prefix in a flat statement list, leaving
the suffix and continuation unexecuted with exact source/noninterference facts. -/
theorem Cmd.steps_prefix (cmd : Cmd modes) (env : Env ctx) (initial : P4bloIR.Run)
    (suffix : List P4bloIR.Stmt)
    (continuation : List P4bloIR.Execution.Work)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx)
    (hf : FrameMatches env initial.frame) (hb : BlockFrame initial.frame) :
    ∃ final, Steps { work := .statements (cmd.lower ++ suffix) :: continuation, run := initial }
        { work := .statements suffix :: continuation, run := final } ∧
      FrameMatches (cmd.denote env) final.frame ∧ ChangesOnlyVars initial final ∧
      PreservesOutside cmd.targets initial final := by
  apply cmd.steps_prefix_with (fun env {_} ref => env.get ref)
    (fun env {_} place value => env.set place.ref value)
    (fun ref => .var ref.name) (fun place => .var place.ref.name)
    (fun place => place.ref.name) (fun env run => FrameMatches env run.frame)
    ?_ ?_ env initial suffix continuation hf hb
  · intro source run hm t ref
    simp [P4bloIR.evaluate, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind, hm ref]
  · intro t place source value run hm block
    let final : P4bloIR.Run := { run with frame := { run.frame with
      vars := run.frame.vars.insert place.ref.name (toValue value) } }
    refine ⟨final, ?_, hm.set hw block place.ref value, ⟨_, rfl⟩, ?_⟩
    · exact P4bloIR.ScalarStatements.writeVar_block run block (hm place.ref)
    · intro name hn
      simp only [List.mem_singleton] at hn
      simp [final, Std.HashMap.getElem?_insert, Ne.symm hn]

/-- Finite execution of precisely this body, leaving an arbitrary continuation
unexecuted. The source result and complete noninterference facts are retained. -/
theorem Cmd.steps (cmd : Cmd modes) (env : Env ctx) (initial : P4bloIR.Run)
    (continuation : List P4bloIR.Execution.Work)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx)
    (hf : FrameMatches env initial.frame) (hb : BlockFrame initial.frame) :
    ∃ final, Steps { work := .statements cmd.lower :: continuation, run := initial }
        { work := continuation, run := final } ∧
      FrameMatches (cmd.denote env) final.frame ∧ ChangesOnlyVars initial final ∧
      PreservesOutside cmd.targets initial final := by
  obtain ⟨final, trace, hmatches, changes, outside⟩ :=
    cmd.steps_prefix env initial [] continuation hw hf hb
  refine ⟨final, ?_, hmatches, changes, outside⟩
  simpa using trace.trans (.next rfl .refl)

/-- Actual reference execution, not an alternative source evaluator. The
declaration premise supplies statement typing; operational preservation uses
the runtime's own write behavior and exact source value correspondence. -/
theorem Cmd.execute_correct (cmd : Cmd modes) (env : Env ctx) (initial : P4bloIR.Run)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) (hd : modes.Agrees initial.frame.scope)
    (hf : FrameMatches env initial.frame) (hb : BlockFrame initial.frame) :
    P4bloIR.ScalarStatements.BodyTyped ctx initial.frame.scope cmd.lower ∧
    ∃ final, (P4bloIR.execute cmd.lower).run initial = (.ok (), final) ∧
      FrameMatches (cmd.denote env) final.frame ∧
      P4bloIR.ScalarTyping.FrameTyped ctx final.frame ∧ modes.Agrees final.frame.scope ∧
      ChangesOnlyVars initial final ∧ PreservesOutside cmd.targets initial final := by
  obtain ⟨final, trace, hm, hc, ho⟩ := cmd.steps env initial [] hw hf hb
  refine ⟨cmd.lower_typed hw hd, final, trace.execute, hm, hm.typed, ?_, hc, ho⟩
  rw [hc.scope]
  exact hd

end P4blo.Scalar
