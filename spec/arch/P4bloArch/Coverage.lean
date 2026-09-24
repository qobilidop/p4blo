import P4bloIR.Coverage
import P4bloArch.Switch

/-!
# The coverage observer: rule tags of one request under the switch

Runs the IR's step machine itself, one `Execution.step` at a time, and asks
`P4bloIR.Coverage.classify` before each step which rules the step is about
to exercise. `Execution.Finishes.sound` is what makes this an observer and
not a second interpreter: a finite trace of `step` determines exactly the
outcome of `Execution.drive`, which is what the real entry points run. The
observer's outcome is nevertheless discarded; the reply of `p4blo-lean
run` comes from `Switch.run`, and this module only reports tags.

`run` follows `Switch.run` (docs/arch-supports.md, "The switch") so that
each block is traced from the configuration the real entry point starts
from. It calls the real `runParser` and `runControl` for the values the
next block needs and traces each block beside them, so the flow between
blocks is the switch's own. The initial configurations are rebuilt here as
`P4bloIR.Interp` builds them; the architecture tests check that the traced
outcomes and the real ones agree.
-/

namespace P4bloArch

namespace Coverage

open P4bloIR P4bloIR.Execution

/-- The names of the tags seen so far. -/
abbrev Tags := Std.HashSet String

/-- `tags` with the names of `new` added. -/
def Tags.add (tags : Tags) (new : List P4bloIR.Coverage.Tag) : Tags :=
  new.foldl (fun s t => s.insert t.name) tags

/-- Step `m` to its end, classifying every configuration before its step and
the final run after the last. The loop is the same as `Execution.drive`'s;
it is `partial` because a nonterminating program has no trace to report. -/
partial def trace (ctx : P4bloIR.Coverage.Context) (m : Machine) (tags : Tags) : Outcome × Tags :=
  let tags := tags.add (P4bloIR.Coverage.classify ctx m)
  match step m with
  | .inl result => (result, tags.add (P4bloIR.Coverage.finalTags result.2))
  | .inr next => trace ctx next tags

/-- The fresh activation of block `name` with `bindings` set, as the entry
points of `P4bloIR.Interp` make it; `none` when the block is unknown. -/
def activation (index : Index) (name : String) (bindings : List Value) :
    Option (Block × Frame) := do
  let decl ← index.blocks[name]?
  let frame ← (Frame.forBlock index decl).toOption
  let vars := (decl.params.zip bindings).foldl
    (fun vars (p, v) => vars.insert p.name v) frame.vars
  pure (decl, { frame with vars })

/-- The traced outcome and tags of parser `name`, from the configuration
`runParser` starts: the metadata bound, the headers at zero. -/
def traceParser (index : Index) (name : String) (packet : ByteArray) (metadata : Value)
    (externs : Externs) (ctx : P4bloIR.Coverage.Context := {}) : Option Outcome × Tags :=
  match index.blocks[name]? with
  | none => (none, {})
  | some decl =>
    -- `runParser` binds only the metadata; the headers keep their zero value.
    let metadataOnly := match decl.params with
      | [_, m] => [(m.name, metadata)]
      | _ => []
    match (Frame.forBlock index decl).toOption with
    | none => (none, {})
    | some frame =>
      let vars := metadataOnly.foldl (fun vars (n, v) => vars.insert n v) frame.vars
      let run : Run := { index, externs, frame := { frame with vars },
                         packet := some (Packet.ofBytes packet) }
      let (outcome, tags) := trace ctx { work := [.states decl], run } {}
      (some outcome, tags)

/-- The traced outcome and tags of control `name`, from the configuration
`runControl` starts. -/
def traceControl (index : Index) (name : String) (headers metadata : Value)
    (entries : Installed) (externs : Externs) (ctx : P4bloIR.Coverage.Context := {}) :
    Option Outcome × Tags :=
  match activation index name [headers, metadata] with
  | none => (none, {})
  | some (decl, frame) =>
    let run : Run := { index, entries := some entries, externs, frame }
    let (outcome, tags) := trace ctx { work := [.statements decl.body], run } {}
    (some outcome, tags)

/-- The traced outcome and tags of deparser `name`, from the configuration
`runDeparser` starts. -/
def traceDeparser (index : Index) (name : String) (headers : Value) (externs : Externs)
    (ctx : P4bloIR.Coverage.Context := {}) : Option Outcome × Tags :=
  match activation index name [headers] with
  | none => (none, {})
  | some (decl, frame) =>
    let run : Run := { index, externs, frame, emitter := some {} }
    let (outcome, tags) := trace ctx { work := [.statements decl.body], run } {}
    (some outcome, tags)

/-- The struct `m` with field `position` set, as `Switch` sets its contract
fields. -/
private def setField (m : Value) (position : Nat) (v : Value) : Except String Value := do
  let (t, fields) ← m.expectStruct
  pure (.struct t (fields.set position v))

/-- The tags of one packet through the switch: every block that `Switch.run`
runs for these inputs, traced from the configuration it starts from. Tags
gathered before a failure are kept, so an error reply reports how far the
request got. -/
def run (sw : Switch) (externs : Externs) (host : Entries) (ingress : Nat)
    (packet : ByteArray) : Tags := Id.run do
  if ingress ≥ sw.ports || ingress ≥ 2 ^ 9 then return {}
  let .ok installed := Installed.build sw.index (some host) | return {}
  let .ok zero := Value.zero (.struct sw.metadataType) sw.index | return {}
  let initial ← match sw.ingressPort with
    | some f =>
      match f.type with
      | .bits w => pure (setField zero f.position (.bits (Bits.wrap w ingress)))
      | _ => pure (.error "unreachable")
    | none => pure (.ok zero)
  let .ok initial := initial | return {}
  let ctx : P4bloIR.Coverage.Context := {
    hostDefaults := host.tables.filterMap fun te =>
      if te.defaultAction.isSome then some (te.block, te.table) else none }
  let (_, tags) := traceParser sw.index sw.parser packet initial externs ctx
  let .ok parsed := runParser sw.index sw.parser packet initial externs | return tags
  if parsed.consumedBits % 8 != 0 then return tags
  let provided ← match sw.parserError with
    | some f => pure (setField parsed.metadata f.position (.error parsed.error))
    | none => pure (.ok parsed.metadata)
  let .ok provided := provided | return tags
  let (_, controlTags) :=
    traceControl sw.index sw.control parsed.headers provided installed parsed.externs ctx
  let tags := tags.union controlTags
  let .ok (headers, _, externs) :=
    runControl sw.index sw.control parsed.headers provided installed parsed.externs
    | return tags
  let (_, deparserTags) := traceDeparser sw.index sw.deparser headers externs ctx
  tags.union deparserTags

/-- The sorted names of `tags`, as the reply carries them. -/
def Tags.sorted (tags : Tags) : List String :=
  tags.toList.mergeSort (· ≤ ·)

end Coverage

end P4bloArch
