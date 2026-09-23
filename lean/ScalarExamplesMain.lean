import P4bloLean.ScalarExamples
import P4blo.Json

/-- Export source-built IR, never precomputed source answers. The conformance
suite places these expressions in independently validated packet programs. -/
def main : IO Unit := do
  for c in P4bloLean.ScalarExamples.cases do
    let width := match c.type with
      | .bits n => Lean.toJson n
      | .boolean => Lean.Json.null
    let json := Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("expression", (P4bloLean.Scalar.lower c.expression).toJson)]
    IO.println json.compress
