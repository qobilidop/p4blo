# Preserve the actual flat statement suffix

2026-09-23. Proof-only prerequisite identified by the reviewed call-entry plan.
Isolated `work/command-prefix` starts at committed main `ad746c5`.

## Why the existing continuation theorem is not enough

An actual control body queues one flat statement list containing local
initializers, the authored command and observer statements. Existing Cmd.steps
executes a work item containing only the authored command, then leaves a
separate continuation stack. Those are different machine states. The proof
must bridge them rather than changing the actual wrapper's representation.

Strengthen the single generic command induction with an arbitrary statement
suffix. Its initial work item contains `cmd.lower ++ suffix`; its endpoint
contains `statements suffix`, with the entire continuation still pending.
The empty command takes no step. A chosen conditional branch still executes
its own actual list and consumes its administrative empty-list work item
before proceeding through the command's remaining flat prefix.

Derive the existing whole-body theorem by taking the empty suffix and then
executing the actual empty-list transition. Keep its original public signature
and all existing application theorems. There is no new command constructor,
lowerer, denotation, executor or runtime wrapper edit. Leaf assumptions remain
individual exact reads/writes; public scalar/field adapters discharge them
with the existing concrete laws. Exact source state, complete non-variable
Run preservation and outside-target lookups remain required conclusions.

Confidence: high in this narrowly stronger proof boundary, medium in whether
future applications need a general machine-list composition theorem instead.
Revisit after a second non-command prefix requires composition. This increment
does not execute call entry, local initialization, an observer, return/copyback
or fault unwinding. A suffix may itself fault; it remains unexecuted.

## Checked implementation and independent boundaries

`CmdWith.steps_prefix_with` is the strengthened induction. Existing
`steps_with`, `Scalar.Cmd.steps` and `Fields.Cmd.steps` retain their signatures
as derived empty-suffix instances. The concrete `steps_prefix` adapters retain
all original typing/frame/index/mode premises and discharge every generic
leaf using existing actual-code laws. No suffix typing or termination promise
is added: the suffix is arbitrary unexecuted IR, not part of the authored
command's typing conclusion.

Default audits cover the generic lemma, both concrete adapters and the
`CommandPrefixTests.prefix_correct` constructive witness for arbitrary source
stores, suffixes and continuations. All four report exactly
`[propext, Classical.choice, Quot.sound]`. The witness uses existing initialized
Run premises and is not a call-entry or caller-initialization theorem.

Sixteen native cases independently fix both branch outcomes, empty/nonempty
suffixes, empty commands, a write, empty branches and an order-sensitive shared
tail. Literal step counts 0/2/3/9 and scratch answers are not computed by a cost
function or the denotation under test. Endpoint observation includes pending
suffix, saved caller return, faulting continuation, exact scratch, all other
modeled roots, outside storage and nontrivial packet/emitter/entry/extern/visit
sentinels. Executing a pending nonempty suffix overwrites scratch with 200;
executing the pending queue produces its designated parse error. Thus these
are observably distinct unexecuted boundaries, not inert suffix fixtures.

Fresh-cache two-package gate and all default/native tests exit 0 (481 spec
checks). Required real-Lean DRT: 564 passed, 1424 deselected, no skips, exit 0.
All five preexisting authoring exporters have identical raw stdout, clean
stderr and status versus checked main `cffad0d`: scalarExamples 5155 bytes,
scalarCommands 4402, fieldExpressions 1590, fieldCommands 17721, headerReads
6008. No schema or Python runtime changed. Full combined integration gates
remain the integrator's obligation. No Docker images were built.

## Deliberate faults

Candidate sources stayed unchanged. A separate worktree
`p4blo-command-prefix-mutants` at the same base received the candidate proof
and test files by anchored patches, then built both packages from fresh caches
with the new 16 tests passing. Three separate challenges followed:

1. Change only the generic prefix theorem's endpoint from
   `statements suffix :: continuation` to `continuation`. The proof build
   exits 1: even its empty-command case cannot discharge the false queue
   equation, and branch composition also fails. This is rejection of a false
   logical contract, not a production runtime mismatch.
2. Restore the statement, then replace
   `branchTrace.trans (.next rfl tail)` with `branchTrace.trans tail`.
   The proof build exits 1: the chosen branch still has its actual empty-list
   work item pending. Omitting that administrative step is not a valid
   composition. This is proof rejection, not runtime detection.
3. Restore the proof and change the actual IR executor in `P4bloIR/Exec.lean`:

   ```diff
   -  | .statements (s :: ss) => pure [.statement s, .statements ss]
   +  | .statements (s :: ss) => pure [.statement s, .statements ss.tail]
   ```

   Both `lake build P4bloIR.Exec` and `lake build p4blo-lean` exit 0.
   Building `P4blo.Commands` exits 1 at the real transition equations: dropping
   a tail element cannot equal the required authored-tail-plus-suffix list.
   Separately, the compiled faulty Lean endpoint is exercised by the existing
   independent `dependent-next` field-command test. It exits 1 with one clean
   divergence, no protocol error and neither side faulting. The full input is
   saved before assertions. Python returns the existing independent expected
   packet; faulty Lean emits 42 zero observation bytes followed by `deadbeef`.
   Live replay exits 1 with the same divergence. This is a genuine runtime
   inconsistency in addition to the proof rejection.

Faults 1/2 use the pinned environment from the mutant's `lean/` directory:
`nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.Commands`.
Fault 3 builds actual IR targets from `ir/`, then runs from the worktree root:

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest 'tests/test_lean_edsl_field_commands.py::test_lean_agrees_on_authored_field_commands[dependent-next]' -q
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/lean-field-commands-dependent-next.json
```

The retained 40053-byte bundle is byte-identical to the existing main replay
of that program (SHA256
`689d227dbe6e84f1398a6fd5bbb8a0db3185123733fbe04231f94919677ed130`).
It is an additional fault detected by the **same** input, not an additional
distinct execution witness. The tracked test reconstructs its exact exporter,
wrapper, request and seed. The replay runner selects the current binary; saved
command metadata is never executed.

Both mutated sources are restored, with byte comparisons to the untouched
candidate and an empty production Exec diff. SHA256 values:

```text
17550dfa95e6d7e904333e6e86fcb118c59ef4d0cb625f1c2417d17b3a042b6b  lean/P4blo/Commands.lean
ae4bef02b3ce8255a919d8e69375439fcaecd4f87cdd90702dd3e3b655235e75  ir/P4bloIR/Exec.lean
```

Restored both-package/default/native gates exit 0, including all 16 boundary
cases; the retained input replays with one agreement/no errors, exit 0, and
the exact selected DRT test passes again. Independent final review is clear:
`reviews/command-prefix.md` records separately executed native/audit checks,
source-matched replay, byte/hash restoration and inspected actual fault logs.
Local logs under `/tmp/p4blo-command-prefix-` supplement these tracked recipes; the
recipes and checked source are the durable evidence, not temporary logs.
