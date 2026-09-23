import P4blo.Commands
import P4blo.FieldPlaces

namespace P4blo.Fields

abbrev Cmd {roots : Layout} (modes : Modes roots) := Scalar.CmdWith (Read roots) (Place modes)

variable {roots : Layout} {modes : Modes roots}

namespace Cmd
abbrev done {roots : Layout} {modes : Modes roots} := @Scalar.CmdWith.done (Read roots) (Place modes)
abbrev write {roots : Layout} {modes : Modes roots} := @Scalar.CmdWith.write (Read roots) (Place modes)
abbrev branch {roots : Layout} {modes : Modes roots} := @Scalar.CmdWith.branch (Read roots) (Place modes)
end Cmd

def Cmd.assign (place : Place modes t) (value : Expr roots t) : Cmd modes := Scalar.CmdWith.assign place value
def Cmd.ite (condition : Expr roots .boolean) (yes no : Cmd modes) : Cmd modes := Scalar.CmdWith.ite condition yes no
def Cmd.seq (first second : Cmd modes) : Cmd modes := Scalar.CmdWith.seq first second
def Cmd.block (commands : List (Cmd modes)) : Cmd modes := Scalar.CmdWith.block commands

def Cmd.denote (cmd : Cmd modes) (store : Store roots) : Store roots :=
  cmd.denoteWith (fun store {_} ref => ref.get store) (fun store {_} place value => place.ref.set store value) store

def Cmd.lower (cmd : Cmd modes) : List P4bloIR.Stmt :=
  cmd.lowerWith (fun ref => ref.expr) (fun place => place.ref.lvalue)

def Cmd.targets (cmd : Cmd modes) : List String := cmd.targetsWith (fun place => place.ref.rootName)

theorem Cmd.denote_seq (first second : Cmd modes) (store : Store roots) :
    (first.seq second).denote store = second.denote (first.denote store) :=
  Scalar.CmdWith.denoteWith_seq _ _ first second store

theorem Cmd.lower_seq (first second : Cmd modes) :
    (first.seq second).lower = first.lower ++ second.lower :=
  Scalar.CmdWith.lowerWith_seq _ _ first second

theorem Cmd.denote_block (commands : List (Cmd modes)) (store : Store roots) :
    (Cmd.block commands).denote store = commands.foldl (fun state cmd => cmd.denote state) store :=
  Scalar.CmdWith.denoteWith_block _ _ commands store

theorem Cmd.lower_block (commands : List (Cmd modes)) :
    (Cmd.block commands).lower = commands.flatMap Cmd.lower :=
  Scalar.CmdWith.lowerWith_block _ _ commands

/-- Scalar-leaf writes preserve every header validity bit, including those
outside the selected path. This is a property of the independent source
store; exact final frame agreement lifts its full values to actual execution. -/
theorem Cmd.validities (cmd : Cmd modes) (store : Store roots) :
    (cmd.denote store).validities = store.validities := by
  induction cmd generalizing store with
  | done => rfl
  | write place value next ih =>
    exact (ih _).trans (place.ref.validities_set store _)
  | branch condition yes no next hy hn ht =>
    change (Cmd.denote next _).validities = _
    rw [ht]
    change (if Fields.denote store condition then Cmd.denote yes store else Cmd.denote no store).validities = _
    cases hc : Fields.denote store condition
    · simpa [hc] using hn store
    · simpa [hc] using hy store

theorem Cmd.lower_typed (cmd : Cmd modes) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : modes.Agrees scope) :
    P4bloIR.FieldTyping.BodyTyped index scope cmd.lower := by
  induction cmd with
  | done => exact .nil
  | @write t place value next ih =>
    exact .cons (.assign (t := t) (place.typed hw hi hd) (Fields.lower_typed value hw hi hd.declares)) ih
  | branch condition yes no next hy hn ht =>
    exact .cons (.conditional (Fields.lower_typed condition hw hi hd.declares) hy hn) ht

open P4bloIR.ScalarStatements (BlockFrame ChangesOnlyVars PreservesOutside)
open P4bloIR.Execution (Steps)

/-- Concrete aggregate execution, not a callback assumption: reviewed path
read/write laws discharge every generic leaf operation. An arbitrary
continuation is retained, and the complete source store is related exactly. -/
theorem Cmd.steps (cmd : Cmd modes) (store : Store roots) (initial : P4bloIR.Run)
    (continuation : List P4bloIR.Execution.Work) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees initial.index) (hd : modes.Agrees initial.frame.scope)
    (hf : FrameMatches store initial.frame) (hb : BlockFrame initial.frame) :
    P4bloIR.FieldTyping.BodyTyped initial.index initial.frame.scope cmd.lower ∧
    ∃ final, Steps { work := .statements cmd.lower :: continuation, run := initial }
        { work := continuation, run := final } ∧
      FrameMatches (cmd.denote store) final.frame ∧ ChangesOnlyVars initial final ∧
      PreservesOutside cmd.targets initial final := by
  refine ⟨cmd.lower_typed hw hi hd, ?_⟩
  have trace := cmd.steps_with
    (fun store {_} ref => ref.get store) (fun store {_} place value => place.ref.set store value)
    (fun ref => ref.expr) (fun place => place.ref.lvalue) (fun place => place.ref.rootName)
    (fun store run => FrameMatches store run.frame ∧ roots.IndexAgrees run.index)
    (by intro source run hm t ref; exact ref.evaluate source run hm.2 hm.1)
    (by
      intro t place source value run hm block
      obtain ⟨final, write, hmatches, changes, outside⟩ :=
        place.ref.write_matches source value run hm.2 hm.1 hw.1 block
      have hiFinal : roots.IndexAgrees final.index := by
        obtain ⟨_, rfl⟩ := changes
        exact hm.2
      exact ⟨final, write, ⟨hmatches, hiFinal⟩, changes, outside⟩)
    store initial continuation ⟨hf, hi⟩ hb
  obtain ⟨final, trace, hmatches, changes, outside⟩ := trace
  exact ⟨final, trace, hmatches.1, changes, outside⟩

/-- Exact execution of an already-initialized, action-free body under real
nominal declarations and root permissions. No initializer, parser, table,
packet operation, aggregate-copy or whole-program validity claim follows. -/
theorem Cmd.execute_correct (cmd : Cmd modes) (store : Store roots) (initial : P4bloIR.Run)
    (hw : RootWellFormed roots) (hi : roots.IndexAgrees initial.index)
    (hd : modes.Agrees initial.frame.scope) (hf : FrameMatches store initial.frame)
    (hb : BlockFrame initial.frame) :
    P4bloIR.FieldTyping.BodyTyped initial.index initial.frame.scope cmd.lower ∧
    ∃ final, (P4bloIR.execute cmd.lower).run initial = (.ok (), final) ∧
      FrameMatches (cmd.denote store) final.frame ∧ modes.Agrees final.frame.scope ∧
      (cmd.denote store).validities = store.validities ∧
      ChangesOnlyVars initial final ∧ PreservesOutside cmd.targets initial final := by
  obtain ⟨typed, final, trace, hmatches, changes, outside⟩ :=
    cmd.steps store initial [] hw hi hd hf hb
  refine ⟨typed, final, trace.execute, hmatches, ?_, cmd.validities store, changes, outside⟩
  rw [changes.scope]
  exact hd

end P4blo.Fields
