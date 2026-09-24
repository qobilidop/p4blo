import P4bloIR.Env
import P4bloIR.Widths

/-!
# Expressions and lvalues

Mirrors `impl/python/p4blo/interp/expr.py`. `evaluate` has one case per `Expr`
kind and implements docs/ir-semantics.md, "Values". `readLValue` and
`writeLValue` implement "Headers" and "Header stacks": a read of an invalid
header returns its stored fields, a read past a stack's end returns a zero
invalid header, and a write past its end does nothing. `hs.next` is only
ever the target of an `extract`, which `Exec` handles on its own.

Every `Bits` result goes through `Bits.wrap`, which enforces the width
invariant. Values are immutable, so a write rebuilds the containers on the
path from the variable to the field; Python mutates them in place. The
index expression of an `LIndex` on that path is evaluated once on the way
down and once on the way up; evaluation has no effect but a `lookahead`
peek, so that is invisible.
-/

namespace P4bloIR

-- ---------------------------------------------------------------------------
-- Narrowing in the monad
-- ---------------------------------------------------------------------------

def expectBits (v : Value) : M Bits := liftExcept v.expectBits
def expectBool (v : Value) : M Bool := liftExcept v.expectBool
def expectHeader (v : Value) : M (String × Bool × List Value) := liftExcept v.expectHeader
def expectStruct (v : Value) : M (String × List Value) := liftExcept v.expectStruct
def expectStack (v : Value) : M (String × List Value × Nat) := liftExcept v.expectStack

-- ---------------------------------------------------------------------------
-- Literals and packet representations
-- ---------------------------------------------------------------------------

/-- The value of a literal. -/
def literalValue (lit : Literal) : Value := lit.toValue

/-- The fields of widths `ws` read out of `raw`, first field in the high
bits: field `i` is the `ws[i]` bits of `raw` just above its low
`ws[i+1] + ⋯` bits. The pure core of `extract` and `lookahead`;
`P4bloIR.Theorems` proves it the inverse of `packFields`. -/
def unpackFields : List Nat → Nat → List Nat
  | [], _ => []
  | w :: ws, raw => (raw >>> ws.sum) % 2 ^ w :: unpackFields ws raw

/-- The `(width, value)` pairs concatenated, first pair in the high bits:
`packFields [(w₁, v₁), …, (wₖ, vₖ)]` is `v₁ <<< (w₂ + ⋯ + wₖ) ||| ⋯ ||| vₖ`.
The pure core of `emit`. -/
def packFields : List (Nat × Nat) → Nat
  | [] => 0
  | (_, v) :: fs => (v <<< (fs.map Prod.fst).sum) ||| packFields fs

/-- Field `f` holding `chunk`, a `width`-bit number: a boolean is `1`,
anything else is bits. -/
def fieldFromBits (f : Field) (width chunk : Nat) : Value :=
  if f.type == .boolean then .bool (chunk == 1) else .bits (Bits.wrap width chunk)

/-- A valid header of `typeName` whose fields hold `raw`, first field in
the high bits (docs/ir-semantics.md, "Extract sets the target valid"). -/
def headerFromBits (typeName : String) (raw : Nat) (index : Index) : Except String Value := do
  let some decl := index.headerTypes[typeName]? | throw s!"unknown header type '{typeName}'"
  let widths ← decl.fields.mapM fun f => widthOf f.type index
  let fields := (decl.fields.zip (widths.zip (unpackFields widths raw))).map fun p =>
    fieldFromBits p.1 p.2.1 p.2.2
  pure (.header typeName true fields)

/-- The `(width, value)` of one header field; a boolean is one bit. -/
def fieldBits : Value → Except String (Nat × Nat)
  | .bool b => pure (1, if b then 1 else 0)
  | .bits b => pure (b.width, b.value)
  | v => throw s!"expected bits, got {v.kindName}"

/-- The `(width, value)` of a header's fields concatenated, first field in
the high bits; the inverse of `headerFromBits`. -/
def headerToBits (fields : List Value) : Except String (Nat × Nat) := do
  let fs ← fields.mapM fieldBits
  pure ((fs.map Prod.fst).sum, packFields fs)

/-- The value of `ty` that `raw` spells: what `lookahead<T>` returns. -/
def valueFromBits (ty : Ty) (raw : Nat) (index : Index) : Except String Value :=
  match ty with
  | .bits n => pure (.bits (Bits.wrap n raw))
  | .boolean => pure (.bool (raw == 1))
  | .header name => headerFromBits name raw index
  | t => throw s!"cannot read a value of kind {repr t} from the packet"

-- ---------------------------------------------------------------------------
-- Containers
-- ---------------------------------------------------------------------------

/-- Field `field` of a header or struct; an invalid header's stored fields
are returned as they are (docs/ir-semantics.md, "Headers"). -/
def fieldOf (container : Value) (field : String) : M Value := do
  let (typeName, fields) ← match container with
    | .header t _ fields => pure (t, fields)
    | .struct t fields => pure (t, fields)
    | v => throwInterp s!"{v.kindName} has no fields"
  let some i := (← getIndex).fieldIndex? typeName field | throwInterp s!"{typeName}.{field}"
  match fields[i]? with
  | some v => pure v
  | none => throwInterp s!"{typeName}.{field}"

/-- `container` with `field` set to `value`; validity is untouched
(docs/ir-semantics.md, "Writing a field of an invalid header"). -/
def setField (container : Value) (field : String) (value : Value) : M Value := do
  let (typeName, fields, rebuild) ← match container with
    | .header t valid fields => pure (t, fields, fun fs => Value.header t valid fs)
    | .struct t fields => pure (t, fields, fun fs => Value.struct t fs)
    | v => throwInterp s!"{v.kindName} has no fields"
  let some i := (← getIndex).fieldIndex? typeName field | throwInterp s!"{typeName}.{field}"
  pure (rebuild (fields.set i value))

/-- `hs[i]`; past the end, a zero invalid header not stored anywhere
(docs/ir-semantics.md, "Index out of range"). -/
def elementOf (headerType : String) (elements : List Value) (i : Nat) : M Value := do
  match elements[i]? with
  | some h => pure h
  | none => liftExcept (Value.zeroHeader headerType (← getIndex))

-- ---------------------------------------------------------------------------
-- Expressions
-- ---------------------------------------------------------------------------

/-- The `bit<N>` operators of docs/ir-semantics.md, "Values": wrapping and
saturating arithmetic, bitwise operators, shifts that give `0` at the width
or more, concatenation with the left operand high, unsigned comparison. -/
def bitsBinary (op : BinaryOp) (x y : Bits) : M Value :=
  let n := x.width
  match op with
  | .add => pure (.bits (Bits.wrap n (x.value + y.value)))
  | .sub => pure (.bits (Bits.wrap n (x.value + 2 ^ n - y.value)))
  | .mul => pure (.bits (Bits.wrap n (x.value * y.value)))
  | .addSat => pure (.bits (Bits.wrap n (min (x.value + y.value) (2 ^ n - 1))))
  | .subSat => pure (.bits (Bits.wrap n (x.value - y.value)))
  | .bitAnd => pure (.bits (Bits.wrap n (x.value &&& y.value)))
  | .bitOr => pure (.bits (Bits.wrap n (x.value ||| y.value)))
  | .bitXor => pure (.bits (Bits.wrap n (x.value ^^^ y.value)))
  | .shl => pure (.bits (if y.value < n then Bits.wrap n (x.value <<< y.value) else Bits.wrap n 0))
  | .shr => pure (.bits (if y.value < n then Bits.wrap n (x.value >>> y.value) else Bits.wrap n 0))
  | .concat => pure (.bits (Bits.wrap (x.width + y.width) ((x.value <<< y.width) ||| y.value)))
  | .lt => pure (.bool (x.value < y.value))
  | .le => pure (.bool (x.value ≤ y.value))
  | .gt => pure (.bool (x.value > y.value))
  | .ge => pure (.bool (x.value ≥ y.value))
  | .eq | .ne | .and | .or => throwInterp "binary operator is not a bits operator"

/-- Bits to bits truncates or zero-extends; `bool` and `bit<1>` map onto
each other (docs/ir-semantics.md, "Casts"). -/
def castValue (to : Ty) (operand : Value) : M Value :=
  match to, operand with
  | .bits n, .bool b => pure (.bits (Bits.wrap n (if b then 1 else 0)))
  | .bits n, v => do pure (.bits (Bits.wrap n (← expectBits v).value))
  | .boolean, v => do pure (.bool ((← expectBits v).value == 1))
  | t, _ => throwInterp s!"no cast to {repr t}"

/-- Read `width(T)` bits without moving the cursor; a header result is
valid (docs/ir-semantics.md, "lookahead"). -/
def lookaheadValue (ty : Ty) : M Value := do
  let packet ← requirePacket
  let index ← getIndex
  let width ← liftExcept (widthOf ty index)
  let some raw := packet.peek? width | throwParse "PacketTooShort"
  liftExcept (valueFromBits ty raw index)

/-- Evaluate an expression. `&&`, `||` and the mux evaluate only the
operands they need; `==` and `!=` use `Value.equal`. -/
def evaluate : Expr → M Value
  | .literal lit => pure (literalValue lit)
  | .var name => readVar name
  | .member base field => do fieldOf (← evaluate base) field
  | .index base idx => do
    let (headerType, elements, _) ← expectStack (← evaluate base)
    let i ← expectBits (← evaluate idx)
    elementOf headerType elements i.value
  | .lastIndex stack => do
    -- `nextIndex - 1` as a `bit<32>`, wrapping at `nextIndex == 0`.
    let (_, _, nextIndex) ← expectStack (← evaluate stack)
    pure (.bits (Bits.wrap 32 (nextIndex + 2 ^ 32 - 1)))
  | .unary op operand => do
    let v ← evaluate operand
    match op with
    | .not => pure (.bool (!(← expectBool v)))
    | .complement => do
      let x ← expectBits v
      pure (.bits (Bits.wrap x.width (2 ^ x.width - 1 - x.value)))
    | .negate => do
      let x ← expectBits v
      pure (.bits (Bits.wrap x.width (2 ^ x.width - x.value)))
  | .binary op left right => do
    match op with
    | .and => do
      if ← expectBool (← evaluate left) then pure (.bool (← expectBool (← evaluate right)))
      else pure (.bool false)
    | .or => do
      if ← expectBool (← evaluate left) then pure (.bool true)
      else pure (.bool (← expectBool (← evaluate right)))
    | .eq => do
      let l ← evaluate left
      let r ← evaluate right
      pure (.bool (Value.equal l r))
    | .ne => do
      let l ← evaluate left
      let r ← evaluate right
      pure (.bool (!Value.equal l r))
    | _ => do
      let l ← evaluate left
      let r ← evaluate right
      bitsBinary op (← expectBits l) (← expectBits r)
  | .cast to operand => do castValue to (← evaluate operand)
  | .slice operand hi lo => do
    let x ← expectBits (← evaluate operand)
    if hi < lo then throwInterp s!"slice [{hi}:{lo}] is empty"
    pure (.bits (Bits.wrap (hi - lo + 1) (x.value >>> lo)))
  | .isValid header => do
    let (_, valid, _) ← expectHeader (← evaluate header)
    pure (.bool valid)
  | .mux condition thenBranch otherwise => do
    if ← expectBool (← evaluate condition) then evaluate thenBranch else evaluate otherwise
  | .lookahead ty => lookaheadValue ty

-- ---------------------------------------------------------------------------
-- Lvalues
-- ---------------------------------------------------------------------------

/-- The value an lvalue currently denotes. `hs.next` is only ever the
target of an `extract`, which handles it itself (docs/ir-semantics.md,
"`hs.next`"); anywhere else it is invalid input. -/
def readLValue : LValue → M Value
  | .var name => readVar name
  | .member base field => do fieldOf (← readLValue base) field
  | .index base idx => do
    let (headerType, elements, _) ← expectStack (← readLValue base)
    let i ← expectBits (← evaluate idx)
    elementOf headerType elements i.value
  | .next _ => throwInterp "hs.next is only the target of an extract"

/-- Store `value` at `lv`.

A whole-header write copies validity and fields; a write through a stack
index past the end does nothing. `hs.next` is not a general lvalue: see
`readLValue`. -/
def writeLValue : LValue → Value → M Unit
  | .var name, value => writeVar name value
  | .member base field, value => do
    -- A container past a stack's end is a fresh zero header; writing it
    -- back through the index changes nothing, as the semantics require.
    let container ← readLValue base
    writeLValue base (← setField container field value)
  | .index base idx, value => do
    let (headerType, elements, nextIndex) ← expectStack (← readLValue base)
    let i ← expectBits (← evaluate idx)
    if i.value < elements.length then
      let (t, valid, fields) ← expectHeader value
      writeLValue base (.stack headerType (elements.set i.value (.header t valid fields)) nextIndex)
  | .next _, _ => throwInterp "hs.next is only the target of an extract"

end P4bloIR
