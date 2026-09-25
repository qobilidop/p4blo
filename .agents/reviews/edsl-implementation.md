# Independent eDSL implementation review

Reviewed `80eba84..58275b82ed3fdbb82213c28f6fc0db825218daa2` in the
isolated `/Users/qobilidop/my/work/p4blo-edsl-review` worktree on
2026-09-25. This is an AI-agent correctness and fresh-reader review,
not human review. Production files were not edited. Initial review covered
`fb41e27f20af367db3de2d6f89f1c49b3c229844`; the final reviewed revision
includes the independently verified fix below and the documentation/process
follow-up. No blocking findings remain.

## Confirmed finding

**P2, fixed: independent compilation omitted a local's declared type.**
`BlockLibrary.compile()` promises the block's transitive declarations,
including types reached through locals. `Block.__init__` constructs a local
without registering its annotation in the build context. Assembly can mask
this when the selected H/M roots already include that type. Independent
compilation cannot rely on those roots.

Reproducer, executed with the repository's Python environment:

```python
from p4blo import edsl as p4

class Local(p4.Struct):
    value: p4.bit8

class Scalar(p4.Control):
    value: p4.InOut[p4.bit8]
    scratch: Local

p4.BlockLibrary(Scalar).compile()
```

Actual result at the initial revision: `KeyError: 'Local'`, including
when the local is unused. An apply body assigning `self.scratch.value`
fails the same way. Expected: a compiled fragment containing the scalar
block and `Local` declaration. Register local annotations before creating
their core declarations, and cover a type reachable only through a local
in a regression.

Fix `c150d31` registers each local annotation before creating its core
declaration. Reviewed the exact fix and its two regressions, then reran
both the unused-local reproducer above and the variant assigning its field:
both compile and contain `Local`. The added tests cover a nested header,
an enum local, and assembled-program validation. The focused test command
below now gives **34 passed, 3 deselected**. Ruff on the changed block and
test modules passes, and targeted Pyright reports **0 errors, 0 warnings**.
Nix reported temporary eval-cache SQLite contention on some invocations;
all verification commands subsequently completed with exit status zero.

## Checks and fresh-reader exercise

Commands below used
`nix develop /Users/qobilidop/my/work/p4blo-edsl-review --command`
and ran from that worktree. Initial checks ran at `fb41e27`; the fix and
focused suite were rechecked at `c150d31` as detailed above. All completed
with exit status zero except the deliberate failing construction above,
caught by its probe.

- `uv run python -m examples.router.demo`,
  `uv run python -m examples.firewall.demo`, and
  `uv run python -m examples.load_balancer.demo`: exact documented output.
- `uv run python -m examples.custom_extern`: `(1, 2)` as documented.
  Read the interface, factory, registration and explicit host loader;
  state belongs to the binding and no core special case is needed.
- Independently compiled `BlockLibrary(Route, externs=[checksum])` from
  the router README: one Route block, dependency declarations, no exports.
- Applied the router README's suggested policy change in memory only:
  asserted exactly one `port:2` occurrence in `demo.POLICY`, replaced it
  with `port:3`, then called `demo.main()`. Specific route used port 3;
  broad route remained port 1 and the miss remained a drop. No canonical
  source or golden was modified.
- Compiled a scalar caller of another scalar control: one shared
  Increment dependency followed by Caller, with no struct declarations.
- Deliberately exercised duplicate roots, same-name distinct block
  classes, repeated extern object, missing extern declaration, invalid
  extern and error declarations, and empty export labels. Each produced
  an appropriate `EdslError`.
- Recompiled after mutating a previous compiled protobuf: the next build
  was fresh. Mutating the original extern list did not alter the library's
  snapshot; replacing `library.externs` affected the next compilation,
  and restoring it recovered normally.
- `uv run pytest tests/unit/test_edsl_exports.py
  tests/unit/test_explicit_loader.py tests/unit/test_extern_registration.py
  tests/programs/test_block_libraries.py tests/examples/test_examples.py
  -q -k 'not lean_agrees'`: **32 passed, 3 deselected**. Covers shared
  dependencies, role requirements, independently supplied custom externs,
  missing/duplicate/shape-mismatched registration, fresh state per instance
  and load, demo outputs and application golden reconstruction.
- `uv run pytest tests/unit/test_edsl.py tests/unit/test_edsl_v2.py
  tests/unit/test_externs.py tests/unit/test_extern_families.py
  tests/programs/test_corpus.py tests/examples/router tests/examples/firewall
  tests/examples/load_balancer -q -k 'not lean_agrees'`:
  **151 passed, 6 deselected**. Includes corpus reconstruction and
  independent application behavior checks. No corpus/application golden
  changed in the reviewed diff.
- Targeted Ruff check on the new library, build, assembly, reference,
  custom-extern and focused test modules: passed.
- `uv run pyright impl/python/p4blo/edsl/library.py
  impl/python/p4blo/edsl/_build.py impl/python/p4blo/arch/assembly.py
  impl/python/p4blo/arch/reference.py examples`:
  **0 errors, 0 warnings**.

## Other observations and limits

The library/assembly split is visible in the public API and examples.
`p4.Program` is absent from the typed eDSL; the documentation only names
that spelling in migration guidance. The wire Program and dynamic core
builder remain deliberately separate. Generic core imports do not select
an architecture or supplied extern family. Named exports are checked by
class identity, and the loader checks explicitly requested block kinds.

A nonblocking consistency observation: `library.blocks` is publicly
writable, so replacing it with `()` bypasses the constructor's nonempty
guard, and replacing it with `(C, C)` silently compiles C once. No escape
from loader validation or incorrect executable behavior was established.
If mutable library configuration is supported, the constructor invariants
should also be checked when consumed; otherwise read-only properties would
clarify the intended boundary.

The review did not run the full gate, rebuild Lean, run real-Lean
differentials or assurance mutations, or build/run external oracle images.
Those were reserved for the integrator to avoid shared-resource contention.
Custom Python registration does not establish Lean or printer support;
the new guide accurately says so. The existing shape registry accepts bit
widths, not every scalar/aggregate P4 type.

Reviewed the additional `c150d31..58275b8` process/documentation diff after
the fix's checks completed. It records the acknowledged implementation
iteration and makes caller examples, boundary counterexamples, commit
handoffs and provenance freezes explicit. It changes no execution behavior
or semantic claim and introduces no conflicting approval requirement.
Events outside this review were recorded by the integrator; this report
does not independently attest their execution.

The fresh-reader commands and small policy change were straightforward
without conversation context. One process lesson is concrete: preserved
application goldens and broad passing tests do not establish the new
independent-compilation boundary. A block whose dependency is absent from
all H/M roots found a defect those examples masked. Future boundary tests
should deliberately remove the architecture-provided context they claim
the core no longer needs.
