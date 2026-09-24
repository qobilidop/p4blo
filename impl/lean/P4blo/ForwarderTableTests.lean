import P4blo.ForwarderTables
import P4blo.CallReturnTests

/-! Independent finite install/lookup answers. No action or table application
is executed here; arbitrary-address coverage is the separate core theorem. -/
namespace P4blo.ForwarderTableTests
open P4bloIR ForwarderTables

def shapeProfiles : List (String × ForwarderTables.Shape) :=
  [("empty", .empty), ("network", .network), ("host", .host),
   ("network-host", .networkHost), ("host-network", .hostNetwork)]

-- Membership flags are hand-written answers, not produced by prefix matching.
def addresses : List (Nat × Bool × Bool) :=
  [(0, false, false), (0x0a0001ff, false, false),
   (0x0a000200, true, false), (0x0a000201, true, false),
   (0x0a000202, true, true), (0x0a000203, true, false),
   (0x0a0002ff, true, false), (0x0a000300, false, false),
   (0xffffffff, false, false)]

def networkData (high : Bool) : RouteData :=
  if high then ⟨⟨0xffffffffffff, by decide⟩, ⟨511, by decide⟩⟩
  else ⟨⟨0x222222222222, by decide⟩, ⟨2, by decide⟩⟩
def hostData (high : Bool) : RouteData :=
  if high then ⟨⟨0xfffffffffffe, by decide⟩, ⟨510, by decide⟩⟩
  else ⟨⟨0x333333333333, by decide⟩, ⟨3, by decide⟩⟩
def defaultData (high : Bool) : RouteData :=
  if high then ⟨⟨0, by decide⟩, ⟨0, by decide⟩⟩
  else ⟨⟨0x444444444444, by decide⟩, ⟨1, by decide⟩⟩

structure Profile where
  name : String
  shape : ForwarderTables.Shape
  mode : String
  high : Bool

def Profile.config (p : Profile) : Config :=
  ⟨p.shape, networkData p.high, hostData p.high,
    if p.mode == "drop" then .drop else if p.mode == "noop" then .noAction
    else .forward (defaultData p.high)⟩

def profiles : List Profile :=
  shapeProfiles.flatMap fun (name, shape) =>
    ["drop", "noop", "forward"].flatMap fun mode =>
      [false, true].map fun high => ⟨s!"{name}/{mode}/{high}", shape, mode, high⟩

private def expectedCall (which : String) (high : Bool) : ActionCall :=
  if which == "drop" then ⟨"drop", []⟩
  else if which == "noop" then ⟨"NoAction", []⟩
  else
    let (mac, port) := if which == "host" then
      (if high then (0xfffffffffffe, 510) else (0x333333333333, 3))
    else if which == "network" then
      (if high then (0xffffffffffff, 511) else (0x222222222222, 2))
    else (if high then (0, 0) else (0x444444444444, 1))
    ⟨"ipv4_forward", [.bits 48 mac, .bits 9 port]⟩

private def expectedMatch (p : Profile) (network host : Bool) : Match :=
  let hasHost := [ForwarderTables.Shape.host, .networkHost, .hostNetwork].any
    fun s => decide (s = p.shape)
  let hasNetwork := [ForwarderTables.Shape.network, .networkHost, .hostNetwork].any
    fun s => decide (s = p.shape)
  if hasHost && host then ⟨some (expectedCall "host" p.high), true⟩
  else if hasNetwork && network then ⟨some (expectedCall "network" p.high), true⟩
  else ⟨some (expectedCall p.mode p.high), false⟩

private def expectedEntries (p : Profile) : Array Entry :=
  let network : Entry := ⟨[.lpm 167772672 24], expectedCall "network" p.high, 0⟩
  let host : Entry := ⟨[.lpm 167772674 32], expectedCall "host" p.high, 0⟩
  match p.shape with
  | .empty => #[]
  | .network => #[network]
  | .host => #[host]
  | .networkHost => #[network, host]
  | .hostNetwork => #[host, network]

def mapsJson (i : Installed) : Lean.Json := Lean.Json.mkObj [
  ("entries", Lean.Json.mkObj (i.entries.toList.map fun (key, values) =>
    ((Lean.toJson [key.1, key.2]).compress, Lean.toJson (values.map Entry.toJson)))),
  ("defaults", Lean.Json.mkObj (i.defaults.toList.map fun (key, value) =>
    ((Lean.toJson [key.1, key.2]).compress, value.map ActionCall.toJson |>.getD .null)))]

def matchJson (m : Match) : Lean.Json := Lean.Json.mkObj [
  ("hit", Lean.toJson m.hit), ("action", m.action.map ActionCall.toJson |>.getD .null)]

def snapshot (p : Profile) : IO Lean.Json := do
  let c := p.config
  let i ← IO.ofExcept (Installed.build Forwarder.index (some c.input))
  let observations ← addresses.mapM fun (q, _, _) => do
    let m ← IO.ofExcept (i.lookup ref [Bits.wrap 32 q])
    pure (Lean.Json.mkObj [("address", Lean.toJson q), ("match", matchJson m)])
  pure (Lean.Json.mkObj [("name", Lean.toJson p.name), ("input", c.input.toJson),
    ("maps", mapsJson i), ("lookups", Lean.toJson observations)])

private def expectError (name : String) (result : Except String α) : IO Unit :=
  match result with
  | .error _ => pure ()
  | .ok _ => throw (IO.userError s!"accepted invalid table operation: {name}")

private def rejectionChecks : IO Unit := do
  let i ← IO.ofExcept (Installed.build Forwarder.index)
  let a := networkEntry (networkData false)
  let b := hostEntry (hostData false)
  let n ← IO.ofExcept (i.install ref a)
  let h ← IO.ofExcept (i.install ref b)
  expectError "duplicate /24" (n.install ref a)
  expectError "duplicate /32" (h.install ref b)
  for (name, bad) in [
      ("noncanonical", { a with keys := [.lpm 0x0a000201 24] }),
      ("prefix33", { a with keys := [.lpm 0 33] }),
      ("key count", { a with keys := [] }),
      ("nonzero priority", { a with priority := 1 }),
      ("unknown action", { a with action := ⟨"missing", []⟩ }),
      ("argument width", { a with action := ⟨"ipv4_forward", [.bits 47 1, .bits 9 2]⟩ }),
      ("argument overflow", { a with action := ⟨"ipv4_forward", [.bits 48 1, .bits 9 512]⟩ })] do
    expectError name (i.install ref bad)
  expectError "scope" (i.install ("Other", "ipv4_lpm") a)
  expectError "empty lookup keys" (i.lookup ref [])
  expectError "extra lookup key" (i.lookup ref [Bits.wrap 32 0, Bits.wrap 32 1])
  expectError "bad default" (i.setDefault ref (some ⟨"missing", []⟩))
  -- Outside the universal family's fixed /24 and host address: executable
  -- extremal prefix controls, not an extra universal theorem.
  let zero ← IO.ofExcept (i.install ref { a with keys := [.lpm 0 0] })
  let max ← IO.ofExcept (zero.install ref { b with keys := [.lpm 0xffffffff 32] })
  for (q, expected) in [(0, a.action), (0xfffffffe, a.action), (0xffffffff, b.action)] do
    let m ← IO.ofExcept (max.lookup ref [Bits.wrap 32 q])
    unless m == ⟨some expected, true⟩ do
      throw (IO.userError "wrong extremal prefix answer")

def run : IO Unit := do
  rejectionChecks
  unless profiles.length == 30 && addresses.length == 9 do
    throw (IO.userError "table profile coverage changed")
  for p in profiles do
    let i ← IO.ofExcept (Installed.build Forwarder.index (some p.config.input))
    unless CallReturnTests.indexJson i.index == CallReturnTests.indexJson Forwarder.index do
      throw (IO.userError "installed index changed")
    unless i.entries.size == 1 && i.defaults.size == 1 do
      throw (IO.userError "unexpected installed map keys")
    unless i.entries[ref]? == some (expectedEntries p) &&
        i.defaults[ref]? == some (some (expectedCall p.mode p.high)) do
      throw (IO.userError s!"wrong complete installed maps: {p.name}")
    for (q, network, host) in addresses do
      let m ← IO.ofExcept (i.lookup ref [Bits.wrap 32 q])
      unless m == expectedMatch p network host do
        throw (IO.userError s!"wrong independent route answer: {p.name}/{q}")
    let restored ← IO.ofExcept (i.setDefault ref none)
    unless restored.defaults.getD ref none == some ⟨"drop", []⟩ do
      throw (IO.userError "absent override must restore drop")
  IO.println "270 independent forwarder route/default answers passed"

end P4blo.ForwarderTableTests
