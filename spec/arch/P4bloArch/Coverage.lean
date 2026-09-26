import P4bloIR.Coverage
import P4bloArch.V1Model

/-!
# The coverage observer: rule tags of one request under v1model

Runs the IR's step machine itself, one `Execution.step` at a time, and asks
`P4bloIR.Coverage.classify` before each step which rules the step is about
to exercise. `Execution.Finishes.sound` is what makes this an observer and
not a second interpreter: a finite trace of `step` determines exactly the
outcome of `Execution.drive`, which is what the real entry points run. The
observer's outcome is nevertheless discarded; the reply of `p4blo-lean
run` comes from `V1Model.run`, and this module only reports tags.

`run` follows `V1Model.run` (docs/arch-supports.md, "v1model") so that
each block is traced from the configuration the real entry point starts
from. It calls the real `runParser` and `runControl` for the values the
next block needs and traces each block beside them, so the flow between
blocks is the v1model's own. The initial configurations are rebuilt here as
`P4bloArch.Interp` builds them; the architecture tests check that the traced
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

/-- Block `name` when it is of `kind` with `arity` parameters, the check
`runParser`, `runControl` and `runDeparser` make before they run anything;
`none` otherwise, and then nothing is traced, since nothing ran. -/
def blockOf? (index : Index) (name : String) (kind : BlockKind) (arity : Nat) : Option Block := do
  let decl ← index.blocks[name]?
  if decl.kind != kind || decl.params.length != arity then none
  pure decl

/-- The fresh activation of `decl` with `bindings` set, as the entry
points of `P4bloArch.Interp` make it; `none` when it has no frame. -/
def activation (index : Index) (decl : Block) (bindings : List Value) : Option Frame := do
  let frame ← (Frame.forBlock index decl).toOption
  let vars := (decl.params.zip bindings).foldl
    (fun vars (p, v) => vars.insert p.name v) frame.vars
  pure { frame with vars }

/-- The traced outcome and tags of parser `name`, from the configuration
`runParser` starts: the metadata bound, the headers at zero. -/
def traceParser (index : Index) (name : String) (packet : ByteArray) (metadata : Value)
    (externs : Externs) (ctx : P4bloIR.Coverage.Context := {}) : Option Outcome × Tags :=
  match blockOf? index name .parser 2 with
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
  match blockOf? index name .control 2 with
  | none => (none, {})
  | some decl =>
    match activation index decl [headers, metadata] with
    | none => (none, {})
    | some frame =>
      let run : Run := { index, entries := some entries, externs, frame }
      let (outcome, tags) := trace ctx { work := [.statements decl.body], run } {}
      (some outcome, tags)

/-- The traced outcome and tags of deparser `name`, from the configuration
`runDeparser` starts. -/
def traceDeparser (index : Index) (name : String) (headers : Value) (externs : Externs)
    (ctx : P4bloIR.Coverage.Context := {}) : Option Outcome × Tags :=
  match blockOf? index name .deparser 1 with
  | none => (none, {})
  | some decl =>
    match activation index decl [headers] with
    | none => (none, {})
    | some frame =>
      let run : Run := { index, externs, frame, emitter := some {} }
      let (outcome, tags) := trace ctx { work := [.statements decl.body], run } {}
      (some outcome, tags)

/-- The struct `m` with field `position` set, as `V1Model` sets its contract
fields. -/
private def setField (m : Value) (position : Nat) (v : Value) : Except String Value := do
  let (t, fields) ← m.expectStruct
  pure (.struct t (fields.set position v))

/-- The tags of one packet through v1model: every block that `V1Model.run`
runs for these inputs, traced from the configuration it starts from. Tags
gathered before a failure are kept, so an error reply reports how far the
request got. -/
def run (sw : V1Model) (externs : Externs) (host : Entries) (ingress : Nat)
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
  let mut tags := tags
  let mut headers := parsed.headers
  let mut metadata := provided
  let mut externs := parsed.externs
  for stage in [sw.verifyChecksum, some sw.ingress] do
    if let some name := stage then
      let (_, nextTags) := traceControl sw.index name headers metadata installed externs ctx
      tags := tags.union nextTags
      let .ok (h, m, e) := runControl sw.index name headers metadata installed externs | return tags
      headers := h
      metadata := m
      externs := e
  let .ok destination := V1Model.portField metadata sw.egressSpec | return tags
  if destination == 511 || destination ≥ sw.ports then return tags
  if let some field := sw.egressPort then
    let .ok m := setField metadata field.position (.bits (Bits.wrap 9 destination)) | return tags
    metadata := m
  if let some field := sw.egressSpec then
    let .ok m := setField metadata field.position (.bits (Bits.wrap 9 0)) | return tags
    metadata := m
  if let some name := sw.egress then
    let (_, nextTags) := traceControl sw.index name headers metadata installed externs ctx
    tags := tags.union nextTags
    let .ok (h, m, e) := runControl sw.index name headers metadata installed externs | return tags
    headers := h
    metadata := m
    externs := e
  let .ok fate := V1Model.portField metadata sw.egressSpec | return tags
  if fate == 511 then return tags
  if let some name := sw.computeChecksum then
    let (_, nextTags) := traceControl sw.index name headers metadata installed externs ctx
    tags := tags.union nextTags
    let .ok (h, _, e) := runControl sw.index name headers metadata installed externs | return tags
    headers := h
    externs := e
  let (_, deparserTags) := traceDeparser sw.index sw.deparser headers externs ctx
  tags.union deparserTags

/-- The sorted names of `tags`, as the reply carries them. -/
def Tags.sorted (tags : Tags) : List String :=
  tags.toList.mergeSort (· ≤ ·)

end Coverage

end P4bloArch
