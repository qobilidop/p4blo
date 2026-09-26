# IR design rationale

Reasons and still-binding tradeoffs, consolidated from the register on 2026-09-26.
[Design](../../docs/design.md), [semantics](../../docs/ir-semantics.md),
[coverage](../../docs/p4-spec-coverage.md) and [authoring](../../docs/python-edsl.md)
own the contracts; this note preserves their decision dates and unique rationale.

## Wire grammar and elaboration

- **Pre-1.0 package** (2026-09-22): `p4blo.v0` is intentional; except buf's
  version-suffix lint rather than rename to `v1alpha1`.
- **Schema choices** (2026-09-22): one kind-tagged Block avoids tripling shared
  machinery; scoped names make goldens read like programs; typed oneofs fit the
  roughly twenty fixed operators. Typed leaves, value widths and one inference
  pass suffice, so expression annotations would double goldens. Dedicated
  packet/header nodes reverse directly in the printer and reserve "extern" for
  declared externs. Separate expressions/lvalues avoid a second dotted-string
  syntax that cannot express indices. Annotation fields start at 100 to separate
  metadata; rename Python-keyword fields to avoid `getattr`; informative table
  size preserves printer roundtrips.
- **Elaboration boundaries** (2026-09-22; bridge 2026-09-24): coverage owns the
  rewrites for slice lvalues, `switch(action_run)`, `type`/`typedef`, inlined
  functions and per-instantiation blocks. `int<N>` stays out: no corpus need and
  twice the arithmetic rules. String/non-header arrays, `packet_in.length()`,
  static extern methods, mutable initial entries/per-entry const, object
  initializers and abstract methods are scope exclusions, additive if wanted.
  Range/optional/`..` entries are excluded by thesis: core.p4 declares only
  exact/ternary/lpm. The bridge rewrites covered rows and refuses excluded rows
  by name; it does not silently broaden them.
- **Decimal strings and canonical JSON** (2026-09-23): emit zero explicitly and
  reject missing strings because Protobuf's empty default was hidden by Lean's
  absent-as-zero decoder. [Assurance](../../docs/assurance.md) owns the tested
  canonical profile and parser differences, including unknown keys, enum numbers
  and camelCase. Reject ambiguous JSON before information is lost, while retaining
  semantically invalid IR for experiments.

## Independent blocks and authoring

- **One assembly context, no fragment linker** (2026-09-25): recompilation
  preserves declaration order and shared type/sub-block/extern identities. Core
  libraries exclude bindings; the architecture's flat BlockAssembly preserved
  corpus payload fields/bytes while intentionally changing descriptors/generated
  APIs. Transport compatibility does not make assembly a complete program or
  return binding choices to core.
- **Local, explicit extern registration** (2026-09-25): generic `edsl.Extern`
  must not imply a built-in switch or fixed services. Architecture support owns
  concrete declarations; independent Shapes and per-instance factories keep
  registration separate from loading's registry/contract/role selection.
  `arch.v1model` selects the supplied environment. Registration grants neither
  Lean semantics nor printer support.
- **First-order extern state** (2026-09-24): kind, optional width, cells and
  private configuration remain data, with `ExternModel` supplied at load. This
  leaves `Run` unparameterized and cells inspectable. Closure threading lacked a
  total Lean definition; threading type parameters through all theorems was
  invasive without expressive gain. Confidence medium; revisit if cells cannot
  carry a family's structured state.
- **Readability before syntax** (2026-09-25): the router/firewall/load-balancer
  examples use domain aliases, symbolic predicates and build-time helpers with
  explicit assignments/runtime branches. Keep unchanged goldens and independent
  state/packet tests as acceptance anchors; examples remain self-contained until
  sharing gives a demonstrated authoring gain.
- **Four pyright deviations** (2026-09-22): width aliases/literals type as places
  so literal targets fail only at runtime; Bool/Enum/Error have no static place
  split; extern `in` widths and sub-block call arguments are checked at runtime.
  The type checker forced these compromises. Separately, overloaded `assign`
  reports `reportCallIssue`; `impl/python/tests/edsl/test_typing.py` pins static
  rules and the corresponding must-fail fixtures.

## Semantic choices

- **Fresh-scope locals** (2026-09-24; eDSL followed 2026-09-25): re-zero on
  parser-state/action/inlined-function entry because P4-SpecTec enters fresh
  scopes while IR block locals persist. Bridge review exposed validated
  disagreements, requiring elaboration resets.
- **No-consumption parser revisit instead of fuel** (2026-09-22): fuel would
  make meaning depend on an unspecified number; the chosen rule matches BMv2.
- **Continuation machine** (2026-09-23): total single-operation steps and a
  proof-visible fixpoint connect finite traces to results. This does not prove
  termination of validated programs.
- **Entry priority** (2026-09-24): larger wins and const numbering follows the
  specification, not the compiler backend's reversed convention. The
  [priority disposition](../../docs/oracle-discrepancies.md) and
  [corpus derivation](../../tests/programs/corpus/priority/README.md)
  retain the explicit/implicit numbering derivation, ignored `@priority`, exact
  source disagreement and explicit printed priorities that pass both oracles.
- **Register and CRC choices:** zero for out-of-range reads is deterministic
  implementation-defined policy, unlike BMv2's unchanged destination; keep the
  exact vector's strict xfail and revisit only if a corpus program depends on it
  (2026-09-22). Stateless CRC16/CRC32 use exact byte-aligned widths, full results,
  no padding/range reduction: independent answers exposed P4-SpecTec's odd-byte
  defect and BMv2 confirmed standard behavior (2026-09-23). The public discrepancy
  catalog and architecture profile own the exact cases and contracts.
