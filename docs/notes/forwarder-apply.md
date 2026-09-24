# Actual bounded forwarder table application

2026-09-23. Checkpoint 2 of [the selected-table plan](forwarder-table-next.md),
built on committed `b3635a0`. The unchanged real Forwarder program, golden,
runtime, table-selection theorem and selected-action theorem are dependencies,
not replacement semantics. Checkpoint 3 (the real ingress prefix, retaining
its pending checksum conditional) remains next.

## Exact contract and its boundaries

`ForwarderApply.run_correct` proves actual
`applyTable "ipv4_lpm" none` for every fitting source store and every member
of `ForwarderTables.Config`: five route installation shapes, three defaults,
arbitrary fitting route MAC/port data and every 32-bit destination address.
Its premises separately require the real runtime index, actual ingress
scope, an action-free outer frame, full source-frame value agreement, and
the actual successfully built installed configuration. The latter's index
identity follows the installation theorem; no lookup-correctness callback
or fabricated manually populated installed map substitutes for that theorem.

`key_evaluate` proves the actual authored destination read with the whole
Run unchanged. `dispatch_table` composes it with the real installed lookup.
The independent source `Effect.policy` is the complete existing forward
Snapshot policy, drop-only, or identity. Forwarding reuses the real selected
action theorem; the new drop and NoAction laws execute actual table-action
entry, body and normal return. Drop changes only metadata.drop. Explicit
NoAction still enters and returns from its real empty action; it is not an
absent optional action. An absent host override keeps the program's drop.

`before_hit` stops before the actual hit write for any target and arbitrary
continuation K. It does not promise a valid arbitrary target. `source_steps`
specializes the original absent target, consumes its administrative step and
stops at exact K. `run_correct` then uses actual `Finishes.sound` to establish
normal public execution. The exact Run result retains actual ordered map
inserts, all non-variable state and action-layer restoration. `result_matches`
connects it to the independent complete source policy; `changes_only_vars`
and `preserves_outside` retain the other Run fields and block names outside
hdr/meta. `populated_correct` supplies real initialization/scope/index witnesses.

The explicit derivations have 13/7/5 transitions for forward/drop/NoAction,
confirmed by independent native counts. `Execution.Steps` itself is unindexed:
these are not theorem conclusions carrying a numeric step counter. In
particular, one transition short retains writeHit even with no target.

No ingress-validity guard executes in this theorem. Applying the table to an
invalid header uses its stored destination just as the runtime does. There
is no checksum, parser, full ingress/pipeline, arbitrary-list/prefix LPM,
global validity, general hit-target or universal Python equivalence claim.
Active action frames are handled by the real action laws, not mislabeled
as BlockFrame. Extra native/Python decoy variables are operational sentinels,
not a claim of accepted source declarations.

Confidence is high in these semantic boundaries and concrete composition;
medium in keeping the small Effect wrapper as the long-term API. Revisit
when the ingress-prefix composition or another real routing family needs
a common interface; do not generalize by assuming lookup correctness.
No new AST, operator, evaluator, fuel or runtime behavior was introduced.
All proofs compile with default Lean heartbeat and recursion limits.

## Independent observation

`ForwarderApplyTests` runs all 30 configuration profiles against nine literal
address boundaries. Those 270 cases cycle every one of 24 asymmetric stored
state profiles (both header validities, old drop and TTL0/1/255); this is
**not** the 6480-case Cartesian product. The theorem, separately, quantifies
arbitrary complete stores. Native initial states use actual Index.build,
Frame.forBlock and Installed.build. Independent raw records specify every
header/meta field and expected parameter map, rather than calling the source
policy or authored paths. Full before/entered/active-end/returned states
retain complete index/scopes/installed maps, packet/cursor, emitter, externs,
visits and unrelated block values.

Three continuations per case yield 810 exact native boundary checks. The
pending actionReturn and writeHit stages are distinguished. Subsequent real
modifying/faulting continuations confirm that stopping at K is meaningful.
Twenty-four controls use a different hit target, metadata.drop: default drop
first sets true and then its false miss result overwrites it. Optional
action-none and wrong-arity maps are separate, explicitly installer-rejected
operational controls; errors skip the hit write.

The Python fixture validates exported case inventory and complete state once
per module, then executes real `stmt.apply` normally. Delegating hooks check
exactly one actual key evaluation, lookup, selected action and body execution,
with every expected stage frozen independently before execution. The complete
type-sensitive snapshots prevent int/bool/float aliases and later repairs
from concealing changes. Permanent process-local faults challenge wrong or
duplicate key reads, sibling/cursor read effects, installed-map mutation,
skipped default, leaked action layers and complete outer-variable restoration.
Weak return-only controls explicitly survive the two read-side effects;
the full observer rejects them. Malformed exported inventory, hit types,
counts, chosen calls, complete maps/state and coordinated address changes
are rejected independently.

Five whole-packet anchors cover overlapping routes in both orders and the
three default choices. Expected bytes preserve old destination-to-source,
TTL0 wrapping, untouched payload and checksum-after-table behavior. These
are executable packet evidence, not a newly proved checksum/pipeline result.
DRT mismatch reports, including ProtocolError reports, are saved before
independent expected-output assertions. A retained skip-drop regression
checks the full internal observer and complete input save/live/restored replay.
The immutable existing BMv2 image also executes all five packet profiles;
its printer compilation happens inside the existing image, not an image build.

## Adversarial source campaign

The separate `p4blo-forwarder-apply-mutants` worktree starts at `b3635a0`
with only this candidate's files/registrations copied, and fresh Lean caches.
The implementation worktree remains unmutated. Four campaigns were run:

1. In actual `ir/P4bloIR/Exec.lean` table dispatch, remove the appended
   `[.writeHit hit m.hit]`, changing the now-unused pattern binder to `_hit`.
   The runtime module builds successfully; `ForwarderApply.dispatch_table`
   then has a genuine unsolved queue equality (reduced to False). Logs:
   `/tmp/p4blo-forwarder-apply-skip-hit-runtime.log` (exit0),
   `...-skip-hit-proof.log` (exit1). A preliminary unused-binder warning was
   fixed before this counted runtime build; it is not a semantic kill.
2. Restore the queue and replace the actual key evaluator by
   `evaluate (.member (.member (.var "hdr") "ipv4") "srcAddr")`, using `_k`
   for the ignored key binder. The runtime builds0; the actual application
   dispatch theorem fails at its semantic goal. Additional unused-simp
   diagnostics are not counted as the kill. Logs use `key-runtime` (0) and
   `key-proof` (1). These two are proof-rejected **compiling runtime edits**,
   not packet mismatches or new retained request inputs.
3. Restore runtime and replace `ipDst :=` by `ipSrc :=` only in native
   `ForwarderApplyTests.source`. All core proofs/default audits and exporter
   build0: the general proof remains true for a different store. The Python
   independent complete-before record rejects
   `empty/drop/false/0/0`. Logs `fixture-build` (0), `fixture-kill` (1).
   This is a compiled wrong-intent fixture/answer kill, not a false proof
   rejection or a production-runtime divergence.
4. In actual Python `stmt.apply`, require `match.hit` as well as a nonempty
   chosen action before calling `run_action_call`. The source compiles. The
   internal positive test sees zero real action/body calls instead of one;
   the packet positive test saves a clean mismatch before asserting. Both
   fail1 (`default-internal-kill`, `default-packet-kill`). The source-edited
   runtime emits the unchanged TTL0/MAC packet at port0, whereas Lean drops.
   There are no error/diagnostic outcomes and extern-state observations agree.
   The same saved input diverges live and agrees after exact source restore
   (`default-live-replay`, `default-restored-replay`, both checker exit0).

Each abbreviated log above is under `/tmp/p4blo-forwarder-apply-` with
suffix `.log`. The three intentionally changed source files are restored
byte-for-byte. Five candidate/clone comparisons also include the unmodified
core and complete final Python test helper: `ir/P4bloIR/Exec.lean`,
`python/p4blo/interp/stmt.py`, `lean/P4blo/ForwarderApply.lean`,
`lean/P4blo/ForwarderApplyTests.lean`, `tests/test_lean_forwarder_apply.py`.
Runtime/Program diffs are empty. The restored isolated package gate passes.

The actual packet bundle is
`.artifacts/drt/forwarder-apply-empty-drop-false.json`, retained in both
implementation and isolated worktrees: 26918 bytes, SHA-256
`39b7ebeeb12760cd89e0b408117d7bf9ba1eb8f8589c7fe3d9baf001a70bcc81`.
It contains the unchanged complete corpus Forwarder, exact no-route host
configuration, ingress0, TTL0 packet, four ports and seed0. Recursive
deduplication against all 19 then-retained main bundles (26 requests) found
no equal bundle or exact request. Packet bytes alone are reused from
`forwarder-tables-lpm.json` and `lean-forwarder-ttl-0.json`; the host
configuration differs. This is not a newly invented packet vector.

### Reproduce the actual default-skip mismatch

Use an isolated worktree containing this checkpoint, build both Lean packages
first, and make the single Python source edit in item4. From its root:

```sh
nix develop -c uv run python -m compileall -q python/p4blo/interp/stmt.py
nix develop -c uv run pytest 'tests/test_lean_forwarder_apply.py::test_lean_agrees_forwarder_apply[empty/drop/false/0/0]' -q
nix develop -c uv run pytest 'tests/test_lean_forwarder_apply.py::test_lean_agrees_apply_packets[empty/drop/false]' -q
```

Both pytest commands must exit1; the second saves the complete bundle before
its failing assertion. Check exact reconstruction and replay while live:

```python
from pathlib import Path
from p4blo import ir
from p4blo.drt import replay
from tests.test_lean_forwarder_apply import application_packet, application_output

root = Path.cwd()
bundle = root / ".artifacts/drt/forwarder-apply-empty-drop-false.json"
program, cases, ports, seed = replay.load(bundle)
assert program == ir.load_text(root / "tests/corpus/forwarder/forwarder.txtpb")
assert cases == [application_packet("empty/drop/false")]
assert (ports, seed) == (4, 0)
report = replay.replay(bundle, [root / "ir/.lake/build/bin/p4blo-lean"])
assert report.protocol_error is None and report.both_errored == 0
assert report.agreed == 0 and len(report.divergences) == 1
mismatch = report.divergences[0]
assert mismatch.lean.outputs == ()
assert mismatch.python.outputs == tuple(application_output("empty/noop/false"))
assert mismatch.lean.state == mismatch.python.state
for outcome in [mismatch.lean, mismatch.python]:
    assert outcome.error is None and outcome.diagnostic is None
```

After restoring the one Python source line, replay this exact bundle and
require `report.passed`, `report.agreed == 1`, and `both_errored == 0`.
The candidate copy also replays with one clean agreement. The earlier
process-local skip-drop regression remains permanently in the normal suite;
it independently checks internal state, saving, live mismatch and restoration.

## Gates and review

Both Lean packages/default audits/native tests pass. Twelve new theorem
roots each audit exactly `[propext, Classical.choice, Quot.sound]`.
All following commands exited0 against the final code/test revision, with
Lean executables built before any consuming tests. No Docker image was built
or replaced. Logs have prefix `/tmp/p4blo-forwarder-apply-`:

- `nix develop -c scripts/check-lean.sh`: both packages, default audits and
  native suites (`lean.log`).
- `nix develop -c uv run pytest tests/test_lean_forwarder_apply.py -q`:
  320 passed, including the five-vector immutable BMv2 profile (`focused.log`).
- `nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees -q`:
  2124 passed/1782 deselected (`required.log`), no skipped Lean obligation.
- `nix develop -c scripts/check.sh`: all checks passed; 3900 passed,
  5 expected xfails and the existing unavailable local compile-only XDP image
  skip (`full.log`). This includes format/lint/type/schema/generated-code and
  workflow checks, all available immutable oracle profiles, and final tests.
- Isolated restored `scripts/check-lean.sh`: both packages/default audits/native
  suites pass (`restored-build.log`). Its rebuilt exporter is byte-identical
  to the candidate; its full focused suite also passes all 320 tests
  (`restored-focused.log`), including the existing-image BMv2 profile.

Independent read-only review is **CLEAR** in
[the review report](reviews/forwarder-apply.md). The reviewer independently
passed 319 focused tests (BMv2 excluded, owner-attributed above), native
270/810/24 checks and twelve fresh exact-axiom queries; compared all five
restored source pairs and complete exporter bytes; source-matched the exact
saved Program/request/ports/seed and reproduced one clean restored agreement;
and inspected the separately classified campaign logs. Parent integration
remains responsible for combined gates on final merged interfaces.

The unchanged previous table exporter is byte-identical to its committed
checkpoint capture: 82350 bytes, SHA-256
`cd34627a55f885e67ff76272fec924446837eaae2e26cdc018d2ece7237ebc42`.
The new complete-state application exporter is 49719204 bytes, SHA-256
`aab4a8f59ec967c1f499a5f2b85c496370acc656c64f5ed00254f28075daeb97`;
capture `/tmp/p4blo-forwarder-apply-final-export.json`.
