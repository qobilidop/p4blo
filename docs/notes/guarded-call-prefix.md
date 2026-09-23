# Actual guarded call prefix

2026-09-23; based on committed `21410b6`, following
[call-body-prefix-plan.md](call-body-prefix-plan.md). Composes actual built
body entry, control expansion, real local assignments and guarded authored
body. It deliberately stops before observer execution or normal return.

## Exact theorem and assumptions removed

`GuardedCallPrefix.source_prefix` starts with actual
`.block "RewriteBody" PlainCallEntry.args :: K`. It quantifies arbitrary
caller Run, hdr/meta/route source Data, observer Value, statement suffix and
continuation K. Its premises name the actual built `WithBody.index` of the
entire flat body, caller BlockFrame and four actual caller read equations.
It does not assume an already-installed callee or post-initializer source
frame. Those are established through the real entry and assignments.

The one body is exactly:

```text
scratch := bits8(19); unrelated := bits8(165);
guardedForward.lower ++ suffix
```

`initializers_eq` is a kernel rfl equation with the reviewed actual wrapper
pair. `selected_body` is a kernel rfl equation identifying the complete body
with `CallBodyEntry.body` when suffix is its actual observer. The theorem
composes existing `source_entry_with_body`, one actual control runBlock
transition, `CallInitializers.source_steps`, the existing concrete field
command `steps_prefix`, and the independent guarded application policy.
No new AST, executor, fuel, binder or source denotation is introduced.

The exact endpoint has no fault and work:

```text
statements suffix :: blockReturn originalCaller actualParams args :: K
```

Its Run equals the original caller Run with **only the entire frame replaced**.
The final frame has the actual body-bearing scope, no action layers, actual
mode agreement, full independent policy FrameMatches, unchanged observer and
unrelated165. Its source store starts from arbitrary hdr/meta/route and
scratch19, then uses the separately proved guarded Snapshot policy. Both
initializers and the guarded body separately have authoritative scoped typing
under the actual resulting declarations. No suffix typing is assumed.

This is not ChangesOnlyVars between caller and callee: call entry changes
scope. ChangesOnlyVars is used only within the installed callee, then combined
with exact entry frame replacement. Consequently packet/cursor, emitter,
entries, externs, visits and **all** Index fields remain exactly those of the
arbitrary caller Run. Its entire original frame is captured verbatim in the
pending return. No independently reconstructed HashMap equality is required.

Invalid headers remain in scope. The authored guarded policy changes only
drop on invalid input; the entire call prefix additionally installs a callee
and initializes its locals, so it is not described as changing only drop.
The observer Value is preserved, not proved well-typed merely by binding it.

Confidence high in the semantic composition; medium in the fixed four-root/
two-local API's ergonomics. It removes real callee initialization and body
entry assumptions without broadening the runtime. Revisit when another call
profile requires reuse. A later empty-suffix normal-return composition can
consume the administrative statements[] item and actual return; that is not
proved here. Caller construction, parsing, route lookup, checksums, observer
correctness, copyback/failure unwinding, packet fate and whole-program/global
validation remain outside this result.

## Independent boundaries

The concrete kernel application supplies a nonempty caller, real built Index
and actual read facts for arbitrary profile values and suffix. Native tests
cover all validity pairs, hit values, TTL0/1/2/255 and prior-drop values,
crossed with empty, actual observer and faulting suffixes: 192 cases. Literal
step counts are 11/14/17/20/23/31, derived by hand, not computed from a command
cost semantics. Entry after one step must have locals0/0; after six steps
locals19/165 and unchanged source aggregates; final full source values use the
independent finite policy answer table, with explicit scratch19.

Native answers also check nonzero observer, unrelated165, scope/actions,
exact pending suffix/return/caller/continuation and shared state. Complete
order-independent finite map comparisons cover every Index field, every
indexed and active/captured BlockScope field (including nested action parameter
maps), installed Index/entry arrays/defaults, all extern-state variants,
visits, packet data/value/cursor and emitter. Corruption controls change each
Index and scope component individually, including indexed scope contents,
and clear/change installed entries, defaults, installed Index, externs, visits,
packet and emitter. Both runtimes have a nonempty installed-entry array plus
default sentinel; they are unconsulted arbitrary shared state, not a claim of
globally valid table installation. These are finite observations; the universal
theorem supplies exact preservation for arbitrary whole Runs. Advancing
the faulting suffix writes scratch200 then faults. Executing the empty suffix
and pending return reaches the designated missing-block continuation fault.
These negative controls are tests of observable pending work, not a new
copyback theorem.

The default `guardedCallPrefix` exporter records actual stepped snapshots,
complete selected program and args. Python compares the full selected body
to the real tracked guarded wrapper via its independent body identity helper.
It rejects missing/duplicate profiles, Boolean-as-int/bit-as-Bool confusion,
corrupted observer or suffix, and missing captured caller. Snapshot expectation
values are separate Python constants/table entries, never Lean denotation.

The Python test runs actual `call_block`, `run_block`, `execute` and nested
conditionals/assignments. Only `execute_one` is intercepted at the first unique
observer statement. The callback freezes/checks the entire callee value map,
original caller values/scope/action layers, detached complete Index/scopes and
installed-entry Index, and immutable packet/emitter/entries/extern/visit
contents. It has exactly one hit. Assertions happen **inside the callback**,
before raising a test sentinel; Python's `finally: copy_back` subsequently
executes. No post-exception caller is mistaken for the prefix state, and no
copyback implementation is replaced. A retained negative executes the first
observer before taking the snapshot; its changed observer is rejected.

Independent review found a genuine observer survivor: changing cursor int3
to float3.0 during actual delegated `Env.enter_block` passed Python's ordinary
tuple equality. The shared-state check now recursively requires identical
types for every immutable tuple/scalar component, including bytes. Retained
delegating controls cover cursor3→3.0, visit1→True and bytes→bytearray; each
first demonstrates that the old comparison still agrees, then the real
prefix observer rejects it with exactly one entry-hook hit. Clearing the
nonempty installed-entry array is a fourth retained corruption control.
The local helpers do not change the shared legacy test helper or production
runtime. The 64 profile snapshots still strictly distinguish JSON Booleans
from integers; malformed snapshot controls remain in place.

## Gates and adversarial evidence

Candidate both-package/default-audit/native gates pass, including all 192
prefix profiles and projection controls. Two rfl audit roots are axiom-free;
local typing, universal source prefix and concrete application have exactly
`[propext, Classical.choice, Quot.sound]`. Focused Python: 78 passed. Scoped
Ruff format/lint and pyright pass. Required differential gate after observer
hardening: 673 passed, 1,475 deselected, no skips. Final independent review by
`architecture_review` is CLEAR; see
[reviews/guarded-call-prefix.md](reviews/guarded-call-prefix.md).

Experiments run only in a separate worktree. Build rejection is distinguished
from runtime detection:

1. Remove `.statements suffix ::` from the public endpoint in `source_prefix`.
   The core build exits1 at its final trace: the actual suffix-bearing machine
   does not have the claimed bare-return work list. This is **proof rejection**,
   not a Python/Lean runtime divergence.
2. Change the independent test boundary count for invalid Ethernet from11 to13.
   Default package/audit build and native test executable build both exit0;
   every public theorem remains intact. Rebuilt native tests exit1 on changed
   `hdr` at the empty-suffix return boundary; the selected Python test exits1
   on exported count13 versus independently expected11. This is a compiled
   fixture-observation fault, not an IR interpreter fault or a theorem failure.
3. In actual Python `stmt.assign`, evaluate normally, then change only
   RewriteBody's plain scratch assignment value bits8(19) to bits8(20) before
   the real write. The direct prefix test rejects the incorrect local at the
   pre-observer hook. The existing guarded packet test saves a complete genuine
   mismatch **before** its known-answer assertion: only output byte40 changes
   from19 to20. The returned packet otherwise agrees, with no errors,
   diagnostics or extern outputs. Live replay exits1 (one divergence); source
   restoration yields exit0 (one agreement).

The permanent local-fault regression delegates the actual writer, checks
exactly one fault hit for the prefix, initial packet comparison and live
replay, checks the full program/input identity, exact independent two packet
answers and clean outcomes, then restores and replays agreement. The direct
prefix and whole-packet wrapper use different initial observer/source values;
the packet replay demonstrates the same local assignment fault, not the
internal queue boundary itself.

### Reproduce the production fault and complete replay

In an isolated worktree, add `Bits` to `stmt.py`'s values imports and replace
only the body of `assign` after its docstring with:

```python
value = evaluate(a.value, env)
if env.block.name == "RewriteBody" and a.target == pb.LValue(var="scratch") and value == Bits(8, 19):
    value = Bits(8, 20)
write_lvalue(a.target, value, env)
```

With both Lean packages already built, run from that worktree (no concurrent
binary rebuild):

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_lean_guarded_call_prefix.py -k 'on_guarded_call_prefix and guard-false-false-true-2 and False' -q -x
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_lean_edsl_guarded_forwarding.py -k 'on_guarded_forwarding and guard-false-false-true-2' -q -x
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/lean-guard-false-false-true-2.json
# Restore only the intentional assign/import edit, then repeat the replay.
```

The saved ignored bundle is `.artifacts/drt/lean-guard-false-false-true-2.json`,
50,175 bytes, SHA256
`3ef594c90fab7df89131d2983c3bab3cfe8004dbc22dfdf0c3017182376d6fe3`.
Its exact tracked fixture is `guard-false-false-true-2` from `guardedForward`:
one empty-entry request, ingress0, packet `deadbeef`, four ports, seed0. Its
input-only hash matches the earlier guard-fault bundle because the complete
input program/request is identical; this is a distinct local-write fault
campaign, not a new input. The permanent focused regression above reconstructs
and asserts that complete identity without depending on ignored artifacts.

### Restoration and exact evidence

The candidate is never mutated. The isolated tree is restored byte-for-byte
for the theorem, native tests, Python test and production `stmt.py`; its
default build and native tests pass. The production file has no diff.
Final candidate/restored exporter outputs are identical, 866,173 bytes,
SHA256 `eb3f2ef539102c316ec8b3c63903d998d06c0fb7e26c45bff008b81140229327`.
Old `callEntry` and `callBodyEntry` outputs independently match their previous
captures: 11,649 bytes / `b81ffabafa5375d95be65a7a0b56d85485eac9e014b24a2ff47784caf50f87b2`
and 97,269 bytes / `da016fb8436517a04b1c55eca15ace874124c83589ab9d89a85a3daeaa5c1318`.

Final source SHA256s (also checked equal across candidate/restored tree):

| File | SHA256 |
| --- | --- |
| `lean/P4blo/GuardedCallPrefix.lean` | `368f169e0f1f5a60c6184df46883f5dd9fa6b401d295eed47bdaee59193419c9` |
| `lean/P4blo/GuardedCallPrefixTests.lean` | `19b2b814590ccadec3889e20935e3c46c9871edf031db7eb9d7acb78327f6455` |
| `tests/test_lean_guarded_call_prefix.py` | `6d6f26e5437fe3ef2bc34ecd68d783a670824e3d75c8f55e4e4ffffcfd4513f8` |
| `python/p4blo/interp/stmt.py` (unchanged) | `4aeb566ca2281d10935c60883a7acad7dd80385c29258c8e9d02e5fd1226a014` |

Logs for this session are `/tmp/p4blo-guarded-call-` followed by
`final-lean.log`, `final-focused.log`, `final-drt.log`, `final-static.log`,
`missing-suffix-kill.log`, `late-boundary-build.log`,
`late-boundary-native-build.log`, `late-boundary-native-kill.log`,
`late-boundary-python-kill.log`, `python-local-prefix-kill.log`,
`python-local-packet-kill.log`, `python-local-live-replay.log`,
`python-local-restored-replay.log`, `mutant-restored-build.log`,
`mutant-restored-native.log` and `mutant-restored-focused.log`.
The commands, faults, outcomes, input identity and hashes above are the durable
reconstruction record; temporary logs and ignored bundles are not prerequisites
for resuming the work.

The reviewer independently reran all 78 focused tests, 192 native cases,
five audits, original cursor survivor, map-order controls, source-matched
bundle replay and restoration comparisons before final CLEAR. No production
runtime or pre-existing proof modules were changed in the candidate. No Docker images are built.
Full merged Python/schema/oracle gates remain root-owned.
