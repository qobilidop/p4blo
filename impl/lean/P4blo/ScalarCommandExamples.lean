import P4blo.ScalarCommands

namespace P4blo.ScalarCommandExamples

open Scalar
open scoped Scalar

def context : Context := [("x", .bits 8), ("y", .bits 8), ("flag", .boolean)]
def modes : Modes context := .cons .local (.cons .local (.cons .local .nil))
def x : Place modes (.bits 8) := ⟨.here, rfl⟩
def y : Place modes (.bits 8) := ⟨.there .here, rfl⟩
def flag : Place modes .boolean := ⟨.there (.there .here), rfl⟩

def update : Cmd modes :=
  (Cmd.assign x (.read x.ref + bits[8, 1])).seq
    ((Cmd.assign y (.read x.ref + .read y.ref)).seq
      (Cmd.ite (.read x.ref === bits[8, 0])
        (Cmd.assign flag (.boolean true)) (Cmd.assign flag (.boolean false))))

def choose : Cmd modes :=
  (Cmd.ite (.read flag.ref)
    (Cmd.assign x (.read x.ref + bits[8, 7]))
    (Cmd.assign x (.read x.ref + bits[8, 9]))).seq
    (Cmd.assign y (.read x.ref + .read y.ref))

structure Case where
  name : String
  command : Cmd modes
  first : Fin 256
  second : Fin 256
  flag : Bool

def Case.environment (c : Case) : Env context :=
  .cons c.first (.cons c.second (.cons c.flag .nil))

def cases : List Case := [
  ⟨"update-wrap", update, 255, 7, false⟩,
  ⟨"update-dependent", update, 3, 7, true⟩,
  ⟨"update-y-wrap", update, 254, 2, true⟩,
  ⟨"update-zero", update, 0, 0, false⟩,
  ⟨"choose-yes", choose, 3, 7, true⟩,
  ⟨"choose-no", choose, 3, 7, false⟩,
  ⟨"choose-wrap", choose, 250, 255, true⟩,
  ⟨"skip", .done, 19, 7, true⟩,
  ⟨"boolean", Cmd.assign flag (.boolean false), 19, 7, true⟩]

example : P4bloIR.ScalarTyping.Context.WellFormed context := by decide
example : modes.Agrees modes.scope := modes.scope_agrees (by decide)
example (c : Case) : FrameMatches c.environment (modes.frame c.environment) :=
  modes.frame_matches c.environment (by decide)

end P4blo.ScalarCommandExamples
