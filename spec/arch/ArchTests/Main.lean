import ArchTests.Check
import ArchTests.Forwarder
import ArchTests.Externs
import ArchTests.CRC
import ArchTests.ExternFamilies
import ArchTests.ExecutionCertificate
import ArchTests.CertificateWire
import ArchTests.HostTrap

/-!
Tests for the reference architecture: the forwarder's vectors replayed under
the switch, the extern families, the certificate example and its wire
adapter. Run by `lake test` from the `spec/arch/` directory; the fixture
paths may also be given as arguments (the program JSON, then the vectors
JSON), and default to the IR specification's copies.
-/

open P4bloIR

def main (args : List String) : IO UInt32 := do
  let fixture := args.head?.getD "../ir/Tests/forwarder.json"
  let vectors := (args.drop 1).head?.getD "../ir/Tests/forwarder_vectors.json"
  let text ← IO.FS.readFile fixture
  let vectorsText ← IO.FS.readFile vectors
  let ((), failures) ← (do
    match Program.fromJsonString text with
    | .ok p =>
      check "fixture decodes" true
      forwarderReplayTests p vectorsText
    | .error e =>
      IO.println s!"     got: {e}"
      check "fixture decodes" false
    ExternTests.tests
    CRCTests.tests
    ExternFamiliesTests.tests
    ExecutionCertificateTests.tests
    certificateWireTests
    HostTrapTests.tests).run []
  if failures.isEmpty then
    IO.println "all tests passed"
    return 0
  else
    IO.println s!"{failures.length} failed: {failures}"
    return 1
