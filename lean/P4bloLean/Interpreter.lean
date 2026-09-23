import P4blo.Switch

/-!
User-facing execution API. These names reuse reference semantics directly;
they are not a second implementation or a whole-program validity theorem.
Raw programs still need validation before trusted execution. `Index.build`
checks names, not every typing/control-flow rule of the Python validator.
-/

namespace P4bloLean

abbrev runParser := P4blo.runParser
abbrev runControl := P4blo.runControl
abbrev runDeparser := P4blo.runDeparser

/-- Prepare a switch and fresh extern state. This performs indexing, extern
binding and the switch contract checks, NOT whole-program validation. -/
def prepareSwitch (program : P4blo.Program) (ports : Nat := 4) :
    Except String (P4blo.Switch × P4blo.Externs) := do
  let index ← P4blo.Index.build program
  let externs ← P4blo.Externs.bind index
  let sw ← P4blo.Switch.load index ports
  pure (sw, externs)

/-- Execute against caller-owned persistent state and table configuration.
Thread the returned extern state into the next packet to preserve history. -/
abbrev runSwitch := P4blo.Switch.run

end P4bloLean
