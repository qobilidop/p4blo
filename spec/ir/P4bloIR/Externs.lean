import Std.Data.HashMap
import P4bloIR.Value

/-!
# Externs as contracts

An extern is state owned by the caller (docs/ir-semantics.md, "Externs").
The IR says only an extern type's method signatures, an instance's
constructor arguments and the call sites; which families exist and what a
call does to their state is the architecture's decision, supplied at load
as an `ExternRegistry`. `Externs` holds
the logical state of every instance and the model that interprets calls;
every call returns the state after it, and the caller threads it through
the three block runs and across packets.

Binding mirrors `impl/python/p4blo/arch/externs/__init__.py`: an instance's
family, the segment of its extern type name before the first dot, selects
the model, and the declaration is checked against the model's `Shape`,
where a width may be a variable such as `"T"` that the declaration binds
consistently. The error sentences are the Python ones.
-/

namespace P4bloIR

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
-- State and models
-- ---------------------------------------------------------------------------

/-- The logical state of one extern instance, as the IR carries it: the
family's kind name, an optional cell width, optional natural cells, and
configuration the model needs but observers do not report. This is what a
differential observation reports and what a proof about persistent state
inspects; the model that interprets a call on it is the architecture's. -/
structure ExternState where
  kind : String
  width : Option Nat := none
  cells : Option (Array Nat) := none
  config : List Nat := []
  deriving Repr, BEq, DecidableEq, Inhabited

/-- What a model does on a method call: the state after it and the result. -/
structure ExternModel where
  call : ExternState → String → List Value → Except String (ExternState × ExternResult)

/-- No model: every call is an error. -/
def ExternModel.none : ExternModel :=
  ⟨fun s method _ => throw s!"no extern model for {s.kind}.{method}"⟩

instance : Inhabited ExternModel := ⟨.none⟩

/-- What an architecture supplies for binding: the shape each family
accepts, the initial state of an instance, and the model. -/
structure ExternRegistry where
  shapeOf : String → Option Shape
  make : ExternType → Bindings → List Value → Except String ExternState
  model : ExternModel

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

/-- The extern state of one run: the model that interprets calls and one
logical state per extern instance, by name. -/
structure Externs where
  model : ExternModel := .none
  instances : HashMap String ExternState := {}
  deriving Inhabited

namespace Externs

/-- One state per extern instance of the program, under `registry`, as the
Python `Registry.bind` does: an error on a declaration without a model or
with a mismatched shape, and on constructor arguments that do not fit. -/
def bind (registry : ExternRegistry) (index : Index) : Except String Externs := do
  let mut instances : HashMap String ExternState := {}
  for inst in index.program.externInstances do
    let some decl := index.externTypes[inst.externType]? | throw s!"unknown extern type '{inst.externType}'"
    let some shape := registry.shapeOf (decl.name.splitOn ".").head!
      | throw s!"no implementation for extern type '{decl.name}'"
    let bindings ← matchShape decl shape
    let args := inst.args.map Literal.toValue
    if args.length != decl.constructorParams.length then
      throw s!"{inst.name}: constructor takes {decl.constructorParams.length} arguments"
    for ((param, value), i) in (decl.constructorParams.zip args).zipIdx do
      if !value.fits param.type then throw s!"{inst.name}: constructor arg {i} does not fit"
    instances := instances.insert inst.name (← registry.make decl bindings args)
  pure { model := registry.model, instances }

/-- Call `method` on instance `inst` under the model; the result and the
externs after. -/
def call (e : Externs) (inst method : String) (args : List Value) :
    Except String (Externs × ExternResult) := do
  let some state := e.instances[inst]? | throw s!"extern instance '{inst}' is not bound"
  let (state, result) ← e.model.call state method args
  pure ({ e with instances := e.instances.insert inst state }, result)

end Externs

end P4bloIR
