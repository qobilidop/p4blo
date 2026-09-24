import Lean.Data.Json.FromToJson
import P4bloIR.Externs

/-!
# Differential observations

Logical state only: instance names, register widths and cells, counter
values, and the presence of stateless checksum instances. Naturals are
hexadecimal strings to avoid JSON precision and decimal-conversion limits. Object ordering is
not significant. Every family reports its kind, then its width and cells
when it has them. This adapter is not a shared implementation of extern
semantics; those remain in the architecture's model and Python's
independent implementations.
-/

namespace P4bloIR

private def naturalHex (n : Nat) : String :=
  "0x" ++ String.ofList (Nat.toDigits 16 n)

def ExternState.observe (s : ExternState) : Lean.Json :=
  Lean.Json.mkObj ([("kind", .str s.kind)] ++
    (s.width.map fun w => ("width", Lean.toJson w)).toList ++
    (s.cells.map fun cells => ("values", Lean.Json.arr (cells.map fun n => .str (naturalHex n)))).toList)

def Externs.observe (externs : Externs) : Lean.Json :=
  Lean.Json.mkObj (externs.instances.toList.map fun (name, state) => (name, state.observe))

end P4bloIR
