import P4blo.ForwarderAction
import P4blo.GuardedCallPrefixTests
import P4blo.CallReturnTests
import P4bloArch.Externs

namespace P4blo.ForwarderActionTests
open P4bloIR P4bloIR.Execution P4bloIR.ScalarStatements Fields ForwarderAction

structure Case where
  ev : Bool
  iv : Bool
  drop : Bool
  ttl : Fin 256
  high : Bool

def cases : List Case :=
  [false, true].flatMap fun ev => [false, true].flatMap fun iv =>
  [false, true].flatMap fun drop => ([0, 1, 255] : List (Fin 256)).flatMap fun ttl =>
  [false, true].map fun high => ⟨ev, iv, drop, ttl, high⟩

def Case.name (c : Case) : String := s!"{c.ev}-{c.iv}-{c.drop}-{c.ttl.val}-{c.high}"
def Case.dst (c : Case) : Fin (2 ^ 48) := if c.high then 0xfffffffffffe else 0x020202020202
def Case.port (c : Case) : Fin 512 := if c.high then 511 else 2

def source (c : Case) : Snapshot :=
  { dst := 0x010203040506, src := 0x111213141516, etherType := 0x0800, ethernetValid := c.ev
    version := 4, ihl := 5, diffserv := 17, totalLen := 26, identification := 37
    flags := 5, fragOffset := 47, ttl := c.ttl, protocol := 17, checksum := 0x9876
    ipSrc := 0x0a000101, ipDst := 0x0a000202, ipv4Valid := c.iv
    ingress := 3, egress := 7, drop := c.drop }

private def bits (width value : Nat) : Value := .bits (Bits.wrap width value)

def initial (c : Case) : Run :=
  { index := Forwarder.index
    frame := { populated (restore (source c)) with
      vars := (((populated (restore (source c))).vars.insert "untouched" (bits 8 165)).insert
        "dstAddr" (bits 48 99)).insert "port" (bits 9 77) }
    entries := some {
      index := Forwarder.index
      entries := ({} : Std.HashMap (String × String) (Array Entry)).insert
        ("MyIngress", "ipv4_lpm") #[⟨[.lpm 0x0a000200 24], ⟨"drop", []⟩, 7⟩]
      defaults := ({} : Std.HashMap (String × String) (Option ActionCall)).insert
        ("MyIngress", "ipv4_lpm") (some ⟨"NoAction", []⟩) }
    externs := { model := P4bloArch.model, instances := (({} : Std.HashMap String ExternState).insert
      "sentinel" (.register 8 #[3, 9, 27])) }
    packet := some ⟨ByteArray.mk #[0xde, 0xad, 0xbe, 0xef], 0xdeadbeef, 3⟩
    emitter := some ⟨5, 3⟩
    visits := ((({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 13).insert
      ("sentinel", "one") 1) }

/-- Literal independent answer: no policy, authored Ref or execution result
is used to determine expected fields. The checksum deliberately stays old. -/
def expectedHeaders (c : Case) : Value := .struct "headers" [
  .header "ethernet_t" c.ev [bits 48 c.dst.val, bits 48 0x010203040506, bits 16 0x0800],
  .header "ipv4_t" c.iv [bits 4 4, bits 4 5, bits 8 17, bits 16 26, bits 16 37,
    bits 3 5, bits 13 47, bits 8 (if c.ttl.val == 0 then 255 else c.ttl.val - 1),
    bits 8 17, bits 16 0x9876, bits 32 0x0a000101, bits 32 0x0a000202]]
def expectedMeta (c : Case) : Value := .struct "metadata" [bits 9 3, bits 9 c.port.val, .bool c.drop]
def expectedFrame (c : Case) : Frame :=
  { (initial c).frame with vars := (((initial c).frame.vars.insert "hdr" (expectedHeaders c)).insert
    "meta" (expectedMeta c)) }

private def sameFrame (a b : Frame) : Bool :=
  GuardedCallPrefixTests.sameScope a.scope b.scope &&
    GuardedCallPrefixTests.sameMap (· == ·) a.vars b.vars &&
    a.action == b.action && match a.actionVars, b.actionVars with
      | none, none => true
      | some x, some y => GuardedCallPrefixTests.sameMap (· == ·) x y
      | _, _ => false

def machine (c : Case) (continuation : List Work) : Machine :=
  { work := .tableAction (call c.dst c.port) :: continuation, run := initial c }

def writeContinuation : List Work := [.statement (.assign (.var "untouched") (.literal (.bits 8 0)))]
def faultContinuation : List Work := [.statement (.assign (.var "absent") (.literal (.bits 8 0)))]

private def sameContinuation : List Work → List Work → Bool
  | [], [] => true
  | .statement a :: as, .statement b :: bs => a.toJson == b.toJson && sameContinuation as bs
  | _, _ => false

def snapshot (c : Case) : IO Lean.Json := do
  let entered ← IO.ofExcept (GuardedCallPrefixTests.advance 1 (machine c []))
  let pending ← IO.ofExcept (GuardedCallPrefixTests.advance 10 (machine c []))
  let final ← IO.ofExcept (GuardedCallPrefixTests.advance 11 (machine c []))
  pure (Lean.Json.mkObj [
    ("name", Lean.toJson c.name), ("call", (call c.dst c.port).toJson),
    ("before", CallReturnTests.runJson (initial c)),
    ("entered", CallReturnTests.runJson entered.run),
    ("pending", CallReturnTests.runJson pending.run),
    ("after", CallReturnTests.runJson final.run), ("steps", Lean.toJson (11 : Nat))])

example : (policy (source ⟨false, false, true, 0, false⟩) 0x020202020202 2).src =
    0x010203040506 := rfl
example : (policy (source ⟨false, false, true, 0, false⟩) 0x020202020202 2).ttl.val = 255 := rfl
example : (policy (source ⟨true, true, false, 1, true⟩) 0xfffffffffffe 511).ttl.val = 0 := rfl

/-- Independent asymmetric raw constructors pin the source observation's
meaning, beyond the two inverse laws (which could share a permutation). -/
example : (restore (source ⟨true, false, true, 0, false⟩)).toValues = [
    .struct "headers" [
      .header "ethernet_t" true [bits 48 0x010203040506, bits 48 0x111213141516, bits 16 0x0800],
      .header "ipv4_t" false [bits 4 4, bits 4 5, bits 8 17, bits 16 26, bits 16 37,
        bits 3 5, bits 13 47, bits 8 0, bits 8 17, bits 16 0x9876,
        bits 32 0x0a000101, bits 32 0x0a000202]],
    .struct "metadata" [bits 9 3, bits 9 7, .bool true]] := by rfl

def run : IO Unit := do
  unless cases.length == 48 do throw (IO.userError "action profiles missing")
  for c in cases do
    let before := initial c
    let (outcome, after) := (runActionCall (call c.dst c.port)).run before
    unless outcome.isOk && sameFrame after.frame (expectedFrame c) &&
        GuardedCallPrefixTests.sameShared before after do
      throw (IO.userError s!"selected action policy/state mismatch: {c.name}")
    for continuation in [[], writeContinuation, faultContinuation] do
      let pending ← IO.ofExcept (GuardedCallPrefixTests.advance 10 (machine c continuation))
      match pending.work with
      | .actionReturn outer none :: tail =>
        unless sameContinuation tail continuation && sameFrame outer before.frame &&
            sameFrame pending.run.frame { (expectedFrame c) with
              action := some "ipv4_forward", actionVars := some (parameters c.dst c.port) } &&
            pending.fault.isNone && GuardedCallPrefixTests.sameShared before pending.run do
          throw (IO.userError "one-step-short actionReturn state is wrong")
      | _ => throw (IO.userError "ten steps must still retain actionReturn")
      let final ← IO.ofExcept (GuardedCallPrefixTests.advance 11 (machine c continuation))
      unless sameContinuation final.work continuation && final.fault.isNone &&
          sameFrame final.run.frame (expectedFrame c) &&
          GuardedCallPrefixTests.sameShared before final.run do
        throw (IO.userError "eleven steps changed the continuation/state boundary")
    let written ← IO.ofExcept (GuardedCallPrefixTests.advance 12 (machine c writeContinuation))
    unless written.run.frame.vars["untouched"]? == some (bits 8 0) do
      throw (IO.userError "pending continuation write control was inert")
    let faulted ← IO.ofExcept (GuardedCallPrefixTests.advance 12 (machine c faultContinuation))
    unless faulted.fault.isSome do throw (IO.userError "pending fault control was inert")
    let (bad, badRun) := (runActionCall ⟨"ipv4_forward", [.bits 48 c.dst.val]⟩).run before
    unless !bad.isOk && sameFrame badRun.frame before.frame &&
        GuardedCallPrefixTests.sameShared before badRun do
      throw (IO.userError "wrong arity must reject before installing action storage")
  IO.println "48 selected-action answers and 144 exact pending/return boundaries passed"

end P4blo.ForwarderActionTests
