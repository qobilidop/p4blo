import P4bloIR.Value
import P4bloIR.Packet
import P4bloIR.Tables
import P4bloIR.Externs

/-!
# The run-time environment

Mirrors `impl/python/p4blo/interp/env.py`. Names are block-scoped (proto header,
"Names"), so each activation of a block has its own `Frame` of parameters
and locals, created at their zero values (docs/ir-semantics.md, "Uninitialized
variables"). While an action runs, its parameters are layered on top of the
block's store, because an action body sees both. The packet, the emitter,
the installed entries, the extern state and the parser's revisit
bookkeeping belong to the run (`Run`) and are shared by every activation
in it.

The interpreter monad `M` threads the run as state and stops on a `Fault`.
The state survives a fault, as Python's mutable environment does: a parser
that raises reports the headers as they were at that moment, and a
sub-parser's arguments are copied back before its error propagates.
-/

namespace P4bloIR

open Std (HashMap)

/-- Why a run stopped. -/
inductive Fault
  /-- `InterpError`: the interpreter met a program the validator would have
  rejected. A validated program never produces one. -/
  | interp (msg : String)
  /-- `ParseError`: the parser rejects with this error name; `"NoError"`
  for an explicit transition to `reject` (docs/ir-semantics.md, "Parsers"). -/
  | parse (error : String)
  deriving Repr, BEq, Inhabited

/-- Variable storage for one block activation. -/
structure Frame where
  scope : BlockScope
  vars : HashMap String Value
  /-- The action running in this activation, with its parameters. -/
  action : Option String := none
  actionVars : Option (HashMap String Value) := none

instance : Inhabited BlockScope := ⟨{ block := default }⟩
instance : Inhabited Index := ⟨{ program := default }⟩
instance : Inhabited Frame := ⟨{ scope := default, vars := {} }⟩

namespace Frame

/-- A fresh activation of `block`, every parameter and local at zero. -/
def forBlock (index : Index) (block : Block) : Except String Frame := do
  let some scope := index.scopes[block.name]? | throw s!"unknown block '{block.name}'"
  let mut vars : HashMap String Value := {}
  for (name, decl) in scope.vars.toList do
    vars := vars.insert name (← Value.zero decl.type index)
  pure { scope, vars }

/-- The block of this activation. -/
def block (f : Frame) : Block := f.scope.block

/-- The value of `name`: an action parameter first, then the block's. -/
def read? (f : Frame) (name : String) : Option Value :=
  (f.actionVars.bind (·[name]?)) <|> f.vars[name]?

/-- `f` with `name` set: in the action layer when it holds the name, else
in the block's store; `none` when neither declares it. -/
def write? (f : Frame) (name : String) (value : Value) : Option Frame :=
  match f.actionVars with
  | some avs => if avs.contains name then some { f with actionVars := some (avs.insert name value) }
    else if f.vars.contains name then some { f with vars := f.vars.insert name value } else none
  | none => if f.vars.contains name then some { f with vars := f.vars.insert name value } else none

end Frame

/-- The state of one run: what every activation shares, plus the current
activation. -/
structure Run where
  index : Index
  /-- Installed entries; only a control has them. -/
  entries : Option Installed := none
  externs : Externs := {}
  frame : Frame
  /-- The packet; only a parser has one. -/
  packet : Option Packet := none
  /-- The emit buffer; only a deparser has one. -/
  emitter : Option Emitter := none
  /-- `(block name, state name)` to the cursor when that state was last
  entered, for the revisit rule. -/
  visits : HashMap (String × String) Nat := {}
  deriving Inhabited

/-- The interpreter monad: the run as state, stopping on a fault, with the
state kept at the stop. -/
abbrev M := ExceptT Fault (StateM Run)

/-- Run `x` on `run`; the outcome and the run after it, faulted or not. -/
def M.run (x : M α) (run : Run) : Except Fault α × Run :=
  Id.run (StateT.run (ExceptT.run x) run)

/-- Stop with an `InterpError`. -/
def throwInterp (msg : String) : M α := throw (.interp msg)

/-- Stop the parser with a raised error. -/
def throwParse (error : String) : M α := throw (.parse error)

/-- Lift a checked computation whose failure is an `InterpError`. -/
def liftExcept : Except String α → M α
  | .ok a => pure a
  | .error e => throwInterp e

/-- The current activation. -/
def getFrame : M Frame := do pure (← get).frame

def setFrame (f : Frame) : M Unit := modify fun r => { r with frame := f }

/-- The name index of the program. -/
def getIndex : M Index := do pure (← get).index

/-- The current activation's block. -/
def currentBlock : M Block := do pure (← getFrame).block

/-- Read a variable of the current activation. -/
def readVar (name : String) : M Value := do
  let f ← getFrame
  match f.read? name with
  | some v => pure v
  | none => throwInterp s!"unknown variable '{name}' in block '{f.block.name}'"

/-- Write a variable of the current activation. -/
def writeVar (name : String) (value : Value) : M Unit := do
  let f ← getFrame
  match f.write? name value with
  | some f' => setFrame f'
  | none => throwInterp s!"unknown variable '{name}' in block '{f.block.name}'"

def requirePacket : M Packet := do
  match (← get).packet with
  | some p => pure p
  | none => throwInterp s!"block '{(← currentBlock).name}' has no packet"

def setPacket (p : Packet) : M Unit := modify fun r => { r with packet := some p }

def requireEmitter : M Emitter := do
  match (← get).emitter with
  | some e => pure e
  | none => throwInterp s!"block '{(← currentBlock).name}' has no packet to emit to"

def setEmitter (e : Emitter) : M Unit := modify fun r => { r with emitter := some e }

def requireEntries : M Installed := do
  match (← get).entries with
  | some e => pure e
  | none => throwInterp s!"block '{(← currentBlock).name}' has no table entries"

end P4bloIR
