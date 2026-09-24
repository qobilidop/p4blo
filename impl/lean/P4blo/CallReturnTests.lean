import P4blo.CallEntryTests
import P4bloIR.PlainCallReturn
import P4bloArch.Externs

namespace P4blo.CallReturnTests
open P4bloIR P4bloIR.Execution P4bloIR.PlainCallEntry P4bloIR.PlainCallReturn

def b (width value : Nat) : Value := .bits (Bits.wrap width value)
def newHdr (ev iv : Bool) : Value := .struct "Headers"
  [.header "Ethernet" ev [b 48 0x313233343536, b 48 0x414243444546, b 16 0x86dd],
   .header "IPv4" iv [b 8 17, b 8 29, b 16 0x1357]]
def newMeta : Value := .struct "Metadata" [b 9 257, .bool false, b 16 0x5678]
def newObserver : Value := .struct "H" [.header "Result" false
  [b 48 1001, b 48 2002, b 16 3003, b 8 40, b 8 50, b 8 60, b 16 7007,
   b 8 80, b 16 9009, b 8 100, b 16 11011, b 8 120, b 48 13013, b 48 14014,
   b 16 15015, b 8 160, b 8 170]]
def newRoute : Value := .struct "Route" [.bool false, b 48 0x999999999999, b 48 0x888888888888, b 9 511]

def caller (ev iv : Bool) : Frame :=
  { CallEntryTests.caller ev iv with
    vars := (CallEntryTests.caller ev iv).vars |>.insert "scratch" (b 8 41) |>.insert "unrelated" (b 8 42) }

/-- Extra destination-name decoys make a skipped restore succeed in the
wrong frame rather than merely fault. This is an operational fixture. -/
def callee (ev iv : Bool) : Frame :=
  let vars := ({} : Std.HashMap String Value)
    |>.insert "hdr" (newHdr ev iv) |>.insert "meta" newMeta |>.insert "observer" newObserver
    |>.insert "scratch" (b 8 91) |>.insert "unrelated" (b 8 92)
    |>.insert "source_hdr" (b 8 93) |>.insert "source_meta" (b 8 94) |>.insert "callee_only" (.bool true)
  { scope := CallEntry.scope, vars := if ev then vars.insert "route" newRoute else vars }

/-- Shared state deliberately differs from the entry fixture's old state. -/
def current (ev iv : Bool) : Run :=
  { index := CallEntry.index, frame := callee ev iv
    entries := some {
      index := CallEntry.index
      entries := ({} : Std.HashMap TableRef (Array Entry)).insert ("untouched", "table")
        #[⟨[], ⟨"currentEntry", []⟩, 37⟩]
      defaults := ({} : Std.HashMap TableRef (Option ActionCall)).insert ("untouched", "table") (some ⟨"currentAction", []⟩) }
    externs := { model := P4bloArch.model, instances := ({} : Std.HashMap String ExternState).insert "sentinel" (.register 8 #[31, 19, 7]) }
    packet := some { data := ⟨#[0xde, 0xad, 0xbe, 0xef]⟩, value := 0xdeadbeef, cursor := 11 }
    emitter := some { value := 19, width := 5 }
    visits := ({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 29 }

theorem concrete_return (ev iv : Bool) :
    (dispatch (.blockReturn (caller ev iv) params args)).run (current ev iv) =
      (.ok [], { current ev iv with frame := returnedFrame (caller ev iv) (newHdr ev iv) newMeta newObserver }) := by
  apply dispatch_return (current ev iv) (caller ev iv) (newHdr ev iv) newMeta newObserver
    ((CallEntryTests.hdr ev iv).toValue) ((CallEntryTests.metadataValue ev iv).toValue) CallEntryTests.observer
    ⟨rfl, rfl⟩
  all_goals cases ev <;> simp [current, caller, callee, CallEntryTests.caller, Frame.read?, Std.HashMap.getElem_insert]

def mapJson (encode : α → Lean.Json) (values : Std.HashMap String α) : Lean.Json :=
  Lean.Json.mkObj (values.toList.map fun (name, value) => (name, encode value))
def varDeclJson : VarDecl → Lean.Json
  | .param p => Lean.Json.mkObj [("param", p.toJson)]
  | .var v => Lean.Json.mkObj [("var", v.toJson)]
def scopeJson (scope : BlockScope) : Lean.Json := Lean.Json.mkObj [
  ("block", scope.block.toJson), ("vars", mapJson varDeclJson scope.vars),
  ("actions", mapJson Action.toJson scope.actions), ("actionParams", mapJson (mapJson Param.toJson) scope.actionParams),
  ("tables", mapJson Table.toJson scope.tables), ("states", mapJson State.toJson scope.states)]
def indexJson (index : Index) : Lean.Json := Lean.Json.mkObj [
  ("program", index.program.toJson), ("headerTypes", mapJson HeaderType.toJson index.headerTypes),
  ("structTypes", mapJson StructType.toJson index.structTypes), ("enumTypes", mapJson EnumType.toJson index.enumTypes),
  ("externTypes", mapJson ExternType.toJson index.externTypes), ("externInstances", mapJson ExternInstance.toJson index.externInstances),
  ("blocks", mapJson Block.toJson index.blocks), ("scopes", mapJson scopeJson index.scopes),
  ("programNames", Lean.Json.mkObj (index.programNames.toList.map fun name => (name, Lean.toJson true))),
  ("errors", mapJson Lean.toJson index.errors)]
def frameJson (frame : Frame) : Lean.Json := Lean.Json.mkObj [
  ("scope", scopeJson frame.scope), ("vars", mapJson CallEntryTests.valueJson frame.vars),
  ("action", Lean.toJson frame.action), ("actionVars", frame.actionVars.map (mapJson CallEntryTests.valueJson) |>.getD .null)]

def runJson (run : Run) : Lean.Json :=
  let externs := mapJson (fun state => match state.register? with
    | some (width, cells) => Lean.Json.mkObj [("register", Lean.toJson [Lean.toJson width, Lean.toJson cells])]
    | none => .null) run.externs.instances
  let entries := run.entries.map (fun e => Lean.Json.mkObj [
    ("index", indexJson e.index),
    ("entries", Lean.Json.mkObj (e.entries.toList.map fun (key, values) =>
      ((Lean.toJson [key.1, key.2]).compress, Lean.toJson (values.map Entry.toJson)))),
    ("defaults", Lean.Json.mkObj (e.defaults.toList.map fun (key, value) =>
      ((Lean.toJson [key.1, key.2]).compress, value.map ActionCall.toJson |>.getD .null)))]) |>.getD .null
  Lean.Json.mkObj [("index", indexJson run.index), ("frame", frameJson run.frame), ("entries", entries),
    ("externs", externs),
    ("packet", run.packet.map (fun p => Lean.toJson [Lean.toJson (p.data.data.map UInt8.toNat), Lean.toJson p.value, Lean.toJson p.cursor]) |>.getD .null),
    ("emitter", run.emitter.map (fun e => Lean.toJson [e.value, e.width]) |>.getD .null),
    ("visits", Lean.Json.mkObj (run.visits.toList.map fun (key, value) => ((Lean.toJson [key.1, key.2]).compress, Lean.toJson value)))]

def returned (ev iv : Bool) : Machine :=
  match step { work := .blockReturn (caller ev iv) params args :: [.block "mustRemainPending" []], run := current ev iv } with
  | .inr machine => machine
  | .inl outcome => { run := outcome.2, work := [] }

def snapshot (ev iv : Bool) : Lean.Json :=
  let result := returned ev iv
  Lean.Json.mkObj [("ev", Lean.toJson ev), ("iv", Lean.toJson iv), ("faultNone", Lean.toJson result.fault.isNone),
    ("pending", Lean.toJson (result.work matches [.block "mustRemainPending" []])),
    ("run", runJson result.run), ("callee", frameJson (callee ev iv))]

def run : IO Unit := do
  for ev in [false, true] do
    for iv in [false, true] do
      let m := returned ev iv
      unless m.fault.isNone && (m.work matches [.block "mustRemainPending" []]) &&
          m.run.frame.scope.block.name == "Caller" && m.run.frame.vars.size == 7 &&
          m.run.frame.read? "source_hdr" == some (newHdr ev iv) &&
          m.run.frame.read? "source_meta" == some newMeta && m.run.frame.read? "hdr" == some newObserver &&
          m.run.frame.read? "scratch" == some (b 8 41) && m.run.frame.read? "unrelated" == some (b 8 42) do
        throw (IO.userError "normal return must restore original caller with only three copied roots")
  IO.println "Normal plain-root return tests passed"

end P4blo.CallReturnTests
