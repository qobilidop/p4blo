import P4blo.ScalarExamples
import P4bloIR.Json

/-- Export source-built IR, never precomputed source answers. The conformance
suite places these expressions in independently validated packet programs. -/
def main : IO Unit := do
  for c in P4blo.ScalarExamples.cases do
    let width := match c.type with
      | .bits n => Lean.toJson n
      | .boolean => Lean.Json.null
    let json := Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("expression", (P4blo.Scalar.lower c.expression).toJson)]
    IO.println json.compress
