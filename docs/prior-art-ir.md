# Prior art for the p4blo IR schema

Researched 2026-09-22 against the `main` branches of the four repositories,
read through raw.githubusercontent.com and the GitHub tree pages. Context:
`docs/design.md`, sections "The IR is post-elaboration", "Blocks and the
P4NAH rule", "Scope". Nothing in the repository was modified.

Summary of what each IR is:

| IR | Form | Post-elaboration? | Architecture coupling | Names |
|---|---|---|---|---|
| P4-SpecTec IL | SpecTec `.watsup` grammar (`spec/4-p4-ir/4.0-ir-syntax.watsup`, types in `spec/2-static-runtime/2.2.1-type.watsup`) | Typed and cast-explicit, but generic, with `INT`, tuples, switch, exit, value sets | None in the IL; `spec/9-arch` and `7-instantiation` sit outside it | Identifiers with a `.`-prefix for top-level |
| BMv2 JSON | JSON (`docs/JSON_format.md`) | Fully lowered: flat headers, widths on every field, no types on expressions | Total: pipelines, deparsers, checksums, meters, registers, `field_aliases` for `standard_metadata` | Strings plus per-category integer `id`s |
| 4ward `ir.proto` | protobuf edition 2024 (`simulator/ir.proto`) | Post-p4c-midend: generics instantiated, constants folded, stacks concretized; every `Expr` carries a `Type` | An `Architecture` message with `PipelineStage`s and extern type decls; tables and entries live in P4Info/P4Runtime | Strings by design ("names, not numeric IDs") |
| p4c IR | C++ classes from `ir/*.def` | Any stage; `Expression.type` filled by `TypeInference`; frontend and midend passes progressively remove sugar | None in the IR; the `Type_Package` instantiation names the architecture | `ID`/`Path`, `declid` for uniqueness |

---

## 1. P4-SpecTec's elaborated IL

### Where it lives

There is no `p4/lib/il/ast.ml` on `main` anymore; the top level has
`p4spec/` (OCaml: `lib/{frontend,interp,lang,pass,runtime,backend-sim,
backend-boot,stf,...}`, which interprets the spec) and `spec/`, where the
P4 language itself is defined in watsup. The relevant files:

- `spec/1-p4-surface/1-syntax.watsup`: surface (EL) syntax of P4, including
  `unop`, `binop`, `sliceop`, `assignop`, `literalExpression`,
  `keysetExpression`, `selectCase`.
- `spec/4-p4-ir/4.0-ir-syntax.watsup`: the IL syntax; every production is
  the surface one suffixed `IR`. Siblings: `4.1-ir-call-helper`,
  `4.2-ir-call-overload`, `4.3-annotation`, `4.4-ir-subexpression`,
  `4.5-ir-to-surface` (a printer back to surface, the same direction as
  p4blo's printer).
- `spec/2-static-runtime/2.2.1-type.watsup`: `typeIR`.
  `2.1.1-value.watsup`: runtime `value`. `2.7-compile-time-known.watsup`:
  `ctk`.
- `spec/3-operations/3-operations.watsup`: the arithmetic (`$bin_plus`,
  `$bin_satplus`, `$bin_shl`, `$shr_arith`, `$bin_concat`, `$bitacc`,
  `$cast_op`, `$default(typeIR)` ...). Arithmetic is on arbitrary-precision
  integers and wraps when converted to the fixed-width result; right shift
  on signed values is arithmetic; saturating variants clamp.
- `spec/5-typing/5.05.2-typing-casting.watsup`: implicit-cast insertion.
- `spec/7-instantiation`, `spec/8-dynamic`, `spec/9-arch`: instantiation
  of objects (packages, parsers, controls, externs), dynamic semantics,
  v1model/ebpf.

The processing pipeline in the README is EL (parsed) -> IL (type-checked
with annotations) -> SL -> PL prose. `./p4spectec sim spec` drives the
simulator; `elab`, `run`, `testgen` are the other commands.

### Types (`typeIR`)

Verbatim constructor list from `2.2.1-type.watsup`:

- base: `VOID`, `BOOL`, `ERROR`, `MATCH_KIND`, `STRING`, `INT`
  (arbitrary precision), `INT < nat >`, `BIT < nat >`, `VARBIT < nat >`.
- named/alias: `_NAME typeId`; `TYPEDEF typeId typeIR`; `TYPE typeId typeIR`
  (newtype).
- data: `LIST < typeIR >`, `TUPLE < typeIR* >`, `ARRAY typeIR [ nat ]`,
  `HEADER_STACK typeIR [ nat ]`,
  `STRUCT typeId < typeArgumentIR* > { fieldTypeIR* }`,
  `HEADER typeId < typeArgumentIR* > { fieldTypeIR* }`,
  `HEADER_UNION typeId < typeArgumentIR* > { fieldTypeIR* }`,
  `ENUM typeId { nameIR* }`, `ENUM typeId < typeIR > { valueFieldIR* }`
  (serializable, members carry `value`s).
- object: `EXTERN typeId < typeArgumentIR* > externMethodTypeDefEnv`,
  `PARSER typeId < ... > ( parameterIR* )`, `CONTROL ...`,
  `PACKAGE typeId < ... > { typeIR* }`,
  `TABLE typeId { tableMetadataStructTypeIR }`.
- synthesized (types only literals and results have): `DEFAULT`,
  `HEADER_INVALID`, `SEQ < typeIR* >` (with an optional `...` form),
  `RECORD { fieldTypeIR* }` (idem), `SET < typeIR >` (keysets),
  `TABLE_ENUM typeId { nameIR* }` and
  `TABLE_STRUCT typeId { HIT BOOL; MISS BOOL; ACTION_RUN TABLE_ENUM }`
  (the type of `t.apply()`).

Widths are `nat`, already numbers. Struct and header types still carry
type arguments (generic headers are not monomorphized in the IL).

### Values (`2.1.1-value.watsup`)

`value = baseValue | dataValue | objectReferenceValue | synthesizedValue`;
`baseValue = bool | error | matchKind | string | integer`;
`dataValue = list | tuple | array | headerStack | struct | header |
headerUnion | enum`; `objectReferenceValue = REF objectId`. A `headerValue`
carries a validity boolean and a `headerStackValue` a `nat` next index.

### Expressions (`4.0-ir-syntax.watsup`)

Every expression is annotated: `typedExpressionIR = expressionIR '#'
expressionNoteIR`, with `expressionNoteIR = ( typeIR ctk )`, "a pair of
type and compile-time known-ness". L-values are a separate sort:
`typedLvalueIR = lvalueIR '#' ( typeIR )` where `lvalueIR =
referenceExpressionIR | typedLvalueIR '.' nameIR | typedLvalueIR [ e ] |
typedLvalueIR [ e sliceop e ] | ( typedLvalueIR )`.

`expressionIR` alternatives: `literalExpressionIR` (= surface
`literalExpression`: `TRUE|FALSE`, `integerLiteral = D int | nat W int |
nat S int` so width and signedness are on the literal, `stringLiteral`),
`referenceExpressionIR = prefixedNameIR` (`_BARE nameIR | '.' nameIR`),
`defaultExpressionIR`, `unaryExpressionIR = unop e`,
`binaryExpressionIR = e binop e`, `ternaryExpressionIR = e ? e : e`,
`castExpressionIR = ( typeIR ) e`, `dataExpressionIR` (`invalidHeader`,
`SEQ { e* }` with optional `...`, `RECORD { name = e; * }` with optional
`...`), `accessExpressionIR` (`errorAccess`, `memberAccess`, `indexAccess`,
`sliceAccess`), `callExpressionIR = constructorTargetIR ( argumentListIR )
| callableTargetIR < typeArgumentListIR > ( argumentListIR )`,
`parenthesizedExpressionIR`.

Operators are the surface ones: `unop = ! | ~ | - | +`;
`binop = * / % + - |+| |-| << >> <= >= < > != == & ^ | ++ && ||`;
`sliceop = : | +:`.

Arguments: `argumentIR = e | name = e | name = _ | _` (named arguments and
don't-care arguments survive).

### Statements

`statementIR = empty | assignment (typedLvalueIR assignop e) | call
(callableTargetIR < typeArgs > ( args )) | directApplication
(constructorTargetIR . APPLY ( args )) | return [e] | exit | block |
conditional (IF (e) s [ELSE s]) | for (three forms) | break | continue |
switch (SWITCH (e) { case* }, switchLabelIR = DEFAULT | e)`.
Compound assignment operators (`+=` etc.) are still present.

### Declarations

`declarationIR = constant | instantiation (annotationList typeIR
constructorTargetIR ( args ) nameIR objectInitializerOptIR) | function |
action | error | matchKind | extern (function and object) | parser |
control | typeDeclaration (enum, struct, header, header_union, typedef,
type, parserType, controlType, packageType) | valueSet`.

Parser: `parserDeclarationIR = annotationList PARSER nameIR
< typeParameterListIR , typeParameterListIR > ( parameterListIR )
( constructorParameterListIR ) ...`; `parserStateIR = annotationList STATE
nameIR { parserBlockElementStatementListIR transitionStatementIR }`;
`transitionStatementIR = TRANSITION stateExpressionIR`;
`selectExpressionIR = SELECT ( typedExpressionListIR ) { selectCaseListIR }`;
`selectCaseIR = keysetExpressionIR ':' nameIR ';'`;
`keysetExpressionIR = simpleKeysetExpressionIR | tupleKeysetExpressionIR`;
simple keysets are `e | e &&& e | e .. e | DEFAULT | _`.

Table: `tableDeclarationIR = annotationList TABLE typeIR nameIR
{ tablePropertyListIR }`, properties `KEY | ACTIONS | DEFAULT_ACTION |
ENTRIES | CUSTOM | CUSTOM_CONST`;
`tableKeyIR = typedExpressionIR '#' nameIR ':' nameIR annotationList ';'`
(expression, key name, match kind);
`tableEntryIR = constOptIR tableEntryPriorityOptIR keysetExpressionIR ':'
tableActionReferenceIR annotationList ';'` with
`tableEntryPriorityIR = PRIORITY '=' integerLiteral ':'`;
`tableActionReferenceIR = prefixedNameIR controlPlaneNameIR ( args )`.

### What elaboration does and does not remove

Removed or made explicit by the surface-to-IL elaboration (`5-typing`):

- Implicit casts. `5.05.2-typing-casting.watsup` defines `Cast_impl`,
  `Cast_impl_neq`, `$cast_unary(e, t)` ("implicitly cast to"),
  `$cast_binary(e1, e2)` ("implicitly cast to equal types") and
  `$apply_cast`, which wraps the expression in an ordinary cast node:
  `( (typeIR_h) typedExpressionIR ) '#' ( typeIR_h ctk )`. The rules
  `Cast_impl_neq/fixInt: INT -> INT<w>` and `Cast_impl_neq/fixBit: INT ->
  BIT<w>` are how `int` literals reach a width. So the IL has one cast
  node and no implicit/explicit flag (contrast p4c's `Cast.implicit`).
- Types and `ctk` on every expression; typed l-values; key names
  (`# nameIR`) on table keys; control-plane names on action references;
  name prefixes resolved to `_BARE` versus `.`.

Still present in the IL, hence what p4blo must decide about (see
Implications, item f): type parameters on parsers, controls, functions
and externs (two type-parameter lists: declared and inferred), type
arguments on calls, generic `STRUCT`/`HEADER` types; the
arbitrary-precision `INT` type; `LIST`, `TUPLE`, `SEQ`, `RECORD`,
`DEFAULT`, `HEADER_INVALID`, `SET` synthesized types; `VARBIT`,
`HEADER_UNION`, value sets, `STRING`, `MATCH_KIND`; `for`, `break`,
`continue`, `switch` (both on expressions and on `action_run`), `return`,
`exit`; compound assignment; named and don't-care arguments; direct
application statements; instantiations with object initializers (abstract
extern methods); custom table properties; the `TABLE_STRUCT`
hit/miss/action_run result type; package types; annotations. Object
instantiation, and therefore the binding of a program to an architecture,
happens later, in `7-instantiation` and `9-arch`, outside the IL.

---

## 2. BMv2 JSON input format (`docs/JSON_format.md`)

- **Versioning and ids.** `__meta__: {version: [major, minor], compiler}`.
  Every object has a string `name` and an integer `id`. Header types,
  headers and stacks have ids unique within their category; parse states,
  tables, conditionals and action profiles have ids that are globally
  unique across the JSON; actions, calculations, checksums and parsers are
  globally unique. References between objects are by *name* (e.g.
  `next_state`, `next_tables`, `header_type`, `actions: ["a1", ...]`), not
  by id, except `default_entry.action_id` and `action_entry.action_id`.
- **Header types.** `fields: [[name, bitwidth], ...]`, with an optional
  third element `true` for signed fields; `"*"` width for varbit with
  `length_exp` and `max_length`. Headers: `{name, id, header_type,
  metadata: bool}`. Header stacks: `{name, id, header_type, header_ids}`
  (elements are ordinary header instances). Also `header_union_types`,
  `header_unions`, `header_union_stacks`, `errors: [[name, int]]`,
  `enums: [{name, entries}]`, `field_aliases` (maps target names like
  `standard_metadata.egress_port` onto real `[header, field]` pairs).
  Locals are metadata headers (p4c emits a `scalars` header) and, inside
  expressions, `{"type": "local", "value": i}` indexes runtime data.
- **Parsers.** `parse_states: [{name, id, parser_ops, transition_key,
  transitions}]`. `parser_ops[].op` is one of `extract` (`type`:
  regular/stack/union_stack, `value`: header or stack name), `extract_VL`
  (plus an `expression` for the varbit length), `set` (target field,
  source of type field/hexstr/lookahead/expression), `verify` (boolean
  expression plus an error constant expression), `advance` (a bit count,
  "bmv2 currently requires the number of bits to shift to be a multiple of
  8"), `primitive` (extern method call). `lookahead` appears as `[bit
  offset, bitwidth]` both in `set` sources and in `transition_key`.
  `transition_key: [{type: field|stack_field|union_stack_field|lookahead,
  value}]`. `transitions: [{type: default|hexstr|parse_vset, value, mask,
  next_state}]`, where value and mask "need to be the concatenation (in
  the right order) of all byte padded fields", so masks apply to the
  concatenated key and ranges do not exist (p4c lowers them, see section
  4). `next_state: null` ends the parser.
- **Pipelines.** `pipelines: [{name, id, init_table, tables, action_profiles,
  conditionals}]`. A table: `match_type` (`exact|lpm|ternary|range`, the
  most specific across keys), `type` (`simple|indirect|indirect_ws`),
  `max_size`, `with_counters`, `support_timeout`, `direct_meters`,
  `key: [{match_type: valid|exact|lpm|ternary|range, target: [header,
  field] (or a header name for valid), mask}]`, `actions: [names]`,
  `base_default_next`, `next_tables: {action: table}` or `{__HIT__,
  __MISS__}`, `default_entry: {action_id, action_const, action_data,
  action_entry_const}`, `entries: [{match_key: [{match_type, key} |
  {match_type: lpm, key, prefix_length} | {match_type: ternary, key, mask}
  | {match_type: range, start, end}], action_entry: {action_id,
  action_data}, priority}]`. Conditionals: `{name, id, expression,
  true_next, false_next}`. Control flow is a graph of table and
  conditional nodes, not statements.
- **Actions.** `{name, id, runtime_data: [{name, bitwidth}], primitives:
  [{op, parameters}]}`. Parameter types: `field [header, field]`, `hexstr`,
  `header`, `header_stack`, `runtime_data` (index), `expression`,
  `calculation`, `register_array`, `counter_array`, `meter_array`,
  `extern`, `parse_vset`, `bool`, `string`. Core primitives: `assign`,
  `assign_VL`, `assign_header`, `assign_union`, `assign_header_stack`,
  `assign_union_stack`, `push`, `pop`, `_jump`, `_jump_if_zero`, `exit`,
  `assert`, `assume`, `log_msg`; "support for additional primitives
  depends on the architecture" (add_header, remove_header, mark_to_drop,
  clone, resubmit, recirculate, count, execute_meter, register_read/write
  are v1model's).
- **Expressions.** `{"type": "expression", "value": {"op", "left",
  "right"}}` (`cond` added for `?`), operands typed by `type`: `field`,
  `hexstr`, `header`, `header_stack`, `stack_field`, `expression`, `bool`,
  `register`, `local`. Ops: `+ - * << >>`, `& | ^ ~`, `== != > >= < <=`,
  `and or not`, `valid`, `valid_union`, `d2b`, `b2d`, `two_comp_mod`,
  `sat_cast`, `usat_cast`, `?`, `dereference_header_stack`,
  `last_stack_index`, `size_stack`, `access_field`. Constants carry no
  width: "Arithmetic is done with infinite precision, but when a value is
  copied into a field, it is truncated based on the field's bitwidth";
  `two_comp_mod(v, w)` gives "the signed value of the source given a
  2-complement representation with that width" and p4c inserts it (and
  `sat_cast`/`usat_cast`) to reproduce fixed-width semantics. Header
  validity is a read-only 1-bit pseudo field `<header>.$valid$`.
- **Architecture coupling.** Total. `parsers`, `deparsers: [{name, id,
  order: [header names]}]` (emit in order, skipping invalid),
  `calculations`, `checksums: [{target, calculation, verify, update}]`,
  `meter_arrays`, `counter_arrays`, `register_arrays: [{bitwidth, size}]`,
  `extern_instances: [{type, attribute_values}]`, `learn_lists`,
  `field_lists`, and `field_aliases` all sit at the root next to the
  program, and `standard_metadata` is just a metadata header.

---

## 3. 4ward's protobuf IR (`simulator/ir.proto`)

`edition = "2024"; package fourward;` imports `p4/config/v1/p4info.proto`
and `p4/v1/p4runtime.proto`. Header comment, verbatim in part: "Architecture-
generic: the Architecture message captures pipeline wiring and extern
declarations; extern semantics are implemented per-architecture in the
simulator. Readable: all cross-references use names, not numeric IDs.
Numeric IDs from p4info are reserved for the control-plane API. Type-
complete: every Expr node carries a Type annotation populated by p4c after
type resolution. The simulator never infers types at runtime. ... The IR
is emitted after p4c's midend passes: generics instantiated, types
resolved, constants folded, header stacks concretized."

- **Top.** `PipelineConfig { P4Info p4info; DeviceConfig device }`;
  `DeviceConfig { BehavioralConfig behavioral; p4.v1.WriteRequest
  static_entries; repeated TypeTranslation translations;
  ControlPlaneBindings control_plane_bindings }`;
  `BehavioralConfig { Architecture architecture; repeated TypeDecl types;
  repeated ParserDecl parsers; repeated ControlDecl controls; repeated
  ActionDecl actions; repeated TableBehavior tables }`.
- **Types.** `Type { oneof kind { BitType bit (width); IntType signed_int
  (width); VarbitType varbit (max_width); bool boolean; string named;
  HeaderStackType header_stack { string element_type; uint32 size }; bool
  error } }`. `TypeDecl { string name; oneof kind { HeaderDecl (fields,
  controller_header); StructDecl (fields); HeaderUnionDecl; EnumDecl
  (repeated string members; uint32 width, zero for non-serializable) } }`;
  `FieldDecl { name; Type type; repeated int32 field_list_ids }`.
- **Names.** Strings everywhere: `NameRef.name`, `ParserState.name`
  (`start`/`accept`/`reject` predefined), `TableBehavior.name`,
  `ControlPlaneBinding { p4info_name; simulator_name }`. `ActionDecl` has
  both `name` (source) and `current_name` (post-midend rename).
- **Expressions.** `Expr { oneof kind { Literal; NameRef; FieldAccess
  (expr, field_name); ArrayIndex (expr, index); Slice (expr, uint32 hi,
  uint32 lo); Concat; Cast (Type target_type, expr); BinaryOp (operator,
  left, right); UnaryOp (operator, expr); MethodCall (Expr target, string
  method, repeated Expr args, repeated Type type_args); TableApplyExpr
  (table_name, AccessKind RESULT|HIT|MISS); MuxExpr; StructExpr }; Type
  type = 100; SourceInfo = 100 elsewhere }`.
  `enum BinaryOperator { ADD SUB MUL DIV MOD ADD_SAT SUB_SAT BIT_AND BIT_OR
  BIT_XOR SHL SHR EQ NEQ LT GT LE GE AND OR }`; `enum UnaryOperator { NEG
  BIT_NOT NOT }`. `Literal { oneof kind { uint64 integer (N <= 64); bytes
  big_integer (big-endian, N > 64); bool boolean; string error_member;
  string enum_member; string string_literal } }`, width from `Expr.type`.
  `MethodCall` "covers extern method calls, header methods (isValid,
  setValid, setInvalid), and packet methods (extract, emit, lookahead)":
  there are no dedicated extract/emit/setValid/push/pop nodes.
- **Parsers.** `ParserDecl { name; params; local_vars; extern_instances;
  value_sets; repeated ParserState states }`; `ParserState { name; repeated
  Stmt stmts; Transition transition }`; `Transition { oneof { string
  next_state; SelectTransition select } }`; `SelectTransition { repeated
  Expr keys; repeated SelectCase cases; string default_state }`;
  `SelectCase { repeated KeysetExpr keyset; string next_state }`;
  `KeysetExpr { oneof kind { Expr exact; RangeKeyset range (lo, hi); 
  MaskKeyset mask (value, mask); bool default_case; string value_set } }`.
- **Tables.** Only `TableBehavior { name; repeated TableKey keys
  (field_name, expr); map<string,string> action_overrides }`. Match kinds,
  default action, size, entries and priorities are in P4Info and in the
  `static_entries` P4Runtime `WriteRequest`.
- **Actions and statements.** `ActionDecl { name; params; body;
  current_name }`; `ParamDecl { name; Type; Direction IN|OUT|INOUT }`;
  `VarDecl { name; Type; Expr initializer }`. `Stmt { oneof kind {
  AssignmentStmt (lhs, rhs); MethodCallStmt; IfStmt (condition, then_block,
  else_block); SwitchStmt (subject always a TableApplyExpr, cases keyed by
  action_name, default_block); BlockStmt; ExitStmt; ReturnStmt } }`.
- **Architecture coupling.** `Architecture { string name ("v1model",
  "psa", "pna"); repeated PipelineStage stages { name; StageKind
  PARSER|CONTROL|DEPARSER; block_name }; repeated ExternTypeDecl
  extern_types; string port_type_name }`; `ControlDecl { name; params;
  local_vars; local_actions; repeated Stmt apply_body; extern_instances }`;
  `ExternInstanceDecl { type_name; name; constructor_args }`;
  `ExternTypeDecl { name; constructor_params; methods }`; `MethodDecl {
  name; params; return_type }`. Intrinsic metadata are ordinary structs in
  `types`; the architecture is named, and the simulator implements it in
  Kotlin (`V1ModelArchitecture.kt`, `PSAArchitecture.kt`,
  `PNAArchitecture.kt`).

---

## 4. p4c's IR (`ir/base.def`, `ir/expression.def`, `ir/type.def`, `ir/ir.def`)

- **Base.** `abstract Expression { optional Type type = Type::Unknown::get();
  ... }` (`base.def`; "the type field stores TypeInferencing results").
  `Declaration { ID name; long declid }`, `Path { ID name; bool absolute }`,
  annotations, `IDeclaration`, `IGeneralNamespace`, `INestedNamespace`.
  `TypeInference` runs early in the frontend ("insert casts, don't check
  arrays"), is re-run as `TypeChecking` throughout the midend, and
  `ClearTypeMap` discards the side table; the `type` field on the node is
  what backends read after `EvaluatorPass`.
- **Types (`type.def`).** `Type_Bits { optional int size = 0; NullOK
  optional Expression expression; bool isSigned }` ("represents both bit<>
  and int<>", width may still be an expression before constant folding),
  `Type_Boolean`, `Type_InfInt` (the arbitrary-precision `int`, with a
  `declid` as a type variable), `Type_Varbits { size, expression }`,
  `Type_Name { Path }`, `Type_StructLike { annotations; TypeParameters
  typeParameters; IndexedVector<StructField> fields }` with `Type_Struct`,
  `Type_Header` (static `setValid`, `setInvalid`, `isValid`),
  `Type_HeaderUnion`, `Type_Array { Type elementType; Expression size }`
  (the former `Type_Stack`), `Type_Enum`, `Type_SerEnum { Type type;
  members }`, `Type_Error`, `Type_Tuple`, `Type_List`, `Type_Specialized
  { Type_Name baseType; Vector<Type> arguments }`, `Type_Var`,
  `Type_Parser/Type_Control { applyParams }`, `Type_Extern`,
  `Type_MethodBase { typeParameters; returnType; parameters }`,
  `Type_Action`, `Type_Table { P4Table }`, `Type_ActionEnum { ActionList }`
  (the `action_run` type), `Type_MatchKind`, `Type_Package`,
  `Type_Typedef`, `Type_Newtype`, `Type_String`, `Type_Dontcare`,
  `Type_Void`, `Type_Set { elementType }` (keysets), `Type_Any`,
  `Type_P4List`, `Type_Type`, `Type_Fragment`, `Type_Unknown`.
- **Expressions (`expression.def`).** `Operation_Unary { Expression expr }`
  with `Neg - UPlus + Cmpl ~ LNot !`; `Operation_Binary { left, right }`
  with `Mul Div Mod Add Sub AddSat SubSat Shl Shr Concat BAnd BOr BXor LAnd
  LOr`, `Operation_Relation` (Boolean-typed) `Equ Neq Lss Leq Grt Geq`,
  and `Range ..`, `Mask &&&` (Type_Set); `Operation_Ternary { e0 e1 e2 }`
  with `Mux ?:` and `Slice` (`e0[e1:e2]`, `getH()/getL()` require
  constants), `PlusSlice`; `Member { expr; ID member }`; `ArrayIndex {
  left; right }`; `Cast { Type destType; optional bool implicit; expr }`;
  `Constant : Literal { big_int value; unsigned base }`, `BoolLiteral`,
  `StringLiteral`; `PathExpression { Path }`; `TypeNameExpression`;
  `ListExpression { components }`, `P4ListExpression`, `StructExpression {
  structType; components }`, `ArrayExpression`; `MethodCallExpression {
  Expression method; Vector<Type> typeArguments; Vector<Argument>
  arguments }`; `ConstructorCallExpression`; `SelectExpression {
  ListExpression select; Vector<SelectCase> selectCases }` with
  `SelectCase { Expression keyset; PathExpression state }`;
  `DefaultExpression`, `Dots`, `NamedDots`, `This`, `Invalid`,
  `InvalidHeader { Type headerType }`, `InvalidHeaderUnion`; the
  `*Assign` op-assignment nodes; `SymbolicVariable`. Every `Operation` has
  `getStringOp()` and a `precedence`.
- **Statements and declarations (`ir.def`).** `AssignmentStatement { left;
  right }`, `OpAssignmentStatement`, `MethodCallStatement { methodCall }`,
  `IfStatement { condition; ifTrue; NullOK ifFalse }`, `BlockStatement {
  components }`, `ReturnStatement { NullOK expression }`, `ExitStatement`,
  `EmptyStatement`, `SwitchStatement { expression; cases }` with
  `SwitchCase { label; NullOK statement }` (fall-through by null),
  `ForStatement`, `ForInStatement`, `BreakStatement`, `ContinueStatement`.
  `ParserState { annotations; components; NullOK Expression
  selectExpression }`; `P4Parser { Type_Parser type; constructorParams;
  parserLocals; states }`; `P4Control { Type_Control type;
  constructorParams; controlLocals; BlockStatement body }`; `P4Action {
  parameters; body }`; `P4Table { TableProperties properties }` with
  `Key { keyElements }`, `KeyElement { Expression expression;
  PathExpression matchType }`, `ActionList`, `ActionListElement {
  expression }`, `EntriesList`, `Entry { bool isConst; NullOK Expression
  priority; ListExpression keys; Expression action; bool singleton }`,
  `Property { value; isConstant }`; `P4ValueSet { elementType; size }`;
  `Declaration_Variable`, `Declaration_Constant`, `Declaration_Instance {
  type; arguments; properties; NullOK initializer }`; `P4Program { objects }`.
- **Which passes remove what** (`frontends/p4/frontend.cpp`, in order):
  `ConstantFolding` (before types), `InstantiateDirectCalls` ("desugars
  direct parser and control applications" into instances), `TypeInference`
  ("insert casts"), `DefaultValues`, `BindTypeVariables`,
  `EntryPriorities` (assigns priorities to const entries), then repeated
  `SpecializeGenericTypes`, `DefaultArguments`, `TypeInference`,
  `SpecializeGenericFunctions`; `RemoveParserIfs`, `StructInitializers`,
  `TableKeyNames`, repeated `ConstantFolding`/`StrengthReduction`/
  `Reassociation`/`UselessCasts`, `SimplifyControlFlow`,
  `SwitchAddDefault`, `RemoveAllUnusedDeclarations`, `UniqueNames`,
  `SimplifyParsers`, `ResetHeaders`, `MoveDeclarations`,
  `MoveInitializers`, `SideEffectOrdering`, `RemoveOpAssign`,
  `SimplifySwitch`, `SimplifyDefUse`, `UniqueParameters`, `SpecializeAll`
  (specializes parser/control instantiations by constructor arguments),
  `RemoveParserControlFlow`, `RemoveReturns`, `RemoveDontcareArgs`,
  `MoveConstructors`, `RemoveRedundantParsers`, `EvaluatorPass`, `Inline`,
  `InlineActions`, `LocalizeAllActions`, `RemoveActionParameters`,
  `InlineFunctions`, `SetHeaders`, `HierarchicalNames`, `FrontEndLast`.
  Then in `backends/bmv2/simple_switch/midend.cpp`: `RemoveMiss`,
  `EliminateNewtype`, `EliminateInvalidHeaders`, `EliminateSerEnums`,
  `ConvertEnums` (EnumOn32Bits), `OrderArguments` (named args to
  positional), `SimplifyKey` (non-trivial keys into temporaries),
  `SimplifySelectCases` (constant keysets only), `ExpandLookahead`,
  `ExpandEmit`, `SimplifyParsers`, `EliminateTuples`,
  `SimplifyComparisons`, `CopyStructures`, `NestedStructs`,
  `SimplifySelectList`, `RemoveSelectBooleans`, `FlattenHeaders`,
  `FlattenInterfaceStructs`, `ReplaceSelectRange` (ranges into sets of
  masks), `LocalCopyPropagation`, `ValidateTableProperties`,
  `EliminateTypedef`, `CompileTimeOperations`, `TableHit`,
  `EliminateSwitch` (switch on non-action-run expressions into a
  synthesized table), `RemoveLeftSlices`, `ParsersUnroll` (optional),
  `EvaluatorPass`. `RemoveExits` is a midend pass other backends add;
  simple_switch keeps `exit` as a primitive.

---

## Implications for p4blo's schema

Each recommendation names the prior art that supports it.

### (a) Types: a `Type` message with a `oneof`, not width plus kind

All three typed IRs use a sum type: 4ward `Type { oneof kind { bit(width),
signed_int(width), varbit, boolean, named, header_stack(element, size),
error } }`, p4c's `Type_*` class hierarchy, SpecTec's `typeIR`. BMv2's
"width integer plus signed flag" per field works only because everything
is already flattened to header fields and expressions carry no types at
all. p4blo has structs, headers, stacks and enums as first-class values in
`H` and `M`, so it needs the sum. Concretely:

- `Type { oneof kind { uint32 bit; bool boolean; Error error; uint32
  enum_id; uint32 header_id; uint32 struct_id; Stack stack { uint32
  header_id; uint32 size } } }`. Widths are integers, never expressions
  (p4c's `Type_Bits.expression` and `Type_Array.size: Expression` are
  exactly the pre-elaboration residue the design forbids; 4ward and
  SpecTec both have `nat`/`uint32`).
- Follow 4ward in making enum declarations carry a `width` (zero for
  non-serializable), and SpecTec/p4c in distinguishing `error` from
  enums; p4c's midend `ConvertEnums`/`EliminateSerEnums` shows both can be
  lowered to `bit<N>`, but keeping them typed keeps the printer trivial.
- Decide `int<N>`. It is in every prior IR (SpecTec `INT<nat>`, 4ward
  `IntType`, p4c `Type_Bits.isSigned`, BMv2 signed field flag) and is core
  P4 (arithmetic right shift, saturating ops, signed comparison), but the
  design's "In" list has only `bit<N>`. Excluding it is "out by scope";
  including it costs one `oneof` arm and a signed flag in the Lean
  arithmetic. Not architecture-dependent, so it should be explicitly one
  or the other in `coverage.md`.

### (b) Expressions: a `oneof` of structural node kinds, with operator enums inside unary/binary

Every IR studied is structural at the node level and enumerated at the
operator level: 4ward `Expr.oneof kind` with `BinaryOp { BinaryOperator
operator; left; right }` and `UnaryOp`; SpecTec `unaryExpressionIR = unop e`,
`binaryExpressionIR = e binop e`; p4c has one class per operator but they
are all `Operation_Unary/Binary/Ternary` with a `getStringOp()`, i.e. the
same shape flattened. BMv2's fully generic `{op, left, right}` with string
ops and untyped operands is the outlier and the one that needed
`two_comp_mod`/`sat_cast` bolt-ons because the node has no width. So:

- `Expr { Type type = 1 (mandatory); oneof kind { Literal; VarRef; Field
  (expr, field index); Index (stack, expr); Slice (expr, hi, lo as
  integers, per 4ward and p4c `getH()/getL()`); Concat; Cast (target type
  is `Expr.type`); Unary { UnaryOp op; expr }; Binary { BinaryOp op; left;
  right }; Mux; IsValid (header expr); StackLast/StackSize if index
  arithmetic on `.last`/`.lastIndex` is in } }`.
- `BinaryOp` enum straight from SpecTec's `binop`/4ward's `BinaryOperator`:
  `ADD SUB MUL DIV MOD ADD_SAT SUB_SAT SHL SHR BIT_AND BIT_OR BIT_XOR
  CONCAT EQ NEQ LT LE GT GE AND OR`; `UnaryOp { NEG BIT_NOT NOT }`
  (drop unary plus; p4c folds it). Consider whether `DIV`/`MOD` are in:
  P4 restricts them to compile-time constants, so after constant folding
  they should not appear at all (p4c `ConstantFolding`,
  `CompileTimeOperations`).
- Put the type on every node and make it mandatory (4ward: "always
  populated by p4c ... never inferred at runtime"; SpecTec: `e # (type
  ctk)`; p4c: `Expression.type`). The validator, not the schema, checks
  consistency (operand widths equal, cast target equals node type, slice
  bounds within width), which is the validator role the design already
  assigns. Drop SpecTec's `ctk` (compile-time-knownness): after
  elaboration only literals are ctk and the validator can require
  literals where P4 requires constants (slice bounds, entry keysets,
  shift amounts if desired).
- Literals: 4ward's `uint64 integer | bytes big_integer` with width from
  the type is the practical choice (IPv6 addresses exceed 64 bits); BMv2
  uses hex strings, p4c `big_int`. A single `bytes value` big-endian plus
  the width in `Type` is simplest for Lean's JSON decoding and for the text
  format; a `uint64` fast path is optional.
- Keep l-values as a separate message (SpecTec `typedLvalueIR`: reference,
  member, index, slice) rather than "any Expr", so the validator's
  assignability rule is structural.

### (c) Names and ids

The four IRs split two ways. BMv2 has string names plus dense integer ids
per category and references mostly by name; p4c has `ID`/`Path` with a
hidden `declid`; SpecTec has identifiers with a `.`-prefix flag; 4ward
explicitly chose "names, not numeric IDs" for readability and pushed
numeric ids to P4Info. The design's "names are ids, flat string table"
is closer to BMv2 than to 4ward, and the trade is readability of the raw
text format, which 4ward valued and the design already assigns to the
printer. Recommendations:

- One `repeated string strings` on `Program`; every declaration has a
  `uint32 name` indexing it. References are by *declaration index* into
  the typed list they live in (`header_id` into `Program.headers`,
  `table_id` into `Block.tables`, `state_id` into `Block.states`), the
  BMv2 pattern of "ids unique within category", not by string-table
  index. That keeps validation to bounds checks and keeps the Lean decoder
  free of name resolution. The string table then serves the printer, the
  STF runner (`add` lines name tables and actions) and error messages.
- Carry the P4 source name (after p4c's `@name`/`HierarchicalNames`) for
  tables and actions specifically, because STF and any future P4Runtime
  bridge address them by that string (4ward `ControlPlaneBinding {
  p4info_name; simulator_name }`, `ActionDecl.name` vs `current_name`).
  For p4blo this is the same string-table entry; the point is that it
  must roundtrip through the printer unchanged.
- Reserve a `SourceInfo`/comment field at a fixed high number (4ward puts
  `SourceInfo` and `Type` at field 100 on every message) so the text
  format can carry comments emitted by the eDSL without touching the
  semantic fields.
- Do not put a version inside the message beyond the package name
  (`p4blo.v0`); BMv2's `__meta__.version` exists because JSON has no
  package, protobuf does.

### (d) Parser `select` with masks and ranges

- Represent it as SpecTec and 4ward do, not as BMv2 does. `Select {
  repeated Expr keys; repeated Case cases }`, `Case { repeated Keyset
  keyset (one per key, i.e. SpecTec's tuple keyset); uint32 next_state }`,
  `Keyset { oneof kind { Literal exact; Mask { Literal value; Literal
  mask }; Range { Literal lo; Literal hi }; bool dont_care } }`. `default`
  is a case whose keysets are all `dont_care` (SpecTec distinguishes
  `DEFAULT` and `_` syntactically; semantically for a select they
  coincide). Keysets are literals, not expressions, matching p4c's
  `SimplifySelectCases` ("requires constant keysets") and SpecTec's `ctk`.
- First-matching-case order is the semantics in all four; no case
  matching is `reject` with `error.NoMatch` (p4c `HandleNoMatch`, BMv2
  `next_state: null`); the design should say so in `semantics.md`.
- Do not pre-lower ranges to masks or concatenate keys into one
  byte-padded value (BMv2 `transitions[].value/mask` over the
  concatenation; p4c `ReplaceSelectRange`, `SimplifySelectList`). That
  lowering destroys readability and is exactly the kind of target-specific
  encoding an interchange IR should leave to the consumer.
- Keep `lookahead`, `advance`, `extract`, `verify` as explicit parser
  statement kinds (BMv2's `parser_ops`, and p4c's midend `ExpandLookahead`,
  `ExpandEmit` show these are the primitives), rather than 4ward's
  `MethodCall` on a `packet_in` value (see (g)). Lookahead is an
  expression (`Lookahead { Type type }` with its width from the type);
  extract, advance and verify are statements; extract has an optional
  stack target (`extract(hs.next)`), which BMv2 models as `extract` with
  `type: stack`.

### (e) Table keys, entries and priorities

- Keys: `Key { Expr expr; MatchKind kind (EXACT|LPM|TERNARY); uint32 name }`,
  which is SpecTec's `tableKeyIR = e # name : matchKind` and p4c's
  `KeyElement { expression; matchType }` with `TableKeyNames`. 4ward
  carries only `TableKey { field_name; expr }` because P4Info owns the
  match kind; p4blo has no P4Info, so the kind lives here. A fixed enum,
  not a `match_kind` declaration (SpecTec's `MATCH_KIND` type and p4c's
  `Declaration_MatchKind` exist to make `match_kind` extensible per
  architecture; p4blo's scope fixes the three).
- Entries: one `Entry { repeated EntryKey keys; uint32 action_id; repeated
  Literal args; int32 priority }` with `EntryKey { oneof { Literal exact;
  Lpm { Literal value; uint32 prefix_len }; Ternary { Literal value;
  Literal mask } } }`, which is BMv2's `entries[].match_key` with
  `prefix_length` / `mask` and `priority` exactly. Reuse this same
  message for the `TableEntries` input of a control block and for the
  STF runner's `add` lines: the design's block signature takes entries as
  data, and BMv2 proves the same shape serves both const entries and
  runtime-installed ones (`action_entry {action_id, action_data}`).
- Table: `Table { name; repeated Key keys; repeated uint32 action_ids;
  DefaultAction default_action { action_id; args }; repeated Entry
  const_entries; optional uint32 size }`. p4c `Entry` also has `isConst`
  and `singleton` and SpecTec has `constOptIR`; p4blo's entries in the IR
  are all const by construction, so a flag is unnecessary. p4c's frontend
  `EntryPriorities` pass assigns priorities to const entries lacking them
  (with `largest_priority_wins` default), and SpecTec's
  `PRIORITY = integerLiteral` is optional; p4blo should require an
  explicit priority on every ternary entry and make its tie-break a closed
  behavior in `semantics.md` (the design already lists "LPM and ternary
  tie-breaking").
- The apply result. SpecTec types `t.apply()` as `TABLE_STRUCT { HIT; MISS;
  ACTION_RUN TABLE_ENUM }`; 4ward has `TableApplyExpr { table_name;
  RESULT|HIT|MISS }` and a `SwitchStmt` whose subject is always a table
  apply; p4c has `Type_ActionEnum` and the midend `TableHit` pass. Since
  the design elaborates `switch` on `action_run` away, the schema still
  needs an `Apply { uint32 table_id; optional uint32 hit_local; optional
  uint32 action_run_local }` statement whose action-run result has a
  per-table enum type (or `bit<N>` over action ids), so that the frontend
  can rewrite `switch (t.apply().action_run) { a: ... }` into an `if`
  chain. Without that local, the elaboration has nothing to switch on.

### (f) What SpecTec's IL still contains and p4blo must decide on

From section 1, "still present in the IL". The recommended disposition,
each with the p4c pass that performs the elaboration and can be cited in
`coverage.md`:

| IL construct | p4blo | Elaboration precedent |
|---|---|---|
| Type parameters on parser/control/function/extern, type args on calls, generic `STRUCT`/`HEADER` | elaborate away | p4c `SpecializeGenericTypes`, `SpecializeGenericFunctions`, `SpecializeAll`, `BindTypeVariables`; 4ward "generics instantiated" |
| `INT` (arbitrary precision) | elaborate away | SpecTec `Cast_impl_neq/fixBit` plus `ConstantFolding`; every literal gets `nat W int` width |
| Implicit casts | already explicit in the IL (`$apply_cast`) | keep one `Cast` node, no `implicit` flag (unlike p4c `Cast.implicit`) |
| `TUPLE`, `LIST`, `SEQ`, `RECORD` (`...`), `DEFAULT` | elaborate away | p4c `EliminateTuples`, `StructInitializers`, `DefaultValues`, `CopyStructures`/`NestedStructs` |
| `HEADER_INVALID` literal | elaborate to `setInvalid` on the target | p4c `EliminateInvalidHeaders` |
| `switch` (on expressions and on `action_run`) | elaborate away | p4c `SimplifySwitch`, `SwitchAddDefault`, `EliminateSwitch`; needs the `Apply` statement from (e) |
| `return`, `exit` | out by scope (design) | p4c `RemoveReturns`, `RemoveExits` exist, so "elaborated away" is also defensible for `return` |
| `for`, `break`, `continue` | exclude (P4-16 1.2.5 addition) | p4c `ParsersUnroll` for parser loops only |
| Compound assignment `+=` | elaborate away | p4c `RemoveOpAssign` |
| Named and `_` don't-care arguments | elaborate to positional | p4c `OrderArguments`, `RemoveDontcareArgs`, `DefaultArguments` |
| Direct application `p.apply(...)` and instantiations | keep as sub-block call with an instance | design: "a block may call another block"; p4c `InstantiateDirectCalls` makes it an instance first |
| Object initializers, abstract extern methods | exclude | none needed |
| `VARBIT`, `HEADER_UNION`, value sets | out by scope (design) | p4c has no removal pass; genuinely excluded |
| `STRING`, `MATCH_KIND` types | exclude / fixed enum | only annotations and `log_msg` use strings |
| Custom table properties (`size`, `implementation`, direct resources) | `size` informative, rest out by thesis | 4ward moves them to P4Info |
| `TABLE_STRUCT` apply result | keep as `Apply` statement outputs | see (e) |
| Typed l-values, `ctk` | keep l-values, drop `ctk` | see (b) |
| Annotations | drop, except the control-plane name | p4c `HierarchicalNames`, 4ward `ControlPlaneBinding` |
| `.`-prefixed (top-level) names | resolved by ids | p4c `Path.absolute` |
| Package types and instantiation | out by thesis | SpecTec `7-instantiation`/`9-arch`, 4ward `Architecture`, BMv2 root |

A useful framing for the design doc: p4blo's IR is SpecTec's IL *after*
`7-instantiation` has run (objects and type arguments resolved) with `INT`
and the synthesized literal types folded into typed literals, and with the
package/architecture layer (`9-arch`) removed. That is the same cut 4ward
makes at p4c's midend, minus P4Info.

### (g) Where the prior art contradicts the design and a decision is needed

1. **Names as ids versus names as strings.** 4ward's first design
   principle is the opposite of the design's "names are ids", chosen for
   readability of the raw proto. The design already answers this
   (readability through the printer), but should say so in
   `.agents/decisions.md` citing 4ward, and should acknowledge that the hand-written
   forwarder in build step 1 will be the least readable artifact of the
   project for exactly this reason.
2. **Packet and header operations as method calls versus as statements.**
   4ward, p4c and SpecTec all model `extract`, `emit`, `lookahead`,
   `advance`, `isValid`, `setValid`, `push_front`, `pop_front` as method
   calls on extern or built-in objects (`packet_in`, `packet_out`, header,
   stack); only BMv2 has dedicated ops. The design's Block signature
   (`parse : Packet × M -> ...`) has no `packet_in` value, and the Lean
   semantics is simpler with dedicated statement kinds than with
   method-name dispatch. Recommendation: dedicated nodes, and record that
   this is a deliberate divergence from SpecTec's IL, which the printer
   reverses trivially. The `Externs` section's "method signatures and
   call sites" then applies only to declared externs, not to packet or
   header built-ins.
3. **`int<N>`.** Present in all four; absent from the design's "In" list.
   Decide and record (see (a)).
4. **Table entries and match kinds live in P4Info for 4ward.** p4blo has no
   P4Info (P4Runtime is a non-goal), so the schema must own match kinds,
   default actions, const entries and priorities, and the runtime entry
   message. This is not a contradiction so much as a place where 4ward
   cannot be copied; BMv2's `entries`/`default_entry` is the model.
5. **Arithmetic semantics.** BMv2 computes "with infinite precision" and
   truncates on assignment, patched with `two_comp_mod`/`sat_cast`;
   SpecTec's `3-operations` and p4c's typed nodes wrap at every operator's
   width. p4blo's "wrapping arithmetic" and per-node types follow SpecTec.
   Since BMv2 is an oracle, the differential tests should include cases
   where an intermediate overflow feeds a comparison or a shift, where the
   two models could in principle diverge if p4c's inserted `two_comp_mod`
   were missing; expect agreement, but test it.
6. **Header stacks.** BMv2 flattens a stack to N named header instances
   plus `stack_field`/`dereference_header_stack`/`last_stack_index`/
   `size_stack` ops; 4ward has `HeaderStackType { element_type; size }`
   and `ArrayIndex`; SpecTec has `HEADER_STACK typeIR [ nat ]` with a
   `nat` next index in the value. p4blo should follow SpecTec/4ward: a
   stack type, an `Index` expression with a runtime index, `next`/`last`/
   `lastIndex` as expression kinds or as sugar the frontend rewrites, and
   `push_front`/`pop_front` statements. Out-of-range index is already a
   closed behavior in the design.
7. **Header validity.** BMv2 exposes `$valid$` as a read-only 1-bit
   pseudo-field; the others use `isValid()` calls. An `IsValid` expression
   node plus `SetValid`/`SetInvalid` statements is the clean encoding;
   assignment of whole headers must copy validity (p4c `SetHeaders`,
   BMv2 `assign_header`), which `semantics.md` should state.
8. **Parser loop bound.** The design claims BMv2 "effectively implements"
   the no-consumption revisit rule. `JSON_format.md` says nothing about
   loop detection; that claim needs to be verified in BMv2's parser
   source (`src/bm_sim/parser.cpp`) or in p4c's `ParsersUnroll`, and is
   not confirmed by this survey.
9. **Deparser as a block versus as an order list.** BMv2's deparser is
   `{name, order: [headers]}`; the others make it a control with `emit`
   calls. The design's `deparse : H -> Packet` is a control-shaped block
   restricted to `emit`, which is the SpecTec/4ward/p4c view and prints
   directly; keep it, and let the validator enforce "only emit" per the
   per-kind statement rule already in the design.
10. **Field numbering.** 4ward pins `Type` and `SourceInfo` at field 100 on
    every message and keeps semantic fields at 1-7; `edition = "2024"`.
    p4blo uses `buf` lint, which will want `proto3` or an edition and
    consistent numbering; reserving 100+ for non-semantic annotations is a
    cheap convention to adopt now.

### Sources

- P4-SpecTec: `spec/4-p4-ir/4.0-ir-syntax.watsup`,
  `spec/2-static-runtime/2.2.1-type.watsup`,
  `spec/2-static-runtime/2.1.1-value.watsup`,
  `spec/3-operations/3-operations.watsup`,
  `spec/5-typing/5.05.2-typing-casting.watsup`,
  `spec/1-p4-surface/1-syntax.watsup`, repository README.
- BMv2: `docs/JSON_format.md`.
- 4ward: `simulator/ir.proto`, repository README.
- p4c: `ir/base.def`, `ir/expression.def`, `ir/type.def`, `ir/ir.def`,
  `frontends/p4/frontend.cpp`, `backends/bmv2/simple_switch/midend.cpp`.

Fetch notes: all fetches succeeded. The summaries of `2.1.1-value.watsup`
and the `unop`/`binop` lists came back partial on the first pass and were
re-fetched with narrower prompts; the value constructor names above are
the category-level productions the file exposes, not the leaf constructors.
