# Coverage

Every construct of P4's core, walked in the order of P4-SpecTec's
elaborated IL, with a status for each.

## How to read this

The checklist is SpecTec's IL after instantiation, minus the
architecture layer. That is: every production of
`spec/4-p4-ir/4.0-ir-syntax.watsup` and of the type grammar
`spec/2-static-runtime/2.2.1-type.watsup`, as of P4-SpecTec `2730cfd9`
(the pinned oracle), with packages, package instantiation and the
architecture's interface types set aside as the design directs. The IL
reuses the surface operator sets from `spec/1-p4-surface/1-syntax.watsup`
(`unop`, `binop`, `sliceop`, `assignop`, `literalExpression`); those rows
cite the surface name. Every row names its production. A production
with several alternatives that get different statuses is split into
one row per alternative.

Each row has one of these statuses.

- **in**: a message or field of `spec/ir/proto/p4blo/v0/p4blo.proto` is the
  construct itself. The column names it.
- **elaborated**: the frontend rewrites the construct into in-constructs
  and its meaning survives. The column names the rewrite, and every
  rewrite here is one the project has performed or ruled on: an entry
  in `.agents/decisions.md`, a rule in [ir-semantics.md](ir-semantics.md)
  or the schema, an elaboration a corpus README records, or one the IL
  bridge performs (below).
- **excluded**: nothing in the IR represents the construct. The
  category is the design's ([design.md](design.md#scope)):
  - *by thesis*: architecture-dependent;
  - *by elaboration*: sugar the frontend removes. The rewrite is not
    one the project has performed yet, so only the category is asserted;
    where the prior-art survey names a p4c pass, the note cites it as a
    precedent, not a decision;
  - *by scope*: a feature left out of v0 that threatens no claim, and
    an additive change if wanted.
- **undecided**: no design category applies without a ruling. These are
  collected under [Open rows](#open-rows).

The difference between *elaborated* and *excluded by elaboration* is
evidence, not kind: both are removed by the frontend, but only the first
has a named rewrite somebody has done.

Columns: IL construct (production) | status | p4blo form or elaboration
| note | bridge. A row whose status cell points at another section is a
cross-reference, not a row, and is not counted.

The last column says what the IL bridge, `p4blo.frontend`, does with the
construct when it translates P4-SpecTec's typed and instantiated IL into
IR (see [design.md](design.md#printer-and-oracles)): *translated* for an
in-row; *performed* when it carries out the row's elaboration, *partial*
when it does so for the cases named; *refused by name* when it raises an
error naming the row; *not attempted* when the IR could hold the construct
and the bridge does not yet translate it; *unreachable* when the bridge has
code for it that nothing it translates can reach. Where the bridge performs the
rewrite of a row that was *excluded, by elaboration*, the row is now
*elaborated*, since the rewrite has been performed; fourteen rows moved on
2026-09-24 for that reason alone, and their notes are unchanged. The
bridge's claims are checked on the corpus by
`tests/external/test_frontend_spectec.py`; it is not a verified frontend.

## Types

Productions from `2.2.1-type.watsup`.

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `voidTypeIR` (`VOID`) | elaborated | `Method.returns` absent | Schema: "Absent for a method that returns nothing." Actions and blocks return nothing by construction. | performed |
| `boolTypeIR` (`BOOL`) | in | `Type.boolean` | | translated |
| `errorTypeIR` (`ERROR`) | in | `Type.error` | Values are names from `BlockLibrary.errors`. | translated |
| `matchKindTypeIR` (`MATCH_KIND`) | elaborated | the `MatchKind` enum on `Key` | No value of this type exists in the IR. See `matchKindDeclarationIR`. | performed; a value of type `match_kind` is not attempted |
| `stringTypeIR` (`STRING`) | excluded, by scope | none | Reaches only annotations and extern arguments such as `log_msg`. The survey recommends exclusion; nothing rules. | refused by name |
| `intTypeIR` (`INT`) | elaborated | none | Design: no `int`. Its literals are sized by context; see `literalExpressionIR`. | performed: folded into sized literals; an `int` value that reaches the IR is refused |
| `fixedIntTypeIR` (`INT<n>`) | excluded, by scope | none | Decision: `int<N>` out for v0. One more `Type` kind and a signed variant of each arithmetic rule when wanted. | refused by name |
| `fixedBitTypeIR` (`BIT<n>`) | in | `Type.bits` | `N >= 1`. | translated |
| `varBitTypeIR` (`VARBIT<n>`) | excluded, by scope | none | Design. `HeaderTooShort` stays reserved in the error list so indices agree. | refused by name |
| `nameTypeIR` (`_NAME typeId`) | in | `Type.header`, `Type.struct`, `Type.enum_type` | A reference by name; the validator resolves it once. | translated |
| `typedefTypeIR` (`TYPEDEF`) | elaborated | replaced by its definition | Forwarder README: `macAddr_t`, `ip4Addr_t`, `egressSpec_t` are 48, 32, 9. | performed |
| `newTypeIR` (`TYPE`, P4 `type`) | elaborated | its underlying type, as typedef (p4c `EliminateNewtype`) | Nothing rules on it. The typedef route is available (p4c `EliminateNewtype`); a newtype only forbids implicit casts, which is a typing fact. | performed |
| `listTypeIR`, `tupleTypeIR` | excluded, by elaboration | none | Design: no tuples. The one list the corpus met, a checksum field list, became a concatenation; see `sequenceExpressionIR`. | partial: a hash or checksum field list, as `sequenceExpressionIR` as an extern argument; otherwise refused |
| `arrayTypeIR` (`ARRAY t[n]`) | excluded, by scope | none | SpecTec's fixed-size array over a non-header element. P4 surface syntax reaches it only through header stacks. Likely by scope; nothing rules. | refused by name |
| `headerStackTypeIR` | in | `Type.stack` (`StackType`) | Element must be a header. A stack of header unions goes with unions. | translated |
| `structTypeIR` | in | `StructType` | Fields of any type. Type arguments: see `typeArgumentIR`. | translated |
| `headerTypeIR` | in | `HeaderType` | Fields are bits or bool. | translated |
| `headerUnionTypeIR` | excluded, by scope | none | Design. | refused by name |
| `simpleEnumTypeIR` | in | `EnumType` | | translated |
| `serializableEnumTypeIR` (with `valueFieldIR`) | elaborated | `bit<N>` and `BitsLiteral` | Schema: "Serializable enums are elaborated to bits and literals." Casts among them become the IR's three casts (ir-semantics.md, Casts). | performed |
| `externObjectTypeIR` | in | `ExternType` | Monomorphic. Decision: one `ExternType` per instantiation (`register`, `register.16`); `externMethodTypeDefEnv` is `Method`. | translated for v1model's `register` and `counter`; other extern objects not attempted |
| `parserObjectTypeIR`, `controlObjectTypeIR` | in | `Block.kind` and `Block.params` | A P4 deparser is a control; here it is a third kind with its own statement set. | translated |
| `packageObjectTypeIR` | excluded, by thesis | `Export` names the role | Design: the architecture is outside; SpecTec's `7-instantiation` and `9-arch`. | V1Switch bound by the v1model shim in reverse (`p4blo.frontend.v1model`); other packages refused |
| `tableObjectTypeIR` | in | `Table` | Its result struct: see `tableMetadataStructTypeIR`. | translated |
| `typeArgumentIR`, type arguments on `STRUCT`, `HEADER`, `EXTERN`, `PARSER`, `CONTROL` | excluded, by elaboration | none | Design: no generics. Every IR type is concrete. | refused by name |
| `defaultTypeIR` (`DEFAULT`) | excluded, by elaboration | none | Type of `...`; see `defaultExpressionIR`. | refused by name |
| `invalidHeaderTypeIR` (`HEADER_INVALID`) | excluded, by elaboration | none | Type of `{#}`; see `invalidHeaderExpressionIR`. | refused by name |
| `sequenceTypeIR`, `recordTypeIR` | excluded, by elaboration | none | Types of initializer expressions; see `sequenceExpressionIR`, `recordExpressionIR`. | partial: header and struct initializers, with `sequenceExpressionIR`; otherwise refused |
| `setTypeIR` (`SET<t>`) | elaborated | none | Type of keyset expressions. Keysets are the constants `KeySet` and `KeyValue`. | performed: a keyset's element is read at the key's type |
| `tableMetadataEnumTypeIR` (`TABLE_ENUM`) | elaborated | with `switchStatementIR` on `action_run` | See the table section. | performed |
| `tableMetadataStructTypeIR` (`TABLE_STRUCT`) | elaborated | `HIT` is `Apply.hit`; `MISS` and `ACTION_RUN` are rewritten | See the table section for each field. | performed |

## Expressions

Productions from `4.0-ir-syntax.watsup`; operator sets from
`1-syntax.watsup`.

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `typedExpressionIR`, `expressionNoteIR` (`typeIR ctk`) | elaborated | `Expr` carries no note | Decision: no type annotations on expressions; the validator computes each type once. `ctk` is a typing fact. | performed: the note is dropped; `ctk` decides only what is folded |
| `literalExpressionIR`: `TRUE`, `FALSE` | in | `Literal.boolean` | | translated |
| `literalExpressionIR`: `nat W int` | in | `Literal.bits` (`BitsLiteral{width, value}`) | Decimal in `[0, 2^width)`. | translated |
| `literalExpressionIR`: `D int` (unsized) | elaborated | sized by the other operand, the target or the key | Forwarder, stacks, subparser_stack, stateful and csum16 READMEs. SpecTec's `Cast_impl_neq/fixBit` is the same step. | performed |
| `literalExpressionIR`: `nat S int` (signed) | excluded, by scope | none | With `int<N>`. | refused by name |
| `literalExpressionIR`: `stringLiteral` | excluded, by scope | none | With `stringTypeIR`. | refused by name |
| `referenceExpressionIR` (`prefixedNameIR`: `_BARE`, `.`) | in | `Expr.var`; every reference is a scoped name | Schema: scopes are P4's and the validator resolves every name once. The `.` prefix is a resolution fact the validator recomputes. | translated |
| `defaultExpressionIR` (`...`) | excluded, by elaboration | none | Design: "other sugar the frontend removes." Precedent: p4c `DefaultValues`. | refused by name |
| `unaryExpressionIR` with `!`, `~`, `-` | in | `Unary` NOT, COMPLEMENT, NEGATE | Negation wraps modulo `2^N`. | translated |
| `unaryExpressionIR` with `+` | elaborated | the operand | Identity. | performed |
| `binaryExpressionIR` with `+ - * \|+\| \|-\| & \| ^ << >> ++ == != < <= > >= && \|\|` | in | `Binary` | ir-semantics.md: wrapping, saturating, shift by width or more, unsigned comparison, equality on every type, short-circuit. | translated |
| `binaryExpressionIR` with `/`, `%` | elaborated | folded | ir-semantics.md: P4 defines them only on compile-time constants, which the frontend folds. | performed when both operands are compile-time known; otherwise not representable, reported as not attempted |
| `ternaryExpressionIR` (`e ? e : e`) | in | `Mux` | Same type on both branches. | translated; a branch with a call becomes an `If` into a fresh local, since only the chosen branch runs |
| `castExpressionIR` | in | `Cast` | Three pairs: bits to bits, bool to `bit<1>`, `bit<1>` to bool. Every other P4 cast is elaborated into these (ir-semantics.md, Casts). Implicit casts are already explicit in the IL (`$apply_cast`), so they have no row. | translated; a cast between types that translate alike is dropped |
| `invalidHeaderExpressionIR` (`{#}`) | excluded, by elaboration | none | Design: other sugar. Precedent: p4c `EliminateInvalidHeaders`, into `SetInvalid`. | refused by name |
| `sequenceExpressionIR` as an extern argument | elaborated | concatenation of the fields, in order | Forwarder and csum16 READMEs: `update_checksum`'s field list becomes one `bit<144>` or `bit<16>` argument. | performed: `hash` and `update_checksum` data |
| `sequenceExpressionIR`, `recordExpressionIR` elsewhere (with `namedExpressionIR`, `...`) | excluded, by elaboration | none | Design: no tuples, other sugar. Precedents: p4c `EliminateTuples`, `StructInitializers`. | partial: a header or struct initializer is a fresh local assigned field by field (p4c `StructInitializers`); elsewhere refused |
| `errorAccessExpressionIR` (`error.X`) | in | `Literal.error` | | translated |
| `memberAccessExpressionIR`: field of a header or struct | in | `Member` | Reading a field of an invalid header is closed in ir-semantics.md. | translated |
| `memberAccessExpressionIR`: `TYPE name . member` (enum member) | in | `Literal.enum_member` | | translated |
| `memberAccessExpressionIR`: `hs.lastIndex` | in | `LastIndex` | `bit<32>`; parser-only in P4, and `nextIndex == 0` closed in ir-semantics.md (`hs.lastIndex`). | translated |
| `memberAccessExpressionIR`: `hs.last` | elaborated | `Index(hs, LastIndex(hs))` | Parser-only in P4. Faithful when the stack is non-empty; on `nextIndex == 0` P4-SpecTec raises `StackOutOfBounds` where the elaborated form reads a zero invalid header, a listed deviation (ir-semantics.md, `hs.last` on an empty stack). Stacks and subparser_stack READMEs use it. | performed |
| `memberAccessExpressionIR`: `hs.next` | in | `LValue.next` | Parser only, as the target of an extract. | translated |
| `memberAccessExpressionIR`: `hs.size` | elaborated | the constant `StackType.size` | Compile-time known. | performed |
| `callExpressionIR`: size methods (`minSizeInBits`, `minSizeInBytes`, `maxSizeInBits`, `maxSizeInBytes`) | excluded, by elaboration | the constant | Compile-time known, as `hs.size`: P4 defines them on types and header values whose sizes are fixed. | not attempted |
| `memberAccessExpressionIR`: `t.apply().hit`, `.miss`, `.action_run` | see the table section | | | |
| `indexAccessExpressionIR` (`hs[e]`) | in | `Index` | Run-time index; out of range closed in ir-semantics.md. | translated |
| `sliceAccessExpressionIR` with `sliceop` `:` | in | `Slice{hi, lo}` | Bounds are constants; the validator checks `lo <= hi < N`. | translated |
| `sliceAccessExpressionIR` with `sliceop` `+:` | elaborated | `[lo + w - 1 : lo]` | P4 1.2.5's `e[lo +: w]`; both operands are compile-time known. | performed |
| `callExpressionIR`: extern method in expression position | elaborated | `CallExtern.result` into a fresh local | Schema: "The IR has no discarded results; the frontend introduces a local." | unreachable: neither object the bridge binds, v1model's `register` and `counter`, has a method that returns a value; the code would guard the call by an `If` under `&&`, `\|\|` or `?:` |
| `callExpressionIR`: `h.isValid()` | in | `IsValid` | Decision: dedicated packet and header nodes. | translated |
| `callExpressionIR`: `packet.lookahead<T>()` | in | `Lookahead{type}` | Parser only. | translated; in statement position its value goes to a fresh local, since it can still reject |
| `callExpressionIR`: `packet.length()` | excluded, by scope | none | Declared in core.p4's `packet_in`; no design list names it and no corpus program uses it. | refused by name |
| `callExpressionIR`: `t.apply()` in expression position | see the table section | | | |
| `callExpressionIR`: `constructorTargetIR ( args )` | see `instantiationIR` | | | |
| `callExpressionIR`: call of a `functionDeclarationIR` | elaborated | inlined at the call site (p4c `InlineFunctions`) | With `functionDeclarationIR`. | partial: inlined when the only `return` is the last statement; an earlier `return` is not attempted |
| `callableTargetIR`: `TYPE name . method` (static extern method) | excluded, by scope | none | Nothing rules; the IR calls methods on instances only. | refused by name |
| `callExpressionIR`: `< typeArgumentListIR >` on a call | excluded, by elaboration | none | Design: no generics. | refused by name |
| `parenthesizedExpressionIR` | elaborated | none | A tree has no parentheses. | performed |
| `argumentIR`: positional `e` | in | `Arg.expr` for `in`; `Arg.lvalue` for `out` and `inout` | Copy-in, copy-out in parameter order; aliasing is a validator error (ir-semantics.md, Block calls). | translated; an `in` argument overlapping an `out` one, and an `out` argument aliasing another, go through fresh locals (copy-in, copy-out) |
| `argumentIR`: `name = e`, `name = _`, `_` | elaborated | positional order; a `_` out-argument to a fresh local | Design: other sugar. Precedents: p4c `OrderArguments`, `RemoveDontcareArgs`. | performed; `_` for an `out` parameter is a fresh local |
| `lvalueIR`: `referenceExpressionIR` | in | `LValue.var` | | translated |
| `lvalueIR`: `typedLvalueIR . name` | in | `LMember` | | translated |
| `lvalueIR`: `typedLvalueIR [ e ]` | in | `LIndex` | | translated |
| `lvalueIR`: `typedLvalueIR [ e sliceop e ]` | elaborated | read-modify-write of the whole field, `f = (f & ~mask) \| (v << lo)` | Decision: slice lvalues are elaborated, not added. Stacks README gives the formula. | performed, also for a slice passed as an `out` argument; a slice of a slice is not attempted |
| `lvalueIR`: `( typedLvalueIR )`; `lvalueNoteIR` | elaborated | none | As for expressions. | performed |
| `simpleKeysetExpressionIR`: `e` | in | `KeySet.exact` in a select; `KeyValue.exact` in an entry | A constant of the key's type. | translated |
| `simpleKeysetExpressionIR`: `e &&& e` | in | `MaskedValue` in a select; `TernaryValue` in an entry | Entry values are canonical (ir-semantics.md, Key expressions). | translated |
| `simpleKeysetExpressionIR`: `e .. e` in a select | in | `RangeValue` | Closed range. | translated |
| `simpleKeysetExpressionIR`: `e .. e` in a table entry | excluded, by thesis | none | Needs the `range` match kind; see the table section. | refused by name |
| `simpleKeysetExpressionIR`: `DEFAULT`, `_` | in | `DontCare` in a select; a full-width wildcard in an entry | | translated |
| `tupleKeysetExpressionIR` | in | `SelectCase.sets`, `Entry.keys` | One per key, in order. | translated |

## Statements

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `emptyStatementIR` | elaborated | none | | performed |
| `assignmentStatementIR` with `assignop` `=` | in | `Assign` | Assigning a header copies validity (ir-semantics.md, Assigning a header). | translated |
| `assignmentStatementIR` with a compound `assignop` (`+=` and the rest) | elaborated | `a = a op b` | Design: other sugar. Precedent: p4c `RemoveOpAssign`. | performed, a shift's unsized amount sized as in a plain shift; `/=` and `%=` on values not known at compile time are not attempted |
| `callStatementIR`: action call from a control body | in | `CallAction` | | translated |
| `callStatementIR`: extern method on an instance | in | `CallExtern` | `result` present exactly when the method returns. | translated |
| `callStatementIR`: `t.apply()` | in | `Apply` | Forwarder README. Not inside an action. | translated |
| `callStatementIR`: `inst.apply(args)` on a sub-parser or sub-control instance | elaborated | `CallBlock` naming the block | Decision: the IR has no block instances. Stacks and subparser_stack READMEs. | performed; a block with constructor arguments or its own extern state is one block per instantiation |
| `callStatementIR`: `packet.extract(h)` | in | `Extract` | Decision: dedicated packet and header nodes. Target may be `hs.next`. | translated |
| `callStatementIR`: `packet.extract(h, n)` | excluded, by scope | none | The varbit form. `ParserInvalidArgument` stays reserved. | refused by name |
| `callStatementIR`: `packet.advance(n)` | in | `Advance` | | translated |
| `callStatementIR`: `verify(c, e)` | in | `Verify` | core.p4's one extern function. | translated |
| `callStatementIR`: `h.setValid()`, `h.setInvalid()` | in | `SetValid`, `SetInvalid` | | translated |
| `callStatementIR`: `hs.push_front(n)`, `hs.pop_front(n)` | in | `Push`, `Pop` | `count` is a constant. | translated |
| `callStatementIR`: `packet.emit(x)` | in | `Emit` | A header, a struct or a stack. Deparser only. | translated |
| `callStatementIR`: call of a `functionDeclarationIR` | elaborated | inlined at the call site (p4c `InlineFunctions`) | With `functionDeclarationIR`. | partial: as the expression row |
| `directApplicationStatementIR` (`Type.apply(args)`) | in | `CallBlock` | A call naming the block is exactly a direct application. | translated |
| `returnStatementIR` | excluded, by scope | none | Design. | refused by name |
| `exitStatementIR` | excluded, by scope | none | Design. | refused by name |
| `blockStatementIR` | elaborated | flattened into the enclosing statement list; its declarations hoisted to `Block.locals` | Stateful README: locals of the apply block become locals of the control block. | performed |
| `conditionalStatementIR` | in | `If` | `otherwise` may be empty. | translated |
| `forStatementIR` (all three forms), `forInitStatementIR`, `forUpdateStatementIR`, `forCollectionExpressionIR` | excluded, by scope | none | Design. | refused by name |
| `breakStatementIR`, `continueStatementIR` | excluded, by scope | none | With `for`. | refused by name |
| `switchStatementIR` on `t.apply().action_run` (with `switchLabelIR`, `switchCaseIR`) | elaborated | each action records which one ran in a local; an `If` chain dispatches | Implemented by the acl program; its README describes the exact action marker and dispatch. | performed; a `NoAction` label, whose IR body must stay empty, starts the marker at its number and the table's other actions overwrite it |
| `switchStatementIR` on an expression | elaborated | an `If` chain | Design: other sugar. Precedent: p4c `SimplifySwitch`. | performed |
| `constantDeclarationIR` inside a block | elaborated | folded into literals | Forwarder README (`TYPE_IPV4`); stacks README (`MAX_H2_HEADERS`). | performed |
| `variableDeclarationIR` | in | `Var` in `Block.locals` | An initializer becomes an `Assign` where the declaration stood (stacks README: `op1 = hdr.h1.op1`). Reading before writing gives zero (ir-semantics.md). | translated; a local declared without an initializer inside a parser state, an action or an inlined function gets its zero value where the declaration stood, as does an inlined function's `out` parameter, so it re-defaults on every entry (ir-semantics.md, State-local variables) |

## Parser declarations and states

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `parserDeclarationIR` | in | `Block` with `BLOCK_KIND_PARSER` | States, `start_state`, no body. | translated |
| its `packet_in` parameter | elaborated | carried by the block's kind | Every corpus README. The calling convention has no packet value. | performed |
| its two `typeParameterListIR` | excluded, by elaboration | none | Design: no generics. | refused by name |
| its `constructorParameterListIR` | elaborated | one block per instantiation, arguments substituted | The block-instances decision covers extern state but does not say what a constructor argument becomes. No corpus program has one. | performed for scalar constant arguments; others not attempted |
| `parserLocalDeclarationIR`: `constantDeclarationIR` | elaborated | folded | As in blocks. | performed |
| `parserLocalDeclarationIR`: `variableDeclarationIR` | in | `Block.locals` | Subparser_stack README: a parser-scoped local written by a sub-parser call and read by a select. A local declared inside a state without an initializer is hoisted the same way, and since P4-SpecTec re-defaults it on every entry of the state, the elaboration writes its zero value where the declaration stood (ir-semantics.md, State-local variables). | translated; an initializer of a parser-scoped local runs in the start state, or in an entry state when `start` is re-entered |
| `parserLocalDeclarationIR`: `instantiationIR` | see the declarations section | | | |
| `valueSetDeclarationIR` | excluded, by scope | none | Design. | refused by name |
| `parserStateIR` | in | `State` | `accept` and `reject` are `Target`s, not states. | translated |
| `parserBlockStatementIR` | elaborated | flattened; its declarations hoisted to `Block.locals` | As `blockStatementIR`. The printer braces the branches of a parser `if`, so SpecTec evaluates parser blocks, but never declares a variable inside one. | performed |
| `parserConditionalStatementIR` | in | `If` in a state body | | translated |
| `parserStatementIR`: the other alternatives | see the statements section | | Assignment, calls, direct application. | |
| `transitionStatementIR` with `stateExpressionIR` `nameIR` | in | `Transition.direct` to `Target.state`, `accept` or `reject` | Explicit `reject` rejects with `NoError` (ir-semantics.md). | translated |
| `selectExpressionIR` | in | `Select` | Keys evaluated once; first matching case wins; no match rejects with `NoMatch`. | translated |
| `selectCaseIR` | in | `SelectCase` | Keysets are constants of the key types. | translated |
| `parserTypeDeclarationIR` | excluded, by thesis | `Export` names the role; `BlockKind` fixes the signature | The architecture's interface type. | set aside |
| parser loops (no production; a state graph with a cycle) | in | the state graph | Bounded by the no-consumption revisit rule (ir-semantics.md, Parser loop bound). | translated |

## Table declarations

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `tableDeclarationIR` | in | `Table` | Its `typeIR` is the `TABLE` object type, a typing note with no residue. | translated |
| `tableKeysPropertyIR`, `tableKeyIR`: the expression | in | `Key.expr` | Keys are bits. A bool key is cast to `bit<1>`; a plain enum key is its member index in `bit<32>` (ir-semantics.md, Keys are bits; schema `Key`). | translated; a `bool` key is cast to `bit<1>`; a key of another type is not attempted |
| `tableKeyIR`: the key name (`# nameIR`) | in | `Key.name` | Decision: per-table action copies set `Key.name` to p4c's key names. | translated: `Key.name` is P4's control-plane name when it differs from the expression's path, and the path when the key read intrinsic metadata |
| `tableKeyIR`: match kind `exact`, `lpm`, `ternary` | in | `MatchKind` | Ties closed in ir-semantics.md (LPM, Ternary). | translated |
| `tableKeyIR`: match kind `selector` | excluded, by thesis | none | Action selectors and profiles. | refused by name |
| `tableKeyIR`: match kinds `range`, `optional` | excluded, by thesis | none | Declared by v1model and PSA, not core.p4. Nothing rules. | refused by name |
| `tableActionsPropertyIR`, `tableActionIR`: the action reference | in | `Table.actions` | Names of actions of the block. | translated |
| `tableActionIR`: bound arguments in `tableActionReferenceIR` | elaborated | one action copy per table, the bound lvalue substituted | Decision: per-table action copies (`setbyte`, `setbyte_1`, ...). | performed; a bound expression the action body also reaches is not attempted |
| `controlPlaneNameIR` (`@name` on an action reference) | elaborated | the copy's name | Same decision: the corpus STF names the elaborated actions directly. | partial: copies are named as p4c's frontend names them (`setbyte_1`), not by the control-plane name (`setbyte`) p4c's STF and P4Runtime use; an explicit `@name` is not read |
| `tableActionIR` note `# ( parameterListIR , parameterListIR )` | elaborated | none | A typing note splitting bound from control-plane parameters. | performed: the note is dropped |
| `tableDefaultActionPropertyIR` | in | `Table.default_action`, `Table.const_default_action` | Absent means `NoAction` (ir-semantics.md, Table miss). `NoAction` is declared with an empty body (forwarder README). | translated |
| `tableEntriesPropertyIR` with `const` | in | `Table.const_entries` | Installed before any host entry. | translated |
| `tableEntriesPropertyIR` without `const`, and a per-entry `constIR` | excluded, by scope | none | P4 1.2.5's mutable initial entries. The IR has only const entries; `TableEntries` on the host side could carry them. The printer decision on ternary entries concerns the oracle only. | refused by name |
| `tableEntryPriorityIR` (`priority = n`) | in | `Entry.priority`, larger wins | Decision: entry priority. Const entries without an explicit `priority = n` are numbered by position as §14.2.1.4 does under the default `largest_priority_wins`, the first ranking highest; p4c's `@priority` annotation is not read. | translated from the typed IL's priorities, which already number entries without one |
| `tableEntryIR`: the keyset | in | `KeyValue` exact, `LpmValue`, `TernaryValue` | Canonical values; `_` is a full-width wildcard (ir-semantics.md, Key expressions). | translated |
| `tableEntryIR`: `tableActionReferenceIR` with arguments | in | `ActionCall` with literal args | Action data of the declared widths. | translated |
| `tableCustomPropertyIR`: `size` | in | `Table.size`, informative | Decision: no meaning; kept for the roundtrip. | translated |
| `tableCustomPropertyIR`: `largest_priority_wins`, `priority_delta` | elaborated | the frontend's priority numbering | Decision: larger wins everywhere in the IR; the frontend assigns the numbers, so the direction and the spacing are consumed. | performed: `largest_priority_wins` decides the direction; `priority_delta` is already applied by typing |
| `tableCustomPropertyIR`: `implementation`, `counters`, `meters`, `psa_*` and other architecture properties | excluded, by thesis | none | Design: action profiles and selectors, direct counters and meters. | refused by name |
| `tableMetadataStructTypeIR.HIT` | in | `Apply.hit` | | translated |
| `tableMetadataStructTypeIR.MISS` | elaborated | `not hit` | ir-semantics.md defines `hit` as false on a miss, including a miss that ran the default action. | performed |
| `tableMetadataStructTypeIR.ACTION_RUN` (`tableMetadataEnumTypeIR`) | elaborated | with `switchStatementIR` on `action_run` | Design: out by elaboration. | performed |

## Declarations and instantiation

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `p4programIR` | in | `BlockLibrary` | Its blocks and shared declarations have no selected pipeline; architecture bindings separately carry `headers`, `metadata` and `exports`, which have no IL counterpart. | translated |
| `constantDeclarationIR` at top level | elaborated | folded into literals | Forwarder README. | performed |
| `instantiationIR` of an extern object | in | `ExternInstance` | Constructor arguments are literals. Program-level state (schema). | translated for v1model's `register` and `counter`, hoisted to program level; other objects not attempted |
| `instantiationIR` of a parser or control | elaborated | the block is called by name; a block that owns extern state and is instantiated more than once becomes one block per instantiation | Schema `BlockLibrary`; stacks and subparser_stack READMEs. | performed |
| `instantiationIR` of a package (`main`) | excluded, by thesis | architecture `Export` per role | Design: the architecture binds blocks to roles. | V1Switch bound by the v1model shim in reverse; other packages refused |
| `objectInitializerIR`, `ABSTRACT` in `externMethodPrototypeIR` | excluded, by scope | none | The survey recommends exclusion. The design's "extern function objects" may be meant to cover this; the wording does not say. | refused by name |
| `functionDeclarationIR`, `functionPrototypeIR` | elaborated | inlined at every call site (p4c `InlineFunctions`) | Core P4, absent from both the In list and the exclusions. Precedent: p4c `FunctionsInliner`. | partial: as the call rows |
| `actionDeclarationIR` | in | `Action` inside a `Block` | Directionless parameters are action data. Top-level actions have no corpus instance; the IR keeps actions block-scoped. | translated; a top-level action a block uses becomes that block's |
| `errorDeclarationIR` | in | `BlockLibrary.errors` | core.p4's seven first, in fixed order; user errors after (stacks README). | translated |
| `matchKindDeclarationIR` | elaborated | the fixed `MatchKind` enum | core.p4's three kinds; others per `tableKeyIR`. | performed |
| `enumTypeDeclarationIR`: plain | in | `EnumType` | | translated |
| `enumTypeDeclarationIR`: serializable (`ENUM typeIR nameIR { namedValueIR* }`) | elaborated | bits and literals | As `serializableEnumTypeIR`. | performed |
| `structTypeDeclarationIR`, `headerTypeDeclarationIR` | in | `StructType`, `HeaderType` | Type parameters: excluded by elaboration. | translated |
| `headerUnionTypeDeclarationIR` | excluded, by scope | none | Design. | refused by name |
| `typedefDeclarationIR` with `TYPEDEF` | elaborated | replaced by its definition | Forwarder README. | performed |
| `typedefDeclarationIR` with `TYPE` | elaborated | as `newTypeIR` | As `newTypeIR`. | performed |
| `externFunctionDeclarationIR`: core.p4's `verify` | in | `Verify` | Decision: dedicated nodes. | translated |
| `externFunctionDeclarationIR`: an architecture's functions | excluded, by thesis | none | Design: packet fate as externs. The corpus routes: `mark_to_drop` is `meta.drop = true` (forwarder), `update_checksum` is a `checksum16` instance (forwarder, csum16), `verify_checksum` deferred pending a contract field. | `mark_to_drop` as v1model defines it, writing only the drop port 511 to `egress_spec` (`M.egress_port`) in ingress, so that a later write of a port undoes it, and setting `drop` in egress; `hash`, `update_checksum` mapped as the v1model shim maps them back; `verify_checksum` left out while nothing reads `checksum_error`; others refused |
| `externObjectDeclarationIR` | in | `ExternType` | Type parameters: one type per instantiation (decision: monomorphic externs). | translated for v1model's `register` and `counter` |
| `externConstructorPrototypeIR` | in | `ExternType.constructor_params` | | translated for v1model's `register` and `counter` |
| `externMethodPrototypeIR` (non-abstract) | in | `Method` | | translated for v1model's `register` and `counter` |
| `controlDeclarationIR`, `controlBodyIR` | in | `Block` with `BLOCK_KIND_CONTROL` or `BLOCK_KIND_DEPARSER`; `Block.body` | The kind decides the statement set. | translated; V1Switch's verify, ingress, egress and compute controls merge into the control role; when there is an egress part, the ingress part ends with v1model's drop decision `drop = (egress_port == 511)` and the egress part is guarded by `!drop`; without one, 511 is no port of p4blo's switch, which drops the packet as v1model does |
| its two `typeParameterListIR` | excluded, by elaboration | none | Design: no generics. | refused by name |
| its `constructorParameterListIR` | elaborated | as for parsers | As for parsers. | performed for scalar constant arguments; others not attempted |
| its `packet_out` parameter | elaborated | carried by the block's kind | Every corpus README. | performed |
| `controlLocalDeclarationIR`: `actionDeclarationIR`, `tableDeclarationIR`, `variableDeclarationIR` | in | `Block.actions`, `Block.tables`, `Block.locals` | | translated |
| `controlLocalDeclarationIR`: `constantDeclarationIR`, `instantiationIR` | see the rows above | | | |
| `controlTypeDeclarationIR`, `packageTypeDeclarationIR` | excluded, by thesis | architecture `Export` and core `BlockKind` | The architecture's interface. | set aside |
| `parameterListIR`, `parameterIR` with a direction | in | `Param` with `Direction` | `DIRECTION_NONE` is action data. | translated |
| `standard_metadata` and other intrinsic metadata parameters (no IL production; the architecture's parameter) | excluded, by thesis | fields of the program's `M` under the metadata contract | Design, Metadata contract; forwarder README: `egress_spec` is `meta.egress_port`. | mapped: `ingress_port`, `parser_error`, `egress_spec` and `egress_port` onto the contract, `egress_spec` read in egress being 511 once `mark_to_drop` has run there; other fields refused; a user field of `M` named like a contract field is renamed, and is the contract field only where the source copies it to or from `standard_metadata` exactly as the printer's shim does |

## Annotations and misc

| IL construct (production) | Status | p4blo form or elaboration | Note | Bridge |
|---|---|---|---|---|
| `annotationList` (on every declaration, field, key, entry, block) | excluded, by scope | none; field numbers 100 and above are reserved for them | Decision: annotations never mix with semantics. Three annotations have semantic residue and are rows above: `@name` on a key (`Key.name`), `@name` on an action reference (the copy's name), `@priority` on a const entry (`Entry.priority`). | ignored; `@priority` reaches the IR through the typed IL's entry priorities |
| `nameIR`, `prefixedNameIR`, `nameListIR` | in | scoped `string` names | Schema: program, block, action, field, member, error and method namespaces. | translated |
| `namedValueIR`, `namedValueListIR` | elaborated | with serializable enums | | performed |
| `namedExpressionIR`, `namedExpressionListIR` | excluded, by elaboration | with record expressions | | partial: in record initializers of headers and structs |
| `ctk` (`2.7-compile-time-known.watsup`) | elaborated | none | A typing fact; the validator recomputes what it needs. | performed: dropped |
| runtime `value` (`2.1.1-value.watsup`): the header validity bit and the stack `nat` next index | in | the run-time model of ir-semantics.md | Not syntax; listed because the IL's values carry them and every closed behavior on headers and stacks refers to them. | the run-time model |

p4blo constructs with no IL production, for completeness: architecture
`Export`, `BlockBindings.headers`, `BlockBindings.metadata` (the metadata
contract), core `BLOCK_KIND_DEPARSER`, and the host-side `Entries` and
`TableEntries`. The first three are architecture binding choices.

## Summary

| Status | Rows |
|---|---|
| in | 84 |
| elaborated | 52 |
| excluded, by thesis | 10 |
| excluded, by elaboration | 13 |
| excluded, by scope | 19 |
| undecided | 0 |
| total | 178 |

Until 2026-09-24 this table counted 26 rows excluded by elaboration and
177 in all, one short of the rows above; the count was corrected when the
bridge's fourteen rows moved.

## Open rows

None. The sixteen rows that the first draft left undecided were ruled
on 2026-09-22; the rulings and their reasons are in
`.agents/decisions.md`.

## How the corpus exercises the in-rows

All twelve programs below are implemented, not planned. Their READMEs record
the precise source elaborations and bounded vectors. Syntax occurrence alone
does not show that a vector executes a branch; use the current
[evidence matrix](assurance.md#evidence-by-semantic-family) for semantic checks and qualifications.

| Corpus program | Principal exercised boundary |
|---|---|
| [forwarder](../tests/corpus/forwarder/README.md) | IPv4 parsing, LPM actions/defaults, TTL rewrite, checksum and deparse; complete independent Python/Lean sources |
| [stacks](../tests/corpus/stacks/README.md) | Header stacks, next/last/index, validity, push/pop, slice elaboration and inout block calls |
| [subparser_stack](../tests/corpus/subparser_stack/README.md) | Parser-scoped locals and next extraction through sub-parser inout arguments |
| [stateful](../tests/corpus/stateful/README.md) | Persistent register/counter instances, extern results and arithmetic |
| [csum16](../tests/corpus/csum16/README.md) | Checksum16 field input and 0xffff/0x0000 boundary |
| [acl](../tests/corpus/acl/README.md) | Ternary host priorities, masked parser select, stack loop and action-run elaboration |
| [priority](../tests/corpus/priority/README.md) | Overlapping const ternary entries and priority-convention elaboration |
| [parser_error](../tests/corpus/parser_error/README.md) | Atomic short extraction and controls after parser rejection |
| [verify_error](../tests/corpus/verify_error/README.md) | User errors, verify failure and parser-error observation |
| [register_bounds](../tests/corpus/register_bounds/README.md) | Persistent read/write, wrapping and explicit out-of-bounds policy |
| [tutorial_firewall](../tests/corpus/tutorial_firewall/README.md) | Direction/default policies, action calls, CRC16/32 and two persistent Bloom arrays; complete independent Python/Lean sources |
| [vlan_gateway](../tests/corpus/vlan_gateway/README.md) | Single-tag VLAN parsing, exact match/action policy, header invalidation, a counter extern and deparsing; complete Python source with an independent packet/state sequence |

Operators and execution paths not exercised by these fixed vectors have
focused native/Python known answers and generated differential suites where
listed in [assurance.md](assurance.md#evidence-by-semantic-family). In particular, scalar/lazy-expression,
aggregate/call-copy and stateful program generators complement the corpus.
Do not infer that every IR constructor has every kind of evidence, or that
every P4 feature is implemented, from the aggregate test or row counts.

## Rule coverage on P4-SpecTec

The table above says which IL constructs p4blo has. A second, measured
account says which of P4-SpecTec's rules p4blo's inputs make the pinned
simulator fire. [`spectec-coverage.json`](../tests/oracle/spectec-coverage.json)
records, for every rule, rule group, relation and function of the
[rule inventory](../tests/oracle/spectec-rules.json), whether it fired and
in how many of the vectors, over every corpus program and example and a
fixed set of 18 generated programs
([`generated.py`](../tests/oracle/generated.py)), printed through the
v1model shim. The simulator runs the spec in a structured form in
which each relation's rules are merged into one instruction tree; a rule
counts as fired when the instruction that concludes it ran, found through
the source region the instruction keeps.
[`coverage.py`](../tests/oracle/coverage.py) explains the method and its two
approximations, and cross-checks its instruction totals against the
simulator's own `cover-sim` command.

In scope are the rules of `8-dynamic` and the functions of `3-operations`
and `8-dynamic`, including the `builtin` functions the OCaml runtime
supplies for them.
Every one of them that does not fire is listed in
[`spectec-coverage-exclusions.json`](../tests/oracle/spectec-coverage-exclusions.json)
with a reason written by hand, in one of four categories: `architecture`
(fires only through the architecture layer), `excluded-construct` (the
construct is excluded or elaborated away by a row above, which the entry
names), `not-representable` (the construct is in, but the printer cannot
produce input that reaches the rule), and `unhit` (reachable, not yet
exercised; each entry names the generated input that would reach it).
`tests/external/test_spectec_coverage.py` fails when an in-scope item is neither hit
nor excluded, when an exclusion is stale, and when the counts below drift.

At the pinned commit, over 33 programs and 93 vectors:

| Status | 8-dynamic rules | 3-operations and 8-dynamic functions |
|---|---|---|
| hit | 183 | 69 |
| architecture | 0 | 1 |
| excluded-construct | 151 | 32 |
| not-representable | 25 | 1 |
| unhit | 2 | 0 |

A hit rule is exercised, not verified equivalent: the simulator applied it
while running a printed program, which says nothing about whether p4blo's
own semantics agrees with it beyond what the oracle tests compare. A
function counts as hit wherever it was entered, including constant folding
during typing. The two unhit rules propagate a packet read past the end
through an extern call's data and through a sub-parser's `inout`
argument, shapes no generated family produces yet.

The measurement needs the oracle and a small probe built against its
library; regenerating it takes about forty seconds:

```sh
python3 tests/oracle/coverage.py build   # once per pin, where tests/oracle/build.sh runs
uv run python tests/oracle/coverage.py   # rewrite the report; --check compares instead
```
