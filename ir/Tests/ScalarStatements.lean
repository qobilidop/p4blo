import Tests.Check
import P4bloIR.ScalarStatements

open P4bloIR

namespace ScalarStatementTests

private def ctx : ScalarTyping.Context := [("x", .bits 8)]
private def scope (decl : VarDecl) : BlockScope :=
  { block := default, vars := ({} : Std.HashMap String VarDecl).insert "x" decl }

private def param (direction : Direction) : VarDecl := .param ⟨"x", .bits 8, direction⟩

/-- Operational collision witnesses, not validator-accepted declarations. -/
private def layered : Frame :=
  { scope := { block := { (default : Block) with name := "Layered" } }
    vars := ({} : Std.HashMap String Value).insert "blockOnly" (.bool false)
      |>.insert "x" (.bits (Bits.wrap 8 17)) |>.insert "untouched" (.error "Keep")
    action := some "active"
    actionVars := some (({} : Std.HashMap String Value).insert "x" (.bool false)
      |>.insert "actionOnly" (.bits (Bits.wrap 9 303))) }

/-- Genuine active-frame hypotheses discharge by kernel reduction; every
shared component of the surrounding Run remains arbitrary and unchanged. -/
theorem unshadowed_witness (run : Run) :
    (writeVar "blockOnly" (.bool true)).run { run with frame := layered } =
      (.ok (), { run with frame :=
        { layered with vars := layered.vars.insert "blockOnly" (.bool true) } }) := by
  apply ScalarStatements.writeVar_block_unshadowed (old := .bool false)
  · simp [layered]
  · simp only [layered, Std.HashMap.getElem?_insert]
    rfl

example : ¬ ScalarStatements.BlockFrame layered := by
  simp [ScalarStatements.BlockFrame, layered]

example : (readVar "x").run { index := default, frame := layered } =
    (.ok (.bool false), { index := default, frame := layered }) := by
  apply ScalarStatements.readVar_action (active := rfl)
  simp only [Std.HashMap.getElem?_insert]
  rfl

example : (writeVar "x" (.bool true)).run { index := default, frame := layered } =
    (.ok (), { index := default, frame := { layered with
      actionVars := some ((({} : Std.HashMap String Value).insert "x" (.bool false)
        |>.insert "actionOnly" (.bits (Bits.wrap 9 303))).insert "x" (.bool true)) } }) := by
  apply ScalarStatements.writeVar_action (active := rfl) (old := .bool false)
  simp only [Std.HashMap.getElem?_insert]
  rfl

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
  let initial : Run := { index := default, frame := layered }
  let read := (readVar "x").run initial
  check "active false value shadows block decoy" (read.1.toOption == some (.bool false))
  let blockWrite := (writeVar "blockOnly" (.bool true)).run initial
  check "unshadowed block write succeeds with action installed"
    (blockWrite.1.toOption.isSome && blockWrite.2.frame.vars["blockOnly"]? == some (.bool true))
  check "unshadowed write retains full action bindings"
    (blockWrite.2.frame.action == some "active" &&
      (blockWrite.2.frame.actionVars.map (·.size)) == some 2 &&
      blockWrite.2.frame.read? "x" == some (.bool false) &&
      blockWrite.2.frame.read? "actionOnly" == some (.bits (Bits.wrap 9 303)))
  check "unshadowed write retains block decoy and unrelated root"
    (blockWrite.2.frame.vars.size == 3 &&
      blockWrite.2.frame.vars["x"]? == some (.bits (Bits.wrap 8 17)) &&
      blockWrite.2.frame.vars["untouched"]? == some (.error "Keep") &&
      blockWrite.2.frame.scope.block.name == "Layered")
  let actionWrite := (writeVar "x" (.bool true)).run initial
  check "action hit writes active layer rather than block decoy"
    (actionWrite.1.toOption.isSome && actionWrite.2.frame.read? "x" == some (.bool true) &&
      actionWrite.2.frame.vars["x"]? == some (.bits (Bits.wrap 8 17)))
  check "action write retains both stores and action identity"
    (actionWrite.2.frame.vars.size == 3 &&
      (actionWrite.2.frame.actionVars.map (·.size)) == some 2 &&
      actionWrite.2.frame.action == some "active" &&
      actionWrite.2.frame.read? "blockOnly" == some (.bool false) &&
      actionWrite.2.frame.read? "untouched" == some (.error "Keep") &&
      actionWrite.2.frame.read? "actionOnly" == some (.bits (Bits.wrap 9 303)))
  let missing := (writeVar "missing" (.bool true)).run initial
  check "absent active and block root is not implicitly declared"
    (missing.1 matches .error (.interp "unknown variable 'missing' in block 'Layered'"))
  let empty := (writeVar "blockOnly" (.bool true)).run
    { initial with frame := { layered with actionVars := some {} } }
  check "empty installed action map permits existing block write"
    (empty.1.toOption.isSome && empty.2.frame.vars["blockOnly"]? == some (.bool true) &&
      empty.2.frame.action == some "active" && (empty.2.frame.actionVars.map (·.size)) == some 0)

end ScalarStatementTests
