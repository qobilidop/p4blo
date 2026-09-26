import P4bloIR.Json
import P4bloIR.Validity.Check

namespace P4bloArch
open P4bloIR
open Lean (Json FromJson ToJson)

/-- An architecture's role-to-block binding. -/
structure Export where
  role : String
  block : String
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Architecture-owned roots and calling conventions. -/
structure BlockBindings where
  headers : String
  metadata : String
  exports : List Export
  deriving Repr, BEq, Inhabited

/-- Flat compatibility transport; declarations project to a core library. -/
structure BlockAssembly extends BlockLibrary, BlockBindings
  deriving Repr, BEq, Inhabited

instance : Coe BlockAssembly BlockLibrary := ⟨BlockAssembly.toBlockLibrary⟩

open Decode in
def Export.decode (path : String) (j : Json) : Dec Export := do
  pure { role := ← strField path j "role", block := ← strField path j "block" }

open Decode in
def BlockAssembly.decode (path : String) (j : Json) : Dec BlockAssembly := do
  let library ← BlockLibrary.decode path j
  pure { toBlockLibrary := library,
         headers := ← strField path j "headers", metadata := ← strField path j "metadata",
         exports := ← listField path j "exports" Export.decode }

def BlockAssembly.fromJsonString (text : String) : Except String BlockAssembly := do
  BlockAssembly.decode "" (← Json.parse text)

open Encode in
def Export.toJson (e : Export) : Json := obj [ofStr "role" e.role, ofStr "block" e.block]

open Encode in
def BlockAssembly.toJson (p : BlockAssembly) : Json :=
  match p.toBlockLibrary.toJson with
  | .obj fields => obj ([fields.toList] ++
      [ofStr "headers" p.headers, ofStr "metadata" p.metadata,
       ofList "exports" (p.exports.map Export.toJson)])
  | _ => Json.mkObj []

instance : FromJson Export := ⟨Export.decode ""⟩
instance : ToJson Export := ⟨Export.toJson⟩
instance : FromJson BlockAssembly := ⟨BlockAssembly.decode ""⟩
instance : ToJson BlockAssembly := ⟨BlockAssembly.toJson⟩

def BlockBindings.exported? (p : BlockBindings) (idx : Index) (role : String) : Option Block := do
  let e ← p.exports.find? (·.role == role)
  idx.blocks[e.block]?

namespace Bindings
open P4bloIR.Validity

def exportSignature : BlockKind → List (Direction × Bool)
  | .parser => [(.out, true), (.inout, false)]
  | .control => [(.inout, true), (.inout, false)]
  | .deparser => [(.in, true)]

/-- An exported block's params match its kind's signature. -/
def signatureOk (p : BlockBindings) (b : Block) : Bool :=
  let want := exportSignature b.kind
  b.params.length == want.length &&
    (b.params.zip want).all fun (q, d, h) =>
      q.direction == d && decide (q.type = .struct (if h then p.headers else p.metadata))

/-- The exports: roles distinct, each block resolved, with the signature
of its kind (validator, `check_exports`). -/
def checkExports (p : BlockBindings) (idx : Index) (seen : List String) : Nat → List Export → Chk Unit
  | _, [] => pure ()
  | i, e :: es => do
    let path := at_ "exports" i
    ensure (!seen.contains e.role) .exportDuplicate path s!"role '{e.role}' exported twice"
    let b ← resolve idx idx.blocks[e.block]? e.block "block" (dot path "block")
    ensure (signatureOk p b) .exportSignature path s!"'{b.name}' lacks the signature of its kind"
    checkExports p idx (seen ++ [e.role]) (i + 1) es

def check (p : BlockBindings) (idx : Index) : Chk Unit := do
  let _ ← resolve idx idx.structTypes[p.headers]? p.headers "struct type" "headers"
  let _ ← resolve idx idx.structTypes[p.metadata]? p.metadata "struct type" "metadata"
  checkExports p idx [] 0 p.exports

end Bindings

def BlockAssembly.check (p : BlockAssembly) : Except Validity.Diagnostic Index := do
  let idx ← Validity.check p.toBlockLibrary
  Bindings.check p.toBlockBindings idx
  pure idx

end P4bloArch
