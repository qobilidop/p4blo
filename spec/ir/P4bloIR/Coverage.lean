import P4bloIR.Exec

/-!
# Rule tags: which rules of the semantics a run exercised

The adequacy criterion for differential testing is coverage of the
semantics' own rules, measured on the executable Lean definition, as ESMeta
and JEST measure it for JavaScript. This module names those rules and
classifies a configuration of
the step machine by the rules its next step is about to exercise. It
mirrors nothing in Python: the Python interpreter is a peer under test, not
the criterion.

**Tags.** Every constructor of `Tag` is one stable identifier, spelled
`<category>.<construct>` for a plain evaluator case and
`<category>.<construct>.<case>` for a closed behavior of
docs/ir-semantics.md, all segments lower camel case. The categories are
`expr` (one case of `evaluate`, and the value rules of "Values"), `value`,
`header`, `stack`, `lvalue` (one case of `writeLValue`), `stmt` (one case of
`executeOne`), `parser`, `select`, `table`, `call` and `emit`. A tag is
never renamed: a new rule gets a new tag, and a retired rule's tag is
deleted with it. The docstring of each constructor says the rule it stands
for; `Coverage.all` lists every tag with that docstring, read from the
environment at compile time, so the list and the docstrings cannot drift.

**Conditions.** `classify` is a pure function of the configuration the
step machine is about to step: the head work item and the current `Run`.
It reuses the real evaluator (`evaluate`, `readLValue`, `keySetMatches`,
`Installed.lookup`, `keyValueMatches`) and the real helpers for widths and
values to decide the operands of a rule, and duplicates only the *condition*
of a closed behavior (for example "the shift amount is at least the
width"), never its outcome. Expressions nested inside one step are walked
syntactically in evaluation order: a sub-expression's operands are
evaluated with the real evaluator first, the effects of that evaluation
are discarded, and walking stops where evaluation would fault or short
circuit. Nothing here is called by the semantics: `Execution.step` and
the theorems do not mention this module, and the observer that runs the
machine with it lives in the architecture package.
-/

namespace P4bloIR

namespace Coverage

/-- `tag_inventory T`, docstring-and-name pairs, then `end_tag_inventory`, declares the
inductive `T` with one constructor per pair, carrying its docstring, and
`T.inventory`, every constructor with its name and docstring as data. One
source for both, so the inventory cannot drift from the docstrings; a
macro rather than an elaborator, so this module needs no `import Lean`,
which would bring `Lean.Expr` into every module that opens `Lean` beside
`P4bloIR`. -/
syntax (docComment)? "tag_inventory " ident (ppLine docComment ident)* ppLine "end_tag_inventory" :
    command

macro_rules
  | `($[$doc?:docComment]? tag_inventory $ty $[$docs:docComment $ctors:ident]* end_tag_inventory) => do
    let items ← (docs.zip ctors).mapM fun (d, c) =>
      `(($(Lean.mkIdent (ty.getId ++ c.getId)), $(Lean.quote (c.getId.toString (escape := false))),
          $(Lean.quote d.getDocString)))
    let inductive_ ← `($[$doc?:docComment]? inductive $ty where
        $[$docs:docComment | $ctors:ident]*
        deriving Repr, DecidableEq, Inhabited)
    let inventory ← `(/-- Every constructor with its name and raw docstring. -/
      def $(Lean.mkIdent (ty.getId ++ `inventory)) : List ($ty × String × String) := [$items,*])
    return Lean.mkNullNode #[inductive_, inventory]

/-- The rules a differential run can exercise. See the module header for the
naming scheme; each docstring names the evaluator case or the closed behavior
of docs/ir-semantics.md the tag stands for, and says when a condition is only
a witness rather than the exact behavior. -/
tag_inventory Tag
  -- Expressions: one tag per case of `evaluate`.
  /-- `evaluate`, a literal. -/
  «expr.literal»
  /-- `evaluate`, a variable read. -/
  «expr.var»
  /-- `evaluate`, a field of a header or struct. -/
  «expr.member»
  /-- `evaluate`, a stack element `hs[i]`. -/
  «expr.index»
  /-- `evaluate`, `hs.lastIndex`. -/
  «expr.lastIndex»
  /-- `evaluate`, logical not. -/
  «expr.not»
  /-- `evaluate`, bitwise complement. -/
  «expr.complement»
  /-- `evaluate`, two's complement negation. -/
  «expr.negate»
  /-- `evaluate`, `+` on bits. -/
  «expr.add»
  /-- `evaluate`, `-` on bits. -/
  «expr.sub»
  /-- `evaluate`, `*` on bits. -/
  «expr.mul»
  /-- `evaluate`, saturating `|+|`. -/
  «expr.addSat»
  /-- `evaluate`, saturating `|-|`. -/
  «expr.subSat»
  /-- `evaluate`, bitwise and. -/
  «expr.bitAnd»
  /-- `evaluate`, bitwise or. -/
  «expr.bitOr»
  /-- `evaluate`, bitwise xor. -/
  «expr.bitXor»
  /-- `evaluate`, left shift. -/
  «expr.shl»
  /-- `evaluate`, right shift. -/
  «expr.shr»
  /-- `evaluate`, concatenation `++`. -/
  «expr.concat»
  /-- `evaluate`, `==`. -/
  «expr.eq»
  /-- `evaluate`, `!=`. -/
  «expr.ne»
  /-- `evaluate`, unsigned `<`. -/
  «expr.lt»
  /-- `evaluate`, unsigned `<=`. -/
  «expr.le»
  /-- `evaluate`, unsigned `>`. -/
  «expr.gt»
  /-- `evaluate`, unsigned `>=`. -/
  «expr.ge»
  /-- `evaluate`, short-circuit `&&`. -/
  «expr.and»
  /-- `evaluate`, short-circuit `||`. -/
  «expr.or»
  /-- `evaluate`, a cast. -/
  «expr.cast»
  /-- `evaluate`, a slice `e[hi:lo]`. -/
  «expr.slice»
  /-- `evaluate`, `isValid`. -/
  «expr.isValid»
  /-- `evaluate`, the conditional operator. -/
  «expr.mux»
  /-- `evaluate`, `lookahead<T>`. -/
  «expr.lookahead»
  -- Values: the closed behaviors of "Values".
  /-- Values, "Arithmetic": `+` whose true sum is at least `2^N`, so it wraps. -/
  «expr.add.wrap»
  /-- Values, "Arithmetic": `-` with the right operand larger, so it wraps. -/
  «expr.sub.wrap»
  /-- Values, "Arithmetic": `*` whose true product is at least `2^N`, so it wraps. -/
  «expr.mul.wrap»
  /-- Values, "Arithmetic": `|+|` whose true sum exceeds `2^N - 1`, so it saturates. -/
  «expr.addSat.clamp»
  /-- Values, "Arithmetic": `|-|` with the right operand larger, so it saturates at 0. -/
  «expr.subSat.clamp»
  /-- Values, "Shifts": `<<` by an amount at least the width, which gives 0. -/
  «expr.shl.overflow»
  /-- Values, "Shifts": `>>` by an amount at least the width, which gives 0. -/
  «expr.shr.overflow»
  /-- Values, "Shifts": `<<` by less than the width that shifts set bits out,
  so the result is truncated to `N` bits. -/
  «expr.shl.truncate»
  /-- Values, "Shifts": a shift whose amount has a different width from the
  shifted value; the amount's width does not affect the result. -/
  «expr.shift.otherWidth»
  /-- Values, "Comparison": `==` or `!=` on two `bit<N>` values. -/
  «expr.equality.bits»
  /-- Values, "Comparison": `==` or `!=` on two booleans. -/
  «expr.equality.bool»
  /-- Values, "Comparison": `==` or `!=` on two enum members, by member. -/
  «expr.equality.enum»
  /-- Values, "Comparison": `==` or `!=` on two errors, by member. -/
  «expr.equality.error»
  /-- Headers, "Header equality": two valid headers, compared fieldwise. -/
  «expr.equality.header.bothValid»
  /-- Headers, "Header equality": one valid and one invalid header, unequal. -/
  «expr.equality.header.validityDiffers»
  /-- Headers, "Header equality": two invalid headers, equal regardless of fields. -/
  «expr.equality.header.bothInvalid»
  /-- Headers, "Header equality": two invalid headers whose stored fields
  differ, still equal. -/
  «expr.equality.header.invalidFieldsDiffer»
  /-- Values, "Comparison": `==` or `!=` on two structs, fieldwise. -/
  «expr.equality.struct»
  /-- Values, "Comparison": `==` or `!=` on two stacks, elementwise. -/
  «expr.equality.stack»
  /-- Values, "Comparison": two stacks with different `nextIndex`, which
  equality does not compare. -/
  «expr.equality.stack.nextIndexDiffers»
  /-- Values, "Casts": `bit<N>` to a narrower `bit<M>`, truncating. -/
  «expr.cast.truncate»
  /-- Values, "Casts": `bit<N>` to a wider `bit<M>`, zero-extending. -/
  «expr.cast.extend»
  /-- Values, "Casts": `bit<N>` to `bit<N>`. -/
  «expr.cast.sameWidth»
  /-- Values, "Casts": `bool` to `bit<1>`. -/
  «expr.cast.boolToBits»
  /-- Values, "Casts": `bit<1>` to `bool`. -/
  «expr.cast.bitsToBool»
  /-- `evaluate`: `&&` whose left operand is false, so the right is not evaluated. -/
  «expr.and.shortCircuit»
  /-- `evaluate`: `||` whose left operand is true, so the right is not evaluated. -/
  «expr.or.shortCircuit»
  /-- Parsers, "lookahead": a `bit<N>` read. -/
  «expr.lookahead.bits»
  /-- Parsers, "lookahead": a `bool` read, one bit. -/
  «expr.lookahead.bool»
  /-- Parsers, "lookahead": a header read, whose result is valid. -/
  «expr.lookahead.header»
  /-- Parsers, "lookahead": fewer bits remain than the width, `PacketTooShort`. -/
  «expr.lookahead.tooShort»
  /-- Values, "Uninitialized variables": a read of a block local or an `out`
  parameter that holds its type's zero value. A witness, not the exact
  behavior: a variable explicitly written with zero also counts. -/
  «value.uninitialized»
  -- Headers.
  /-- Headers, "Reading a field of an invalid header": the stored value is returned. -/
  «header.field.readInvalid»
  /-- Headers, "Writing a field of an invalid header": stored, validity unchanged. -/
  «header.field.writeInvalid»
  /-- Headers, "Assigning a header": an invalid header is assigned, so the
  target becomes invalid and the fields are copied anyway. -/
  «header.assign.invalid»
  /-- Headers, "`setValid` on a valid header": no effect on the fields. -/
  «header.setValid.alreadyValid»
  /-- Headers, "`setInvalid` on an invalid one": no effect on the fields. -/
  «header.setInvalid.alreadyInvalid»
  -- Header stacks.
  /-- Header stacks, "Index out of range": a read of `hs[i]` with `i >= S`
  gives a zero invalid header. -/
  «stack.index.readOutOfRange»
  /-- Header stacks, "Index out of range": a write through `hs[i]` with
  `i >= S` does nothing. -/
  «stack.index.writeOutOfRange»
  /-- Header stacks, "`hs.lastIndex`": `nextIndex == 0`, so the value wraps to `2^32 - 1`. -/
  «stack.lastIndex.empty»
  /-- Header stacks, "`push_front`": `nextIndex + n` exceeds the size, so it clamps at `S`. -/
  «stack.push.clamp»
  /-- Header stacks, "`push_front`": `n > S`, which behaves as `n = S`. -/
  «stack.push.oversize»
  /-- Header stacks, "`pop_front`": `n` exceeds `nextIndex`, so it clamps at 0. -/
  «stack.pop.clamp»
  /-- Header stacks, "`pop_front`": `n > S`, which behaves as `n = S`. -/
  «stack.pop.oversize»
  -- Lvalues: one tag per case of `writeLValue` at the top of a write.
  /-- `writeLValue`, a variable. -/
  «lvalue.var»
  /-- `writeLValue`, a field. -/
  «lvalue.member»
  /-- `writeLValue`, a stack element. -/
  «lvalue.index»
  -- Statements: one tag per case of `executeOne`.
  /-- `executeOne`, assignment. -/
  «stmt.assign»
  /-- `executeOne`, `if`. -/
  «stmt.conditional»
  /-- `executeOne`, `if` whose condition holds. -/
  «stmt.conditional.then»
  /-- `executeOne`, `if` whose condition fails. -/
  «stmt.conditional.otherwise»
  /-- `executeOne`, a table apply. -/
  «stmt.apply»
  /-- `executeOne`, a direct action call. -/
  «stmt.callAction»
  /-- `executeOne`, a sub-block call. -/
  «stmt.callBlock»
  /-- `executeOne`, an extern method call. -/
  «stmt.callExtern»
  /-- `executeOne`, `setValid`. -/
  «stmt.setValid»
  /-- `executeOne`, `setInvalid`. -/
  «stmt.setInvalid»
  /-- `executeOne`, `push_front`. -/
  «stmt.push»
  /-- `executeOne`, `pop_front`. -/
  «stmt.pop»
  /-- `executeOne`, `extract`. -/
  «stmt.extract»
  /-- `executeOne`, `advance`. -/
  «stmt.advance»
  /-- `executeOne`, `verify`. -/
  «stmt.verify»
  /-- `executeOne`, `emit`. -/
  «stmt.emit»
  -- Parsers.
  /-- Parsers, "Extract sets the target valid": an extract into a header lvalue. -/
  «parser.extract.header»
  /-- Header stacks, "`hs.next`": an extract into `hs.next`. -/
  «parser.extract.next»
  /-- Parsers, "Extraction past the packet end": fewer bits remain than the
  header's width, `PacketTooShort`, nothing consumed. -/
  «parser.extract.tooShort»
  /-- Parsers, "Extract sets the target valid": a header of width zero,
  which consumes nothing even at the end of the packet. -/
  «parser.extract.zeroWidth»
  /-- Header stacks, "`hs.next`": `nextIndex == S`, `StackOutOfBounds`. -/
  «parser.extract.next.full»
  /-- Header stacks, "`hs.next`": a full stack and a short packet together,
  which report `StackOutOfBounds`. -/
  «parser.extract.next.fullAndShort»
  /-- Header stacks, "`hs.next`": an extract into `hs[i]` with `i >= S`,
  which consumes the bits and stores nothing. -/
  «parser.extract.indexOutOfRange»
  /-- Parsers, "`advance(n)`": past the end, `PacketTooShort`, the cursor stays. -/
  «parser.advance.tooShort»
  /-- Parsers, "`verify`": the condition holds. -/
  «parser.verify.pass»
  /-- Parsers, "`verify`": the condition fails and the error is raised. -/
  «parser.verify.fail»
  /-- Parsers, "`verify`": the condition fails with error `NoError`, the
  same outcome as an explicit `reject`. -/
  «parser.verify.failNoError»
  /-- The parser's transition case, a direct target. -/
  «parser.transition.direct»
  /-- The parser's transition case, a `select`. -/
  «parser.transition.select»
  /-- A transition to a state. -/
  «parser.target.state»
  /-- A transition to `accept`. -/
  «parser.target.accept»
  /-- Parsers, "`reject`": a transition to `reject` reached explicitly,
  which rejects with `NoError`. -/
  «parser.target.reject»
  /-- Parsers, "Parser loop bound": a state entered again after the cursor
  advanced, which is allowed. -/
  «parser.revisit»
  /-- Parsers, "Parser loop bound": a state entered again with the cursor
  where it was, `ParserTimeout`. -/
  «parser.timeout»
  /-- Parsers, "Parser loop bound": a `ParserTimeout` inside a sub-parser,
  whose states count as states of the enclosing run. -/
  «parser.timeout.subparser»
  /-- Parsers: a call of a sub-parser. -/
  «parser.subparser»
  /-- Parsers: an explicit `reject` inside a sub-parser, which rejects the
  whole run after the copyback. -/
  «parser.subparser.reject»
  -- Select.
  /-- Parsers, "`select`": the taken case has an exact key set. -/
  «select.exact»
  /-- Parsers, "`select`": the taken case has a masked key set. -/
  «select.masked»
  /-- Parsers, "`select`": the taken case has a range key set. -/
  «select.range»
  /-- Parsers, "`select`": the taken case has a don't-care key set. -/
  «select.dontCare»
  /-- Parsers, "`select`": a later case also matches; the first one wins. -/
  «select.firstOfSeveral»
  /-- Parsers, "`select`": no case matches, `NoMatch`. -/
  «select.noMatch»
  /-- Parsers, "`select`": a key that is a `bool`, enum or error. -/
  «select.nonBitsKey»
  /-- Parsers, "`select`": more than one key, evaluated once in order. -/
  «select.multiKey»
  -- Tables.
  /-- Tables, "Exact keys": an applied table has an exact key. -/
  «table.key.exact»
  /-- Tables, "LPM": an applied table has an lpm key. -/
  «table.key.lpm»
  /-- Tables, "Ternary": an applied table has a ternary key. -/
  «table.key.ternary»
  /-- Tables, "`hit`": an entry matched. -/
  «table.hit»
  /-- Tables, "Table miss": no entry matched and the default action runs. -/
  «table.miss»
  /-- Tables, "Table miss": the default action on a miss is an action. -/
  «table.miss.defaultAction»
  /-- Tables, "Table miss": the default on a miss is `NoAction`, nothing. -/
  «table.miss.noAction»
  /-- Tables, "Host default action": a miss runs a default the host replaced. -/
  «table.miss.hostDefault»
  /-- Tables, "LPM": two matching entries with different prefix lengths;
  the longest wins. -/
  «table.lpm.longest»
  /-- Tables, "Ternary": two matching entries; the largest priority wins. -/
  «table.ternary.priority»
  /-- Tables, "Ternary": a matching entry has priority 0, an ordinary one. -/
  «table.ternary.priorityZero»
  /-- Tables: a program's const entry matches. -/
  «table.constEntry»
  /-- Tables, "`hit`": the apply writes whether it hit. -/
  «table.hit.written»
  /-- Tables, "`hit`": the chosen action assigns the same lvalue the apply
  writes `hit` to, and is overwritten. A syntactic witness over the
  action's body. -/
  «table.hit.overwritesAction»
  -- Calls.
  /-- Controls, "Block calls": a sub-block call enters. -/
  «call.block»
  /-- Controls, "Action calls": a direct action call enters. -/
  «call.action»
  /-- Tables: a table runs an action with its action data. -/
  «call.tableAction»
  /-- Externs, "Extern calls": a method call on an extern instance. -/
  «call.extern»
  /-- Controls, "Block calls": an `in` parameter, copied in. -/
  «call.param.in»
  /-- Controls, "Block calls": an `out` parameter, starting at zero. -/
  «call.param.out»
  /-- Controls, "Block calls": an `inout` parameter, copied in and back. -/
  «call.param.inout»
  /-- Controls, "Action calls": a directionless parameter, read-only action data. -/
  «call.param.none»
  /-- Controls, "Block calls": two or more `out` or `inout` arguments are
  copied back, in parameter order. -/
  «call.copyOut.order»
  /-- Controls, "Block calls": an `in` argument reads storage that an `out`
  or `inout` argument of the same call writes; it is copied in first. A
  syntactic witness: the paths share a prefix. -/
  «call.copyIn.overlap»
  /-- Controls, "Recursion": an action called from inside an action. -/
  «call.action.nested»
  /-- Parsers: a block return that copies arguments back while a fault is
  being unwound, as a sub-parser's error propagates. -/
  «call.block.faultCopyBack»
  /-- Externs, "Extern calls": results written back to `out` or `inout` arguments. -/
  «call.extern.out»
  /-- Externs, "Extern calls": the return value written after the results. -/
  «call.extern.result»
  -- Deparsers.
  /-- Deparsers: `emit` of a valid header. -/
  «emit.header.valid»
  /-- Deparsers, "`emit` of an invalid header": writes nothing. -/
  «emit.header.invalid»
  /-- Deparsers, "`emit` of a struct": its fields in declaration order. -/
  «emit.struct»
  /-- Deparsers, "`emit` of a stack": elements from 0 to `S - 1`. -/
  «emit.stack»
  /-- Deparsers, "Bit alignment": the emitted total is not a multiple of
  eight, so it is padded with zero bits. -/
  «emit.padding»
end_tag_inventory

/-- A tag with its stable name and its docstring. -/
structure Info where
  tag : Tag
  name : String
  doc : String
  deriving Repr, Inhabited

/-- `s` with every run of whitespace one space, trimmed, so a docstring fits
on one line of the inventory. -/
def oneLine (s : String) : String :=
  let (words, current) := s.toList.foldl (fun (acc : List String × List Char) c =>
    if c.isWhitespace then
      if acc.2.isEmpty then acc else (String.ofList acc.2.reverse :: acc.1, [])
    else (acc.1, c :: acc.2)) ([], [])
  let words := if current.isEmpty then words else String.ofList current.reverse :: words
  " ".intercalate words.reverse

/-- Every tag, in declaration order, with its name and its docstring on one
line. -/
def all : List Info :=
  Tag.inventory.map fun (tag, name, doc) => { tag, name, doc := oneLine doc }

/-- The stable name of a tag. -/
def Tag.name (t : Tag) : String :=
  match all.find? (·.tag == t) with
  | some i => i.name
  | none => "unknown"

-- ---------------------------------------------------------------------------
-- Conditions
-- ---------------------------------------------------------------------------

open Execution

/-- The value `x` computes on `run`, with its effects discarded; `none` when
it faults. Evaluation has no effect but a `lookahead` peek, so discarding
the run changes nothing the next step sees. -/
def peek (x : M α) (run : Run) : Option α :=
  match x.run run with
  | (.ok a, _) => some a
  | (.error _, _) => none

/-- The plain tag of a binary operator. -/
def binaryTag : BinaryOp → Tag
  | .add => .«expr.add» | .sub => .«expr.sub» | .mul => .«expr.mul»
  | .addSat => .«expr.addSat» | .subSat => .«expr.subSat»
  | .bitAnd => .«expr.bitAnd» | .bitOr => .«expr.bitOr» | .bitXor => .«expr.bitXor»
  | .shl => .«expr.shl» | .shr => .«expr.shr» | .concat => .«expr.concat»
  | .eq => .«expr.eq» | .ne => .«expr.ne»
  | .lt => .«expr.lt» | .le => .«expr.le» | .gt => .«expr.gt» | .ge => .«expr.ge»
  | .and => .«expr.and» | .or => .«expr.or»

/-- The closed behaviors of a `bit<N>` operator on its evaluated operands:
the condition of each ledger entry, not its result. -/
def bitsBehaviors (op : BinaryOp) (x y : Bits) : List Tag :=
  let n := x.width
  let otherWidth := if y.width != n then [.«expr.shift.otherWidth»] else []
  match op with
  | .add => if x.value + y.value ≥ 2 ^ n then [.«expr.add.wrap»] else []
  | .sub => if x.value < y.value then [.«expr.sub.wrap»] else []
  | .mul => if x.value * y.value ≥ 2 ^ n then [.«expr.mul.wrap»] else []
  | .addSat => if x.value + y.value > 2 ^ n - 1 then [.«expr.addSat.clamp»] else []
  | .subSat => if x.value < y.value then [.«expr.subSat.clamp»] else []
  | .shl =>
    otherWidth ++
      if y.value ≥ n then [.«expr.shl.overflow»]
      else if x.value <<< y.value ≥ 2 ^ n then [.«expr.shl.truncate»] else []
  | .shr => otherWidth ++ if y.value ≥ n then [.«expr.shr.overflow»] else []
  | _ => []

/-- The kind of an `==` or `!=` on two evaluated operands, and of every
comparison it makes inside them. A struct compares its fields and a stack
its elements by the same rule, so a header nested in either is compared by
the header rule and reports its case, as a top-level one does. A header's
own fields are part of the header rule and are not walked. -/
partial def equalityBehaviors : Value → Value → List Tag
  | .bits _, .bits _ => [.«expr.equality.bits»]
  | .bool _, .bool _ => [.«expr.equality.bool»]
  | .enum .., .enum .. => [.«expr.equality.enum»]
  | .error _, .error _ => [.«expr.equality.error»]
  | .header _ va fa, .header _ vb fb =>
    if va && vb then [.«expr.equality.header.bothValid»]
    else if va != vb then [.«expr.equality.header.validityDiffers»]
    else [.«expr.equality.header.bothInvalid»] ++
      (if fa != fb then [.«expr.equality.header.invalidFieldsDiffer»] else [])
  | .struct _ fa, .struct _ fb =>
    .«expr.equality.struct» :: (fa.zip fb).flatMap fun (a, b) => equalityBehaviors a b
  | .stack _ ea na, .stack _ eb nb =>
    [.«expr.equality.stack»] ++
      (if na != nb then [.«expr.equality.stack.nextIndexDiffers»] else []) ++
      (ea.zip eb).flatMap fun (a, b) => equalityBehaviors a b
  | _, _ => []

/-- The kind of a cast of an evaluated operand. Only the casts the ledger
names are tagged; the validator admits no other. -/
def castBehaviors : Ty → Value → List Tag
  | .bits 1, .bool _ => [.«expr.cast.boolToBits»]
  | .bits m, .bits x =>
    if m < x.width then [.«expr.cast.truncate»]
    else if m > x.width then [.«expr.cast.extend»] else [.«expr.cast.sameWidth»]
  | .boolean, .bits _ => [.«expr.cast.bitsToBool»]
  | _, _ => []

/-- Whether `name`, read in the current activation, is a block local, an
`out` parameter of the block or an `out` parameter of the running action,
holding its type's zero value: the witness of `value.uninitialized`. An
action's parameter shadows the block's name, as `Frame.read?` reads it. -/
def zeroLocal (run : Run) (name : String) : Bool :=
  let frame := run.frame
  let isZero (ty : Ty) (v : Value) : Bool :=
    match Value.zero ty run.index with
    | .ok z => v == z
    | .error _ => false
  match frame.actionVars.bind (·[name]?) with
  | some v =>
    let param? : Option Param := do
      let action ← frame.scope.actions[← frame.action]?
      action.params.find? (·.name == name)
    match param? with
    | some p => p.direction == .out && isZero p.type v
    | none => false
  | none =>
    let decl? := frame.scope.vars[name]?
    let candidate := match decl? with
      | some (.var _) => true
      | some (.param p) => p.direction == .out
      | none => false
    match decl?, frame.vars[name]? with
    | some decl, some v => candidate && isZero decl.type v
    | _, _ => false

/-- The tags of evaluating `e` on `run`, walked in evaluation order: the
case's own tag when evaluation enters it, then its operands' tags, then the
closed behaviors once the operands are known. Operands that evaluation would
skip (a short circuit, the untaken branch of a mux) or never reach (after a
fault) are not walked. -/
def exprTags (run : Run) : Expr → List Tag
  | .literal _ => [.«expr.literal»]
  | .var name => .«expr.var» :: (if zeroLocal run name then [.«value.uninitialized»] else [])
  | .member base _ =>
    .«expr.member» :: exprTags run base ++
      match peek (evaluate base) run with
      | some (.header _ false _) => [.«header.field.readInvalid»]
      | _ => []
  | .index base idx =>
    .«expr.index» :: exprTags run base ++
      match peek (evaluate base) run with
      | none => []
      | some b => exprTags run idx ++
        match b, peek (evaluate idx) run with
        | .stack _ elements _, some (.bits i) =>
          if i.value ≥ elements.length then [.«stack.index.readOutOfRange»] else []
        | _, _ => []
  | .lastIndex stack =>
    .«expr.lastIndex» :: exprTags run stack ++
      match peek (evaluate stack) run with
      | some (.stack _ _ 0) => [.«stack.lastIndex.empty»]
      | _ => []
  | .unary op operand =>
    let tag : Tag := match op with
      | .not => .«expr.not» | .complement => .«expr.complement» | .negate => .«expr.negate»
    tag :: exprTags run operand
  | .binary op left right =>
    let own := binaryTag op :: exprTags run left
    match peek (evaluate left) run with
    | none => own
    | some l =>
      match op, l with
      | .and, .bool false => own ++ [.«expr.and.shortCircuit»]
      | .or, .bool true => own ++ [.«expr.or.shortCircuit»]
      | _, _ =>
        let both := own ++ exprTags run right
        match peek (evaluate right) run with
        | none => both
        | some r =>
          both ++ match op, l, r with
            | .eq, _, _ | .ne, _, _ => equalityBehaviors l r
            | _, .bits x, .bits y => bitsBehaviors op x y
            | _, _, _ => []
  | .cast to operand =>
    .«expr.cast» :: exprTags run operand ++
      match peek (evaluate operand) run with
      | some v => castBehaviors to v
      | none => []
  | .slice operand _ _ => .«expr.slice» :: exprTags run operand
  | .isValid header => .«expr.isValid» :: exprTags run header
  | .mux condition thenBranch otherwise =>
    .«expr.mux» :: exprTags run condition ++
      match peek (evaluate condition) run with
      | some (.bool true) => exprTags run thenBranch
      | some (.bool false) => exprTags run otherwise
      | _ => []
  | .lookahead ty =>
    let kind : List Tag := match ty with
      | .bits _ => [.«expr.lookahead.bits»]
      | .boolean => [.«expr.lookahead.bool»]
      | .header _ => [.«expr.lookahead.header»]
      | _ => []
    let short : List Tag := match run.packet, widthOf ty run.index with
      | some p, .ok w => if w > p.remainingBits then [.«expr.lookahead.tooShort»] else []
      | _, _ => []
    .«expr.lookahead» :: kind ++ short

/-- The tags of reading an lvalue, as `readLValue` walks it. -/
def readTags (run : Run) : LValue → List Tag
  | .var _ => []
  | .member base _ =>
    readTags run base ++
      match peek (readLValue base) run with
      | some (.header _ false _) => [.«header.field.readInvalid»]
      | _ => []
  | .index base idx =>
    readTags run base ++ exprTags run idx ++
      match peek (readLValue base) run, peek (evaluate idx) run with
      | some (.stack _ elements _), some (.bits i) =>
        if i.value ≥ elements.length then [.«stack.index.readOutOfRange»] else []
      | _, _ => []
  | .next _ => []

/-- The closed behaviors of writing through `lv`, as `writeLValue` recurses:
a field of an invalid header, and a stack index past the end, where the
recursion stops because the write does nothing. -/
def writeBehaviors (run : Run) : LValue → List Tag
  | .var _ => []
  | .member base _ =>
    readTags run base ++
      (match peek (readLValue base) run with
        | some (.header _ false _) => [.«header.field.writeInvalid»]
        | _ => []) ++
      writeBehaviors run base
  | .index base idx =>
    readTags run base ++ exprTags run idx ++
      match peek (readLValue base) run, peek (evaluate idx) run with
      | some (.stack _ elements _), some (.bits i) =>
        if i.value ≥ elements.length then [.«stack.index.writeOutOfRange»]
        else writeBehaviors run base
      | _, _ => []
  | .next _ => []

/-- The tags of a write through `lv`: its top case, then its behaviors. -/
def writeTags (run : Run) (lv : LValue) : List Tag :=
  let top : List Tag := match lv with
    | .var _ => [.«lvalue.var»]
    | .member .. => [.«lvalue.member»]
    | .index .. => [.«lvalue.index»]
    | .next _ => []
  top ++ writeBehaviors run lv

/-- The variable paths an expression reads, for the copy-in overlap witness. -/
def exprPath? : Expr → Option (List String)
  | .var name => some [name]
  | .member base field => (· ++ [field]) <$> exprPath? base
  | .index base _ => exprPath? base
  | _ => none

/-- The variable path an lvalue names, stack indices dropped. -/
def lvaluePath : LValue → List String
  | .var name => [name]
  | .member base field => lvaluePath base ++ [field]
  | .index base _ => lvaluePath base
  | .next stack => lvaluePath stack

/-- Whether an `in` argument of a call reads storage an `out` or `inout`
argument writes: one path is a prefix of the other. -/
def overlaps (params : List Param) (args : List Arg) : Bool :=
  let pairs := params.zip args
  let written := pairs.filterMap fun (p, a) =>
    match a with
    | .lvalue lv => if p.direction == .out || p.direction == .inout then some (lvaluePath lv) else none
    | .expr _ => none
  let read := pairs.filterMap fun (p, a) =>
    match a with
    | .expr e => if p.direction == .«in» then exprPath? e else none
    | .lvalue _ => none
  read.any fun r => written.any fun w => r.isPrefixOf w || w.isPrefixOf r

/-- The direction tag of a parameter. -/
def directionTag : Direction → Tag
  | .«in» => .«call.param.in»
  | .out => .«call.param.out»
  | .inout => .«call.param.inout»
  | .none => .«call.param.none»

/-- The tags of entering a call with `params` bound to `args`: each
parameter's direction, the arguments evaluated for `in` and read for
`inout`, and the copy-in overlap witness. -/
def entryTags (run : Run) (params : List Param) (args : List Arg) : List Tag :=
  let perArg := (params.zip args).flatMap fun (p, a) =>
    directionTag p.direction ::
      if p.direction == .out then []
      else match a with
        | .expr e => exprTags run e
        | .lvalue lv => readTags run lv
  perArg ++ (if overlaps params args then [.«call.copyIn.overlap»] else [])

/-- The tags of writing `lvalues` back, in order, into `run`: each write as
`writeTags` classifies it. Every copy-back goes through here: an action's
or a block's `out` and `inout` arguments, and an extern call's results and
return value.

It assumes the lvalues are already resolved: every index inside them is a
literal fixed at copy-in, as P4 resolves an argument once (§6.8). Then the
tags of one write depend only on its lvalue and the storage it lands in,
and the writes of one call land in disjoint storage, which the validator's
alias rule guarantees, so classifying them all against `run` is exact.

Today the interpreters resolve each lvalue again when it is written
(ledger: Copy-back target), after the earlier writes of the same call. An
index read from a variable that an earlier write of the same call changes
then names a different element here from the one written, and that
lvalue's tags, `stack.index.writeOutOfRange` and
`header.field.writeInvalid` among them, describe the wrong element. The
classification makes no attempt to replay the earlier writes. -/
def writeBackTags (run : Run) (lvalues : List LValue) : List Tag :=
  lvalues.flatMap (writeTags run)

/-- The lvalues of the `out` and `inout` arguments of a call, in parameter
order. -/
def writtenArgs (params : List Param) (args : List Arg) : List LValue :=
  (params.zip args).filterMap fun (p, a) =>
    match a with
    | .lvalue lv => if p.direction == .out || p.direction == .inout then some lv else none
    | .expr _ => none

/-- The tags of copying `out` and `inout` arguments back into `run`, in
parameter order. -/
def copyBackTags (run : Run) (params : List Param) (args : List Arg) : List Tag :=
  let written := writtenArgs params args
  writeBackTags run written ++
    (if written.length ≥ 2 then [.«call.copyOut.order»] else [])

/-- The tags of emitting an evaluated value, as `emitValue` recurses. -/
partial def emitTags : Value → List Tag
  | .header _ true _ => [.«emit.header.valid»]
  | .header _ false _ => [.«emit.header.invalid»]
  | .struct _ fields => .«emit.struct» :: fields.flatMap emitTags
  | .stack _ elements _ => .«emit.stack» :: elements.flatMap emitTags
  | _ => []

/-- The width of header type `name`, when the index knows it. -/
def headerWidth? (run : Run) (name : String) : Option Nat :=
  match widthOf (.header name) run.index with
  | .ok w => some w
  | .error _ => none

/-- The tags of an extract into `target`, in the order `extract` checks. -/
def extractTags (run : Run) (target : LValue) : List Tag :=
  let remaining := (run.packet.map (·.remainingBits)).getD 0
  match target with
  | .next stack =>
    .«parser.extract.next» :: readTags run stack ++
      match peek (readLValue stack) run with
      | some (.stack t elements nextIndex) =>
        let short : Bool := match headerWidth? run t with
          | some w => w > remaining
          | none => false
        if nextIndex ≥ elements.length then
          .«parser.extract.next.full» :: (if short then [.«parser.extract.next.fullAndShort»] else [])
        else if short then [.«parser.extract.tooShort»]
        else if headerWidth? run t == some 0 then [.«parser.extract.zeroWidth»] else []
      | _ => []
  | _ =>
    .«parser.extract.header» :: readTags run target ++
      match peek (readLValue target) run with
      | some (.header t _ _) =>
        match headerWidth? run t with
        | some w =>
          if w > remaining then [.«parser.extract.tooShort»]
          else
            let outOfRange := (writeTags run target).contains .«stack.index.writeOutOfRange»
            (if w == 0 then [.«parser.extract.zeroWidth»] else []) ++
              (if outOfRange then [.«parser.extract.indexOutOfRange»] else []) ++
              writeTags run target
        | none => []
      | _ => []

/-- Whether a statement list assigns `lv` at any depth of `if`. -/
partial def assigns (lv : LValue) : List Stmt → Bool
  | [] => false
  | s :: ss =>
    (match s with
      | .assign target _ => target == lv
      | .conditional _ t o => assigns lv t || assigns lv o
      | _ => false) || assigns lv ss

/-- The tags of one statement, from the configuration before it runs. -/
def stmtTags (run : Run) : Stmt → List Tag
  | .assign target value =>
    .«stmt.assign» :: exprTags run value ++
      match peek (evaluate value) run with
      | some v =>
        writeTags run target ++
          match v with
          | .header _ false _ => [.«header.assign.invalid»]
          | _ => []
      | none => []
  | .conditional condition _ _ =>
    .«stmt.conditional» :: exprTags run condition ++
      match peek (evaluate condition) run with
      | some (.bool true) => [.«stmt.conditional.then»]
      | some (.bool false) => [.«stmt.conditional.otherwise»]
      | _ => []
  | .apply .. => [.«stmt.apply»]
  | .callAction .. => [.«stmt.callAction»]
  | .callBlock block _ =>
    .«stmt.callBlock» ::
      match run.index.blocks[block]? with
      | some b => if b.kind == .parser then [.«parser.subparser»] else []
      | none => []
  | .callExtern inst method args result =>
    let decl? : Option Method := do
      let i ← run.index.externInstances[inst]?
      let t ← run.index.externTypes[i.externType]?
      t.methods.find? (·.name == method)
    .«stmt.callExtern» :: .«call.extern» ::
      match decl? with
      | none => []
      | some decl =>
        -- The results are written in parameter order, then the return value.
        let outs := writtenArgs decl.params args
        entryTags run decl.params args ++ writeBackTags run (outs ++ result.toList) ++
          (if outs.isEmpty then [] else [Tag.«call.extern.out»]) ++
          (if outs.length ≥ 2 then [Tag.«call.copyOut.order»] else []) ++
          (if result.isSome then [Tag.«call.extern.result»] else [])
  | .setValid header =>
    .«stmt.setValid» :: readTags run header ++
      match peek (readLValue header) run with
      | some (.header _ true _) => [.«header.setValid.alreadyValid»] ++ writeTags run header
      | some _ => writeTags run header
      | none => []
  | .setInvalid header =>
    .«stmt.setInvalid» :: readTags run header ++
      match peek (readLValue header) run with
      | some (.header _ false _) => [.«header.setInvalid.alreadyInvalid»] ++ writeTags run header
      | some _ => writeTags run header
      | none => []
  | .push stack count =>
    .«stmt.push» :: readTags run stack ++
      match peek (readLValue stack) run with
      | some (.stack _ elements nextIndex) =>
        (if nextIndex + count > elements.length then [.«stack.push.clamp»] else []) ++
          (if count > elements.length then [.«stack.push.oversize»] else []) ++
          writeTags run stack
      | _ => []
  | .pop stack count =>
    .«stmt.pop» :: readTags run stack ++
      match peek (readLValue stack) run with
      | some (.stack _ elements nextIndex) =>
        (if count > nextIndex then [.«stack.pop.clamp»] else []) ++
          (if count > elements.length then [.«stack.pop.oversize»] else []) ++
          writeTags run stack
      | _ => []
  | .extract target => .«stmt.extract» :: extractTags run target
  | .advance bits =>
    .«stmt.advance» :: exprTags run bits ++
      match peek (evaluate bits) run, run.packet with
      | some (.bits n), some p => if n.value > p.remainingBits then [.«parser.advance.tooShort»] else []
      | _, _ => []
  | .verify condition error =>
    .«stmt.verify» :: exprTags run condition ++
      match peek (evaluate condition) run with
      | some (.bool true) => [.«parser.verify.pass»]
      | some (.bool false) =>
        .«parser.verify.fail» :: (if error == "NoError" then [.«parser.verify.failNoError»] else [])
      | _ => []
  | .emit value =>
    .«stmt.emit» :: exprTags run value ++
      match peek (evaluate value) run with
      | some v => emitTags v
      | none => []

/-- The key-set kind of a select case entry. -/
def keySetTag : KeySet → Tag
  | .exact _ => .«select.exact»
  | .masked .. => .«select.masked»
  | .range .. => .«select.range»
  | .dontCare => .«select.dontCare»

/-- The tags of a select: its keys walked in order, then the kinds of the
case that `keySetMatches` picks, whether a later case also matches, or
`NoMatch`. -/
def selectTags (run : Run) (keys : List Expr) (cases : List SelectCase) : List Tag :=
  let keyTags := keys.flatMap (exprTags run)
  let multi : List Tag := if keys.length ≥ 2 then [.«select.multiKey»] else []
  match peek (keys.mapM evaluate) run with
  | none => keyTags ++ multi
  | some values =>
    let nonBits : List Tag :=
      if values.any (fun v => match v with | .bits _ => false | _ => true)
      then [.«select.nonBitsKey»] else []
    let matching := cases.filter fun c =>
      c.sets.length == values.length &&
        (peek ((c.sets.zip values).allM fun (ks, k) => keySetMatches ks k) run == some true)
    let taken : List Tag := match matching with
      | [] => [.«select.noMatch»]
      | [c] => c.sets.map keySetTag
      | c :: _ => c.sets.map keySetTag ++ [.«select.firstOfSeveral»]
    keyTags ++ multi ++ nonBits ++ taken

/-- What the observer knows about a request beyond the machine it steps. -/
structure Context where
  /-- The tables, as `(block, table)`, whose default action the host set in
  its entries, whatever action it set. -/
  hostDefaults : List (String × String) := []
  deriving Inhabited

/-- The tags of a table apply: its key kinds and key expressions, then hit or
miss as the real `Installed.lookup` reports, and the conditions of the
longest-prefix and priority rules over the entries that `keyValueMatches`.
The write of `hit` is its own step, `writeHit`, classified there. -/
def tableTags (ctx : Context) (run : Run) (name : String) (hit : Option LValue) : List Tag :=
  let frame := run.frame
  match frame.scope.tables[name]? with
  | none => []
  | some table =>
    let kinds := table.keys.map fun k => match k.matchKind with
      | .exact => Tag.«table.key.exact»
      | .lpm => .«table.key.lpm»
      | .ternary => .«table.key.ternary»
    let keyTags := table.keys.flatMap fun k => exprTags run k.expr
    let outcome : List Tag :=
      match peek (table.keys.mapM fun k => do expectBits (← evaluate k.expr)) run, run.entries with
      | some keys, some installed =>
        let ref := (frame.block.name, table.name)
        match installed.lookup ref keys with
        | .error _ => []
        | .ok m =>
          let entries := (installed.entries.getD ref #[]).toList
          let matching := entries.filter fun e =>
            (e.keys.zip keys).all fun (kv, k) => Installed.keyValueMatches kv k
          let ternary := table.keys.any (·.matchKind == .ternary)
          let lengths := matching.map Installed.prefixLength
          let behaviors : List Tag :=
            (if table.keys.any (·.matchKind == .lpm) && lengths.eraseDups.length ≥ 2
              then [.«table.lpm.longest»] else []) ++
            (if ternary && matching.length ≥ 2 then [.«table.ternary.priority»] else []) ++
            (if ternary && matching.any (·.priority == 0) then [.«table.ternary.priorityZero»] else []) ++
            (if matching.any table.constEntries.contains then [.«table.constEntry»] else [])
          let overwritten : List Tag := match hit, m.action with
            | some lv, some call =>
              match frame.scope.actions[call.action]? with
              | some a => if assigns lv a.body then [.«table.hit.overwritesAction»] else []
              | none => []
            | _, _ => []
          behaviors ++ overwritten ++
            if m.hit then [.«table.hit»]
            else
              -- A declared `NoAction` is empty (ledger: Table miss), so it
              -- is the same miss as no default at all.
              let noAction := match installed.defaults.getD ref none with
                | none => true
                | some call => call.action == "NoAction"
              .«table.miss» ::
                (if noAction then [.«table.miss.noAction»] else [.«table.miss.defaultAction»]) ++
                (if ctx.hostDefaults.contains ref then [.«table.miss.hostDefault»] else [])
      | _, _ => []
    kinds ++ keyTags ++ outcome

/-- Whether a block return is pending below the current work item, so that
the item runs inside a called sub-block. In a parser that is a sub-parser. -/
def insideCall (rest : List Work) : Bool :=
  rest.any fun w => match w with | .blockReturn .. => true | _ => false

/-- The tags of entering a parser state: a revisit after progress, or the
revisit rule's timeout, inside a sub-parser when a block return is pending
below. -/
def stateTags (run : Run) (state : State) (rest : List Work) : List Tag :=
  let key := (run.frame.block.name, state.name)
  match run.packet, run.visits[key]? with
  | some p, some cursor =>
    if cursor == p.cursor then
      .«parser.timeout» :: (if insideCall rest then [.«parser.timeout.subparser»] else [])
    else [.«parser.revisit»]
  | _, _ => []

/-- The tags of a transition: its case, then where the real `transition`
goes, and an explicit `reject` inside a sub-parser. A `verify` that raises
`NoError` rejects the same way but is not a transition, so it is not an
explicit `reject`. -/
def transitionTags (run : Run) (trans : Transition) (rest : List Work) : List Tag :=
  let own : List Tag := match trans with
    | .direct _ => [.«parser.transition.direct»]
    | .select keys cases => .«parser.transition.select» :: selectTags run keys cases
  own ++
    match peek (P4bloIR.transition trans) run with
    | some (.state _) => [.«parser.target.state»]
    | some .accept => [.«parser.target.accept»]
    | some .reject =>
      .«parser.target.reject» :: (if insideCall rest then [.«parser.subparser.reject»] else [])
    | none => []

/-- The tags of the work item `task` about to be dispatched on `run`, with the
pending fault and the rest of the continuation stack. -/
def workTags (ctx : Context) (run : Run) (fault : Option Fault) (rest : List Work) :
    Work → List Tag
  | .statements _ => []
  | .statement stmt => stmtTags run stmt
  | .table name hit => tableTags ctx run name hit
  | .writeHit target _ =>
    match target with
    | some lv => .«table.hit.written» :: writeTags run lv
    | none => []
  | .tableAction call =>
    .«call.tableAction» :: (if call.args.isEmpty then [] else [.«call.param.none»])
  | .action name args =>
    .«call.action» :: (if run.frame.action.isSome then [.«call.action.nested»] else []) ++
      match run.frame.scope.actions[name]? with
      | some a => entryTags run a.params args
      | none => []
  | .actionReturn outer copy =>
    match copy with
    | some (params, args) =>
      -- `dispatch` restores the caller's action layer before the copyback,
      -- so the argument names resolve in the caller, not in the callee.
      let caller := { run.frame with action := outer.action, actionVars := outer.actionVars }
      copyBackTags { run with frame := caller } params args
    | none => []
  | .block name args =>
    .«call.block» ::
      match run.index.blocks[name]? with
      | some b => entryTags run b.params args
      | none => []
  | .blockReturn caller params args =>
    -- The copyback runs in the caller's activation.
    copyBackTags { run with frame := caller } params args ++
      if fault.isSome then [.«call.block.faultCopyBack»] else []
  | .runBlock _ | .states _ => []
  | .state _ state => stateTags run state rest
  | .transition _ trans => transitionTags run trans rest

/-- The tags of the step the machine is about to take. A task skipped while
a fault unwinds exercises nothing, exactly as `step` skips it.

Tags are not withdrawn when the step faults. A step's tags name the rules it
starts to apply, and for every statement that can fault in a validated
program, the parser's, the tags classify the fault condition itself, as
`parser.extract.tooShort` does; withdrawing them would lose exactly those.
A step that faults for a reason no tag names keeps the tags it started
with: an extern binding that fails still reports `call.extern.out`. A
validated control has no such fault today. -/
def classify (ctx : Context) (m : Machine) : List Tag :=
  match m.work with
  | [] => []
  | task :: rest =>
    if m.fault.isSome && !task.handlesFault then []
    else workTags ctx m.run m.fault rest task

/-- The tags of a finished run: the deparser's zero padding when the emitted
bits are not whole bytes (docs/ir-semantics.md, "Bit alignment"). -/
def finalTags (run : Run) : List Tag :=
  match run.emitter with
  | some e => if e.width % 8 != 0 then [.«emit.padding»] else []
  | none => []

end Coverage

end P4bloIR
