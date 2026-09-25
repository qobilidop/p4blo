import P4bloIR.Exec

/-!
# The three entry points

The calling convention of docs/design.md, "Blocks and the P4NAH rule":

    parse   : Packet × M → H × M × bits consumed × accepted × error
    control : H × M × TableEntries → H × M
    deparse : H → Packet

Mirrors `impl/python/p4blo/interp/{parser,control,deparser}.py`. None of them
mutates its arguments. Externs are the only state a block can touch; the
caller passes them in and gets them back, since a Lean value cannot be
mutated in place the way the Python bindings are. `Except String` is for
`InterpError`-class failures, which a validated program never produces; a
parse error is an outcome, not a failure.
-/

namespace P4bloArch
open P4bloIR

/-- What a parser run produced (docs/ir-semantics.md, "Parsers"). Rejection
and error are separate: `accept` gives `accepted` with `NoError`; an
explicit `reject` gives not accepted with `NoError`; a raised error gives
not accepted with that error. -/
structure ParseOutcome where
  headers : Value
  metadata : Value
  consumedBits : Nat
  accepted : Bool
  /-- A name from `BlockLibrary.errors`. -/
  error : String
  /-- The extern state after the run. -/
  externs : Externs
  deriving Inhabited

/-- The block `name` of `kind` with `arity` parameters, or the error
sentence `what` describes. -/
private def blockOf (index : Index) (name : String) (kind : BlockKind) (arity : Nat) (what : String) :
    Except String Block := do
  let some decl := index.blocks[name]? | throw s!"unknown block '{name}'"
  if decl.kind != kind || decl.params.length != arity then throw s!"block '{name}' is not a {what}"
  pure decl

/-- The struct value the variable `name` of the final activation holds. -/
private def structVar (run : Run) (name : String) : Except String Value := do
  let some v := run.frame.vars[name]? | throw s!"unknown variable '{name}'"
  let _ ← v.expectStruct
  pure v

/-- Run parser `block` over `packet` with an initial metadata value. The
headers value starts as the zero value of the program's headers type. -/
def runParser (index : Index) (block : String) (packet : ByteArray) (metadata : Value)
    (externs : Externs) : Except String ParseOutcome := do
  let decl ← blockOf index block .parser 2 "parser of (out H, inout M)"
  let [headersParam, metadataParam] := decl.params | throw "unreachable"
  let frame ← Frame.forBlock index decl
  let frame := { frame with vars := frame.vars.insert metadataParam.name metadata }
  let run : Run := { index, externs, frame, packet := some (Packet.ofBytes packet) }
  let (result, run) := (runStates decl).run run
  let (accepted, error) ← match result with
    | .ok () => pure (true, "NoError")
    | .error (.parse e) => pure (false, e)
    | .error (.interp msg) => throw msg
  let some packet := run.packet | throw "the parser lost its packet"
  pure { headers := ← structVar run headersParam.name,
         metadata := ← structVar run metadataParam.name,
         consumedBits := packet.cursor, accepted, error, externs := run.externs }

/-- The outcome of a control or deparser run, which has no parse errors. -/
private def finished (result : Except Fault Unit) : Except String Unit :=
  match result with
  | .ok () => pure ()
  | .error (.interp msg) => throw msg
  | .error (.parse e) => throw s!"parse error '{e}' outside a parser"

/-- Run control `block` and return the new headers, metadata and externs. -/
def runControl (index : Index) (block : String) (headers metadata : Value)
    (entries : Installed) (externs : Externs) : Except String (Value × Value × Externs) := do
  let decl ← blockOf index block .control 2 "control of (inout H, inout M)"
  let [headersParam, metadataParam] := decl.params | throw "unreachable"
  let frame ← Frame.forBlock index decl
  let frame := { frame with vars := (frame.vars.insert headersParam.name headers).insert metadataParam.name metadata }
  let run : Run := { index, entries := some entries, externs, frame }
  let (result, run) := (execute decl.body).run run
  finished result
  pure (← structVar run headersParam.name, ← structVar run metadataParam.name, run.externs)

/-- Run deparser `block` and return the emitted bytes, zero-padded to a
byte boundary, and the externs after. -/
def runDeparser (index : Index) (block : String) (headers : Value) (externs : Externs) :
    Except String (ByteArray × Externs) := do
  let decl ← blockOf index block .deparser 1 "deparser of (in H)"
  let [headersParam] := decl.params | throw "unreachable"
  let frame ← Frame.forBlock index decl
  let frame := { frame with vars := frame.vars.insert headersParam.name headers }
  let run : Run := { index, externs, frame, emitter := some {} }
  let (result, run) := (execute decl.body).run run
  finished result
  let some emitter := run.emitter | throw "the deparser lost its buffer"
  pure (emitter.toBytes, run.externs)

end P4bloArch
