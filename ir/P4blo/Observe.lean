import Lean.Data.Json.FromToJson
import P4blo.Externs

/-!
# Differential observations

Logical state only: instance names, register widths and cells, counter
values, and the presence of stateless checksum instances. Naturals are
hexadecimal strings to avoid JSON precision and decimal-conversion limits. Object ordering is
not significant. This adapter is not a shared implementation of extern
semantics; those remain in `Externs` and Python's independent models.
-/

namespace P4blo

private def naturalHex (n : Nat) : String :=
  "0x" ++ String.ofList (Nat.toDigits 16 n)

def ExternState.observe : ExternState → Lean.Json
  | .register width cells => Lean.Json.mkObj
    [("kind", .str "register"), ("width", Lean.toJson width),
     ("values", .arr (cells.map fun n => .str (naturalHex n)))]
  | .counter counts => Lean.Json.mkObj
    [("kind", .str "counter"), ("values", .arr (counts.map fun n => .str (naturalHex n)))]
  | .checksum16 => Lean.Json.mkObj [("kind", .str "checksum16")]

def Externs.observe (externs : Externs) : Lean.Json :=
  Lean.Json.mkObj (externs.instances.toList.map fun (name, state) => (name, state.observe))

end P4blo
