import P4bloArch.Assembly
import P4bloArch.Switch
import P4bloArch.Externs

/-!
User-facing execution API. These names reuse reference semantics directly;
they are not a second implementation or a whole-program validity theorem.
Raw programs still need validation before trusted execution. `Index.build`
checks names, not every typing/control-flow rule of the Python validator.
-/

namespace P4blo

abbrev runParser := P4bloArch.runParser
abbrev runControl := P4bloArch.runControl
abbrev runDeparser := P4bloArch.runDeparser

/-- Prepare a switch and fresh extern state. This performs indexing, extern
binding under the reference extern families and the switch contract
checks, NOT whole-program validation. -/
def prepareSwitch (program : P4bloArch.BlockAssembly) (ports : Nat := 4) :
    Except String (P4bloArch.Switch × P4bloIR.Externs) := do
  let index ← P4bloIR.Index.build program
  let externs ← P4bloArch.bind index
  let sw ← P4bloArch.Switch.load index program.toBlockBindings ports
  pure (sw, externs)

/-- Execute against caller-owned persistent state and table configuration.
Thread the returned extern state into the next packet to preserve history. -/
abbrev runSwitch := P4bloArch.Switch.run

end P4blo
