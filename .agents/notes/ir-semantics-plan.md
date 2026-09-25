# Plan: the arch-free IR semantics story

Drafted 2026-09-24 from a review of the repository, the P4-SpecTec
OOPSLA 2026 paper and toolchain at the pinned commit `2730cfd9`, and the
current practice in comparable projects (cedar-spec, leanerVM, ESMeta and
JEST, ETH2SpecTec, HOL4P4.EXE). Not yet a scope: nothing here is active
until the user adopts it, and the decisions it proposes are not recorded
in `decisions.md` until then.

## Framing

p4blo is an independent P4-inspired project. It does not ask P4 to adopt
its semantics; it uses the best tools for its own goal. The goal, restricted
to what this plan covers, is:

> An architecture-free IR whose meaning is an executable, proved Lean
> definition; an independent Python reference tested against it to the
> current state of the art; and a checked account of how that meaning
> relates to P4's own mechanized semantics, up to elaboration and a
> listed set of deliberate deviations.

Three consequences for the current repository:

- **P4-SpecTec becomes the primary oracle.** BMv2 stays as the tie-breaker
  where SpecTec is known to be wrong (CRC padding, mask construction), not
  as a co-equal claim.
- **Everything architectural is frozen.** Claim 3, the two architectures,
  the application collection and the XDP profile keep their evidence and
  get no new work. The application proof drafts stay parked.
- **"Normative" leaves the vocabulary.** The Lean definitions are
  "executable and proved, checked against SpecTec". The reference for what
  P4 means is SpecTec's elaborated IL; p4blo's IR is a serialized,
  architecture-free, closed refinement of it.

## Division of labor with the SpecTec-to-Lean compiler

Decided 2026-09-24. A separate project compiles P4-SpecTec's elaborated
spec into Lean and verifies that compiler. This repository therefore
owns exactly four things and builds nothing else about SpecTec:

- **the IR and its meaning**: `spec/ir/`, the ledger, the deviation and
  validity theorems, the Python reference and its differential evidence;
- **the elaboration from SpecTec's IL to the IR**: the bridge, kept
  small and specified, because it is the other side of the eventual
  simulation theorem;
- **the block contract in SpecTec's own language**: `p4blo.watsup`, the
  definition of running one parser, control or deparser on the
  architecture-free rules, which the compiler project renders and the
  theorem relates to `P4bloIR.Exec`;
- **the validation suite the rendering will be checked against**: the
  conformance fixtures, the block-runner requests and the rule-coverage
  measurement, all with stable documented formats.

Not built here: any rendering of SpecTec's rules into Lean, any Lean
interpreter for them, N+1 differential testing with trace localization
(the rendering makes it a theorem instead), further simulator patches
beyond keeping the two existing ones applying at the pin, and any
expansion of the bridge's census beyond the corpus and the programs the
theorem's domain needs. The oracle machinery built in Phases 1 and 2
stays as it is, frozen at maintenance: it is the test bed for the
rendering, not a thing to grow.

## What the state of the art looks like

| Practice | Who does it | p4blo today |
|---|---|---|
| Executable model in a prover, production implementation, typed generators, differential random testing, retained regressions | cedar-spec, leanerVM | in place |
| Model called through a stable interface with a serialized exchange format | Cedar (FFI plus protobuf) | pipe plus protobuf JSON; equivalent |
| Coverage of the *specification's rules* as the adequacy criterion, and generation guided by it | ESMeta/JEST/JESTfs, SpecTec's coverage command, ETH2SpecTec | parser-state coverage only |
| A conformance corpus exported from the model as data, consumed by every implementation | Cedar integration tests, Wasm spec tests | live pipe only |
| N+1 differential testing: several implementations plus the spec, disagreement localized to a rule | JEST | pairwise only, no localization |
| Deliberate faults on both sides, checked catalogue | cedar-spec informally; p4blo formally | in place, ahead of most |
| Comparison to the language's own mechanization at the IL level, not through surface syntax | nobody yet for P4 | printed P4 through a v1model shim |

The last two rows are where p4blo can be ahead of everyone; the middle
three are where it is behind.

## Workstreams

Each has a goal, deliverables, the gate that proves it, and an exit
criterion. Sizes are S (days), M (a few weeks), L (a quarter).

### A. SpecTec as the primary oracle, at the level of the arch-free rules

**A1. Generated programs on SpecTec (S).** The DRT generators already emit
validated packet-visible programs. Print them, translate their cases to
STF, and run them on the simulator through the existing adapter. Gate: a
new job in the oracle workflow with a fixed seed set and a nightly larger
run. Exit: the corpus of SpecTec comparisons grows from twelve programs to
thousands; every disagreement is a classified exception or a fixed bug.

**A2. SpecTec rule coverage of p4blo's inputs (S).** SpecTec ships a
coverage command that runs STF directories and reports which rules fired.
Run it over the corpus and the generated programs; produce a tracked
report listing every rule of `spec/8-dynamic` and the functions of
`spec/3-operations` as hit, unhit-in-scope, or out-of-scope by
p4-spec-coverage.md. Gate: a test that fails when an in-scope rule is unhit and
not listed as excluded with a reason. Exit: the semantic surface p4blo
claims to share with P4 is exactly the set of rules its tests exercise.

**A3. The deviation ledger (S, then continuous).** Rewrite every entry of
`docs/ir-semantics.md` to a fixed template: behavior, p4blo's choice, the
reason, the P4 specification section, the SpecTec rule or function at the
pin, the Lean definition, the Python function, and the test that exercises
it. Classify each as *same*, *refines undefined* (SpecTec leaves it open;
p4blo closes it), *deviates* (with reason), or *not representable*. A
script extracts the SpecTec rule inventory from the pinned checkout into a
tracked fixture, so the test that checks every citation resolves runs
without OCaml. Exit: "up to known deviation" is a checkable list, not
prose.

**A4. Single-block execution on SpecTec (M).** The simulator only runs whole
v1model pipelines, so today every comparison passes through the shim and
the architecture. SpecTec's architectures are OCaml plugins under
`backend-sim/`; the upstream repository keeps a `patches/` directory, so
a minimal `p4blo` architecture plugin, maintained as a patch applied at
build time and pinned with the commit, is the honest cost. It runs one
parser, control or deparser on given headers, metadata, entries and extern
state, and returns headers, metadata, consumed bits and error. Gate: the
DRT protocol gains a SpecTec runner beside the Lean one. Exit: the
comparison is between p4blo's block semantics and SpecTec's block
semantics, with nothing architectural between them.

**A5. The IL bridge (L).** SpecTec's run command evaluates any named
relation, its instantiation relation produces the elaborated IL, and the
`il-value-tree` branch already prints IL values. Add an exporter from
SpecTec's instantiated IL to p4blo IR. This does three things at once: it
turns every "elaborated" row of p4-spec-coverage.md from a ruling into code; it
gives p4blo a P4 source frontend it never had, going through the
language's own typing and instantiation; and it lets real P4 programs
enter the DRT loop. The reverse direction, p4blo IR to SpecTec IL, is the
printer's successor and comes second. Gate: every corpus program's golden
is reproduced from its original P4 source through the bridge. Exit: claim
1 has the experiment it has been waiting for, at a fraction of a p4c
backend's cost.

**A6. N+1 testing with localization: superseded.** The SpecTec-to-Lean
compiler turns disagreement localization into a theorem about rendered
rules; nothing is built here. The paragraph below is kept for the record.
Run Python,
Lean and SpecTec on the same generated inputs and classify each
disagreement by which pair agrees. SpecTec's `-trace` output and Lean's
explicit step trace make the disagreeing rule identifiable; record it in
the ledger. Exit: a divergence report names a rule, not a packet.

**A7. Upstream tracking (S, continuous).** SpecTec merges fix batches
weekly. Write the pin-bump procedure: bump, rerun A2 and the ledger test,
diff the rule inventory, re-classify. Decide whether to report the four
known SpecTec defects upstream; that is the user's call, and each report
is a small reproducer p4blo already has.

### B. Spec-coverage-guided generation and a conformance corpus

**B1. Rule tags in the Lean machine (S).** Give every closed behavior and
every case of `executeOne` and `evaluate` a stable tag, emitted in the
DRT reply beside the extern state. Python's interpreter as a proxy is not
enough: the criterion must be the model's rules. Gate: the DRT report
prints coverage over the ledger; a test requires every ledger entry to be
hit by at least one retained case. Exit: the adequacy criterion is the
specification, as in JESTfs.

**B2. Coverage-guided generation (M).** Feed B1 back into the generators:
bias toward unhit tags and toward unhit (tag, enclosing construct) pairs,
which is the one-feature-sensitive criterion JESTfs found most effective.
Keep type-preserving shrinking and the rule that invalid generated
programs fail rather than being filtered.

**B3. Exported conformance corpus (M).** Lean enumerates and executes small
programs and request sequences and writes program, requests, outputs and
extern state as tracked fixtures under `tests/conformance/`. Python
consumes them without a pipe; a third implementation could too. Cedar's
corpus tests are the model. Gate: the fixtures are regenerated in CI and
drift fails. Exit: the semantics has a test suite that does not depend on
either implementation being present.

### C. What to prove next, arch-free only

Reprioritized: no new application theorems until A5 exists, because the
theorems so far establish p4blo's internal consistency, and the bridge is
what would make a claim about P4.

**C1. Whole-program validity and progress (L).** A statement and program
checker in Lean, with the theorem that a valid program never gets stuck in
the step machine except at a documented parser error. This is the same
shape as the stuckness lemmas the Lean port of SpecTec is proving, and it
closes the largest open obligation in `design.md`'s authority table.

**C2. Termination under the stated discipline (M, after C1).** Acyclic
call graph plus the no-consumption revisit rule implies the runner
terminates. With C1, a validated program has a defined result.

**C3. Codec composition through Program and Export (M).** Finishes the
interchange story so that the wire form is covered end to end.

**C4. Deviation theorems (S each).** For every *refines undefined* and
*deviates* entry in the ledger, a theorem in the `ScalarLaws` style that
states the Lean result on the case P4 leaves open, cited from the ledger.
Cheap, and it makes the ledger machine-checked on the Lean side.

### D. Code organization and readability

The principle: a reader should be able to go from a ledger entry to the
P4 section, the SpecTec rule, the Lean definition, the Python function and
the test in one hop each, and back. Every reorganization is guarded by the
existing layout and boundary tests and done in a worktree.

**Lean, `spec/ir/`.** Fourteen flat modules with two very large ones. Group
by concern and split the large ones by syntactic category, mirroring the
codec-law files that already exist per category:

```
P4bloIR/Syntax/      IR, Value, Widths
P4bloIR/Semantics/   Env, Eval, Step (today Exec), Tables, Externs, Packet, Interp
P4bloIR/Typing/      ScalarTyping, FieldTyping
P4bloIR/Codec/       Decode/<category>, Encode/<category>, Laws/<category>
P4bloIR/Laws/        Theorems, FieldLaws, ScalarLaws, FrameInitialization, PlainCall*, ExecutionCertificate
P4bloIR/Coverage/    the rule tags of B1
```

Package roots follow the Mathlib and Batteries layout, which is the
one-line answer to "which directory does a Lean file go in": under
`<Root>/` if a client may import it, under `<Root>Test/` if only the
gate runs it (tests, proof audits and probes alike), and at the root
only what Lake requires there: the root module, `lakefile.toml`,
`lean-toolchain`, `lake-manifest.json`, `README.md` and at most one
`Main.lean`. Test libraries are named `<Root>Test`, singular, because
Lake module names are global across a workspace and a bare `Tests` in
two packages collides; that is why `ArchTests` exists today. So
`Tests/` becomes `P4bloIRTest/`, `ArchTests/` becomes `P4bloArchTest/`,
the user package's sixteen `*Main.lean` executables become subcommands
of one `Main.lean` as the arch package already does, and the three
unregistered `*CodecProbe.lean` files at the IR root are deleted or
promoted into the test library. Acronyms stay capitalized inside
module names (`P4bloIR`, as Lean core's `Lean.Compiler.IR` and `LCNF`),
and names read as words are written as words (`Json`, `Lsp`).

Every module header keeps its "mirrors" line to the Python module and
gains the SpecTec rules it corresponds to. Every theorem docstring opens
with a one-sentence plain-words claim, then the premises, then what it
does not establish; the audit files stay the inventory.

**Python, `impl/python/p4blo/`.** The validator is one 1,600-line module;
split it into a package by the categories its own code list already uses,
keeping one public `validate`. Collapse the three expression typers (the
validator's, `interp/widths.py`, the printer's) into one module that all
three import, which closes an open thread. Separate the P4 printer from
the v1model shim, since A4 needs the printer without the shim. The eDSL
and the architectures are out of this plan's scope and stay as they are.

**Tests.** Seventy-six flat files at the top of `tests/`. Group into
`unit/`, `codec/`, `drt/`, `lean/`, `oracle/`, `conformance/`, keeping
the `test_lean_agrees` discovery rule and the layout tests. Each
directory gets a README saying which question its tests answer, in the
words of the six-layer testing strategy.

**Docs.** `ir-semantics.md` becomes the ledger, ordered as SpecTec orders
its rules so that lookups go both ways. `assurance.md` gains a "checked
against SpecTec" table beside "what is proved" and "what is tested", with
the A2 coverage numbers. A generated cross-reference table, checked by a
test, lists every ledger entry with its five links. Comments in code name
the ledger entry, not the prose.

## Sequencing

| Phase | Items | Exit |
|---|---|---|
| 0 | decisions recorded; SpecTec rule inventory fixture; ledger template and citation test | the plan is the scope |
| 1 | A1, A2, A3, B1, C4 | coverage report and ledger published; every in-scope rule hit or excluded |
| 2 | A4, B2, B3, D (in parallel worktrees) | block-level SpecTec comparison; conformance corpus; reorganized tree, all gates green |
| 3 | A5, C1, C2 (A6 superseded) | P4 source through SpecTec into p4blo; validated programs have a defined result |
| 4 | C3; the joint milestone with the SpecTec-to-Lean compiler: its executable rendering answers every conformance fixture and block-runner request as the OCaml simulator does, then the simulation theorem between the rendered `p4blo.watsup` relations and `P4bloIR.Exec` under the bridge's elaboration | the equivalence claim becomes a theorem; the pairwise oracle testing retires |

Phase 1 is the only one that changes what the repository claims without
new infrastructure, so it goes first regardless of what follows.

## Decisions this plan proposes for `decisions.md`

- P4-SpecTec is the primary oracle; BMv2 is the tie-breaker for its known
  defects. Comparison is at the block level once A4 lands, and at the IL
  level once A5 lands.
- The scope is the architecture-free IR. Architectures, applications and
  XDP are frozen at their current evidence.
- The Lean definitions are "executable and proved, checked against
  SpecTec", never "normative".
- The deviation ledger is the contract for "up to elaboration and known
  deviation"; an unlisted difference from SpecTec is a bug on one side.
- The adequacy criterion for generated testing is coverage of the ledger
  and of SpecTec's rules, not test counts.
- No new application or typed-source-language theorems until A5 exists.

## Risks

- SpecTec builds are OCaml-heavy and slow to elaborate the spec on every
  run; A1 needs batching or a resident process, which the simulator's
  cache flag partly gives.
- A4 and A5 need patches against SpecTec; keep them small, pinned with the
  commit, and offer them upstream when they stabilize.
- SpecTec evolves weekly; without A7 the ledger rots.
- Directory moves have broken gates before; D is done last in its phase,
  in a worktree, with the layout tests extended first.
