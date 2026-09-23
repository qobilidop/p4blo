# Statement-codec pre-refactor baseline review

Final review: clear for the pre-refactor baseline only. This is not approval
of the in-progress total decoder, proofs, or mutation campaign.

2026-09-23. Independent read-only review of the test-only baseline in
`/Users/qobilidop/my/work/p4blo-stmt-codec`, production base `1d1168c`, against
the committed `docs/notes/stmt-codec-plan.md`. No implementation files were
edited. No candidate Lean executable or build was run: the owner had begun
the production refactor, so the old capture is checked as recorded evidence,
not relabeled as a fresh observation of the old decoder.

## Structural assessment

The Lean test descriptor matches all fourteen `Stmt` constructors directly.
It does not derive constructor tags, branch order, argument order, optional
targets, or counts from `Stmt.toJson`. Nested expression, lvalue, and argument
descriptors retain their explicit constructor matches, including the earlier
independent operator observations. The endpoint invokes actual `Stmt.decode`
without semantic validation and returns its independent descriptor together
with the actual encoder output.

The Python cases cover all fourteen tags in 28 canonical inputs, including
unequal branches, nested conditionals, mixed/reversed argument lists,
set-valid versus set-invalid, optional result/hit targets, empty/unresolved
names, escaped Unicode, and zero/maximum uint32 counts. These are wire
observations; several deliberately do not describe valid executable programs.

The 42 malformed cases anchor decoder case-list order separately from textual
key order, condition-before-branch processing, then-before-otherwise, array
indices and nested paths, assignment target-before-value, extern
instance/method/arguments/result order, stack-before-count, integer overflow,
and nested expression failures. Nine normalization cases distinguish absent,
null and empty arrays, optional fields, string defaults, decimal count
spelling, and a null competing kind/ignored annotation. These are useful
finite compatibility anchors, not exhaustive field combinations or a general
ProtoJSON acceptance policy.

The shared observer uses strict JSON rendering, not Python's loose
Boolean/integer equality. Canonical actual Lean outputs are parsed by the
protobuf `Stmt` adapter and the public `Program` JSON loader/dumper. The
normalization tests use the same strict known-answer assertion; this reviewer
also independently passed all nine recorded normalized outputs through that
protobuf/public adapter.

## Independently executed checks

- Pure Python canonical adapter tests: **28 passed, 79 deselected**, exit 0.
  Candidate Lean tests were deliberately not selected.
- Artifact size **104543 bytes**, SHA-256
  `303a5bb6b682463d1029951070bb16120bf8c343c38a774d0eafccc89d95979e`.
- All **79** artifact rows match the ordered current `requests()` source,
  with **79 distinct requests**, exact compact-JSON-plus-newline input bytes,
  strict expected JSON, recorded exit 0 and empty stderr. Recorded stdout was
  parsed with the harness's duplicate-rejecting `loads`, not plain `json.loads`.
- All **37 successful** captured outputs also pass protobuf parsing and the
  public Python loader/dumper with strict canonical-output agreement.
- Both frozen descriptor/fixture source hashes match the artifact. The old
  production decoder hash matches `git show 1d1168c:ir/P4bloIR/Json.lean`:
  `44449c41e178a79dcc4d5a566dc4c89827b0810048b553bac7c7fbf293824b9c`.

The initial reviewer script used a nonexistent fixture function name
`statements`; that import failed before checking evidence. The corrected
script used the actual `cases()` function and completed all checks above.
This tooling correction is not a test or production failure.

The owner's pre-refactor gate logs were inspected: the combined codec suite
reports **495 passed**, and the two-package log completes the native/user
tests. Their successful command exit statuses are owner-attributed; this
review did not rebuild or rerun the historical decoder.

## Reproduction and limits

The baseline source is pinned, and the note explicitly requires rebuilding
the old decoder with the frozen test-only endpoint/fixtures. The reviewer
requested two small capture-recipe protections: parse stdout with strict
`loads`, and check the old production source hash before capture so running
the recipe in the now-refactored checkout cannot overwrite old evidence
under a misleading baseline label.

Resolution: independently inspected the updated recipe. It now uses strict
`loads`, compares production bytes with `git show 1d1168c` before any capture,
and additionally refuses to overwrite an existing baseline artifact. The
original retained artifact is unchanged. The reproduction recommendation is
closed.

The artifact establishes the recorded finite behavior of the prior partial
decoder; it does not establish the new decoder's termination or universal
compatibility. Final review must separately inspect the actual production
recursion, erasure/unfolding statements, representability laws and axiom
audits, then replay these exact source-matched byte transcripts and inspect
the independently observed paired-fault campaign. No resource-limit,
duplicate-raw-key, whole-program-validity, or execution claim is approved by
this baseline review.
