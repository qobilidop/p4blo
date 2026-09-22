import Std.Data.HashMap
import P4blo.Value
import P4blo.Widths

/-!
# Installed table entries and the match algorithm

Mirrors `python/p4blo/interp/tables.py`; see docs/semantics.md, "Tables":
exact, longest prefix, and largest priority among ternary matches; const
entries first; the default action on a miss. Tables are block-scoped, so
they are addressed by `(block, table)` names. Installation errors are
strings with the Python sentences.
-/

namespace P4blo

open Std (HashMap)

/-- The result of a lookup: the action to run and whether an entry hit. -/
structure Match where
  action : Option ActionCall
  hit : Bool
  deriving Repr, BEq

/-- The kind name of a match kind, as the error sentences use it. -/
def MatchKind.kindName : MatchKind → String
  | .exact => "exact"
  | .lpm => "lpm"
  | .ternary => "ternary"

/-- `(block name, table name)`. -/
abbrev TableRef := String × String

/-- Everything installed in every table of a program: the program's const
entries and defaults, then the host's. Entries keep their installation
order. -/
structure Installed where
  index : Index
  entries : HashMap TableRef (Array Entry) := {}
  defaults : HashMap TableRef (Option ActionCall) := {}

namespace Installed

/-- The table `ref` names. -/
def table? (i : Installed) (ref : TableRef) : Except String Table :=
  match i.index.scopes[ref.1]?.bind (·.tables[ref.2]?) with
  | some t => pure t
  | none => throw s!"no table '{ref.2}' in block '{ref.1}'"

/-- The width of each key of the table, in order. -/
def keyWidths (i : Installed) (ref : TableRef) : Except String (List Nat) := do
  let some scope := i.index.scopes[ref.1]? | throw s!"no block '{ref.1}'"
  (← i.table? ref).keys.mapM fun key => do
    match ← typeOf i.index scope none key.expr with
    | .bits n => pure n
    | _ => throw s!"key '{key.name}' of table '{ref.2}' is not bits"

-- ---------------------------------------------------------------------------
-- Entry values
-- ---------------------------------------------------------------------------

/-- A value that fits in `width` bits. -/
def fitsWidth (value width : Nat) (what : String) : Except String Unit :=
  if value < 2 ^ width then pure () else throw s!"{what} '{value}' does not fit in {width} bits"

/-- The value's kind is the key's match kind, it fits the key's width, and
it is canonical: no set bit outside an LPM prefix or a ternary mask. -/
def checkKeyValue (key : Key) (kv : KeyValue) (width : Nat) : Except String Unit := do
  let wants := key.matchKind.kindName
  match key.matchKind, kv with
  | .exact, .exact value => fitsWidth value width "exact value"
  | .lpm, .lpm value prefixLen => do
    fitsWidth value width "lpm value"
    if prefixLen > width then throw s!"prefix length {prefixLen} exceeds width {width}"
    if value % 2 ^ (width - prefixLen) != 0 then throw s!"lpm value '{value}' has bits outside its prefix"
  | .ternary, .ternary value mask => do
    fitsWidth value width "ternary value"
    fitsWidth mask width "ternary mask"
    if value &&& (mask ^^^ (2 ^ width - 1)) != 0 then
      throw s!"ternary value '{value}' has bits outside its mask"
  | _, _ => throw s!"key '{key.name}' wants a {wants} value"

/-- Whether a literal has the declared type of an action parameter. -/
def literalFits : Literal → Ty → Bool
  | .bits width value, .bits n => width == n && value < 2 ^ n
  | .boolean _, .boolean => true
  | .enumMember t _, .enumType n => t == n
  | .error _, .error => true
  | _, _ => false

/-- Exact equality, prefix equality, or equality under the mask. -/
def keyValueMatches (kv : KeyValue) (key : Bits) : Bool :=
  match kv with
  | .exact value => key.value == value
  | .lpm value prefixLen =>
    let shift := key.width - prefixLen
    key.value >>> shift == value >>> shift
  | .ternary value mask => key.value &&& mask == value &&& mask

/-- The total prefix length of an entry's lpm keys. -/
def prefixLength (entry : Entry) : Nat :=
  entry.keys.foldl (fun n kv => match kv with | .lpm _ len => n + len | _ => n) 0

/-- Whether `entry` wins over `best` when both match: larger priority in a
ternary table, longer prefix otherwise. Exact tables never tie. -/
def beats (entry best : Entry) (ternary : Bool) : Bool :=
  if ternary then entry.priority > best.priority
  else prefixLength entry > prefixLength best

/-- Two entries of an exact or LPM table with identical keys: equal exact
values, and equal prefixes of equal length (values are canonical, so the
prefix is the value). -/
def sameKeys (a b : Entry) : Bool :=
  (a.keys.zip b.keys).all fun
    | (.exact x, .exact y) => x == y
    | (.lpm xv xl, .lpm yv yl) => xl == yl && xv == yv
    | _ => true

/-- Whether some key value matches both entries: every key overlaps. -/
def overlaps (a b : Entry) (widths : List Nat) : Bool :=
  ((a.keys.zip b.keys).zip widths).all fun
    | ((.exact x, .exact y), _) => x == y
    | ((.lpm xv xl, .lpm yv yl), width) =>
      let shift := width - min xl yl
      xv >>> shift == yv >>> shift
    | ((.ternary xv xm, .ternary yv ym), _) =>
      let mask := xm &&& ym
      xv &&& mask == yv &&& mask
    | _ => true

-- ---------------------------------------------------------------------------
-- Installation
-- ---------------------------------------------------------------------------

/-- The call names one of the table's actions and carries one literal of
the declared type per directionless parameter. -/
def checkAction (i : Installed) (ref : TableRef) (decl : Table) (call : ActionCall) :
    Except String Unit := do
  if !decl.actions.contains call.action then
    throw s!"table '{decl.name}' has no action '{call.action}'"
  let some action := i.index.scopes[ref.1]?.bind (·.actions[call.action]?)
    | throw s!"no action '{call.action}' in block '{ref.1}'"
  if action.params.any (·.direction != .none) then
    throw s!"action '{action.name}' has directional parameters"
  if call.args.length != action.params.length then
    throw s!"action '{action.name}' takes {action.params.length} arguments"
  for (param, arg) in action.params.zip call.args do
    if !literalFits arg param.type then
      throw s!"argument for {action.name}.{param.name} has the wrong type"

/-- Add an entry after checking it fits the table and ties nothing. Ternary
tables order by priority, and two entries of equal priority whose key sets
overlap are rejected. Other tables require priority 0 and reject an entry
whose keys repeat an installed one's. -/
def install (i : Installed) (ref : TableRef) (entry : Entry) : Except String Installed := do
  let decl ← i.table? ref
  let widths ← i.keyWidths ref
  if entry.keys.length != decl.keys.length then throw s!"table '{decl.name}' has {decl.keys.length} keys"
  for ((key, kv), width) in (decl.keys.zip entry.keys).zip widths do
    checkKeyValue key kv width
  i.checkAction ref decl entry.action
  let ternary := decl.keys.any (·.matchKind == .ternary)
  if !ternary && entry.priority != 0 then
    throw s!"table '{decl.name}' has no ternary key; priority must be 0"
  let installed := i.entries.getD ref #[]
  for other in installed do
    if ternary then
      if other.priority == entry.priority && overlaps entry other widths then
        throw s!"table '{decl.name}': overlapping entries at priority {entry.priority}"
    else if sameKeys entry other then throw s!"table '{decl.name}': duplicate entry"
  pure { i with entries := i.entries.insert ref (installed.push entry) }

/-- Replace a non-const default action; `none` restores the program's own,
since a host cannot remove a default. -/
def setDefault (i : Installed) (ref : TableRef) (action : Option ActionCall) :
    Except String Installed := do
  let decl ← i.table? ref
  if decl.constDefaultAction then throw s!"table '{decl.name}' has a const default action"
  let action ← match action with
    | none => pure decl.defaultAction
    | some call => do i.checkAction ref decl call; pure (some call)
  pure { i with defaults := i.defaults.insert ref action }

/-- The program's const entries and defaults, then the host's. -/
def build (index : Index) (host : Option Entries := none) : Except String Installed := do
  let mut i : Installed := { index }
  for block in index.program.blocks do
    for table in block.tables do
      let ref := (block.name, table.name)
      i := { i with entries := i.entries.insert ref #[],
                    defaults := i.defaults.insert ref table.defaultAction }
      for entry in table.constEntries do
        i ← i.install ref entry
  if let some host := host then
    for te in host.tables do
      let ref := (te.block, te.table)
      for entry in te.entries do
        i ← i.install ref entry
      if te.defaultAction.isSome then
        i ← i.setDefault ref te.defaultAction
  pure i

-- ---------------------------------------------------------------------------
-- Lookup
-- ---------------------------------------------------------------------------

/-- The entry that matches best, or the default action on a miss. -/
def lookup (i : Installed) (ref : TableRef) (keys : List Bits) : Except String Match := do
  let decl ← i.table? ref
  if keys.length != decl.keys.length then throw s!"table '{decl.name}' has {decl.keys.length} keys"
  let ternary := decl.keys.any (·.matchKind == .ternary)
  let mut best : Option Entry := none
  for entry in i.entries.getD ref #[] do
    if (entry.keys.zip keys).all fun (kv, k) => keyValueMatches kv k then
      match best with
      | none => best := some entry
      | some b => if beats entry b ternary then best := some entry
  match best with
  | none => pure { action := (i.defaults.getD ref none), hit := false }
  | some entry => pure { action := some entry.action, hit := true }

end Installed

end P4blo
