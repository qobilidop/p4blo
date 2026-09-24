import P4blo
import P4blo.ForwarderTests
import P4blo.FieldActionWriteTests
import P4blo.ForwarderActionTests
import P4bloIR.Json
import P4blo.ScalarTests
import P4blo.ScalarCommandTests
import P4blo.FieldTests
import P4blo.FieldCommandTests
import P4blo.NamedFieldsTests
import P4blo.ForwardPolicyTests
import P4blo.CommandBlockTests
import P4blo.HeaderFieldTests
import P4blo.SourceZeroTests
import P4blo.HeaderReadExamples
import P4blo.InitialFrameTests
import P4blo.GuardedForwardTests
import P4blo.CommandPrefixTests
import P4blo.CallEntryTests
import P4blo.CallBodyEntryTests
import P4blo.CallInitializerTests
import P4blo.CallReturnTests
import P4blo.GuardedCallPrefixTests
import P4blo.GuardedControlCallTests

def main : IO Unit := do
  P4blo.ScalarTests.run
  P4blo.ScalarCommandTests.run
  P4blo.FieldTests.run
  P4blo.FieldCommandTests.run
  P4blo.NamedFieldsTests.run
  P4blo.ForwardPolicyTests.run
  P4blo.CommandBlockTests.run
  P4blo.HeaderFieldTests.run
  P4blo.SourceZeroTests.run
  P4blo.HeaderReadExamples.run
  P4blo.InitialFrameTests.run
  P4blo.GuardedForwardTests.run
  P4blo.CommandPrefixTests.run
  P4blo.CallEntryTests.run
  P4blo.CallBodyEntryTests.run
  P4blo.CallInitializerTests.run
  P4blo.CallReturnTests.run
  P4blo.GuardedCallPrefixTests.run
  P4blo.GuardedControlCallTests.run
  P4blo.ForwarderTests.run
  P4blo.FieldActionWriteTests.run
  P4blo.ForwarderActionTests.run
  let source ← IO.FS.readFile "../ir/Tests/forwarder.json"
  let program ← IO.ofExcept (P4bloIR.Program.fromJsonString source)
  let (sw, externs) ← IO.ofExcept (P4blo.prepareSwitch program)
  let (result, _) ← IO.ofExcept (P4blo.runSwitch sw externs { tables := [] } 0 ByteArray.empty)
  -- The reference architecture still runs control after parser rejection.
  -- This program sets drop only inside its IPv4-valid table application.
  unless result.outputs == [(0, ByteArray.empty)] && result.diagnostic.isNone do
    throw (IO.userError "empty packet must preserve the forwarder's reference behavior")
  match P4blo.prepareSwitch (default : P4bloIR.Program) with
  | .error _ => pure ()
  | .ok _ => throw (IO.userError "missing switch exports must be rejected")
  IO.println "Lean package API tests passed"
