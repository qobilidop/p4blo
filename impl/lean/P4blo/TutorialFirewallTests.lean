import P4blo.TutorialFirewallProof
import P4blo.GuardedCallPrefixTests
import P4bloArch.Externs

namespace P4blo.TutorialFirewallTests
open P4bloIR TutorialFirewall

private def bits (width value : Nat) : Value := .bits (Bits.wrap width value)

def expectedHeaders : Value := .struct "headers" [
  .header "ethernet_t" false [bits 48 0, bits 48 0, bits 16 0],
  .header "ipv4_t" false ([4, 4, 8, 16, 16, 3, 13, 8, 8, 16, 32, 32].map (bits · 0)),
  .header "tcp_t" false ([16, 16, 32, 32, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 16, 16, 16].map (bits · 0))]

def expectedVars : Std.HashMap String Value := Std.HashMap.ofList [
  ("hdr", expectedHeaders), ("meta", .struct "metadata" [bits 9 0, bits 9 0, .bool false]),
  ("reg_pos_one", bits 32 0), ("reg_pos_two", bits 32 0),
  ("reg_val_one", bits 1 0), ("reg_val_two", bits 1 0), ("direction", bits 1 0),
  ("crc16_result", bits 16 0), ("check_ports_hit", .bool false)]

def initial (ev drop overlay dirty : Bool) (tcpShape : Nat) : Run := Id.run do
  let tcpValue := match tcpShape with
    | 0 => Value.header "tcp_t" false []
    | 1 => .header "tcp_t" true [bits 7 83]
    | _ => .struct "UnusedUnknown" [.bool true, bits 65 0x12345]
  let headers := invalidHeaders
    (.header "ethernet_t" ev [bits 48 0x101, bits 48 0x202, bits 16 0x0800])
    tcpValue (if dirty then [.bool true, bits 9 511] else [])
  let values := (expectedVars.insert "hdr" headers).insert "meta"
    (.struct "metadata" [bits 9 3, bits 9 511, .bool drop])
  let values := if dirty then values.insertMany [
    ("reg_pos_one", bits 32 0xffffffff), ("reg_pos_two", bits 32 211),
    ("reg_val_one", bits 1 1), ("reg_val_two", bits 1 1), ("direction", bits 1 1),
    ("crc16_result", bits 16 0xffff), ("check_ports_hit", .bool true)] else values
  let values := values.insert "untouched" (.struct "Unrelated" [bits 5 17, .bool true])
  return {
    index := index
    frame := { initialFrame with
      vars := if overlay then values.insert "hdr" (.bool true) else values
      action := if overlay then some "operational-overlay" else none
      actionVars := if overlay then some (Std.HashMap.ofList [
        ("hdr", headers), ("reg_pos_one", .bool true), ("shadow", bits 17 0x12345)]) else none }
    entries := some {
      index := index
      entries := Std.HashMap.ofList [( ("MyIngress", "ipv4_lpm"),
        #[⟨[.lpm 0x0a000200 24], ⟨"drop", []⟩, 0⟩])]
      defaults := Std.HashMap.ofList [( ("MyIngress", "ipv4_lpm"), some ⟨"NoAction", []⟩)] }
    externs := { model := P4bloArch.model, instances := Std.HashMap.ofList [
      ("bloom_filter_1", .register 1 #[1, 0, 1]),
      ("bloom_filter_2", .register 1 #[0, 1]),
      ("csum", .checksum16), ("hash16", .crc16 104), ("hash32", .crc32 104),
      ("sentinel", .counter #[7, 9])] }
    packet := some ⟨ByteArray.mk #[0xde, 0xad, 0xbe, 0xef], 0xdeadbeef, 3⟩
    emitter := some ⟨0x1234, 13⟩
    visits := Std.HashMap.ofList [( ("sentinel", "state"), 13)] }

private def sameFrame (a b : Frame) : Bool :=
  GuardedCallPrefixTests.sameScope a.scope b.scope &&
  GuardedCallPrefixTests.sameMap (· == ·) a.vars b.vars && a.action == b.action &&
  match a.actionVars, b.actionVars with
  | none, none => true
  | some x, some y => GuardedCallPrefixTests.sameMap (· == ·) x y
  | _, _ => false

def run : IO Unit := do
  let actualIndex ← IO.ofExcept (Index.build program)
  let frame ← IO.ofExcept (Frame.forBlock actualIndex ingress)
  unless GuardedCallPrefixTests.sameMap (· == ·) frame.vars expectedVars &&
      frame.action.isNone && frame.actionVars.isNone &&
      GuardedCallPrefixTests.sameScope frame.scope scope do
    throw (IO.userError "actual firewall initialization differs from all nine independent roots")
  let mut count := 0
  for ev in [false, true] do
    for drop in [false, true] do
      for overlay in [false, true] do
        for dirty in [false, true] do
          for tcpShape in [0, 1, 2] do
            let before := initial ev drop overlay dirty tcpShape
            let (outcome, after) := (execute ingress.body).run before
            unless outcome.isOk && sameFrame before.frame after.frame &&
                GuardedCallPrefixTests.sameShared before after do
              throw (IO.userError "invalid IPv4 changed complete firewall Run")
            count := count + 1
  unless count == 48 do throw (IO.userError "missing firewall body profiles")
  IO.println "Nine initialized firewall roots and 48 complete invalid-body states passed"

end P4blo.TutorialFirewallTests
