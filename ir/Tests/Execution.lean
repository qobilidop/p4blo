import Tests.Check

/-! Proof-visible execution and continuation regressions, including malformed
inputs whose fault and frame behavior must survive the executor refactor. -/

open P4blo

namespace ExecutionTests

-- These proofs unfold the actual runner via finite traces. Ordinary `partial`
-- definitions did not permit these statements to be proved by their equations.
example (run : Run) : (execute []).run run = (.ok (), run) := by
  change Execution.drive { work := [.statements []], run } = _
  exact (Execution.Finishes.next rfl (.done rfl)).sound

example (run : Run) (error : String) :
    (executeOne (.verify (.literal (.boolean false)) error)).run run =
      (.error (.parse error), run) := by
  change Execution.drive { work := [.statement (.verify (.literal (.boolean false)) error)], run } = _
  exact (Execution.Finishes.next rfl (.done rfl)).sound

private def bits (n : Nat) : Value := .bits (Bits.wrap 8 n)
private def lit (n : Nat) : Expr := .literal (.bits 8 n)
private def stop : Stmt := .verify (.literal (.boolean false)) "InnerFault"
private def output (name : String) : Param := { name, type := .bits 8, direction := .out }

private def caller : Block := { (default : Block) with
  name := "Caller", kind := .control, locals := [{ name := "x", type := .bits 8 }] }

private def setup (blocks : List Block) : Except String Run := do
  let index ← Index.build { (default : Program) with blocks }
  let frame ← Frame.forBlock index caller
  pure { index, frame }

def tests : T Unit := do
  let inner := { (default : Block) with
    name := "Inner", kind := .control, params := [output "p", output "q"],
    body := [.assign (.var "p") (lit 42), stop] }
  checkOk "machine block copyback fault overrides callee fault and keeps earlier writes"
    (do
      let run ← setup [caller, inner]
      let (result, run) := (callBlock "Inner" [.lvalue (.var "x"), .lvalue (.var "missing")]).run run
      pure (match result with
            | .error (.interp "unknown variable 'missing' in block 'Caller'") => true
            | _ => false,
        run.frame.block.name, run.frame.read? "x", run.frame.action))
    (· == (true, "Caller", some (bits 42), none))
  let leaf := { inner with params := [output "p"] }
  let middle := { (default : Block) with
    name := "Middle", kind := .control, params := [output "m"],
    body := [.callBlock "Inner" [.lvalue (.var "m")]] }
  checkOk "machine nested block unwinding copies every frame back"
    (do
      let run ← setup [caller, middle, leaf]
      let (result, run) := (callBlock "Middle" [.lvalue (.var "x")]).run run
      pure (match result with
            | .error (.parse "InnerFault") => true
            | _ => false,
        run.frame.block.name, run.frame.read? "x"))
    (· == (true, "Caller", some (bits 42)))
  let action : Action := {
    name := "fail", params := [output "p"],
    body := [.assign (.var "p") (lit 42), .assign (.var "x") (lit 7), stop] }
  let actionCaller := { caller with actions := [action] }
  checkOk "machine action fault preserves its layer and does not copy arguments back"
    (do
      let run ← setup [actionCaller]
      let (result, run) := (callAction "fail" [.lvalue (.var "x")]).run run
      pure (match result with
            | .error (.parse "InnerFault") => true
            | _ => false,
        run.frame.action, run.frame.read? "p", run.frame.read? "x"))
    (· == (true, some "fail", some (bits 42), some (bits 7)))
  let successCaller := { caller with actions := [{ action with body := [.assign (.var "p") (lit 42)] }] }
  checkOk "machine action return restores outer parameters before copyback"
    (do
      let run ← setup [successCaller]
      let outer := { run.frame with
        action := some "outer", actionVars := some (Std.HashMap.ofList [("outerParam", bits 5)]) }
      let run := { run with frame := outer }
      let (result, run) := (callAction "fail" [.lvalue (.var "outerParam")]).run run
      pure (result matches .ok (), run.frame.action, run.frame.read? "outerParam", run.frame.read? "p"))
    (· == (true, some "outer", some (bits 42), none))
  checkOk "machine fault skips remaining caller statements"
    (do
      let run ← setup [caller, leaf]
      let (result, run) := (execute [.callBlock "Inner" [.lvalue (.var "x")],
        .assign (.var "x") (lit 99)]).run run
      pure (match result with
            | .error (.parse "InnerFault") => true
            | _ => false,
        run.frame.read? "x"))
    (· == (true, some (bits 42)))
  -- The action sets hit true. A default-action miss must overwrite it false
  -- only after the action returns, and must retain true if the action faults.
  let hitAction : Action := {
    name := "mark", params := [],
    body := [.assign (.var "hit") (.literal (.boolean true))] }
  let table : Table := {
    name := "t", keys := [], actions := ["mark"],
    defaultAction := some { action := "mark", args := [] }, constDefaultAction := false,
    constEntries := [], size := 0 }
  for fail in [false, true] do
    let block := { caller with
      locals := [{ name := "hit", type := .boolean }],
      actions := [{ hitAction with body := hitAction.body ++ (if fail then [stop] else []) }],
      tables := [table] }
    checkOk s!"machine hit continuation follows action success only: fault={fail}"
      (do
        let index ← Index.build { (default : Program) with blocks := [block] }
        let frame ← Frame.forBlock index block
        let entries ← Installed.build index none
        let (result, run) := (applyTable "t" (some (.var "hit"))).run { index, frame, entries := some entries }
        pure (match result with | .error _ => true | .ok () => false,
          run.frame.read? "hit", run.frame.action))
      (· == (fail, some (.bool fail), if fail then some "mark" else none))

end ExecutionTests
