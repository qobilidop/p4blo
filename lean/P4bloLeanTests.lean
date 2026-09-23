import P4bloLean
import P4blo.Json
import P4bloLean.ScalarTests

def main : IO Unit := do
  P4bloLean.ScalarTests.run
  let source ← IO.FS.readFile "../ir/Tests/forwarder.json"
  let program ← IO.ofExcept (P4blo.Program.fromJsonString source)
  let (sw, externs) ← IO.ofExcept (P4bloLean.prepareSwitch program)
  let (result, _) ← IO.ofExcept (P4bloLean.runSwitch sw externs { tables := [] } 0 ByteArray.empty)
  -- The reference architecture still runs control after parser rejection.
  -- This program sets drop only inside its IPv4-valid table application.
  unless result.outputs == [(0, ByteArray.empty)] && result.diagnostic.isNone do
    throw (IO.userError "empty packet must preserve the forwarder's reference behavior")
  match P4bloLean.prepareSwitch (default : P4blo.Program) with
  | .error _ => pure ()
  | .ok _ => throw (IO.userError "missing switch exports must be rejected")
  IO.println "Lean package API tests passed"
