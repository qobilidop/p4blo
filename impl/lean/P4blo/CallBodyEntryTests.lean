import P4blo.CallBodyEntry
import P4blo.CallEntryTests

namespace P4blo.CallBodyEntryTests
open P4bloIR P4bloIR.Execution P4bloIR.PlainCallEntry

def profiles : List (String × List Stmt) :=
  [("empty", []), ("guarded-wrapper", CallBodyEntry.body),
   ("faulting", [.verify (.literal (.boolean false)) "body-must-not-run"])]

def initial (body : List Stmt) (ev iv : Bool) : Run :=
  let run := CallEntryTests.initial ev iv
  { run with
    index := CallEntry.WithBody.index body
    entries := run.entries.map (fun entries => { entries with index := CallEntry.WithBody.index body }) }

def entered (body : List Stmt) (ev iv : Bool) : Except String Machine :=
  match step { work := .block "RewriteBody" args :: CallEntryTests.continuation
               run := initial body ev iv } with
  | .inr machine => .ok machine
  | .inl _ => .error "call entry unexpectedly completed"

/-- Concrete application for every body and validity pair. Locals remain zero;
the arbitrary body is still pending, including intentionally faulting bodies. -/
theorem concrete_entry (body : List Stmt) (ev iv : Bool) : ∃ zero,
    Frame.forBlock (CallEntry.WithBody.index body) (CallEntry.WithBody.block body) = .ok zero ∧
    (dispatch (.block "RewriteBody" args)).run (initial body ev iv) =
      (.ok [.runBlock (CallEntry.WithBody.block body),
        .blockReturn (CallEntryTests.caller ev iv) (CallEntry.WithBody.block body).params args],
       { (initial body ev iv) with
         frame := boundFrame zero (CallEntryTests.hdr ev iv).toValue
           (CallEntryTests.metadataValue ev iv).toValue
           (CallEntryTests.routeValue ev iv).toValue CallEntryTests.observer }) := by
  obtain ⟨zero, hz, _, _, _, _, _, hd, _⟩ :=
    CallEntry.source_entry_with_body body (initial body ev iv)
      (CallEntryTests.hdr ev iv) (CallEntryTests.metadataValue ev iv)
      (CallEntryTests.routeValue ev iv) CallEntryTests.observer CallEntryTests.continuation
      rfl ⟨rfl, rfl⟩
      (by simp [initial, CallEntryTests.initial, CallEntryTests.caller, Frame.read?, Std.HashMap.getElem_insert])
      (by simp [initial, CallEntryTests.initial, CallEntryTests.caller, Frame.read?, Std.HashMap.getElem_insert])
      (by simp [initial, CallEntryTests.initial, CallEntryTests.caller, Frame.read?, Std.HashMap.getElem_insert])
      (by simp [initial, CallEntryTests.initial, CallEntryTests.caller, Frame.read?, Std.HashMap.getElem_insert])
  exact ⟨zero, hz, hd⟩

def snapshot (name : String) (body : List Stmt) (ev iv : Bool) : IO Lean.Json := do
  let m ← IO.ofExcept (entered body ev iv)
  let queue := match m.work with
    | [.runBlock b, .blockReturn caller ps aa, .block "mustRemainPending" []] =>
      Lean.Json.mkObj [("block", b.toJson), ("params", Lean.toJson (ps.map Param.toJson)),
        ("args", Lean.toJson (aa.map Arg.toJson)),
        ("caller", CallEntryTests.bindingsJson caller ["source_hdr", "source_meta", "source_route", "hdr", "caller_only"])]
    | _ => .null
  return Lean.Json.mkObj [
    ("name", Lean.toJson name), ("ev", Lean.toJson ev), ("iv", Lean.toJson iv),
    ("faultNone", Lean.toJson m.fault.isNone),
    ("scopeBlock", m.run.frame.scope.block.toJson),
    ("vars", CallEntryTests.bindingsJson m.run.frame ["hdr", "meta", "route", "observer", "scratch", "unrelated", "caller_only"]),
    ("queue", queue)]

def run : IO Unit := do
  for (name, body) in profiles do
    for ev in [false, true] do
      for iv in [false, true] do
        let m ← IO.ofExcept (entered body ev iv)
        unless m.fault.isNone && m.run.frame.scope.block == CallEntry.WithBody.block body do
          throw (IO.userError s!"body-bearing entry scope: {name}")
        match m.work with
        | [.runBlock b, .blockReturn caller ps aa, .block "mustRemainPending" []] =>
          unless b == CallEntry.WithBody.block body && ps == params && aa == args &&
              caller.read? "caller_only" == some (.bits (Bits.wrap 9 301)) do
            throw (IO.userError s!"body-bearing pending queue: {name}")
        | _ => throw (IO.userError s!"body-bearing queue shape: {name}")
        unless m.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 0)) &&
            m.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 0)) &&
            m.run.frame.read? "observer" == some CallEntryTests.observer do
          throw (IO.userError s!"body or observer ran during entry: {name}")
  IO.println "12 body-parametric entry scope/queue/local/observer answers passed"

end P4blo.CallBodyEntryTests
