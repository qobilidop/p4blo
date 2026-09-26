import P4bloArchTest.Check

/-! Actual host installation must reject before an independently observable
missing-parser trap. This is operational precedence, not global validity. -/

open P4bloIR P4bloArch

namespace HostTrapTests

def tests : T Unit := do
  -- Actual host installation must reject before an independently observable
  -- missing-parser trap. This is operational precedence, not global validity.
  let indexed := Index.build { (default : BlockLibrary) with structTypes := [⟨"M", []⟩] }
  match indexed with
  | .error _ => check "host trap index builds" false
  | .ok index => do
    let sw : V1Model := {
      index, parser := "PacketEntryTrap", ingress := "", deparser := ""
      metadataType := "M", ingressPort := none, parserError := none
      egressPort := none, egressSpec := none, ports := 4 }
    let externs := P4bloArch.externs (Std.HashMap.ofList [("sentinel", .counter #[7, 0, 19])])
    check "host trap control reaches actual packet entry"
      (sw.run externs ⟨[]⟩ 0 ByteArray.empty matches .error "unknown block 'PacketEntryTrap'")
    for host in [Entries.mk [⟨"C", "Missing", [], some ⟨"NoAction", []⟩⟩],
        Entries.mk [⟨"C", "Missing", [⟨[], ⟨"NoAction", []⟩, 0⟩], none⟩]] do
      check "host rejection precedes actual packet entry"
        (sw.run externs host 0 ByteArray.empty matches .error "no table 'Missing' in block 'C'")

end HostTrapTests
