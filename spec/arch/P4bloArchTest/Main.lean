import P4bloArchTest.Bindings
import P4bloArchTest.Interp
import P4bloArchTest.AssemblyCodec
import P4bloArch.Assembly
import P4bloArchTest.Check
import P4bloArchTest.Forwarder
import P4bloArchTest.Externs
import P4bloArchTest.CRC
import P4bloArchTest.ExternFamilies
import P4bloArchTest.HostTrap
import P4bloArchTest.Coverage

/-!
The `P4bloArchTest` library holds everything in this package that only the
gate runs: the test modules this driver imports and the fixtures under
`P4bloArchTest/fixtures/`. It is a default target, so `lake build`
elaborates every module;
`lake test` then runs this driver. `scripts/check-lean.sh` does both.

Tests for the reference architecture: the forwarder's vectors replayed under
the switch, the extern families, binding validation and assembly codecs.
Run by `lake test` from the `spec/arch/` directory; the fixture paths may also be given as
arguments (the program JSON, then the vectors JSON), and default to the IR
specification's copies. The coverage witness table is read from
`P4bloArchTest/fixtures/witnesses.json`.
-/

open P4bloArch P4bloIR

def main (args : List String) : IO UInt32 := do
  let fixture := args.head?.getD "../ir/P4bloIRTest/forwarder.json"
  let vectors := (args.drop 1).head?.getD "../ir/P4bloIRTest/forwarder_vectors.json"
  let text ← IO.FS.readFile fixture
  let vectorsText ← IO.FS.readFile vectors
  let ((), failures) ← (do
    match BlockAssembly.fromJsonString text with
    | .ok p =>
      check "fixture decodes" true
      check "headers and metadata" (p.headers == "headers" && p.metadata == "metadata")
      check "three exports" (p.exports.map Export.role == ["parser", "control", "deparser"])
      check "exported control" ((do
        let idx ← (Index.build p).toOption
        (p.toBlockBindings.exported? idx "control").map Block.name) == some "MyIngress")
      forwarderReplayTests p vectorsText
      CoverageTests.tests p
      CoverageTests.witnessTests "P4bloArchTest/fixtures/witnesses.json"
    | .error e =>
      IO.println s!"     got: {e}"
      check "fixture decodes" false
    BindingTests.tests
    interpTests
    AssemblyCodecTests.tests
    ExternTests.tests
    CRCTests.tests
    ExternFamiliesTests.tests
    HostTrapTests.tests).run []
  if failures.isEmpty then
    IO.println "all tests passed"
    return 0
  else
    IO.println s!"{failures.length} failed: {failures}"
    return 1
