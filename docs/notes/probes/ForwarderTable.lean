import P4blo.ForwarderAction

/-! Unregistered feasibility probe. These fixed checks are not a universal
route-selection proof or a new application guarantee. -/
namespace ForwarderTableProbe
open P4bloIR
set_option maxRecDepth 4096

def ref : TableRef := ("MyIngress", "ipv4_lpm")
def route (network prefixLen dst port : Nat) : Entry :=
  ⟨[.lpm network prefixLen], ⟨"ipv4_forward", [.bits 48 dst, .bits 9 port]⟩, 0⟩
def network : Entry := route 0x0a000200 24 0x222222222222 2
def host : Entry := route 0x0a000202 32 0x333333333333 3
def config (reverse : Bool) : Entries :=
  ⟨[⟨"MyIngress", "ipv4_lpm", if reverse then [host, network] else [network, host], none⟩]⟩
def installed (reverse : Bool) : Installed :=
  (Installed.build P4blo.Forwarder.index (some (config reverse))).toOption.getD
    { index := P4blo.Forwarder.index }

theorem installed_forward : Installed.build P4blo.Forwarder.index (some (config false)) =
    .ok (installed false) := by cbv
theorem installed_reverse : Installed.build P4blo.Forwarder.index (some (config true)) =
    .ok (installed true) := by cbv

theorem host_forward : (installed false).lookup ref [Bits.wrap 32 0x0a000202] =
    .ok ⟨some host.action, true⟩ := by cbv
theorem host_reverse : (installed true).lookup ref [Bits.wrap 32 0x0a000202] =
    .ok ⟨some host.action, true⟩ := by cbv
theorem network_hit : (installed false).lookup ref [Bits.wrap 32 0x0a000203] =
    .ok ⟨some network.action, true⟩ := by cbv
theorem miss_drop : (installed false).lookup ref [Bits.wrap 32 0x0a000300] =
    .ok ⟨some ⟨"drop", []⟩, false⟩ := by cbv

-- This is the arithmetic boundary needed for the universal query theorem:
-- actual shift matching agrees with an independently stated numeric range.
theorem network_range (q : Nat) :
    Installed.keyValueMatches (.lpm 0x0a000200 24) (Bits.wrap 32 q) =
      decide (0x0a000200 ≤ q % 2 ^ 32 ∧ q % 2 ^ 32 < 0x0a000300) := by
  apply Bool.eq_iff_iff.mpr
  simp [Installed.keyValueMatches, Bits.wrap, Nat.shiftRight_eq_div_pow]
  omega

#print axioms installed_forward
#print axioms installed_reverse
#print axioms host_forward
#print axioms host_reverse
#print axioms network_hit
#print axioms miss_drop
#print axioms network_range

end ForwarderTableProbe
