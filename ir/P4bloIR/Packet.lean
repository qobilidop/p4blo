/-!
# The packet under a parser and the buffer of a deparser

Mirrors `python/p4blo/interp/packet.py`. Both work in bits, most significant
first, because headers need not be byte aligned (docs/semantics.md,
"Parsers" and "Deparsers"). Neither raises: a read past the end returns
`none`, and the interpreter turns that into `PacketTooShort`.
-/

namespace P4bloIR

/-- The bytes of `data` as one big-endian natural number. -/
def bytesToNat (data : ByteArray) : Nat :=
  data.data.foldl (fun n b => n * 256 + b.toNat) 0

/-- The low `size` bytes of `n`, big-endian. -/
def natToBytes (n : Nat) (size : Nat) : ByteArray :=
  let rec go : Nat → Nat → List UInt8 → List UInt8
    | 0, _, acc => acc
    | k + 1, m, acc => go k (m / 256) (UInt8.ofNat (m % 256) :: acc)
  ⟨(go size n []).toArray⟩

/-- A packet under a parser: bytes that never change and a cursor in bits. -/
structure Packet where
  data : ByteArray
  /-- `bytesToNat data`, computed once. -/
  value : Nat
  cursor : Nat
  deriving Inhabited

namespace Packet

def ofBytes (data : ByteArray) : Packet := { data, value := bytesToNat data, cursor := 0 }

def totalBits (p : Packet) : Nat := p.data.size * 8

def remainingBits (p : Packet) : Nat := p.totalBits - p.cursor

/-- The next `n` bits as a number, without moving the cursor; `none` when
fewer than `n` bits remain. -/
def peek? (p : Packet) (n : Nat) : Option Nat :=
  if n > p.remainingBits then none
  else some ((p.value >>> (p.remainingBits - n)) % 2 ^ n)

/-- `peek?`, then the cursor moved past the bits. -/
def read? (p : Packet) (n : Nat) : Option (Nat × Packet) := do
  let v ← p.peek? n
  pure (v, { p with cursor := p.cursor + n })

/-- The cursor moved by `n` bits; `none` past the end (docs/semantics.md,
"advance"). -/
def advance? (p : Packet) (n : Nat) : Option Packet :=
  if n > p.remainingBits then none else some { p with cursor := p.cursor + n }

end Packet

/-- The output of a deparser: bits appended in order, padded to bytes. -/
structure Emitter where
  value : Nat := 0
  width : Nat := 0
  deriving Inhabited

namespace Emitter

/-- Append `value` as `width` bits. -/
def write (e : Emitter) (width value : Nat) : Emitter :=
  { value := (e.value <<< width) ||| value, width := e.width + width }

/-- Every bit written so far, then zero bits up to a byte boundary
(docs/semantics.md, "Bit alignment"). -/
def toBytes (e : Emitter) : ByteArray :=
  let padding := (8 - e.width % 8) % 8
  natToBytes (e.value <<< padding) ((e.width + padding) / 8)

end Emitter

end P4bloIR
