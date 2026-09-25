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
  or the schema, or an elaboration a corpus README records.
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
| note. A row whose status cell points at another section is a
cross-reference, not a row, and is not counted.

## Types

Productions from `2.2.1-type.watsup`.

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `voidTypeIR` (`VOID`) | elaborated | `Method.returns` absent | Schema: "Absent for a method that returns nothing." Actions and blocks return nothing by construction. |
| `boolTypeIR` (`BOOL`) | in | `Type.boolean` | |
| `errorTypeIR` (`ERROR`) | in | `Type.error` | Values are names from `Program.errors`. |
| `matchKindTypeIR` (`MATCH_KIND`) | elaborated | the `MatchKind` enum on `Key` | No value of this type exists in the IR. See `matchKindDeclarationIR`. |
| `stringTypeIR` (`STRING`) | excluded, by scope | none | Reaches only annotations and extern arguments such as `log_msg`. The survey recommends exclusion; nothing rules. |
| `intTypeIR` (`INT`) | excluded, by elaboration | none | Design: no `int`. Its literals are sized by context; see `literalExpressionIR`. |
| `fixedIntTypeIR` (`INT<n>`) | excluded, by scope | none | Decision: `int<N>` out for v0. One more `Type` kind and a signed variant of each arithmetic rule when wanted. |
| `fixedBitTypeIR` (`BIT<n>`) | in | `Type.bits` | `N >= 1`. |
| `varBitTypeIR` (`VARBIT<n>`) | excluded, by scope | none | Design. `HeaderTooShort` stays reserved in the error list so indices agree. |
| `nameTypeIR` (`_NAME typeId`) | in | `Type.header`, `Type.struct`, `Type.enum_type` | A reference by name; the validator resolves it once. |
| `typedefTypeIR` (`TYPEDEF`) | elaborated | replaced by its definition | Forwarder README: `macAddr_t`, `ip4Addr_t`, `egressSpec_t` are 48, 32, 9. |
| `newTypeIR` (`TYPE`, P4 `type`) | elaborated | its underlying type, as typedef (p4c `EliminateNewtype`) | Nothing rules on it. The typedef route is available (p4c `EliminateNewtype`); a newtype only forbids implicit casts, which is a typing fact. |
| `listTypeIR`, `tupleTypeIR` | excluded, by elaboration | none | Design: no tuples. The one list the corpus met, a checksum field list, became a concatenation; see `sequenceExpressionIR`. |
| `arrayTypeIR` (`ARRAY t[n]`) | excluded, by scope | none | SpecTec's fixed-size array over a non-header element. P4 surface syntax reaches it only through header stacks. Likely by scope; nothing rules. |
| `headerStackTypeIR` | in | `Type.stack` (`StackType`) | Element must be a header. A stack of header unions goes with unions. |
| `structTypeIR` | in | `StructType` | Fields of any type. Type arguments: see `typeArgumentIR`. |
| `headerTypeIR` | in | `HeaderType` | Fields are bits or bool. |
| `headerUnionTypeIR` | excluded, by scope | none | Design. |
| `simpleEnumTypeIR` | in | `EnumType` | |
| `serializableEnumTypeIR` (with `valueFieldIR`) | elaborated | `bit<N>` and `BitsLiteral` | Schema: "Serializable enums are elaborated to bits and literals." Casts among them become the IR's three casts (ir-semantics.md, Casts). |
| `externObjectTypeIR` | in | `ExternType` | Monomorphic. Decision: one `ExternType` per instantiation (`register`, `register.16`); `externMethodTypeDefEnv` is `Method`. |
| `parserObjectTypeIR`, `controlObjectTypeIR` | in | `Block.kind` and `Block.params` | A P4 deparser is a control; here it is a third kind with its own statement set. |
| `packageObjectTypeIR` | excluded, by thesis | `Export` names the role | Design: the architecture is outside; SpecTec's `7-instantiation` and `9-arch`. |
| `tableObjectTypeIR` | in | `Table` | Its result struct: see `tableMetadataStructTypeIR`. |
| `typeArgumentIR`, type arguments on `STRUCT`, `HEADER`, `EXTERN`, `PARSER`, `CONTROL` | excluded, by elaboration | none | Design: no generics. Every IR type is concrete. |
| `defaultTypeIR` (`DEFAULT`) | excluded, by elaboration | none | Type of `...`; see `defaultExpressionIR`. |
| `invalidHeaderTypeIR` (`HEADER_INVALID`) | excluded, by elaboration | none | Type of `{#}`; see `invalidHeaderExpressionIR`. |
| `sequenceTypeIR`, `recordTypeIR` | excluded, by elaboration | none | Types of initializer expressions; see `sequenceExpressionIR`, `recordExpressionIR`. |
| `setTypeIR` (`SET<t>`) | excluded, by elaboration | none | Type of keyset expressions. Keysets are the constants `KeySet` and `KeyValue`. |
| `tableMetadataEnumTypeIR` (`TABLE_ENUM`) | elaborated | with `switchStatementIR` on `action_run` | See the table section. |
| `tableMetadataStructTypeIR` (`TABLE_STRUCT`) | elaborated | `HIT` is `Apply.hit`; `MISS` and `ACTION_RUN` are rewritten | See the table section for each field. |

## Expressions

Productions from `4.0-ir-syntax.watsup`; operator sets from
`1-syntax.watsup`.

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `typedExpressionIR`, `expressionNoteIR` (`typeIR ctk`) | excluded, by elaboration | `Expr` carries no note | Decision: no type annotations on expressions; the validator computes each type once. `ctk` is a typing fact. |
| `literalExpressionIR`: `TRUE`, `FALSE` | in | `Literal.boolean` | |
| `literalExpressionIR`: `nat W int` | in | `Literal.bits` (`BitsLiteral{width, value}`) | Decimal in `[0, 2^width)`. |
| `literalExpressionIR`: `D int` (unsized) | elaborated | sized by the other operand, the target or the key | Forwarder, stacks, subparser_stack, stateful and csum16 READMEs. SpecTec's `Cast_impl_neq/fixBit` is the same step. |
| `literalExpressionIR`: `nat S int` (signed) | excluded, by scope | none | With `int<N>`. |
| `literalExpressionIR`: `stringLiteral` | excluded, by scope | none | With `stringTypeIR`. |
| `referenceExpressionIR` (`prefixedNameIR`: `_BARE`, `.`) | in | `Expr.var`; every reference is a scoped name | Schema: scopes are P4's and the validator resolves every name once. The `.` prefix is a resolution fact the validator recomputes. |
| `defaultExpressionIR` (`...`) | excluded, by elaboration | none | Design: "other sugar the frontend removes." Precedent: p4c `DefaultValues`. |
| `unaryExpressionIR` with `!`, `~`, `-` | in | `Unary` NOT, COMPLEMENT, NEGATE | Negation wraps modulo `2^N`. |
| `unaryExpressionIR` with `+` | excluded, by elaboration | the operand | Identity. |
| `binaryExpressionIR` with `+ - * \|+\| \|-\| & \| ^ << >> ++ == != < <= > >= && \|\|` | in | `Binary` | ir-semantics.md: wrapping, saturating, shift by width or more, unsigned comparison, equality on every type, short-circuit. |
| `binaryExpressionIR` with `/`, `%` | elaborated | folded | ir-semantics.md: P4 defines them only on compile-time constants, which the frontend folds. |
| `ternaryExpressionIR` (`e ? e : e`) | in | `Mux` | Same type on both branches. |
| `castExpressionIR` | in | `Cast` | Three pairs: bits to bits, bool to `bit<1>`, `bit<1>` to bool. Every other P4 cast is elaborated into these (ir-semantics.md, Casts). Implicit casts are already explicit in the IL (`$apply_cast`), so they have no row. |
| `invalidHeaderExpressionIR` (`{#}`) | excluded, by elaboration | none | Design: other sugar. Precedent: p4c `EliminateInvalidHeaders`, into `SetInvalid`. |
| `sequenceExpressionIR` as an extern argument | elaborated | concatenation of the fields, in order | Forwarder and csum16 READMEs: `update_checksum`'s field list becomes one `bit<144>` or `bit<16>` argument. |
| `sequenceExpressionIR`, `recordExpressionIR` elsewhere (with `namedExpressionIR`, `...`) | excluded, by elaboration | none | Design: no tuples, other sugar. Precedents: p4c `EliminateTuples`, `StructInitializers`. |
| `errorAccessExpressionIR` (`error.X`) | in | `Literal.error` | |
| `memberAccessExpressionIR`: field of a header or struct | in | `Member` | Reading a field of an invalid header is closed in ir-semantics.md. |
| `memberAccessExpressionIR`: `TYPE name . member` (enum member) | in | `Literal.enum_member` | |
| `memberAccessExpressionIR`: `hs.lastIndex` | in | `LastIndex` | `bit<32>`; parser-only in P4, and `nextIndex == 0` closed in ir-semantics.md (`hs.lastIndex`). |
| `memberAccessExpressionIR`: `hs.last` | elaborated | `Index(hs, LastIndex(hs))` | Parser-only in P4. Faithful when the stack is non-empty; on `nextIndex == 0` P4-SpecTec raises `StackOutOfBounds` where the elaborated form reads a zero invalid header, a listed deviation (ir-semantics.md, `hs.last` on an empty stack). Stacks and subparser_stack READMEs use it. |
| `memberAccessExpressionIR`: `hs.next` | in | `LValue.next` | Parser only, as the target of an extract. |
| `memberAccessExpressionIR`: `hs.size` | excluded, by elaboration | the constant `StackType.size` | Compile-time known. |
| `memberAccessExpressionIR`: `t.apply().hit`, `.miss`, `.action_run` | see the table section | | |
| `indexAccessExpressionIR` (`hs[e]`) | in | `Index` | Run-time index; out of range closed in ir-semantics.md. |
| `sliceAccessExpressionIR` with `sliceop` `:` | in | `Slice{hi, lo}` | Bounds are constants; the validator checks `lo <= hi < N`. |
| `sliceAccessExpressionIR` with `sliceop` `+:` | excluded, by elaboration | `[lo + w - 1 : lo]` | P4 1.2.5's `e[lo +: w]`; both operands are compile-time known. |
| `callExpressionIR`: extern method in expression position | elaborated | `CallExtern.result` into a fresh local | Schema: "The IR has no discarded results; the frontend introduces a local." |
| `callExpressionIR`: `h.isValid()` | in | `IsValid` | Decision: dedicated packet and header nodes. |
| `callExpressionIR`: `packet.lookahead<T>()` | in | `Lookahead{type}` | Parser only. |
| `callExpressionIR`: `packet.length()` | excluded, by scope | none | Declared in core.p4's `packet_in`; no design list names it and no corpus program uses it. |
| `callExpressionIR`: `t.apply()` in expression position | see the table section | | |
| `callExpressionIR`: `constructorTargetIR ( args )` | see `instantiationIR` | | |
| `callExpressionIR`: call of a `functionDeclarationIR` | elaborated | inlined at the call site (p4c `InlineFunctions`) | With `functionDeclarationIR`. |
| `callableTargetIR`: `TYPE name . method` (static extern method) | excluded, by scope | none | Nothing rules; the IR calls methods on instances only. |
| `callExpressionIR`: `< typeArgumentListIR >` on a call | excluded, by elaboration | none | Design: no generics. |
| `parenthesizedExpressionIR` | excluded, by elaboration | none | A tree has no parentheses. |
| `argumentIR`: positional `e` | in | `Arg.expr` for `in`; `Arg.lvalue` for `out` and `inout` | Copy-in, copy-out in parameter order; aliasing is a validator error (ir-semantics.md, Block calls). |
| `argumentIR`: `name = e`, `name = _`, `_` | excluded, by elaboration | positional order; a `_` out-argument to a fresh local | Design: other sugar. Precedents: p4c `OrderArguments`, `RemoveDontcareArgs`. |
| `lvalueIR`: `referenceExpressionIR` | in | `LValue.var` | |
| `lvalueIR`: `typedLvalueIR . name` | in | `LMember` | |
| `lvalueIR`: `typedLvalueIR [ e ]` | in | `LIndex` | |
| `lvalueIR`: `typedLvalueIR [ e sliceop e ]` | elaborated | read-modify-write of the whole field, `f = (f & ~mask) \| (v << lo)` | Decision: slice lvalues are elaborated, not added. Stacks README gives the formula. |
| `lvalueIR`: `( typedLvalueIR )`; `lvalueNoteIR` | excluded, by elaboration | none | As for expressions. |
| `simpleKeysetExpressionIR`: `e` | in | `KeySet.exact` in a select; `KeyValue.exact` in an entry | A constant of the key's type. |
| `simpleKeysetExpressionIR`: `e &&& e` | in | `MaskedValue` in a select; `TernaryValue` in an entry | Entry values are canonical (ir-semantics.md, Key expressions). |
| `simpleKeysetExpressionIR`: `e .. e` in a select | in | `RangeValue` | Closed range. |
| `simpleKeysetExpressionIR`: `e .. e` in a table entry | excluded, by thesis | none | Needs the `range` match kind; see the table section. |
| `simpleKeysetExpressionIR`: `DEFAULT`, `_` | in | `DontCare` in a select; a full-width wildcard in an entry | |
| `tupleKeysetExpressionIR` | in | `SelectCase.sets`, `Entry.keys` | One per key, in order. |

## Statements

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `emptyStatementIR` | excluded, by elaboration | none | |
| `assignmentStatementIR` with `assignop` `=` | in | `Assign` | Assigning a header copies validity (ir-semantics.md, Assigning a header). |
| `assignmentStatementIR` with a compound `assignop` (`+=` and the rest) | excluded, by elaboration | `a = a op b` | Design: other sugar. Precedent: p4c `RemoveOpAssign`. |
| `callStatementIR`: action call from a control body | in | `CallAction` | |
| `callStatementIR`: extern method on an instance | in | `CallExtern` | `result` present exactly when the method returns. |
| `callStatementIR`: `t.apply()` | in | `Apply` | Forwarder README. Not inside an action. |
| `callStatementIR`: `inst.apply(args)` on a sub-parser or sub-control instance | elaborated | `CallBlock` naming the block | Decision: the IR has no block instances. Stacks and subparser_stack READMEs. |
| `callStatementIR`: `packet.extract(h)` | in | `Extract` | Decision: dedicated packet and header nodes. Target may be `hs.next`. |
| `callStatementIR`: `packet.extract(h, n)` | excluded, by scope | none | The varbit form. `ParserInvalidArgument` stays reserved. |
| `callStatementIR`: `packet.advance(n)` | in | `Advance` | |
| `callStatementIR`: `verify(c, e)` | in | `Verify` | core.p4's one extern function. |
| `callStatementIR`: `h.setValid()`, `h.setInvalid()` | in | `SetValid`, `SetInvalid` | |
| `callStatementIR`: `hs.push_front(n)`, `hs.pop_front(n)` | in | `Push`, `Pop` | `count` is a constant. |
| `callStatementIR`: `packet.emit(x)` | in | `Emit` | A header, a struct or a stack. Deparser only. |
| `callStatementIR`: call of a `functionDeclarationIR` | elaborated | inlined at the call site (p4c `InlineFunctions`) | With `functionDeclarationIR`. |
| `directApplicationStatementIR` (`Type.apply(args)`) | in | `CallBlock` | A call naming the block is exactly a direct application. |
| `returnStatementIR` | excluded, by scope | none | Design. |
| `exitStatementIR` | excluded, by scope | none | Design. |
| `blockStatementIR` | elaborated | flattened into the enclosing statement list; its declarations hoisted to `Block.locals` | Stateful README: locals of the apply block become locals of the control block. |
| `conditionalStatementIR` | in | `If` | `otherwise` may be empty. |
| `forStatementIR` (all three forms), `forInitStatementIR`, `forUpdateStatementIR`, `forCollectionExpressionIR` | excluded, by scope | none | Design. |
| `breakStatementIR`, `continueStatementIR` | excluded, by scope | none | With `for`. |
| `switchStatementIR` on `t.apply().action_run` (with `switchLabelIR`, `switchCaseIR`) | elaborated | each action records which one ran in a local; an `If` chain dispatches | Implemented by the acl program; its README describes the exact action marker and dispatch. |
| `switchStatementIR` on an expression | excluded, by elaboration | an `If` chain | Design: other sugar. Precedent: p4c `SimplifySwitch`. |
| `constantDeclarationIR` inside a block | elaborated | folded into literals | Forwarder README (`TYPE_IPV4`); stacks README (`MAX_H2_HEADERS`). |
| `variableDeclarationIR` | in | `Var` in `Block.locals` | An initializer becomes an `Assign` where the declaration stood (stacks README: `op1 = hdr.h1.op1`). Reading before writing gives zero (ir-semantics.md). |

## Parser declarations and states

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `parserDeclarationIR` | in | `Block` with `BLOCK_KIND_PARSER` | States, `start_state`, no body. |
| its `packet_in` parameter | elaborated | carried by the block's kind | Every corpus README. The calling convention has no packet value. |
| its two `typeParameterListIR` | excluded, by elaboration | none | Design: no generics. |
| its `constructorParameterListIR` | elaborated | one block per instantiation, arguments substituted | The block-instances decision covers extern state but does not say what a constructor argument becomes. No corpus program has one. |
| `parserLocalDeclarationIR`: `constantDeclarationIR` | elaborated | folded | As in blocks. |
| `parserLocalDeclarationIR`: `variableDeclarationIR` | in | `Block.locals` | Subparser_stack README: a parser-scoped local written by a sub-parser call and read by a select. A local declared inside a state without an initializer is hoisted the same way, but P4-SpecTec re-defaults it on every entry of the state; whether the elaboration must insert a zeroing assignment at the state's entry is undecided (ir-semantics.md, State-local variables). |
| `parserLocalDeclarationIR`: `instantiationIR` | see the declarations section | | |
| `valueSetDeclarationIR` | excluded, by scope | none | Design. |
| `parserStateIR` | in | `State` | `accept` and `reject` are `Target`s, not states. |
| `parserBlockStatementIR` | elaborated | flattened | As `blockStatementIR`. |
| `parserConditionalStatementIR` | in | `If` in a state body | |
| `parserStatementIR`: the other alternatives | see the statements section | | Assignment, calls, direct application. |
| `transitionStatementIR` with `stateExpressionIR` `nameIR` | in | `Transition.direct` to `Target.state`, `accept` or `reject` | Explicit `reject` rejects with `NoError` (ir-semantics.md). |
| `selectExpressionIR` | in | `Select` | Keys evaluated once; first matching case wins; no match rejects with `NoMatch`. |
| `selectCaseIR` | in | `SelectCase` | Keysets are constants of the key types. |
| `parserTypeDeclarationIR` | excluded, by thesis | `Export` names the role; `BlockKind` fixes the signature | The architecture's interface type. |
| parser loops (no production; a state graph with a cycle) | in | the state graph | Bounded by the no-consumption revisit rule (ir-semantics.md, Parser loop bound). |

## Table declarations

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `tableDeclarationIR` | in | `Table` | Its `typeIR` is the `TABLE` object type, a typing note with no residue. |
| `tableKeysPropertyIR`, `tableKeyIR`: the expression | in | `Key.expr` | Keys are bits. A bool key is cast to `bit<1>`; a plain enum key is its member index in `bit<32>` (ir-semantics.md, Keys are bits; schema `Key`). |
| `tableKeyIR`: the key name (`# nameIR`) | in | `Key.name` | Decision: per-table action copies set `Key.name` to p4c's key names. |
| `tableKeyIR`: match kind `exact`, `lpm`, `ternary` | in | `MatchKind` | Ties closed in ir-semantics.md (LPM, Ternary). |
| `tableKeyIR`: match kind `selector` | excluded, by thesis | none | Action selectors and profiles. |
| `tableKeyIR`: match kinds `range`, `optional` | excluded, by thesis | none | Declared by v1model and PSA, not core.p4. Nothing rules. |
| `tableActionsPropertyIR`, `tableActionIR`: the action reference | in | `Table.actions` | Names of actions of the block. |
| `tableActionIR`: bound arguments in `tableActionReferenceIR` | elaborated | one action copy per table, the bound lvalue substituted | Decision: per-table action copies (`setbyte`, `setbyte_1`, ...). |
| `controlPlaneNameIR` (`@name` on an action reference) | elaborated | the copy's name | Same decision: the corpus STF names the elaborated actions directly. |
| `tableActionIR` note `# ( parameterListIR , parameterListIR )` | excluded, by elaboration | none | A typing note splitting bound from control-plane parameters. |
| `tableDefaultActionPropertyIR` | in | `Table.default_action`, `Table.const_default_action` | Absent means `NoAction` (ir-semantics.md, Table miss). `NoAction` is declared with an empty body (forwarder README). |
| `tableEntriesPropertyIR` with `const` | in | `Table.const_entries` | Installed before any host entry. |
| `tableEntriesPropertyIR` without `const`, and a per-entry `constIR` | excluded, by scope | none | P4 1.2.5's mutable initial entries. The IR has only const entries; `TableEntries` on the host side could carry them. The printer decision on ternary entries concerns the oracle only. |
| `tableEntryPriorityIR` (`priority = n`) | in | `Entry.priority`, larger wins | Decision: entry priority. Const entries' smaller-wins `@priority` and list order are renumbered. |
| `tableEntryIR`: the keyset | in | `KeyValue` exact, `LpmValue`, `TernaryValue` | Canonical values; `_` is a full-width wildcard (ir-semantics.md, Key expressions). |
| `tableEntryIR`: `tableActionReferenceIR` with arguments | in | `ActionCall` with literal args | Action data of the declared widths. |
| `tableCustomPropertyIR`: `size` | in | `Table.size`, informative | Decision: no meaning; kept for the roundtrip. |
| `tableCustomPropertyIR`: `largest_priority_wins`, `priority_delta` | elaborated | the frontend's priority numbering | Decision: larger wins everywhere in the IR; the frontend assigns the numbers, so the direction and the spacing are consumed. |
| `tableCustomPropertyIR`: `implementation`, `counters`, `meters`, `psa_*` and other architecture properties | excluded, by thesis | none | Design: action profiles and selectors, direct counters and meters. |
| `tableMetadataStructTypeIR.HIT` | in | `Apply.hit` | |
| `tableMetadataStructTypeIR.MISS` | elaborated | `not hit` | ir-semantics.md defines `hit` as false on a miss, including a miss that ran the default action. |
| `tableMetadataStructTypeIR.ACTION_RUN` (`tableMetadataEnumTypeIR`) | elaborated | with `switchStatementIR` on `action_run` | Design: out by elaboration. |

## Declarations and instantiation

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `p4programIR` | in | `Program` | Plus `headers`, `metadata` and `exports`, which have no IL counterpart. |
| `constantDeclarationIR` at top level | elaborated | folded into literals | Forwarder README. |
| `instantiationIR` of an extern object | in | `ExternInstance` | Constructor arguments are literals. Program-level state (schema). |
| `instantiationIR` of a parser or control | elaborated | the block is called by name; a block that owns extern state and is instantiated more than once becomes one block per instantiation | Schema `Program`; stacks and subparser_stack READMEs. |
| `instantiationIR` of a package (`main`) | excluded, by thesis | `Export` per role | Design: the architecture binds blocks to roles. |
| `objectInitializerIR`, `ABSTRACT` in `externMethodPrototypeIR` | excluded, by scope | none | The survey recommends exclusion. The design's "extern function objects" may be meant to cover this; the wording does not say. |
| `functionDeclarationIR`, `functionPrototypeIR` | elaborated | inlined at every call site (p4c `InlineFunctions`) | Core P4, absent from both the In list and the exclusions. Precedent: p4c `FunctionsInliner`. |
| `actionDeclarationIR` | in | `Action` inside a `Block` | Directionless parameters are action data. Top-level actions have no corpus instance; the IR keeps actions block-scoped. |
| `errorDeclarationIR` | in | `Program.errors` | core.p4's seven first, in fixed order; user errors after (stacks README). |
| `matchKindDeclarationIR` | elaborated | the fixed `MatchKind` enum | core.p4's three kinds; others per `tableKeyIR`. |
| `enumTypeDeclarationIR`: plain | in | `EnumType` | |
| `enumTypeDeclarationIR`: serializable (`ENUM typeIR nameIR { namedValueIR* }`) | elaborated | bits and literals | As `serializableEnumTypeIR`. |
| `structTypeDeclarationIR`, `headerTypeDeclarationIR` | in | `StructType`, `HeaderType` | Type parameters: excluded by elaboration. |
| `headerUnionTypeDeclarationIR` | excluded, by scope | none | Design. |
| `typedefDeclarationIR` with `TYPEDEF` | elaborated | replaced by its definition | Forwarder README. |
| `typedefDeclarationIR` with `TYPE` | elaborated | as `newTypeIR` | As `newTypeIR`. |
| `externFunctionDeclarationIR`: core.p4's `verify` | in | `Verify` | Decision: dedicated nodes. |
| `externFunctionDeclarationIR`: an architecture's functions | excluded, by thesis | none | Design: packet fate as externs. The corpus routes: `mark_to_drop` is `meta.drop = true` (forwarder), `update_checksum` is a `checksum16` instance (forwarder, csum16), `verify_checksum` deferred pending a contract field. |
| `externObjectDeclarationIR` | in | `ExternType` | Type parameters: one type per instantiation (decision: monomorphic externs). |
| `externConstructorPrototypeIR` | in | `ExternType.constructor_params` | |
| `externMethodPrototypeIR` (non-abstract) | in | `Method` | |
| `controlDeclarationIR`, `controlBodyIR` | in | `Block` with `BLOCK_KIND_CONTROL` or `BLOCK_KIND_DEPARSER`; `Block.body` | The kind decides the statement set. |
| its two `typeParameterListIR` | excluded, by elaboration | none | Design: no generics. |
| its `constructorParameterListIR` | elaborated | as for parsers | As for parsers. |
| its `packet_out` parameter | elaborated | carried by the block's kind | Every corpus README. |
| `controlLocalDeclarationIR`: `actionDeclarationIR`, `tableDeclarationIR`, `variableDeclarationIR` | in | `Block.actions`, `Block.tables`, `Block.locals` | |
| `controlLocalDeclarationIR`: `constantDeclarationIR`, `instantiationIR` | see the rows above | | |
| `controlTypeDeclarationIR`, `packageTypeDeclarationIR` | excluded, by thesis | `Export` and `BlockKind` | The architecture's interface. |
| `parameterListIR`, `parameterIR` with a direction | in | `Param` with `Direction` | `DIRECTION_NONE` is action data. |
| `standard_metadata` and other intrinsic metadata parameters (no IL production; the architecture's parameter) | excluded, by thesis | fields of the program's `M` under the metadata contract | Design, Metadata contract; forwarder README: `egress_spec` is `meta.egress_port`. |

## Annotations and misc

| IL construct (production) | Status | p4blo form or elaboration | Note |
|---|---|---|---|
| `annotationList` (on every declaration, field, key, entry, block) | excluded, by scope | none; field numbers 100 and above are reserved for them | Decision: annotations never mix with semantics. Three annotations have semantic residue and are rows above: `@name` on a key (`Key.name`), `@name` on an action reference (the copy's name), `@priority` on a const entry (`Entry.priority`). |
| `nameIR`, `prefixedNameIR`, `nameListIR` | in | scoped `string` names | Schema: program, block, action, field, member, error and method namespaces. |
| `namedValueIR`, `namedValueListIR` | elaborated | with serializable enums | |
| `namedExpressionIR`, `namedExpressionListIR` | excluded, by elaboration | with record expressions | |
| `ctk` (`2.7-compile-time-known.watsup`) | excluded, by elaboration | none | A typing fact; the validator recomputes what it needs. |
| runtime `value` (`2.1.1-value.watsup`): the header validity bit and the stack `nat` next index | in | the run-time model of ir-semantics.md | Not syntax; listed because the IL's values carry them and every closed behavior on headers and stacks refers to them. |

p4blo constructs with no IL production, for completeness: `Export`,
`Program.headers`, `Program.metadata` (the metadata contract),
`BLOCK_KIND_DEPARSER`, and the host-side `Entries` and `TableEntries`.
Each is where the architecture layer used to be.

## Summary

| Status | Rows |
|---|---|
| in | 84 |
| elaborated | 38 |
| excluded, by thesis | 10 |
| excluded, by elaboration | 26 |
| excluded, by scope | 19 |
| undecided | 0 |
| total | 177 |

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

In scope are the rules of `8-dynamic` and the functions of `3-operations`,
including the `builtin` functions the OCaml runtime supplies for them.
Every one of them that does not fire is listed in
[`spectec-coverage-exclusions.json`](../tests/oracle/spectec-coverage-exclusions.json)
with a reason written by hand, in one of four categories: `architecture`
(fires only through the architecture layer), `excluded-construct` (the
construct is excluded or elaborated away by a row above, which the entry
names), `not-representable` (the construct is in, but the printer cannot
produce input that reaches the rule), and `unhit` (reachable, not yet
exercised; each entry names the generated input that would reach it).
`tests/test_spectec_coverage.py` fails when an in-scope item is neither hit
nor excluded, when an exclusion is stale, and when the counts below drift.

At the pinned commit, over 33 programs and 93 vectors:

| Status | 8-dynamic rules | 3-operations functions |
|---|---|---|
| hit | 183 | 39 |
| architecture | 0 | 0 |
| excluded-construct | 149 | 20 |
| not-representable | 27 | 8 |
| unhit | 2 | 1 |

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
