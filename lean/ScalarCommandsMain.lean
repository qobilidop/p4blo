import P4blo.ScalarCommandExamples
import P4bloIR.Json

/-- Syntax and initial inputs only; independent expected final values live
in the tests. This is a fixture exporter, not a whole-program compiler. -/
def main : IO Unit := do
  for c in P4blo.ScalarCommandExamples.cases do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name),
      ("inputs", Lean.Json.mkObj [("x", Lean.toJson c.first.val),
        ("y", Lean.toJson c.second.val), ("flag", Lean.toJson c.flag)]),
      ("body", Lean.toJson (c.command.lower.map P4bloIR.Stmt.toJson))]).compress
