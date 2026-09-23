# Exact local-initializer prefix

2026-09-23. Implements the two-assignment prerequisite from
`call-body-prefix-plan.md`, against committed `ac69759`. Independent final
review is clear; no whole-call theorem is claimed here.

`CallInitializers.body` is the actual flat pair scratch:=bit8(19),
unrelated:=bit8(165). `steps` proves four actual machine transitions from
that list followed by an arbitrary suffix to exactly the pending suffix,
with the entire arbitrary continuation unchanged. The result is the exact
original Run with only two ordered inserts into its block variable map.
The premise requires an action-free frame and both actual bindings to exist;
it does not invent runtime declaration or permission checks.

`source_steps` specializes the operational result to the independent entry
source store and yields constructor-based `bodyStore` (same arbitrary
hdr/meta/route, scratch19), unrelated165, ChangesOnlyVars and preservation
of every name outside the two locals. This includes observer and names not
present in the original frame. `body_typed` separately discharges actual
local declaration/type/permission obligations for the two bit8 literals.
It does not infer writable declarations from operational map membership.

The concrete kernel witness derives its starting frame from the actual-built
empty-body call-entry theorem, for every validity pair and arbitrary suffix
and continuation. It then starts at the local statement-list boundary.
This is deliberately not actual dispatch of a body-bearing call: that later
composition must use the body-parametric built index and runBlock transition.
No observer, return/copyback, parser or whole-wrapper correctness follows.

Five default audit roots cover operational/source prefix, local typing and
constructive execution/typing witnesses. Sixteen native cases cross all
validity pairs, zero/nonzero pre-existing unrelated values and empty/nonempty
suffixes. They use literal four-step and 19/165 answers, not finalRun or the
source denotation. They check exact pending suffix/original caller/continuation,
preserved stored roots/validities, local counts and non-frame sentinels.
Those sentinels do not exhaust every native Index map; the theorem itself
preserves the entire Run outside its two variable-map updates.

The pending suffix writes scratch200 then faults; with no suffix the pending
continuation faults. Four missing-extra controls demonstrate that failure of
the second write retains the first write, so no atomic rollback is implied.
The existing full authored-program conformance tests already execute these
exact local assignments. A new packet wrapper or runtime is unnecessary.

Confidence is high in the bounded operational composition and medium in the
fixed two-local API as a reusable abstraction. Revisit after a second actual
initializer shape needs it. Current raw result keeps unrelated outside the
modeled roots, matching the existing authored-store boundary.

## Gates and adversarial evidence

The candidate's pinned two-package/default-audit/native gate exits 0, with
488 spec checks, all existing user suites and the new sixteen prefix/four
missing-extra cases. The first native run used an incomplete expected error
string; correcting it to the actual `unknown variable 'unrelated' in block
'RewriteBody'` resolved that test-only failure. It is not a production fix.
All five new audit roots use exactly `propext`, `Classical.choice`, `Quot.sound`.
Required real-Lean conformance after the retained regression: **603 passed**,
1449 deselected, no skips, exit 0 (49.80 s), after the final error/diagnostic
assertion hardening. Focused retained test, Ruff check,
Ruff format and Pyright pass. No native axioms or runtime source changes.

The independently owned review has run fresh five-root queries, all native
tests and the full compiled user suite, plus 36 existing field-command/entry
Python cases. Final campaign review is clear:
`reviews/call-initializers.md`. Its final request added explicit absent
error/diagnostic and empty-state checks to the retained runtime mismatch;
the independently rerun regression passes. Full combined
Python/schema/oracle checks are the integrator's next gate, not inferred
from this branch's required conformance run.

All faults ran in a separate `work/call-initializer-mutants` worktree at
`ac69759` with copied candidate source and fresh Lean caches. Its untouched
two-package baseline passed first; the candidate itself was never mutated.

1. Change only the actual body scratch literal 19 to 20. Building
   `P4blo.CallInitializers` exits 1 with a genuine false actual transition
   obligation and incompatible typing witness. This is source/lowering
   **proof rejection**, not an executed interpreter mismatch.
2. From the untouched candidate, replace the seven literal tokens `19` with
   `20` in `CallInitializers.lean` only, consistently changing the body,
   result, independent source constant and proof instantiations. Default
   user build and all proof audits exit 0. `lake test` exits 1 at
   `initializer independent local answers differ`: the unchanged native
   literal 19 anchor rejects the paired wrong intention. This is a
   **compiled known-answer rejection**, not a Lean/Python mismatch. Restoring
   that file and rerunning both packages/native suites exits 0.
3. In actual Python `stmt.assign`, evaluate the RHS normally, then replace
   the value with `Bits(8, 20)` only when the block is RewriteBody, target is
   plain scratch, and the evaluated Bits has width/value 8/19. Import Bits
   from the existing values module; leave `write_lvalue` unchanged. The
   modified source compiles. The existing authored `forward-hit` test exits 1
   with one clean divergence, no protocol error or matching errors: Lean
   retains expected scratch19, Python emits scratch20, and all other output
   bytes match. It saves the complete packet-program input before failing.

Fault 3's retained bundle is 43,963 bytes, SHA256
`af03fad4149a65fddbe3345cb546e08e1e9d6820b34a82ac47a9a514abfeb79b`.
The ignored copy is `.artifacts/drt/lean-field-commands-forward-hit.json`;
its source is the existing `fieldCommands` exporter and tracked
`field_command_program` for forward-hit, one empty-entry ingress-0 deadbeef
request, four ports and seed zero. Live replay exits 1 with exactly that
single divergence; restored replay exits 0 with one agreement and no errors.
The restored selected original test passes too. Actual Python stmt.py has
an empty diff and SHA256
`4aeb566ca2281d10935c60883a7acad7dd80385c29258c8e9d02e5fd1226a014`.
Restored CallInitializers.lean is byte-identical to the untouched candidate,
SHA256 `5c5df1bf94024e897524f86c10cb2d5b279e4b1be43a643695a2aaf5907e24e6`.

`tests/test_lean_call_initializers.py` permanently reproduces the same wrong
value through a delegating write hook. It requires exactly one initial hit,
exact saved program/request equality, one live replay hit, the independently
expected one-byte output difference and restored agreement. It is selected
by the required real-Lean gate. The temporary bundle is reconstructible even
if all ignored artifacts disappear; the actual-source recipe above separately
documents that this was also exercised without a test monkeypatch.

Reconstruction commands (use the appropriate isolated worktree root; pinned
Lake builds/tests use its lean directory):

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build
nix develop -c lake +leanprover/lean4:v4.34.0 test
# At the repository root with the actual Python fault installed:
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest 'tests/test_lean_edsl_field_commands.py::test_lean_agrees_on_authored_field_commands[forward-hit]' -q
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/lean-field-commands-forward-hit.json
# Restore Python, then rerun the replay and selected test.
```

Temporary logs use `/tmp/p4blo-call-initializer-` for `one-sided.log`,
`paired-build.log`, `paired-test.log`, `restored-lean.log`,
`python-fault.log`, `python-live.log`, `python-restored.log` and
`python-restored-test.log`. Candidate gate logs use
`/tmp/p4blo-call-initializers-{lean,final-drt2,retained}.log`. Logs are
convenient local evidence, not the only reproduction instructions.
