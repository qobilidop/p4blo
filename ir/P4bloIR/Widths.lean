import P4bloIR.Index

/-!
# Static types and widths

Mirrors `impl/python/p4blo/interp/widths.py`. Expressions carry no annotations,
so `typeOf` recomputes a type where the interpreter needs a width before it
has a value: the width of a table key at installation and of the header an
`extract` or `lookahead` reads.
-/

namespace P4bloIR

/-- `widthOf` with a nesting bound; see `Value.zeroWith` for why the
recursion is on `fuel`. -/
def widthOfWith (index : Index) : Nat → Ty → Except String Nat
  | 0, _ => throw "type nesting deeper than the number of declared types"
  | fuel + 1, ty =>
    match ty with
    | .bits n => pure n
    | .boolean => pure 1
    | .header name => do
      let some decl := index.headerTypes[name]? | throw s!"unknown header type '{name}'"
      decl.fields.foldlM (fun n f => (n + ·) <$> widthOfWith index fuel f.type) 0
    | .struct name => do
      let some decl := index.structTypes[name]? | throw s!"unknown struct type '{name}'"
      decl.fields.foldlM (fun n f => (n + ·) <$> widthOfWith index fuel f.type) 0
    | .stack header size => (size * ·) <$> widthOfWith index fuel (.header header)
    | .enumType _ => throw "a value of kind 'enum_type' has no width"
    | .error => throw "a value of kind 'error' has no width"

/-- The number of packet bits a value of `ty` occupies. -/
def widthOf (ty : Ty) (index : Index) : Except String Nat :=
  widthOfWith index (index.headerTypes.size + index.structTypes.size + 2) ty

/-- The type of a literal. -/
def literalType : Literal → Ty
  | .bits width _ => .bits width
  | .boolean _ => .boolean
  | .enumMember enumType _ => .enumType enumType
  | .error _ => .error

/-- The operators whose result is boolean. -/
def BinaryOp.isBoolean : BinaryOp → Bool
  | .eq | .ne | .lt | .le | .gt | .ge | .and | .or => true
  | _ => false

/-- The static type of `expr` as seen from `scope`, or from `action` in it. -/
def typeOf (index : Index) (scope : BlockScope) (action : Option String := none) :
    Expr → Except String Ty
  | .literal lit => pure (literalType lit)
  | .var name =>
    match scope.var? name action with
    | some decl => pure decl.type
    | none => throw s!"unknown variable '{name}' in block '{scope.block.name}'"
  | .member base field => do
    let baseTy ← typeOf index scope action base
    let name ← match baseTy with
      | .header n => pure n
      | .struct n => pure n
      | _ => throw s!"a {repr baseTy} has no fields"
    let some fields := index.fields? name | throw s!"unknown type '{name}'"
    match fields.find? (·.name == field) with
    | some f => pure f.type
    | none => throw s!"{name} has no field '{field}'"
  | .index base _ => do
    match ← typeOf index scope action base with
    | .stack header _ => pure (.header header)
    | t => throw s!"cannot index a {repr t}"
  | .lastIndex _ => pure (.bits 32)
  | .unary _ operand => typeOf index scope action operand
  | .binary op left right => do
    if op.isBoolean then pure .boolean
    else
      let l ← typeOf index scope action left
      if op == .concat then
        let r ← typeOf index scope action right
        match l, r with
        | .bits a, .bits b => pure (.bits (a + b))
        | _, _ => throw "concatenation of non-bits"
      else pure l
  | .cast to _ => pure to
  | .slice _ hi lo => pure (.bits (hi - lo + 1))
  | .isValid _ => pure .boolean
  | .mux _ thenBranch _ => typeOf index scope action thenBranch
  | .lookahead ty => pure ty

end P4bloIR
