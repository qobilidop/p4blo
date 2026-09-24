import P4blo.GuardedCallPrefix
import P4blo.GuardedForwardTests
import P4blo.CallEntryTests
import P4bloArch.Externs

namespace P4blo.GuardedCallPrefixTests
open P4bloIR P4bloIR.Execution P4bloIR.PlainCallEntry
open Fields FieldCommandExamples

abbrev Case := GuardedForwardTests.Case

def source (c : Case) (priorDrop : Bool) : Store roots :=
  ForwardPolicy.restore (GuardedForwardTests.input c priorDrop)

def initial (suffix : List Stmt) (c : Case) (priorDrop : Bool) : Run :=
  let run := CallEntryTests.initial c.ethernetValid c.ipv4Valid
  let s := source c priorDrop
  let index := CallEntry.WithBody.index (GuardedCallPrefix.body suffix)
  let vars := run.frame.vars
    |>.insert "source_hdr" (s.get .here).toValue
    |>.insert "source_meta" (s.get (.there .here)).toValue
    |>.insert "source_route" (s.get (.there (.there .here))).toValue
  { run with
    index
    entries := run.entries.map (fun e =>
      { e with
        index := index
        entries := e.entries.insert ("untouched", "table") #[⟨[], ⟨"sentinelEntry", []⟩, 7⟩] })
    visits := run.visits.insert ("sentinel", "one") 1
    frame := { run.frame with vars } }

/-- Literal hand-derived boundary counts, not a command cost interpreter. -/
def count (c : Case) : Nat :=
  if !c.ethernetValid then 11
  else if !c.ipv4Valid then 14
  else if !c.hit then 17
  else if c.ttl.val == 0 then 20
  else if c.ttl.val == 1 then 23
  else 31

def advance : Nat → Machine → Except String Machine
  | 0, machine => .ok machine
  | n + 1, machine => match step machine with
    | .inl _ => .error "call completed before guarded prefix boundary"
    | .inr next => advance n next

def machine (suffix : List Stmt) (c : Case) (priorDrop : Bool) : Machine :=
  { work := .block "RewriteBody" args :: CallEntryTests.continuation,
    run := initial suffix c priorDrop }

def ended (suffix : List Stmt) (c : Case) (priorDrop : Bool) : Except String Machine :=
  advance (count c) (machine suffix c priorDrop)

/-- Constructive application with a real caller for arbitrary source-profile
inputs and arbitrary suffix, not an assumed body-entry frame. -/
theorem concrete_prefix (suffix : List Stmt) (c : Case) (priorDrop : Bool) :
    ∃ frame, Steps (machine suffix c priorDrop)
      { work := .statements suffix ::
          .blockReturn (initial suffix c priorDrop).frame params args :: CallEntryTests.continuation,
        run := { (initial suffix c priorDrop) with frame } } := by
  obtain ⟨frame, trace, _⟩ := GuardedCallPrefix.source_prefix (initial suffix c priorDrop)
    ((source c priorDrop).get .here) ((source c priorDrop).get (.there .here))
    ((source c priorDrop).get (.there (.there .here))) CallEntryTests.observer suffix
    CallEntryTests.continuation rfl ⟨rfl, rfl⟩
    (by simp [initial, Frame.read?, CallEntryTests.initial, CallEntryTests.caller, Std.HashMap.getElem_insert])
    (by simp [initial, Frame.read?, CallEntryTests.initial, CallEntryTests.caller, Std.HashMap.getElem_insert])
    (by simp [initial, Frame.read?, CallEntryTests.initial, CallEntryTests.caller])
    (by simp [initial, Frame.read?, CallEntryTests.initial, CallEntryTests.caller, Std.HashMap.getElem_insert])
  exact ⟨frame, trace⟩

def faultSuffix : List Stmt :=
  [.assign (.var "scratch") (.literal (.bits 8 200)),
   .verify (.literal (.boolean false)) "guarded-suffix-must-stay-pending"]

/-- Complete, order-independent map observations, not selected-key sentinels. -/
def sameMap [BEq κ] [Hashable κ] (same : α → α → Bool)
    (left right : Std.HashMap κ α) : Bool :=
  left.size == right.size && left.toList.all (fun (key, value) =>
    (right[key]?).any (same value))

def sameScope (left right : BlockScope) : Bool :=
  left.block == right.block && sameMap (· == ·) left.vars right.vars &&
    sameMap (· == ·) left.actions right.actions &&
    sameMap (sameMap (· == ·)) left.actionParams right.actionParams &&
    sameMap (· == ·) left.tables right.tables && sameMap (· == ·) left.states right.states

def sameIndex (left right : Index) : Bool :=
  left.program == right.program && sameMap (· == ·) left.headerTypes right.headerTypes &&
    sameMap (· == ·) left.structTypes right.structTypes && sameMap (· == ·) left.enumTypes right.enumTypes &&
    sameMap (· == ·) left.externTypes right.externTypes && sameMap (· == ·) left.externInstances right.externInstances &&
    sameMap (· == ·) left.blocks right.blocks && sameMap sameScope left.scopes right.scopes &&
    left.programNames.size == right.programNames.size && left.programNames.toList.all right.programNames.contains &&
    sameMap (· == ·) left.errors right.errors

def sameExtern (left right : ExternState) : Bool := left == right

def sameShared (left right : Run) : Bool :=
  sameIndex left.index right.index &&
    (match left.entries, right.entries with
      | none, none => true
      | some l, some r => sameIndex l.index r.index && sameMap (· == ·) l.entries r.entries &&
          sameMap (· == ·) l.defaults r.defaults
      | _, _ => false) &&
    sameMap sameExtern left.externs.instances right.externs.instances &&
    left.packet.map (fun p => (p.data, p.value, p.cursor)) == right.packet.map (fun p => (p.data, p.value, p.cursor)) &&
    left.emitter.map (fun e => (e.value, e.width)) == right.emitter.map (fun e => (e.value, e.width)) &&
    sameMap (· == ·) left.visits right.visits

def checkProjections : IO Unit := do
  let index := CallEntry.WithBody.index (GuardedCallPrefix.body CallBodyEntry.observerSuffix)
  for changed in [
      { index with program := { index.program with errors := ["changed"] } },
      { index with headerTypes := index.headerTypes.insert "changed" default },
      { index with structTypes := index.structTypes.insert "changed" default },
      { index with enumTypes := index.enumTypes.insert "changed" default },
      { index with externTypes := index.externTypes.insert "changed" default },
      { index with externInstances := index.externInstances.insert "changed" default },
      { index with blocks := index.blocks.insert "changed" default },
      { index with scopes := index.scopes.insert "changed" default },
      { index with programNames := index.programNames.insert "changed" },
      { index with errors := index.errors.insert "changed" 99 }] do
    if sameIndex index changed then throw (IO.userError "incomplete native Index projection")
  let scope := CallEntry.WithBody.scope (GuardedCallPrefix.body CallBodyEntry.observerSuffix)
  for changed in [
      { scope with block := { scope.block with name := "changed" } },
      { scope with vars := scope.vars.insert "changed" default },
      { scope with actions := scope.actions.insert "changed" default },
      { scope with actionParams := scope.actionParams.insert "changed" {} },
      { scope with tables := scope.tables.insert "changed" default },
      { scope with states := scope.states.insert "changed" default }] do
    if sameScope scope changed then throw (IO.userError "incomplete native scope projection")
    if sameIndex index { index with scopes := index.scopes.insert "RewriteBody" changed } then
      throw (IO.userError "incomplete native indexed scope projection")

def snapshot (c : Case) (priorDrop : Bool) : IO Lean.Json := do
  let m ← IO.ofExcept (ended CallBodyEntry.observerSuffix c priorDrop)
  let queue := match m.work with
    | [.statements suffix, .blockReturn caller ps aa, .block "mustRemainPending" []] =>
      Lean.Json.mkObj [("suffix", Lean.toJson (suffix.map Stmt.toJson)),
        ("params", Lean.toJson (ps.map Param.toJson)), ("args", Lean.toJson (aa.map Arg.toJson)),
        ("caller", CallEntryTests.bindingsJson caller ["source_hdr", "source_meta", "source_route", "hdr", "caller_only"])]
    | _ => .null
  return Lean.Json.mkObj [
    ("name", Lean.toJson c.name), ("priorDrop", Lean.toJson priorDrop),
    ("steps", Lean.toJson (count c)), ("faultNone", Lean.toJson m.fault.isNone),
    ("vars", CallEntryTests.bindingsJson m.run.frame ["hdr", "meta", "route", "observer", "scratch", "unrelated", "caller_only"]),
    ("scopeBlock", m.run.frame.scope.block.toJson), ("queue", queue),
    ("packet", m.run.packet.map (fun p => Lean.toJson [Lean.toJson (p.data.data.map UInt8.toNat), Lean.toJson p.value, Lean.toJson p.cursor]) |>.getD .null),
    ("emitter", m.run.emitter.map (fun e => Lean.toJson [e.value, e.width]) |>.getD .null)]

def run : IO Unit := do
  checkProjections
  for c in GuardedForwardTests.cases do
    for priorDrop in [false, true] do
      for suffix in [[], CallBodyEntry.observerSuffix, faultSuffix] do
        let before := initial suffix c priorDrop
        for changed in [
            { before with entries := before.entries.map (fun e => { e with entries := {} }) },
            { before with entries := before.entries.map (fun e => { e with defaults := {} }) },
            { before with entries := before.entries.map (fun e => { e with index := { e.index with errors := e.index.errors.insert "changed" 99 } }) },
            { before with externs := {} }, { before with visits := {} },
            { before with packet := none }, { before with emitter := none }] do
          if sameShared before changed then throw (IO.userError "incomplete native shared projection")
        let entry ← IO.ofExcept (advance 1 (machine suffix c priorDrop))
        unless entry.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 0)) &&
            entry.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 0)) &&
            entry.run.frame.read? "observer" == some CallEntryTests.observer do
          throw (IO.userError "guarded call entry must precede local assignments")
        let ready ← IO.ofExcept (advance 6 (machine suffix c priorDrop))
        unless ready.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 19)) &&
            ready.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 165)) do
          throw (IO.userError "guarded call local boundary constants")
        for (root, actual) in [("hdr", "source_hdr"), ("meta", "source_meta"), ("route", "source_route")] do
          unless ready.run.frame.read? root == before.frame.read? actual do
            throw (IO.userError "guarded call ran body before initializer boundary")
        let m ← IO.ofExcept (ended suffix c priorDrop)
        let expected := ForwardPolicy.restore { GuardedForwardTests.expected c with scratch := 19 }
        unless m.fault.isNone do throw (IO.userError "guarded call prefix faulted")
        for root in ["hdr", "meta", "route", "scratch"] do
          unless m.run.frame.read? root == expected.bindings[root]? do
            throw (IO.userError s!"guarded call independent source {root}/{c.name}")
        unless m.run.frame.read? "observer" == some CallEntryTests.observer &&
            m.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 165)) &&
            m.run.frame.vars.size == 6 && m.run.frame.action.isNone && m.run.frame.actionVars.isNone &&
            sameScope m.run.frame.scope (CallEntry.WithBody.scope (GuardedCallPrefix.body suffix)) do
          throw (IO.userError "guarded call extra/scope state")
        match m.work with
        | [.statements pending, .blockReturn caller ps aa, .block "mustRemainPending" []] =>
          unless pending == suffix && caller.vars.toList == before.frame.vars.toList &&
              sameScope caller.scope before.frame.scope && caller.action.isNone &&
              caller.actionVars.isNone && ps == params && aa == args do
            throw (IO.userError "guarded call changed exact suffix/caller/return")
        | _ => throw (IO.userError "guarded call queue boundary")
        unless sameShared m.run before &&
            m.run.packet.any (fun p => p.data == ⟨#[0xde, 0xad, 0xbe, 0xef]⟩ && p.value == 0xdeadbeef && p.cursor == 3) &&
            m.run.emitter.any (fun e => e.value == 5 && e.width == 3) &&
            m.run.entries.any (fun e => e.entries.size == 1 &&
              e.entries[("untouched", "table")]? == some #[⟨[], ⟨"sentinelEntry", []⟩, 7⟩] && e.defaults.size == 1 &&
              e.defaults[("untouched", "table")]? == some (some ⟨"sentinelAction", []⟩)) &&
            (m.run.externs.instances["sentinel"]?).any (fun e => e.register? == some (8, #[3, 9, 27])) && m.run.visits[("parser", "state")]? == some 13 do
          throw (IO.userError "guarded call shared sentinels changed")
        if suffix == faultSuffix then
          let premature ← IO.ofExcept (advance 2 m)
          unless premature.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 200)) do
            throw (IO.userError "suffix negative control did not write")
          let (outcome, _) := (Execution.run m.work).run m.run
          unless (match outcome with
            | .error (.parse e) => e == "guarded-suffix-must-stay-pending"
            | _ => false) do throw (IO.userError "suffix negative control did not fault")
        if suffix.isEmpty then
          let (outcome, _) := (Execution.run m.work).run m.run
          unless (match outcome with
            | .error (.interp e) => e == "unknown block 'mustRemainPending'"
            | _ => false) do throw (IO.userError "return/continuation negative control did not fault")
  IO.println "192 actual guarded call prefixes with independent counts/state and pending-fault controls passed"

end P4blo.GuardedCallPrefixTests
