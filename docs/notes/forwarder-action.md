# The actual forwarder selected-action boundary

2026-09-23. Follows `forwarder-action-next.md` and the separately reviewed
`field-action-writes.md` prerequisite. The actual corpus Program, runtime,
golden, action parameters and four-statement body remain unchanged.

## Contract and proof

`P4blo.ForwarderAction` proves the selected `ipv4_forward` **table-action**
path: literal data enter through `Execution.Work.tableAction` and the public
`runActionCall`. This is not the direct `callAction` expression/copyback path.
The outer frame is action-free, has the actual built `MyIngress` scope and
matches the independent source store; the index is the actual built
forwarder index. All other Run state and unrelated block bindings are
arbitrary. No `BlockFrame` premise is applied inside the action.

`Snapshot` names all twenty stored scalars/validity bits. Constructor-only
`restore` and `observe` are inverse and never invoke the IR evaluator or
authored field accessors. The independent policy performs precisely:

- egress receives the literal port;
- Ethernet source receives the **old** destination;
- Ethernet destination receives the literal new destination;
- TTL becomes `(oldTTL + 255) % 256`.

Every other field, both validity bits, checksum, ingress and prior drop are
preserved. The real body still uses IR subtraction by one, with no validity
or TTL guard; a dedicated arithmetic correspondence establishes wraparound.
An asymmetric raw constructor anchor pins what the source observations mean,
beyond inverse laws that alone would permit paired field permutations.

`entry` proves actual lookup, arity, literal binding and layer installation.
`before_return` gives ten explicitly composed real transitions, stopping
with `actionReturn outer none` pending. `source_steps` adds its normal return,
leaves arbitrary continuation `K` untouched, and restores only the original
action layers while retaining the updated block map. `Steps` is unindexed:
10/11 is the explicit derivation plus independent native boundary evidence,
not a numeric proposition in that relation's conclusion. `run_correct`
derives actual public completion through `Finishes.sound` at `K=[]`.

The exact result retains four ordered HashMap inserts obtained from
independent intermediate records, not an assumed equality between differently
built maps. `result_matches` establishes the entire final policy store;
`changes_only_vars` and `preserves_outside` preserve the rest of the Run and
all names except hdr/meta. `populated_correct` supplies a constructive actual
`Frame.forBlock` witness, using the existing successful initialization and
deriving its actual scope identity. The real control has no checksum local.

The two inverse laws use no axioms. The other nine registered roots use only
`propext`, `Classical.choice`, `Quot.sound`. No sorry, unchecked native proof,
alternate executor or semantic callback premise is introduced. The core
compiles at the default heartbeat limit; only recursion depth is increased
for the nested dependent source records.

## Independent execution observations

Forty-eight profiles cover all validity pairs, both prior-drop values,
TTL 0/1/255 and two asymmetric literal MAC/port choices. The native test
checks complete modeled values against raw independently constructed answers,
complete shared Run projections and all frame maps. Its 144 trace profiles
use empty, mutating and faulting continuations; step ten must retain the
actual original outer frame in `actionReturn`, step eleven leaves exactly
the chosen continuation, and step twelve demonstrates the write/fault is
non-inert. Wrong arity fails before action storage is installed.

The dedicated exporter retains full before/entered/pending/returned Run
projections, including complete index/scope/installed-entry maps and nonempty
shared-state sentinels. Its extern profile contains a register; it does not
pretend that the reused JSON helper encodes other extern variants. Native
shared-state comparison remains constructor-sensitive. The actual Program
and exact complete action are compared to the Python builder and frozen
golden, and a literal four-statement/parameter anchor independently fixes
the selected body. No parser or packet setup is replaced by this fixture.

Python validates all exported profiles once in a module-scoped fixture, then
runs actual `stmt.run_action_call` normally for each. Its hook delegates the
real body, never throws a boundary sentinel, and freezes every field of the
full actual Env at active entry, active completion and normal return. The
freeze is detached and type-sensitive (including bool/int/float distinctions).
The complete JSON wire projection is separately compared to Lean. LPM entry
keys explicitly retain snake-case proto spelling; this is serialization
alignment, not a relaxation of value checking.

Block-map `dstAddr=99` and `port=77` are operational decoys, not a claim of
validator-accepted declarations. Actual reads must prefer literal action
parameters. After observation, real parameter writes exercise the action-hit
branch and must leave those block decoys unchanged. These extra probes compare
the strict **entire inner state after each write**, with both expectations
frozen before execution. Independent review found that the first version's
ordinary Bits equality accepted a Boolean payload and that the second write
could repair a corrupted sibling parameter. Both actual single-hit faults
are now retained regressions. This strengthened an auxiliary leaf observer;
it was not a defect in the normal action proof or production interpreter.
Shared block storage is
intentional here: unlike block copy-in/out, an action's updates persist in
the outer activation. Scope/index/packet/emitter/extern/entries/visits cannot
change. The old forwarder exporter remains byte-identical.

## Confidence and exclusions

High confidence in this fixed action's source policy and actual normal-call
boundary; medium confidence that direct four-statement proof composition is
the best long-term reusable interface. Revisit when a second action needs
parameter writes, direct-call out/inout copyback or action-aware source typing.
No route-selection, parser, checksum, architecture fate, fault unwinding,
nested-action legality, whole-program validation or complete forwarding proof
is claimed. The next useful composition boundary is selected table execution
and checksum/control continuation, not a claim that this action alone routes
a packet correctly.

## Gates and adversarial evidence

The implementation candidate is frozen and all isolated source edits are
restored. From `/Users/qobilidop/my/work/p4blo-forwarder-action`:

```sh
nix develop -c /Users/qobilidop/my/work/p4blo-forwarder-action/scripts/check-lean.sh
nix develop -c uv run pytest tests/test_lean_forwarder_action.py -q
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q
nix develop -c /Users/qobilidop/my/work/p4blo-forwarder-action/scripts/check.sh
nix develop -c uv run ruff check tests/test_lean_forwarder_action.py
nix develop -c uv run ruff format --check tests/test_lean_forwarder_action.py
nix develop -c uv run pyright tests/test_lean_forwarder_action.py
```

Both Lean packages/default audits/full native suites pass, including all
48 action outcomes and 144 continuation boundaries. The final focused suite
passes 76 checks. The full Python/schema/static gate passes with **2507 passed,
5 expected failures, 1 skip**, exit 0. The skip is the unavailable optional
XDP compile image, independently rechecked with `tests/test_xdp_build.py -rs`
(16 passed, 1 skip); no image was built. The final required conformance run
passes **917 tests, 1596 deselected, no skip**, exit 0. The earlier 917/1594
run preceded the two auxiliary write-probe negatives. The only later
Lean registration adjustment imports the core directly into its audit module
to permit the intended core/test commit split; the final both-package gate
has already passed that adjustment. No executable source changed after the
full Python gate began.

Logs are `/tmp/p4blo-forwarder-action-{full,focused,final-lean,final-required,
final-ruff,final-format,final-pyright,skip}.log`. Independent review already
checked the core, all eleven exact axiom roots, native suite and final 76
Python checks. Final review is **CLEAR**: the reviewer additionally checked
all campaign logs, seven restored source pairs, exact bundle/source identity,
restored replay and both exporter identities. The two observer survivors
were fixed and retained before clearance. See
`docs/notes/reviews/forwarder-action.md` (integrator-owned report).

The isolated campaign worktree is
`/Users/qobilidop/my/work/p4blo-forwarder-action-mutants`, created at the
committed helper `0da36db`, with mechanical copies of the candidate additions
and fresh package caches. No candidate source or executable is mutated.

For each of the following source edits, run from its `lean/` package:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.ForwarderAction
```

Each modified runtime module compiles, then the new correspondence proof
fails with exit 1. These are **compiling semantic edits rejected by proofs**,
not runtime differential kills or new saved packet inputs:

| Exact isolated edit | Rejected obligation | Log in `/tmp/` |
| --- | --- | --- |
| `Exec.dispatch.actionReturn`: replace `setFrame { inner with action := outer.action, actionVars := outer.actionVars }` with `setFrame outer` | Original frame cannot equal the frame with the four retained block inserts | `p4blo-action-full-restore-proof-kill.log` |
| Same branch: use `setFrame inner`, rename now-unused pattern `outer` to `_outer` | Installed action name/map cannot equal arbitrary original layers | `p4blo-action-missing-restore-proof-kill.log` |
| `Exec.dispatch.tableAction`: `action.params.zip call.args` → `action.params.zip call.args.reverse` | Swapped literal bindings cannot equal the declared parameter map | `p4blo-action-binding-proof-kill.log` |
| `Forwarder.forwardAction`: swap its second/third assignments | Complete body anchor and actual per-statement trace no longer match | `p4blo-action-order-proof-kill.log` |
| `Eval.bitsBinary.sub`: replace `x.value + 2 ^ n - y.value` with `x.value - y.value` | Saturating predecessor cannot equal modular add255 at TTL0 | `p4blo-action-saturation-proof-kill.log` |

The missing-return first attempt stopped at the unused-variable linter; it
was rerun with `_outer` to reach the genuine false layer equality. That
initial warning is not counted as a semantic kill. The saturation proof also
reports an unused arithmetic simplifier after the actual false arithmetic
goal; only the latter is the semantic evidence. Each edit is restored before
the next one.

### Compiled fixture intent fault

Change only `ForwarderActionTests.Case.dst`'s low branch from
`0x020202020202` to `0x030303030303`. Both package gates, default audits and
all native tests still pass (`p4blo-action-profile-build.log`): the action
theorem correctly holds for either literal input, while the native expected
output follows that input definition. The independently literal Python
profile contract rejects the changed call:

```sh
nix develop -c uv run pytest 'tests/test_lean_forwarder_action.py::test_lean_agrees_forwarder_action[false-false-false-0-false]' -q
```

Exit 1 at `literal bindings`, recorded in
`/tmp/p4blo-action-profile-known-answer-kill.log`. This is a compiled
**fixture-intent fault**, not an incorrect action theorem or Lean/Python
semantic divergence. Paired MAC input/output permutations, duplicate/missing
cases, count/type corruption and damaged complete map projections are also
retained independent-export rejection tests.

### Actual Python destination-write fault and complete replay

Restore every Lean edit and run both package gates before this campaign.
In the isolated `python/p4blo/interp/expr.py`, insert immediately before
`write_lvalue`'s `match lv.WhichOneof("kind")`:

```python
if env.action == "ipv4_forward" and lv == pb.LValue(
    member=pb.LMember(
        base=pb.LValue(member=pb.LMember(base=pb.LValue(var="hdr"), field="ethernet")),
        field="dstAddr",
    )
):
    return
```

`python -m py_compile` succeeds. The real action runs normally, but its
destination assignment silently disappears. The focused positive node
`test_lean_agrees_forwarder_action[true-true-false-0-false]` fails at strict
`active completed state`, not at compilation, setup, exception or a fake
callback. Logs: `/tmp/p4blo-action-python-compile.log` and
`/tmp/p4blo-action-python-internal-kill.log`.

The following exact reconstruction uses tracked corpus/test helpers. Execute
in the isolated worktree while that one source edit is live:

```sh
nix develop -c uv run python - <<'PY'
from pathlib import Path
from p4blo import ir
from p4blo.drt.run import compare_program
from p4blo.drt.replay import save, load, replay
from tests.test_lean_forwarder import edge_case
root = Path('/Users/qobilidop/my/work/p4blo-forwarder-action-mutants')
binary = root / 'ir/.lake/build/bin/p4blo-lean'
program = ir.load_text(root / 'tests/corpus/forwarder/forwarder.txtpb')
case, expected = edge_case(0)
bundle = root / '.artifacts/drt/forwarder-action-destination.json'
bundle.parent.mkdir(parents=True, exist_ok=True)
report = compare_program(program, [case], 4, [binary])
save(report, bundle)
assert load(bundle) == (program, [case], 4, 0)
assert report.agreed == 0 and len(report.divergences) == 1
assert report.protocol_error is None and report.both_errored == 0
live = replay(bundle, [binary])
assert live.agreed == 0 and len(live.divergences) == 1
fault = live.divergences[0]
assert fault.lean.outputs == tuple(expected)
wrong = bytes.fromhex('000000000101') + expected[0][1][6:]
assert fault.python.outputs == ((2, wrong),)
assert fault.python.error is None and fault.lean.error is None
assert fault.python.diagnostic is None and fault.lean.diagnostic is None
print('Saved and live-replayed exact destination-write mismatch')
PY
nix develop -c uv run python -m p4blo.drt.replay /Users/qobilidop/my/work/p4blo-forwarder-action-mutants/.artifacts/drt/forwarder-action-destination.json --lean /Users/qobilidop/my/work/p4blo-forwarder-action-mutants/ir/.lake/build/bin/p4blo-lean
```

The script exits 0 after verifying the expected divergence; the standalone
live replay exits 1 with one divergence and no joint errors. Both engines
emit port 2, preserve payload and agree on wrapping TTL/checksum. Only the
Ethernet destination remains `000000000101` in Python instead of Lean's
`000000000202`. Restore the inserted branch and repeat the standalone replay:
exit 0, one agreement, no divergence/error. The permanent regression applies
the same scoped fault to the actual `stmt.write_lvalue` call site, saves
before asserting answers, replays live/restored and checks the strong action
observer as well.

Bundle copies in both worktrees:
`.artifacts/drt/forwarder-action-destination.json`, 27,697 bytes,
SHA-256 `27376cf7dfe17455b40b849323b35186b471c0b432b01495aa7bd3d9dc0b9c4b`.
This is the **same retained input** as the earlier forwarder TTL0 campaign,
with a new field-write fault and different live mismatch, not an additional
distinct packet witness. It contains the complete real Program, installed
route, packet, ingress, four-port count and seed 0; it does not serialize the
internal action observer's Env. Internal checks are reproduced from this
suite's tracked environment constructor separately.

Logs in `/tmp/`: `p4blo-action-python-save.log`,
`p4blo-action-python-live-replay.log`, `p4blo-action-python-restored-replay.log`,
`p4blo-action-restored-lean.log`, `p4blo-action-restored-focused.log`.
The restored isolated focused suite passes all 76 tests. Runtime files,
Program source and profile source are byte-identical to the candidate again.
The restored action exporter equals the original candidate capture exactly:
8,803,741 bytes, SHA-256
`1b210355f9f2d66b9b764003166e660e7c02be10dd452250fd7c5dfc19ea109e`.
The old forwarder Program exporter remains 6,085 bytes, SHA-256
`c1f7c1c16d10c1c11f536cb0a5ff54a42fd11d6a2c30c8a4ac06633d6adc4669`.
