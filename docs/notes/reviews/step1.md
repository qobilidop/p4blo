# Step 1 review: interpreter, validator, semantics

Reviewer: independent, read-only, against `main` at c8783b2 (the proto
gained the extern-family comment while I was reading; nothing below
depends on it). Reproducers: `test_review.py` beside this file, 14 tests,
each asserting the *defective* behavior, all passing:

    nix develop -c uv run pytest scratchpad/review/test_review.py -p no:cacheprovider

Findings are ranked by severity. "Confirmed" means a reproducer runs.

## Confirmed defects

### 1. Recursive actions validate; the interpreter overflows the Python stack (high)

- `python/p4blo/validator.py:898` `check_call_action` resolves the callee
  and checks its arguments, but records no call edge; `check_call_graph`
  (`:798`) only walks `CallBlock` edges. `call_action` is allowed inside
  an action body (`_STMTS_BY_KIND`, `:294`).
- Violates semantics.md, Controls: "Recursion between blocks is a
  validator error, so no run can fail to terminate; every construct in
  the IR is bounded", and design.md's "every construct in the IR is
  bounded". The doc only names blocks, but the promise is termination.
- Reproducer: `actions { name: "a" body { call_action { action: "a" } } }`
  called from the body. `validate()` returns `[]`; `run_control` raises
  `RecursionError`. Mutual recursion `a -> b -> a` likewise
  (`test_recursive_action_validates_and_overflows`,
  `test_mutually_recursive_actions_validate`).
- Fix: in `check_call_action`, when `scope.action is not None`, record
  `(scope.action.name, callee.name, path)` in a per-block action graph and
  run the same white/grey/black DFS as `check_call_graph`, reporting
  `CALL_CYCLE`. Add one line to semantics.md: recursion among actions is
  a validator error too.

### 2. A deparser may call a control that applies a table; the run raises `InterpError` (high)

- `validator.py:910` lets any non-parser call a control
  (`wanted = CONTROL`; `test_deparser_may_call_a_control` pins this).
  `interp/deparser.py:32` builds the deparser's `Env` with
  `entries=None`, `Env.enter_block` (`env.py:68`) inherits that, and
  `stmt.apply` (`stmt.py:249`) calls `require_entries()`.
- Violates the `InterpError` contract (`api.py:58`: "Raised only on
  inputs the validator rejects; a validated program never triggers it")
  and the calling convention `deparse : H -> Packet`, which has no
  `TableEntries` input, so a deparser cannot mean anything that applies
  a table.
- Reproducer: control `C` with a table and `apply`; deparser `D` with two
  locals passed as `inout` to `C`. Validates clean; `run_deparser` raises
  `InterpError: block 'C' has no table entries`
  (`test_deparser_calling_a_control_with_a_table_validates_and_raises`).
- Fix (pick one, then state it in the proto comment on `CallBlock` and in
  semantics.md, Deparsers): (a) a deparser may call only a block that
  contains no `apply`, transitively, checked in `check_call_graph`; or
  (b) simply forbid `call_block` from a deparser to a control, since the
  design already says a deparser is `H -> Packet`. (a) keeps the existing
  test; (b) is one line and matches the proto's "a parser may only call
  parsers and a control only controls" if extended with "a deparser only
  deparsers".

### 3. `hs.next` is accepted as any lvalue in a parser, not only as an extract target (medium)

- `validator.py:1288-1294` `type_of_lvalue` for `next` checks only
  `scope.in_parser`. The proto says `Next` is "the target of an extract
  into a stack" and semantics.md says "`hs.next` is a parser-only lvalue.
  Extracting into it ..." and specifies nothing else.
- Each of these validates and the interpreter invents a meaning
  (`expr.py:330-334`, `:364-371`):
  - `hs.next = hdr.e` with `hdr.e` invalid: fills `hs[0]`, forces it
    **valid**, increments `nextIndex` (an assignment that behaves like an
    extract of a valid header) (`test_assign_to_next_validates_...`).
  - `hs.next.setValid()`: sets `hs[nextIndex]` valid, does **not**
    increment (`test_set_valid_on_next_validates_and_does_not_advance`).
  - `hs.next.f = 7`: writes the field of the not-yet-extracted element,
    no validity or index change (`test_field_write_through_next_validates`).
  - `hs.next` as an `out` argument of a sub-parser: copy-back fills the
    slot, forces it valid, increments, even though the callee never wrote
    it (`test_next_as_out_argument_of_a_sub_parser_validates_and_advances`).
  - As an `inout` argument (not tested): `argument_value` reads
    `hs.next` first and raises `StackOutOfBounds` on a full stack before
    the callee starts.
- Fix: handle `next` in `check_stmt`'s `extract` branch (accept it there,
  returning the header type) and make `type_of_lvalue` report a new code
  or `PARSER_ONLY`-style diagnostic for `next` anywhere else, including
  as the base of `member`. Then `write_lvalue`'s `next` case is reached
  only from `extract`; keep the `valid = True` there or move it into
  `extract`, where the doc puts it.

### 4. `InstalledEntries.check_action` finds the table's block by protobuf value equality (medium)

- `interp/tables.py:132`:
  `block = next(b for b in self.index.program.blocks if decl in b.tables)`.
  `in` on a repeated message field compares by value, so two blocks that
  declare byte-identical tables resolve to the first block, and the
  action data of a host entry for the second block is checked against
  the first block's action.
- Violates semantics.md, Tables: "Entries name their action and carry
  action data as constants of the declared parameter widths; a mismatch
  is rejected at installation" (here a correct entry is rejected; with
  swapped widths an incorrect one would be accepted, and then
  `run_action_call` would bind a `bit<8>` literal to a `bit<16>` param
  and the width invariant would be silently broken).
- Reproducer: blocks `A` and `B`, each `tables { name: "t" actions: "set" }`
  with `A.set(bit<8>)`, `B.set(bit<16>)`; a host entry for `(B, t)` with a
  16-bit arg raises `InstallError: ... wrong type`
  (`test_check_action_looks_up_the_wrong_block_for_an_identical_table`).
- Fix: `check_action(self, table: TableRef, call)` and
  `self.index.scopes[table[0]].actions[call.action]`; the block name is
  already in every caller's hand.

### 5. A non-decimal host action argument escapes as `ValueError`, not `InstallError` (low)

- `tables.py:207` `literal_fits` calls `int(literal.bits.value)`;
  `decimal()` at `:163` exists for exactly this and is used for keys but
  not for action data.
- Violates the `InstallError` docstring ("An entry does not fit its
  table") and the API promise that host input is rejected, not crashed
  on. Also `int()` accepts `" 7"`, `"+7"`, `"1_0"`, which the validator's
  `parse_decimal` does not, so const entries and host entries disagree on
  what is decimal.
- Reproducer: host entry `args { bits { width: 8 value: "0x1" } }` →
  `ValueError` (`test_non_decimal_host_action_arg_is_a_value_error`).
- Fix: `literal_fits` uses `decimal(literal.bits.value, type.bits, ...)`
  inside a try, or the validator's `parse_decimal` regex, and returns
  `False`/raises `InstallError`.

### 6. `ExternBinding` docstring promises the current value for `out` args; the interpreter passes zero (low)

- `api.py:28-30`: "`args` holds one value per parameter in order, with
  the current value for out and inout parameters." `stmt.argument_value`
  (`stmt.py:142`) returns `zero(param.type)` for `out`.
- The interpreter is right (P4 `out` is uninitialized, and semantics.md
  says uninitialized reads are zero); the contract text is wrong, and an
  extern author reading it would rely on a value that is never there.
  Confirmed by `test_extern_out_argument_is_zero_not_current_value`
  (lvalue holds 5, binding receives `Bits(8, 0)`).
- Fix: docstring: "the zero value for out parameters and the current
  value for inout". Add an "Extern calls" bullet to semantics.md,
  Externs: `in`/`inout` copied in, `out` zero, `out`/`inout` results
  written back in parameter order, then the return value.

### 7. STF: a non-canonical LPM value resolves in `to_entries` and fails at install, without a line number (low)

- `stf.py:534-540` `_key_value` builds `LpmValue(value, prefix)` without
  masking or checking the bits below the prefix; `tables.check_key_value`
  (`:195`) later rejects with `InstallError: lpm value ... has bits
  outside its prefix`, and by then the line is gone.
- semantics.md says entries are canonical; the runner's own docstring
  promises `StfError` "with the line number when there is one" for a
  vector that "cannot be resolved against a program".
- Reproducer: `add ipv4_lpm hdr.ipv4.dstAddr:0x0a000201/24 ...` on the
  forwarder (`test_stf_non_canonical_lpm_value_fails_late_as_install_error`).
- Fix: in `_key_value`, either raise `StfError(f"line {line}: ... has
  bits below /{prefix}")` or mask the value as p4c's runner effectively
  does; record the choice in the STF dialect list in decisions.md.

### 8. Dead code (low)

- `interp/values.py:129` `assign()` has no caller (the eDSL's `a.assign`
  is a different function).
- `validator.py:1622-1633`: the `boolean`, `enum_type` and `error`
  branches of `exact_pattern` are unreachable, because `check_keys`
  (`:1483`) nulls every non-bits key type before entries are checked.
  `ExactPattern.value: int | str` and the comment at `:242` ("the types a
  literal, a select key or an exact table key can have") are stale for
  the same reason: table keys are bits only.

## Plausible but unconfirmed (at most five)

- **P1. `call_block` inside an action body validates.** `_ANY_BLOCK_STMTS`
  includes `call_block` and `check_action` reuses `check_stmt`, so an
  action may apply a sub-control (`test_call_block_inside_an_action_validates`
  shows it validates and runs). I believe P4-16 §14.1 forbids applying
  controls inside actions ("No table, control or parser applications can
  appear within actions" or close to it); check the spec text. If so it
  is a fidelity gap in the validator, not a crash; if the IR wants to
  allow it, say so in the proto's placement table, which currently lists
  only `apply` as excluded from actions.
- **P2. `verify(cond, NoError)`** rejects with `NoError`, indistinguishable
  from an explicit `reject`. This is what P4 does, but semantics.md's
  Parsers section presents explicit reject and raised errors as always
  distinguishable; one sentence closes it.
- **P3. Stack `==` ignores `nextIndex`** (`values.py:123`). semantics.md
  says "elementwise", so the two agree, but the P4 spec's stack equality
  should be checked for whether `nextIndex` participates, and the doc
  should say "and not on nextIndex" either way, since the Lean side will
  have to decide.
- **P4. `lookahead<bool>`** is rejected by the validator (`:1249`, bits or
  header only) while semantics.md's "reads `width(T)` bits" and the
  interpreter (`value_from_bits` handles `boolean`) both allow it. Pick
  one; I would drop `boolean` from `value_from_bits` and say "bits or a
  header" in the doc.
- **P5. `Apply.hit` is written after the chosen action runs**
  (`stmt.py:250-253`). Correct for P4 (`t.apply().hit` reads the result
  after the apply) but unstated; matters if an action writes the same
  lvalue.

## Semantics doc gaps

Behaviors the interpreter had to decide that `docs/semantics.md` does not
state, beyond those in findings 1-3 and 6:

- Actions calling actions: allowed; arguments are copy-in/copy-out like a
  block call; the callee sees the block's variables but not the caller
  action's parameters; recursion must be a validator error (finding 1).
- Extern calls: direction handling and write-back order (finding 6);
  an extern's `out`/`inout` results and return value are copied, so a
  binding cannot alias program storage.
- Deparsers and tables (finding 2).
- `hs.next` outside `extract` (finding 3): after the validator fix the doc
  should say "`hs.next` appears only as the target of an extract".
- `push_front(n)` and `pop_front(n)` with `n > S`: the interpreter clips
  `n` to `S` (`stmt.py:118`, `:128`); the doc's formulas happen to give
  the same answer but "discards the last n" reads oddly for `n > S`.
- `hit` write timing (P5), `verify(.., NoError)` (P2), stack equality and
  `nextIndex` (P3), `lookahead<bool>` (P4).
- Select key sets: `masked` and `range` apply only to `bit<N>` keys;
  a `bool`, enum or error key takes `exact` and don't-care only. The
  validator enforces this (`:1392`); the doc's "A key set entry is an
  exact value, a value with a mask, a closed range, or don't-care" does
  not say it.
- Extract into a header type with zero fields consumes nothing, sets it
  valid, and does not count as consumption for the revisit rule. Corner
  case, but the Lean model needs the answer.

## What I checked and found correct

Against every rule in semantics.md, line by line: wrapping and saturating
arithmetic, complement and negate, shifts by `>= N` for any amount width,
comparisons unsigned, casts (truncate, zero-extend, `bool`/`bit<1>` both
ways, and the validator's allowed pairs), slice width and range, concat
order, uninitialized values including enum first member and `NoError`;
header field read/write on invalid headers, `setValid`/`setInvalid`,
whole-header assignment copying validity and fields, header equality
(invalid == invalid, valid != invalid), struct and stack equality;
out-of-range stack read (fresh zero invalid header, never stored) and
write (dropped), including `hs[i].setValid()` and `hs[i].f = x` past the
end; `lastIndex` wrap; `push_front`/`pop_front` shifting, clearing and
`nextIndex` clamping; `.next` extract raising `StackOutOfBounds` before
the packet is read (target resolved first, `stmt.py:269`); extract past
the end consuming nothing and leaving the target; extract into `hs[i]`,
`i >= S`, consuming and storing nothing (`test_extract_past_stack_end_...`);
MSB-first field order and the emit/extract roundtrip; lookahead and
advance past the end; verify; select evaluating keys once, first match,
`NoMatch`; explicit reject giving `NoError` from a top-level or sub-parser
state; sub-parser copy-back in `finally` before the error propagates;
the revisit rule keyed by `(block, state)` and cursor, shared across
sub-parser activations; core error order; block-call copy-in, `out` at
zero, copy-back in parameter order, alias check between arguments
(prefix-aware, computed index wildcards); table matching for exact, LPM
longest prefix and ternary largest priority, ties rejected at install for
both const and host entries, canonical entry checks, priority required
only with a ternary key, default action and `NoAction`, `hit` on hit and
on a default run, host default replacing a non-const default and refused
on a const one; key expressions evaluated once before matching; deparser
emit of invalid headers, structs in order, stacks `0..S-1`, and zero
padding to a byte. `run_parser`, `run_control` and `run_deparser` copy
their compound inputs and return fresh values; `write_lvalue` copies so
no two variables share storage.

Validator coverage of the proto contract is otherwise complete: names,
kinds, scopes, error list, type well-formedness including struct cycles,
literal format and range, block shapes, statement placement, parser
graphs, select arity and types, table key rules, action lists, const
entry shape/range/tie rules, extern constructor args, export signatures,
block call cycles.

## Readability

The interpreter does read as an explanation of P4's core, and the
bottom-up module order announced in `interp/__init__.py` holds. Each
function that implements a closed behavior cites the semantics.md section
it implements, which is the right discipline; the citations should be
kept exact after the doc edits above. Specific notes:

- `expr.py` and `stmt.py` are the best files: one function per node,
  no cleverness, and the two non-obvious orderings (target resolved before
  the packet is read in `extract`; keys evaluated once in `select` and
  `apply`) each carry a comment saying why.
- `values.py` and `packet.py` are small and exact. `Bits.__post_init__`
  enforcing the width invariant everywhere is what makes the arithmetic
  section trustworthy at a glance.
- `env.py`'s `enter_action` constructs `Env` with ten positional
  arguments; a reader has to count fields to see that only `action` and
  `action_vars` change. `dataclasses.replace(self, action=..., action_vars=...)`
  says it in one line.
- `write_lvalue`'s `next` case, and the module docstring's "a write to
  `hs.next` fills the next slot", describe a general write, which is
  exactly the freedom finding 3 exploits. Once `next` is extract-only,
  move the fill-and-increment into `extract` and the lvalue code gets
  simpler and truer.
- `call_block`'s `finally` runs copy-back for controls too, where nothing
  can raise; the comment names only sub-parsers. Harmless, but say "on
  any exit" or restrict it to parsers so the reader does not wonder.
- `tables.py` is the least readable file: `KIND_OF_MATCH` duplicates the
  validator's mapping, `decimal()` and `literal_fits()` parse the same
  thing two ways (finding 5), and `check_action`'s block lookup is the one
  line in the package a reader cannot verify by inspection (finding 4).
  `widths.type_of` is a second, smaller type checker that must stay in
  step with the validator's; a comment saying so, and that it is only
  needed for key widths and lookahead/extract widths, would help.
- `stf.py`'s module docstring is a model of stating a dialect precisely.
- The validator's per-rule code list at the top is excellent as the
  "contract's fine print"; findings 1-3 are each one missing rule there,
  which is a good sign about the structure.
