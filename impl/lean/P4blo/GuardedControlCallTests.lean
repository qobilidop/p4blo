import P4blo.GuardedControlCall
import P4blo.GuardedCallPrefixTests
import P4blo.CallReturnTests

namespace P4blo.GuardedControlCallTests
open P4bloIR P4bloIR.Execution P4bloIR.PlainCallEntry
open Fields FieldCommandExamples
open GuardedCallPrefixTests (sameScope sameIndex sameShared)
abbrev Case := GuardedForwardTests.Case

def initial (c : Case) (priorDrop : Bool) : Run :=
  let run := GuardedCallPrefixTests.initial [] c priorDrop
  let vars := run.frame.vars |>.insert "scratch" (.bits (Bits.wrap 8 41)) |>.insert "unrelated" (.bits (Bits.wrap 8 42))
  { run with frame := { run.frame with vars } }

def source (c : Case) (priorDrop : Bool) : Store roots := GuardedCallPrefixTests.source c priorDrop

theorem concrete_call (c : Case) (priorDrop : Bool) :
    (callBlock "RewriteBody" args).run (initial c priorDrop) =
      (.ok (), GuardedControlCall.result (initial c priorDrop)
        ((source c priorDrop).get .here) ((source c priorDrop).get (.there .here))
        ((source c priorDrop).get (.there (.there .here))) CallEntryTests.observer) := by
  apply GuardedControlCall.call_correct _ _ _ _ _
  · change CallEntry.WithBody.index (GuardedCallPrefix.body []) = GuardedControlCall.index
    rw [← GuardedControlCall.body_prefix]
    rfl
  · exact ⟨rfl, rfl⟩
  all_goals simp [initial, GuardedCallPrefixTests.initial, source,
    CallEntryTests.initial, CallEntryTests.caller, Frame.read?, Std.HashMap.getElem_insert]

/-- Literal complete-call counts; independently anchored, not computed by
evaluating the source command or by traversing the IR body. -/
def count (c : Case) : Nat :=
  if !c.ethernetValid then 13
  else if !c.ipv4Valid then 16
  else if !c.hit then 19
  else if c.ttl.val == 0 then 22
  else if c.ttl.val == 1 then 25
  else 33

def machine (c : Case) (priorDrop : Bool) (continuation : List Work) : Machine :=
  { work := .block "RewriteBody" args :: continuation, run := initial c priorDrop }

def ended (c : Case) (priorDrop : Bool) (continuation : List Work) : Except String Machine :=
  GuardedCallPrefixTests.advance (count c) (machine c priorDrop continuation)

def expectedCaller (c : Case) (priorDrop : Bool) : Frame :=
  let old := (initial c priorDrop).frame
  let expected := ForwardPolicy.restore (GuardedForwardTests.expected c)
  let vars := old.vars
    |>.insert "source_hdr" (expected.get .here).toValue
    |>.insert "source_meta" (expected.get (.there .here)).toValue
  { old with vars }

def faultBody : List Stmt :=
  [.assign (.var "scratch") (.literal (.bits 8 200)),
   .verify (.literal (.boolean false)) "after-successful-guarded-call"]

def snapshot (c : Case) (priorDrop : Bool) : IO Lean.Json := do
  let short ← IO.ofExcept (GuardedCallPrefixTests.advance (count c - 1) (machine c priorDrop []))
  let complete ← IO.ofExcept (ended c priorDrop [])
  let pending := match short.work with
    | [.blockReturn caller ps aa] =>
        CallReturnTests.frameJson caller == CallReturnTests.frameJson (initial c priorDrop).frame && ps == params && aa == args
    | _ => false
  return Lean.Json.mkObj [
    ("name", Lean.toJson c.name), ("priorDrop", Lean.toJson priorDrop),
    ("steps", Lean.toJson (count c)), ("faultNone", Lean.toJson complete.fault.isNone),
    ("empty", Lean.toJson complete.work.isEmpty), ("returnPendingOneStepShort", Lean.toJson pending),
    ("run", CallReturnTests.runJson complete.run), ("callee", CallReturnTests.frameJson short.run.frame)]

def run : IO Unit := do
  GuardedCallPrefixTests.checkProjections
  for c in GuardedForwardTests.cases do
    for priorDrop in [false, true] do
      for continuation in [[], [.block "mustRemainPending" []], [.statements faultBody]] do
        let before := initial c priorDrop
        unless count c == GuardedCallPrefixTests.count c + 2 do
          throw (IO.userError "complete call needs empty-pop and return")
        let short ← IO.ofExcept (GuardedCallPrefixTests.advance (count c - 1) (machine c priorDrop continuation))
        match short.work with
        | .blockReturn caller ps aa :: _ =>
          unless CallReturnTests.frameJson caller == CallReturnTests.frameJson before.frame &&
              ps == params && aa == args && short.run.frame.scope.block.name == "RewriteBody" do
            throw (IO.userError "one-step-short return boundary")
        | _ => throw (IO.userError "return was executed too early")
        let expectedSource := ForwardPolicy.restore { GuardedForwardTests.expected c with scratch := 19 }
        for root in ["hdr", "meta", "route", "scratch"] do
          unless short.run.frame.read? root == expectedSource.bindings[root]? do
            throw (IO.userError "independent retained callee source")
        unless short.run.frame.vars.size == 6 && short.run.frame.read? "observer" == some CallEntryTests.observer &&
            short.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 165)) &&
            short.run.frame.action.isNone && short.run.frame.actionVars.isNone &&
            sameScope short.run.frame.scope (CallEntry.WithBody.scope GuardedControlCall.body) && sameShared short.run before do
          throw (IO.userError "retained callee full state")
        let m ← IO.ofExcept (ended c priorDrop continuation)
        unless m.fault.isNone && sameShared m.run before &&
            CallReturnTests.frameJson m.run.frame == CallReturnTests.frameJson (expectedCaller c priorDrop) do
          throw (IO.userError "independent complete caller/shared answer")
        match continuation, m.work with
        | [], [] =>
            let (outcome, actual) := (callBlock "RewriteBody" args).run before
            unless (outcome matches .ok ()) && sameShared actual before &&
                CallReturnTests.frameJson actual.frame == CallReturnTests.frameJson (expectedCaller c priorDrop) do
              throw (IO.userError "actual callBlock normal completion")
        | [.block "mustRemainPending" []], [.block "mustRemainPending" []] =>
            let (outcome, _) := (Execution.run m.work).run m.run
            unless (match outcome with | .error (.interp e) => e == "unknown block 'mustRemainPending'" | _ => false) do
              throw (IO.userError "pending block negative control")
        | [.statements _], [.statements pending] =>
            unless pending == faultBody do throw (IO.userError "changed pending fault body")
            let (outcome, after) := (Execution.run m.work).run m.run
            unless after.frame.read? "scratch" == some (.bits (Bits.wrap 8 200)) &&
                (match outcome with | .error (.parse e) => e == "after-successful-guarded-call" | _ => false) do
              throw (IO.userError "pending caller write/fault negative control")
        | _, _ => throw (IO.userError "complete call consumed continuation")
  IO.println "192 whole guarded control calls with exact normal-return/pending-work answers passed"

end P4blo.GuardedControlCallTests
