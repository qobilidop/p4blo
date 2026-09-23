import P4blo.FieldTests
import P4bloIR.Json

/-- Test fixture syntax and selected initial validity only. Expected answers
and the independent full-store observer live outside this exporter. -/
def main : IO Unit := do
  for c in P4blo.FieldTests.expressionCases do
    let width := match c.type with
      | .bits width => Lean.toJson width
      | .boolean => Lean.Json.null
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width), ("valid", Lean.toJson c.valid),
      ("expression", P4bloIR.Expr.toJson (P4blo.Fields.lower c.expression))]).compress
