# Actual plain-root call entry

2026-09-23. Implements the entry-only slice of
[the reviewed plan](call-entry-plan.md). No body-prefix, observer execution,
return, copyback, caller initialization or packet-wrapper theorem is claimed.

## Exact boundary

`P4bloIR.PlainCallEntry.dispatch_entry` unfolds the actual block arm of
`Execution.dispatch`, including block lookup, exact arity, actual
`Frame.forBlock`, and its four-element binding loop. Its initializer equality
and four caller reads are explicit lower-level premises. The closed
`boundFrame` expression describes four ordered map inserts; it is not another
initializer or binder. The result is exact equality of the whole `Run` with
only its frame replaced, and exactly `runBlock block` followed by
`blockReturn originalCaller params args`. `entry_steps` preserves arbitrary
pending continuation and has no pending fault at either endpoint.

`P4blo.CallEntry.source_entry` discharges initialization using
`Layout.initialize`, source-zero correspondence, nominal agreement and an
explicit fuel bound for the actual-built selected declaration program.
Modeled hdr/meta/route data are arbitrary; scratch is independently zero.
The actual extra declarations observer:H and unrelated:bit<8> have explicit
zero-success proofs. After binding, the entire caller observer value is
preserved and unrelated remains zero. The theorem also gives the exact
looked-up scope, absent action layers and source `FrameMatches`. Its caller
is explicitly a `BlockFrame`; actual caller lookup premises remain. Runtime
argument binding itself does not typecheck the supplied observer value, so
the theorem preserves an arbitrary `Value` without claiming its typing.

`CallEntryDeclarations.program` contains exactly the selected RewriteBody
declarations, Ethernet/IPv4/Result headers and Headers/Metadata/Route/H
structs. Its empty body is deliberate: the endpoint precedes execution of
that body. It is not the full Python wrapper or caller. `index_built` is a
kernel-checked real `Index.build` equation, not a native test or manually
inserted scope. `CallEntryTests.concrete_entry` applies the public theorem to
an actual nonempty caller for arbitrary Ethernet/IPv4 validity bits. Both
roots, along with the generic bridge, are default axiom-audited.

The failing-extra counterexample adds an undeclared `Missing` struct local
to this actual declaration program. The kernel proves its `Index.build`
succeeds, its zero is impossible, and the exact extra-zeroability premise is
false for an actual looked-up declaration outside the modeled roots.
Native execution separately checks that actual `Frame.forBlock` fails.
Direct kernel reduction of the entire failing HashMap initialization hit
the recursion-depth limit (also at 4096); this optional whole-loop negative
was replaced with the smaller exact-premise counterexample, not called a
kernel initialization-failure theorem. The positive real-built initializer
and call theorem remain fully kernel-checked and default-audited.

## Independent observations

The default `callEntry` exporter emits selected declarations, actual args,
and four snapshots obtained by one actual `Execution.step`. Python compares
the declarations/types/args with the tracked `field_command_program`,
projecting away only the selected block body. Nominal declaration order is
ignored; field order, names, widths, directions and argument kind are exact.
This is an executable declaration consistency check, not a wire-codec or
whole-program identity theorem.

All four header-validity combinations retain asymmetric source fields and
nonzero H/Result observer sentinels. Independent expected values check six
callee variables, absent caller-only name, exact caller capture, two pending
return/body items and a deliberately faulting continuation still pending.
Packet bytes/value/cursor, emitter, installed entries/index, extern state,
visits and scope/action-layer sentinels are checked. The theorem preserves
all non-frame state, not merely the observed sentinels.

Python uses its existing `stmt.call_block`, intercepting only `run_block`
after the real binder has completed. The snapshot is taken before Python's
subsequent copyback; no claim is made about that return. Shared non-frame
object identity and independently frozen contents, including the untouched
caller, are checked at this boundary. The expected
values are written separately, not obtained from a source denotation or
either runtime. Native tests also cover unknown block, wrong arity before
initialization, the fourth direction (`none`), and out ignoring both a
nonzero caller value and an otherwise unreadable argument.

## Decisions and limits

- Keep a fixed four-parameter theorem: this matches the useful wrapper and
  avoids a general call framework. Confidence high; revisit when a second
  real call shape needs reusable binder facts.
- Keep exact map lookups, not equality with a independently reconstructed
  HashMap. Insertion representation order is not a semantic obligation.
- Preserve the declaration-only build witness and independently compare its
  selected declarations. Confidence high for this boundary; a full-wrapper
  build/caller theorem is a distinct later checkpoint.
- Source scratch is zero here, not the authored-body fixture's 19. Neither
  scratch:=19 nor unrelated:=165 has executed. The next authorized proof
  boundary is real local assignments and flat-body prefix composition.
- No global validation, unlimited zero fuel, action compatibility, arbitrary
  argument evaluation, copyback, parsing or architecture result follows.

## Evidence

Five real Lean semantic mutations were applied separately to `Exec.lean`.
Each modified runtime module compiled successfully (exit 0), and the
unchanged `PlainCallEntry` correspondence module failed to prove (exit 1):

| Actual mutation | Rejected obligation |
|---|---|
| Swap insertion destinations hdr/meta while preserving argument reads | Unequal ordered insert maps in `dispatch_entry` |
| Evaluate observer but skip its insertion | Missing observer insert in `dispatch_entry` |
| Capture callee instead of original caller in blockReturn | Final frame is not arbitrary original caller |
| Set Run.packet to none after setFrame | Would require `none = run.packet` |
| Change argumentValue's zero guard from out to none | `argument_out` can no longer reduce to actual zero |

These are **proof rejection**, not runtime differential detections. Initial
malformed record-layout and unused-variable variants failed to compile;
they were corrected before the successful runtime-build/proof-rejection
checks above and are not counted as semantic detections. Lean source was
restored byte-for-byte: `Exec.lean` SHA-256
`ae4bef02b3ce8255a919d8e69375439fcaecd4f87cdd90702dd3e3b655235e75`.

Independent review identified a real test observer weakness: identity of
shared objects, and equality with an aliased caller dictionary, do not
detect content mutation. The observer now freezes caller JSON and immutable
contents of packet, emitter, full installed entries/defaults and index
program, nonempty extern register cells, and full visits before calling.
Eight permanent regressions wrap the actual `Env.enter_block` with isolated
cursor/caller/extern/visits/entries/emitter/index/caller-action changes. Each old weak observer
passes and the strengthened one rejects at the real entry boundary.
The second review pass additionally required detached deep copies of the
entire Index dataclass (not merely its unchanged Program bytes), original
caller scope/action layers and selected callee scope. The strengthened
observer checks those and the installed-entries Index too: lookup-map
clearing and caller metadata changes cannot hide behind unchanged identity.

The final independent review also demonstrated Python's `False == 0` and
`True == 1` could accept malformed native JSON validity/fault flags. The
observer now compares the **complete** expected snapshot through the existing
type-sensitive canonical-JSON helper, and requires exactly four unique
Boolean validity pairs. Seven permanent malformed-export regressions cover
stored validity, fault flags, zero-valued bits, case flags and duplicated,
missing or extra cases. These are observer-validation failures, not claimed
Lean semantic mismatches or proof rejections.
The final Python observed-versus-expected values use the same strict helper.
A retained argument-value fault changes only the copied Ethernet validity
from false to integer zero, leaving the caller intact: the old equality
passes, while the strict Python output comparison rejects it.

A separate actual Python `stmt.call_block` mutation inserted this code
immediately after `callee = env.enter_block(block)`:

```python
if env.packet is not None:
    env.packet.cursor += 1
```

The focused four-validity entry tests executed and all four failed at the
frozen shared-state comparison, cursor 4 versus expected 3. This is an
**entry known-answer runtime failure**, not whole-program DRT. The durable
regression `test_call_entry_observer_rejects_shared_state_faults[cursor]`
reproduces this same state-only boundary fault using the real enter-block
method; its weak pass and strong rejection are retained in the suite.
Reproduction commands, from this worktree:

```sh
nix develop -c uv run pytest tests/test_lean_call_entry.py -q -k observer_rejects
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_lean_call_entry.py -q -k 'test_lean_agrees_on_call_entry and not declarations'
```

The second command is the live/restored actual-source check. The actual
Python source was restored byte-for-byte: `stmt.py` SHA-256
`4aeb566ca2281d10935c60883a7acad7dd80385c29258c8e9d02e5fd1226a014`.
No packet-program DRT replay bundle is claimed for these non-packet-entry
snapshots. The complete constructive input and independent expected entry
state, along with all fault reproductions, live in the focused test module.

The paired fixture challenge changed `CallEntryDeclarations.resultWidths`
from dst:48,src:48 to src:48,dst:48. This changes both the nominal layout and
the generated declaration consistently. All source/concrete proofs,
`UserProofAudit` and the exporter built successfully (exit 0), but
`test_lean_agrees_on_call_entry_declarations` failed (exit 1) against the
tracked Python wrapper's field order. The permanent paired-remapping test
retains this independent anchor. This is a declaration mismatch, not an
interpreter mismatch. Restoration SHA-256 for `CallEntryDeclarations.lean`:
`3d35cd51475c3d6538f71bb95d0f2e494cd4f147ea3e4885112a3a857b1dac2f`.

Final restored gates (pinned Lean `v4.34.0`, fresh worktree caches):

- `nix develop -c scripts/check-lean.sh`: exit 0, both packages/default
  audits/native suites; 488 IR checks (481 prior plus seven entry/out checks).
  All twelve newly audited generic/concrete/negative roots use exactly
  `propext`, `Classical.choice`, `Quot.sound`; no native reduction axiom.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_lean_call_entry.py -q`:
  exit 0, 23 passed after all observer review fixes.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q`:
  exit 0, 569 passed, 1442 deselected, no skips (49.54 s), after all final
  tests-only refinements. Earlier complete runs also passed 569.
- Focused Ruff check, Ruff format check and Pyright: exit 0; no diagnostics.
- `git diff --check`: clean. Actual `Exec.lean` and Python `stmt.py` diffs
  are empty, with restored hashes above; no intentional fault is committed.

The first full Lean baseline preceded the fault campaign. The final restored
two-package gate rebuilt all changed dependencies and reran default audits
and native tests. No executable was rebuilt during the final focused or
required runtime tests. Docker/oracle/XDP builds were not run; the integrator
owns full combined integration checks. This proof/test increment
changes no production semantics or existing wrapper program.

Independent read-only review: [plain call entry](reviews/plain-call-entry.md),
clear after the observer fixes above. The reviewer independently ran both
Lean packages/default audits/native tests, all twelve axiom queries and the
final focused 23 tests, and inspected the retained fault diagnostics and
restoration hashes. The integrator owns that review artifact.
