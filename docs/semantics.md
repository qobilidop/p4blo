# Semantics

The closed behaviors: everything P4 leaves open, undefined or
target-defined that p4blo closes, each with its choice and the reason.
Until the Lean interpreter exists this file together with the Python
interpreter is the normative meaning, and the Python interpreter is
provisional. After that the Lean interpreter is normative and this file
is commentary on it.

A behavior is added here before it is implemented. A divergence
between interpreters that turns out to be an unlisted open behavior is
resolved by adding it here, not by patching one side. A divergence
between p4blo and an oracle that traces to an entry here is documented,
not a failure; claim 2 allows exactly those.

Section references are to the P4-16 language specification, version
1.2.5.

## Values

Every value of type `bit<N>` is an unsigned integer in `[0, 2^N)`. A
value carries its width at run time; the interpreters never infer a
width from context. `bool` is `true` or `false`. Enum and error values
are member indices into their declaration. Header, struct and stack
values are described below.

- **Arithmetic on `bit<N>`.** `+`, `-` and `*` wrap modulo `2^N`
  (§8.6). `|+|` and `|-|` saturate at `2^N - 1` and `0`. There is no
  division or modulo in the IR; P4 defines them only on compile-time
  constants, which the frontend folds.
- **Shifts.** `<<` and `>>` on `bit<N>` by an amount `k`: if `k >= N`
  the result is `0`; otherwise the usual logical shift, with the left
  shift truncated to `N` bits (§8.6). The shift amount is any `bit<M>`
  value; its width does not affect the result.
- **Comparison.** `<`, `<=`, `>`, `>=` compare as unsigned integers.
  `==` and `!=` are defined on every type: on `bit<N>` and `bool` by
  value, on enums and errors by member, on headers by validity and
  then fieldwise, on structs fieldwise, on stacks elementwise
  (§8.16, §8.17).
- **Casts.** `bit<N>` to `bit<M>` truncates to the low `M` bits when
  `M < N` and zero-extends when `M > N`. `bool` to `bit<1>` maps
  `false` to `0` and `true` to `1`; `bit<1>` to `bool` is the inverse.
  No other cast exists in the IR; the frontend elaborates every other
  P4 cast, including serializable enums, into these (§8.11).
- **Slices.** `e[hi:lo]` has width `hi - lo + 1` and the validator
  requires `hi < N` and `lo <= hi`, so no slice is ever out of range at
  run time.
- **Concatenation.** `a ++ b` has width `N + M` with `a` in the high
  bits.
- **Uninitialized variables.** A block-local variable or an `out`
  parameter that is read before it is written has the value `0` for
  `bit<N>`, `false` for `bool`, member `0` for enums and errors, and
  the recursively zero value with every header invalid for compound
  types. P4 leaves this undefined (§6.8); zero is chosen because it is
  the least surprising value, it is what BMv2 does at packet start,
  and it makes the Lean model total.

## Headers

A header value is a validity bit plus one value per field. A struct
value is one value per field.

- **Reading a field of an invalid header.** Returns the field's
  current stored value. A header's fields are initialized to zero and
  keep whatever was last written to them, including across
  `setInvalid`. P4 says the result is undefined (§8.17). This is the
  BMv2 behavior, chosen so that the oracle agrees rather than because
  it is principled; programs in the corpus must not depend on it, and
  the validator will warn on an unguarded read where it can see one.
- **Writing a field of an invalid header.** Stores the value and does
  not change validity. Same reason.
- **`setValid` on a valid header** and **`setInvalid` on an invalid
  one.** No effect on the fields.
- **Assigning a header** copies validity and all fields. Assigning an
  invalid header makes the target invalid and copies the fields
  anyway, so that a later read sees the same thing on both sides.
- **`isValid`** is the validity bit.
- **Header equality** on two invalid headers is `true` regardless of
  fields; on one valid and one invalid is `false` (§8.17).

## Header stacks

A stack of size `S` holds `S` header values and a `nextIndex` in
`[0, S]`.

- **Index out of range.** Reading `hs[i]` with `i >= S` returns an
  invalid header whose fields are zero. Writing `hs[i]` with `i >= S`
  does nothing. Both are undefined in P4 (§8.18). This closes the
  behavior without an error because the IR has no runtime error in
  controls; a program that wants a check writes one.
- **`hs.next`** is a parser-only lvalue. Extracting into it with
  `nextIndex == S` is a parse error `StackOutOfBounds` and consumes
  nothing. On success it fills `hs[nextIndex]`, sets it valid, and
  increments `nextIndex`.
- **`hs.lastIndex`** is `nextIndex - 1` as a `bit<32>`; when
  `nextIndex == 0` its value is `2^32 - 1`, the wrapped result. P4
  says undefined.
- **`push_front(n)`** shifts elements toward higher indices by `n`,
  discards the last `n`, makes the first `n` invalid with zero fields,
  and sets `nextIndex` to `min(nextIndex + n, S)`. **`pop_front(n)`**
  shifts toward lower indices, makes the last `n` invalid with zero
  fields, and sets `nextIndex` to `max(nextIndex - n, 0)` (§8.18).

## Parsers

A parser runs over a packet with a cursor in bits, starting at zero.
Its outcome is the headers, the metadata, the number of bits
consumed, and an error, which is `NoError` on `accept`. On any error
the parser stops immediately with the headers and metadata as they
were at that moment; the caller decides what to do with them. This
matches v1model, where the controls run after a parser rejection with
`parser_error` set.

- **Extraction past the packet end.** If fewer bits remain than the
  header's width, the extract raises `PacketTooShort`, consumes
  nothing, and leaves the target as it was (§12.8.2).
- **Extract sets the target valid** and fills every field from the
  packet, most significant bit first.
- **`lookahead<T>`** reads `width(T)` bits without moving the cursor;
  past the end it raises `PacketTooShort`.
- **`advance(n)`** moves the cursor by `n` bits; past the end it
  raises `PacketTooShort` and the cursor does not move.
- **`verify(cond, err)`** raises `err` when `cond` is `false`.
- **`select`** evaluates the key expressions once, then tries the
  cases in order and takes the first that matches. A key set entry is
  an exact value, a value with a mask, a closed range, or don't-care.
  With no matching case, the transition is to `reject` with error
  `NoMatch` (§12.6).
- **`reject`** is a transition like any other; the error is whatever
  was last raised, or `NoError` if the program transitioned to
  `reject` explicitly without an error. This is what the P4
  specification says (§12.7) and what makes `verify` and explicit
  rejection distinguishable.
- **Parser loop bound.** A state may be entered any number of times
  as long as the cursor advanced since the last time it was entered.
  Entering a state a second time with the cursor at the same position
  as at the previous entry raises `ParserTimeout` (§12.11 leaves the
  bound to the target). This is the no-consumption revisit rule from
  the design doc. Sub-parser states count as states of the enclosing
  run.
- **Errors.** The IR's error set begins with core.p4's, in this order
  at these indices: `NoError` 0, `PacketTooShort` 1, `NoMatch` 2,
  `StackOutOfBounds` 3, `HeaderTooShort` 4, `ParserTimeout` 5,
  `ParserInvalidArgument` 6. A program may declare more after them.
  `HeaderTooShort` and `ParserInvalidArgument` are never raised by the
  IR because varbit and the extract-with-length form are out of scope;
  they are reserved so that indices agree with every reader.

## Controls

A control runs its body once over the headers, the metadata and the
installed entries, and returns the headers and metadata. It has no
other effect. Externs are the only way a control touches anything
else, and every extern instance is state supplied by the caller.

- **Block calls.** A sub-block call copies `in` arguments in, runs the
  block, and copies `out` and `inout` arguments back in parameter
  order. Two arguments that alias the same storage are a validator
  error, so copy order never matters (§6.8).
- **Action calls** from a control body pass arguments in the same
  way. Actions invoked by a table receive their action data as `in`
  parameters.
- **Recursion** between blocks is a validator error, so no run can
  fail to terminate; every construct in the IR is bounded.

## Tables

A table match is evaluated over the installed entries; the program's
`const entries` are installed first and cannot be removed.

- **Exact keys** match when every key equals the entry value.
- **LPM.** A table has at most one `lpm` key. Among the entries whose
  other keys match exactly and whose prefix covers the key value, the
  longest prefix wins. Two entries with the same prefix length and the
  same other keys are rejected at installation, so there is no tie.
- **Ternary.** A table with any `ternary` key requires a priority on
  every entry. Among the entries that match, the one with the largest
  priority wins. Two matching entries with equal priority are
  rejected at installation when their key sets overlap, which is
  decidable for ternary and exact keys, so there is no tie. Larger
  wins because that is what the P4Runtime specification says (§9.1);
  the STF runner converts if the oracle's convention differs.
- **Table miss.** The default action runs. A table always has a
  default action; when the program declares none, it is `NoAction`,
  which does nothing (§14.2.1.4).
- **`hit`** is `true` when an entry matched and `false` on a miss,
  including a miss that ran the default action.
- **Key expressions** are evaluated once, before matching. An entry
  value wider than the key is rejected at installation.
- **Entries reference actions by id** and carry action data as
  constants of the declared parameter widths; a mismatch is rejected
  at installation.

## Deparsers

A deparser runs over the headers and produces the bytes of the emitted
headers; the caller appends the payload it retained after parsing.

- **`emit` of an invalid header** writes nothing (§15.1).
- **`emit` of a struct** emits its fields in declaration order.
  **`emit` of a stack** emits its elements from index `0` to `S - 1`,
  each subject to the invalid-header rule.
- **Bit alignment.** Emitted headers are concatenated at the bit
  level; a total that is not a multiple of eight is padded with zero
  bits at the end. P4 leaves this to the target; BMv2 pads the same
  way.

## Externs

An extern instance is state owned by the caller, bound to the program
at load time by name. The IR says only its type, its constructor
arguments and its call sites.

- **Method call order** is program order; an extern may keep state
  between calls and between packets, and that state is part of the
  caller's world, not the program's.
- **Extern implementations** for the corpus are specified by their
  own vectors under `corpus/`, not here.
