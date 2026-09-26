import P4bloArch.Assembly
import P4bloArch.Interp
import P4bloArch.Profile

/-!
# The scoped v1model packet architecture

Six stages run in order: parser, verify_checksum, ingress, egress,
compute_checksum, deparser. The optional control stages are identities when
absent. The flattened metadata contract and supported subset are specified in
`docs/arch-supports.md`. `egress_spec = 511` drops at the ingress or egress
boundary, before any later stage can run. The destination is selected before
egress; rewriting egress_spec there does not redirect it. As in BMv2
simple_switch 1.15.4, egress_spec resets to zero before egress. This is the
chosen target policy, not a P4-language guarantee. There are no
architecture-specific proof claims.
-/

namespace P4bloArch

open P4bloIR

/-- The position of a contract field in `M`. -/
structure MetaField where
  position : Nat
  type : Ty
  deriving Repr

/-- A loaded program under v1model. -/
structure V1Model where
  index : Index
  parser : String
  ingress : String
  verifyChecksum : Option String := none
  egress : Option String := none
  computeChecksum : Option String := none
  deparser : String
  metadataType : String
  ingressPort : Option MetaField
  parserError : Option MetaField
  egressPort : Option MetaField
  egressSpec : Option MetaField
  /-- Configured physical ports, numbered from zero. -/
  ports : Nat

/-- What one packet produced: the packets that left and, when the packet
was dropped for a reason the program did not decide, why. -/
structure V1ModelResult where
  outputs : List (Nat × ByteArray)
  diagnostic : Option String := none

namespace V1Model

/-- The contract field `name` of `M`, checked against `expected` when
present. -/
private def contractField (index : Index) (metadataType name : String) (expected : Ty) :
    Except String (Option MetaField) := do
  let some fields := index.fields? metadataType | throw s!"unknown metadata type '{metadataType}'"
  match fields.findIdx? (·.name == name) with
  | none => pure none
  | some position =>
    let ty := fields[position]!.type
    if ty != expected then throw s!"metadata field '{name}' has type {repr ty}, the contract wants {repr expected}"
    pure (some { position, type := ty })

/-- Load `index` under v1model with `ports` ports. -/
def load (index : Index) (bindings : BlockBindings) (ports : Nat) : Except String V1Model := do
  if ports < 1 || ports > 511 then throw "v1model ports must be between 1 and 511"
  (Bindings.check bindings index).mapError toString
  V1ModelProfile.check index bindings
  let role (r : String) (kind : BlockKind) : Except String String := do
    let some b := bindings.exported? index r | throw s!"the program exports no '{r}' block"
    if b.kind != kind then throw s!"export '{r}' has the wrong block kind"
    pure b.name
  let metadataType := bindings.metadata
  let optionalRole (r : String) : Except String (Option String) := do
    if bindings.exports.any (·.role == r) then pure (some (← role r .control)) else pure none
  pure { index, parser := ← role "parser" .parser, ingress := ← role "ingress" .control,
         deparser := ← role "deparser" .deparser,
         verifyChecksum := ← optionalRole "verify_checksum", egress := ← optionalRole "egress",
         computeChecksum := ← optionalRole "compute_checksum", metadataType,
         ingressPort := ← contractField index metadataType "ingress_port" (.bits 9),
         parserError := ← contractField index metadataType "parser_error" .error,
         egressPort := ← contractField index metadataType "egress_port" (.bits 9),
         egressSpec := ← contractField index metadataType "egress_spec" (.bits 9), ports }

/-- Field `position` of the struct `m`. -/
private def getField (m : Value) (position : Nat) : Except String Value := do
  let (_, fields) ← m.expectStruct
  let some v := fields[position]? | throw s!"metadata has no field {position}"
  pure v

/-- The struct `m` with field `position` set. -/
private def setField (m : Value) (position : Nat) (v : Value) : Except String Value := do
  let (t, fields) ← m.expectStruct
  pure (.struct t (fields.set position v))

/-- A bit-valued contract field, zero when absent. -/
def portField (m : Value) (f : Option MetaField) : Except String Nat := do
  let some f := f | pure 0
  pure (← (← getField m f.position).expectBits).value

/-- An omitted control stage is the identity, preserving all state. -/
def runStage (vm : V1Model) (name : Option String) (headers metadata : Value)
    (entries : Installed) (externs : Externs) : Except String (Value × Value × Externs) := do
  match name with
  | none => pure (headers, metadata, externs)
  | some name => runControl vm.index name headers metadata entries externs

/-- Run one packet arriving on `ingress` through the six v1model stages. -/
def run (sw : V1Model) (externs : Externs) (host : Entries) (ingress : Nat) (packet : ByteArray) :
    Except String (V1ModelResult × Externs) := do
  if ingress ≥ sw.ports then throw s!"ingress_port {ingress} is not a configured v1model port"
  if ingress ≥ 2 ^ 9 then throw s!"ingress_port {ingress} does not fit in bit<9>"
  let installed ← Installed.build sw.index (some host)
  let mut initial ← Value.zero (.struct sw.metadataType) sw.index
  if let some f := sw.ingressPort then
    let .bits w := f.type | throw "unreachable"
    initial ← setField initial f.position (.bits (Bits.wrap w ingress))
  let parsed ← runParser sw.index sw.parser packet initial externs
  if parsed.consumedBits % 8 != 0 then
    let why := s!"parser consumed {parsed.consumedBits} bits, not whole bytes; packet dropped"
    return ({ outputs := [], diagnostic := some why }, parsed.externs)
  let mut provided := parsed.metadata
  if let some f := sw.parserError then
    provided ← setField provided f.position (.error parsed.error)
  let (headers, metadata, externs) ←
    sw.runStage sw.verifyChecksum parsed.headers provided installed parsed.externs
  let (headers, metadata, externs) ←
    runControl sw.index sw.ingress headers metadata installed externs
  let destination ← portField metadata sw.egressSpec
  if destination == 511 then return ({ outputs := [] }, externs)
  if destination ≥ sw.ports then
    let why := s!"egress_spec {destination} is not a configured v1model port"
    return ({ outputs := [], diagnostic := some why }, externs)
  let metadata ← match sw.egressPort with
    | some f => setField metadata f.position (.bits (Bits.wrap 9 destination))
    | none => pure metadata
  -- BMv2 simple_switch clears egress_spec after selecting the destination.
  -- This also applies when the optional egress stage is empty.
  let metadata ← match sw.egressSpec with
    | some f => setField metadata f.position (.bits (Bits.wrap 9 0))
    | none => pure metadata
  let (headers, metadata, externs) ← sw.runStage sw.egress headers metadata installed externs
  if (← portField metadata sw.egressSpec) == 511 then return ({ outputs := [] }, externs)
  let (headers, _, externs) ← sw.runStage sw.computeChecksum headers metadata installed externs
  let (emitted, externs) ← runDeparser sw.index sw.deparser headers externs
  let payload := packet.extract (parsed.consumedBits / 8) packet.size
  pure ({ outputs := [(destination, emitted ++ payload)] }, externs)

end V1Model

end P4bloArch
