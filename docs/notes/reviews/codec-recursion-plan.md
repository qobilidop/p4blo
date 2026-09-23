# Recursive codec feasibility review

**Approved for the bounded Expr-only production increment**, not as an
already established recursive-codec theorem. Reviewed the plan and both
isolated probes in `p4blo-codec-recursion` at baseline `ba274f3`, together
with the actual production helper and decoder definitions. Production
`Json.lean` remains unchanged in this planning checkpoint.

Independently executed the positive probe against the stable pinned Lean
build: exit 0, with all seven named results using only standard foundational
axioms. The structural lookup proof follows physical tree branches and
generated structural size, without assuming well-formed balancing, ordering
or cached tree counts. The null-as-absent lookup path and synthesized empty
message case are handled explicitly. Universal `boundedMsgField` erasure
preserves both successful callback results and exact errors of the actual
helper; it is not merely a sample of normal messages.

Independently executed the negative fixed-point probe: exit 1, specifically
the documented missing non-tail `Except` monotonicity/`MonoBind` obligation,
after the tail control's unfolding theorem succeeded with standard axioms.
This supports preferring finite well-founded recursion; it does not show
that every possible fixed-point encoding is impossible.

The proposed measure argument is appropriate. A selected oneof payload
is strictly smaller than the outer object; a successful message lookup's
target is no larger than that payload, even when it synthesizes `{}`.
Demanding strict descent from the payload itself would mishandle an empty
payload and risk changing missing-message semantics. Expr has no recursive
arrays, so it is a useful independently reviewable first boundary.

The plan correctly leaves selected-oneof erasure and the actual recursive
definition as unfinished implementation obligations. Its acceptance gate
requires replacing the actual production decoder, preserving its public
signature/defaults/field visitation and exact diagnostic order, with no fuel
limit or parallel proof-only decoder. A checked unfolding equation and a
nontrivial actual nested roundtrip must land before claiming the seam usable;
a universal Expr representability result remains a separate claim unless
also proved. The existing opaque decoder cannot simply be assumed equal
to a new function: pre-change descriptor/wire/error vectors and helper
erasure provide the planned compatibility evidence.

The staged acceptance tests cover every constructor, unequal operands,
semantically invalid but representable nodes, all relevant missing/null and
malformed cases, ordered multi-errors and independent Python wire mapping.
The explicit timeout-retention gap is a useful in-scope observer correction,
not a codec correctness theorem. Paired wrong wire mappings must still be
challenged with an independent decoded descriptor; roundtrips alone remain
insufficient. Test artifacts must survive crashes/timeouts and missing replay
selections must fail.

Array traversal erasure, LValue/Stmt recursion, raw-text parsing policy,
resource limits and whole-program codec/validator/execution theorems remain
staged obligations. Keeping TreeMap-internal lemmas behind a focused helper
is important for future pinned-toolchain changes. No build, production edit,
Docker operation or full suite was performed for this planning review.
