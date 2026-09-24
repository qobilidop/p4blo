import P4bloIR.Index

/-!
# Run-time values

Mirrors `python/p4blo/interp/values.py`. A value carries everything the
semantics needs: a `Bits` knows its width, a header its validity, a stack
its next index (docs/ir-semantics.md, "Values"). Values are immutable, so the
Python `copy` is the identity here and is not written.
-/

namespace P4bloIR

-- ---------------------------------------------------------------------------
-- Bits
-- ---------------------------------------------------------------------------

/-- An unsigned value of `width` bits (docs/ir-semantics.md, "Values"). The
invariant `value < 2^width` is a field, so it holds by construction; every
arithmetic result goes through `Bits.wrap`. -/
structure Bits where
  width : Nat
  value : Nat
  isLt : value < 2 ^ width

namespace Bits

/-- Reduce `value` modulo `2^width`: the wrapping of §8.6. -/
def wrap (width value : Nat) : Bits :=
  ⟨width, value % 2 ^ width, Nat.mod_lt _ (Nat.two_pow_pos width)⟩

/-- `2^width - 1`, the saturation point of `|+|`. -/
def max (width : Nat) : Bits := wrap width (2 ^ width - 1)

instance : BEq Bits := ⟨fun a b => a.width == b.width && a.value == b.value⟩
instance : Repr Bits := ⟨fun b _ => s!"{b.width}w{b.value}"⟩
instance : Inhabited Bits := ⟨wrap 1 0⟩

end Bits

-- ---------------------------------------------------------------------------
-- Values
-- ---------------------------------------------------------------------------

/-- A run-time value. Header fields are `bits` or `bool`; struct fields are
any value; stack elements are headers of the stack's header type. -/
inductive Value
  | bits (b : Bits)
  | bool (b : Bool)
  /-- A member of an enum, compared by name. -/
  | enum (enumType : String) (member : String)
  /-- A name from `Program.errors`; `"NoError"` means no error. -/
  | error (name : String)
  | header (typeName : String) (valid : Bool) (fields : List Value)
  | struct (typeName : String) (fields : List Value)
  | stack (headerType : String) (elements : List Value) (nextIndex : Nat)
  deriving Repr, BEq, Inhabited

namespace Value

/-- The error value that means no error. -/
def noError : Value := .error "NoError"

-- Narrowing helpers: a validated program never fails these. The messages are
-- expr.py's.

/-- The kind name used in narrowing errors, matching Python's class names. -/
def kindName : Value → String
  | .bits _ => "Bits"
  | .bool _ => "bool"
  | .enum .. => "EnumValue"
  | .error _ => "ErrorValue"
  | .header .. => "Header"
  | .struct .. => "Struct"
  | .stack .. => "Stack"

def expectBits : Value → Except String Bits
  | .bits b => pure b
  | v => throw s!"expected bits, got {v.kindName}"

def expectBool : Value → Except String Bool
  | .bool b => pure b
  | v => throw s!"expected boolean, got {v.kindName}"

/-- A header as its `(typeName, valid, fields)`. -/
def expectHeader : Value → Except String (String × Bool × List Value)
  | .header t valid fields => pure (t, valid, fields)
  | v => throw s!"expected header, got {v.kindName}"

/-- A struct as its `(typeName, fields)`. -/
def expectStruct : Value → Except String (String × List Value)
  | .struct t fields => pure (t, fields)
  | v => throw s!"expected struct, got {v.kindName}"

/-- A stack as its `(headerType, elements, nextIndex)`. -/
def expectStack : Value → Except String (String × List Value × Nat)
  | .stack t elements next => pure (t, elements, next)
  | v => throw s!"expected header stack, got {v.kindName}"

-- ---------------------------------------------------------------------------
-- Zero values
-- ---------------------------------------------------------------------------

/-- `zero` with a nesting bound. Types nest through the index, not through
`Ty` itself, so the recursion is on `fuel`: a chain of nested header and
struct types longer than the number of declared types would repeat one,
which the validator rejects, so `Value.zero` never runs out. -/
def zeroWith (index : Index) : Nat → Ty → Except String Value
  | 0, _ => throw "type nesting deeper than the number of declared types"
  | fuel + 1, ty =>
    match ty with
    | .bits n => pure (.bits (Bits.wrap n 0))
    | .boolean => pure (.bool false)
    | .header name => do
      let some decl := index.headerTypes[name]? | throw s!"unknown header type '{name}'"
      let fields ← decl.fields.mapM fun f => zeroWith index fuel f.type
      pure (.header decl.name false fields)
    | .struct name => do
      let some decl := index.structTypes[name]? | throw s!"unknown struct type '{name}'"
      let fields ← decl.fields.mapM fun f => zeroWith index fuel f.type
      pure (.struct decl.name fields)
    | .enumType name => do
      let some decl := index.enumTypes[name]? | throw s!"unknown enum type '{name}'"
      let some member := decl.members.head? | throw s!"enum '{name}' has no members"
      pure (.enum name member)
    | .error => pure noError
    | .stack hdr size => do
      let element ← zeroWith index fuel (.header hdr)
      pure (.stack hdr (List.replicate size element) 0)

/-- The initial value of a type: zero bits, `false`, member 0, `NoError`,
invalid headers with zero fields, and stacks with `nextIndex` 0
(docs/ir-semantics.md, "Uninitialized variables"). -/
def zero (ty : Ty) (index : Index) : Except String Value :=
  zeroWith index (index.headerTypes.size + index.structTypes.size + 2) ty

/-- An invalid header of `typeName` with zero fields. -/
def zeroHeader (typeName : String) (index : Index) : Except String Value :=
  zero (.header typeName) index

-- ---------------------------------------------------------------------------
-- Equality
-- ---------------------------------------------------------------------------

mutual
/-- `==` as docs/ir-semantics.md, "Comparison", defines it: by value on bits and
booleans, by member on enums and errors, on headers by validity and then
fieldwise (two invalid headers are equal whatever their fields), on structs
fieldwise, on stacks elementwise. -/
def equal : Value → Value → Bool
  -- Keep scalar meaning proof-visible instead of entering the opaque
  -- derived comparison for nested recursive Value. These are the same
  -- width/value and Bool comparisons used by that runtime instance.
  | .bits a, .bits b => a == b
  | .bool a, .bool b => a == b
  | .header _ va fa, .header _ vb fb =>
    if va != vb then false else if !va then true else equalList fa fb
  | .struct _ fa, .struct _ fb => equalList fa fb
  | .stack _ ea _, .stack _ eb _ => equalList ea eb
  | a, b => a == b

/-- Fieldwise equality. Lists of different lengths are unequal; a validated
program never compares such values. -/
def equalList : List Value → List Value → Bool
  | [], [] => true
  | x :: xs, y :: ys => equal x y && equalList xs ys
  | _, _ => false
end

@[simp] theorem equal_bits (a b : Bits) :
    equal (.bits a) (.bits b) = (a.width == b.width && a.value == b.value) := rfl

@[simp] theorem equal_bool (a b : Bool) :
    equal (.bool a) (.bool b) = (a == b) := rfl

end Value

end P4bloIR
