# Actual flat command-prefix review

Final review: clear; chronological investigation follows below. Combined
integration gates remain the integrator's responsibility.

2026-09-23. Reviewed the stable candidate in
`/Users/qobilidop/my/work/p4blo-command-prefix`, based on `ad746c5`.
No candidate source edits or rebuilds by this reviewer.

## Proof boundary

The same generic command induction now proves execution from the real flat
`cmd.lower ++ suffix` statement list to the exact pending `statements suffix`
work item, followed by the unchanged arbitrary continuation. It does not
silently replace the wrapper with two initially queued statement lists.

The empty command correctly takes zero transitions. Assignment consumes only
its actual list-head/statement steps and carries the suffix through its tail.
The chosen branch uses an empty suffix locally, leaving its administrative
empty-list item; the proof explicitly consumes that item before executing
the shared command tail with the real outer suffix. This is the significant
queue-shape distinction, not merely a renamed whole-body theorem.

The previous generic whole-body theorem follows by empty suffix plus the
real machine's final empty-list transition. Both public scalar/field steps
signatures and their exact source, non-variable Run and outside-target facts
are retained. Concrete adapters still discharge individual read/write laws;
they do not assume an arbitrary whole-command correctness callback. Field
typing remains about the authored prefix only, not the arbitrary suffix.
No AST, source meaning, lowering, runtime transition or wrapper has changed.

All machine endpoints have no pending fault by construction. An arbitrary
suffix or continuation can contain faulting work without being executed.
The theorem is a finite successful prefix, not completion or termination of
that later work. Existing initialization/caller/copyback exclusions remain.

## Witnesses and independent tests

The concrete prefix_correct witness quantifies over every modeled source
store, suffix and continuation and discharges actual declaration, Index,
FrameMatches and BlockFrame premises using existing constructive witnesses.
It is correctly not described as a caller initialization theorem.

Sixteen finite cases combine both hit values, empty/nonempty suffixes and
four independently specified boundaries: empty command at zero steps,
assignment at two, empty branches at three and branch/shared tail at nine.
The private advance helper drives the actual Execution.step exactly N times;
it is a test observer, not an alternate semantics or theorem premise.

Tests check exact pending suffix, return frame and continuation shape, scratch
answers, unrelated stored values and non-value Run sentinels. The continuation
carries a distinct caller frame, so premature return is observable. Executing
the pending suffix separately overwrites scratch to 200 and then faults;
with an empty suffix the continuation faults instead. These controls establish
that unexecuted work is nontrivial, not an inert suffix chosen to pass.

## Independently executed checks

- Compiled userTests: exit 0, including all prior suites and the 16 new
  queue-boundary/full-state cases.
- Fresh pinned Lean import/query plus CommandPrefixTests.run: exit 0; all
  four generic/scalar/field/concrete-witness audit roots report exactly
  `[propext, Classical.choice, Quot.sound]`.
- Ordinary native driver and four default audit guards are registered.
- Candidate whitespace check: exit 0.

No blocking structural finding. The implementer's fresh complete package and
required differential gates remain separately attributed. Final isolated
proof-contract/runtime-dispatch faults and restoration will be reviewed before
closing this report; proof rejection will not be called runtime detection.

## Final mutation and restoration closure

Reviewed the completed command-prefix note and the actual fault logs. The
false consumed-suffix endpoint fails at the empty-command queue equation;
omitting the branch's administrative empty-list transition fails composition
at precisely that queue mismatch. Both are accurately called proof rejections.

The actual Exec.dispatch `ss` to `ss.tail` fault compiles both the IR module
and runnable Lean interpreter. The prefix induction separately rejects its
incorrect actual transitions. The existing dependent-next DRT case genuinely
runs the faulty binary and records a clean mismatch: Python emits the
independent expected state bytes, while Lean emits zero observation bytes and
retains the packet suffix. The saved live CLI replay reports one divergence,
no errors. This is runtime inconsistency evidence in addition to proof
rejection, not an inferred result from a failed build.

Independently loaded the retained 40,053-byte bundle and required exact
equality to the current tracked authored fixture's dependent-next program,
one empty-entry/port-0/deadbeef request, four ports and seed zero. Its SHA256
is `689d227dbe6e84f1398a6fd5bbb8a0db3185123733fbe04231f94919677ed130`.
It is byte-identical to the existing main artifact, independently checked;
the note correctly counts this as another killed fault on the same input,
not another distinct witness. Independent restored replay succeeds with
one agreement and no protocol or both-error result.

Both intentionally changed source files cmp-equal the untouched candidate.
Their SHA256 values match the recorded restoration hashes, and production
Exec.lean has an empty diff. The restored selected runtime log passes its
one test; the fresh restored complete-package/default/native gate and
candidate 564 required DRT are separately attributed root evidence.
Candidate whitespace checks pass.

The final note preserves exact edits, relevant build/test/replay commands and
honest boundary claims. No remaining correction requested; clear for the
scoped proof/test commits and subsequent combined integration gate.
