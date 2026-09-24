import P4bloIR.Switch

/-!
User-facing execution API. These names reuse reference semantics directly;
they are not a second implementation or a whole-program validity theorem.
Raw programs still need validation before trusted execution. `Index.build`
checks names, not every typing/control-flow rule of the Python validator.
-/

namespace P4blo

abbrev runParser := P4bloIR.runParser
abbrev runControl := P4bloIR.runControl
abbrev runDeparser := P4bloIR.runDeparser

/-- Prepare a switch and fresh extern state. This performs indexing, extern
binding and the switch contract checks, NOT whole-program validation. -/
def prepareSwitch (program : P4bloIR.Program) (ports : Nat := 4) :
    Except String (P4bloIR.Switch × P4bloIR.Externs) := do
  let index ← P4bloIR.Index.build program
  let externs ← P4bloIR.Externs.bind index
  let sw ← P4bloIR.Switch.load index ports
  pure (sw, externs)

/-- Execute against caller-owned persistent state and table configuration.
Thread the returned extern state into the next packet to preserve history. -/
abbrev runSwitch := P4bloIR.Switch.run

end P4blo
