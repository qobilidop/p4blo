import P4bloArchTest.Check
import P4bloArch.CertificateWire

open P4bloIR

private def certificateArtifact (seed : String) (fuel : Nat) (cell : String)
    (program : Program := P4bloArch.Certificate.Example.program) : Lean.Json :=
  Lean.Json.mkObj [
    ("format", .str "p4blo.example-certificate"), ("version", Lean.toJson (1 : Nat)),
    ("example", .str "register-counter-v1"), ("program", Lean.toJson program),
    ("initial", .arr #[.str seed, .str "0x9"]), ("fuel", Lean.toJson fuel),
    ("claim", Lean.Json.mkObj [
      ("completion", Lean.Json.mkObj [("kind", .str "success")]),
      ("register", .arr #[Lean.toJson (8 : Nat), .arr #[.str cell]]),
      ("counter", .arr #[.str "0xa"]),
      ("local", .arr #[Lean.toJson (8 : Nat), .str "0x2a"])])]

def certificateWireTests : T Unit := do
  check "wire certificate accepts the exact example"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x29" 10 "0x2a") matches .ok "accepted")
  check "wire certificate reports exhaustion separately"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x29" 9 "0x2a") matches .ok "exhausted")
  check "wire certificate binds initial state"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x28" 10 "0x2a") matches .ok "mismatch")
  check "wire certificate binds claimed state"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x29" 10 "0x2b") matches .ok "mismatch")
  check "wire certificate binds actual program"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x29" 10 "0x2a"
      { P4bloArch.Certificate.Example.program with name := "changed" }) matches .error _)
  check "wire certificate rejects noncanonical hex"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x029" 10 "0x2a") matches .error _)
  check "wire certificate rejects out-of-width initial state"
    (P4bloArch.CertificateWire.verify (certificateArtifact "0x100" 10 "0x2a") matches .error _)
  check "wire certificate rejects a missing envelope"
    (P4bloArch.CertificateWire.verify (Lean.Json.mkObj []) matches .error _)
