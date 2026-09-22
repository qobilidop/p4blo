# Steps 2-5 review: printer, architectures, STF, oracle, DRT, eDSL, Lean

Reviewer: independent, read-only, against `main` at fa62352 (the theorem
commit landed while I was reading; HEAD was d662e32 when the reproducers
last ran, and nothing below depends on the intervening commits).
Reproducers: `test_review2.py` beside this file, 16 tests, each asserting
the *defective* or *gap* behavior it documents, all passing:

    nix develop -c uv run pytest scratchpad/review2/test_review2.py -p no:cacheprovider

Eight tests need the Lean binary (`lean/.lake/build/bin/p4blo-lean`, present)
and three need Docker's `p4lang/p4c` (present); they skip otherwise. The
printed programs the p4c tests judged are kept beside the tests as
`port_parser.p4`, `noaction_body.p4`, `narrow.p4`.

Findings are ranked by severity. "Confirmed" means a reproducer runs.

## Confirmed defects

### 1. The shim provides `ingress_port` to the control only; the parser sees zero (high)

- `python/p4blo/printer.py:271-272` builds the prologue
  `M.ingress_port = sm.ingress_port;` and `:774-778` emits it at the top of
  the exported *control's* `apply`. Both architectures write
  `ingress_port` into `M` before the *parser* runs
  (`python/p4blo/arch/switch.py:29-31`, `filter.py:29-31`), and the
  contract says so: design.md, "Metadata contract", `provided` means
  "the architecture provides it before the block runs"; contract.py:33
  says the same. A parser that reads `meta.ingress_port` runs on the port
  in p4blo and on `0` under the oracle.
- Violates claim 2's setup: the printed program is not the IR program
  under the shim, so an oracle divergence on such a program would be the
  printer's, not the semantics'. Nothing in the corpus reads the port in a
  parser, which is why the vectors did not catch it.
- Reproducer (`test_printer_provides_ingress_port_after_the_parser_has_run`):
  a parser that `select`s on `meta.ingress_port` and marks port-1 packets
  for drop. Under the switch, port 0 unicasts and port 1 drops; the
  printed parser contains no `standard_metadata.ingress_port`, the only
  copy is in `control C`, and p4test accepts the program, so the oracle
  would run it and unicast the port-1 packet.
- Fix: `standard_metadata_binding` should return the provided-field
  prologue for the parser too, and `states()` (`:667`) should emit it as
  the first statements of the start state (or of the synthesized `start`
  when `start_state != "start"`; re-entering the start state in a loop
  re-runs an idempotent copy). Keep `parser_error` where it is, since
  v1model sets it after the parser, as the architectures do. Add one
  parser-side test to `test_standard_metadata_binding_is_by_name`.

### 2. A declared `NoAction` with a body is printed as core.p4's empty one (medium)

- `printer.py:705-708` skips any action named `NoAction` ("core.p4
  declares it; redeclaring it would clash"), body and all. The IR has no
  implicit declarations (corpus/forwarder/README.md, "NoAction"): a
  program's `NoAction` is an ordinary action of the block, and
  `interp/tables.py:143-156` runs whatever body it has when a table's
  `default_action` or an entry names it. Only a table with *no*
  `default_action` gets the implicit no-op (`default_actions[ref] = None`).
- Violates the printer's own contract ("a faithful reversal of the IR",
  `printer.py:6-8`) and semantics.md, "Table miss": the default action
  that runs is the program's.
- Reproducer (`test_printer_drops_the_body_of_a_declared_noaction`):
  `action NoAction { meta.drop = true; }`, a table with
  `default = "NoAction"`. p4blo drops every missed packet; the printed
  program has no `meta.drop = true` anywhere, prints
  `default_action = NoAction();`, and p4test accepts it.
- Fix: skip the declaration only when the body is empty and the action
  has no parameters; otherwise raise `PrintError("NoAction with a body
  cannot be printed for core.p4")` or rename it (`NoAction_` plus a
  rename map for table action lists, entries and calls). The validator
  could equally reserve the name: one `NAME_RESERVED` rule saying a
  `NoAction` action must have an empty body and no parameters, which
  matches what every P4 reader assumes the name means.

### 3. "Both errored" is agreement whatever the reasons, and the Lean sweep never checks it is zero (medium)

- `python/p4blo/drt/run.py:67-69` `Outcome.agrees_with` returns `True`
  whenever both sides carry an error, without comparing them;
  `compare_cases` (`:259-262`) counts the case in `both_errored` and not
  in `divergences`. `tests/test_drt.py:377-385`
  `test_lean_agrees_with_python` asserts `divergences == []` only; the
  fake-Lean test at `:277` does assert `both_errored == 0`, the real one
  does not. So a sweep in which every case errored on both sides for
  unrelated reasons is green in CI.
- Violates claim 4's wording, "zero unexplained divergences": two sides
  that stop for different reasons have not agreed on anything, and the
  report's summary line is the only place the count appears.
- Reproducer (`test_both_errored_counts_as_agreement_with_different_reasons`):
  two forwarder cases, an lpm entry with prefix 40 on a 32-bit key and an
  ingress port of 600. Python reports `InstallError: ...` and
  `ValueError: 600 does not fit in 9 bits`; Lean reports its own
  sentences; `compare_cases` returns no divergence and `both_errored == 2`.
  For the record, the sweep as it stands is clean: 300 cases per corpus
  program at seed 7 gave `0 errored on both sides` for all nine.
- Fix: assert `report.both_errored == 0` in `test_lean_agrees_with_python`
  (the generator promises installable entries and in-range ports, so any
  error is a bug), and make `agrees_with` compare an error *class* (the
  Python exception name against a Lean prefix, or a normalized message,
  since `Tables.lean` already copies the Python sentences).

### 4. The differential loop cannot reach an out-of-range register or counter index (low)

- `python/p4blo/drt/generate.py` draws packets by walking the parser and
  entries by key; extern indices come from the program. The one stateful
  corpus program indexes `register(256)` and `counter(256)` with
  `(bit<32>) hdr.myhdr.reg_idx_to_update`, an 8-bit field
  (`corpus/stateful/stateful.py:19, 32-33, 44`), so no generated case can
  index at or beyond `size`, and the closed behavior "read beyond size
  yields zero, write is ignored" (`externs/register.py:10-12`,
  `lean/P4blo/Externs.lean:107-114`) is never exercised by the sweep.
- Reproducer (`test_drt_never_generates_an_out_of_range_register_index`):
  a recording `Register` over 2000 generated cases; every index is below
  256. `test_lean_agrees_on_out_of_range_register_and_counter` then runs
  a `register(4)`/`counter(4)` program indexed by an 8-bit field on both
  sides: they agree, so this is a coverage gap, not a divergence.
- Fix: a companion corpus program (or a smaller `r` in a copy of
  `stateful`) whose register is narrower than its index field, with
  vectors that read a cell past the end; or a generator knob that mutates
  extern constructor sizes.

### 5. `advance` accepts any `bit<N>` amount; the printed program does not compile (low)

- `python/p4blo/validator.py:880-881` checks `advance.bits` with
  `is_bits`; core.p4's `advance(in bit<32> sizeInBits)` takes exactly
  `bit<32>`, and `printer.py:372-373` prints the expression verbatim.
  The eDSL only widens an `int` (`edsl/blocks.py:548-553`), an `Expr` of
  another width passes through.
- Violates the printer's claim to feed the oracle: the oracle reports
  `error`, not a divergence, so nothing is masked, but a valid IR program
  has no P4 form. (p4c *does* accept a `bit<4>` header-stack index, checked
  with `idx.p4`, so `type_of_index` needs no change.)
- Reproducer (`test_validator_accepts_widths_that_p4_rejects_for_advance_and_index`):
  `advance(n)` with `bit<8> n` validates and runs; p4test rejects the
  printed program: "Cannot cast implicitly type 'bit<8>' to type
  'bit<32>'".
- Fix: require `bit<32>` in the validator (one line, plus a sentence in
  semantics.md, "advance"), or have the printer wrap a narrower amount in
  `(bit<32>)`. The validator is the better place; the IR is
  post-elaboration and the frontend owes the cast.

### 6. An STF port that does not fit `bit<9>` escapes as `ValueError` (low)

- `stf.py:341-344` accepts any decimal port; `arch/contract.py:131-132`
  builds `Bits(9, value)`, whose `__post_init__` raises `ValueError`
  from inside `Switch.run`/`Filter.run`, past `stf.replay`, with no line
  number. Lean rejects the same request with a clean error
  (`Switch.lean:112`).
- Violates the runner's docstring ("a vector file that cannot be ... resolved
  against a program" is an `StfError` with its line) and the DRT's
  symmetry: finding 3 shows this exact pair counting as agreement.
- Reproducer (`test_stf_port_out_of_range_is_a_value_error_not_a_failure`):
  `packet 600 00` on the forwarder raises `ValueError`.
- Fix: the architectures check `ingress_port < 2**9` and report through
  `diagnostics` or a typed error; the STF parser rejects a port over 511
  with its line.

### 7. `exact()`/`lpm()`/`ternary()` take anything; a shadowed field name dies as `AttributeError` (low)

- `edsl/blocks.py:161-179` `Key` is a bare dataclass and the three
  constructors do not check `isinstance(expr, Expr)`. `Expr.type` shadows
  a field named `type` by design (`edsl/expr.py:46-51`), so
  `exact(c.hdr.eth.type)` silently holds a `pb.Type` until
  `Control.table` (`:850`) evaluates `k.expr.pb` and raises
  `AttributeError: pb`.
- Violates the eDSL's stated error discipline (`types.py:20-26`, "a
  mistake the builder can see at build time" is an `EdslError`). The
  parser_error corpus already met this shadow and worked around it.
- Reproducer (`test_edsl_key_on_a_shadowed_field_is_an_attribute_error`).
- Fix: `Key.__post_init__` (or the three helpers) raise
  `EdslError("a key is an Expr; hdr.eth.type is the expression's type, use
  hdr.eth.field('type')")`.

### 8. A program with no exports loads under both architectures and fails at the first packet with `KeyError` (low)

- The validator has `EXPORT_DUPLICATE` and `EXPORT_SIGNATURE` but no
  rule that the roles an architecture needs exist (`validator.py:773-800`);
  `arch/loader.py:39-49` checks the contract but not the exports; the
  first `loaded.block("parser")` (`loader.py:30-32` via `ir.py:154-158`)
  raises `KeyError('parser')` from inside `run`. `Switch.lean:75-78`
  refuses at load with "the program exports no 'parser' block".
- Violates the loader's promise ("everything that happens once per program
  rather than once per packet") and is one more Python/Lean asymmetry in
  the error class of finding 3.
- Reproducer (`test_arch_loads_a_program_without_exports_and_fails_late`).
- Fix: `Loaded.__post_init__` or `load()` resolves the roles the
  architecture will ask for and raises a `LoadError` naming the missing
  role; the filter needs two, the switch three.

### 9. An `int` shift amount takes the left operand's width (low)

- `edsl/expr.py:322-328` `_shift` gives a Python `int` amount the type of
  the shifted operand, so `bit<2> x << 4` is refused with "4 does not fit
  in bit<2>" although P4 accepts it (the result is 0; semantics.md,
  "Shifts": "the shift amount is any `bit<M>`"). `assign_slice`
  (`blocks.py:320`) inherits the limit, though its `lo < width` always fits.
- Reproducer (`test_edsl_refuses_a_shift_amount_p4_allows`); the
  workaround is `x << p.literal(4, bit(8))`.
- Fix: give an `int` amount the smallest width that holds it (or a fixed
  `bit<32>`); the IR does not care, and no cast appears either way.

## Plausible but unconfirmed (at most five)

- **P1. Dropping `no_packet` lets a later `expect` claim an earlier
  packet's stray output.** `oracle/run.py:127-130, 158-159` turn
  `no_packet` into a comment and rely on the simulator's end-of-file
  leftover check. The README says the simulator matches by port from one
  queue of unclaimed outputs as expectations arrive. If so, `packet A;
  no_packet; packet B; expect 1 X` passes on the oracle when A wrongly
  emits X on port 1 and B emits nothing, and fails on p4blo. No corpus
  vector has that shape; `forwarder/miss.stf` and `too_short.stf` are
  single-packet. I could not run the simulator (not built here). A
  translation that also asserts *ordering* (an `expect` right after each
  `packet` for whatever p4blo produced) would close it, or an `assert`
  that the vector's `no_packet` is last.
- **P2. `egress_port == 511` and ports beyond `ports`.** `switch.py:50`
  and `Switch.lean:130-134` emit on whatever `egress_port` holds, and
  neither architecture checks `ingress_port < ports`. Under v1model
  `egress_spec == 511` is BMv2's drop port and `mark_to_drop` writes
  exactly that, so a program that writes 511 without `drop` diverges from
  the shim (P4-SpecTec's v1model presumably copies the convention). One
  sentence in decisions.md, "Architecture rules", either way; the DRT
  generates 9-bit action data, so 511 appears in the sweep and both
  interpreters agree with each other already (checked in
  `test_lean_agrees_on_flood_drop_and_wide_ports`).
- **P3. The comparison ignores diagnostics.** `run.py:110-120` builds a
  fresh `Switch` per case and drops `switch.diagnostics`;
  `parse_reply` (`:134-153`) ignores Lean's `"diagnostic"`. A
  misaligned-parse drop on one side and a program `drop` (or an
  empty flood) on the other compare equal, as do two misaligned parses
  that consumed different bit counts. `Outcome` could carry the
  diagnostic and `agrees_with` compare it.
- **P4. `checksum16` over a width that is not a multiple of 16.**
  `externs/checksum.py:44-46` and `Externs.lean:149-153` pad with zero
  bits at the *end*; the corpus widths are 144 and 16, so the oracle has
  not judged the padding convention against `hash(..., csum16, ...)`
  (BMv2's `BufBuilder` packs bits then pads the last byte, which should
  agree, but P4-SpecTec's model is unread). A csum16 vector over a
  `bit<12>` or `bit<24>` field would settle it.
- **P5. Sub-block instantiation names can collide.** `printer.py:423-425`
  names every instantiation `<block>_inst` inside the caller; a local or
  parameter of the caller with that name (`Rewrite_inst`) is legal IR and
  produces a P4 program that p4c rejects (an `error` verdict, not a
  silent one). `missing_roles` and `shim_controls` already check the
  shim's own names against `program_names`; the instantiation names
  should be checked against the caller's scope, or drawn from a counter.

## What I checked and found correct

- **Printer, expressions.** Every non-atom operand is parenthesized
  (`_operand`), so the printed precedence is the IR's for every operator
  incl. cast, unary minus, slice-of-member, concat, mux and nested mux;
  literals carry widths; `bool`/`bit<1>` casts print as P4 allows; enum
  and error literals qualify. The goldens typecheck here (p4test ran on
  all five).
- **Printer, tables.** Ternary const entries as `entries` with
  `priority = N` in descending order and `largest_priority_wins = true`
  reproduce "larger wins" (the priority corpus passed the oracle on
  overlapping entries). The lpm mask `((1 << p) - 1) << (w - p)` is
  right for every `p` in `[0, w]`, and `x &&& 0` compiles. The lpm
  const-entry priority gap is documented in oracle/README.md and stands.
  `NoAction` is appended to the action list only when p4c needs it.
- **Printer, externs and blocks.** `hash(r, csum16, 16w0, {d}, 32w65536)`
  is the one's-complement checksum for 16-aligned data (the forwarder's
  vectors carry the values the oracle confirmed); register width comes
  from `read`'s out parameter; counters are `packets`; placement keeps
  one piece of state per IR instance. Callees precede callers; sub-parser
  and sub-deparser calls get the packet argument; exported signatures are
  checked against the role.
- **Shim contract.** `parser_error` is copied at control entry, which is
  when both architectures write it (after the parser's own `inout`
  writes); `egress_spec` then `mark_to_drop` last, so drop wins;
  `flood` is left to the architectures as documented; a wrong-typed
  contract field is a `PrintError`, as it is a `ContractError` at load.
- **Architectures.** Both write `ingress_port` before the parser, run the
  control after a rejection, drop a misaligned parse with a diagnostic,
  read undeclared fields as zero and swallow writes, and share one
  `Loaded` (so extern state) across a replay; the filter forwards the
  original bytes. Lean's `Switch.run` agrees on every fate incl. flood
  with 8 ports, an ingress port beyond `ports`, egress 511 and egress
  beyond `ports` (`test_lean_agrees_on_flood_drop_and_wide_ports`).
- **STF runner.** The prefix rule and `$`, `*` nibbles, the strict
  per-packet output pairing, `no_packet` placement, qualified table and
  action names, stack-indexed key names, canonical lpm/ternary checks
  with line numbers, ternary-only priorities, and the per-packet
  reinstall through `stf_driver` all do what the docstring says.
  Nothing p4c's vectors write is accepted with a different meaning: the
  p4c-isms that differ (`&&&` in values, `expect <port>` without bytes,
  unknown statements, a priority on a non-ternary table, non-canonical
  values) are `StfError`s, not silent passes.
- **Oracle translation.** Prefix length as priority is equivalent to
  longest-prefix among the matching entries (ties are install errors on
  p4blo's side, and entries whose other keys differ never compete;
  checked on Lean and Python in
  `test_lean_agrees_on_host_install_errors_and_default_overrides`).
  `render_masked` is right for nibble-aligned and unaligned masks at
  full width; every `add` is resolved by `stf.to_entries` first, so the
  oracle never sees a vector p4blo refuses.
- **DRT generator.** It reaches every parser state, every select case
  incl. `reject` and `default`, truncates at arbitrary byte positions
  (so `PacketTooShort` with zero and with partial remaining bits both
  occur), floods with random 9-bit egress ports, replaces non-const
  defaults, and draws canonical entries of every kind; an `InstallError`
  during generation drops the entry, never the case. Register indices
  repeat across cases (8-bit field, birthday bound).
- **Lean versus Python.** Read side by side: values, casts, shifts by
  wide amounts, `lastIndex` wrap, stack reads/writes past the end,
  `push`/`pop` beyond the size, extract target-before-packet, sub-parser
  copy-back on error, revisit rule, select, table install/lookup/tie
  rules, host default restore, extern direction handling and copy-back,
  the emitter's padding. Then run on both sides: 300 cases per corpus
  program (seed 7, zero divergences, zero both-errored), 300 cases each
  on the `control_features`, `parser_features` and `externs` printer
  goldens (which exercise the operators the corpus does not), and the
  hand-picked edge programs in `test_review2.py`: out-of-range
  register/counter, every install-error path, const-default override,
  longest prefix with a differing exact key, ternary priorities,
  `StackOutOfBounds` through a sub-parser called twice, `PacketTooShort`
  inside a callee (out-arg copy-back), extract into `hs[5]`, push 3 /
  pop 5 on a 2-stack, `lastIndex` wrap to `bit<8>` 255,
  `verify(false, NoError)`, lookahead and advance past the end, a 4-bit
  header (misaligned and re-aligned), and a no-consumption loop
  (`ParserTimeout`). All agree.
- **eDSL.** Int literals take their width from the other operand, the
  target or the parameter, never from nowhere; `&`/`|`/`~` on booleans
  build `&&`/`||`/`!` whose short-circuit is the interpreter's (the eDSL
  only builds trees, so Python's eager operand construction changes no
  meaning); `__bool__` refuses Python `and`/`or`; casts are exactly the
  three the semantics allows; `assign_slice` is the documented
  read-modify-write; `elif_`/`else_` attach to the right `if`; ternary
  entries canonicalize `dont_care` and plain ints; a non-canonical
  `prefix()` reaches the validator, which rejects it.

## Readability

- `printer.py` reads well top to bottom and its docstring conventions are
  the right kind of promise; `standard_metadata_binding`'s table is the
  clearest statement of the shim anywhere in the repo, which is exactly
  why finding 1 is worth a row: the table's "provided" column should say
  *where* (parser start) as design.md does. `_Typer` is a third small
  type checker beside the validator's and `interp/widths.type_of`;
  `stf._type_of` is a fourth. One `widths.type_of` used by all three
  would remove three places that must agree.
- `arch/` is the most readable package: fifty lines each and no P4, as
  claimed, and `contract.py`'s `Metadata` view makes "undeclared reads as
  zero" visible in one method. The two `run` methods are near-duplicates
  up to the deparser; a shared `_parse_and_control` would leave the
  difference, the fate, as the only text.
- `stf.py`'s docstring remains the model; `_parse_pairs` and
  `_parse_pairs_raw` are the same loop twice (one parses numbers, one
  does not) and could be one function with a flag. Program-side
  `StfError`s from `dotted`/`key_name`/`_key_width` carry no line, which
  the docstring's "when there is one" covers but a reader of a failure
  will not know.
- `oracle/run.py` and its README are unusually honest about what the
  oracle does not check (longest prefix, `no_packet`, registers); P1
  above is the one consequence the README does not draw.
- `drt/generate.py` is the best-documented module of the step: the walk
  is explained before it is coded, and `Tuning` makes every probability
  a named number. `run.py`'s `agrees_with` is the one line whose leniency
  the docstring states ("or when both report an error") without saying
  why that is acceptable; finding 3 is that sentence.
- `edsl/expr.py`'s attribute-shadowing rule is documented, but the
  failure mode when it bites (finding 7) is an `AttributeError` two calls
  later; the eDSL otherwise fails early and in its own words.
- Lean mirrors the Python module for module and function for function,
  with the Python sentences as error strings, which made the side-by-side
  read mechanical; `Exec.lean`'s `callBlock` says in four lines what
  `stmt.py`'s `try/finally` says, and the `M` monad comment in `Env.lean`
  ("the state survives a fault") is the one non-obvious property and is
  stated up front.
