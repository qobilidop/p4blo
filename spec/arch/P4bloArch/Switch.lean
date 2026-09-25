import P4bloArch.Assembly
import P4bloArch.Interp

/-!
# The switch architecture

Ordinary code outside the IR (docs/arch-supports.md, "The switch"): given an
ingress port and a packet, run the exported parser, control and deparser,
and return the packets that leave. It is the Lean twin of the Python switch
so that the differential-testing pipe (`p4blo-lean run`) compares whole
packets in and out.

The rules, all from docs/arch-supports.md:
- the metadata starts as the zero value of `M` with `ingress_port` set;
- the control runs after a parser rejection too, over the partial headers,
  with `parser_error` set when the program declares it;
- a parser that consumed a number of bits that is not a multiple of eight
  is a program bug: the packet is dropped with a diagnostic;
- the output packet is the deparser's bytes followed by the payload, the
  bytes after the ones the parser consumed;
- `drop` wins; then `flood` sends to every port but the ingress one; else
  the packet goes to `egress_port`;
- ports are `0` to `ports - 1` (.agents/decisions.md, "Port rules"): an
  ingress port outside them is the caller's error, before anything runs;
  an `egress_port` outside them drops the packet with a diagnostic. 511,
  BMv2's drop port, is just an out-of-range port here.

The metadata contract fields are each optional and only checked when
present, by name and type (docs/arch-supports.md, "The metadata contract"). As in
`impl/python/p4blo/arch/contract.py`, an undeclared field reads as its zero
value and ignores writes: a program without `egress_port` unicasts to
port 0. The deparser runs before the fate is read, as in
`impl/python/p4blo/arch/switch.py`, so its extern calls happen on a drop too.
-/

namespace P4bloArch

open P4bloIR

/-- The position of a contract field in `M`. -/
structure MetaField where
  position : Nat
  type : Ty
  deriving Repr

/-- A loaded program under the switch. -/
structure Switch where
  index : Index
  parser : String
  control : String
  deparser : String
  metadataType : String
  ingressPort : Option MetaField
  parserError : Option MetaField
  egressPort : Option MetaField
  drop : Option MetaField
  flood : Option MetaField
  /-- The number of ports, `0` to `ports - 1`, that a flood reaches. -/
  ports : Nat

/-- What one packet produced: the packets that left and, when the packet
was dropped for a reason the program did not decide, why. -/
structure SwitchResult where
  outputs : List (Nat × ByteArray)
  diagnostic : Option String := none

namespace Switch

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

/-- Load `index` under the switch with `ports` ports. -/
def load (index : Index) (bindings : BlockBindings) (ports : Nat) : Except String Switch := do
  (Bindings.check bindings index).mapError toString
  let role (r : String) (kind : BlockKind) : Except String String := do
    let some b := bindings.exported? index r | throw s!"the program exports no '{r}' block"
    if b.kind != kind then throw s!"export '{r}' has the wrong block kind"
    pure b.name
  let metadataType := bindings.metadata
  pure { index, parser := ← role "parser" .parser, control := ← role "control" .control, deparser := ← role "deparser" .deparser,
         metadataType,
         ingressPort := ← contractField index metadataType "ingress_port" (.bits 9),
         parserError := ← contractField index metadataType "parser_error" .error,
         egressPort := ← contractField index metadataType "egress_port" (.bits 9),
         drop := ← contractField index metadataType "drop" .boolean,
         flood := ← contractField index metadataType "flood" .boolean,
         ports }

/-- Field `position` of the struct `m`. -/
private def getField (m : Value) (position : Nat) : Except String Value := do
  let (_, fields) ← m.expectStruct
  let some v := fields[position]? | throw s!"metadata has no field {position}"
  pure v

/-- The struct `m` with field `position` set. -/
private def setField (m : Value) (position : Nat) (v : Value) : Except String Value := do
  let (t, fields) ← m.expectStruct
  pure (.struct t (fields.set position v))

/-- A boolean contract field of the metadata, `false` when not declared. -/
private def flag (m : Value) (f : Option MetaField) : Except String Bool := do
  let some f := f | pure false
  (← getField m f.position).expectBool

/-- Run one packet arriving on `ingress` through the three blocks. -/
def run (sw : Switch) (externs : Externs) (host : Entries) (ingress : Nat) (packet : ByteArray) :
    Except String (SwitchResult × Externs) := do
  if ingress ≥ sw.ports then throw s!"ingress_port {ingress} is not a port of this switch"
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
    runControl sw.index sw.control parsed.headers provided installed parsed.externs
  let (emitted, externs) ← runDeparser sw.index sw.deparser headers externs
  let payload := packet.extract (parsed.consumedBits / 8) packet.size
  let out := emitted ++ payload
  if ← flag metadata sw.drop then return ({ outputs := [] }, externs)
  if ← flag metadata sw.flood then
    return ({ outputs := (List.range sw.ports).filter (· != ingress) |>.map (·, out) }, externs)
  let egress ← match sw.egressPort with
    | some f => do pure (← (← getField metadata f.position).expectBits).value
    | none => pure 0
  if egress ≥ sw.ports then
    let why := s!"egress_port {egress} is not a port of this switch"
    return ({ outputs := [], diagnostic := some why }, externs)
  pure ({ outputs := [(egress, out)] }, externs)

end Switch

end P4bloArch
