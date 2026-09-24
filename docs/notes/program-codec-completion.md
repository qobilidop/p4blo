# Route to a representable Program JSON roundtrip

2026-09-23. Planning baseline `634a21a`, after the four table laws are merged.
Only this plan and the unregistered [parser probe](probes/ParserCodecProbe.lean)
are added. Production codecs, runtime, default registrations, tests and prior
evidence remain untouched. Independent [plan/probe review](reviews/program-codec-completion.md)
is clear, including a fresh pinned probe run and all six axiom sets.
Implementation awaits a separate scoped handoff.

## Recommendation

Take **five parser-syntax codecs next: Target, KeySet, SelectCase, Transition,
State**. They are a small closed dependency slice using only the already
committed Literal/Expr/Stmt/list laws. The standalone probe proves all five
actual-code roundtrips plus a mixed kernel witness without new helpers,
increased limits, decoder changes or successful-decoder callback premises.
This is feasibility, not default-audited production coverage.

Then take **Action/Block**, then **Export/Program**. Keep host-installed
**TableEntries/Entries** a separate optional side checkpoint: these are not
members of Program and must not silently become part of its claim. Do not
bundle all eleven remaining laws and their observer/error matrices into one
large proof/test refactor. Each checkpoint starts with its independently
reviewed, committed, source-pinned test baseline before production proof work.

There is no remaining codec termination barrier. All eleven actual remaining
decoders are ordinary total definitions in an acyclic graph; no recursive
Block tree or new statement recursion is hidden here. Control and deparser
are BlockKind constructors, not separate Control/deparser codecs. The parser
state type is actually named `State`, not `ParserState`. Text wrappers
`Program.fromJsonString`/`Entries.fromJsonString` add `Json.parse`; their
correctness is not implied by a JSON-value roundtrip.

## Exact remaining dependency map

Actual decoders are `Json.lean:734–821`; encoders `1075–1146` at this baseline.
Existing foundational declarations and table laws remain in CodecLaws's
namespace, split into focused modules. No additional direct numeric field
appears in any of these eleven records: all bounds are inherited.

| Codec | Actual dependencies | Wire-only premise |
| --- | --- | --- |
| Target | state string / accept / reject | True, all names and constructors |
| KeySet | exact Literal; masked value/mask; range lo/hi; dontCare | each embedded LiteralRepresentable |
| SelectCase | ordered KeySet list; Target | every set representable; no target restriction |
| Transition | direct Target; select Expr keys and SelectCase lists | every key ExprRepresentable and every case representable |
| State | name; ordered Stmt body; Transition | every statement StmtRepresentable and transition representable |
| Action | name; Param and Stmt lists | every ParamRepresentable and StmtRepresentable |
| Block | BlockKind; Param, Var, Action, Table, State, Stmt lists; two strings | every element in each typed list representable; all three kinds |
| Export | role and block strings | True |
| Program | error strings; HeaderType, StructType, EnumType, ExternType, ExternInstance, Block, Export lists; name/headers/metadata strings | every bounded declaration/block representable; string/enum/export lists unrestricted |
| TableEntries | block/table strings; Entry list; optional ActionCall | every EntryRepresentable; every present default ActionCallRepresentable |
| Entries | TableEntries list | every member representable |

Program's eventual predicate must cover every reachable uint32 field: Ty bit
width/stack size, Literal bit width, Expr slice bounds, Stmt push/pop counts,
KeyValue LPM prefix, Entry priority and Table size. Reuse the existing member
predicates; do not approximate the Program premise by checking nominal types
or top-level declarations alone. Decimal values/masks stay unbounded naturals.
No list-length bound, executable fuel or resource-budget claim is added.

## Preserve permissive wire domains

Parser names/targets may be empty, duplicated, unresolved or cyclic. Accept
and reject are distinct constructors; a present state string `""` is still a
selected oneof, not absent. KeySets admit every Literal kind: Boolean, error,
enum and zero-width/oversized numeric values. Mixed literal types/widths,
noncanonical masks and descending ranges are wire-representable. Select keys
need not be bits-typed, cases may be empty/duplicated/unequal in arity, wildcard
may coexist with any other set, and a select may have no keys or no cases.
State bodies may contain any representable Stmt, including statements that
semantic validation forbids in parsers. Do not require actual parser progress.

Likewise Action parameters retain all four Directions, not just directionless
action data. Block kind imposes no wire-level shape restriction: parsers may
carry body/actions/tables; controls/deparsers may carry states/startState.
All local/action/table/state/parameter lists may contain conflicting empty or
duplicate names. Exports need not resolve, agree with a block kind, use distinct
roles or satisfy calling conventions. Program errors need not begin with core
errors; nominal headers/metadata may be missing or unresolved. Even `{}` is a
successful empty Program decode. No Index.build, validator or execution
premise belongs in these laws or in canonical protobuf wrapper checks.

For host entries, arbitrary repeated block/table pairs, unresolved names,
mixed entries, priority zero, const-table overrides and optional empty defaults
remain wire data. Whether installation accepts or applies them is separate.

### Presence and diagnostic boundaries

Preserve these actual distinctions; do not infer stronger presence rules from
semantic comments in the schema:

- Missing/null oneof fields are absent; exactly one non-null recognized field
  is required. Multiple recognized fields fail before payload decoding, in
  decoder case-list order, not object insertion order. Unknown fields remain
  ignored as current behavior, not a compatibility policy.
- `Target.state ""` roundtrips. `accept:{}` / `reject:{}` / `dont_care:{}`
  accept object payloads (including ignored annotations), not arbitrary scalar
  payloads. A sole `accept:null` is no kind set.
- `Transition.select {}` succeeds with two empty lists. `direct:{}` fails
  at `.direct: no kind set`; missing/null/present-empty SelectCase.target and
  State.transition fail their nested oneof checks.
- Action `{}` succeeds with empty name/params/body. Export `{}` succeeds with
  two empty strings. Block `{}` fails at `.kind: unspecified`; BlockKind has
  exactly parser/control/deparser, no abstract unspecified constructor.
- Program `{}` and Entries `{}` succeed; TableEntries `{}` succeeds with
  empty strings/list and no default. Its absent/null default differs from
  present `{}`, which is some empty ActionCall, exactly as for Table.
- All ordinary repeated fields accept omitted/null/empty arrays as `[]`;
  a null list element is not the same as an omitted list. String defaults
  are empty, never guessed names. Existing numeric/decimal rules propagate.

Pin error evaluation order with simultaneous errors, not just isolated failures:
KeySet masked value before mask / range lo before hi; SelectCase sets before
target; select keys before cases; State name/body/transition; Action
name/params/body; Block name/kind/params/locals/actions/tables/states/start_state/
body; Export role/block; Program name/errors/header_types/struct_types/
enum_types/extern_types/extern_instances/blocks/headers/metadata/exports;
TableEntries block/table/entries/default_action. Arrays retain first failure,
zero/later/nested indices and `Decode.sub`'s empty-path formatting.

## Feasibility probe and proof-cost boundary

`docs/notes/probes/ParserCodecProbe.lean` imports only P4bloIR.CodecLaws.
It defines local parser wire predicates and proves all five actual codec laws
at every path. Transition composes two arbitrary arrays; State composes the
actual arbitrary Stmt array with Transition. Small object-shape exposure and
finite omission splits suffice; there is no new decoder, serializer, fuel,
assumed member-correctness callback or global heartbeat override.

Its `unusual_roundtrip` kernel witness includes all three Target constructors,
all four KeySet constructors, mismatched list arity/types, a descending range,
an unresolved zero stack, nested conditional statements, a max push count and
a huge zero-width literal. It includes a false range-literal bound premise and
twelve actual empty/null/default kernel answers, including the empty Program
and host entries. Those assembly defaults are not universal assembly laws.
All six named roots print exactly `propext`, `Classical.choice`, `Quot.sound`.

Fresh own caches, scoped working directory
`/Users/qobilidop/my/work/p4blo-program-codec-completion/ir`:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.CodecLaws
nix develop -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true /Users/qobilidop/my/work/p4blo-program-codec-completion/docs/notes/probes/ParserCodecProbe.lean
```

Dependency build exits 0 (`/tmp/p4blo-program-completion-deps.log`); final
probe exits 0 (`/tmp/p4blo-program-completion-probe-final.log`). The first
attempt omitted the type annotation on a constructor-function placeholder;
it failed elaboration and its dependent printed sorryAx results are not
evidence. The corrected final source has no admitted proof and all six roots
are clean. Independent review may execute the absolute probe with another
checkout's identical compiled CodecLaws and the same pinned Lean without
rebuilding executables. No full package/Python/schema/oracle gate is claimed
for this planning-only change. No Docker operations or old artifact changes.

For Block/Program, do not repeat the exponential field-presence split that
the Table proof already exposed. Their nine/eleven fields warrant the same
proved actual TreeMap lookup/omission factoring. Those helpers are currently
private in TableCodecLaws: they are **not** an available public proof API.
At that later checkpoint, propose the minimum extraction into an internal
shared proof-helper module, preserving old public laws and rechecking them.
Do not import mangled private names, copy a second decoder, or raise proof
limits by default. The parser checkpoint needs no such ownership expansion.

## Baseline-first implementation checkpoints

1. **Parser syntax:** proposed `ParserCodecLaws.lean`, `Tests.ParserCodec`,
   `tests/test_codec_parser.py`, narrow codec kind/endpoint/default registrations
   and a scoped evidence note. New kind labels should be `target`, `key_set`,
   `select_case`, `transition`, `state`; preserve old `key` (KeyValue) and
   `table_key` labels. Freeze/independently review/commit the test-only baseline,
   then implement five universal laws and a default-audited constructive State.
2. **Executable declarations:** after parser APIs are committed, baseline
   Action/Block independently, including direct three-constructor BlockKind
   observations and all permissive kind/shape combinations. Then two laws,
   mixed constructive Block, all inherited overflow negatives and audits.
   Review the helper extraction separately if it changes Table proof plumbing.
3. **Program closure:** after Block is committed, baseline Export/Program,
   then unconditional Export and universal representable Program laws. Require
   a kernel mixed Program witness that covers every bounded member family;
   a valid authored forwarder/firewall is an additional useful instance, not
   the only nonvacuity evidence. Do not silently strengthen the predicate to
   accept only those applications. Export may be proved during this checkpoint
   because it introduces no dependency beyond strings.
4. **Host entries (optional, separate):** two independently baselined laws
   reuse Entry/ActionCall and ordered arrays. This can run once table laws are
   committed, but it is not a prerequisite or part of Program completion.

Each baseline needs a complete ordered, nonzero, unique request inventory;
independent full constructor descriptors; canonical public protobuf load/dump
checks without validation; raw stdin/stdout/stderr/status; historical source
hashes pinned to the reviewed baseline commit; non-overwriting capture guards
and before/after source checks. Preserve old request inventories and artifacts.
Final replay checks historical hashes against historical git objects, then
separately matches current requests and expected answers. Never recapture an
old baseline because proof witnesses change its test-module source hash.

For parser canonical wrappers, place Target under a state's direct transition,
KeySet under a select case, SelectCase under select, Transition under State,
and State under Block.states. Preserve empty-message oneof presence explicitly.
For later Action/Block/Export, use their actual Program fields; for Program
use `ir.dump_json`/`ir.load_json` directly. Host entries have no dedicated
public IR JSON wrapper: existing DRT uses `json_format.ParseDict(..., pb.Entries())`.
Use the actual protobuf message's JSON conversion there, not a fictional
Program adapter or a newly added production API.
The wrapper is only codec transport, not a semantically valid program theorem.

Parser fixtures must observe every constructor and all contained expressions,
literals, statements, lists and targets. Cover all Literal families through
KeySet; Expr/Stmt member families and nested branches; zero/max/overflow
in every propagated numeric position; asymmetric three-element keys/cases/
sets/body order; both masked operands and range endpoints with unequal values;
empty/duplicate/unresolved targets and malformed competing fields. Include
nonobject, no-kind, multiple-kind, null and wrong-type payloads; absent/null/
empty/nonarray lists; later and nested errors; unknown annotations and decimal
normalizations. Root path `""` and a nonempty path need independent anchors.

Use existing strict `same_json`, duplicate-rejecting loads, shared lean_binary,
test_lean_agrees discovery and retained process-error handling. Do not generate
expected descriptors from Lean output or production encoder tables. Canonical
successes use protobuf; malformed acceptance languages need not match protobuf.

## Required independent challenges

For the next parser checkpoint, require actual compiling isolated mutations:

1. Reverse a real Transition case array or State body in the encoder only;
   unchanged universal proof or independent ordered anchors must reject it.
2. Pair accept/reject wire-label mappings in actual Target encode/decode.
   Roundtrip can remain consistent; literal wire inputs and direct native
   constructor anchors must reject the semantic remapping. Corrupt Python
   expected tags and the Lean descriptor separately to demonstrate that an
   independent native literal anchor still rejects their false agreement.
3. Pair KeySet masked value/mask (or range lo/hi) mappings on both actual sides.
   Use asymmetric full decoded answers, not only encoded roundtrip or lengths.
4. Change actual first-error order or a nested array index. Require an exact
   competing-error input; successful roundtrip does not specify diagnostics.
5. Drop an empty state target or change select-empty/direct-empty behavior.
   Preserve positive empty-select and negative empty-direct controls and report
   proof versus executable rejection distinctly.

Later Block tests additionally challenge shared BlockKind.names with all three
independent literal anchors and a paired fixture/observer; Program tests challenge
equal-shaped slot swaps (headers/metadata, role/block, header/struct lists) and
one-sided list loss/order, all embedded-bound paths and first-error precedence.
Host entries challenge absent versus some-empty default independently.

Compile the real mutated codec before crediting proof rejection. A stronger
intermediate proof lemma failing is not a mathematical disproof of roundtrip.
For buildable runtime faults retain source-matched raw mismatches and matching
ordinary harness views; replay live, restore, rebuild and replay clean. Packet
preflight setup failures are not scoped codec detections. Use the existing
direct-test-body fallback only if actual preflight blocks, with an explicit
distinction from ordinary required DRT. Never count views or observations of
one request across faults as additional independent inputs.

Each implementation gate: both packages/default audits/native tests before
consumers, old/new focused codecs, required real-Lean discovery, strict historic
and fault replays, lint/type checks, integrator-owned combined full gates and
independent read-only review before small coauthored commits. Production Json
should remain byte-identical. If a genuine defect is found, stop and propose a
separate reviewed fix rather than silently altering baseline behavior.

## Confidence and exclusions

High confidence in the five-codec next boundary and actual proof feasibility
after the complete probe. Medium-high confidence in the staged Block/Program
composition; the main remaining cost is reusable object lookup plumbing and
independent baseline breadth, not recursion. Revisit scope only if a concrete
member proof or reviewed observer matrix exceeds a small checkpoint; keep
pending laws named rather than replacing universality with a fixture callback.
Medium confidence in long-term module placement: preserve CodecLaws public
names and revisit private helper sharing at the demonstrated nine-field Block
seam, not by introducing a serializer framework now.

Even final Program JSON-value roundtrip would not prove JSON text or binary
protobuf correctness, arbitrary decode/encode normalization, unknown-field or
version safety, resource bounds, semantic validation, parser termination,
table selection, call/execution correctness, or universal Python equivalence.
