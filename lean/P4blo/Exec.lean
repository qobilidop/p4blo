import P4blo.Eval

/-!
# Statements, calls, and the parser's state machine

Mirrors `python/p4blo/interp/stmt.py`. `executeOne` has one case per
`Stmt` kind. Statements are shared by the three block kinds where the
schema allows (proto, "Where each statement may appear"), so they live
together; the parser's states are here too because a sub-parser call is a
statement that walks states.

Calls follow docs/semantics.md, "Controls": `in` arguments are copied in,
`out` parameters start at zero, `out` and `inout` arguments are copied back
in parameter order. Every entry of a block or action binds by name in a
fresh activation (see `Env`).

The executor is `partial`: a block call runs the callee's body, which is
not a subterm of the caller's, and a parser walks its states in a loop. The
validator's acyclic call graph bounds the calls, and the no-consumption
revisit rule bounds the state walk (a state is entered at most once per
cursor position), so every run terminates; Lean is not shown the proof.
-/

namespace P4blo

-- ---------------------------------------------------------------------------
-- Statements of every block kind
-- ---------------------------------------------------------------------------

/-- `setValid` and `setInvalid` touch only the validity bit
(docs/semantics.md, "Headers"). -/
def setValidity (lv : LValue) (valid : Bool) : M Unit := do
  let (t, _, fields) ← expectHeader (← readLValue lv)
  writeLValue lv (.header t valid fields)

/-- Shift elements up by `n`, discarding the last `n`; the first `n`
become invalid zero headers; `nextIndex` grows by `n` up to the size
(docs/semantics.md, "Header stacks"). `n` above the size acts as the size. -/
def pushFront (stack : Value) (n : Nat) (index : Index) : Except String Value := do
  let (headerType, elements, nextIndex) ← stack.expectStack
  let size := elements.length
  let n := min n size
  let fresh := List.replicate n (← Value.zeroHeader headerType index)
  pure (.stack headerType (fresh ++ elements.take (size - n)) (min (nextIndex + n) size))

/-- Shift elements down by `n`; the last `n` become invalid zero headers;
`nextIndex` shrinks by `n` down to zero. -/
def popFront (stack : Value) (n : Nat) (index : Index) : Except String Value := do
  let (headerType, elements, nextIndex) ← stack.expectStack
  let size := elements.length
  let n := min n size
  let fresh := List.replicate n (← Value.zeroHeader headerType index)
  pure (.stack headerType (elements.drop n ++ fresh) (nextIndex - n))

-- ---------------------------------------------------------------------------
-- Parser statements
-- ---------------------------------------------------------------------------

/-- The next `n` bits of the packet, consumed; `PacketTooShort` when fewer
remain, and then the cursor stays. -/
def packetRead (n : Nat) : M Nat := do
  let packet ← requirePacket
  let some (raw, packet') := packet.read? n | throwParse "PacketTooShort"
  setPacket packet'
  pure raw

/-- Fill the target header from the packet and make it valid.

The target is resolved first, so a full stack raises `StackOutOfBounds`
before the packet is looked at; a short packet raises `PacketTooShort` and
consumes nothing (docs/semantics.md, "Parsers"). Into `hs.next`, the
element at `nextIndex` is filled and `nextIndex` incremented. -/
def extract (target : LValue) : M Unit := do
  let _ ← requirePacket
  let index ← getIndex
  match target with
  | .next stack =>
    let (headerType, elements, nextIndex) ← expectStack (← readLValue stack)
    if nextIndex ≥ elements.length then throwParse "StackOutOfBounds"
    let raw ← packetRead (← liftExcept (widthOf (.header headerType) index))
    let header ← liftExcept (headerFromBits headerType raw index)
    writeLValue stack (.stack headerType (elements.set nextIndex header) (nextIndex + 1))
  | _ =>
    let (typeName, _, _) ← expectHeader (← readLValue target)
    let raw ← packetRead (← liftExcept (widthOf (.header typeName) index))
    writeLValue target (← liftExcept (headerFromBits typeName raw index))

/-- Skip `n` bits; past the end, `PacketTooShort` and the cursor stays. -/
def advance (bits : Expr) : M Unit := do
  let n ← expectBits (← evaluate bits)
  let packet ← requirePacket
  let some packet' := packet.advance? n.value | throwParse "PacketTooShort"
  setPacket packet'

/-- Raise `error` unless `condition` holds. -/
def verify (condition : Expr) (error : String) : M Unit := do
  if !(← expectBool (← evaluate condition)) then throwParse error

-- ---------------------------------------------------------------------------
-- Deparser statements
-- ---------------------------------------------------------------------------

mutual
/-- Emit a header if valid, a struct's fields in order, or a stack's
elements from 0 to S - 1 (docs/semantics.md, "Deparsers"). -/
def emitValue : Value → M Unit
  | .header _ valid fields => do
    if valid then
      let (width, value) ← liftExcept (headerToBits fields)
      setEmitter ((← requireEmitter).write width value)
  | .struct _ fields => emitList fields
  | .stack _ elements _ => emitList elements
  | v => throwInterp s!"cannot emit a {v.kindName}"

def emitList : List Value → M Unit
  | [] => pure ()
  | v :: vs => do emitValue v; emitList vs
end

-- ---------------------------------------------------------------------------
-- Select
-- ---------------------------------------------------------------------------

/-- Whether a key set matches a key: an exact value by `Value.equal`, a
mask or a range on bits, or don't-care. -/
def keySetMatches (ks : KeySet) (key : Value) : M Bool :=
  match ks with
  | .exact lit => pure (Value.equal key (literalValue lit))
  | .masked value mask => do
    let k ← expectBits key
    let v ← expectBits (literalValue value)
    let m ← expectBits (literalValue mask)
    pure (k.value &&& m.value == v.value &&& m.value)
  | .range lo hi => do
    let k ← expectBits key
    let l ← expectBits (literalValue lo)
    let h ← expectBits (literalValue hi)
    pure (l.value ≤ k.value && k.value ≤ h.value)
  | .dontCare => pure true

/-- Evaluate the keys once; the first case whose every set matches wins;
none raises `NoMatch` (docs/semantics.md, "select"). -/
def select (keys : List Expr) (cases : List SelectCase) : M Target := do
  let values ← keys.mapM evaluate
  for c in cases do
    if c.sets.length != values.length then throwInterp "select case arity"
    if ← (c.sets.zip values).allM fun (ks, k) => keySetMatches ks k then
      return c.target
  throwParse "NoMatch"

def transition : Transition → M Target
  | .direct target => pure target
  | .select keys cases => select keys cases

/-- The no-consumption revisit rule: entering a state again with the
cursor where it was at the last entry raises `ParserTimeout`
(docs/semantics.md, "Parser loop bound"). -/
def enterState (state : State) : M Unit := do
  let key := ((← currentBlock).name, state.name)
  let cursor := (← requirePacket).cursor
  if (← get).visits[key]? == some cursor then throwParse "ParserTimeout"
  modify fun r => { r with visits := r.visits.insert key cursor }

-- ---------------------------------------------------------------------------
-- Calls and the executor
-- ---------------------------------------------------------------------------

/-- What the callee's parameter starts as: the argument for `in`, `inout`
and action data, the zero value for `out`. -/
def argumentValue (param : Param) (arg : Arg) : M Value := do
  if param.direction == .out then liftExcept (Value.zero param.type (← getIndex))
  else match arg with
    | .expr e => evaluate e
    | .lvalue lv => readLValue lv

/-- Write `out` and `inout` parameters back to their arguments, in
parameter order, from the callee's activation `values`. -/
def copyBack (params : List Param) (args : List Arg) (values : Frame) : M Unit := do
  for (param, arg) in params.zip args do
    if param.direction == .out || param.direction == .inout then
      let .lvalue lv := arg | throwInterp "lvalue has no kind"
      let some v := values.read? param.name | throwInterp s!"unknown variable '{param.name}'"
      writeLValue lv v

/-- Run the action `name` with its parameters bound to `params`, layered
on the current activation, and return that activation afterwards. -/
def withAction (name : String) (params : Std.HashMap String Value) (body : List Stmt)
    (execute : List Stmt → M Unit) : M Frame := do
  let outer ← getFrame
  setFrame { outer with action := some name, actionVars := some params }
  execute body
  let inner ← getFrame
  setFrame { inner with action := outer.action, actionVars := outer.actionVars }
  pure inner

mutual

/-- Execute statements in order. -/
partial def execute (stmts : List Stmt) : M Unit := stmts.forM executeOne

/-- Execute one statement. The right-hand side of an assignment is
evaluated before the target is resolved. -/
partial def executeOne : Stmt → M Unit
  | .assign target value => do writeLValue target (← evaluate value)
  | .conditional condition thenBranch otherwise => do
    if ← expectBool (← evaluate condition) then execute thenBranch else execute otherwise
  | .apply table hit => applyTable table hit
  | .callAction action args => callAction action args
  | .callBlock block args => callBlock block args
  | .callExtern inst method args result => callExtern inst method args result
  | .setValid header => setValidity header true
  | .setInvalid header => setValidity header false
  | .push stack count => do
    writeLValue stack (← liftExcept (pushFront (← readLValue stack) count (← getIndex)))
  | .pop stack count => do
    writeLValue stack (← liftExcept (popFront (← readLValue stack) count (← getIndex)))
  | .extract target => extract target
  | .advance bits => advance bits
  | .verify condition error => verify condition error
  | .emit value => do emitValue (← evaluate value)

/-- Evaluate the keys once, look them up, run the chosen action, then
record `hit` (docs/semantics.md, "Tables"). -/
partial def applyTable (name : String) (hit : Option LValue) : M Unit := do
  let frame ← getFrame
  let some table := frame.scope.tables[name]? | throwInterp s!"unknown table '{name}'"
  let keys ← table.keys.mapM fun k => do expectBits (← evaluate k.expr)
  let m ← liftExcept ((← requireEntries).lookup (frame.block.name, table.name) keys)
  if let some call := m.action then runActionCall call
  if let some lv := hit then writeLValue lv (.bool m.hit)

/-- Run an action chosen by a table, with its action data bound to the
directionless parameters by value. -/
partial def runActionCall (call : ActionCall) : M Unit := do
  let frame ← getFrame
  let some action := frame.scope.actions[call.action]? | throwInterp s!"unknown action '{call.action}'"
  if call.args.length != action.params.length then
    throwInterp s!"action '{action.name}' takes {action.params.length} arguments"
  let params := (action.params.zip call.args).foldl
    (fun m (p, a) => m.insert p.name (literalValue a)) ({} : Std.HashMap String Value)
  let _ ← withAction action.name params action.body execute

/-- A direct action call from a control body, with directional arguments
passed like a block call's. -/
partial def callAction (name : String) (args : List Arg) : M Unit := do
  let frame ← getFrame
  let some action := frame.scope.actions[name]? | throwInterp s!"unknown action '{name}'"
  if args.length != action.params.length then
    throwInterp s!"action '{action.name}' takes {action.params.length} arguments"
  let mut params : Std.HashMap String Value := {}
  for (param, arg) in action.params.zip args do
    params := params.insert param.name (← argumentValue param arg)
  let inner ← withAction action.name params action.body execute
  copyBack action.params args inner

/-- Run a sub-parser or sub-control. If a sub-parser raises, its arguments
are copied back first, so the outcome shows what it had already written
(docs/semantics.md, "Parsers"). -/
partial def callBlock (name : String) (args : List Arg) : M Unit := do
  let index ← getIndex
  let some block := index.blocks[name]? | throwInterp s!"unknown block '{name}'"
  if args.length != block.params.length then
    throwInterp s!"block '{block.name}' takes {block.params.length} arguments"
  let mut callee ← liftExcept (Frame.forBlock index block)
  for (param, arg) in block.params.zip args do
    callee := { callee with vars := callee.vars.insert param.name (← argumentValue param arg) }
  let caller ← getFrame
  setFrame callee
  let fault ← tryCatch (do runBlock block; pure none) (fun e => pure (some e))
  let calleeAfter ← getFrame
  setFrame caller
  copyBack block.params args calleeAfter
  if let some e := fault then throw e

/-- A parser walks its states; a control or deparser runs its body. -/
partial def runBlock (block : Block) : M Unit :=
  if block.kind == .parser then runStates block else execute block.body

/-- Call a method on an extern instance, then copy the `out` and `inout`
results and the return value back (docs/semantics.md, "Externs"). -/
partial def callExtern (inst method : String) (args : List Arg) (result : Option LValue) :
    M Unit := do
  let index ← getIndex
  let some instance_ := index.externInstances[inst]? | throwInterp s!"unknown extern instance '{inst}'"
  let some externType := index.externTypes[instance_.externType]?
    | throwInterp s!"unknown extern type '{instance_.externType}'"
  let some decl := externType.methods.find? (·.name == method)
    | throwInterp s!"extern '{externType.name}' has no method '{method}'"
  if args.length != decl.params.length then
    throwInterp s!"method '{method}' takes {decl.params.length} arguments"
  let values ← (decl.params.zip args).mapM fun (p, a) => argumentValue p a
  let (externs, r) ← liftExcept ((← get).externs.call inst method values)
  modify fun run => { run with externs }
  let written := (decl.params.zip args).filterMap fun (p, a) =>
    if p.direction == .out || p.direction == .inout then some a else none
  if r.outs.length != written.length then
    throwInterp s!"method '{method}' produced {r.outs.length} out values"
  for (arg, v) in written.zip r.outs do
    let .lvalue lv := arg | throwInterp "lvalue has no kind"
    writeLValue lv v
  if let some lv := result then
    let some v := r.returns | throwInterp s!"method '{method}' returned nothing"
    writeLValue lv v

/-- Walk the states from `startState` until `accept` returns or `reject`
raises `NoError`. -/
partial def runStates (block : Block) : M Unit := do
  let scope := (← getFrame).scope
  let some start := scope.states[block.startState]? | throwInterp s!"unknown state '{block.startState}'"
  let mut state := start
  repeat
    enterState state
    execute state.body
    match ← transition state.transition with
    | .state next =>
      let some s := scope.states[next]? | throwInterp s!"unknown state '{next}'"
      state := s
    | .accept => return
    | .reject => throwParse "NoError"

end

end P4blo
