import P4blo.ForwarderProof
import P4blo.GuardedCallPrefixTests
import P4bloIR.Hex

namespace P4blo.ForwarderTests
open P4bloIR Forwarder

private def bits (width value : Nat) : Value := .bits (Bits.wrap width value)

def storedIPv4 (ttl : Nat) : List Value :=
  [bits 4 4, bits 4 5, bits 8 17, bits 16 26, bits 16 1, bits 3 0,
    bits 13 0, bits 8 ttl, bits 8 17, bits 16 0x9876,
    bits 32 0x0a000101, bits 32 0x0a000202]

def initial (valid drop : Bool) (port ttl : Nat) : Run :=
  { index
    frame := invalidFrame (.header "ethernet_t" valid
      [bits 48 0x0101, bits 48 1, bits 16 0x0800]) (storedIPv4 ttl)
      (.struct "metadata" [bits 9 3, bits 9 port, .bool drop])
    entries := some {
      index := index
      entries := ({} : Std.HashMap (String × String) (Array Entry)).insert
        ("MyIngress", "ipv4_lpm") #[⟨[.lpm 0x0a000200 24], ⟨"drop", []⟩, 0⟩]
      defaults := ({} : Std.HashMap (String × String) (Option ActionCall)).insert
        ("MyIngress", "ipv4_lpm") (some ⟨"NoAction", []⟩) }
    externs := { instances := (({} : Std.HashMap String ExternState).insert "csum" .checksum16).insert "sentinel" (.counter #[7, 9]) }
    packet := some ⟨ByteArray.mk #[0xde, 0xad, 0xbe, 0xef], 0xdeadbeef, 3⟩
    emitter := some ⟨0x1234, 13⟩
    visits := ({} : Std.HashMap (String × String) Nat).insert ("sentinel", "state") 13 }

theorem concrete_invalid (valid drop : Bool) (port ttl : Nat) :
    (execute ingress.body).run (initial valid drop port ttl) =
      (.ok (), initial valid drop port ttl) :=
  invalid_ipv4_control_unchanged _ _ _ _ rfl rfl

private def sameFrame (left right : Frame) : Bool :=
  GuardedCallPrefixTests.sameScope left.scope right.scope &&
    GuardedCallPrefixTests.sameMap (· == ·) left.vars right.vars &&
    left.action == right.action && left.actionVars.isNone && right.actionVars.isNone

def route : Entries :=
  { tables := [⟨"MyIngress", "ipv4_lpm",
    [⟨[.lpm 0x0a000200 24], ⟨"ipv4_forward", [.bits 48 0x202, .bits 9 2]⟩, 0⟩], none⟩] }

def run : IO Unit := do
  for valid in [false, true] do
    for drop in [false, true] do
      for port in [0, 3] do
        for ttl in [0, 1, 255] do
          let before := initial valid drop port ttl
          let (outcome, after) := (execute ingress.body).run before
          unless outcome.isOk && GuardedCallPrefixTests.sameShared before after &&
              sameFrame before.frame after.frame do
            throw (IO.userError "invalid IPv4 changed actual control Run")
  for valid in [false, true] do
    let original := initial valid false 3 0
    let ethernet := Value.header "ethernet_t" valid [bits 48 0x0101, bits 48 1, bits 16 0x0800]
    let headers := Value.struct "headers" [ethernet, .header "ipv4_t" true (storedIPv4 0)]
    let installed ← IO.ofExcept (Installed.build index (some { tables := [] }))
    let before := { original with
      entries := some installed
      frame := { original.frame with vars := original.frame.vars.insert "hdr" headers } }
    let (outcome, after) := (execute ingress.body).run before
    let expected := { before.frame with vars := (before.frame.vars.insert "hdr"
      (.struct "headers" [ethernet, .header "ipv4_t" true ((storedIPv4 0).set 9 (bits 16 0xa3bf))])).insert "meta" (.struct "metadata" [bits 9 3, bits 9 3, .bool true]) }
    unless outcome.isOk && GuardedCallPrefixTests.sameShared before after && sameFrame expected after.frame do
      throw (IO.userError "valid IPv4 table miss must still compute checksum after drop")
  let (sw, externs) ← IO.ofExcept (P4blo.prepareSwitch program 4)
  for (inputTTL, outputWord) in [("00", "ff11a4cf"), ("01", "0011a3d0"), ("40", "3f1164d0")] do
    let packet ← IO.ofExcept (hexToBytes? ("00000000010100000000000108004500001a00010000" ++
      inputTTL ++ "1100000a0001010a000202deadbeefcafe"))
    let expected ← IO.ofExcept (hexToBytes? ("00000000020200000000010108004500001a00010000" ++
      outputWord ++ "0a0001010a000202deadbeefcafe"))
    let (answer, _) ← IO.ofExcept (P4blo.runSwitch sw externs route 0 packet)
    unless answer.outputs == [(2, expected)] && answer.diagnostic.isNone do
      throw (IO.userError "in-memory Program: independent TTL/MAC/checksum answer")
  let arp ← IO.ofExcept (hexToBytes? "ffffffffffff000000000001080600010800060400010000000000010a0001010000000000000a000202")
  let (answer, _) ← IO.ofExcept (P4blo.runSwitch sw externs { tables := [] } 0 arp)
  unless answer.outputs == [(0, arp)] && answer.diagnostic.isNone do
    throw (IO.userError "in-memory Program: independent ARP pass-through")
  IO.println "24 invalid states, 2 post-drop checksums and 4 in-memory forwarder answers passed"

end P4blo.ForwarderTests
