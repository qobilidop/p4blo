import P4blo
import P4blo.ScalarExamples
import P4blo.ScalarCommandExamples
import P4blo.FieldTests
import P4blo.FieldCommandExamples
import P4blo.HeaderReadExamples
import P4blo.GuardedForwardTests
import P4blo.CallEntryTests
import P4blo.CallBodyEntryTests
import P4blo.CallReturnTests
import P4blo.GuardedCallPrefixTests
import P4blo.GuardedControlCallTests
import P4blo.ForwarderActionTests
import P4blo.ForwarderTableTests
import P4blo.ForwarderApplyTests
import P4bloIR.Json
import P4bloIR.Observe
import P4bloIR.Hex

/-!
The package's one executable, `p4blo`. Each subcommand is named after the
separate executable it replaces and does what that executable did.

Two subcommands, `leanForwarder` and `leanTutorialFirewall`, export an
authored application BlockAssembly, or with `run` execute that same in-memory
BlockAssembly through the public user API; run mode decodes requests only, never a
BlockAssembly, and the extern state returned by each call persists for the next
request. The others are test fixture exporters: they print authored syntax
and inputs, never expected answers, which the cross-language tests specify
independently. None is a whole-program compiler or a new wire protocol.
-/

namespace P4bloMain

open P4bloIR P4bloArch

/-! ## Application servers -/

private def request (line : String) : Except String (Entries × Nat × ByteArray) := do
  let json ← Lean.Json.parse line
  let entries ← match ← Decode.get? "" json "entries" with
    | none => pure { tables := [] }
    | some entries => Entries.decode "entries" entries
  let port ← Decode.uint32Field "" json "ingress_port"
  let packet ← hexToBytes? (← Decode.strField "" json "packet")
  pure (entries, port, packet)

private def response (outcome : Except String SwitchResult) (externs : Externs) : String :=
  (match outcome with
  | .error message => Lean.Json.mkObj [("error", .str message), ("state", externs.observe)]
  | .ok result => Lean.Json.mkObj (
      [("outputs", Lean.Json.arr (result.outputs.map fun ((port, packet) : Nat × ByteArray) =>
        Lean.Json.arr #[Lean.toJson port, Lean.Json.str (bytesToHex packet)]).toArray),
       ("state", externs.observe)] ++
      (result.diagnostic.map fun message => ("diagnostic", Lean.Json.str message)).toList)).compress

private def serve (program : P4bloArch.BlockAssembly) : IO UInt32 := do
  let (sw, initial) ← IO.ofExcept (P4blo.prepareSwitch program 4)
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  let mut externs := initial
  repeat
    let line ← stdin.getLine
    if line.isEmpty then break
    if line.trimAscii.isEmpty then continue
    let outcome := do
      let (entries, port, packet) ← request line
      P4blo.runSwitch sw externs entries port packet
    match outcome with
    | .ok (result, next) =>
      externs := next
      stdout.putStrLn (response (.ok result) externs)
    | .error message => stdout.putStrLn (response (.error message) externs)
    stdout.flush
  return 0

/-- Export the authored BlockAssembly, or serve requests against it with `run`. -/
private def application (name : String) (program : P4bloArch.BlockAssembly) : List String → IO UInt32
  | [] => do
    IO.println (Lean.toJson program).compress
    return 0
  | ["run"] => serve program
  | _ => do
    IO.eprintln s!"usage: p4blo {name} [run]"
    return 2

/-! ## Test fixture exporters -/

private def bindings : P4blo.Scalar.Env ctx → List Lean.Json
  | .nil => []
  | .cons (name := name) (t := t) value rest =>
    let literal : P4bloIR.Literal := match t, value with
      | .bits width, value => .bits width value.val
      | .boolean, value => .boolean value
    Lean.Json.mkObj [("name", Lean.toJson name),
      ("value", (P4bloIR.Expr.literal literal).toJson)] :: bindings rest

/-- Export source-built IR, never precomputed source answers. The conformance
suite places these expressions in independently validated packet programs. -/
def scalarExamples : IO Unit := do
  for c in P4blo.ScalarExamples.cases do
    let width := match c.type with
      | .bits n => Lean.toJson n
      | .boolean => Lean.Json.null
    let json := Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("bindings", Lean.toJson ([] : List Lean.Json)),
      ("expression", (P4blo.Scalar.lower c.expression).toJson)]
    IO.println json.compress
  for c in P4blo.ScalarExamples.openCases do
    let width := match c.type with
      | .bits n => Lean.toJson n
      | .boolean => Lean.Json.null
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("bindings", Lean.toJson (bindings c.environment)),
      ("expression", (P4blo.Scalar.lower c.expression).toJson)]).compress

/-- Syntax and initial inputs only; independent expected final values live
in the tests. This is a fixture exporter, not a whole-program compiler. -/
def scalarCommands : IO Unit := do
  for c in P4blo.ScalarCommandExamples.cases do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name),
      ("inputs", Lean.Json.mkObj [("x", Lean.toJson c.first.val),
        ("y", Lean.toJson c.second.val), ("flag", Lean.toJson c.flag)]),
      ("body", Lean.toJson (c.command.lower.map P4bloIR.Stmt.toJson))]).compress

/-- Test fixture syntax and selected initial validity only. Expected answers
and the independent full-store observer live outside this exporter. -/
def fieldExpressions : IO Unit := do
  for c in P4blo.FieldTests.expressionCases do
    let width := match c.type with
      | .bits width => Lean.toJson width
      | .boolean => Lean.Json.null
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width), ("valid", Lean.toJson c.valid),
      ("expression", P4bloIR.Expr.toJson (P4blo.Fields.lower c.expression))]).compress

/-- Authored body syntax and inputs, never computed expected final state.
The cross-language tests independently specify declarations and outputs. -/
def fieldCommands : IO Unit := do
  for c in P4blo.FieldCommandExamples.cases do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name),
      ("ttl", Lean.toJson c.initialTTL.val),
      ("ethernetValid", Lean.toJson c.ethernetValid),
      ("ipv4Valid", Lean.toJson c.ipv4Valid),
      ("hit", Lean.toJson c.hit),
      ("body", Lean.toJson (c.command.lower.map P4bloIR.Stmt.toJson))]).compress

def headerReads : IO Unit := do
  for c in P4blo.HeaderReadExamples.expressionCases do
    let width := match c.type with
      | .bits width => Lean.toJson width
      | .boolean => Lean.Json.null
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name), ("width", width),
      ("a", Lean.toJson c.a), ("b", Lean.toJson c.b),
      ("expression", P4bloIR.Expr.toJson (P4blo.Fields.lower c.expression))]).compress
  for (suffix, a, b) in [("00", false, false), ("01", false, true), ("10", true, false), ("11", true, true)] do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson ("command-" ++ suffix)),
      ("a", Lean.toJson a), ("b", Lean.toJson b),
      ("body", Lean.toJson (P4blo.HeaderReadExamples.command.lower.map P4bloIR.Stmt.toJson))]).compress

/-- Authored syntax and initial inputs only; expected states are independent. -/
def guardedForward : IO Unit := do
  for c in P4blo.GuardedForwardTests.cases do
    IO.println (Lean.Json.mkObj [
      ("name", Lean.toJson c.name),
      ("ttl", Lean.toJson c.ttl.val),
      ("ethernetValid", Lean.toJson c.ethernetValid),
      ("ipv4Valid", Lean.toJson c.ipv4Valid),
      ("hit", Lean.toJson c.hit),
      ("body", Lean.toJson (P4blo.GuardedForwardPolicy.guardedForward.lower.map P4bloIR.Stmt.toJson))]).compress

def callEntry : IO Unit := do
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.BlockLibrary.toJson P4blo.CallEntry.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson ([false, true].flatMap fun ev =>
      [false, true].map fun iv => P4blo.CallEntryTests.snapshot ev iv))]).compress

def callBodyEntry : IO Unit := do
  let mut snapshots := []
  for (name, body) in P4blo.CallBodyEntryTests.profiles do
    for ev in [false, true] do
      for iv in [false, true] do
        snapshots := snapshots ++ [← P4blo.CallBodyEntryTests.snapshot name body ev iv]
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.BlockLibrary.toJson P4blo.CallBodyEntry.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson snapshots)]).compress

def callReturn : IO Unit :=
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.CallEntry.program.toJson),
    ("params", Lean.toJson (P4bloIR.PlainCallEntry.params.map P4bloIR.Param.toJson)),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson ([false, true].flatMap fun ev =>
      [false, true].map fun iv => P4blo.CallReturnTests.snapshot ev iv))]).compress

def guardedCallPrefix : IO Unit := do
  let mut snapshots := []
  for c in P4blo.GuardedForwardTests.cases do
    for priorDrop in [false, true] do
      snapshots := snapshots ++ [← P4blo.GuardedCallPrefixTests.snapshot c priorDrop]
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.BlockLibrary.toJson P4blo.CallBodyEntry.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson snapshots)]).compress

def guardedControlCall : IO Unit := do
  let mut snapshots := []
  for c in P4blo.GuardedForwardTests.cases do
    for priorDrop in [false, true] do
      snapshots := snapshots ++ [← P4blo.GuardedControlCallTests.snapshot c priorDrop]
  IO.println (Lean.Json.mkObj [
    ("program", P4bloIR.BlockLibrary.toJson P4blo.GuardedControlCall.program),
    ("args", Lean.toJson (P4bloIR.PlainCallEntry.args.map P4bloIR.Arg.toJson)),
    ("snapshots", Lean.toJson snapshots)]).compress

def forwarderAction : IO Unit := do
  let snapshots ← P4blo.ForwarderActionTests.cases.mapM P4blo.ForwarderActionTests.snapshot
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.Forwarder.program.toJson),
    ("action", P4blo.Forwarder.forwardAction.toJson),
    ("snapshots", Lean.toJson snapshots)]).compress

def forwarderTables : IO Unit := do
  let configurations ← P4blo.ForwarderTableTests.profiles.mapM P4blo.ForwarderTableTests.snapshot
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.Forwarder.program.toJson),
    ("index", P4blo.CallReturnTests.indexJson P4blo.Forwarder.index),
    ("configurations", Lean.toJson configurations)]).compress

def forwarderApply : IO Unit := do
  let snapshots ← P4blo.ForwarderApplyTests.cases.mapM P4blo.ForwarderApplyTests.snapshot
  IO.println (Lean.Json.mkObj [
    ("program", P4blo.Forwarder.program.toJson),
    ("snapshots", Lean.toJson snapshots)]).compress

/-! ## Dispatch -/

/-- A fixture exporter takes no arguments. -/
private def exporter (name : String) (action : IO Unit) : List String → IO UInt32
  | [] => do
    action
    return 0
  | _ => do
    IO.eprintln s!"usage: p4blo {name}"
    return 2

/-- Every subcommand, by the name of the executable it replaces. -/
def commands : List (String × (List String → IO UInt32)) := [
  ("leanForwarder", application "leanForwarder" P4blo.Forwarder.program),
  ("leanTutorialFirewall", application "leanTutorialFirewall" P4blo.TutorialFirewall.program),
  ("scalarExamples", exporter "scalarExamples" scalarExamples),
  ("scalarCommands", exporter "scalarCommands" scalarCommands),
  ("fieldExpressions", exporter "fieldExpressions" fieldExpressions),
  ("fieldCommands", exporter "fieldCommands" fieldCommands),
  ("headerReads", exporter "headerReads" headerReads),
  ("guardedForward", exporter "guardedForward" guardedForward),
  ("callEntry", exporter "callEntry" callEntry),
  ("callBodyEntry", exporter "callBodyEntry" callBodyEntry),
  ("callReturn", exporter "callReturn" callReturn),
  ("guardedCallPrefix", exporter "guardedCallPrefix" guardedCallPrefix),
  ("guardedControlCall", exporter "guardedControlCall" guardedControlCall),
  ("forwarderAction", exporter "forwarderAction" forwarderAction),
  ("forwarderTables", exporter "forwarderTables" forwarderTables),
  ("forwarderApply", exporter "forwarderApply" forwarderApply)]

end P4bloMain

def main (args : List String) : IO UInt32 := do
  match args with
  | name :: rest =>
    match P4bloMain.commands.lookup name with
    | some command => command rest
    | none => usage
  | [] => usage
where
  usage : IO UInt32 := do
    IO.eprintln s!"usage: p4blo <command> [args]\ncommands: {", ".intercalate (P4bloMain.commands.map (·.1))}"
    return 2
