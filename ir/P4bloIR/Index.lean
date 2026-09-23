import Std.Data.HashMap
import Std.Data.HashSet
import P4bloIR.IR

/-!
# Name index

`Index` resolves names to declarations, as `python/p4blo/ir.py`'s `Index`
does, and `Index.build` enforces the same naming rules: every name is
non-empty and unique in its scope, and a block-level name may not reuse a
program-level one. Program-level declarations (header, struct, enum and
extern types, extern instances and blocks) share one namespace; a block's
params, locals, actions, tables and states share another; an action's
params may not reuse a name of the enclosing block. The error list has its
own namespace.

Errors are the same sentences ir.py raises, so that the two sides can be
compared on the same inputs.
-/

namespace P4bloIR

open Std (HashMap HashSet)

/-- A variable a block body sees: one of its params or locals. -/
inductive VarDecl
  | param (p : Param)
  | var (v : Var)
  deriving Repr, BEq, Inhabited

/-- The name of the declaration. -/
def VarDecl.name : VarDecl → String
  | .param p => p.name
  | .var v => v.name

/-- The type of the declaration. -/
def VarDecl.type : VarDecl → Ty
  | .param p => p.type
  | .var v => v.type

/-- The declarations of one block, each by name. Mirrors ir.py's
`BlockScope`. `vars` holds the block's params and locals; action params are
under `actionParams[action]`, and an action body sees those plus `vars`. -/
structure BlockScope where
  block : Block
  vars : HashMap String VarDecl := {}
  actions : HashMap String Action := {}
  actionParams : HashMap String (HashMap String Param) := {}
  tables : HashMap String Table := {}
  states : HashMap String State := {}

/-- The variable `name` sees from the block body, or from `action` when
given: an action param shadows nothing, since the names may not collide,
but is looked up first as ir.py does. -/
def BlockScope.var? (scope : BlockScope) (name : String) (action : Option String := none) :
    Option VarDecl :=
  let fromAction := do
    let a ← action
    let params ← scope.actionParams[a]?
    let p ← params[name]?
    pure (VarDecl.param p)
  fromAction <|> scope.vars[name]?

/-- Every declaration of a program by name. Mirrors ir.py's `Index`.
`programNames` holds every program-level name, since they share one
namespace; `errors` maps each error name to its position in
`Program.errors`. -/
structure Index where
  program : Program
  headerTypes : HashMap String HeaderType := {}
  structTypes : HashMap String StructType := {}
  enumTypes : HashMap String EnumType := {}
  externTypes : HashMap String ExternType := {}
  externInstances : HashMap String ExternInstance := {}
  blocks : HashMap String Block := {}
  scopes : HashMap String BlockScope := {}
  programNames : HashSet String := {}
  errors : HashMap String Nat := {}

namespace Index

/-- Add `decl` under `name` to `table`, checking the name against `taken`,
the names already used in the scope `where_`. The error sentences are
ir.py's. -/
private def add (table : HashMap String α) (name : String) (decl : α) (taken : HashSet String)
    (where_ : String) : Except String (HashMap String α × HashSet String) := do
  if name.isEmpty then throw s!"empty name in {where_}"
  if taken.contains name then throw s!"'{name}' declared twice in {where_}"
  pure (table.insert name decl, taken.insert name)

/-- Add a list of declarations in order, threading the taken set. -/
private def addAll (table : HashMap String α) (decls : List α) (name : α → String)
    (taken : HashSet String) (where_ : String) :
    Except String (HashMap String α × HashSet String) :=
  decls.foldlM (fun (table, taken) d => add table (name d) d taken where_) (table, taken)

/-- The scope of one block, given the program-level names. -/
private def buildScope (b : Block) (top : HashSet String) : Except String BlockScope := do
  let where_ := s!"block '{b.name}'"
  let (vars, taken) ← addAll {} (b.params.map VarDecl.param) VarDecl.name top where_
  let (vars, taken) ← addAll vars (b.locals.map VarDecl.var) VarDecl.name taken where_
  let mut actions : HashMap String Action := {}
  let mut actionParams : HashMap String (HashMap String Param) := {}
  let mut taken := taken
  for a in b.actions do
    (actions, taken) ← add actions a.name a taken where_
    let (params, _) ← addAll {} a.params Param.name taken s!"action '{a.name}' of {where_}"
    actionParams := actionParams.insert a.name params
  let (tables, taken') ← addAll {} b.tables Table.name taken where_
  let (states, _) ← addAll {} b.states State.name taken' where_
  pure { block := b, vars, actions, actionParams, tables, states }

/-- Index `program`, rejecting a repeated or empty name within a scope and a
block-level name that reuses a program-level one. -/
def build (program : Program) : Except String Index := do
  let where_ := "program"
  let (headerTypes, top) ← addAll {} program.headerTypes HeaderType.name {} where_
  let (structTypes, top) ← addAll {} program.structTypes StructType.name top where_
  let (enumTypes, top) ← addAll {} program.enumTypes EnumType.name top where_
  let (externTypes, top) ← addAll {} program.externTypes ExternType.name top where_
  let (externInstances, top) ← addAll {} program.externInstances ExternInstance.name top where_
  let (blocks, top) ← addAll {} program.blocks Block.name top where_
  let mut errors : HashMap String Nat := {}
  for (name, i) in program.errors.zipIdx do
    if name.isEmpty || errors.contains name then throw s!"error '{name}' at {i}"
    errors := errors.insert name i
  let mut scopes : HashMap String BlockScope := {}
  for b in program.blocks do
    scopes := scopes.insert b.name (← buildScope b top)
  pure { program, headerTypes, structTypes, enumTypes, externTypes, externInstances, blocks,
         scopes, programNames := top, errors }

/-- The block exported under `role`, if any. -/
def exported? (index : Index) (role : String) : Option Block := do
  let e ← index.program.exports.find? (·.role == role)
  index.blocks[e.block]?

/-- The fields of a header or struct type. -/
def fields? (index : Index) (typeName : String) : Option (List Field) :=
  (index.headerTypes[typeName]?.map (·.fields)) <|> (index.structTypes[typeName]?.map (·.fields))

/-- The position of `fieldName` among the fields of `typeName`. -/
def fieldIndex? (index : Index) (typeName fieldName : String) : Option Nat := do
  (← index.fields? typeName).findIdx? (·.name == fieldName)

end Index

end P4bloIR
