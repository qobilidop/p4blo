import P4bloIR.Eval

/-!
# Statements, calls, and the parser's state machine

Mirrors `impl/python/p4blo/interp/stmt.py`. `executeOne` has one case per
`Stmt` kind. Statements are shared by the three block kinds where the
schema allows (proto, "Where each statement may appear"), so they live
together; the parser's states are here too because a sub-parser call is a
statement that walks states.

Calls follow docs/ir-semantics.md, "Controls": `in` arguments are copied in,
`out` parameters start at zero, `out` and `inout` arguments are copied back
in parameter order. Every entry of a block or action binds by name in a
fresh activation (see `Env`).

`Execution.step` is a total transition function over an explicit continuation
stack. `Execution.drive` is the actual runner, defined with `partial_fixpoint`
so its unfolding equation is available to proofs. `Execution.Finishes.sound`
connects any finite trace to that runner. No validated-program termination
theorem is claimed: the validator's acyclic calls and the parser's revisit
rule still need a joint termination proof. No implementation fuel is used.
-/

namespace P4bloIR

-- ---------------------------------------------------------------------------
-- Statements of every block kind
-- ---------------------------------------------------------------------------

/-- `setValid` and `setInvalid` touch only the validity bit
(docs/ir-semantics.md, "Headers"). -/
def setValidity (lv : LValue) (valid : Bool) : M Unit := do
  let (t, _, fields) ← expectHeader (← readLValue lv)
  writeLValue lv (.header t valid fields)

/-- Shift elements up by `n`, discarding the last `n`; the first `n`
become invalid zero headers; `nextIndex` grows by `n` up to the size
(docs/ir-semantics.md, "Header stacks"). `n` above the size acts as the size. -/
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
consumes nothing (docs/ir-semantics.md, "Parsers"). Into `hs.next`, the
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
elements from 0 to S - 1 (docs/ir-semantics.md, "Deparsers"). -/
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
none raises `NoMatch` (docs/ir-semantics.md, "select"). -/
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
(docs/ir-semantics.md, "Parser loop bound"). -/
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

/-- Call a method on an extern instance, then copy the `out` and `inout`
results and the return value back (docs/ir-semantics.md, "Externs"). -/
def callExtern (inst method : String) (args : List Arg) (result : Option LValue) :
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

namespace Execution

/-- Defunctionalized control flow. Return items carry the frame layers and
copyback arguments that used to live in recursive monadic continuations. -/
inductive Work
  | statements (body : List Stmt)
  | statement (stmt : Stmt)
  | table (name : String) (hit : Option LValue)
  | tableAction (call : ActionCall)
  | action (name : String) (args : List Arg)
  | block (name : String) (args : List Arg)
  | runBlock (block : Block)
  | states (block : Block)
  | state (scope : BlockScope) (state : State)
  | transition (scope : BlockScope) (transition : Transition)
  | writeHit (target : Option LValue) (hit : Bool)
  | actionReturn (outer : Frame) (copy : Option (List Param × List Arg))
  | blockReturn (caller : Frame) (params : List Param) (args : List Arg)

/-- A block return must run even during fault unwinding. Action return and
table hit writes are success-only, as in the original `withAction`. -/
def Work.handlesFault : Work → Bool
  | .blockReturn .. => true
  | _ => false

/-- Execute one work item without recursively executing another. The returned
items are prepended to the remaining continuation stack in source order. -/
def dispatch : Work → M (List Work)
  | .statements [] => pure []
  | .statements (s :: ss) => pure [.statement s, .statements ss]
  | .statement stmt => do
    match stmt with
    | .assign target value => writeLValue target (← evaluate value)
    | .conditional condition thenBranch otherwise =>
      return [.statements (if ← expectBool (← evaluate condition) then thenBranch else otherwise)]
    | .apply table hit => return [.table table hit]
    | .callAction action args => return [.action action args]
    | .callBlock block args => return [.block block args]
    | .callExtern inst method args result => callExtern inst method args result
    | .setValid header => setValidity header true
    | .setInvalid header => setValidity header false
    | .push stack count =>
      writeLValue stack (← liftExcept (pushFront (← readLValue stack) count (← getIndex)))
    | .pop stack count =>
      writeLValue stack (← liftExcept (popFront (← readLValue stack) count (← getIndex)))
    | .extract target => extract target
    | .advance bits => advance bits
    | .verify condition error => verify condition error
    | .emit value => emitValue (← evaluate value)
    pure []
  | .table name hit => do
    let frame ← getFrame
    let some table := frame.scope.tables[name]? | throwInterp s!"unknown table '{name}'"
    let keys ← table.keys.mapM fun k => do expectBits (← evaluate k.expr)
    let m ← liftExcept ((← requireEntries).lookup (frame.block.name, table.name) keys)
    pure ((m.action.toList.map Work.tableAction) ++ [.writeHit hit m.hit])
  | .writeHit target hit => do
    if let some lv := target then writeLValue lv (.bool hit)
    pure []
  | .tableAction call => do
    let outer ← getFrame
    let some action := outer.scope.actions[call.action]?
      | throwInterp s!"unknown action '{call.action}'"
    if call.args.length != action.params.length then
      throwInterp s!"action '{action.name}' takes {action.params.length} arguments"
    let params := (action.params.zip call.args).foldl
      (fun m (p, a) => m.insert p.name (literalValue a)) ({} : Std.HashMap String Value)
    setFrame { outer with action := some action.name, actionVars := some params }
    pure [.statements action.body, .actionReturn outer none]
  | .action name args => do
    let outer ← getFrame
    let some action := outer.scope.actions[name]? | throwInterp s!"unknown action '{name}'"
    if args.length != action.params.length then
      throwInterp s!"action '{action.name}' takes {action.params.length} arguments"
    let mut params : Std.HashMap String Value := {}
    for (param, arg) in action.params.zip args do
      params := params.insert param.name (← argumentValue param arg)
    setFrame { outer with action := some action.name, actionVars := some params }
    pure [.statements action.body, .actionReturn outer (some (action.params, args))]
  | .actionReturn outer copy => do
    let inner ← getFrame
    setFrame { inner with action := outer.action, actionVars := outer.actionVars }
    if let some (params, args) := copy then copyBack params args inner
    pure []
  | .block name args => do
    let index ← getIndex
    let some block := index.blocks[name]? | throwInterp s!"unknown block '{name}'"
    if args.length != block.params.length then
      throwInterp s!"block '{block.name}' takes {block.params.length} arguments"
    let mut callee ← liftExcept (Frame.forBlock index block)
    for (param, arg) in block.params.zip args do
      callee := { callee with vars := callee.vars.insert param.name (← argumentValue param arg) }
    let caller ← getFrame
    setFrame callee
    pure [.runBlock block, .blockReturn caller block.params args]
  | .blockReturn caller params args => do
    let calleeAfter ← getFrame
    setFrame caller
    copyBack params args calleeAfter
    pure []
  | .runBlock block =>
    pure [if block.kind == .parser then .states block else .statements block.body]
  | .states block => do
    let scope := (← getFrame).scope
    let some start := scope.states[block.startState]?
      | throwInterp s!"unknown state '{block.startState}'"
    pure [.state scope start]
  | .state scope state => do
    enterState state
    pure [.statements state.body, .transition scope state.transition]
  | .transition scope trans => do
    match ← P4bloIR.transition trans with
    | .state next =>
      let some s := scope.states[next]? | throwInterp s!"unknown state '{next}'"
      pure [.state scope s]
    | .accept => pure []
    | .reject => throwParse "NoError"

/-- Complete machine configuration, including a fault being unwound. -/
structure Machine where
  work : List Work
  run : Run
  fault : Option Fault := none

abbrev Outcome := Except Fault Unit × Run

/-- One total step. A failing copyback replaces the pending fault; a successful
block return preserves it. All other items are skipped while unwinding. -/
def step (machine : Machine) : Outcome ⊕ Machine :=
  match machine.work with
  | [] => .inl (match machine.fault with
      | none => (.ok (), machine.run)
      | some fault => (.error fault, machine.run))
  | task :: rest =>
    if machine.fault.isSome && !task.handlesFault then
      .inr { machine with work := rest }
    else
      match (dispatch task).run machine.run with
      | (.ok next, run) => .inr { work := next ++ rest, run, fault := machine.fault }
      | (.error fault, run) => .inr { work := rest, run, fault := some fault }

/-- The executable interpreter loop, with an unfolding theorem generated by
Lean's fixed-point construction. For a nonterminating input the flat-order
fixed point makes no asserted language outcome; finite traces are covered by
`Finishes.sound`. There is deliberately no fuel counter or timeout here. -/
def drive (machine : Machine) : Outcome :=
  match step machine with
  | .inl result => result
  | .inr next => drive next
partial_fixpoint

/-- A finite execution trace of the actual transition function. -/
inductive Finishes : Machine → Outcome → Prop
  | done (h : step machine = .inl result) : Finishes machine result
  | next (h : step machine = .inr next) : Finishes next result → Finishes machine result

/-- Every finite trace determines exactly the outcome of the actual runner. -/
theorem Finishes.sound (h : Finishes machine result) : drive machine = result := by
  induction h with
  | done h => rw [drive.eq_def, h]
  | next h _ ih => rw [drive.eq_def, h]; exact ih

/-- Embed the machine runner in the existing state-and-fault API. -/
def run (work : List Work) : M Unit := fun initial =>
  drive { work, run := initial }

theorem run_eq (work : List Work) (initial : Run) :
    (run work).run initial = drive { work, run := initial } := rfl

end Execution

/-- Execute statements in order through the proof-visible machine. -/
def execute (stmts : List Stmt) : M Unit := Execution.run [.statements stmts]

/-- Execute one statement; assignment evaluates its RHS before its target. -/
def executeOne (stmt : Stmt) : M Unit := Execution.run [.statement stmt]

/-- Evaluate table keys once, run the selected action, then write `hit`. -/
def applyTable (name : String) (hit : Option LValue) : M Unit :=
  Execution.run [.table name hit]

/-- Run a table action with its directionless data parameters. -/
def runActionCall (call : ActionCall) : M Unit := Execution.run [.tableAction call]

/-- A direct action call, with success-only argument copyback. -/
def callAction (name : String) (args : List Arg) : M Unit := Execution.run [.action name args]

/-- A block call restores its caller and copies arguments back even on faults. -/
def callBlock (name : String) (args : List Arg) : M Unit := Execution.run [.block name args]

/-- A parser walks its states; a control or deparser runs its body. -/
def runBlock (block : Block) : M Unit := Execution.run [.runBlock block]

/-- Walk parser states to acceptance or a parser fault, enforcing revisits. -/
def runStates (block : Block) : M Unit := Execution.run [.states block]

end P4bloIR
