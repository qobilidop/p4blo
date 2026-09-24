import P4bloIR.Externs

/-!
# The extern families of the reference architecture

The IR carries an extern instance's logical state and sees an extern as a
contract (docs/ir-semantics.md, "Externs"); which families exist and what a
call does to their state is the architecture's decision
(docs/arch-supports.md, "Extern families"). This module supplies the five
families the supplied architectures provide, pinned to
`impl/python/p4blo/arch/externs/` by vectors and independent known answers:
`register`, `counter`, `checksum16`, `crc16` and `crc32`.

Binding mirrors `impl/python/p4blo/arch/externs/__init__.py`: an instance's
family, the segment of its extern type name before the first dot, selects
the model, and the declaration is checked against the model's `Shape`. The
error sentences are the Python ones.
-/

namespace P4bloIR.ExternState

/-! How the reference architecture represents each family in the IR's
logical extern state. Proofs and tests build states through these. -/

/-- `size` cells of width `width`, each starting at zero. -/
def register (width : Nat) (cells : Array Nat) : ExternState :=
  { kind := "register", width := some width, cells := some cells }

/-- How often each index was counted. -/
def counter (counts : Array Nat) : ExternState :=
  { kind := "counter", cells := some counts }

/-- Stateless. -/
def checksum16 : ExternState := { kind := "checksum16" }

/-- Stateless full byte-aligned CRC, remembering the monomorphic input width. -/
def crc16 (dataWidth : Nat) : ExternState := { kind := "crc16", config := [dataWidth] }
def crc32 (dataWidth : Nat) : ExternState := { kind := "crc32", config := [dataWidth] }

/-- The width and cells of a register state. -/
def register? (s : ExternState) : Option (Nat × Array Nat) :=
  match s.kind, s.width, s.cells with
  | "register", some width, some cells => some (width, cells)
  | _, _, _ => none

/-- The counts of a counter state. -/
def counter? (s : ExternState) : Option (Array Nat) :=
  match s.kind, s.cells with
  | "counter", some counts => some counts
  | _, _ => none

end P4bloIR.ExternState

namespace P4bloArch

open P4bloIR

-- ---------------------------------------------------------------------------
-- Shapes
-- ---------------------------------------------------------------------------

/-- The shape of `register`. -/
def registerShape : Shape :=
  { constructor := [.fixed 32],
    methods := [("read", { params := [⟨.out, .var "T"⟩, ⟨.«in», .fixed 32⟩] }),
                ("write", { params := [⟨.«in», .fixed 32⟩, ⟨.«in», .var "T"⟩] })] }

/-- The shape of `counter`. -/
def counterShape : Shape :=
  { constructor := [.fixed 32], methods := [("count", { params := [⟨.«in», .fixed 32⟩] })] }

/-- The shape of `checksum16`. -/
def checksum16Shape : Shape :=
  { constructor := [], methods := [("compute", { params := [⟨.«in», .var "D"⟩], returns := some (.fixed 16) })] }

/-- A stateless full-width CRC over a monomorphic bit string. -/
def crcShape (outputWidth : Nat) : Shape :=
  { constructor := [], methods := [("compute", { params := [⟨.«in», .var "D"⟩], returns := some (.fixed outputWidth) })] }

/-- The model of the extern family `name`, if there is one. -/
def shapeOf : String → Option Shape
  | "register" => some registerShape
  | "counter" => some counterShape
  | "checksum16" => some checksum16Shape
  | "crc16" => some (crcShape 16)
  | "crc32" => some (crcShape 32)
  | _ => none

-- ---------------------------------------------------------------------------
-- The arithmetic
-- ---------------------------------------------------------------------------

/-- Reflect exactly `width` low bits. -/
def reflectBits (width value : Nat) : Nat :=
  (List.range width).foldl (fun acc i => (acc <<< 1) ||| ((value >>> i) &&& 1)) 0

/-- Forward-polynomial CRC with explicitly reflected input bytes and output.
Unlike Python's reflected byte lookup, this shifts a bounded register left
one input bit at a time. Only the extern binding advertises supported widths. -/
def fullCRC (outputWidth polynomial initial finalXor dataWidth value : Nat) : Nat :=
  let mask := 2 ^ outputWidth - 1
  let bytes := dataWidth / 8
  let result := (List.range bytes).foldl (fun crc i =>
    let byte := (value >>> (8 * (bytes - 1 - i))) &&& 255
    (List.range 8).foldl (fun crc bit =>
      let feedback := ((crc >>> (outputWidth - 1)) ^^^ (byte >>> bit)) &&& 1
      let shifted := (crc <<< 1) &&& mask
      if feedback == 1 then shifted ^^^ polynomial else shifted) crc) initial
  reflectBits outputWidth result ^^^ finalXor

def crc16 (dataWidth value : Nat) : Nat := fullCRC 16 0x8005 0 0 dataWidth value
def crc32 (dataWidth value : Nat) : Nat :=
  fullCRC 32 0x04c11db7 0xffffffff 0xffffffff dataWidth value

/-- Fold the carries of a one's-complement sum until it fits in 16 bits. -/
def foldCarry (total : Nat) : Nat :=
  if h : total / 65536 = 0 then total
  else foldCarry (total % 65536 + total / 65536)
termination_by total
decreasing_by omega

/-- The 16-bit words of `value`, which spans `words` words, most significant
first. -/
def words16 (value : Nat) : Nat → List Nat
  | 0 => []
  | n + 1 => ((value >>> (16 * n)) % 65536) :: words16 value n

/-- RFC 1071 over `value` as a bit string of `width` bits, zero-padded at
the end to a multiple of 16: the one's complement of the one's-complement
sum of the 16-bit words. -/
def internetChecksum (width value : Nat) : Nat :=
  let words := (width + 15) / 16
  let padded := value <<< (words * 16 - width)
  let total := (words16 padded words).foldl (· + ·) 0
  65535 - foldCarry total

-- ---------------------------------------------------------------------------
-- The model
-- ---------------------------------------------------------------------------

/-- Call `method` on a state with `args`, one value per parameter in order,
the current value for `out` and `inout` parameters. Called after the shape
check, so the argument shapes are trusted; anything else is an error. A
register read at or beyond `size` gives zero and a write there is ignored;
a count at or beyond `size` is ignored (docs/arch-supports.md). -/
def call (s : ExternState) (method : String) (args : List Value) :
    Except String (ExternState × ExternResult) :=
  match s.kind, s.width, s.cells, s.config, method, args with
  | "register", some width, some cells, _, "read", [_, .bits index] =>
    let value := if h : index.value < cells.size then cells[index.value] else 0
    pure (.register width cells, { outs := [.bits (Bits.wrap width value)] })
  | "register", some width, some cells, _, "write", [.bits index, .bits value] =>
    let cells := if index.value < cells.size then cells.set! index.value value.value else cells
    pure (.register width cells, {})
  | "counter", _, some counts, _, "count", [.bits index] =>
    let counts := if h : index.value < counts.size then counts.set index.value (counts[index.value] + 1) else counts
    pure (.counter counts, {})
  | "checksum16", _, _, _, "compute", [.bits data] =>
    pure (.checksum16, { returns := some (.bits (Bits.wrap 16 (internetChecksum data.width data.value))) })
  | "crc16", _, _, [width], "compute", [.bits data] => do
    if data.width != width then throw "crc16: call does not fit bound width"
    pure (.crc16 width, { returns := some (.bits (Bits.wrap 16 (crc16 width data.value))) })
  | "crc32", _, _, [width], "compute", [.bits data] => do
    if data.width != width then throw "crc32: call does not fit bound width"
    pure (.crc32 width, { returns := some (.bits (Bits.wrap 32 (crc32 width data.value))) })
  | _, _, _, _, _, _ => throw s!"bad extern call {method} with {args.length} arguments on {repr s}"

/-- The reference architecture's extern semantics, as the IR's `Externs` carries them. -/
def model : ExternModel := ⟨call⟩

/-- The initial state of an instance of `decl` with constructor `args`. -/
def make (decl : ExternType) (bindings : Bindings) (args : List Value) :
    Except String ExternState :=
  match (decl.name.splitOn ".").head!, args with
  | "register", [.bits size] => do
    let some width := bindings["T"]? | throw "register: T is unbound"
    pure (.register width (Array.replicate size.value 0))
  | "counter", [.bits size] => pure (.counter (Array.replicate size.value 0))
  | "checksum16", [] => pure .checksum16
  | "crc16", [] | "crc32", [] => do
    let family := (decl.name.splitOn ".").head!
    let some width := bindings["D"]? | throw s!"{family}: D is unbound"
    if width == 0 || width % 8 != 0 then
      throw s!"{family}: data width must be a positive multiple of 8"
    pure (if family == "crc16" then .crc16 width else .crc32 width)
  | name, _ => throw s!"{name}: constructor arguments do not fit"

/-- What the reference architecture supplies to `Externs.bind`. -/
def registry : ExternRegistry := { shapeOf, make, model }

/-- One state per extern instance of the program under the reference
model, as `Registry.bind` does on the Python side. -/
def bind (index : Index) : Except String Externs := Externs.bind registry index

/-- Extern state under the reference model, from given instances. -/
def externs (instances : Std.HashMap String ExternState) : Externs :=
  { model, instances }

end P4bloArch
