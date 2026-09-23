# Next real Lean-authored application: the existing forwarder

2026-09-23. Read-only recommendation after reviewing implementation.md, the
accepted IR/spec boundary, the actual forwarder source/golden/STFs, current
Lean construction/execution APIs, and the guarded whole-call checkpoint.
No implementation, builds, mutations or new oracle runs were performed.

## Decision

Advance a complete readable Lean-authored port of `tests/corpus/forwarder`,
not another proof of its unrelated synthetic observer suffix. Confidence:
**high** in the application choice; **medium** in how much declaration
construction should become reusable API before a second real client exists.
Revisit if a faithful port needs new IR semantics or cannot remain a small
reviewable program. Prefer ordinary Lean definitions/smart constructors over
a new macro frontend or another expression/command AST.

The existing 17-field observer remains useful verification instrumentation.
Finishing its complete packet theorem would strengthen that test harness,
but would still prove neither this corpus application nor its parser, table,
action, checksum or architecture behavior. Keep its current bounded claims
and regressions; do not put observer completion on the critical application
path.

## The corpus policy is different

Preserve the existing golden exactly. The real basic forwarder:

- Checks IPv4 validity only. Non-IPv4 frames keep metadata unchanged and the
  existing switch sends them to port0; they are not forcibly dropped.
- Has no TTL>1 guard. Its 8-bit subtraction wraps TTL0 to255.
- Sets Ethernet source to the **old destination**, then writes the action's
  new destination; there is no route-source-MAC input.
- Applies the LPM table, whose default action sets drop. Checksum recomputation
  follows under the same IPv4-valid guard even on that drop path.
- Parses the fixed twenty-byte IPv4 declaration, not arbitrary IPv4 options;
  the documented checksum-verification omission and informative table size
  remain unchanged.

Do not silently substitute GuardedForwardPolicy, add a TTL safety policy, or
change packet fate while calling this a port.

## First executable checkpoint

Add one user-package example module and a default-built exporter, tentatively
`lean/P4blo/Examples/Forwarder.lean`, without another top-level directory.
Use readable named Lean definitions for the actual Ethernet/IPv4/metadata
layouts, parser states, three actions, LPM table, checksum call, deparser and
Program. The source must construct the program, not parse the golden or call
the Python builder. It must not import test-only FieldCommandExamples or its
synthetic Headers/Route/observer declarations.

The existing verified surface is not yet a complete parser/table/action/extern
frontend. For this first complete **authored executable**, explicit existing IR
constructors behind small readable definitions are acceptable only if labeled
as unverified program assembly. Do not call this a complete verified typed
eDSL. Use named typed field references and existing command/list combinators
where they fit; do not disguise raw operations as a certified escape hatch.
The next increments can replace these visible seams individually.

First acceptance should require:

1. Actual Lean export parsed by the public Python loader is exactly equal to
   both `forwarder.py`'s Program and the existing text golden, including all
   declaration order, parameter modes, action/table/defaults and checksum
   concatenation. Do not rewrite the golden to accommodate the port.
2. Actual Python whole-program validator accepts that exported program.
   Separately execute the actual in-memory Lean program through public
   prepareSwitch/runSwitch on the existing configurations; construction and
   indexing alone are not validation.
3. Replay all five existing STF files through Python and Lean, retaining full
   inputs before independent expected answers on mismatch. Reuse existing
   corpus/oracle discovery rather than inventing a second vector format.
   Exact program identity connects this port to existing printed-P4 oracle
   coverage; rerun available pinned SpecTec/BMv2 vectors, accurately recording
   that these compare printed P4, not a newly established original-P4 oracle.
4. Require source-level wrong-branch/default/MAC-order/checksum-field mutations
   to fail the independent golden/known answers; retain a real runtime fault
   with live/restored replay. Add TTL0/1 and dependent old-destination anchors
   explicitly: the five current files are not an exhaustive edge suite.

This is a usable complete program/export/execution checkpoint with bounded
conformance evidence, not a universal program-correctness theorem.

## Smallest named property alongside it

Prove `Forwarder.invalid_ipv4_control_unchanged` over the **actual selected
MyIngress body**, at an initialized action-free control frame with the actual
built declarations and independently described invalid IPv4 source value.
Both real isValid guards are false, so table application and checksum calls
are not executed and executing the entire body returns the identical Run.
Use actual evaluator/machine equations and the existing header-read laws;
do not assume callbacks saying table/checksum/body execution is correct.
Provide an actual-built frame witness and false/true guard mutation controls.

This property deliberately excludes parser construction, runControl's outer
initialization wrapper, deparser and switch fate. The existing non_ipv4 STF
supplies the separate end-to-end expected output, including payload and
port0. A later short initialization composition may lift it to runControl.
It is a modest application property that is true of the original, unlike the
synthetic guarded-invalid-drop theorem.

## Exact remaining seams

| Boundary | Already executable/tested | Proof or authoring obligation |
| --- | --- | --- |
| Scalar expressions/field commands | One typed AST, named paths, validity reads, list sequencing; exact source/runtime laws | No subtraction or concat/cast constructor in current ExprWith. Add each once with independent Fin meaning; subtraction is needed for exact golden syntax, not replace it with add255 merely to reuse an existing lowering |
| Actions and table calls | Actual Python/Lean action frames, bindings, table application and LPM; corpus hit/miss/precedence vectors | Current concrete field-command execution requires BlockFrame/no action layer. Do not apply it to ipv4_forward with active parameters. A real action-frame read/write/lowering bridge and selection/binding correctness remain distinct |
| Parser/deparser | Existing extracts/select/accept and conditional valid-header emission; forward/non-IPv4/too-short vectors and generated parser coverage | No complete typed parser builder or extraction/bit-layout/payload-conservation application proof supplied by current commands |
| Checksum | Explicit checksum16 extern in both runtimes; known-answer tests and independently derived STF checksums | Typed concat144/extern-result assembly and independent checksum/field-order correspondence remain open; no opaque architecture hook |
| Validation | Python validator checks complete exported golden; actual Lean Index.build and fragment relations exist | Whole-program Lean checker soundness/completeness, action/table/parser legality and overall declaration validity remain open |
| Codec | Leaf/Expr/LValue/Arg actual JSON-value laws; statement totality/roundtrip currently under review | Program/declaration codecs, text parsers, version/unknown-field policy and resource limits remain open. In-memory Lean execution does not require serializing first |
| Architecture | Public Lean switch API and Python Switch/Filter, metadata contract and corpus fate checks | Packet fate/drop/port bounds, retained payload and whole pipeline composition are external contracts, not core control effects or consequences of a body theorem |

After the executable port/invalid-path property, prioritize a named independent
`ipv4_forward_rewrite` specification with arbitrary old/new MACs, action port
and TTL (including wrap), complete sibling/validity preservation and real
action-frame execution. Then table selection/binding and checksum are explicit
positive-path premises to eliminate one at a time. Reuse generic mechanisms;
do not build another fixed synthetic call profile to avoid those boundaries.
