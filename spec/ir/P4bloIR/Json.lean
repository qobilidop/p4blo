import Lean.Data.Json
import P4bloIR.IR
import P4bloIR.JsonBounds
import Init.Data.Array.MapIdx
import Init.Data.Array.Attach

/-!
# JSON decoding and encoding of the IR

The wire format is the protobuf JSON mapping as `p4blo.ir.dump_json`
produces it: keys are the proto's snake_case names, a oneof appears as
whichever field is set, enums are their full names (`"BLOCK_KIND_PARSER"`),
`uint32` are JSON numbers, `bool` are booleans, repeated fields are arrays,
unset `optional` fields are absent, and empty messages are `{}`. Scalars at
their default (`""`, `0`, `false`) and empty repeated fields are omitted,
so a decoder supplies the default when a key is missing; a message-typed
field that is missing decodes as `{}`, which for a oneof message is the
"no kind set" error.
Decimal-string values are not numeric protobuf fields: their missing/null
default is the empty string, which is invalid, not a numeric zero. A zero
bits value or LPM/ternary component must have an explicit decimal spelling.

Decoding is total. Each decoder takes the path to the value it decodes so
that every error names where it happened (`blocks[2].states[0].transition:
no kind set`). Unknown keys are ignored: field numbers 100 and above are
reserved for annotations, and a newer producer may add fields.

Encoding targets the restricted profile emitted by `dump_json`: defaults
are omitted, decimal strings are re-rendered (including a present "0").
Cross-language conformance is tested, not universally proved. Lean `Nat`
fields may exceed protobuf uint32; representability must constrain any
roundtrip theorem. Unknown-key handling above is current adapter behavior,
not a safe semantic-version compatibility policy; that boundary remains open.

`Expr.decode`, `LValue.decode` and `Stmt.decode` use well-founded recursion on JSON size.
An actual child is smaller; a synthesized empty-message default is no
larger than its object payload and hence smaller than the enclosing oneof.
Statement branch arrays retain genuine membership bounds during traversal;
erasure laws recover the original ordered array traversal and its errors.
-/

namespace P4bloIR

open Lean (Json JsonNumber FromJson ToJson)

-- ---------------------------------------------------------------------------
-- Decoding helpers
-- ---------------------------------------------------------------------------

namespace Decode

/-- A decoding result: the value or a message naming the path. -/
abbrev Dec (α : Type) := Except String α

/-- Fail at `path` with `msg`. -/
def fail (path msg : String) : Dec α := .error s!"{path}: {msg}"

/-- The path of key `key` under `path`. -/
def sub (path key : String) : String := if path.isEmpty then key else s!"{path}.{key}"

/-- The path of element `i` of the array at `path`. -/
def at_ (path : String) (i : Nat) : String := s!"{path}[{i}]"

/-- Field `key` of the object `j`, `none` when absent or `null`. Fails when
`j` is not an object. -/
def get? (path : String) (j : Json) (key : String) : Dec (Option Json) :=
  match j with
  | .obj kvs =>
    match kvs.get? key with
    | some Json.null | none => pure none
    | some v => pure (some v)
  | _ => fail path "expected an object"

/-- Parse a decimal natural number; anything but a non-empty run of ASCII
digits is rejected. -/
def decimal (path : String) (s : String) : Dec Nat :=
  if s.isEmpty then fail path "expected a decimal number, got an empty string"
  else if s.all Char.isDigit then
    pure (s.foldl (fun n c => n * 10 + (c.toNat - '0'.toNat)) 0)
  else fail path s!"expected a decimal number, got {repr s}"

/-- A JSON string. -/
def str (path : String) (j : Json) : Dec String :=
  match j with
  | .str s => pure s
  | _ => fail path "expected a string"

/-- A JSON boolean. -/
def bool (path : String) (j : Json) : Dec Bool :=
  match j with
  | .bool b => pure b
  | _ => fail path "expected a boolean"

/-- A `uint32`: a JSON number, or its decimal string as the protobuf JSON
mapping also allows. -/
def uint32 (path : String) (j : Json) : Dec Nat := do
  let n ← match j with
    | .num _ => match j.getNat? with
      | .ok n => pure n
      | .error _ => fail path "expected a non-negative integer"
    | .str s => decimal path s
    | _ => fail path "expected a number"
  if n < 2 ^ 32 then pure n else fail path s!"{n} does not fit in uint32"

/-- A decimal string carrying a bits value. -/
def decimalStr (path : String) (j : Json) : Dec Nat := do
  decimal path (← str path j)

/-- A string field of the object `j`, `""` when absent. -/
def strField (path : String) (j : Json) (key : String) : Dec String := do
  match ← get? path j key with
  | none => pure ""
  | some v => str (sub path key) v

/-- Protobuf defaults an absent/null string to `""`, not the decimal `"0"`.
Reject that invalid spelling before constructing the Nat-based abstract IR. -/
def decimalField (path : String) (j : Json) (key : String) : Dec Nat := do
  decimal (sub path key) (← strField path j key)

/-- A boolean field, `false` when absent. -/
def boolField (path : String) (j : Json) (key : String) : Dec Bool := do
  match ← get? path j key with
  | none => pure false
  | some v => bool (sub path key) v

/-- A `uint32` field, `0` when absent. -/
def uint32Field (path : String) (j : Json) (key : String) : Dec Nat := do
  match ← get? path j key with
  | none => pure 0
  | some v => uint32 (sub path key) v

/-- A message-typed field decoded by `dec`; absent decodes as `{}`. -/
def msgField (path : String) (j : Json) (key : String) (dec : String → Json → Dec α) :
    Dec α := do
  let v := (← get? path j key).getD (Json.mkObj [])
  dec (sub path key) v

/-- An `optional` message field: `none` when absent. -/
def optField (path : String) (j : Json) (key : String) (dec : String → Json → Dec α) :
    Dec (Option α) := do
  match ← get? path j key with
  | none => pure none
  | some v => some <$> dec (sub path key) v

/-- A JSON array decoded element by element with `dec`. -/
def array (path : String) (j : Json) (dec : String → Json → Dec α) : Dec (List α) :=
  match j with
  | .arr xs => (·.toList) <$> xs.mapIdxM fun i x => dec (at_ path i) x
  | _ => fail path "expected an array"

/-- A repeated field, `[]` when absent. -/
def listField (path : String) (j : Json) (key : String) (dec : String → Json → Dec α) :
    Dec (List α) := do
  match ← get? path j key with
  | none => pure []
  | some v => array (sub path key) v dec

/-- An enum field: its full proto name looked up in `table`. Absent, or the
`_UNSPECIFIED` value, or an unknown name, is an error. -/
def enumField (path : String) (j : Json) (key : String) (table : List (String × α)) :
    Dec α := do
  let p := sub path key
  match ← get? path j key with
  | none => fail p "unspecified"
  | some v =>
    let s ← str p v
    match table.lookup s with
    | some x => pure x
    | none =>
      if s.endsWith "_UNSPECIFIED" then fail p "unspecified"
      else fail p s!"unknown value {repr s}"

/-- A `oneof`: exactly one of `cases` must be present in `j`, and its decoder
runs on that field. -/
def oneof (path : String) (j : Json) (cases : List (String × (String → Json → Dec α))) :
    Dec α := do
  let mut present : List (String × (String → Json → Dec α) × Json) := []
  for (key, dec) in cases do
    if let some v ← get? path j key then
      present := present ++ [(key, dec, v)]
  match present with
  | [(key, dec, v)] => dec (sub path key) v
  | [] => fail path "no kind set"
  | ks => fail path s!"more than one kind set: {ks.map (·.1)}"

/-- An actual object field is smaller than the object that contains it. -/
theorem get_some_lt (path : String) (j : Json) (key : String) (v : Json)
    (h : get? path j key = .ok (some v)) : sizeOf v < sizeOf j := by
  cases j with
  | obj fields =>
    cases found : fields.get? key with
    | none => simp [get?, found, pure, Except.pure] at h
    | some value =>
      cases value <;> simp [get?, found, pure, Except.pure] at h
      all_goals subst v; exact JsonBounds.object_lookup_lt fields key _ found
  | _ => cases h

/-- The synthesized empty message is no larger than an object payload. -/
theorem message_target_le (path : String) (j : Json) (key : String)
    (value : Option Json) (h : get? path j key = .ok value) :
    sizeOf (value.getD (Json.mkObj [])) ≤ sizeOf j := by
  cases value with
  | some v => exact Nat.le_of_lt (get_some_lt path j key v h)
  | none =>
    cases j with
    | obj fields => exact JsonBounds.empty_object_le fields
    | _ => cases h

/-- Message access retains a strict bound relative to its enclosing oneof. -/
def msgFieldBounded (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String)
    (dec : String → (child : Json) → sizeOf child < sizeOf outer → Dec α) : Dec α :=
  match h : get? path j key with
  | .error error => .error error
  | .ok value => dec (sub path key) (value.getD (Json.mkObj []))
      (Nat.lt_of_le_of_lt (message_target_le path j key value h) smaller)

theorem msgFieldBounded_erasure (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String)
    (dec : String → Json → Dec α) :
    msgFieldBounded outer path j smaller key (fun p v _ => dec p v) =
      msgField path j key dec := by
  unfold msgFieldBounded msgField
  split <;> simp_all [bind, Except.bind] <;> rfl

private theorem mapIdxM_map (f : Nat → β → Except String γ) (g : α → β) (xs : List α) :
    (xs.map g).mapIdxM f = xs.mapIdxM (fun i x => f i (g x)) := by
  have go (ys : List α) (acc : Array γ) :
      List.mapIdxM.go f (ys.map g) acc =
        List.mapIdxM.go (fun i x => f i (g x)) ys acc := by
    induction ys generalizing acc with
    | nil => rfl
    | cons head tail ih => simp only [List.map_cons, List.mapIdxM.go, ih]
  exact go xs #[]

private theorem array_attach_erasure (xs : Array α) (f : Nat → α → Except String β) :
    Array.toList <$> xs.attach.mapIdxM (fun i x => f i x.val) =
      Array.toList <$> xs.mapIdxM f := by
  rw [Array.toList_mapIdxM, Array.toList_mapIdxM]
  rw [← mapIdxM_map f Subtype.val xs.attach.toList]
  rw [← Array.toList_map, Array.attach_map_subtype_val]

/-- Ordered traversal with a genuine child bound for each array member. -/
def arrayBounded (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer)
    (dec : String → (child : Json) → sizeOf child < sizeOf outer → Dec α) : Dec (List α) :=
  match j with
  | .arr xs => Array.toList <$> xs.attach.mapIdxM fun i x =>
      dec (at_ path i) x.val
        (Nat.lt_trans (JsonBounds.array_mem_lt xs x.val x.property) smaller)
  | _ => fail path "expected an array"

theorem arrayBounded_erasure (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (dec : String → Json → Dec α) :
    arrayBounded outer path j smaller (fun p v _ => dec p v) = array path j dec := by
  cases j <;> try rfl
  exact array_attach_erasure _ _

/-- Missing/null repeated fields stay empty; present arrays retain child bounds. -/
def listFieldBounded (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String)
    (dec : String → (child : Json) → sizeOf child < sizeOf outer → Dec α) : Dec (List α) :=
  match h : get? path j key with
  | .error error => .error error
  | .ok none => .ok []
  | .ok (some v) => arrayBounded outer (sub path key) v
      (Nat.lt_trans (get_some_lt path j key v h) smaller) dec

theorem listFieldBounded_erasure (outer : Json) (path : String) (j : Json)
    (smaller : sizeOf j < sizeOf outer) (key : String) (dec : String → Json → Dec α) :
    listFieldBounded outer path j smaller key (fun p v _ => dec p v) =
      listField path j key dec := by
  unfold listFieldBounded listField
  split <;> simp_all [arrayBounded_erasure, bind, Except.bind, pure, Except.pure]

abbrev Child (j : Json) := {v : Json // sizeOf v < sizeOf j}

def getChild? (path : String) (j : Json) (key : String) : Dec (Option (Child j)) :=
  match h : get? path j key with
  | .error error => .error error
  | .ok none => .ok none
  | .ok (some v) => .ok (some ⟨v, get_some_lt path j key v h⟩)

theorem getChild_erasure (path : String) (j : Json) (key : String) :
    Option.map Subtype.val <$> getChild? path j key = get? path j key := by
  unfold getChild?
  split <;> simp_all [Functor.map, Except.map]

/-- Scan in recognized-case order, retaining the lookup's descent witness. -/
def collectBounded (path : String) (j : Json) :
    List (String × β) → List (String × β × Child j) → Dec (List (String × β × Child j))
  | [], acc => .ok acc
  | (key, value) :: rest, acc =>
    match getChild? path j key with
    | .error error => .error error
    | .ok none => collectBounded path j rest acc
    | .ok (some v) => collectBounded path j rest
        (acc ++ [(key, value, v)])

private def eraseChild (entry : String × β × Child j) : String × β × Json :=
  (entry.1, entry.2.1, entry.2.2.val)

private theorem collectBounded_erasure (path : String) (j : Json)
    (cases : List (String × β)) (acc : List (String × β × Child j)) :
    List.map eraseChild <$> collectBounded path j cases acc =
      forIn cases (acc.map eraseChild) (fun (key, value) present => do
        if let some v ← get? path j key then
          pure (.yield (present ++ [(key, value, v)]))
        else pure (.yield present)) := by
  induction cases generalizing acc with
  | nil => rfl
  | cons head rest ih =>
    rcases head with ⟨key, value⟩
    have erase := getChild_erasure path j key
    cases h : getChild? path j key with
    | error error =>
      simp [h, Functor.map, Except.map] at erase
      simp [collectBounded, List.forIn_cons, h, ← erase, bind, Except.bind,
        Functor.map, Except.map, pure, Except.pure]
    | ok result =>
      cases result with
      | none =>
        simp [h, Functor.map, Except.map] at erase
        simpa [collectBounded, List.forIn_cons, h, ← erase, bind, Except.bind,
          pure, Except.pure] using ih acc
      | some v =>
        simp [h, Functor.map, Except.map] at erase
        simpa [collectBounded, List.forIn_cons, h, ← erase, bind, Except.bind,
          pure, Except.pure, List.map_append, eraseChild]
          using ih (acc ++ [(key, value, v)])

private def mapPayload (f : β → γ) (entry : String × β × Child j) :
    String × γ × Child j := (entry.1, f entry.2.1, entry.2.2)

private theorem collectBounded_map (path : String) (j : Json) (f : β → γ)
    (cases : List (String × β)) (acc : List (String × β × Child j)) :
    collectBounded path j (cases.map fun (k, v) => (k, f v)) (acc.map (mapPayload f)) =
      List.map (mapPayload f) <$> collectBounded path j cases acc := by
  induction cases generalizing acc with
  | nil => rfl
  | cons head rest ih =>
    rcases head with ⟨key, value⟩
    cases h : getChild? path j key with
    | error error => simp [List.map_cons, collectBounded, h, Functor.map, Except.map]
    | ok result =>
      cases result with
      | none => simpa [collectBounded, h] using ih acc
      | some v =>
        simpa [collectBounded, h, List.map_append, mapPayload]
          using ih (acc ++ [(key, value, v)])

def oneofBounded (path : String) (j : Json)
    (cases : List (String × (String → (v : Json) → sizeOf v < sizeOf j → Dec α))) :
    Dec α := do
  let present ← collectBounded path j cases []
  match present with
  | [(key, dec, v)] => dec (sub path key) v.val v.property
  | [] => fail path "no kind set"
  | ks => fail path s!"more than one kind set: {ks.map (·.1)}"

/-- Proof annotation does not alter successful results or any diagnostic. -/
theorem oneofBounded_erasure (path : String) (j : Json)
    (cases : List (String × (String → Json → Dec α))) :
    oneofBounded path j (cases.map fun (key, dec) => (key, fun p v _ => dec p v)) =
      oneof path j cases := by
  unfold oneofBounded oneof
  rw [show ([] : List (String × (String → (v : Json) → sizeOf v < sizeOf j → Dec α) × Child j)) =
    List.map (mapPayload (fun dec p v (_ : sizeOf v < sizeOf j) => dec p v))
      ([] : List (String × (String → Json → Dec α) × Child j)) from rfl]
  rw [collectBounded_map path j (fun dec p v (_ : sizeOf v < sizeOf j) => dec p v) cases []]
  dsimp only
  have collected := collectBounded_erasure path j cases []
  dsimp only at collected
  simp only [List.map_nil] at collected
  rw [← collected]
  cases h : collectBounded path j cases [] with
  | error error => rfl
  | ok present =>
    cases present with
    | nil => rfl
    | cons a rest =>
      cases rest with
      | nil => rfl
      | cons b rest =>
        simp [Functor.map, Except.map, bind, Except.bind,
          List.map_map, mapPayload, eraseChild, Function.comp_def]

/-- An empty message `{}`; anything else that is an object is accepted too,
since its keys may be reserved annotations. -/
def emptyMsg (path : String) (j : Json) : Dec Unit :=
  match j with
  | .obj _ => pure ()
  | _ => fail path "expected an object"

end Decode

-- ---------------------------------------------------------------------------
-- Enum tables
-- ---------------------------------------------------------------------------

/-- `Direction` values by proto name. -/
def Direction.names : List (String × Direction) :=
  [("DIRECTION_NONE", .none), ("DIRECTION_IN", .«in»), ("DIRECTION_OUT", .out),
   ("DIRECTION_INOUT", .inout)]

/-- `BlockKind` values by proto name. -/
def BlockKind.names : List (String × BlockKind) :=
  [("BLOCK_KIND_PARSER", .parser), ("BLOCK_KIND_CONTROL", .control),
   ("BLOCK_KIND_DEPARSER", .deparser)]

/-- `MatchKind` values by proto name. -/
def MatchKind.names : List (String × MatchKind) :=
  [("MATCH_KIND_EXACT", .exact), ("MATCH_KIND_LPM", .lpm), ("MATCH_KIND_TERNARY", .ternary)]

/-- `UnaryOp` values by proto name. -/
def UnaryOp.names : List (String × UnaryOp) :=
  [("UNARY_OP_NOT", .not), ("UNARY_OP_COMPLEMENT", .complement), ("UNARY_OP_NEGATE", .negate)]

/-- `BinaryOp` values by proto name. -/
def BinaryOp.names : List (String × BinaryOp) :=
  [("BINARY_OP_ADD", .add), ("BINARY_OP_SUB", .sub), ("BINARY_OP_MUL", .mul),
   ("BINARY_OP_ADD_SAT", .addSat), ("BINARY_OP_SUB_SAT", .subSat),
   ("BINARY_OP_BIT_AND", .bitAnd), ("BINARY_OP_BIT_OR", .bitOr), ("BINARY_OP_BIT_XOR", .bitXor),
   ("BINARY_OP_SHL", .shl), ("BINARY_OP_SHR", .shr), ("BINARY_OP_CONCAT", .concat),
   ("BINARY_OP_EQ", .eq), ("BINARY_OP_NE", .ne), ("BINARY_OP_LT", .lt), ("BINARY_OP_LE", .le),
   ("BINARY_OP_GT", .gt), ("BINARY_OP_GE", .ge), ("BINARY_OP_AND", .and), ("BINARY_OP_OR", .or)]

/-- The proto name of an enum value, from its table. -/
private def enumName [BEq α] (table : List (String × α)) (x : α) : String :=
  match table.find? (·.2 == x) with
  | some (s, _) => s
  | none => ""

def Direction.protoName (d : Direction) : String := enumName Direction.names d
def BlockKind.protoName (k : BlockKind) : String := enumName BlockKind.names k
def MatchKind.protoName (m : MatchKind) : String := enumName MatchKind.names m
def UnaryOp.protoName (op : UnaryOp) : String := enumName UnaryOp.names op
def BinaryOp.protoName (op : BinaryOp) : String := enumName BinaryOp.names op

-- ---------------------------------------------------------------------------
-- Decoders
-- ---------------------------------------------------------------------------

open Decode in
/-- Decode a `Type` message. -/
def Ty.decode (path : String) (j : Json) : Dec Ty :=
  oneof path j
    [("bits", fun p v => Ty.bits <$> uint32 p v),
     ("boolean", fun p v => emptyMsg p v *> pure Ty.boolean),
     ("header", fun p v => Ty.header <$> str p v),
     ("struct", fun p v => Ty.struct <$> str p v),
     ("enum_type", fun p v => Ty.enumType <$> str p v),
     ("error", fun p v => emptyMsg p v *> pure Ty.error),
     ("stack", fun p v => do
       pure (Ty.stack (← strField p v "header") (← uint32Field p v "size")))]

open Decode in
/-- Decode a `Literal` message. -/
def Literal.decode (path : String) (j : Json) : Dec Literal :=
  oneof path j
    [("bits", fun p v => do
       let width ← uint32Field p v "width"
       let value ← decimalField p v "value"
       pure (Literal.bits width value)),
     ("boolean", fun p v => Literal.boolean <$> bool p v),
     ("enum_member", fun p v => do
       pure (Literal.enumMember (← strField p v "enum_type") (← strField p v "member"))),
     ("error", fun p v => Literal.error <$> str p v)]

open Decode in
/-- Decode a `Field` message. -/
def Field.decode (path : String) (j : Json) : Dec Field := do
  pure { name := ← strField path j "name", type := ← msgField path j "type" Ty.decode }

open Decode in
/-- Decode a `HeaderType` message. -/
def HeaderType.decode (path : String) (j : Json) : Dec HeaderType := do
  pure { name := ← strField path j "name", fields := ← listField path j "fields" Field.decode }

open Decode in
/-- Decode a `StructType` message. -/
def StructType.decode (path : String) (j : Json) : Dec StructType := do
  pure { name := ← strField path j "name", fields := ← listField path j "fields" Field.decode }

open Decode in
/-- Decode an `EnumType` message. -/
def EnumType.decode (path : String) (j : Json) : Dec EnumType := do
  pure { name := ← strField path j "name", members := ← listField path j "members" str }

open Decode in
/-- Decode a `Var` message. -/
def Var.decode (path : String) (j : Json) : Dec Var := do
  pure { name := ← strField path j "name", type := ← msgField path j "type" Ty.decode }

open Decode in
/-- Decode a `Param` message. -/
def Param.decode (path : String) (j : Json) : Dec Param := do
  pure { name := ← strField path j "name", type := ← msgField path j "type" Ty.decode,
         direction := ← enumField path j "direction" Direction.names }

open Decode in
/-- Decode a `Method` message. -/
def Method.decode (path : String) (j : Json) : Dec Method := do
  pure { name := ← strField path j "name", params := ← listField path j "params" Param.decode,
         returns := ← optField path j "returns" Ty.decode }

open Decode in
/-- Decode an `ExternType` message. -/
def ExternType.decode (path : String) (j : Json) : Dec ExternType := do
  pure { name := ← strField path j "name",
         constructorParams := ← listField path j "constructor_params" Param.decode,
         methods := ← listField path j "methods" Method.decode }

open Decode in
/-- Decode an `ExternInstance` message. -/
def ExternInstance.decode (path : String) (j : Json) : Dec ExternInstance := do
  pure { name := ← strField path j "name", externType := ← strField path j "extern_type",
         args := ← listField path j "args" Literal.decode }

open Decode in
/-- Decode an `Expr` message with checked finite-JSON descent and no fuel cutoff. -/
def Expr.decode (path : String) (j : Json) : Dec Expr :=
  let recur := fun p v (_ : sizeOf v < sizeOf j) => Expr.decode p v
  oneofBounded path j
    [("literal", fun p v _ => Expr.literal <$> Literal.decode p v),
     ("var", fun p v _ => Expr.var <$> str p v),
     ("member", fun p v h => do
       pure (Expr.member (← msgFieldBounded j p v h "base" recur) (← strField p v "field"))),
     ("index", fun p v h => do
       pure (Expr.index (← msgFieldBounded j p v h "base" recur)
         (← msgFieldBounded j p v h "index" recur))),
     ("last_index", fun p v h => Expr.lastIndex <$> msgFieldBounded j p v h "stack" recur),
     ("unary", fun p v h => do
       pure (Expr.unary (← enumField p v "op" UnaryOp.names)
         (← msgFieldBounded j p v h "operand" recur))),
     ("binary", fun p v h => do
       pure (Expr.binary (← enumField p v "op" BinaryOp.names)
         (← msgFieldBounded j p v h "left" recur) (← msgFieldBounded j p v h "right" recur))),
     ("cast", fun p v h => do
       pure (Expr.cast (← msgField p v "to" Ty.decode)
         (← msgFieldBounded j p v h "operand" recur))),
     ("slice", fun p v h => do
       pure (Expr.slice (← msgFieldBounded j p v h "operand" recur)
         (← uint32Field p v "hi") (← uint32Field p v "lo"))),
     ("is_valid", fun p v h => Expr.isValid <$> msgFieldBounded j p v h "header" recur),
     ("mux", fun p v h => do
       pure (Expr.mux (← msgFieldBounded j p v h "condition" recur)
         (← msgFieldBounded j p v h "then" recur) (← msgFieldBounded j p v h "otherwise" recur))),
     ("lookahead", fun p v _ => Expr.lookahead <$> msgField p v "type" Ty.decode)]
termination_by sizeOf j

open Decode in
/-- The actual total decoder unfolds to its original, proof-erased body.
This equation includes malformed inputs and preserves diagnostic order. -/
theorem Expr.decode_unfold (path : String) (j : Json) :
    Expr.decode path j =
      oneof path j
        [("literal", fun p v => Expr.literal <$> Literal.decode p v),
         ("var", fun p v => Expr.var <$> str p v),
         ("member", fun p v => do
           pure (Expr.member (← msgField p v "base" Expr.decode) (← strField p v "field"))),
         ("index", fun p v => do
           pure (Expr.index (← msgField p v "base" Expr.decode) (← msgField p v "index" Expr.decode))),
         ("last_index", fun p v => Expr.lastIndex <$> msgField p v "stack" Expr.decode),
         ("unary", fun p v => do
           pure (Expr.unary (← enumField p v "op" UnaryOp.names) (← msgField p v "operand" Expr.decode))),
         ("binary", fun p v => do
           pure (Expr.binary (← enumField p v "op" BinaryOp.names)
             (← msgField p v "left" Expr.decode) (← msgField p v "right" Expr.decode))),
         ("cast", fun p v => do
           pure (Expr.cast (← msgField p v "to" Ty.decode) (← msgField p v "operand" Expr.decode))),
         ("slice", fun p v => do
           pure (Expr.slice (← msgField p v "operand" Expr.decode)
             (← uint32Field p v "hi") (← uint32Field p v "lo"))),
         ("is_valid", fun p v => Expr.isValid <$> msgField p v "header" Expr.decode),
         ("mux", fun p v => do
           pure (Expr.mux (← msgField p v "condition" Expr.decode)
             (← msgField p v "then" Expr.decode) (← msgField p v "otherwise" Expr.decode))),
         ("lookahead", fun p v => Expr.lookahead <$> msgField p v "type" Ty.decode)] := by
  rw [Expr.decode.eq_def]
  simp only [msgFieldBounded_erasure]
  rw [← oneofBounded_erasure]
  rfl

open Decode in
/-- Decode an `LValue` with checked finite-JSON descent and no fuel cutoff. -/
def LValue.decode (path : String) (j : Json) : Dec LValue :=
  let recur := fun p v (_ : sizeOf v < sizeOf j) => LValue.decode p v
  oneofBounded path j
    [("var", fun p v _ => LValue.var <$> str p v),
     ("member", fun p v h => do
       pure (LValue.member (← msgFieldBounded j p v h "base" recur) (← strField p v "field"))),
     ("index", fun p v h => do
       pure (LValue.index (← msgFieldBounded j p v h "base" recur)
         (← msgField p v "index" Expr.decode))),
     ("next", fun p v h => LValue.next <$> msgFieldBounded j p v h "stack" recur)]
termination_by sizeOf j

open Decode in
/-- The actual total decoder unfolds to the original proof-erased body,
including defaults, recognized-case ordering and first-error behavior. -/
theorem LValue.decode_unfold (path : String) (j : Json) :
    LValue.decode path j =
      oneof path j
        [("var", fun p v => LValue.var <$> str p v),
         ("member", fun p v => do
           pure (LValue.member (← msgField p v "base" LValue.decode) (← strField p v "field"))),
         ("index", fun p v => do
           pure (LValue.index (← msgField p v "base" LValue.decode)
             (← msgField p v "index" Expr.decode))),
         ("next", fun p v => LValue.next <$> msgField p v "stack" LValue.decode)] := by
  rw [LValue.decode.eq_def]
  simp only [msgFieldBounded_erasure]
  rw [← oneofBounded_erasure]
  rfl

open Decode in
/-- Decode an `Arg` message. -/
def Arg.decode (path : String) (j : Json) : Dec Arg :=
  oneof path j
    [("expr", fun p v => Arg.expr <$> Expr.decode p v),
     ("lvalue", fun p v => Arg.lvalue <$> LValue.decode p v)]

open Decode in
/-- Decode a `Stmt` message by strict descent through conditional arrays. -/
def Stmt.decode (path : String) (j : Json) : Dec Stmt :=
  let recur := fun p child (_ : sizeOf child < sizeOf j) => Stmt.decode p child
  oneofBounded path j
    [("assign", fun p v _ => do
       pure (Stmt.assign (← msgField p v "target" LValue.decode)
         (← msgField p v "value" Expr.decode))),
     ("conditional", fun p v h => do
       pure (Stmt.conditional (← msgField p v "condition" Expr.decode)
         (← listFieldBounded j p v h "then" recur)
         (← listFieldBounded j p v h "otherwise" recur))),
     ("apply", fun p v _ => do
       pure (Stmt.apply (← strField p v "table") (← optField p v "hit" LValue.decode))),
     ("call_action", fun p v _ => do
       pure (Stmt.callAction (← strField p v "action") (← listField p v "args" Arg.decode))),
     ("call_block", fun p v _ => do
       pure (Stmt.callBlock (← strField p v "block") (← listField p v "args" Arg.decode))),
     ("call_extern", fun p v _ => do
       pure (Stmt.callExtern (← strField p v "instance") (← strField p v "method")
         (← listField p v "args" Arg.decode) (← optField p v "result" LValue.decode))),
     ("set_valid", fun p v _ => Stmt.setValid <$> msgField p v "header" LValue.decode),
     ("set_invalid", fun p v _ => Stmt.setInvalid <$> msgField p v "header" LValue.decode),
     ("push", fun p v _ => do
       pure (Stmt.push (← msgField p v "stack" LValue.decode) (← uint32Field p v "count"))),
     ("pop", fun p v _ => do
       pure (Stmt.pop (← msgField p v "stack" LValue.decode) (← uint32Field p v "count"))),
     ("extract", fun p v _ => Stmt.extract <$> msgField p v "target" LValue.decode),
     ("advance", fun p v _ => Stmt.advance <$> msgField p v "bits" Expr.decode),
     ("verify", fun p v _ => do
       pure (Stmt.verify (← msgField p v "condition" Expr.decode) (← strField p v "error"))),
     ("emit", fun p v _ => Stmt.emit <$> msgField p v "value" Expr.decode)]
termination_by sizeOf j

open Decode in
/-- Proof-erased original recurrence, including field and first-error order. -/
theorem Stmt.decode_unfold (path : String) (j : Json) : Stmt.decode path j =
  oneof path j
    [("assign", fun p v => do
       pure (Stmt.assign (← msgField p v "target" LValue.decode)
         (← msgField p v "value" Expr.decode))),
     ("conditional", fun p v => do
       pure (Stmt.conditional (← msgField p v "condition" Expr.decode)
         (← listField p v "then" Stmt.decode) (← listField p v "otherwise" Stmt.decode))),
     ("apply", fun p v => do
       pure (Stmt.apply (← strField p v "table") (← optField p v "hit" LValue.decode))),
     ("call_action", fun p v => do
       pure (Stmt.callAction (← strField p v "action") (← listField p v "args" Arg.decode))),
     ("call_block", fun p v => do
       pure (Stmt.callBlock (← strField p v "block") (← listField p v "args" Arg.decode))),
     ("call_extern", fun p v => do
       pure (Stmt.callExtern (← strField p v "instance") (← strField p v "method")
         (← listField p v "args" Arg.decode) (← optField p v "result" LValue.decode))),
     ("set_valid", fun p v => Stmt.setValid <$> msgField p v "header" LValue.decode),
     ("set_invalid", fun p v => Stmt.setInvalid <$> msgField p v "header" LValue.decode),
     ("push", fun p v => do
       pure (Stmt.push (← msgField p v "stack" LValue.decode) (← uint32Field p v "count"))),
     ("pop", fun p v => do
       pure (Stmt.pop (← msgField p v "stack" LValue.decode) (← uint32Field p v "count"))),
     ("extract", fun p v => Stmt.extract <$> msgField p v "target" LValue.decode),
     ("advance", fun p v => Stmt.advance <$> msgField p v "bits" Expr.decode),
     ("verify", fun p v => do
       pure (Stmt.verify (← msgField p v "condition" Expr.decode) (← strField p v "error"))),
     ("emit", fun p v => Stmt.emit <$> msgField p v "value" Expr.decode)] := by
  rw [Stmt.decode.eq_def]
  simp only [listFieldBounded_erasure]
  rw [← oneofBounded_erasure]
  rfl

open Decode in
/-- Decode a `Key` message. -/
def Key.decode (path : String) (j : Json) : Dec Key := do
  pure { expr := ← msgField path j "expr" Expr.decode,
         matchKind := ← enumField path j "match_kind" MatchKind.names,
         name := ← strField path j "name" }

open Decode in
/-- Decode an `ActionCall` message. -/
def ActionCall.decode (path : String) (j : Json) : Dec ActionCall := do
  pure { action := ← strField path j "action", args := ← listField path j "args" Literal.decode }

open Decode in
/-- Decode a `KeyValue` message. -/
def KeyValue.decode (path : String) (j : Json) : Dec KeyValue :=
  oneof path j
    [("exact", fun p v => KeyValue.exact <$> decimalStr p v),
     ("lpm", fun p v => do
       pure (KeyValue.lpm (← decimalField p v "value") (← uint32Field p v "prefix_len"))),
     ("ternary", fun p v => do
       pure (KeyValue.ternary (← decimalField p v "value") (← decimalField p v "mask")))]

open Decode in
/-- Decode an `Entry` message. -/
def Entry.decode (path : String) (j : Json) : Dec Entry := do
  pure { keys := ← listField path j "keys" KeyValue.decode,
         action := ← msgField path j "action" ActionCall.decode,
         priority := ← uint32Field path j "priority" }

open Decode in
/-- Decode a `Table` message. -/
def Table.decode (path : String) (j : Json) : Dec Table := do
  pure { name := ← strField path j "name", keys := ← listField path j "keys" Key.decode,
         actions := ← listField path j "actions" str,
         defaultAction := ← optField path j "default_action" ActionCall.decode,
         constDefaultAction := ← boolField path j "const_default_action",
         constEntries := ← listField path j "const_entries" Entry.decode,
         size := ← uint32Field path j "size" }

open Decode in
/-- Decode a `Target` message. -/
def Target.decode (path : String) (j : Json) : Dec Target :=
  oneof path j
    [("state", fun p v => Target.state <$> str p v),
     ("accept", fun p v => emptyMsg p v *> pure Target.accept),
     ("reject", fun p v => emptyMsg p v *> pure Target.reject)]

open Decode in
/-- Decode a `KeySet` message. -/
def KeySet.decode (path : String) (j : Json) : Dec KeySet :=
  oneof path j
    [("exact", fun p v => KeySet.exact <$> Literal.decode p v),
     ("masked", fun p v => do
       pure (KeySet.masked (← msgField p v "value" Literal.decode)
         (← msgField p v "mask" Literal.decode))),
     ("range", fun p v => do
       pure (KeySet.range (← msgField p v "lo" Literal.decode) (← msgField p v "hi" Literal.decode))),
     ("dont_care", fun p v => emptyMsg p v *> pure KeySet.dontCare)]

open Decode in
/-- Decode a `SelectCase` message. -/
def SelectCase.decode (path : String) (j : Json) : Dec SelectCase := do
  pure { sets := ← listField path j "sets" KeySet.decode,
         target := ← msgField path j "target" Target.decode }

open Decode in
/-- Decode a `Transition` message. -/
def Transition.decode (path : String) (j : Json) : Dec Transition :=
  oneof path j
    [("direct", fun p v => Transition.direct <$> Target.decode p v),
     ("select", fun p v => do
       pure (Transition.select (← listField p v "keys" Expr.decode)
         (← listField p v "cases" SelectCase.decode)))]

open Decode in
/-- Decode a `State` message. -/
def State.decode (path : String) (j : Json) : Dec State := do
  pure { name := ← strField path j "name", body := ← listField path j "body" Stmt.decode,
         transition := ← msgField path j "transition" Transition.decode }

open Decode in
/-- Decode an `Action` message. -/
def Action.decode (path : String) (j : Json) : Dec Action := do
  pure { name := ← strField path j "name", params := ← listField path j "params" Param.decode,
         body := ← listField path j "body" Stmt.decode }

open Decode in
/-- Decode a `Block` message. -/
def Block.decode (path : String) (j : Json) : Dec Block := do
  pure { name := ← strField path j "name", kind := ← enumField path j "kind" BlockKind.names,
         params := ← listField path j "params" Param.decode,
         locals := ← listField path j "locals" Var.decode,
         actions := ← listField path j "actions" Action.decode,
         tables := ← listField path j "tables" Table.decode,
         states := ← listField path j "states" State.decode,
         startState := ← strField path j "start_state",
         body := ← listField path j "body" Stmt.decode }

open Decode in
/-- Decode a `BlockLibrary` message. The path of the program itself is `""`, so
that errors read `blocks[0].name: ...`. -/
def BlockLibrary.decode (path : String) (j : Json) : Dec BlockLibrary := do
  pure { name := ← strField path j "name", errors := ← listField path j "errors" str,
         headerTypes := ← listField path j "header_types" HeaderType.decode,
         structTypes := ← listField path j "struct_types" StructType.decode,
         enumTypes := ← listField path j "enum_types" EnumType.decode,
         externTypes := ← listField path j "extern_types" ExternType.decode,
         externInstances := ← listField path j "extern_instances" ExternInstance.decode,
         blocks := ← listField path j "blocks" Block.decode }

open Decode in
/-- Decode a `TableEntries` message. -/
def TableEntries.decode (path : String) (j : Json) : Dec TableEntries := do
  pure { block := ← strField path j "block", table := ← strField path j "table",
         entries := ← listField path j "entries" Entry.decode,
         defaultAction := ← optField path j "default_action" ActionCall.decode }

open Decode in
/-- Decode an `Entries` message. -/
def Entries.decode (path : String) (j : Json) : Dec Entries := do
  pure { tables := ← listField path j "tables" TableEntries.decode }

/-- Parse and decode a program from its JSON text. -/
def BlockLibrary.fromJsonString (text : String) : Except String BlockLibrary := do
  BlockLibrary.decode "" (← Json.parse text)

/-- Parse and decode host entries from their JSON text. -/
def Entries.fromJsonString (text : String) : Except String Entries := do
  Entries.decode "" (← Json.parse text)

instance : FromJson Ty := ⟨Ty.decode ""⟩
instance : FromJson Literal := ⟨Literal.decode ""⟩
instance : FromJson Field := ⟨Field.decode ""⟩
instance : FromJson HeaderType := ⟨HeaderType.decode ""⟩
instance : FromJson StructType := ⟨StructType.decode ""⟩
instance : FromJson EnumType := ⟨EnumType.decode ""⟩
instance : FromJson Var := ⟨Var.decode ""⟩
instance : FromJson Param := ⟨Param.decode ""⟩
instance : FromJson Method := ⟨Method.decode ""⟩
instance : FromJson ExternType := ⟨ExternType.decode ""⟩
instance : FromJson ExternInstance := ⟨ExternInstance.decode ""⟩
instance : FromJson Expr := ⟨Expr.decode ""⟩
instance : FromJson LValue := ⟨LValue.decode ""⟩
instance : FromJson Arg := ⟨Arg.decode ""⟩
instance : FromJson Stmt := ⟨Stmt.decode ""⟩
instance : FromJson Key := ⟨Key.decode ""⟩
instance : FromJson ActionCall := ⟨ActionCall.decode ""⟩
instance : FromJson KeyValue := ⟨KeyValue.decode ""⟩
instance : FromJson Entry := ⟨Entry.decode ""⟩
instance : FromJson Table := ⟨Table.decode ""⟩
instance : FromJson Target := ⟨Target.decode ""⟩
instance : FromJson KeySet := ⟨KeySet.decode ""⟩
instance : FromJson SelectCase := ⟨SelectCase.decode ""⟩
instance : FromJson Transition := ⟨Transition.decode ""⟩
instance : FromJson State := ⟨State.decode ""⟩
instance : FromJson Action := ⟨Action.decode ""⟩
instance : FromJson Block := ⟨Block.decode ""⟩
instance : FromJson BlockLibrary := ⟨BlockLibrary.decode ""⟩
instance : FromJson TableEntries := ⟨TableEntries.decode ""⟩
instance : FromJson Entries := ⟨Entries.decode ""⟩

-- ---------------------------------------------------------------------------
-- Encoding
-- ---------------------------------------------------------------------------

namespace Encode

/-- The fields of an encoded message: each helper contributes its key only
when the value is not the proto default, as `dump_json` does. -/
abbrev Fields := List (String × Json)

/-- A string field, omitted when empty. -/
def ofStr (key : String) (s : String) : Fields := if s.isEmpty then [] else [(key, .str s)]

/-- A string field that is always present (a set oneof case, or a message
whose only field is a name). -/
def ofStr! (key : String) (s : String) : Fields := [(key, .str s)]

/-- A `uint32` field, omitted when zero. -/
def ofNat (key : String) (n : Nat) : Fields := if n == 0 then [] else [(key, Lean.toJson n)]

/-- A boolean field, omitted when false. -/
def ofBool (key : String) (b : Bool) : Fields := if b then [(key, .bool b)] else []

/-- A decimal-string field. Numeric zero is the nonempty string `"0"`, not
the protobuf string default `""`, and must remain present. -/
def ofDecimal (key : String) (n : Nat) : Fields := [(key, .str (toString n))]

/-- A message field. -/
def ofMsg (key : String) (j : Json) : Fields := [(key, j)]

/-- An `optional` message field. -/
def ofOpt (key : String) (j : Option Json) : Fields := j.toList.map (key, ·)

/-- A repeated field, omitted when empty. -/
def ofList (key : String) (xs : List Json) : Fields :=
  if xs.isEmpty then [] else [(key, .arr xs.toArray)]

/-- An enum field by proto name. -/
def ofEnum (key : String) (name : String) : Fields := [(key, .str name)]

/-- The object of some field groups. -/
def obj (groups : List Fields) : Json := Json.mkObj groups.flatten

/-- The one-case object of a oneof. -/
def case (key : String) (j : Json) : Json := Json.mkObj [(key, j)]

/-- `{}`. -/
def empty : Json := Json.mkObj []

end Encode

open Encode in
/-- Encode a `Type` message. -/
def Ty.toJson : Ty → Json
  | .bits n => case "bits" (Lean.toJson n)
  | .boolean => case "boolean" empty
  | .header name => case "header" (.str name)
  | .struct name => case "struct" (.str name)
  | .enumType name => case "enum_type" (.str name)
  | .error => case "error" empty
  | .stack hdr size => case "stack" (obj [ofStr "header" hdr, ofNat "size" size])

open Encode in
/-- Encode a `Literal` message. -/
def Literal.toJson : Literal → Json
  | .bits width value => case "bits" (obj [ofNat "width" width, ofDecimal "value" value])
  | .boolean b => case "boolean" (.bool b)
  | .enumMember enumType member =>
    case "enum_member" (obj [ofStr "enum_type" enumType, ofStr "member" member])
  | .error name => case "error" (.str name)

open Encode in
/-- Encode a `Field` message. -/
def Field.toJson (f : Field) : Json := obj [ofStr "name" f.name, ofMsg "type" f.type.toJson]

open Encode in
/-- Encode a `HeaderType` message. -/
def HeaderType.toJson (t : HeaderType) : Json :=
  obj [ofStr "name" t.name, ofList "fields" (t.fields.map Field.toJson)]

open Encode in
/-- Encode a `StructType` message. -/
def StructType.toJson (t : StructType) : Json :=
  obj [ofStr "name" t.name, ofList "fields" (t.fields.map Field.toJson)]

open Encode in
/-- Encode an `EnumType` message. -/
def EnumType.toJson (t : EnumType) : Json :=
  obj [ofStr "name" t.name, ofList "members" (t.members.map Json.str)]

open Encode in
/-- Encode a `Var` message. -/
def Var.toJson (v : Var) : Json := obj [ofStr "name" v.name, ofMsg "type" v.type.toJson]

open Encode in
/-- Encode a `Param` message. -/
def Param.toJson (p : Param) : Json :=
  obj [ofStr "name" p.name, ofMsg "type" p.type.toJson, ofEnum "direction" p.direction.protoName]

open Encode in
/-- Encode a `Method` message. -/
def Method.toJson (m : Method) : Json :=
  obj [ofStr "name" m.name, ofList "params" (m.params.map Param.toJson),
       ofOpt "returns" (m.returns.map Ty.toJson)]

open Encode in
/-- Encode an `ExternType` message. -/
def ExternType.toJson (t : ExternType) : Json :=
  obj [ofStr "name" t.name, ofList "constructor_params" (t.constructorParams.map Param.toJson),
       ofList "methods" (t.methods.map Method.toJson)]

open Encode in
/-- Encode an `ExternInstance` message. -/
def ExternInstance.toJson (i : ExternInstance) : Json :=
  obj [ofStr "name" i.name, ofStr "extern_type" i.externType,
       ofList "args" (i.args.map Literal.toJson)]

open Encode in
/-- Encode an `Expr` message. -/
def Expr.toJson : Expr → Json
  | .literal v => case "literal" v.toJson
  | .var name => case "var" (.str name)
  | .member base field => case "member" (obj [ofMsg "base" base.toJson, ofStr "field" field])
  | .index base idx => case "index" (obj [ofMsg "base" base.toJson, ofMsg "index" idx.toJson])
  | .lastIndex stack => case "last_index" (obj [ofMsg "stack" stack.toJson])
  | .unary op operand =>
    case "unary" (obj [ofEnum "op" op.protoName, ofMsg "operand" operand.toJson])
  | .binary op left right =>
    case "binary" (obj [ofEnum "op" op.protoName, ofMsg "left" left.toJson,
      ofMsg "right" right.toJson])
  | .cast to operand => case "cast" (obj [ofMsg "to" to.toJson, ofMsg "operand" operand.toJson])
  | .slice operand hi lo =>
    case "slice" (obj [ofMsg "operand" operand.toJson, ofNat "hi" hi, ofNat "lo" lo])
  | .isValid header => case "is_valid" (obj [ofMsg "header" header.toJson])
  | .mux condition thenBranch otherwise =>
    case "mux" (obj [ofMsg "condition" condition.toJson, ofMsg "then" thenBranch.toJson,
      ofMsg "otherwise" otherwise.toJson])
  | .lookahead type => case "lookahead" (obj [ofMsg "type" type.toJson])

open Encode in
/-- Encode an `LValue` message. -/
def LValue.toJson : LValue → Json
  | .var name => case "var" (.str name)
  | .member base field => case "member" (obj [ofMsg "base" base.toJson, ofStr "field" field])
  | .index base idx => case "index" (obj [ofMsg "base" base.toJson, ofMsg "index" idx.toJson])
  | .next stack => case "next" (obj [ofMsg "stack" stack.toJson])

open Encode in
/-- Encode an `Arg` message. -/
def Arg.toJson : Arg → Json
  | .expr e => case "expr" e.toJson
  | .lvalue l => case "lvalue" l.toJson

open Encode in
/-- Encode a `Stmt` message. -/
def Stmt.toJson : Stmt → Json
  | .assign target value =>
    case "assign" (obj [ofMsg "target" target.toJson, ofMsg "value" value.toJson])
  | .conditional condition thenBranch otherwise =>
    case "conditional" (obj [ofMsg "condition" condition.toJson,
      ofList "then" (thenBranch.map Stmt.toJson), ofList "otherwise" (otherwise.map Stmt.toJson)])
  | .apply table hit => case "apply" (obj [ofStr "table" table, ofOpt "hit" (hit.map LValue.toJson)])
  | .callAction action args =>
    case "call_action" (obj [ofStr "action" action, ofList "args" (args.map Arg.toJson)])
  | .callBlock block args =>
    case "call_block" (obj [ofStr "block" block, ofList "args" (args.map Arg.toJson)])
  | .callExtern inst method args result =>
    case "call_extern" (obj [ofStr "instance" inst, ofStr "method" method,
      ofList "args" (args.map Arg.toJson), ofOpt "result" (result.map LValue.toJson)])
  | .setValid header => case "set_valid" (obj [ofMsg "header" header.toJson])
  | .setInvalid header => case "set_invalid" (obj [ofMsg "header" header.toJson])
  | .push stack count => case "push" (obj [ofMsg "stack" stack.toJson, ofNat "count" count])
  | .pop stack count => case "pop" (obj [ofMsg "stack" stack.toJson, ofNat "count" count])
  | .extract target => case "extract" (obj [ofMsg "target" target.toJson])
  | .advance bits => case "advance" (obj [ofMsg "bits" bits.toJson])
  | .verify condition error =>
    case "verify" (obj [ofMsg "condition" condition.toJson, ofStr "error" error])
  | .emit value => case "emit" (obj [ofMsg "value" value.toJson])

open Encode in
/-- Encode a `Key` message. -/
def Key.toJson (k : Key) : Json :=
  obj [ofMsg "expr" k.expr.toJson, ofEnum "match_kind" k.matchKind.protoName, ofStr "name" k.name]

open Encode in
/-- Encode an `ActionCall` message. -/
def ActionCall.toJson (c : ActionCall) : Json :=
  obj [ofStr "action" c.action, ofList "args" (c.args.map Literal.toJson)]

open Encode in
/-- Encode a `KeyValue` message. -/
def KeyValue.toJson : KeyValue → Json
  | .exact value => case "exact" (.str (toString value))
  | .lpm value prefixLen => case "lpm" (obj [ofDecimal "value" value, ofNat "prefix_len" prefixLen])
  | .ternary value mask => case "ternary" (obj [ofDecimal "value" value, ofDecimal "mask" mask])

open Encode in
/-- Encode an `Entry` message. -/
def Entry.toJson (e : Entry) : Json :=
  obj [ofList "keys" (e.keys.map KeyValue.toJson), ofMsg "action" e.action.toJson,
       ofNat "priority" e.priority]

open Encode in
/-- Encode a `Table` message. -/
def Table.toJson (t : Table) : Json :=
  obj [ofStr "name" t.name, ofList "keys" (t.keys.map Key.toJson),
       ofList "actions" (t.actions.map Json.str),
       ofOpt "default_action" (t.defaultAction.map ActionCall.toJson),
       ofBool "const_default_action" t.constDefaultAction,
       ofList "const_entries" (t.constEntries.map Entry.toJson), ofNat "size" t.size]

open Encode in
/-- Encode a `Target` message. -/
def Target.toJson : Target → Json
  | .state name => case "state" (.str name)
  | .accept => case "accept" empty
  | .reject => case "reject" empty

open Encode in
/-- Encode a `KeySet` message. -/
def KeySet.toJson : KeySet → Json
  | .exact value => case "exact" value.toJson
  | .masked value mask => case "masked" (obj [ofMsg "value" value.toJson, ofMsg "mask" mask.toJson])
  | .range lo hi => case "range" (obj [ofMsg "lo" lo.toJson, ofMsg "hi" hi.toJson])
  | .dontCare => case "dont_care" empty

open Encode in
/-- Encode a `SelectCase` message. -/
def SelectCase.toJson (c : SelectCase) : Json :=
  obj [ofList "sets" (c.sets.map KeySet.toJson), ofMsg "target" c.target.toJson]

open Encode in
/-- Encode a `Transition` message. -/
def Transition.toJson : Transition → Json
  | .direct target => case "direct" target.toJson
  | .select keys cases =>
    case "select" (obj [ofList "keys" (keys.map Expr.toJson),
      ofList "cases" (cases.map SelectCase.toJson)])

open Encode in
/-- Encode a `State` message. -/
def State.toJson (s : State) : Json :=
  obj [ofStr "name" s.name, ofList "body" (s.body.map Stmt.toJson),
       ofMsg "transition" s.transition.toJson]

open Encode in
/-- Encode an `Action` message. -/
def Action.toJson (a : Action) : Json :=
  obj [ofStr "name" a.name, ofList "params" (a.params.map Param.toJson),
       ofList "body" (a.body.map Stmt.toJson)]

open Encode in
/-- Encode a `Block` message. -/
def Block.toJson (b : Block) : Json :=
  obj [ofStr "name" b.name, ofEnum "kind" b.kind.protoName,
       ofList "params" (b.params.map Param.toJson), ofList "locals" (b.locals.map Var.toJson),
       ofList "actions" (b.actions.map Action.toJson), ofList "tables" (b.tables.map Table.toJson),
       ofList "states" (b.states.map State.toJson), ofStr "start_state" b.startState,
       ofList "body" (b.body.map Stmt.toJson)]

open Encode in
/-- Encode a `BlockLibrary` message. -/
def BlockLibrary.toJson (p : BlockLibrary) : Json :=
  obj [ofStr "name" p.name, ofList "errors" (p.errors.map Json.str),
       ofList "header_types" (p.headerTypes.map HeaderType.toJson),
       ofList "struct_types" (p.structTypes.map StructType.toJson),
       ofList "enum_types" (p.enumTypes.map EnumType.toJson),
       ofList "extern_types" (p.externTypes.map ExternType.toJson),
       ofList "extern_instances" (p.externInstances.map ExternInstance.toJson),
       ofList "blocks" (p.blocks.map Block.toJson)]

open Encode in
/-- Encode a `TableEntries` message. -/
def TableEntries.toJson (t : TableEntries) : Json :=
  obj [ofStr "block" t.block, ofStr "table" t.table, ofList "entries" (t.entries.map Entry.toJson),
       ofOpt "default_action" (t.defaultAction.map ActionCall.toJson)]

open Encode in
/-- Encode an `Entries` message. -/
def Entries.toJson (e : Entries) : Json := obj [ofList "tables" (e.tables.map TableEntries.toJson)]

instance : ToJson Ty := ⟨Ty.toJson⟩
instance : ToJson Literal := ⟨Literal.toJson⟩
instance : ToJson Field := ⟨Field.toJson⟩
instance : ToJson HeaderType := ⟨HeaderType.toJson⟩
instance : ToJson StructType := ⟨StructType.toJson⟩
instance : ToJson EnumType := ⟨EnumType.toJson⟩
instance : ToJson Var := ⟨Var.toJson⟩
instance : ToJson Param := ⟨Param.toJson⟩
instance : ToJson Method := ⟨Method.toJson⟩
instance : ToJson ExternType := ⟨ExternType.toJson⟩
instance : ToJson ExternInstance := ⟨ExternInstance.toJson⟩
instance : ToJson Expr := ⟨Expr.toJson⟩
instance : ToJson LValue := ⟨LValue.toJson⟩
instance : ToJson Arg := ⟨Arg.toJson⟩
instance : ToJson Stmt := ⟨Stmt.toJson⟩
instance : ToJson Key := ⟨Key.toJson⟩
instance : ToJson ActionCall := ⟨ActionCall.toJson⟩
instance : ToJson KeyValue := ⟨KeyValue.toJson⟩
instance : ToJson Entry := ⟨Entry.toJson⟩
instance : ToJson Table := ⟨Table.toJson⟩
instance : ToJson Target := ⟨Target.toJson⟩
instance : ToJson KeySet := ⟨KeySet.toJson⟩
instance : ToJson SelectCase := ⟨SelectCase.toJson⟩
instance : ToJson Transition := ⟨Transition.toJson⟩
instance : ToJson State := ⟨State.toJson⟩
instance : ToJson Action := ⟨Action.toJson⟩
instance : ToJson Block := ⟨Block.toJson⟩
instance : ToJson BlockLibrary := ⟨BlockLibrary.toJson⟩
instance : ToJson TableEntries := ⟨TableEntries.toJson⟩
instance : ToJson Entries := ⟨Entries.toJson⟩

end P4bloIR
