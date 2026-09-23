# Step: eDSL v2 review

Reviewer: independent, read-only, against `main` at 01e7871 (working tree
clean). Reproducers: `test_review.py` beside this file, 11 tests, each
asserting the *defective* behaviour, all passing:

    nix develop -c uv run pytest \
        scratchpad/review3/test_review.py -p no:cacheprovider

The static half of findings 1 and 6 is in `probes/`, a copy of
`tests/pyright/pyrightconfig.json` beside small programs, run from the
repository root:

    nix develop -c uv run pyright --outputjson \
        --project scratchpad/review3/probes/pyrightconfig.json \
        scratchpad/review3/probes/*.py

`test_checked2.py`, `test_checked3.py` and `test_checked4.py` hold what I
tried and found correct (32 passing, 3 skipped where the eDSL rightly
refused the program). Findings are ranked by severity; "confirmed" means a
reproducer runs.

## Confirmed defects

### 1. Typed const entries are checked nowhere: not by pyright, not at build time, not by the validator (high)

- `python/p4blo/edsl/blocks.py:436-446`: the last `Table.__init__`
  overload takes `keys: Sequence[Key[Any]]` and `entries:
  Sequence[Entry[Any]]`. A `tuple[Key[A]]` *is* a `Sequence[Key[Any]]`,
  so whenever the typed overload fails, pyright falls through to this one
  and the table silently degrades to `Table[tuple[Any, ...]]` instead of
  reporting the mismatch. The arity-one-to-four overloads, `Key[W]`,
  `Entry[KS]` and the three `_invariant` methods therefore never reject
  anything.
- `python/p4blo/edsl/blocks.py:1054-1059`: `_core_key_value` turns a
  `Bits` literal into `int(expr.pb.literal.bits.value)`, dropping the
  width. The core then checks the integer against the key's width, so
  only an out-of-*range* value is caught; a wrong-width value that fits
  is not. The IR stores decimal strings of the key's width, so the
  validator cannot see it either.
- Violates recommendation 6 of `docs/notes/edsl-v2-design.md`, accepted
  in full ("Entries are the host-facing part of a table and a wrong width
  there is silent until the validator; `Table` becomes generic in its key
  tuple with overloads for arity one to four"), and the design table's
  "action argument count and widths in calls, defaults, **entries**". It
  is not among the four accepted deviations in `docs/decisions.md`.
- Reproducers: `probes/v02_entry_key_width.py` (a `bit16` value for a
  `bit8` key), `probes/v16_entry_arity.py` (two values for a one-key
  table), `probes/v17_entry_list_keys.py` (the forwarder's `keys=[...]`
  form), `probes/v18_entry_explicit_type.py` (with `t: Table[tuple[L[8]]]`
  written out) — pyright reports nothing on any of them, while
  `probes/v15_entry_reveal.py` shows `reveal_type` giving
  `Table[tuple[Literal[8]]]` and `Entry[tuple[Literal[16]]]`. Run time:
  `test_a_const_entry_value_of_the_wrong_width_builds_and_validates`
  builds such a table and `validator.validate` returns `[]`.
- Note that every corpus table and `must_pass/constructs.py` write
  `keys=[...]` (a list), which selects the untyped overload outright, so
  the feature is off in all ten programs and in the suite's own showcase.
- Fix: give the fallback overload `keys: list[Key[Any]]`. A tuple then
  matches only the typed overloads, and a mismatch is an error;
  `keys=[...]` stays unchecked, as today. Verified in isolation in
  `probes/fixcheck.py`: the same call errors under the fixed shape and is
  clean under the current one. Then make `_core_key_value` compare
  `expr.type` with the key's type (the run-time half, for `bit(n)` and
  generated programs), and rewrite the corpus tables and
  `must_pass/constructs.py` to pass a tuple so the guarantee is exercised.
  A must_fail fixture for a wrong-width entry value belongs in
  `tests/pyright/must_fail/` either way.

### 2. A `select` with two eDSL-valued keysets dies with "has no truth value" (high)

- `python/p4blo/edsl/blocks.py:896-902`: `Parser.select` keeps a `seen`
  list of keyset tuples and tests `if sets in seen:`. `list.__contains__`
  compares the tuples with `==`, which for two distinct `Bits`, `Enum` or
  `Error` keysets calls `Bits.__eq__`/`Enum.__eq__`, gets a `Bool`
  *expression* back and asks it for a truth value, which
  `Value.__bool__` (`values.py:143`) raises on.
- The declared keyset type is `KeySet = int | bool | Bits[Any] | Enum |
  Error | Masked | Range | DontCare` (`blocks.py:168`), so three of its
  seven members are unusable from the second case on, and the message a
  user gets ("... has no truth value; use `with self.if_(cond):` for
  control flow") names a mistake they did not make. `self.select(k,
  {bit16(0x800): a, bit16(0x86dd): b})` is exactly how the design's own
  literal rule says a typed constant is written.
- The corpus only ever uses `IntEnum` members, which are Python ints, so
  nothing in the suite touches this.
- Reproducers: `test_select_with_two_literal_keysets_raises_no_truth_value`
  and `test_select_with_two_enum_members_raises_no_truth_value`;
  `test_one_keyset_of_the_same_kind_is_fine` pins that one case is
  enough to hide it.
- Fix: normalise before comparing — build the core keyset first
  (`_core_keyset(s)`, already a function there) and compare the resulting
  `pb.KeySet` messages, which protobuf compares by value. That also makes
  the repeated-case and unreachable-case checks work for literal and enum
  keysets, which today they silently never do.

### 3. `tests/pyright/must_pass/constructs.py` is not a program (medium)

- The file that claims to hold "every construct the design note names,
  once, in one program" type-checks with zero errors and fails to build:
  `constructs.py:113` calls `self.call(SubParser, self.meta.next_type)`
  with one argument, while `SubParser` declares two parameters (`hdr:
  InOut[headers]`, `ret_next_hdr_type: Out[bit8]`). The corpus writes the
  same call correctly, with `self.hdr` first
  (`corpus/subparser_stack/subparser_stack.py:115`).
- `tests/test_pyright.py` only feeds must_pass files to pyright; it never
  imports them. So the one construct whose check is run-time-only by
  accepted deviation ("sub-block call arguments are run-time checked, as
  a callable protocol from annotations cannot be expressed") is the one
  the suite cannot see, and the showcase for it is wrong.
- Reproducer: `test_the_must_pass_constructs_fixture_does_not_build`
  (imports the fixture, calls `program.build()`, gets `EdslError: block
  SubParser takes 2 arguments, got 1`). `must_pass/forwarder.py` builds
  and validates clean; only `constructs.py` is broken.
- Fix: add the missing `self.hdr` argument, and add a test in
  `tests/test_pyright.py` that executes every must_pass module, calls
  `build()` on its `program` and asserts `validator.validate` is empty —
  a must_pass file should be a program, not only a parse tree.

### 4. v2 builds `pb.Program`s that `validator.validate` rejects (medium-low)

- Two shapes found:
  - an entry `priority=` on a table with no ternary key →
    `ENTRY_PRIORITY: only a table with a ternary key has priorities`
    (`test_entry_priority_on_a_non_ternary_table_fails_the_validator`);
  - `Table(actions=[])` → `TABLE_ACTIONS: table lists no actions`
    (`test_a_table_with_an_empty_action_list_fails_the_validator`).
- The neighbouring rules *are* enforced at build time by the core (a
  default or entry action outside the action list, an action listed
  twice, an entry value out of range — three of my probes were refused
  that way, see the skips in `test_checked2.py`), so these two are an
  inconsistency, not a deliberate division of labour. The design's right
  column does say "everything the validator owns" is run-time, which is a
  fair reading in the other direction; the practical difference is that
  the eDSL's refusal carries `(defined at file:line)` and the validator's
  diagnostic carries a protobuf path.
- Inherited from `p4blo.edsl.core` (v1), so it is not a regression: the
  same two mistakes are buildable through the dynamic API.
- Fix: in `core/blocks.py`'s table builder, refuse a non-zero priority
  when no key is ternary, and refuse an empty action list.

### 5. Three build-time mistakes escape without provenance, one of them as the wrong exception type (low)

Design point 12, accepted: "Provenance on every error (`defined at
file:line` from the nearest frame outside the package)".

- `blocks.py:624`: `build.core.add_block(core, before=before)` is the one
  core call in `_assemble` not wrapped in `with provenance()`. Two block
  classes with the same IR name raise the *core* `EdslError` ("block 'Same'
  reuses the name of a block") with no location — and, because
  `p4blo.edsl.errors.EdslError` is a *subclass* of the core one, a user
  who writes `except EdslError` against the v2 surface does not catch it.
  (`test_a_duplicate_block_name_escapes_without_a_location`.)
- `blocks.py:201-207`: `State.__get__` returns a `StateRef` through an
  instance, so the natural slip `return self.parse_ipv4()` instead of
  `return self.goto(self.parse_ipv4)` raises `TypeError: 'StateRef' object
  is not callable` (`test_calling_a_state_method_raises_type_error`).
- `blocks.py:758`: `self._build.pending.remove(result)` — assigning one
  extern result twice raises `ValueError: list.remove(x): x not in list`
  (`test_one_extern_result_assigned_twice_raises_value_error`).
- Fix: wrap the `add_block` call in `with provenance()`; give `StateRef` a
  `__call__` that raises `EdslError("a state is named, not called: write
  self.goto(self.parse_ipv4)")`; test membership in `_call_extern_stmt`
  and raise `EdslError("the result of compute(...) is already assigned")`.

### 6. pyright refuses an int literal as action data, which the build accepts (low)

- `self.fwd(1)` and `default=fwd(1)` are `reportArgumentType: Argument of
  type "Literal[1]" cannot be assigned to parameter "port" of type
  "bit9"` (`probes/fp03_int_action_arg.py`, two diagnostics), while the
  program builds and validates clean
  (`test_an_int_literal_as_action_data_builds`).
- Design rule 10, accepted: "An `int` takes the other operand's width and
  must fit; no context means `bit8(1)`." An action parameter supplies the
  context, and an entry *key* value already accepts a bare int
  (`KeyValue[W]` includes `int`), so action data is the one place where
  the literal rule is statically denied. It is a false positive on a
  valid program, in the sense of the design's own rule.
- Fix: no cheap type-level one — `Action[P]`'s `ParamSpec` is the
  method's own signature, and widening a parameter to `bit9 | int` would
  make it an `int` inside the body too. I would state it in `blocks.py`'s
  static-rules list ("action data is written `bit9(1)`, never a bare
  int"), and keep `must_pass` writing it that way, which it does.

## Plausible but unconfirmed (at most five)

- **P1. An enum-typed assignment across two enum types is not a static
  error.** `assign[E: Enum](target: E, value: E)` lets pyright solve `E`
  to `Color | Shape`, so `self.assign(self.meta.c, Shape.FLAT)` passes
  (`probes/v09_enum_mismatch.py`); the run time catches it. Comparison
  *is* caught (`probes/v19`, `Operator "==" not supported for types
  "Color" and "Shape"`), which makes the assignment hole look accidental.
  The design's table promises static checking of widths, not of enum
  types, so this is a gap in principle 2 rather than a broken promise;
  splitting the overload per enum class (`target: E, value: E` with
  `E` invariant through a private method, as `Key._invariant` does)
  would close it.
- **P2. The ten corpus programs are never type-checked.**
  `[tool.pyright].include` is `["python", "tests"]`, so `uv run pyright`
  in CI does not see `corpus/`. They are clean today — I ran pyright over
  them, 10 files, 0 errors — but nothing keeps them so, and they are the
  real usage the design's point 14 leans on. Adding `"corpus"` to
  `include` costs nothing and would have caught nothing today, which is
  the point.
- **P3. A dead guard in `Block.__init_subclass__`.** `blocks.py:556`,
  `if attr in ("hdr", "meta") and attr not in
  cls.__dict__.get("__annotations__", {})`, can never be true: every
  `attr` comes from `own_annotations(cls)`, which iterates that same
  dict. If it was meant to let a subclass leave `hdr`/`meta` implicit
  while annotating something else, it does not do that; the behaviour it
  seems to want already falls out of `own_annotations`.
- **P4. An action may not call an action.** `_record_action_call`
  requires a `ControlBody` (`blocks.py:1026-1029`), so
  `self.inner()` inside an `@action` is refused, while the IR and the
  validator allow `call_action` in an action body (step 1's review pinned
  that, finding 1). The core's `call_action` lives on `ControlBody` too,
  so v2 is not narrower than v1 — but `docs/coverage.md` and the design
  both read as if the eDSL covers the IR, and this is one construct it
  cannot author.
- **P5. `View.__core_type__` is written and never read** (`views.py:255`,
  `:271`). Constructing the core `HeaderType`/`StructType` at class
  definition is doing real work — it is what refuses a header field of
  struct type at the point of declaration — but the attribute it is
  stored in is dead, and a reader has to prove that before moving on.
  Either drop the attribute and keep the constructor call with a comment
  saying why, or use it when registering.

## What I checked and found correct

Static, by writing the violating program and running pyright
(`probes/v*.py`): widths in `+`/`-`/`&`/`<<` and in `==`, `!=`, `<`, `<=`,
`>`, `>=`; a width mismatch in `assign`, in a block local, in a cast
target, in `mux`'s two branches; a slice or `concat` assigned without
`as_`; a `Bool` into a `bit<N>` place and the reverse; an action argument
of the wrong width in a direct call, in a table `default=` and inside
`entry(...)`; a misspelled action keyword; an extern method name, its
argument count and the width of an `Out` argument; `extract` in a
control. Every one is an error, with the rule the must_fail suite names.

False positives hunted and *not* found (`probes/fp0*.py`, all clean):
a `Bool` field assigned from a comparison; an `Enum`-typed and an
`Error`-typed field assigned from members reached through the class; a
cast result into a field; int literals in `mux`, in `assign`, as entry
key values; `self.local(...)` passed as an `Out` extern argument and as
action data; an action parameter in arithmetic, including the reflected
`1 + tag`; unbound paths (`headers.h.f8`) as table keys; the full stack
surface (`next`, `last`, `last_index`, indexing, push/pop, set_valid);
sub-block parameters declared `In`/`Out`/`InOut`; `bit(n)` locals;
`assign_slice`; `verify` with a declared error. The ten corpus programs
type-check with zero errors, and so does `must_pass/forwarder.py`.

Run time (`test_checked2.py`, `test_checked3.py`, `test_checked4.py`):
building one `Program` twice gives an equal IR; two programs share header
and struct classes; one module-level extern instance serves two programs;
a subclassed parser adds a state in class order and does not duplicate
the base's locals; a subclassed control inherits its `Table`; a control
sharing an `@action` base with a sub-control it calls builds and
validates; a sub-parser called from two states is built once and placed
before its caller (`['Sub', 'P2', 'C', 'D']`). Refused, with
`(defined at file:line)` pointing at the user's line: a wrong argument
count and an rvalue for an `out` parameter in `self.call`; a local whose
name is a parameter's; the same local declared twice; `apply_table` from
an action; a table whose default or entry action is not in its action
list; an action listed twice; an entry value out of range; a state that
does not return a `Transition`; a state named `accept` (refused, though
only incidentally — `self.accept` then names that state, so the start
state stops returning a `Transition`); assigning to a
literal or to a comparison; an extern `in` argument of the wrong width,
an extern result of the wrong width, an extern result never assigned, an
extern instance not listed in `Program(externs=...)`; a statement outside
a body. The four accepted deviations all hold their run-time side.

## Readability

`python/p4blo/edsl/__init__.py` does what the design promised: the "two
clocks" section is the clearest statement of build time versus run time
in the repository, it names what each module's docstring must carry, and
each module does carry it. `values.py`'s docstring is the best of them —
it states the four accepted deviations plainly (the `bitN` aliases are
places, a literal is a place to the checker, `Val[T]` for extern `in`
parameters) instead of leaving them to `decisions.md`. `errors.py` is
small, exact, and explains the traceback-versus-stack choice a reader
would otherwise have to work out. The surface does read as an
explanation. Specific notes:

- `blocks.py` is 1134 lines doing five jobs (transitions, actions,
  tables, extern results, the three block kinds). It is still readable
  because each section is separated and its rules are in the module
  docstring, but `Table` with its five overloads is 110 lines that, as
  finding 1 shows, currently reject nothing; if the fix lands they earn
  their place, and if it does not they should go, along with `Key[W]`,
  `Entry[KS]` and the three `_invariant` methods.
- Those `_invariant` methods (`blocks.py:310`, `:351`, `:472`) exist only
  to make a type parameter invariant. That is worth one comment each; a
  reader currently sees three methods nobody calls.
- `Control._run` fixes the IR order as actions, then tables, then the
  body, whatever the class-body order — which is right, and worth one
  sentence in the docstring, because a table must still be written
  *below* the actions it lists (a Python `NameError` otherwise, pinned in
  `test_checked3.py`).
- `Parser.select`'s two unreachability checks read as if they work; for
  `Bits` and `Enum` keysets they cannot (finding 2). Fixing the
  comparison makes the code honest as well as correct.
- The design's "What pyright checks, and what it cannot" table is the
  contract, and no module reproduces it: `values.py` carries the value
  rules, `views.py` the field rules, `blocks.py` the block rules, and
  nothing carries the whole. Findings 1 and 6 are both about rows of that
  table, and a reader checking either has to assemble it from three
  docstrings and `decisions.md`. The table belongs in `__init__.py`, next
  to the two clocks, with the four deviations marked in it.
- `_Field.__get__` (`views.py:176-180`) raises when `obj` is *not* None,
  which reads backwards until one has the class docstring above it — and
  that docstring does say why (instance attributes set in `__init__`
  shadow the descriptor). Good as it stands; noted because it is the one
  inversion in the package, and it survives only as long as the two stay
  adjacent.
- `tests/test_pyright.py`'s "skip if an import fails" scaffolding was for
  the period before the surface landed. Now that it has, a file whose
  imports break is a failure, not a skip, and the escape hatch will
  outlive its purpose quietly.
