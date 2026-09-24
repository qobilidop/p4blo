import P4blo.ForwarderApply
import P4blo.ForwarderTableTests
import P4blo.ForwarderActionTests

namespace P4blo.ForwarderApplyTests
open P4bloIR P4bloIR.Execution Fields ForwarderAction

structure Case where
  route : ForwarderTableTests.Profile
  address : Nat
  network : Bool
  host : Bool
  state : ForwarderActionTests.Case
  stateNumber : Nat

def states : List ForwarderActionTests.Case :=
  ForwarderActionTests.cases.filter fun c => !c.high

def cases : List Case :=
  let routes := ForwarderTableTests.profiles.flatMap fun p =>
    ForwarderTableTests.addresses.map fun (q, n, h) => (p, q, n, h)
  routes.zipIdx.map fun ((p, q, n, h), i) =>
    ⟨p, q, n, h, states[i % 24]?.getD ⟨false, false, false, 0, false⟩, i % 24⟩

def Case.name (c : Case) : String := s!"{c.route.name}/{c.address}/{c.stateNumber}"
def source (c : Case) : Snapshot :=
  { ForwarderActionTests.source c.state with ipDst := ⟨c.address % 2^32, Nat.mod_lt _ (by decide)⟩ }

def initial (c : Case) : IO Run := do
  let index ← IO.ofExcept (Index.build Forwarder.program)
  let frame ← IO.ofExcept (Frame.forBlock index Forwarder.ingress)
  let entries ← IO.ofExcept (Installed.build index (some c.route.config.input))
  let store := restore (source c)
  let vars := ((((frame.vars.insert "hdr" (store.get .here).toValue).insert
    "meta" (store.get (.there .here)).toValue).insert "untouched" (.bits (Bits.wrap 8 165))).insert
    "dstAddr" (.bits (Bits.wrap 48 99))).insert "port" (.bits (Bits.wrap 9 77))
  pure { (ForwarderActionTests.initial c.state) with
    index, entries := some entries
    frame := { frame with vars } }

/-- Finite independent winners, using hand-written membership flags rather
than calling the proved numeric policy or runtime prefix matcher. -/
def winner (c : Case) : String :=
  let hasHost := [ForwarderTables.Shape.host, .networkHost, .hostNetwork].any
    fun s => decide (s = c.route.shape)
  let hasNetwork := [ForwarderTables.Shape.network, .networkHost, .hostNetwork].any
    fun s => decide (s = c.route.shape)
  if hasHost && c.host then "host"
  else if hasNetwork && c.network then "network"
  else c.route.mode

def routeData (c : Case) : Nat × Nat :=
  if winner c == "host" then
    if c.route.high then (0xfffffffffffe, 510) else (0x333333333333, 3)
  else if winner c == "network" then
    if c.route.high then (0xffffffffffff, 511) else (0x222222222222, 2)
  else if c.route.high then (0, 0) else (0x444444444444, 1)

def hit (c : Case) : Bool := winner c == "host" || winner c == "network"
def forwards (c : Case) : Bool := !(winner c == "drop" || winner c == "noop")

def expectedCall (c : Case) : ActionCall :=
  if winner c == "drop" then ⟨"drop", []⟩
  else if winner c == "noop" then ⟨"NoAction", []⟩
  else ⟨"ipv4_forward", [.bits 48 (routeData c).1, .bits 9 (routeData c).2]⟩

def expectedParams (c : Case) : Std.HashMap String Value :=
  if forwards c then
    (({} : Std.HashMap String Value).insert "dstAddr" (.bits (Bits.wrap 48 (routeData c).1))).insert
      "port" (.bits (Bits.wrap 9 (routeData c).2))
  else {}

private def bits (n v : Nat) : Value := .bits (Bits.wrap n v)

/-- Literal complete record answers, independent of source restore/policy and
authored field paths. Application preserves checksum and header validities. -/
def expectedHeaders (c : Case) (final : Bool) : Value :=
  let rewrite := final && forwards c
  .struct "headers" [
    .header "ethernet_t" c.state.ev [
      bits 48 (if rewrite then (routeData c).1 else 0x010203040506),
      bits 48 (if rewrite then 0x010203040506 else 0x111213141516), bits 16 0x0800],
    .header "ipv4_t" c.state.iv [bits 4 4, bits 4 5, bits 8 17, bits 16 26, bits 16 37,
      bits 3 5, bits 13 47,
      bits 8 (if rewrite then (if c.state.ttl.val == 0 then 255 else c.state.ttl.val - 1)
        else c.state.ttl.val), bits 8 17, bits 16 0x9876, bits 32 0x0a000101, bits 32 c.address]]

def expectedMeta (c : Case) (final : Bool) : Value := .struct "metadata" [bits 9 3,
  bits 9 (if final && forwards c then (routeData c).2 else 7),
  .bool (if final && winner c == "drop" then true else c.state.drop)]

def expectedFrame (c : Case) (before : Run) (final active : Bool) : Frame :=
  { before.frame with
    vars := ((before.frame.vars.insert "hdr" (expectedHeaders c final)).insert
      "meta" (expectedMeta c final))
    action := if active then some (expectedCall c).action else none
    actionVars := if active then some (expectedParams c) else none }

def sameFrame (a b : Frame) : Bool :=
  GuardedCallPrefixTests.sameScope a.scope b.scope &&
    GuardedCallPrefixTests.sameMap (· == ·) a.vars b.vars && a.action == b.action &&
    match a.actionVars, b.actionVars with
    | none, none => true
    | some a, some b => GuardedCallPrefixTests.sameMap (· == ·) a b
    | _, _ => false

def count (c : Case) : Nat := if forwards c then 13 else if winner c == "drop" then 7 else 5
def machine (before : Run) (target : Option LValue) (continuation : List Work) : Machine :=
  { work := .table "ipv4_lpm" target :: continuation, run := before }

private def sameContinuation : List Work → List Work → Bool
  | [], [] => true
  | .statement a :: as, .statement b :: bs => a.toJson == b.toJson && sameContinuation as bs
  | _, _ => false

def snapshot (c : Case) : IO Lean.Json := do
  let before ← initial c
  let dispatched ← IO.ofExcept (GuardedCallPrefixTests.advance 1 (machine before none []))
  let [.tableAction call, .writeHit none actualHit] := dispatched.work
    | throw (IO.userError "unexpected actual dispatch queue")
  let entered ← IO.ofExcept (GuardedCallPrefixTests.advance 2 (machine before none []))
  let activeEnd ← IO.ofExcept (GuardedCallPrefixTests.advance (count c - 2) (machine before none []))
  let after ← IO.ofExcept (GuardedCallPrefixTests.advance (count c) (machine before none []))
  pure (Lean.Json.mkObj [
    ("name", Lean.toJson c.name), ("input", c.route.config.input.toJson),
    ("call", call.toJson), ("hit", Lean.toJson actualHit),
    ("before", CallReturnTests.runJson before), ("entered", CallReturnTests.runJson entered.run),
    ("activeEnd", CallReturnTests.runJson activeEnd.run), ("after", CallReturnTests.runJson after.run),
    ("steps", Lean.toJson (count c))])

private def controls (c : Case) : IO Unit := do
  let before ← initial c
  let defaultInput : Entries := ⟨[⟨"MyIngress", "ipv4_lpm", [], none⟩]⟩
  let installed ← IO.ofExcept (Installed.build before.index (some defaultInput))
  let start := { before with entries := some installed }
  let target := some Forwarder.dropFlag.lvalue
  let pending ← IO.ofExcept (GuardedCallPrefixTests.advance 6 (machine start target []))
  let after ← IO.ofExcept (GuardedCallPrefixTests.advance 7 (machine start target []))
  let metaTrue := Value.struct "metadata" [bits 9 3, bits 9 7, .bool true]
  let metaFalse := Value.struct "metadata" [bits 9 3, bits 9 7, .bool false]
  unless sameFrame pending.run.frame { start.frame with vars := start.frame.vars.insert "meta" metaTrue } &&
      sameFrame after.run.frame { start.frame with vars := start.frame.vars.insert "meta" metaFalse } &&
      GuardedCallPrefixTests.sameShared pending.run start &&
      GuardedCallPrefixTests.sameShared after.run start && after.work.isEmpty do
    throw (IO.userError "hit must overwrite drop only after its action, even on a miss")
  -- Manually supplied operational maps: not accepted host installations.
  let absent := { installed with defaults := installed.defaults.insert ForwarderTables.ref none }
  let absentRun := { start with entries := some absent }
  let absentEnd ← IO.ofExcept (GuardedCallPrefixTests.advance 2 (machine absentRun none []))
  unless absentEnd.work.isEmpty && sameFrame absentEnd.run.frame absentRun.frame &&
      GuardedCallPrefixTests.sameShared absentEnd.run absentRun do
    throw (IO.userError "optional absent action must differ from real empty NoAction")
  let broken := { installed with
    defaults := installed.defaults.insert ForwarderTables.ref (some ⟨"ipv4_forward", []⟩) }
  let badStart := { start with entries := some broken }
  let (fault, badEnd) := (applyTable "ipv4_lpm" target).run badStart
  let .error (.interp message) := fault | throw (IO.userError "expected an action arity fault")
  unless message == "action 'ipv4_forward' takes 2 arguments" &&
      sameFrame badEnd.frame badStart.frame &&
      GuardedCallPrefixTests.sameShared badEnd badStart do
    throw (IO.userError "throwing action must skip hit and preserve original state")

def run : IO Unit := do
  unless cases.length == 270 && states.length == 24 &&
      ((cases.map (·.stateNumber)).eraseDups.length == 24) do
    throw (IO.userError "route/state inventory changed")
  for c in cases do
    let before ← initial c
    unless sameFrame before.frame (expectedFrame c before false false) do
      throw (IO.userError "initial raw field/source anchor changed")
    let (outcome, final) := (applyTable "ipv4_lpm" none).run before
    unless outcome.isOk && sameFrame final.frame (expectedFrame c before true false) &&
        GuardedCallPrefixTests.sameShared before final do
      throw (IO.userError s!"application policy/shared-state mismatch: {c.name}")
    for continuation in [[], ForwarderActionTests.writeContinuation,
        ForwarderActionTests.faultContinuation] do
      let start := machine before none continuation
      let dispatchEnd ← IO.ofExcept (GuardedCallPrefixTests.advance 1 start)
      match dispatchEnd.work with
      | .tableAction call :: .writeHit none actualHit :: tail =>
        unless call == expectedCall c && actualHit == hit c && sameContinuation tail continuation &&
            sameFrame dispatchEnd.run.frame before.frame &&
            GuardedCallPrefixTests.sameShared before dispatchEnd.run do
          throw (IO.userError "real dispatch changed key state or selected wrong action/hit")
      | _ => throw (IO.userError "table dispatch queue identity")
      let entered ← IO.ofExcept (GuardedCallPrefixTests.advance 2 start)
      let activeEnd ← IO.ofExcept (GuardedCallPrefixTests.advance (count c - 2) start)
      unless sameFrame entered.run.frame (expectedFrame c before false true) &&
          sameFrame activeEnd.run.frame (expectedFrame c before true true) &&
          GuardedCallPrefixTests.sameShared before entered.run &&
          GuardedCallPrefixTests.sameShared before activeEnd.run do
        throw (IO.userError "actual active action layer/body result")
      let pending ← IO.ofExcept (GuardedCallPrefixTests.advance (count c - 1) start)
      match pending.work with
      | .writeHit none actualHit :: tail =>
        unless actualHit == hit c && sameContinuation tail continuation &&
            sameFrame pending.run.frame (expectedFrame c before true false) &&
            GuardedCallPrefixTests.sameShared before pending.run do
          throw (IO.userError "one-short hit/continuation/state boundary")
      | _ => throw (IO.userError "one short must still have writeHit pending")
      let finished ← IO.ofExcept (GuardedCallPrefixTests.advance (count c) start)
      unless sameContinuation finished.work continuation && finished.fault.isNone &&
          sameFrame finished.run.frame (expectedFrame c before true false) &&
          GuardedCallPrefixTests.sameShared before finished.run do
        throw (IO.userError "exact application continuation/state boundary")
    let written ← IO.ofExcept (GuardedCallPrefixTests.advance (count c + 1)
      (machine before none ForwarderActionTests.writeContinuation))
    unless written.run.frame.vars["untouched"]? == some (bits 8 0) do
      throw (IO.userError "pending write control was inert")
    let faulted ← IO.ofExcept (GuardedCallPrefixTests.advance (count c + 1)
      (machine before none ForwarderActionTests.faultContinuation))
    unless faulted.fault.isSome do throw (IO.userError "pending fault control was inert")
  for c in cases.take 24 do controls c
  IO.println "270 table applications, 810 exact queue boundaries and 24 hit/error controls passed"

end P4blo.ForwarderApplyTests
