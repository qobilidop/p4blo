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
import P4bloArchTest.V1Model
import P4bloArchTest.Coverage

/-!
The `P4bloArchTest` library holds everything in this package that only the
gate runs: the test modules this driver imports and the fixtures under
`P4bloArchTest/fixtures/`. It is a default target, so `lake build`
elaborates every module;
`lake test` then runs this driver. `scripts/check-lean.sh` does both.

Tests for v1model: ordered stages, packet fate, the forwarder's vectors,
extern families, binding validation and assembly codecs.
Run by `lake test` from the `spec/arch/` directory; the fixture paths may also be given as
arguments (the program JSON, then the vectors JSON), and default to this
architecture package's copies. The coverage witness table is read from
`P4bloArchTest/fixtures/witnesses.json`.
-/

open P4bloArch P4bloIR

def main (args : List String) : IO UInt32 := do
  let fixture := args.head?.getD "P4bloArchTest/fixtures/forwarder.json"
  let vectors := (args.drop 1).head?.getD "P4bloArchTest/fixtures/forwarder_vectors.json"
  let text ← IO.FS.readFile fixture
  let vectorsText ← IO.FS.readFile vectors
  let ((), failures) ← (do
    match BlockAssembly.fromJsonString text with
    | .ok p =>
      check "fixture decodes" true
      check "headers and metadata" (p.headers == "headers" && p.metadata == "metadata")
      check "three exports" (p.exports.map Export.role == ["parser", "ingress", "deparser"])
      check "exported control" ((do
        let idx ← (Index.build p).toOption
        (p.toBlockBindings.exported? idx "ingress").map Block.name) == some "MyIngress")
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
    HostTrapTests.tests
    V1ModelTests.tests).run []
  if failures.isEmpty then
    IO.println "all tests passed"
    return 0
  else
    IO.println s!"{failures.length} failed: {failures}"
    return 1
