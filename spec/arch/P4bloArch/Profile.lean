import P4bloArch.Assembly

/-! Executable restrictions of the supported v1model profile. This checker
tracks aliases of flattened standard metadata through calls. It does not add
premises to, or claim a proof about, the architecture-free core checker. -/

namespace P4bloArch.V1ModelProfile
open P4bloIR

abbrev Protected := List (List String × String)
abbrev Aliases := List (String × Protected)

def reserved : List String := ["ingress_port", "parser_error", "egress_spec", "egress_port"]
def unsupported : List String := ["drop", "flood", "packet_length", "instance_type",
  "mcast_grp", "egress_rid", "checksum_error", "priority", "enq_timestamp", "enq_qdepth",
  "deq_timedelta", "deq_qdepth", "ingress_global_timestamp", "egress_global_timestamp"]

private def pathPrefix : List String → List String → Bool
  | [], _ => true
  | _, [] => false
  | a :: as, b :: bs => a == b && pathPrefix as bs

private def exprPath : Expr → Option (String × List String)
  | .var name => some (name, [])
  | .member base field => do
    let (name, path) ← exprPath base
    pure (name, path ++ [field])
  | _ => none

private def lvaluePath : LValue → Option (String × List String)
  | .var name => some (name, [])
  | .member base field => do
    let (name, path) ← lvaluePath base
    pure (name, path ++ [field])
  | .index base _ | .next base => lvaluePath base

private def affected (aliases : Aliases) (path : Option (String × List String)) : List String :=
  match path with
  | none => []
  | some (name, path) =>
    ((aliases.lookup name).getD []).filterMap fun (guarded, field) =>
      if pathPrefix path guarded || pathPrefix guarded path then some field else none

private def projected (aliases : Aliases) (path : Option (String × List String)) : Protected :=
  match path with
  | none => []
  | some (name, path) =>
    ((aliases.lookup name).getD []).filterMap fun (guarded, field) =>
      if pathPrefix path guarded then some (guarded.drop path.length, field)
      else if pathPrefix guarded path then some ([], field) else none

private def canRead (stage field : String) : Bool :=
  match stage with
  | "parser" => field == "ingress_port"
  | "verify_checksum" => false
  | "ingress" => field != "egress_port"
  | "egress" | "compute_checksum" => true
  | _ => false

private def checkReads (stage : String) (fields : List String) : Except String Unit := do
  for field in fields do
    if !canRead stage field then throw s!"v1model stage '{stage}' cannot read '{field}'"

private def checkWrite (stage : String) (aliases : Aliases) (target : LValue) : Except String Unit := do
  let fields := affected aliases (lvaluePath target)
  for field in fields do
    if field != "egress_spec" || !(stage == "ingress" || stage == "egress") then
      throw s!"v1model stage '{stage}' cannot write '{field}'"

private partial def checkExpr (stage : String) (aliases : Aliases) (expr : Expr) : Except String Unit := do
  if let some path := exprPath expr then
    checkReads stage (affected aliases (some path))
  else
    match expr with
    | .member base _ | .lastIndex base | .unary _ base | .cast _ base | .slice base _ _ | .isValid base =>
      checkExpr stage aliases base
    | .index base index | .binary _ base index =>
      checkExpr stage aliases base
      checkExpr stage aliases index
    | .mux condition yes no =>
      checkExpr stage aliases condition
      checkExpr stage aliases yes
      checkExpr stage aliases no
    | _ => pure ()

private partial def checkIndices (stage : String) (aliases : Aliases) : LValue → Except String Unit
  | .var _ => pure ()
  | .member base _ | .next base => checkIndices stage aliases base
  | .index base index => do
    checkIndices stage aliases base
    checkExpr stage aliases index

private def callAliases (stage : String) (aliases : Aliases) (params : List Param)
    (args : List Arg) : Except String Aliases := do
  let mut result := []
  for (param, arg) in params.zip args do
    let guarded ← match arg with
      | .expr expr => do
        match exprPath expr with
        | some path => pure (projected aliases (some path))
        | none => checkExpr stage aliases expr *> pure []
      | .lvalue target => do
        checkIndices stage aliases target
        let guarded := projected aliases (lvaluePath target)
        if param.direction == .out then checkWrite stage aliases target
        pure guarded
    result := result ++ [(param.name, guarded)]
  pure result

mutual
private partial def checkBlock (index : Index) (stageBlocks : List String) (stage : String) (aliases : Aliases)
    (seen : List String) (block : Block) : Except String Unit := do
  let key := "block:" ++ block.name
  if seen.contains key then throw "v1model profile rejects recursive calls"
  let seen := key :: seen
  checkStmts index stageBlocks stage aliases seen block block.body
  for action in block.actions do
    checkAction index stageBlocks stage aliases seen block action.name []
  for table in block.tables do
    for key in table.keys do checkExpr stage aliases key.expr
  for state in block.states do
    checkStmts index stageBlocks stage aliases seen block state.body
    if let .select keys _ := state.transition then
      for key in keys do checkExpr stage aliases key

private partial def checkAction (index : Index) (stageBlocks : List String) (stage : String) (aliases : Aliases)
    (seen : List String) (block : Block) (name : String) (args : List Arg) : Except String Unit := do
  let some action := block.actions.find? (·.name == name) | pure ()
  let key := "action:" ++ block.name ++ "." ++ name
  if seen.contains key then throw "v1model profile rejects recursive calls"
  let extra ← callAliases stage aliases action.params args
  checkStmts index stageBlocks stage (extra ++ aliases) (key :: seen) block action.body

private partial def checkStmts (index : Index) (stageBlocks : List String) (stage : String) (aliases : Aliases)
    (seen : List String) (block : Block) (stmts : List Stmt) : Except String Unit := do
  for stmt in stmts do
    match stmt with
    | .assign target value =>
      checkWrite stage aliases target
      checkIndices stage aliases target
      checkExpr stage aliases value
    | .conditional condition yes no =>
      checkExpr stage aliases condition
      checkStmts index stageBlocks stage aliases seen block yes
      checkStmts index stageBlocks stage aliases seen block no
    | .apply name hit =>
      if let some target := hit then
        checkWrite stage aliases target
        checkIndices stage aliases target
      if let some table := block.tables.find? (·.name == name) then
        for key in table.keys do checkExpr stage aliases key.expr
        for action in table.actions do checkAction index stageBlocks stage aliases seen block action []
    | .callAction name args => checkAction index stageBlocks stage aliases seen block name args
    | .callBlock name args =>
      if stageBlocks.contains name then
        throw s!"v1model stage block '{name}' cannot be called as a sub-block"
      if let some child := index.blocks[name]? then
        let childAliases ← callAliases stage aliases child.params args
        checkBlock index stageBlocks stage childAliases seen child
    | .callExtern inst method args result =>
      if let some target := result then
        checkWrite stage aliases target
        checkIndices stage aliases target
      let params : List Param := (do
        let instDecl ← index.externInstances[inst]?
        let externType ← index.externTypes[instDecl.externType]?
        let methodDecl ← externType.methods.find? (fun (m : Method) => m.name == method)
        pure methodDecl.params).getD []
      for (param, arg) in params.zip args do
        match arg with
        | .expr value => checkExpr stage aliases value
        | .lvalue target =>
          checkIndices stage aliases target
          if param.direction != .«in» then checkWrite stage aliases target
          if param.direction != .out then checkReads stage (affected aliases (lvaluePath target))
    | .setValid target | .setInvalid target | .push target _ | .pop target _ | .extract target =>
      checkWrite stage aliases target
      checkIndices stage aliases target
    | .advance value | .emit value => checkExpr stage aliases value
    | .verify condition _ => checkExpr stage aliases condition
end

/-- Check each exported stage independently, including action and block callees. -/
def check (index : Index) (bindings : BlockBindings) : Except String Unit := do
  let some fields := index.fields? bindings.metadata | throw "unknown metadata type"
  for field in fields do
    if unsupported.contains field.name then
      throw s!"unsupported v1model metadata field '{field.name}'"
  let guarded := fields.filterMap fun field =>
    if reserved.contains field.name then some ([field.name], field.name) else none
  let roles := ["parser", "verify_checksum", "ingress", "egress", "compute_checksum", "deparser"]
  let stageBlocks := bindings.exports.map (·.block)
  if stageBlocks.eraseDups.length != stageBlocks.length then
    throw "v1model stages must use distinct blocks"
  for binding in bindings.exports do
    if !roles.contains binding.role then throw s!"unsupported v1model role '{binding.role}'"
    if let some block := index.blocks[binding.block]? then
      let aliases := block.params.filterMap fun param =>
        if param.type == .struct bindings.metadata then some (param.name, guarded) else none
      checkBlock index stageBlocks binding.role aliases [] block

end P4bloArch.V1ModelProfile
