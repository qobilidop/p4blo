import P4blo.HeaderReadExamples
import P4bloIR.Json

def main : IO Unit := do
  for c in P4blo.HeaderReadExamples.expressionCases do
    let width := match c.type with
      | .bits width => Lean.toJson width
      | .boolean => Lean.Json.null
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("a", Lean.toJson c.a), ("b", Lean.toJson c.b),
      ("expression", P4bloIR.Expr.toJson (P4blo.Fields.lower c.expression))]).compress
  for (suffix, a, b) in [("00", false, false), ("01", false, true), ("10", true, false), ("11", true, true)] do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson ("command-" ++ suffix)),
      ("a", Lean.toJson a), ("b", Lean.toJson b),
      ("body", Lean.toJson (P4blo.HeaderReadExamples.command.lower.map P4bloIR.Stmt.toJson))]).compress
