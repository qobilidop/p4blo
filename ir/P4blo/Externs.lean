import Std.Data.HashMap
import P4blo.Value

/-!
# Extern models

The Lean side of the corpus externs, pinned to `python/p4blo/externs/` by
vectors (docs/design.md, "Externs"). An extern is state owned by the caller
(docs/semantics.md, "Externs"): `Externs` holds one `ExternState` per
instance, every call returns the state after it, and the caller threads it
through the three block runs and across packets.

Binding mirrors `python/p4blo/externs/__init__.py`: an instance's extern
type name selects the model, and the declaration is checked against the
model's `Shape`, where a width may be a variable such as `"T"` that the
declaration binds consistently. The error sentences are the Python ones.
-/

namespace P4blo

open Std (HashMap)

/-- What a method call produced: one value per `out` or `inout` parameter,
in parameter order, and the return value if any. -/
structure ExternResult where
  outs : List Value := []
  returns : Option Value := none
  deriving Repr, Inhabited

-- ---------------------------------------------------------------------------
-- Shapes
-- ---------------------------------------------------------------------------

/-- A bit width, or the name of a width variable bound by the declaration. -/
inductive Width
  | fixed (n : Nat)
  | var (name : String)
  deriving Repr, BEq

structure ParamShape where
  direction : Direction
  width : Width
  deriving Repr

structure MethodShape where
  params : List ParamShape
  returns : Option Width := none
  deriving Repr

/-- The declarations a model accepts. -/
structure Shape where
  constructor : List Width
  methods : List (String × MethodShape)
  deriving Repr

/-- Width variables bound while matching a declaration against a shape. -/
abbrev Bindings := HashMap String Nat

/-- Bind or check the width variable `expected` against `ty` at `where_`. -/
def Bindings.unify (b : Bindings) (expected : Width) (ty : Ty) (where_ : String) :
    Except String Bindings := do
  let .bits n := ty | throw s!"{where_}: expected bits, got {repr ty}"
  match expected with
  | .fixed w =>
    if n != w then throw s!"{where_}: expected bit<{w}>, got bit<{n}>"
    pure b
  | .var name =>
    match b[name]? with
    | none => pure (b.insert name n)
    | some bound =>
      if bound != n then throw s!"{where_}: {name} is bit<{bound}> elsewhere, bit<{n}> here"
      pure b

/-- Check `decl` against `shape`; the width bindings or an error. -/
def matchShape (decl : ExternType) (shape : Shape) : Except String Bindings := do
  let name := decl.name
  if decl.constructorParams.length != shape.constructor.length then
    throw s!"{name}: constructor takes {shape.constructor.length} args, declared {decl.constructorParams.length}"
  let mut b : Bindings := {}
  for ((param, width), i) in (decl.constructorParams.zip shape.constructor).zipIdx do
    if param.direction != .«in» then throw s!"{name}: constructor param {i} must be in"
    b ← b.unify width param.type s!"{name} constructor param {i}"
  let declared := decl.methods.map (·.name)
  let implemented := shape.methods.map (·.1)
  if !(declared.all implemented.contains && implemented.all declared.contains) then
    throw s!"{name}: methods {declared.mergeSort} declared, {implemented.mergeSort} implemented"
  for (methodName, methodShape) in shape.methods do
    let some method := decl.methods.find? (·.name == methodName) | throw s!"{name}: no method {methodName}"
    let where_ := s!"{name}.{methodName}"
    if method.params.length != methodShape.params.length then
      throw s!"{where_}: {methodShape.params.length} params expected"
    for ((param, expected), i) in (method.params.zip methodShape.params).zipIdx do
      if param.direction != expected.direction then throw s!"{where_} param {i}: direction mismatch"
      b ← b.unify expected.width param.type s!"{where_} param {i}"
    match methodShape.returns, method.returns with
    | none, none => pure ()
    | some w, some ty => b ← b.unify w ty s!"{where_} return"
    | _, _ => throw s!"{where_}: return type mismatch"
  pure b

-- ---------------------------------------------------------------------------
-- The models
-- ---------------------------------------------------------------------------

/-- The state of one extern instance. -/
inductive ExternState
  /-- `register(bit<32> size)` with `read(out T result, in bit<32> index)`
  and `write(in bit<32> index, in T value)`: `size` cells of width
  `width`, each starting at zero. A read at or beyond `size` gives zero and
  a write there is ignored. -/
  | register (width : Nat) (cells : Array Nat)
  /-- `counter(bit<32> size)` with `count(in bit<32> index)`: how often each
  index was counted; a count at or beyond `size` is ignored. -/
  | counter (counts : Array Nat)
  /-- `checksum16()` with `bit<16> compute(in bit<D> data)`: stateless. -/
  | checksum16
  deriving Repr, Inhabited

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

/-- Call `method` on a model with `args`, one value per parameter in order,
the current value for `out` and `inout` parameters. Called after the shape
check, so the argument shapes are trusted; anything else is an error. -/
def ExternState.call : ExternState → String → List Value → Except String (ExternState × ExternResult)
  | .register width cells, "read", [_, .bits index] =>
    let value := if h : index.value < cells.size then cells[index.value] else 0
    pure (.register width cells, { outs := [.bits (Bits.wrap width value)] })
  | .register width cells, "write", [.bits index, .bits value] =>
    let cells := if index.value < cells.size then cells.set! index.value value.value else cells
    pure (.register width cells, {})
  | .counter counts, "count", [.bits index] =>
    let counts := if h : index.value < counts.size then counts.set index.value (counts[index.value] + 1) else counts
    pure (.counter counts, {})
  | .checksum16, "compute", [.bits data] =>
    pure (.checksum16, { returns := some (.bits (Bits.wrap 16 (internetChecksum data.width data.value))) })
  | state, method, args => throw s!"bad extern call {method} with {args.length} arguments on {repr state}"

/-- The value of a literal. -/
def Literal.toValue : Literal → Value
  | .bits width value => .bits (Bits.wrap width value)
  | .boolean b => .bool b
  | .enumMember enumType member => .enum enumType member
  | .error name => .error name

/-- Whether a value has exactly this type (bits, boolean, enum, error). -/
def Value.fits : Value → Ty → Bool
  | .bits b, .bits n => b.width == n
  | .bool _, .boolean => true
  | .enum t _, .enumType n => t == n
  | .error _, .error => true
  | _, _ => false

/-- The extern state of one run: one model per extern instance, by name. -/
structure Externs where
  instances : HashMap String ExternState := {}
  deriving Inhabited

namespace Externs

/-- The model of the extern type `name`, if there is one. -/
def shapeOf : String → Option Shape
  | "register" => some registerShape
  | "counter" => some counterShape
  | "checksum16" => some checksum16Shape
  | _ => none

/-- The initial state of an instance of `decl` with constructor `args`. -/
private def make (decl : ExternType) (bindings : Bindings) (args : List Value) :
    Except String ExternState :=
  match (decl.name.splitOn ".").head!, args with
  | "register", [.bits size] => do
    let some width := bindings["T"]? | throw "register: T is unbound"
    pure (.register width (Array.replicate size.value 0))
  | "counter", [.bits size] => pure (.counter (Array.replicate size.value 0))
  | "checksum16", [] => pure .checksum16
  | name, _ => throw s!"{name}: constructor arguments do not fit"

/-- One model per extern instance of the program, as `Registry.bind` does:
an error on a declaration without a model or with a mismatched shape, and
on constructor arguments that do not fit. -/
def bind (index : Index) : Except String Externs := do
  let mut instances : HashMap String ExternState := {}
  for inst in index.program.externInstances do
    let some decl := index.externTypes[inst.externType]? | throw s!"unknown extern type '{inst.externType}'"
    let some shape := shapeOf (decl.name.splitOn ".").head!
      | throw s!"no implementation for extern type '{decl.name}'"
    let bindings ← matchShape decl shape
    let args := inst.args.map Literal.toValue
    if args.length != decl.constructorParams.length then
      throw s!"{inst.name}: constructor takes {decl.constructorParams.length} arguments"
    for ((param, value), i) in (decl.constructorParams.zip args).zipIdx do
      if !value.fits param.type then throw s!"{inst.name}: constructor arg {i} does not fit"
    instances := instances.insert inst.name (← make decl bindings args)
  pure { instances }

/-- Call `method` on instance `inst`; the result and the externs after. -/
def call (e : Externs) (inst method : String) (args : List Value) :
    Except String (Externs × ExternResult) := do
  let some state := e.instances[inst]? | throw s!"extern instance '{inst}' is not bound"
  let (state, result) ← state.call method args
  pure ({ instances := e.instances.insert inst state }, result)

end Externs

end P4blo
