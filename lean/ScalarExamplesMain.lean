import P4blo.ScalarExamples
import P4bloIR.Json

private def bindings : P4blo.Scalar.Env ctx → List Lean.Json
  | .nil => []
  | .cons (name := name) (t := t) value rest =>
    let literal : P4bloIR.Literal := match t, value with
      | .bits width, value => .bits width value.val
      | .boolean, value => .boolean value
    Lean.Json.mkObj [("name", Lean.toJson name),
      ("value", (P4bloIR.Expr.literal literal).toJson)] :: bindings rest

/-- Export source-built IR, never precomputed source answers. The conformance
suite places these expressions in independently validated packet programs. -/
def main : IO Unit := do
  for c in P4blo.ScalarExamples.cases do
    let width := match c.type with
      | .bits n => Lean.toJson n
      | .boolean => Lean.Json.null
    let json := Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("bindings", Lean.toJson ([] : List Lean.Json)),
      ("expression", (P4blo.Scalar.lower c.expression).toJson)]
    IO.println json.compress
  for c in P4blo.ScalarExamples.openCases do
    let width := match c.type with
      | .bits n => Lean.toJson n
      | .boolean => Lean.Json.null
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("bindings", Lean.toJson (bindings c.environment)),
      ("expression", (P4blo.Scalar.lower c.expression).toJson)]).compress
