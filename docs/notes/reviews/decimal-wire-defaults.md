# Decimal wire defaults review

Initial independent inspection, 2026-09-23. Reviewed the integrator's
test-first decimal-default regression and existing decoder read-only.
The final minimal decoder change and focused post-fix tests were subsequently
reviewed as recorded below.

## Confirmed defect

Independently reproduced all eight combinations of omitted/null fields
and `Literal.bits.value`, LPM value, ternary value and ternary mask.
Used the new test's valid program factories with the independently built
`411ba82` executable in the review worktree. Python protobuf parsing
succeeded, then validation rejected exactly one `LITERAL_FORMAT` or
`ENTRY_SHAPE` issue. Lean accepted every malformed program with exit zero.
The reproduction command exited zero after asserting those outcomes.
No build or source write was performed in the integrator's worktree.

Both current decoder paths explicitly supply `Nat` zero when the field is
missing or null. This disagrees with the protobuf string default, which
is empty and is not a decimal numeral. It can hide encoder defects and
silently invent a valid value from malformed input. The existing encoder
already emits explicit `"0"`, so fixing rejection does not require an
encoder or semantic change.

## Proposed fix and review boundaries

- A shared `Decode.decimalField`, defined before the literal decoder,
  should parse `strField` using `decimal` at the complete subfield path.
  Missing/null then become the protobuf empty string and are rejected;
  explicit zero and leading-zero spellings remain accepted.
- Share that helper across bits, LPM and ternary fields. Preserve ordinary
  `uint32` defaults and the direct decimal-string exact-key variant.
  Exact-key null participates in oneof presence rules, not a numeric-zero
  default; this fix should not change those rules.
- The test-first matrix covers four field locations, six rejected forms
  (missing/null/empty/negative/hex/number) and three accepted decimal forms.
  Assertions check the independent Python parse/validation outcome and
  Lean exit status plus field-specific diagnostics, not just a generic
  process failure. Positive tests establish parse/index acceptance, not
  whole-program semantic equivalence or validator parity.
- Recommended and accepted by the integrator: exercise malformed host
  table entries as well, because `Entries.decode` uses the same key decoder
  during an execution session. The request must return an error without
  changing extern state, and a following valid request should still work.
- Keep claims narrow: this is neither full ProtoJSON support nor a fix to
  unknown-field compatibility, duplicate keys, alternate naming, range
  validation or decimal resource limits. In particular Lean `Nat` and
  Python's decimal conversion limits require separate representability
  and resource policy if a universal codec claim is attempted.

## Final source review and independent focused verification

The implemented diff matches the proposed helper exactly, moves it into
`Decode`, routes bits values through it, and removes the old private
zero-default helper. LPM and ternary now resolve to the shared helper;
exact keys, numeric defaults and all interpreter bodies are unchanged.
Twelve Lean cases independently check missing/null/empty errors for the
four affected fields. The semantics document distinguishes pipeline-stage
differences from full ProtoJSON parity.

Independently invoked all **42** current Python regression cases against
the integrator's already-built executable, without rebuilding or modifying
its worktree. **All passed**, command exit zero: 24 malformed program
inputs, 12 accepted decimal spellings, and six host-entry sessions. Each
session checks valid/malformed/valid execution with exact output and
counter-state observations **1 / 1 / 2** on both implementations. The
malformed request is rejected before execution and does not poison the
following request. Temporary program files stayed outside the main tree;
source bytecode writes were disabled.

The integrator reports both Lean package gates passing with **348** spec
checks; this review did not independently rebuild those packages. Full and
required differential gates were still running when the focused review
completed. No blocking finding remains in the minimal decoder increment.
