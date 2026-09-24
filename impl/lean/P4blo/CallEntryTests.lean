import P4blo.CallEntry
import P4bloIR.Json
import P4bloArch.Externs

namespace P4blo.CallEntryTests
open P4bloIR P4bloIR.Execution P4bloIR.PlainCallEntry
open Fields FieldCommandExamples

def source (ev iv : Bool) : Store roots := store 64 ev iv true
def hdr (ev iv : Bool) : Data headers := (source ev iv).get .here
def metadataValue (ev iv : Bool) : Data metadata := (source ev iv).get (.there .here)
def routeValue (ev iv : Bool) : Data route := (source ev iv).get (.there (.there .here))

-- Nonzero, asymmetric observer fields are independent of source zero.
def observer : Value := .struct "H" [.header "Result" true
  [.bits (Bits.wrap 48 101), .bits (Bits.wrap 48 202), .bits (Bits.wrap 16 303),
   .bits (Bits.wrap 8 4), .bits (Bits.wrap 8 5), .bits (Bits.wrap 8 6),
   .bits (Bits.wrap 16 707), .bits (Bits.wrap 8 8), .bits (Bits.wrap 16 909),
   .bits (Bits.wrap 8 10), .bits (Bits.wrap 16 1111), .bits (Bits.wrap 8 12),
   .bits (Bits.wrap 48 1313), .bits (Bits.wrap 48 1414), .bits (Bits.wrap 16 1515),
   .bits (Bits.wrap 8 16), .bits (Bits.wrap 8 17)]]

def caller (ev iv : Bool) : Frame :=
  { scope := { block := { (default : Block) with name := "Caller", kind := .control } }
    vars := ({} : Std.HashMap String Value)
      |>.insert "source_hdr" (hdr ev iv).toValue
      |>.insert "source_meta" (metadataValue ev iv).toValue
      |>.insert "source_route" (routeValue ev iv).toValue
      |>.insert "hdr" observer
      |>.insert "caller_only" (.bits (Bits.wrap 9 301)) }

def initial (ev iv : Bool) : Run :=
  { index := CallEntry.index, frame := caller ev iv
    entries := some {
      index := CallEntry.index
      defaults := ({} : Std.HashMap TableRef (Option ActionCall)).insert ("untouched", "table")
        (some ⟨"sentinelAction", []⟩) }
    externs := { model := P4bloArch.model, instances := ({} : Std.HashMap String ExternState).insert "sentinel" (.register 8 #[3, 9, 27]) }
    packet := some { data := ⟨#[0xde, 0xad, 0xbe, 0xef]⟩, value := 0xdeadbeef, cursor := 3 }
    emitter := some { value := 5, width := 3 }
    visits := ({} : Std.HashMap (String × String) Nat).insert ("parser", "state") 13 }

def continuation : List Work := [.block "mustRemainPending" []]
def entered (ev iv : Bool) : Machine :=
  match step { work := .block "RewriteBody" args :: continuation, run := initial ev iv } with
  | .inr machine => machine
  | .inl outcome => { run := outcome.2, work := [] }

/-- Kernel application to the actual built index and a concrete nonempty
caller, for every validity pair. No native evaluation is used by this root. -/
theorem concrete_entry (ev iv : Bool) : ∃ zero,
    Frame.forBlock CallEntry.index CallEntry.block = .ok zero ∧
    (dispatch (.block "RewriteBody" args)).run (initial ev iv) =
      (.ok [.runBlock CallEntry.block, .blockReturn (caller ev iv) CallEntry.block.params args],
       { initial ev iv with
         frame := boundFrame zero (hdr ev iv).toValue
           (metadataValue ev iv).toValue (routeValue ev iv).toValue observer }) := by
  obtain ⟨zero, hz, _, _, _, _, _, hd, _⟩ :=
    CallEntry.source_entry (initial ev iv) (hdr ev iv) (metadataValue ev iv) (routeValue ev iv)
    observer continuation rfl ⟨rfl, rfl⟩
    (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
    (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
    (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
    (by simp [initial, caller, Frame.read?, Std.HashMap.getElem_insert])
  exact ⟨zero, hz, hd⟩

def valueJson : Value → Lean.Json
  | .bits b => Lean.toJson ([Lean.toJson "bits", Lean.toJson b.width, Lean.toJson b.value] : List Lean.Json)
  | .bool b => Lean.toJson b
  | .enum t n => Lean.toJson [Lean.toJson "enum", Lean.toJson t, Lean.toJson n]
  | .error n => Lean.toJson [Lean.toJson "error", Lean.toJson n]
  | .header n v fs => Lean.toJson [Lean.toJson "header", Lean.toJson n, Lean.toJson v, Lean.toJson (fs.map valueJson)]
  | .struct n fs => Lean.toJson [Lean.toJson "struct", Lean.toJson n, Lean.toJson (fs.map valueJson)]
  | .stack n fs i => Lean.toJson [Lean.toJson "stack", Lean.toJson n, Lean.toJson (fs.map valueJson), Lean.toJson i]

def bindingsJson (frame : Frame) (names : List String) : Lean.Json :=
  Lean.Json.mkObj (names.map fun name => (name, (frame.read? name).map valueJson |>.getD .null))

def snapshot (ev iv : Bool) : Lean.Json := Id.run do
  let result := entered ev iv
  let r := result.run
  let queue := match result.work with
    | [.runBlock b, .blockReturn c ps aa, .block "mustRemainPending" []] =>
      Lean.Json.mkObj [("block", Lean.toJson b.name), ("params", Lean.toJson (ps.map Param.toJson)),
        ("args", Lean.toJson (aa.map Arg.toJson)), ("callerScope", Lean.toJson c.scope.block.name),
        ("callerSize", Lean.toJson c.vars.size), ("callerActionNone", Lean.toJson (c.action.isNone && c.actionVars.isNone)),
        ("caller", bindingsJson c ["source_hdr", "source_meta", "source_route", "hdr", "caller_only"])]
    | _ => .null
  let externState := match r.externs.instances["sentinel"]?.bind (·.register?) with
    | some (w, cells) => Lean.toJson [Lean.toJson w, Lean.toJson cells]
    | _ => .null
  return Lean.Json.mkObj [
    ("ev", Lean.toJson ev), ("iv", Lean.toJson iv), ("faultNone", Lean.toJson result.fault.isNone),
    ("scope", Lean.toJson r.frame.scope.block.name), ("size", Lean.toJson r.frame.vars.size),
    ("actionNone", Lean.toJson (r.frame.action.isNone && r.frame.actionVars.isNone)),
    ("vars", bindingsJson r.frame ["hdr", "meta", "route", "observer", "scratch", "unrelated", "caller_only"]),
    ("queue", queue), ("index", Lean.toJson r.index.program.name),
    ("packet", r.packet.map (fun p => Lean.toJson [Lean.toJson (p.data.data.map UInt8.toNat), Lean.toJson p.value, Lean.toJson p.cursor]) |>.getD .null),
    ("emitter", r.emitter.map (fun e => Lean.toJson [e.value, e.width]) |>.getD .null),
    ("extern", externState), ("externSize", Lean.toJson r.externs.instances.size),
    ("visit", Lean.toJson r.visits[("parser", "state")]?), ("visitSize", Lean.toJson r.visits.size),
    ("entries", r.entries.map (fun e => Lean.Json.mkObj [
      ("index", Lean.toJson e.index.program.name), ("size", Lean.toJson e.entries.size),
      ("defaultsSize", Lean.toJson e.defaults.size),
      ("default", Lean.toJson ((e.defaults[("untouched", "table")]?).join.map ActionCall.toJson))]) |>.getD .null)]

def run : IO Unit := do
  unless (Frame.forBlock CallEntry.badExtraIndex CallEntry.badExtraProgram.blocks.head!).toOption.isNone do
    throw (IO.userError "unzeroable extra declaration must prevent actual initialization")
  for ev in [false, true] do
    for iv in [false, true] do
      let m := entered ev iv
      unless m.fault.isNone && m.work.length == 3 && m.run.frame.vars.size == 6 do
        throw (IO.userError "plain call entry must stop at the callee body boundary")
      unless m.run.frame.read? "observer" == some observer &&
          m.run.frame.read? "scratch" == some (.bits (Bits.wrap 8 0)) &&
          m.run.frame.read? "unrelated" == some (.bits (Bits.wrap 8 0)) do
        throw (IO.userError "plain call observer or local initialization differs")
  IO.println "Plain call entry tests passed"

end P4blo.CallEntryTests
