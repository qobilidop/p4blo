import P4blo.FieldCommandExamples
import P4bloIR.Json

/-- Authored body syntax and inputs, never computed expected final state.
The cross-language tests independently specify declarations and outputs. -/
def main : IO Unit := do
  for c in P4blo.FieldCommandExamples.cases do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name),
      ("ttl", Lean.toJson c.initialTTL.val),
      ("ethernetValid", Lean.toJson c.ethernetValid),
      ("ipv4Valid", Lean.toJson c.ipv4Valid),
      ("hit", Lean.toJson c.hit),
      ("body", Lean.toJson (c.command.lower.map P4bloIR.Stmt.toJson))]).compress
