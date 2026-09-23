import P4blo.GuardedForwardTests
import P4bloIR.Json

/-- Authored syntax and initial inputs only; expected states are independent. -/
def main : IO Unit := do
  for c in P4blo.GuardedForwardTests.cases do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name),
      ("ttl", Lean.toJson c.ttl.val),
      ("ethernetValid", Lean.toJson c.ethernetValid),
      ("ipv4Valid", Lean.toJson c.ipv4Valid),
      ("hit", Lean.toJson c.hit),
      ("body", Lean.toJson (P4blo.GuardedForwardPolicy.guardedForward.lower.map P4bloIR.Stmt.toJson))]).compress
