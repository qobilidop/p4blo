import Tests.Check
import P4bloIR.ScalarStatements

open P4bloIR

namespace ScalarStatementTests

private def ctx : ScalarTyping.Context := [("x", .bits 8)]
private def scope (decl : VarDecl) : BlockScope :=
  { block := default, vars := ({} : Std.HashMap String VarDecl).insert "x" decl }

private def param (direction : Direction) : VarDecl := .param ⟨"x", .bits 8, direction⟩

example : ¬ScalarStatements.Typed ctx (scope (param .«in»))
    (.assign (.var "x") (.literal (.bits 8 1))) := by
  intro typed
  cases typed with
  | assign permission _ =>
    simp [ScalarStatements.canAssign, ctx, scope, param, ScalarTyping.Context.lookup,
      BlockScope.var?, ScalarStatements.writable] at permission

def tests : T Unit := do
  for direction in [Direction.none, .«in»] do
    check s!"scalar statement rejects readonly {repr direction}"
      (!(ScalarStatements.canAssign ctx (scope (param direction)) "x" (.bits 8)))
  for direction in [Direction.out, .inout] do
    check s!"scalar statement accepts writable {repr direction}"
      (ScalarStatements.canAssign ctx (scope (param direction)) "x" (.bits 8))
  let localScope := scope (.var ⟨"x", .bits 8⟩)
  check "scalar statement accepts a declared local"
    (ScalarStatements.canAssign ctx localScope "x" (.bits 8))
  check "scalar statement rejects RHS width mismatch"
    (!(ScalarStatements.canAssign ctx localScope "x" (.bits 7)))
  check "scalar statement rejects mismatched actual declaration width"
    (!(ScalarStatements.canAssign ctx (scope (.var ⟨"x", .bits 7⟩)) "x" (.bits 8)))
  check "scalar statement rejects mismatched actual declaration name"
    (!(ScalarStatements.canAssign ctx (scope (.var ⟨"other", .bits 8⟩)) "x" (.bits 8)))
  check "scalar statement rejects missing declaration"
    (!(ScalarStatements.canAssign ctx default "x" (.bits 8)))
  check "scalar statement rejects missing source binding"
    (!(ScalarStatements.canAssign [] localScope "x" (.bits 8)))
  check "scalar statement rejects malformed unused context"
    (!(ScalarStatements.canAssign (ctx ++ [("", .boolean)]) localScope "x" (.bits 8)))
  check "scalar statement rejects duplicate context"
    (!(ScalarStatements.canAssign (ctx ++ ctx) localScope "x" (.bits 8)))

end ScalarStatementTests
