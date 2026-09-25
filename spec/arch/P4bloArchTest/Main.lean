import P4bloArchTest.Check
import P4bloArchTest.Forwarder
import P4bloArchTest.Externs
import P4bloArchTest.CRC
import P4bloArchTest.ExternFamilies
import P4bloArchTest.ExecutionCertificate
import P4bloArchTest.CertificateWire
import P4bloArchTest.HostTrap
import P4bloArchTest.Coverage
import P4bloArchTest.NonVacuity

/-!
The `P4bloArchTest` library holds everything in this package that only the
gate runs: the test modules this driver imports, the proof audit
`P4bloArchTest.ArchProofAudit` and the fixtures under
`P4bloArchTest/fixtures/`. It is a default target, so `lake build`
elaborates every module and checks the audit's `#guard_msgs` pins;
`lake test` then runs this driver. `scripts/check-lean.sh` does both.

Tests for the reference architecture: the forwarder's vectors replayed under
the switch, the extern families, the certificate example and its wire
adapter, and the csum16 literal of the progress example. Run by `lake test`
from the `spec/arch/` directory; the fixture paths may also be given as
arguments (the program JSON, then the vectors JSON), and default to the IR
specification's copies. The coverage witness table is read from
`P4bloArchTest/fixtures/witnesses.json`, the csum16 program from
`P4bloArchTest/fixtures/csum16.json`.
-/

open P4bloIR

def main (args : List String) : IO UInt32 := do
  let fixture := args.head?.getD "../ir/P4bloIRTest/forwarder.json"
  let vectors := (args.drop 1).head?.getD "../ir/P4bloIRTest/forwarder_vectors.json"
  let text ← IO.FS.readFile fixture
  let vectorsText ← IO.FS.readFile vectors
  let ((), failures) ← (do
    match Program.fromJsonString text with
    | .ok p =>
      check "fixture decodes" true
      forwarderReplayTests p vectorsText
      CoverageTests.tests p
      CoverageTests.witnessTests "P4bloArchTest/fixtures/witnesses.json"
    | .error e =>
      IO.println s!"     got: {e}"
      check "fixture decodes" false
    ExternTests.tests
    CRCTests.tests
    ExternFamiliesTests.tests
    ExecutionCertificateTests.tests
    certificateWireTests
    HostTrapTests.tests
    ArchTests.Csum16.tests "P4bloArchTest/fixtures/csum16.json").run []
  if failures.isEmpty then
    IO.println "all tests passed"
    return 0
  else
    IO.println s!"{failures.length} failed: {failures}"
    return 1
