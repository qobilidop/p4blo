# Actual firewall Bloom insertion

2026-09-23. Implements the first checkpoint in
[the reviewed plan](firewall-bloom-next.md), based on `5519ada`.
This proves actual two-statement insertion, not hash computation, readback,
classification, SYN gating or a complete firewall pipeline.

## Contract and trust boundary

`P4blo.TutorialFirewall.Bloom.insertion` runs the real `execute insertBloom`.
Its premises identify the actual built firewall index, the action-first reads
of both 32-bit positions and the two bound one-bit registers. The proof resolves
actual instance/type/method declarations and argument evaluation, dispatches
both actual statements, and connects their finite trace through `Finishes.sound`.
There is no assumed evaluator/extern callback or alternative interpreter.

The result is the exact Run with two ordered extern-map insertions. Every
other Run field, the entire frame/action layer and all unrelated extern keys
are preserved. Cell answers are characterized independently by index equality
and bounds. Array sizes and existing one-valued membership are preserved;
the selected cell becomes one when in bounds. Out-of-bounds writes remain
no-ops on cells. Equal numerical positions still address distinct arrays.
The explicit 4096-cell corollary requires in-range positions; bit<32> alone
does not imply that bound. No startup-validity premise is silently added.

`first_step` leaves arbitrary subsequent work pending, with the first register
updated and the second unchanged. A separate initialized witness discharges
the read/state premises using the actual initialized frame and caller-supplied
arrays. Its arrays need not be valid freshly loaded 4096-cell state. This
constructive witness was added after the first campaign to make nonvacuity
explicit; no execution contract or implementation changed.

Thirteen default-audited roots cover the actual calls/body/first step/full
execution, exact extern/preserved-field observations, five cell/profile laws
and the initialized witness. Cell/profile roots use only `propext`; operational
roots use exactly the standard `propext`, `Classical.choice`, `Quot.sound`.
The preservation proof itself is reflexive, but its result type includes the
HashMap operation and therefore reports those same standard three axioms.
No custom axiom, sorry, native proof escape or runtime change is introduced.
The recursion bound is the existing module-local 8192; heartbeat stays default.

Confidence: high in this boundary after independent review and actual runtime
fault rejection; medium in helper API longevity. Helpers remain in the user
application namespace. Revisit generic register laws for a demonstrated second
client or the next readback proof, not by widening the current claim.

## Independent observations

Native tests run 84 complete states: six array pairs, seven position pairs and
both block/action-shadowed storage. They compare every cell and complete Run
before/after the first actual statement with a deliberately faulting sentinel
continuation still pending, then after normal execution of both statements.
Expected cells use literal array enumeration, not the production register or
proved update helper. Complete maps/index/scope/entries/extern types, packet,
emitter, visits and action storage use the existing strict native observers.

Fourteen profiles contain noncanonical natural cells and are native-only.
Python's Bits constructor rejects those one-bit values; no invariant bypass
or matching-state claim is made. The other 70 Python profiles cover empty,
singleton, asymmetric and actual 4096-cell arrays, zero/last/beyond-end/max32
positions, equal positions and action shadows with invalid block decoys.
Nonstandard array sizes are explicitly injected lower-level state, not accepted
startup configurations. Each Python test obtains the unchanged Program from
the independently checked Lean exporter and extracts its actual two statements,
checking their complete protobuf syntax against literal expectations.

The Python observer deep-copies and type-tags the entire Env, builds expected
cell results independently, and delegates through the real Register.call.
It compares full state after each call and after normal statement completion,
including exact call names, arguments and order. It never uses an early
sentinel exception as evidence of normal completion. Six permanent side-effect
controls cover another cell, another extern, unused local, action sibling,
integer-to-float cursor change and a transient effect repaired by the second
call. A reversal explicitly passes a final-state-only observer but fails the
intermediate call trace. Total final focused inventory: **79 tests**.

### Review-discovered survivor

The initial observer called production `Env.read` to compute expected positions.
An actual read alias from reg_pos_one to reg_pos_two changed both the expected
answer and execution. Review independently demonstrated a false pass with two
hook hits and first array `[1,0,1,1]` instead of `[1,1,0,1]`.

The final observer accepts intended p/q directly from the independent profile.
A permanent regression applies the same real Env.read alias, requires exactly
one runtime hit, normal completion and the independently wrong array, then
requires the complete trace to reject it. The expected model makes no runtime
variable reads. The reviewer reran all 79 tests, native tests and audits, and
separately showed that a repaired action-sibling effect leaves the correct final
Env while the first-write snapshot still rejects it.

## Isolated source and runtime challenges

Fault tree: `/Users/qobilidop/my/work/p4blo-firewall-bloom-faults`, branch
`work/firewall-bloom-faults`, created from `5519ada` with fresh caches and copies
of the new candidate modules/tests/registrations. Never mutate main/candidate.
Start each campaign with the original source and restore it before the next.

Six actual source variants modify only the complete `def insertBloom` block
in `lean/P4blo/TutorialFirewall.lean`:

1. First write target bloom_filter_1 becomes bloom_filter_2.
2. Second write target bloom_filter_2 becomes bloom_filter_1.
3. Second position regPosTwo becomes regPosOne.
4. First value `(bits 1 1)` becomes `(bits 1 0)`.
5. Omit the second write, retaining the first unchanged.
6. Reverse the two writes, with each complete call otherwise unchanged.

For each variant, `lake build P4blo.TutorialFirewall` exits 0, then the unchanged
`lake build P4blo.TutorialFirewallBloom` exits 1. All six reject the actual
literal body/order equation. The trace/call connection also fails where the
changed syntax is incompatible; position/value mismatch elaboration additionally
reached the default heartbeat. Those secondary timeouts are not separate
semantic kills, and no limits were raised to count them. Reversal is an order
fault, not a claim that the two final logical arrays differ. These are compiling
application-source proof rejections, not Python/Lean runtime divergences.
Logs: `/tmp/p4blo-bloom-source-<label>-{compile,proof}.log`, with labels
first-target, second-target, position, value, omit, reverse.

The actual Lean runtime fault changes the unique register-write line in
`ir/P4bloIR/Externs.lean` from
`cells.set! index.value value.value` to `cells.set! index.value 0`.
The fault edit also indented that let line two extra spaces (accepted by Lean).
Actual `lake build P4bloIR.Externs` exits 0; the unchanged application proof
exits 1 at the false zero-versus-one whole-Run result in `write_call`.
This is a compiling operational-model fault rejected by the proof, not a
runtime differential claim. Logs: `/tmp/p4blo-bloom-runtime-{compile,proof}.log`.

After restoring Lean, the actual Python runtime fault inserts this block after
the normal register write and before its return in
`python/p4blo/externs/register.py`:

```python
if self.width == 1 and len(self.cells) > 2:
    self.cells[2] = Bits(1, 1)
```

The module compiles. Actual two-write execution completes and changes the
unselected first-array cell; the complete insertion observer rejects it.
Full packet DRT on the existing four-request firewall input yields **three
clean state-only mismatches**, with equal packet outputs and no error or
diagnostic. Save happens before replay/output assertions, and live replay
reproduces the mismatches. The bundle is byte-identical to the existing
`.artifacts/drt/firewall-crc32.json`: **76260 bytes**, SHA-256
`c547f2999038dae030dfd93402e7e26a73782f0424384fda9633a5ee7e886103`.
The initial fault-tree copy is `.artifacts/drt/firewall-bloom-other-cell.json`.
That first run saved after its output assertions. The campaign was rerun with
retention before those assertions, producing the byte-identical
`.artifacts/drt/firewall-bloom-other-cell-retained-first.json` and the same
three clean state-only mismatches. It is reused input, not another distinct
retained bundle. Final log: `/tmp/p4blo-bloom-python-live-final.log`.

Ordinary proof development also needed an escaped binder name, explicit
monadic map reduction, and staged HashMap simplification. Combining eq_comm
with automatic getElem rules looped; explicit key cases fixed it without
raising limits. The initial Python literal class spelling was corrected by
Pyright. Restoration hashing caught the leftover two-space indentation after
the runtime value was restored; the exact source was then restored and rebuilt.
None of those setup/development failures counts as a mutant kill.

## Gates and remaining work

Both complete Lean packages/default audits/native suites pass after the final
initialized witness: **567 spec checks**, all prior user checks and the 84
new native boundaries. Log: `/tmp/p4blo-bloom-final-lean.log`. Focused final
Python suite: **79 passed**, `/tmp/p4blo-bloom-focused-final.log`; Ruff format,
Ruff check and Pyright pass without suppression.

Before review's observer repair and the last kernel witness, the broad gate
passed **3608 / 5 strict expected discrepancies / 1 local-XDP skip**, including
all schema/static/workflow checks; required DRT passed **1834**, no skips.
Logs: `/tmp/p4blo-bloom-check.log`, `/tmp/p4blo-bloom-required.log`.
Those loaded the 78-test revision and are **not** final-revision broad evidence.
Final required DRT passes **1835**, no skips, after both the independent-read
regression and initialized witness (`/tmp/p4blo-bloom-final-required.log`).
The restored fault tree also passes both complete Lean gates and all thirteen
audits (`/tmp/p4blo-bloom-restored-lean.log`). Nine final source pairs match
the candidate exactly; complete Python boundary checks with and without
action shadows pass, and the reused four-packet input agrees after restoration
(`/tmp/p4blo-bloom-restored-replay.log`). Independent final campaign review is
clear in `reviews/firewall-bloom.md`: it separately reproduced the operational
Python effect and restored agreement without editing candidate sources.
The final merged full gate remains the integrator's obligation.
No Docker image was rebuilt or security restriction relaxed.

Next: actual readback and drop/no-op composition, then hash bounds/input
reversal and actual control branching. Preserve the double-collision witness;
neither insertion monotonicity nor its tests imply exact connection tracking.

## Reproduction and exact restoration

Use an isolated worktree with the committed candidate modules, fresh build
outputs and no concurrent consumers. The commands below use the original
absolute campaign paths; adapt all three roots together in a fresh checkout.
Run the live recipe only after applying the exact two-line Python mutation
above, and invoke it with that fault tree as the command's working directory.
It intentionally rejects an existing output path rather than overwriting
retained evidence. The clean main Lean binary must already be built.

```sh
nix develop -c uv run python - <<'PY'
from pathlib import Path
import hashlib,py_compile
import pytest
from p4blo import ir
from p4blo.drt import replay
from p4blo.drt.run import compare_program
from p4blo.interp import stmt
from p4blo.interp.values import Bits
from tests.test_lean_firewall_bloom import initial,insertion_body,observe_insertion,register
root=Path('/Users/qobilidop/my/work/p4blo-firewall-bloom-faults')
main=Path('/Users/qobilidop/my/work/p4blo')
py_compile.compile(str(root/'python/p4blo/externs/register.py'),doraise=True)
program,cases,ports,seed=replay.load(main/'.artifacts/drt/firewall-crc32.json')
assert program==ir.load_text(root/'tests/corpus/tutorial_firewall/tutorial_firewall.txtpb')
env=initial(program,3,1,2,True)
stmt.execute(insertion_body(program),env)
assert register(env,'bloom_filter_1').cells==[Bits(1,v) for v in [1,1,1,1]]
assert register(env,'bloom_filter_2').cells==[Bits(1,v) for v in [0,1,1]]
patch=pytest.MonkeyPatch()
try:
 observe_insertion(initial(program,3,1,2,True),insertion_body(program),(1,2),patch)
except AssertionError as e:
 assert str(e)=='Bloom intermediate complete Env or call order changed'
else: raise AssertionError('strong observer survived real register mutation')
finally: patch.undo()
binary=main/'ir/.lake/build/bin/p4blo-lean'
report=compare_program(program,cases,ports,[binary],seed=seed)
assert report.divergences and report.protocol_error is None and report.both_errored==0
saved=root/'.artifacts/drt/firewall-bloom-other-cell-retained-first.json'
assert not saved.exists()
saved.parent.mkdir(parents=True,exist_ok=True)
replay.save(report,saved)
for d in report.divergences:
 assert d.python.error is None and d.lean.error is None
 assert d.python.diagnostic is None and d.lean.diagnostic is None
 assert d.python.outputs==d.lean.outputs and d.python.state!=d.lean.state
assert saved.read_bytes()==(main/'.artifacts/drt/firewall-crc32.json').read_bytes()
live=replay.replay(saved,[binary])
assert len(live.divergences)==len(report.divergences) and live.both_errored==0 and live.protocol_error is None
print('normal two-write completion and full observer rejection; clean state-only mismatches',len(report.divergences),'requests',len(cases))
print('reused input bytes',len(saved.read_bytes()),'sha256',hashlib.sha256(saved.read_bytes()).hexdigest())
PY
```

Restore the actual Python source exactly, rebuild both Lean packages in the
fault tree, then run this check there. The original saved filename below is
byte-identical to the retention-first rerun; neither is a new input.

```sh
nix develop -c uv run python - <<'PY'
from pathlib import Path
import hashlib
from p4blo.drt import replay
from p4blo import ir
import pytest
from tests.test_lean_firewall_bloom import observe_insertion,initial,insertion_body
root=Path('/Users/qobilidop/my/work/p4blo-firewall-bloom-faults')
owner=Path('/Users/qobilidop/my/work/p4blo-firewall-bloom-next')
paths=['ir/P4bloIR/Externs.lean','python/p4blo/externs/register.py','lean/P4blo/TutorialFirewall.lean','lean/P4blo/TutorialFirewallBloom.lean','lean/P4blo/TutorialFirewallBloomTests.lean','tests/test_lean_firewall_bloom.py','lean/P4blo.lean','lean/P4bloTests.lean','lean/UserProofAudit.lean']
for path in paths:
 data=(root/path).read_bytes()
 assert data==(owner/path).read_bytes(),path
 print(path,hashlib.sha256(data).hexdigest())
program=ir.load_text(root/'tests/corpus/tutorial_firewall/tutorial_firewall.txtpb')
patch=pytest.MonkeyPatch()
for overlay in [False,True]:
 observe_insertion(initial(program,3,1,2,overlay),insertion_body(program),(1,2),patch)
patch.undo()
report=replay.replay(root/'.artifacts/drt/firewall-bloom-other-cell.json',[Path('/Users/qobilidop/my/work/p4blo/ir/.lake/build/bin/p4blo-lean')])
assert report.passed and report.agreed==4 and report.both_errored==0
print('Nine final source pairs; full Python boundary both overlays; reused four-packet restored replay: pass')
PY
```
