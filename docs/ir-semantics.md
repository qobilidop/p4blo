# IR semantics

The meaning of a p4blo program with the architecture taken out: what a
parser, control or deparser computes from its inputs, and every behavior
P4 leaves open, undefined or target-defined that the IR closes, each with
its choice and the reason. Nothing here knows about ports, packet fate,
payloads or what happens after a rejection; those are decisions of the
architecture that calls the blocks, and [arch-supports.md](arch-supports.md)
records them for the architectures this repository supplies, together
with the concrete externs they provide.

This page is the deviation ledger. p4blo's IR semantics is claimed equal
to P4-SpecTec's architecture-free semantics up to elaboration and the
deviations listed here; an unlisted difference from SpecTec is a bug on
one side. The Lean definitions in `spec/ir/P4bloIR/` are the executable
form of this meaning: executable and proved, checked against SpecTec. The
independent Python interpreter is tested against the Lean definitions, not
proved equivalent to them. What is proved, what is tested and the current
input domain and trust boundary are in
[assurance.md](assurance.md#supported-profile).

A behavior is added here before it is implemented. A divergence
between interpreters that turns out to be an unlisted open behavior is
resolved by adding it here, not by patching one side. A divergence
between p4blo and an oracle that traces to an entry here is documented,
not a failure; claim 2 allows exactly those.

## How to read an entry

Each entry is a bullet with a bold behavior name, then p4blo's choice and
its reason in prose, then six lines in this order:

- `P4:` the section of the P4-16 language specification, version 1.2.5,
  or `none` when no section decides it.
- `SpecTec:` the rules, relations or functions that decide the behavior
  in P4-SpecTec at commit `2730cfd9`, the commit the oracle build pins, or
  `none` when no architecture-free rule does. SpecTec's own names are
  used: a rule is `Relation/rule`, a function starts with `$`. Behavior
  that SpecTec implements in its simulator's OCaml code rather than in
  its rules, such as `packet_in.extract`, is named in the class line.
- `Lean:` the definitions under `spec/ir/P4bloIR/` that implement it
  and the theorems, if any, that state what they do on the case; or
  `none` and the reason when only the validator does.
- `Python:` the dotted names in the `p4blo` package that implement it.
- `Test:` the tests or corpus programs that exercise it.
- `Class:` one of four classes, then one sentence saying what SpecTec
  does at the cited rule.
  - *same*: SpecTec's rule decides the same thing.
  - *refines undefined*: SpecTec leaves it open, because no rule applies,
    the rule belongs to the architecture, or the specification says
    undefined, and p4blo closes it.
  - *deviates*: SpecTec decides differently and p4blo knowingly differs,
    for the reason the prose gives.
  - *not representable*: the situation cannot arise in SpecTec's IL.

`tests/test_ledger.py` checks the shape of every entry, that every Lean
and Python name exists where it is cited, that every test reference names
a test, the counts below, and each entry's class against
`tests/ledger-classes.json`; `tests/test_spectec_rules.py` checks that
every SpecTec name exists at the pinned commit.

| Class | Entries |
|---|---|
| same | 42 |
| refines undefined | 7 |
| deviates | 5 |
| not representable | 2 |
| total | 56 |

The sections follow the order of SpecTec's operations and dynamic rules:
values and operations (`3-operations`), expressions, lvalues, statements
and calls, parsers, tables (`8-dynamic`), then the deparser's emit and
externs, which SpecTec implements in its simulator.

## Values and operations

Every value of type `bit<N>` is an unsigned integer in `[0, 2^N)`. A
value carries its width at run time; the interpreters never infer a
width from context. `bool` is `true` or `false`. Enum and error values
are members of their declaration, compared by name. A header value is a
validity bit plus one value per field; a struct value is one value per
field. A stack of size `S` holds `S` header values and a `nextIndex` in
`[0, S]`.

- **Arithmetic on `bit<N>`.** `+`, `-` and `*` wrap modulo `2^N`
  (§8.6). `|+|` and `|-|` saturate at `2^N - 1` and `0`. There is no
  division or modulo in the IR; P4 defines them only on compile-time
  constants, which the frontend folds.
  - P4: §8.6
  - SpecTec: `$bin_plus`, `$bin_minus`, `$bin_mul`, `$bin_satplus`, `$bin_satminus`, `$bin_div`, `$bin_mod`
  - Lean: `bitsBinary`, `Bits.wrap`
  - Python: `p4blo.interp.expr.bits_binary`, `p4blo.interp.values.Bits.wrap`
  - Test: `tests/test_interp_expr.py::test_bits_arithmetic`, `tests/test_interp_expr.py::test_wrapping_arithmetic_agrees_with_modular`, `tests/test_interp_expr.py::test_saturating_operators_clamp`
  - Class: same. For `bit<N>` operands `$bin_plus`, `$bin_minus` and `$bin_mul` reduce modulo `2^N`, `$bin_satplus` and `$bin_satminus` clamp at `2^N - 1` and `0`, and `$bin_div` and `$bin_mod` reach p4blo only as folded constants.
- **Unary and bitwise operators.** On `bit<N>`, `~x` is `2^N - 1 - x`
  and `-x` is `2^N - x` reduced modulo `2^N`; `&`, `|` and `^` act on
  each bit of two operands of one width. `!` negates a `bool`.
  - P4: §8.6
  - SpecTec: `$un_bnot`, `$un_minus`, `$un_lnot`, `$bin_band`, `$bin_bor`, `$bin_bxor`
  - Lean: `evaluate`, `bitsBinary`
  - Python: `p4blo.interp.expr.unary`, `p4blo.interp.expr.bits_binary`
  - Test: `tests/test_interp_expr.py::test_unary_operators`, `tests/test_interp_expr.py::test_bits_arithmetic`
  - Class: same. `$un_bnot` and `$un_minus` compute the same residues for `bit<N>`, `$un_lnot` negates a boolean, and `$bin_band`, `$bin_bor` and `$bin_bxor` act bitwise at the operands' width.
- **Shifts.** `<<` and `>>` on `bit<N>` by an amount `k`: if `k >= N`
  the result is `0`; otherwise the usual logical shift, with the left
  shift truncated to `N` bits (§8.6). The shift amount is any `bit<M>`
  value; its width does not affect the result. An amount above 2048
  also gives `0`. SpecTec's simulator has no outcome there: its builtin
  shift stops with "shift amount too large". That is a limit of the
  oracle, so no vector shifts by more than 2048.
  - P4: §8.6
  - SpecTec: `$bin_shl`, `$bin_shr`
  - Lean: `bitsBinary`, `ScalarLaws.shl_large`, `ScalarLaws.shr_large`, `DeviationLaws.evaluate_shl_large`, `DeviationLaws.evaluate_shr_large`
  - Python: `p4blo.interp.expr.bits_binary`
  - Test: `tests/test_interp_expr.py::test_shift_amount_width_does_not_matter`, `tests/test_interp_expr.py::test_shifts_by_the_width_or_more_give_zero`
  - Class: same. `$bin_shl` and `$bin_shr` shift the unbounded integer and reduce it to the left operand's width, which gives `0` for an amount of `N` or more whatever the amount; the simulator's builtins `$shl` and `$shr`, in `numerics.ml`, stop with "shift amount too large" above 2048, which is an oracle limitation of the simulator, not a rule disagreement.
- **Comparison.** `<`, `<=`, `>`, `>=` compare as unsigned integers.
  `==` and `!=` are defined on every type: on `bit<N>` and `bool` by
  value, on enums and errors by member, on headers by validity and
  then fieldwise, on structs fieldwise, on stacks elementwise over all
  `S` elements and not on `nextIndex` (§8.16, §8.17).
  - P4: §8.16, §8.17
  - SpecTec: `$bin_lt`, `$bin_le`, `$bin_gt`, `$bin_ge`, `$bin_eq`, `$bin_ne`
  - Lean: `bitsBinary`, `Value.equal`, `Value.equalList`
  - Python: `p4blo.interp.expr.bits_binary`, `p4blo.interp.values.equal`
  - Test: `tests/test_interp_expr.py::test_comparisons_are_unsigned`, `tests/test_interp_expr.py::test_equality_on_every_type`, `tests/test_values.py::test_struct_and_stack_equality_are_elementwise`, `tests/test_values.py::test_stack_equality_ignores_next_index`
  - Class: same. `$bin_lt` and its siblings compare `bit<N>` values as unsigned integers, and `$bin_eq` compares bits, booleans, enums, errors and structs the same way and stacks elementwise ignoring the next index; wherever a header is compared, including inside a stack, the next entry applies.
- **Header equality** on two invalid headers is `true` regardless of
  fields; on one valid and one invalid is `false` (§8.17). On two valid
  headers it compares the fields. This is P4's rule.
  - P4: §8.17
  - SpecTec: `$bin_eq`
  - Lean: `Value.equal`, `DeviationLaws.header_equal_invalid`, `DeviationLaws.header_equal_valid_invalid`, `DeviationLaws.header_equal_valid`, `DeviationLaws.evaluate_eq_invalid_headers`
  - Python: `p4blo.interp.values.equal`
  - Test: `tests/test_values.py::test_header_equality_by_validity_then_fields`, `tests/test_interp_expr.py::test_equality_on_every_type`
  - Class: deviates. `$bin_eq` on two headers compares their type and stored fields and ignores the validity bit, so two invalid headers with different stored fields are unequal and a valid and an invalid header with equal fields are equal, which contradicts P4's rule.
- **Casts.** `bit<N>` to `bit<M>` truncates to the low `M` bits when
  `M < N` and zero-extends when `M > N`. `bool` to `bit<1>` maps
  `false` to `0` and `true` to `1`; `bit<1>` to `bool` is the inverse.
  No other cast exists in the IR; the frontend elaborates every other
  P4 cast, including serializable enums, into these (§8.11).
  - P4: §8.11
  - SpecTec: `$cast_op`, `$cast_int`, `$cast_bool`
  - Lean: `castValue`
  - Python: `p4blo.interp.expr.cast`
  - Test: `tests/test_interp_expr.py::test_casts`, `tests/test_interp_expr.py::test_cast_truncates_or_zero_extends`, `tests/test_validator.py::test_bit1_and_boolean_casts_are_fine`
  - Class: same. `$cast_int` reduces a `bit<N>` value modulo `2^M` for `bit<M>` and maps a nonzero `bit<1>` to `true`, and `$cast_bool` maps `false` and `true` to `0` and `1`.
- **Slices.** `e[hi:lo]` has width `hi - lo + 1` and the validator
  requires `hi < N` and `lo <= hi`, so no slice is ever out of range at
  run time.
  - P4: none
  - SpecTec: `$bitacc_range_op`
  - Lean: `evaluate`
  - Python: `p4blo.interp.expr.slice_bits`
  - Test: `tests/test_interp_expr.py::test_slice`, `tests/test_interp_expr.py::test_concat_then_slice_roundtrips`, `tests/test_validator.py::test_slice_range`
  - Class: same. `$bitacc_range_op` takes bits `hi` down to `lo` as a value of width `hi - lo + 1`.
- **Concatenation.** `a ++ b` has width `N + M` with `a` in the high
  bits.
  - P4: none
  - SpecTec: `$bin_concat`
  - Lean: `bitsBinary`
  - Python: `p4blo.interp.expr.bits_binary`
  - Test: `tests/test_interp_expr.py::test_concat_puts_left_in_the_high_bits`, `tests/test_interp_expr.py::test_concat_then_slice_roundtrips`
  - Class: same. `$bin_concat` shifts the left operand up by the right operand's width and adds the right operand, at width `N + M`.
- **Uninitialized variables.** A block-local variable or an `out`
  parameter that is read before it is written has the value `0` for
  `bit<N>`, `false` for `bool`, the first member for enums and
  `NoError` for errors, and
  the recursively zero value with every header invalid for compound
  types. P4 leaves this undefined (§6.8); zero is chosen because it is
  the least surprising value, it is what BMv2 does at packet start,
  and it gives initialization a deterministic value.
  - P4: §6.8
  - SpecTec: `$default`, `VarDecl_eval/non-initializer`, `Copy_in_arg/out`
  - Lean: `Value.zero`, `Frame.forBlock`, `argumentValue`, `Frame.forBlock_initialized`, `DeviationLaws.zero_bits`, `DeviationLaws.zero_boolean`, `DeviationLaws.zero_error`, `DeviationLaws.zeroHeader_eq`
  - Python: `p4blo.interp.values.zero`, `p4blo.interp.env.Env.for_block`, `p4blo.interp.stmt.argument_value`
  - Test: `tests/test_interp_expr.py::test_variables_start_at_zero`, `tests/test_values.py::test_zero_is_recursive_with_invalid_headers_and_first_members`, `tests/test_interp_control.py::test_an_out_parameter_starts_at_zero`
  - Class: same. SpecTec initializes a declared variable and an `out` parameter with `$default`, which gives zero bits, `false`, the first enum member, `NoError`, invalid headers with default fields and stacks with next index `0`; its source marks the choice as a placeholder for a target-specific one.

## Expressions

- **Evaluation order.** Expressions in the IR have no side effects:
  extern calls, table applies and block calls are statements, and
  `lookahead` does not move the cursor. The order in which operands, the
  two sides of an assignment or the arguments of a call are evaluated is
  therefore unobservable. `&&`, `||` and the conditional operator
  evaluate only the operands they need; an assignment evaluates its
  right-hand side before it resolves its target. An extern call with a
  result is not an expression: it resolves the result's target before
  the call, as the next section's "Copy-back target" says, because the
  call can write its `out` arguments.
  - P4: none
  - SpecTec: `Expr_eval/land-false`, `Expr_eval/lor-true`, `Expr_eval/cond-true`, `Stmt_eval/typedLvalueIR-cont-eq-typedExpressionIR-cont`
  - Lean: `evaluate`, `Execution.dispatch`
  - Python: `p4blo.interp.expr.binary`, `p4blo.interp.expr.mux`, `p4blo.interp.stmt.assign`
  - Test: `tests/test_interp_expr.py::test_logical_operators_short_circuit`, `tests/test_interp_expr.py::test_mux_evaluates_only_the_chosen_branch`
  - Class: same. SpecTec short-circuits the same operators and resolves an assignment's target before its right-hand side, which gives the same result for an assignment of an expression because no IR expression has an effect; the timing of target resolution is observable through calls, and the copy-back entry records where p4blo differs.
- **Reading a field of an invalid header.** Returns the field's
  current stored value. A header's fields are initialized to zero and
  keep whatever was last written to them, including across
  `setInvalid`. P4 says the result is undefined (§8.17). This is the
  BMv2 behavior, chosen so that the oracle agrees rather than because
  it is principled; programs in the corpus must not depend on it, and
  the validator will warn on an unguarded read where it can see one.
  - P4: §8.17
  - SpecTec: `Expr_eval/header`, `Lvalue_read/header`
  - Lean: `fieldOf`
  - Python: `p4blo.interp.expr.field_of`
  - Test: `tests/test_interp_expr.py::test_is_valid_and_member_of_invalid_header_reads_stored_fields`
  - Class: same. `Expr_eval/header` returns the stored field whatever the validity bit.
- **`isValid`** is the validity bit.
  - P4: §8.17
  - SpecTec: `Call_eval/builtinIsValidMethodCallee-header`
  - Lean: `evaluate`
  - Python: `p4blo.interp.expr.evaluate`
  - Test: `tests/test_interp_expr.py::test_is_valid_and_member_of_invalid_header_reads_stored_fields`
  - Class: same. `Call_eval/builtinIsValidMethodCallee-header` returns the header's validity bit.
- **Index out of range.** Reading `hs[i]` with `i >= S` returns an
  invalid header whose fields are zero. Writing `hs[i]` with `i >= S`
  does nothing. Both are undefined in P4 (§8.18). This closes the
  behavior without an error because the IR has no runtime error in
  controls; a program that wants a check writes one.
  - P4: §8.18
  - SpecTec: `Expr_eval/headerStack`, `Lvalue_read/stack-out-of-bounds`, `Lvalue_write/stack-out-of-bounds`
  - Lean: `elementOf`, `writeLValue`, `DeviationLaws.evaluate_index_out_of_range`, `DeviationLaws.readLValue_index_out_of_range`, `DeviationLaws.writeLValue_index_out_of_range`, `DeviationLaws.writeLValue_member_out_of_range`
  - Python: `p4blo.interp.expr.element_of`, `p4blo.interp.expr.write_lvalue`
  - Test: `tests/test_interp_control.py::test_out_of_range_stack_read_is_a_zero_invalid_header_and_write_does_nothing`
  - Class: deviates. An out-of-range write does nothing in SpecTec too, but `Expr_eval/headerStack` reads `hs[i]` with `i >= S` as the last element, valid or not, and `Lvalue_read/stack-out-of-bounds` reads it as element `0` made invalid with its stored fields; p4blo gives one answer, an invalid zero header, in both places.
- **`hs.lastIndex`** is `nextIndex - 1` as a `bit<32>`; when
  `nextIndex == 0` its value is `2^32 - 1`, the wrapped result. P4
  says undefined. It exists only in a parser, as in P4, so `hs.last`,
  which the eDSL spells `hs[hs.lastIndex]`, does too; the validator
  rejects it in a control, an action or a deparser with `PARSER_ONLY`.
  - P4: §8.18
  - SpecTec: `Expr_eval/stack-lastIndex`, `Expr_ok/headerStack-lastIndex`
  - Lean: `evaluate`, `DeviationLaws.evaluate_lastIndex`, `DeviationLaws.lastIndex_empty`, `DeviationLaws.lastIndex_nonempty`
  - Python: `p4blo.interp.expr.last_index`, `p4blo.validator._Validator.type_of`
  - Test: `tests/test_interp_parser.py::test_last_index_wraps_at_next_index_zero`, `tests/test_interp_expr.py::test_stack_index_and_last_index`, `tests/test_validator.py::test_parser_only`, `tests/test_validator.py::test_last_index_in_a_parser_is_fine`
  - Class: deviates. `Expr_eval/stack-lastIndex` computes `max(nextIndex, 1) - 1`, which is `0` when `nextIndex == 0`, and p4blo keeps the 32-bit arithmetic of `nextIndex - 1`; `Expr_ok/headerStack-lastIndex` types it only in a parser, as the validator does.
- **`hs.last` on an empty stack.** The IR has no `last`; `hs.last` is
  elaborated to `hs[hs.lastIndex]`. With `nextIndex == 0` that indexes
  element `2^32 - 1`, which reads as a zero invalid header by the
  out-of-range rule and raises no error. P4 and SpecTec reject there
  with `StackOutOfBounds`. The elaboration is the deviation: it is not
  how the language defines `hs.last` at `nextIndex == 0`, and the
  coverage table says so on its `hs.last` row.
  - P4: §8.18
  - SpecTec: `Expr_eval/stack-last-out-of-bounds`, `Lvalue_eval/stack-last-out-of-bounds`, `Expr_eval/stack-last-in-bounds`
  - Lean: `evaluate`, `elementOf`, `DeviationLaws.evaluate_last_empty`, `DeviationLaws.evaluate_last_nonempty`
  - Python: `p4blo.edsl.views.Stack.last`, `p4blo.interp.expr.last_index`, `p4blo.interp.expr.element_of`
  - Test: `tests/test_edsl.py::test_stack_last_is_the_element_at_last_index`, `tests/test_interp_parser.py::test_last_index_wraps_at_next_index_zero`, `tests/corpus/stacks`
  - Class: deviates. `Expr_eval/stack-last-out-of-bounds` and `Lvalue_eval/stack-last-out-of-bounds` reject with `StackOutOfBounds` when `nextIndex` is `0` or above the size, and `Expr_eval/stack-last-in-bounds` reads element `nextIndex - 1` otherwise, which the elaboration matches only for `nextIndex >= 1`.

## Lvalues and assignment

- **Writing a field of an invalid header.** Stores the value and does
  not change validity. Same reason as reading one.
  - P4: §8.17
  - SpecTec: `Lvalue_write/header`
  - Lean: `setField`, `writeLValue`
  - Python: `p4blo.interp.expr.write_lvalue`
  - Test: `tests/test_interp_control.py::test_writing_a_field_of_an_invalid_header_stores_it_and_keeps_it_invalid`
  - Class: same. `Lvalue_write/header` replaces the field and keeps the header's validity bit.
- **Assigning a header** copies validity and all fields. Assigning an
  invalid header makes the target invalid and copies the fields
  anyway, so that a later read sees the same thing on both sides.
  - P4: §8.17
  - SpecTec: `Stmt_eval/typedLvalueIR-cont-eq-typedExpressionIR-cont`, `Lvalue_write/referenceExpressionIR`, `Lvalue_write/memberAccess`
  - Lean: `writeLValue`
  - Python: `p4blo.interp.expr.write_lvalue`
  - Test: `tests/test_interp_control.py::test_assigning_a_header_copies_validity_and_fields`
  - Class: same. An assignment writes the whole header value, validity bit and stored fields, to the target.
- **`hs.next`** appears only as the target of an extract; the validator
  rejects it anywhere else, so no assignment, `setValid`, field write
  or argument ever goes through it. Extracting into it with
  `nextIndex == S` is a parse error `StackOutOfBounds` and consumes
  nothing; this is checked before the packet is, so a full stack and a
  short packet together report `StackOutOfBounds`. On success it fills
  `hs[nextIndex]`, sets it valid, and increments `nextIndex`.
  Extracting into `hs[i]` with `i >= S` consumes the bits and stores
  nothing, by the out-of-range write rule.
  - P4: §8.18
  - SpecTec: `Lvalue_eval/stack-next-out-of-bounds`, `Lvalue_write/stack-next`, `Lvalue_write/stack-out-of-bounds`
  - Lean: `extract`, `readLValue`
  - Python: `p4blo.interp.stmt.extract`, `p4blo.validator._Validator.check_extract`
  - Test: `tests/test_interp_parser.py::test_extract_into_a_full_stack_is_stack_out_of_bounds`, `tests/test_interp_parser.py::test_a_full_stack_is_reported_before_a_short_packet`, `tests/test_interp_expr.py::test_next_is_not_an_lvalue_outside_extract`, `tests/test_validator.py::test_next_only_extract_in_a_parser`, `tests/corpus/stacks`
  - Class: same. SpecTec resolves the `out` argument `hs.next` while copying in, so a full stack rejects with `StackOutOfBounds` before the packet is read, and the copy-out through `Lvalue_write/stack-next` fills the element and increments the index; SpecTec also accepts `hs.next` elsewhere, which the IR excludes.

## Statements and calls

- **`setValid` on a valid header** and **`setInvalid` on an invalid
  one.** No effect on the fields.
  - P4: §8.17
  - SpecTec: `Call_eval/builtinSetValidMethodCallee`, `Call_eval/builtinSetInvalidMethodCallee`
  - Lean: `setValidity`
  - Python: `p4blo.interp.stmt.set_validity`
  - Test: `tests/test_interp_control.py::test_set_valid_and_set_invalid_touch_only_validity`
  - Class: same. Both rules rewrite the validity bit and keep the stored fields.
- **`push_front(n)`** shifts elements toward higher indices by `n`,
  discards the last `n`, makes the first `n` invalid with zero fields,
  and sets `nextIndex` to `min(nextIndex + n, S)`. **`pop_front(n)`**
  shifts toward lower indices, makes the last `n` invalid with zero
  fields, and sets `nextIndex` to `max(nextIndex - n, 0)` (§8.18).
  With `n > S` both behave as `n = S`: every element becomes invalid
  and `nextIndex` goes to `S` or `0`. The `nextIndex` rules are P4's;
  zero fields make a later read of an invalid element deterministic.
  - P4: §8.18
  - SpecTec: `Call_eval/builtinPushFrontMethodCallee`, `Call_eval/builtinPopFrontMethodCallee`, `$invalidate_value`
  - Lean: `pushFront`, `popFront`, `DeviationLaws.pushFront_spec`, `DeviationLaws.pushFront_clamp`, `DeviationLaws.popFront_spec`, `DeviationLaws.popFront_clamp`
  - Python: `p4blo.interp.stmt.push_front`, `p4blo.interp.stmt.pop_front`
  - Test: `tests/test_interp_control.py::test_push_front_shifts_up_and_pops_the_last`, `tests/test_interp_control.py::test_pop_front_shifts_down_and_clears_the_last`, `tests/test_interp_control.py::test_push_and_pop_of_more_than_the_size_clip_to_the_size`
  - Class: deviates. SpecTec shifts the same way but invalidates the vacated elements with `$invalidate_value`, which keeps stored fields: after `push_front(n)` the first `n` elements keep their own old fields, `pop_front(n)` rotates the first `n` elements to the back and invalidates them there, and `pop_front(n)` with `n < S` sets `nextIndex` to `S - n` instead of `nextIndex - n`.
- **Block calls.** A sub-block call copies `in` arguments in, resolves
  `out` and `inout` ones, runs the block, and copies `out` and `inout`
  arguments back in parameter order. Two `out` or `inout` arguments that alias the same storage
  are a validator error, so copy order never matters; an `in` argument
  may overlap them, since it is copied in before anything is written
  (§6.8).
  - P4: §6.8
  - SpecTec: `Call_eval/controlApplyMethodCallee`, `Call_eval/parserApplyMethodCallee`, `Copy_in`, `Copy_out`
  - Lean: `argumentValue`, `copyIn`, `copyBack`, `Execution.dispatch`
  - Python: `p4blo.interp.stmt.call_block`, `p4blo.interp.stmt.argument_value`, `p4blo.interp.stmt.copy_in`, `p4blo.interp.stmt.copy_back`, `p4blo.validator._Validator.check_args`
  - Test: `tests/test_interp_control.py::test_sub_control_call_copies_in_and_out`, `tests/test_interp_control.py::test_an_in_argument_overlapping_an_inout_one_is_copied_in_first`, `tests/test_validator.py::test_call_alias`, `tests/test_validator.py::test_no_alias`
  - Class: same. `Copy_in` evaluates every argument into the callee's frame before the body runs and `Copy_out` writes `out` and `inout` parameters back in parameter order; where a copy-back lands is the next entry.
- **Copy-back target.** An `out` or `inout` argument is resolved once,
  at copy-in: every index expression inside it is evaluated then, in
  argument order, and copy-back writes through the element it named,
  even if the call has since changed a variable the index reads. An
  action can change one directly, since it sees its block's variables;
  a block or extern call can change one through another `out` argument
  copied back earlier. An extern call's result target is resolved the
  same way, before the call. `hs.next` is not resolved here; only an
  extract uses it. P4 resolves the lvalue once, at copy-in (§6.8).
  - P4: §6.8
  - SpecTec: `Copy_in_arg/inout`, `Copy_in_arg/out`, `Copy_out_argument/non-dontcare`, `Stmt_eval/typedLvalueIR-cont-eq-typedExpressionIR-cont`
  - Lean: `resolveLValue`, `resolveArg`, `copyIn`, `copyBack`, `callExtern`, `Execution.dispatch`
  - Python: `p4blo.interp.expr.resolve_lvalue`, `p4blo.interp.stmt.resolve_arg`, `p4blo.interp.stmt.copy_in`, `p4blo.interp.stmt.copy_back`, `p4blo.interp.stmt.call_extern`
  - Test: `tests/test_lean_call_copyback.py::test_lean_agrees_copyback_writes_the_element_resolved_at_copy_in`, `tests/test_lean_call_copyback.py::test_lean_agrees_copyback_with_an_overlapping_in_argument`, `tests/test_lean_call_copyback.py::test_lean_agrees_extern_out_and_result_through_computed_indices`
  - Class: same. `Copy_in_arg/inout` and `Copy_in_arg/out` keep the argument's storage reference with its index evaluated at copy-in, `Copy_out_argument/non-dontcare` writes through that reference, and an assignment of an extern call's result resolves its target before the call.
- **Actions read and write their block's variables.** An action runs in
  its block's activation with its parameters layered on top, so it
  reads the block's current variables and its writes to them persist.
  When it returns, the block's variables as the action left them are
  kept first, and then its `out` and `inout` parameters are copied back
  to the arguments.
  - P4: §6.8
  - SpecTec: `Call_eval/actionCallee`, `$inherit_e`, `Copy_out`, `$copy_e`
  - Lean: `Execution.dispatch`, `Execution.Work`, `copyBack`
  - Python: `p4blo.interp.stmt.call_action`, `p4blo.interp.env.Env.enter_action`, `p4blo.interp.stmt.copy_back`
  - Test: `tests/test_interp_control.py::test_an_action_sees_the_blocks_variables`, `tests/test_interp_control.py::test_direct_action_call_passes_directional_arguments`
  - Class: same. `Call_eval/actionCallee` builds the callee's context with `$inherit_e`, which keeps the block layer and adds a fresh local one, and `Copy_out` first takes the block layer back with `$copy_e` and then writes each argument, the same order as p4blo's.
- **Action calls** from a control body pass arguments in the same
  way. Actions invoked by a table receive their action data as
  directionless parameters, which are read-only like `in` parameters.
  - P4: §6.8
  - SpecTec: `Call_eval/actionCallee`, `Copy_in_arg/directionless-in`
  - Lean: `Execution.dispatch`, `argumentValue`, `copyBack`
  - Python: `p4blo.interp.stmt.call_action`, `p4blo.interp.stmt.run_action_call`
  - Test: `tests/test_interp_control.py::test_direct_action_call_passes_directional_arguments`, `tests/test_interp_control.py::test_apply_runs_the_matching_action_and_records_hit`
  - Class: same. `Call_eval/actionCallee` copies arguments in and out as a block call does and binds directionless parameters like `in` ones.
- **Recursion** between blocks is a validator error. Actions may call
  actions; the call graph of actions and blocks together is acyclic,
  as the intended termination discipline. The check is the validator's
  alone: the interpreters assume an acyclic graph and do not check it.
  A joint theorem connecting whole-program validation, this graph and
  the parser revisit rule to termination of the actual runner has not
  been proved.
  - P4: none
  - SpecTec: none
  - Lean: none; the Lean definitions assume the validator's check and do not repeat it.
  - Python: `p4blo.validator._Validator.check_call_graph`
  - Test: `tests/test_validator.py::test_call_cycle`, `tests/test_validator.py::test_action_call_cycle`, `tests/test_validator.py::test_actions_may_call_actions_without_a_cycle`
  - Class: not representable. P4 has no recursive calls, so no IL program SpecTec evaluates contains one: its typing rejects an action that calls itself, declaration before use rules out mutual recursion between actions, and instantiation rules it out between blocks.

## Parsers

A parser runs over a packet with a cursor in bits, starting at zero.
Its outcome is the headers, the metadata, the number of bits
consumed, whether it accepted, and an error. Rejection and error are
separate: an explicit transition to `reject` rejects with `NoError`,
and a raised error rejects with that error (§12.7). The outcome is
returned to the caller; what follows a rejection is the architecture's
decision, not the parser's.

- **A raised error stops the parser.** On a raised error the parser
  stops immediately with the headers and metadata as they were at that
  moment. A sub-parser's `out` and `inout` arguments are copied back
  before the error propagates, every one of them, so an `out` argument
  the sub-parser never wrote takes its zero value, as on the success
  path; the bits consumed are counted up to that moment. An explicit
  `reject` inside a sub-parser rejects the whole run the same way.
  - P4: §12.7
  - SpecTec: `Call_eval/copyin-cont-parserLocalDeclarationListIR-cont-transition-reject`, `ParserState_trans/reject`
  - Lean: `Execution.step`, `runParser`
  - Python: `p4blo.interp.parser.run_parser`, `p4blo.interp.stmt.call_block`
  - Test: `tests/test_interp_parser.py::test_an_error_keeps_the_partial_headers_and_metadata`, `tests/test_interp_parser.py::test_sub_parser_error_copies_back_before_propagating`, `tests/corpus/parser_error`, `tests/corpus/subparser_stack`
  - Class: same. A rejection propagates from the rule that raised it with the state as it stands, and a sub-parser's rejecting apply still runs `Copy_out`.
- **Extraction past the packet end.** If fewer bits remain than the
  header's width, the extract raises `PacketTooShort`, consumes
  nothing, and leaves the target as it was (§12.8.2).
  - P4: §12.8.2
  - SpecTec: `Call_eval/copyin-cont-non-abstract-reject`
  - Lean: `extract`, `packetRead`
  - Python: `p4blo.interp.stmt.extract`, `p4blo.interp.packet.Packet.read`
  - Test: `tests/test_interp_parser.py::test_extract_past_the_end_is_packet_too_short_and_consumes_nothing`
  - Class: same. SpecTec's `packet_in.extract`, in its simulator's `core/object.ml`, rejects with `PacketTooShort` without moving the cursor, and `Call_eval/copyin-cont-non-abstract-reject` skips the copy-out, so the target keeps its value.
- **Extract sets the target valid** and fills every field from the
  packet, most significant bit first. A header type with no fields has
  width zero: extracting it sets validity, consumes nothing even at
  the end of the packet, and counts as no consumption for the loop
  bound below.
  - P4: §12.8.2
  - SpecTec: `$write_value_from_bits`
  - Lean: `headerFromBits`, `unpackFields`
  - Python: `p4blo.interp.expr.header_from_bits`
  - Test: `tests/test_interp_parser.py::test_extract_fills_the_fields_and_sets_valid`, `tests/test_interp_parser.py::test_extract_takes_fields_most_significant_first`, `tests/test_interp_parser.py::test_extract_of_a_zero_width_header_sets_valid_and_consumes_nothing`
  - Class: same. `$write_value_from_bits` fills the fields from the leading bits in order and sets the validity bit, and the simulator's length check passes for a zero-width header at the end of the packet.
- **Boolean header fields take one bit.** A `bool` field of a header
  is one bit on the wire: extract reads `1` as `true` and `0` as
  `false`, and emit writes `true` as `1`.
  - P4: §12.8.2, §15.1
  - SpecTec: `$write_value_from_bits'`, `$write_bits_from_value`
  - Lean: `fieldFromBits`, `fieldBits`
  - Python: `p4blo.interp.expr.header_from_bits`, `p4blo.interp.expr.header_to_bits`
  - Test: `tests/test_interp_parser.py::test_emit_then_extract_roundtrips_a_header`
  - Class: same. `$write_value_from_bits'` takes one bit for a boolean field, and `$write_bits_from_value` writes a boolean as that one bit.
- **`lookahead<T>`** reads `width(T)` bits without moving the cursor;
  past the end it raises `PacketTooShort`. `T` is `bit<N>`, `bool`
  (one bit, `1` is `true`) or a header; when `T` is a header the
  result is valid.
  - P4: §12.8
  - SpecTec: `$default`, `$write_value_from_bits`
  - Lean: `lookaheadValue`, `valueFromBits`
  - Python: `p4blo.interp.expr.lookahead`, `p4blo.interp.expr.value_from_bits`
  - Test: `tests/test_interp_parser.py::test_lookahead_reads_without_consuming_and_a_header_result_is_valid`, `tests/test_interp_parser.py::test_lookahead_past_the_end_is_packet_too_short`, `tests/test_validator.py::test_lookahead_of_bits_boolean_and_header_is_fine`
  - Class: same. The simulator's `packet_in.lookahead` fills `$default` of `T` with `$write_value_from_bits` without moving the cursor, which makes a header valid, and rejects with `PacketTooShort` past the end.
- **`advance(n)`** moves the cursor by `n` bits; past the end it
  raises `PacketTooShort` and the cursor does not move. `n` is a
  `bit<32>`, as core.p4 declares it; the frontend casts a narrower
  amount, so that the printed program is P4.
  - P4: §12.8
  - SpecTec: `Call_eval/externMethodCallee`
  - Lean: `advance`, `Packet.advance?`
  - Python: `p4blo.interp.stmt.advance`, `p4blo.interp.packet.Packet.advance`
  - Test: `tests/test_interp_parser.py::test_advance_skips_bits`, `tests/test_interp_parser.py::test_advance_past_the_end_is_packet_too_short_and_the_cursor_stays`
  - Class: same. The simulator's `packet_in.advance`, called through `Call_eval/externMethodCallee`, moves the cursor by its `bit<32>` argument or rejects with `PacketTooShort` and leaves it.
- **`verify(cond, err)`** raises `err` when `cond` is `false`. `err`
  may be `NoError`, and then the outcome is the same as an explicit
  `reject`: not accepted, error `NoError`.
  - P4: §12.7
  - SpecTec: `Call_eval/externFunctionCallee-copyin-cont-call-reject`
  - Lean: `verify`
  - Python: `p4blo.interp.stmt.verify`
  - Test: `tests/test_interp_parser.py::test_verify_raises_its_error_when_the_condition_is_false`, `tests/test_interp_parser.py::test_verify_with_no_error_is_an_explicit_reject`, `tests/corpus/verify_error`
  - Class: same. The simulator's `verify`, in `core/func.ml`, rejects with its error argument, `NoError` included, and the rejection propagates like any other.
- **`select`** evaluates the key expressions once, then tries the
  cases in order and takes the first that matches. A key set entry is
  an exact value, a value with a mask, a closed range, or don't-care;
  a mask or a range applies only to a `bit<N>` key, so a `bool`, enum
  or error key takes an exact value or don't-care. With no matching
  case, the transition is to `reject` with error `NoMatch` (§12.6).
  - P4: §12.6
  - SpecTec: `ParserSelect_eval/match`, `ParserSelect_eval/no-match`, `SelectCases_match`, `$match_keysets`, `$match_keyset`
  - Lean: `select`, `keySetMatches`
  - Python: `p4blo.interp.stmt.select`, `p4blo.interp.stmt.key_set_matches`
  - Test: `tests/test_interp_parser.py::test_select_tries_the_cases_in_order`, `tests/test_interp_parser.py::test_select_with_no_matching_case_rejects_with_no_match`, `tests/test_interp_parser.py::test_select_on_several_keys_needs_every_set_to_match`, `tests/test_validator.py::test_select_on_boolean_and_enum_keys`
  - Class: same. `ParserSelect_eval` evaluates the keys once, `SelectCases_match` takes the first case whose sets all match by `$match_keyset`, and `ParserSelect_eval/no-match` rejects with `NoMatch`.
- **`reject`** is a transition like any other. Reached explicitly, it
  rejects with `NoError`; reached because an extract, lookahead,
  advance, verify or select raised, it rejects with that error. This
  is what the P4 specification says (§12.7) and what keeps `verify`
  and explicit rejection distinguishable.
  - P4: §12.7
  - SpecTec: `ParserTransition_eval/nameIR-reject`
  - Lean: `Execution.dispatch`
  - Python: `p4blo.interp.stmt.run_states`
  - Test: `tests/test_interp_parser.py::test_explicit_reject_is_not_accepted_and_has_no_error`, `tests/test_interp_parser.py::test_verify_raises_its_error_when_the_condition_is_false`
  - Class: same. `ParserTransition_eval/nameIR-reject` rejects with `NoError`, and a raised error arrives as a rejection carrying its own error.
- **Parser loop bound.** A state may be entered any number of times
  as long as the cursor advanced since the last time it was entered.
  Entering a state with the cursor at the same position as at its
  last entry raises `ParserTimeout` (§12.11 leaves the
  bound to the target). This is the no-consumption revisit rule from
  the design doc. Sub-parser states count as states of the enclosing
  run, so a sub-parser applied twice without consumption in between
  is a timeout too. A program that loops without consuming is a bug in
  the program, so the corpus never exercises the rule against an
  oracle.
  - P4: §12.11
  - SpecTec: `ParserState_trans/state`
  - Lean: `enterState`, `DeviationLaws.enterState_revisit`, `DeviationLaws.enterState_again`, `DeviationLaws.step_state_revisit`
  - Python: `p4blo.interp.stmt.enter_state`
  - Test: `tests/test_interp_parser.py::test_revisiting_a_state_without_consuming_is_parser_timeout`, `tests/test_interp_parser.py::test_the_revisit_rule_sees_a_cycle_through_another_state`, `tests/test_interp_parser.py::test_revisiting_after_consuming_is_allowed`, `tests/test_interp_parser.py::test_sub_parser_states_count_for_the_revisit_rule`
  - Class: refines undefined. `ParserState_trans/state` recurses into the next state with no bound, so a loop that consumes nothing has no finite derivation and SpecTec gives no outcome.
- **State-local variables.** The IR has no state-local variables: a
  variable a parser declares is a local of the block, zero when the
  block starts and kept across states. SpecTec gives each state a fresh
  local frame on every entry, so a variable declared inside a state
  without an initializer takes its default again each time the state
  is entered. A hoisted state-local keeps its value across a revisit
  unless the elaboration writes the zero value where the declaration
  stood. The eDSL hoists a local without such a write, and no P4
  frontend exists yet to settle it.
  - P4: §12.4
  - SpecTec: `ParserState_eval/cont`, `$enter_e`, `$exit_e`, `VarDecl_eval/non-initializer`
  - Lean: `Frame.forBlock`
  - Python: `p4blo.interp.env.Env.for_block`
  - Test: `tests/test_interp_expr.py::test_variables_start_at_zero`, `tests/corpus/subparser_stack`
  - Class: same. On block locals, SpecTec's `VarDecl_eval/non-initializer` gives the default once per block run, as p4blo does; for a state-local, `ParserState_eval/cont` wraps each entry in `$enter_e` and `$exit_e`, and whether p4blo's elaboration matches that by writing the zero value at the declaration is undecided.
- **Errors.** The IR's error set begins with core.p4's, in this order:
  `NoError`, `PacketTooShort`, `NoMatch`, `StackOutOfBounds`,
  `HeaderTooShort`, `ParserTimeout`, `ParserInvalidArgument`. A program
  may declare more after them. The order is fixed so that every reader
  can find the core errors without a table.
  `HeaderTooShort` and `ParserInvalidArgument` are never raised by the
  IR because varbit and the extract-with-length form are out of scope;
  they are reserved so that indices agree with every reader.
  - P4: none
  - SpecTec: `errorValue`
  - Lean: `Program`
  - Python: `p4blo.ir.CORE_ERRORS`
  - Test: `tests/test_validator.py::test_error_list`
  - Class: not representable. In the architecture-free rules a SpecTec `errorValue` is a name with no position, so the order has nothing to correspond to there; SpecTec's control-plane interface in `9-arch` does index errors by position, casting an integer `n` to the `n`th error of the global frame.

## Tables

A table match is evaluated over the installed entries; the program's
`const entries` are installed first and cannot be removed.

- **Exact keys** match when every key equals the entry value.
  - P4: none
  - SpecTec: `TableMatch_eval/match`, `$match_keyset`
  - Lean: `Installed.keyValueMatches`, `Installed.lookup`
  - Python: `p4blo.interp.tables.key_value_matches`, `p4blo.interp.tables.InstalledEntries.lookup`
  - Test: `tests/test_interp_tables.py::test_exact_hit_and_miss_without_a_default`
  - Class: same. `$match_keyset` matches a single-value set by `$bin_eq`.
- **LPM.** A table has at most one `lpm` key. Among the entries whose
  other keys match exactly and whose prefix covers the key value, the
  longest prefix wins. Two entries with the same prefix length, equal
  under that prefix, and the same other keys are rejected at
  installation, so there is no tie. SpecTec's table interface also
  builds an entry's mask from the key's base instead of the computed
  mask, a known defect of the pinned oracle recorded in
  [assurance.md](assurance.md#known-disagreements-with-the-oracles).
  - P4: none
  - SpecTec: `TableMatches_eval`, `$select_action`
  - Lean: `Installed.beats`, `Installed.prefixLength`, `Installed.sameKeys`, `DeviationLaws.lookup_longest_prefix`, `DeviationLaws.lookup_hit`
  - Python: `p4blo.interp.tables.beats`, `p4blo.interp.tables.prefix_length`, `p4blo.interp.tables.same_keys`
  - Test: `tests/test_interp_tables.py::test_lpm_longest_prefix_wins_and_the_default_runs_on_a_miss`, `tests/test_interp_tables.py::test_install_rejects_duplicate_exact_and_lpm_entries`, `tests/test_validator.py::test_table_lpm_count`, `tests/corpus/forwarder`
  - Class: refines undefined. SpecTec's table interface turns an LPM entry into a masked value with no priority, and `$select_action` chooses among several matches only by priority, so two matching LPM entries without priorities have no rule; the oracle adapter supplies the prefix length as the priority, and the interface's mask construction has the known defect recorded in assurance.md.
- **Ternary.** Every entry of a table with a `ternary` key has a
  priority, and `0` is an ordinary one. Among the entries that match,
  the one with the largest priority wins. Two matching entries with equal priority are
  rejected at installation when their key sets overlap, which is
  decidable for ternary and exact keys, so there is no tie. Larger
  wins because that is what the P4Runtime specification says (§9.1);
  the STF runner converts if the oracle's convention differs. Host and
  STF ternary entries reach SpecTec through its table interface, whose
  mask construction has the known defect recorded in
  [assurance.md](assurance.md#known-disagreements-with-the-oracles).
  - P4: none; P4Runtime §9.1
  - SpecTec: `$select_action`, `$largest_priority_wins`
  - Lean: `Installed.beats`, `Installed.overlaps`, `Installed.install`, `DeviationLaws.lookup_hit`
  - Python: `p4blo.interp.tables.beats`, `p4blo.interp.tables.overlaps`, `p4blo.interp.tables.InstalledEntries.install`
  - Test: `tests/test_interp_tables.py::test_ternary_largest_priority_wins`, `tests/test_interp_tables.py::test_install_rejects_overlapping_ternary_entries_of_equal_priority`, `tests/test_validator.py::test_entry_priority_overlap`, `tests/corpus/priority`
  - Class: same. `$select_action` sorts the matches by priority and takes the largest unless the table sets `largest_priority_wins` to false, which no p4blo table does, and p4blo's installation rule leaves no equal-priority tie to break; the rule is the same, and the interface's mask-from-base defect in `9-arch` is an oracle defect, not a rule disagreement.
- **Priority outside ternary tables.** An entry of a table without a
  `ternary` key has priority `0`; the installer and the validator
  reject any other. A table with an `lpm` key has no `ternary` key, so
  among matching entries the winner is decided by prefix or by
  priority, never both. Two entries of an exact or LPM table with the
  same keys are rejected at installation. These are restrictions on the
  input: SpecTec accepts a priority on any entry, and p4blo accepts
  only the entries where that priority cannot matter. On what p4blo
  accepts, an exact table has at most one matching entry, and several
  matching LPM entries are the LPM entry's business.
  - P4: none
  - SpecTec: `$get_tableEntryPriority`, `$select_action`
  - Lean: `Installed.install`, `Installed.sameKeys`
  - Python: `p4blo.interp.tables.InstalledEntries.install`, `p4blo.validator._Validator.check_keys`
  - Test: `tests/test_validator.py::test_entry_priority_on_non_ternary_table`, `tests/test_validator.py::test_table_key_mix`, `tests/test_interp_tables.py::test_install_rejects_duplicate_exact_and_lpm_entries`
  - Class: same. On the entries p4blo accepts, an exact table matches at most one entry, and `$select_action` with a single match returns that entry's action whatever its priority; SpecTec also accepts a priority on these tables, and p4blo's refusal of one is a restriction of its input, not a disagreement.
- **Table miss.** The default action runs. A table always has a
  default action; when the program declares none, it is `NoAction`,
  which does nothing (§14.2.1.4). A program that declares an action
  named `NoAction` itself gives it no body and no parameters, so that
  the name means to every reader, and to the printer's shim, what
  core.p4 says it means; the validator rejects any other `NoAction`
  (`NOACTION_RESERVED`).
  - P4: §14.2.1.4
  - SpecTec: `$select_action`
  - Lean: `Installed.lookup`, `Table`, `DeviationLaws.lookup_miss`
  - Python: `p4blo.interp.tables.InstalledEntries.lookup`, `p4blo.validator._Validator.check_action`
  - Test: `tests/test_interp_tables.py::test_a_table_without_a_default_falls_back_to_no_action`, `tests/test_interp_control.py::test_apply_on_a_miss_runs_the_default_and_hit_is_false`, `tests/test_validator.py::test_noaction_reserved`
  - Class: same. `$select_action` with no match returns the table's default action; a missing default being `NoAction` is P4's rule, settled before SpecTec's dynamic rules run.
- **`hit`** is `true` when an entry matched and `false` on a miss,
  including a miss that ran the default action. It is written after
  the chosen action has run, so an action that writes the same lvalue
  is overwritten, as `t.apply().hit` reads the result of the apply.
  - P4: none
  - SpecTec: `Table_eval/keys-cont-matches-cont-action-cont`, `Expr_eval/tableMetadataStructValue-hit`
  - Lean: `Execution.dispatch`
  - Python: `p4blo.interp.stmt.apply`
  - Test: `tests/test_interp_control.py::test_hit_is_written_after_the_action_runs`, `tests/test_interp_control.py::test_apply_on_a_miss_runs_the_default_and_hit_is_false`
  - Class: same. `Table_eval` runs the selected action and then returns an apply result whose `hit` is whether any entry matched.
- **Key expressions** are evaluated once, before matching. The
  program's `const entries` must be canonical: an LPM value with a set
  bit outside its prefix, or a ternary value with a set bit outside its
  mask, is a validator error. That restricts behavior SpecTec defines,
  since its match masks both sides and gives a non-canonical entry the
  meaning of its canonical form; the frontend can always write that
  form, `(v & m) &&& m`, instead.
  - P4: none
  - SpecTec: `TableKeys_eval`, `TableMatches_eval`, `$match_keyset`
  - Lean: `Execution.dispatch`, `Installed.build`, `Installed.checkKeyValue`
  - Python: `p4blo.interp.stmt.apply`, `p4blo.validator._Validator.check_entry`
  - Test: `tests/test_interp_tables.py::test_exact_hit_and_miss_without_a_default`, `tests/test_validator.py::test_lpm_entry_must_be_canonical`, `tests/test_validator.py::test_ternary_entry_must_be_canonical`
  - Class: same. `TableKeys_eval` evaluates each key once before `TableMatches_eval`, as p4blo does, and on the canonical `const entries` p4blo accepts, `$match_keyset` masking both sides gives the same matches; rejecting a non-canonical one is a restriction of p4blo's input, not a disagreement.
- **Host entries are canonical.** An entry value wider than the key is
  rejected at installation, as is an LPM value with a set bit outside
  its prefix and a ternary value with a set bit outside its mask:
  entries are canonical, as P4Runtime requires (§8.1). A key value's
  kind must be the key's match kind; an exact value on a ternary key is
  written as a full mask.
  - P4: none; P4Runtime §8.1
  - SpecTec: none
  - Lean: `Installed.checkKeyValue`, `Installed.install`
  - Python: `p4blo.interp.tables.check_key_value`, `p4blo.interp.tables.InstalledEntries.install`
  - Test: `tests/test_interp_tables.py::test_install_rejects_an_entry_that_does_not_fit`, `tests/test_stf.py::test_a_non_canonical_lpm_value_is_reported_with_its_line`
  - Class: refines undefined. The architecture-free rules take the installed entries as given, and what a host may install is decided by SpecTec's table interface in `9-arch`, which belongs to the architecture.
- **Host default action.** A host may replace a non-const default
  action; it cannot remove one. Absent means the program's own.
  - P4: none
  - SpecTec: `$select_action`
  - Lean: `Installed.setDefault`
  - Python: `p4blo.interp.tables.InstalledEntries.set_default`
  - Test: `tests/test_interp_tables.py::test_host_default_replaces_a_non_const_default_and_none_restores_the_programs`, `tests/test_interp_tables.py::test_host_default_cannot_replace_a_const_default`
  - Class: same. `$select_action` runs whatever default the table holds, and SpecTec's table interface likewise replaces a default only when it is not const and has no way to remove one.
- **Entries name their action** and carry action data as constants of
  the declared parameter widths; a mismatch is rejected at
  installation.
  - P4: none
  - SpecTec: `Table_eval/keys-cont-matches-cont-action-cont`
  - Lean: `Installed.checkAction`
  - Python: `p4blo.interp.tables.InstalledEntries.check_action`
  - Test: `tests/test_interp_tables.py::test_install_rejects_action_data_that_is_not_a_constant_of_the_param`, `tests/test_interp_tables.py::test_install_rejects_an_entry_that_does_not_fit`
  - Class: refines undefined. `Table_eval` calls whatever action the chosen entry names with its arguments; action data is decided by SpecTec's table interface in `9-arch`, outside the architecture-free rules, which fills a missing argument with zero and truncates a too-wide one by a cast where p4blo rejects both.
- **Keys are bits.** A table key expression has type `bit<N>`. The
  frontend casts a boolean key to `bit<1>` and represents a plain enum
  key by its member index in `bit<32>`, as p4c's `ConvertEnums` does;
  select keys may be any scalar.
  - P4: none
  - SpecTec: `TableMatch_eval/match`, `$match_keyset`
  - Lean: `Installed.keyWidths`
  - Python: `p4blo.validator._Validator.check_keys`
  - Test: `tests/test_validator.py::test_table_keys_are_bits_only`, `tests/test_validator.py::test_key_type`
  - Class: same. `$match_keyset` compares keys of any type with `$bin_eq`, and casting a `bool` key to `bit<1>` or an enum key to its member index preserves which entries match, so the difference is elaboration.

## Deparsers

A deparser runs over the headers and produces the bytes of the emitted
headers, and nothing else; what becomes of the bytes the parser did not
consume is the caller's decision.

- **Sub-blocks.** A deparser may call only deparsers, which emit and
  never apply a table, so `deparse : H -> Packet` needs no entries.
  - P4: none
  - SpecTec: `Call_eval/controlApplyMethodCallee`
  - Lean: `runDeparser`
  - Python: `p4blo.interp.deparser.run_deparser`, `p4blo.validator._Validator.check_call_block`
  - Test: `tests/test_validator.py::test_deparser_may_call_a_deparser`, `tests/test_validator.py::test_call_kind`
  - Class: same. SpecTec runs a deparser as a control through `Call_eval/controlApplyMethodCallee` and allows it anything a control may do; on the deparsers the IR accepts it computes the same thing.
- **`emit` of an invalid header** writes nothing (§15.1).
  - P4: §15.1
  - SpecTec: `$write_bits_from_value`
  - Lean: `emitValue`
  - Python: `p4blo.interp.stmt.emit_value`
  - Test: `tests/test_interp_deparser.py::test_valid_header_emits_its_fields_and_invalid_emits_nothing`, `tests/test_interp_deparser.py::test_the_zero_headers_emit_nothing`
  - Class: same. The simulator's `packet_out.emit` appends `$write_bits_from_value` of its argument, which is empty for an invalid header.
- **`emit` of a struct** emits its fields in declaration order; the
  fields are headers, stacks or such structs, recursively, which the
  validator enforces.
  **`emit` of a stack** emits its elements from index `0` to `S - 1`,
  each subject to the invalid-header rule.
  - P4: §15.1
  - SpecTec: `$write_bits_from_value`
  - Lean: `emitValue`, `emitList`
  - Python: `p4blo.interp.stmt.emit_value`
  - Test: `tests/test_interp_deparser.py::test_struct_emits_its_fields_in_declaration_order`, `tests/test_interp_deparser.py::test_stack_emits_elements_in_order_skipping_invalid_ones`
  - Class: same. `$write_bits_from_value` concatenates a struct's fields in order and a stack's elements from index `0`, each invalid header contributing nothing.
- **Bit alignment.** Emitted headers are concatenated at the bit
  level; a total that is not a multiple of eight is padded with zero
  bits at the end, before the architecture appends any payload. P4
  leaves this to the target. SpecTec's simulator joins the payload at
  the bit level instead, so every emission that is not a whole number
  of bytes differs from it once a payload follows; whether BMv2 pads
  is not verified, since p4c rejects such headers for it.
  - P4: none
  - SpecTec: `$write_bits_from_value`
  - Lean: `Emitter.toBytes`, `Emitter.write`, `DeviationLaws.toBytes_padded`, `DeviationLaws.write_fits`
  - Python: `p4blo.interp.packet.Emitter.to_bytes`
  - Test: `tests/test_interp_deparser.py::test_bits_are_concatenated_and_padded_to_a_byte_at_the_end`
  - Class: refines undefined. SpecTec's emit appends bits with no padding, and what becomes of a partial byte is decided by its simulator's architecture code and packet printer, outside the rules: the payload is appended at the bit level and the printer pads the last group of bits to a nibble rather than a byte. The generated-program oracle test pins the exact mismatch as a strict expected failure.

## Externs

An extern is a contract, not a construct. The IR says only an extern
type's method signatures, an instance's constructor arguments and the
call sites; the instance itself is state owned by the caller, bound to
the program at load time by name. Which extern types exist, what their
methods do and how their state persists is decided by the architecture
that supplies them; the families this repository provides are in
[arch-supports.md](arch-supports.md#extern-families).

- **Binding** checks the declaration against the implementation's shape:
  method names, arity, parameter directions and widths, where a width
  may be a variable the declaration binds consistently. A mismatch
  refuses to load; nothing is coerced.
  - P4: none
  - SpecTec: none
  - Lean: `matchShape`, `Externs.bind`
  - Python: `p4blo.arch.externs.match_shape`, `p4blo.arch.externs.Registry.bind`
  - Test: `tests/test_externs.py::test_extra_method_refuses_to_bind`, `tests/test_externs.py::test_inconsistent_width_variable_refuses_to_bind`, `tests/test_externs.py::test_constructor_arg_must_fit`
  - Class: refines undefined. SpecTec has no binding step: extern objects come from its instantiation and their methods from its simulator's architecture code.
- **Method call order** is program order; an extern may keep state
  between calls and between packets, and that state is part of the
  caller's world, not the program's.
  - P4: none
  - SpecTec: `BlockElementStmtList_eval`, `Stmt_eval/callStatementIR`
  - Lean: `Externs.call`, `callExtern`
  - Python: `p4blo.interp.stmt.call_extern`
  - Test: `tests/test_arch.py::test_a_register_counts_across_packets`, `tests/corpus/stateful`
  - Class: same. SpecTec evaluates a block's statements in order and threads the architecture state, which holds extern objects, through every call.
- **Extern calls.** `in` and `inout` arguments are copied in, `out`
  arguments arrive as zero, results are written back in parameter
  order, then the return value. The binding sees and returns copies,
  so it can never alias program storage.
  - P4: §6.8
  - SpecTec: `Call_eval/externMethodCallee`, `Copy_in_arg/out`, `Copy_out`
  - Lean: `callExtern`, `argumentValue`
  - Python: `p4blo.interp.stmt.call_extern`
  - Test: `tests/test_interp_control.py::test_extern_call_with_an_out_argument_and_a_return_value`, `tests/test_interp_control.py::test_extern_out_argument_arrives_as_zero_whatever_its_lvalue_holds`
  - Class: same. `Call_eval/externMethodCallee` copies arguments in with `out` ones at `$default`, runs the method, and copies `out` and `inout` parameters back in parameter order before the call's value is used.
- **Where an implementation closes something P4 leaves open**, that
  choice is a closed behavior of the implementation, recorded with it,
  and both interpreters' models of the family must agree on it.
  - P4: none
  - SpecTec: none
  - Lean: `ExternModel`
  - Python: `p4blo.interp.api.ExternBinding`
  - Test: `tests/test_extern_families.py::test_python_dispatches_existing_families`
  - Class: refines undefined. SpecTec leaves every extern method but the parser's built-in ones to its simulator's architecture code, outside the rules.

## Decimal values at the JSON boundary

The handwritten Lean adapter accepts the decimal strings used by the
protobuf encoding for bits literals and exact/LPM/ternary key components.
An explicit nonempty ASCII digit string denotes a natural number; leading
zeros are allowed and re-encoding may canonicalize them. Numeric zero is
`"0"`, not an omitted string. Missing or null string fields have protobuf's
empty-string default and are rejected before constructing Lean's Nat value.
JSON numbers, signs, hexadecimal spellings and empty strings are not decimal
strings. Native numeric protobuf fields retain their own default rules.

Python may parse a malformed protobuf string field before its validator or
entry installer rejects it; Lean rejects the unrepresentable spelling during
decoding. This is agreement on rejection, not identical pipeline staging or
full ProtoJSON conformance. An invalid host-entry request must not execute a
packet or change persistent extern state; subsequent valid requests continue
from the previous state. The supported canonical wire profile, current
unknown-key/alias differences and version-policy exclusions are explicit in
[assurance.md](assurance.md#wire-contract). Scoped JSON-value roundtrip
proofs do not establish arbitrary ProtoJSON or whole-program validation
equivalence.
