import P4blo.ForwarderIngress
import P4blo.ForwarderApplyTests

namespace P4blo.ForwarderIngressTests
open P4bloIR P4bloIR.Execution

structure Case where
  base : ForwarderApplyTests.Case
  valid : Bool

def cases : List Case := ForwarderApplyTests.cases.flatMap fun c =>
  [⟨c, false⟩, ⟨c, true⟩]
def Case.name (c : Case) : String := s!"{c.base.name}/{c.valid}"
def Case.application (c : Case) : ForwarderApplyTests.Case :=
  { c.base with state := { c.base.state with iv := c.valid } }
def count (c : Case) : Nat := if c.valid then ForwarderApplyTests.count c.application + 5 else 3

private def field (name : String) : P4bloIR.Expr :=
  .member (.member (.var "hdr") "ipv4") name

/-- Independent raw syntax anchor, including checksum concat order/target. -/
def checksum : Stmt := .conditional (.isValid (.member (.var "hdr") "ipv4"))
  [.callExtern "csum" "compute"
    [.expr (["ihl", "diffserv", "totalLen", "identification", "flags",
      "fragOffset", "ttl", "protocol", "srcAddr", "dstAddr"].map field |>.foldl
        (.binary .concat) (field "version"))]
    (some (.member (.member (.var "hdr") "ipv4") "hdrChecksum"))] []

def expectedBody : List Stmt :=
  [.conditional (.isValid (.member (.var "hdr") "ipv4")) [.apply "ipv4_lpm" none] [], checksum]

private def workEqual : List Work → List Work → Bool
  | [], [] => true
  | .statements a :: as, .statements b :: bs =>
    a.map Stmt.toJson == b.map Stmt.toJson && workEqual as bs
  | .statement a :: as, .statement b :: bs => a.toJson == b.toJson && workEqual as bs
  | _, _ => false

private def sameState (a b : Run) : Bool :=
  ForwarderApplyTests.sameFrame a.frame b.frame && GuardedCallPrefixTests.sameShared a b

private def machine (run : Run) (continuation : List Work) : Machine :=
  { work := .statements Forwarder.ingress.body :: continuation, run }

def snapshot (c : Case) : IO Lean.Json := do
  let before ← ForwarderApplyTests.initial c.application
  let after ← IO.ofExcept (GuardedCallPrefixTests.advance (count c) (machine before []))
  let [.statements [pending]] := after.work | throw (IO.userError "pending checksum identity")
  pure (Lean.Json.mkObj [
    ("name", Lean.toJson c.name), ("input", c.base.route.config.input.toJson),
    ("before", CallReturnTests.runJson before), ("after", CallReturnTests.runJson after.run),
    ("pending", pending.toJson), ("steps", Lean.toJson (count c))])

/-- Deliberately unvalidated runtime controls. The raw theorem does not read
metadata or unused IPv4 fields and follows action-first hdr precedence. -/
def rawInitial (kind : Nat) : IO Run := do
  let base : ForwarderApplyTests.Case :=
    ⟨⟨"empty/drop/false", .empty, "drop", false⟩, 0, false, false,
      ⟨false, false, false, 0, false⟩, 0⟩
  let before ← ForwarderApplyTests.initial base
  let some parserScope := before.index.scopes["MyParser"]?
    | throw (IO.userError "actual parser scope missing")
  let invalid := Forwarder.invalidHeaders (.bool true)
    (if kind == 3 then [.bool false, .struct "unused" []] else [])
  let valid := Value.struct "headers" [.bool true, .header "ipv4_t" true []]
  let vars := (before.frame.vars.erase "meta").insert "hdr" (if kind < 2 then invalid else valid)
  let actionVars := if kind < 2 then none else some
    ((({} : Std.HashMap String Value).insert "hdr" invalid).insert "keep" (.bits (Bits.wrap 8 11)))
  let entries := if kind == 1 then some {
      index := (default : Index)
      entries := ({} : Std.HashMap (String × String) (Array Entry)).insert ("poison", "unused") #[]
      defaults := ({} : Std.HashMap (String × String) (Option ActionCall)).insert
        ("MyIngress", "ipv4_lpm") (some ⟨"missing", []⟩) }
    else none
  pure { before with entries, frame := { before.frame with
    vars, actionVars
    action := if kind < 2 then none else some "shadow"
    scope := if kind % 2 == 0 then before.frame.scope else parserScope } }

def rawSnapshot (kind : Nat) : IO Lean.Json := do
  let before ← rawInitial kind
  let after ← IO.ofExcept (GuardedCallPrefixTests.advance 3 (machine before []))
  pure (Lean.Json.mkObj [
    ("kind", Lean.toJson kind), ("before", CallReturnTests.runJson before),
    ("after", CallReturnTests.runJson after.run)])

/-- Constructive kernel witness with absent metadata/entries, unrelated
scope, and an invalid action hdr shadowing a valid block hdr. -/
private def witness : Run :=
  { index := Forwarder.index
    frame := { (default : Frame) with
      action := some "shadow"
      actionVars := some (({} : Std.HashMap String Value).insert "hdr"
        (Forwarder.invalidHeaders (.bool true) []))
      vars := ({} : Std.HashMap String Value).insert "hdr"
        (.struct "headers" [.bool true, .header "ipv4_t" true []]) } }

example (continuation : List Work) :
    Steps { work := .statements Forwarder.ingress.body :: continuation, run := witness }
      { work := .statements [ForwarderIngress.checksumConditional] :: continuation
        run := witness } := by
  apply ForwarderIngress.invalid_steps_header witness (.bool true) [] continuation rfl
  simp [witness, Frame.read?]

def run : IO Unit := do
  unless cases.length == 540 && (cases.filter (·.valid)).length == 270 do
    throw (IO.userError "ingress configuration/validity inventory changed")
  unless Forwarder.ingress.body.map Stmt.toJson == expectedBody.map Stmt.toJson do
    throw (IO.userError "full independent first/checksum syntax changed")
  for c in cases do
    let before ← ForwarderApplyTests.initial c.application
    let expected := { before with frame :=
      ForwarderApplyTests.expectedFrame c.application before c.valid false }
    for continuation in [[], ForwarderActionTests.writeContinuation,
        ForwarderActionTests.faultContinuation] do
      let start := machine before continuation
      let oneShort ← IO.ofExcept (GuardedCallPrefixTests.advance (count c - 1) start)
      unless workEqual oneShort.work (.statements [] :: .statements [checksum] :: continuation) &&
          sameState oneShort.run expected && oneShort.fault.isNone do
        throw (IO.userError s!"one-short branch-pop state/queue: {c.name}")
      let after ← IO.ofExcept (GuardedCallPrefixTests.advance (count c) start)
      unless workEqual after.work (.statements [checksum] :: continuation) &&
          sameState after.run expected && after.fault.isNone do
        throw (IO.userError s!"prefix complete state/queue: {c.name}")
      let expanded ← IO.ofExcept (GuardedCallPrefixTests.advance (count c + 1) start)
      unless workEqual expanded.work (.statement checksum :: .statements [] :: continuation) &&
          sameState expanded.run expected && expanded.fault.isNone do
        throw (IO.userError "next step must only expand pending checksum list")
      let guarded ← IO.ofExcept (GuardedCallPrefixTests.advance (count c + 2) start)
      let .conditional _ yes _ := checksum | throw (IO.userError "checksum syntax")
      unless workEqual guarded.work
          (.statements (if c.valid then yes else []) :: .statements [] :: continuation) &&
          sameState guarded.run expected && guarded.fault.isNone do
        throw (IO.userError "following step begins real checksum guard, not K")
  for kind in [0, 1, 2, 3] do
    let before ← rawInitial kind
    for continuation in [[], ForwarderActionTests.writeContinuation,
        ForwarderActionTests.faultContinuation] do
      let after ← IO.ofExcept (GuardedCallPrefixTests.advance 3 (machine before continuation))
      unless sameState before after.run && after.fault.isNone &&
          workEqual after.work (.statements [checksum] :: continuation) do
        throw (IO.userError "raw invalid prefix inspected metadata/entries/block hdr")
  IO.println "540 ingress prefixes, 1620 exact queue boundaries and 12 raw invalid controls passed"

end P4blo.ForwarderIngressTests
