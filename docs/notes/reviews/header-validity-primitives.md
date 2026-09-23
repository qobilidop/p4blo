# Header-validity primitive review

Final review: clear for primitive checkpoint 1.

2026-09-23. Independently reviewed the restored candidate in
`/Users/qobilidop/my/work/p4blo-validity-reads`, based on `cdb7a3c`.
No implementation files were modified or rebuilt by this reviewer.

## Contract and scope

`HeaderPath` can end only at a header, including a directly rooted empty
header. Intermediate aggregates use existing typed Slots. Source observation
selects the independent stored Bool; lowering selects actual member names and
the existing IR `isValid`. There is no new writable validity location,
scalar Ref/Place conversion, command semantics or alternate evaluator.

The path evaluation theorem returns the exact Bool and entire unchanged Run.
The public root theorem discharges base evaluation through actual root lookup
and FrameMatches, including action-first lookup. Its premise is not an
arbitrary evaluator callback. A no-action restriction is appropriately absent
for this pure read; this does not weaken the separate command restrictions.

Typing separately requires actual root declarations and exact nominal Index
agreement. In particular the new authoritative `Typed.isValid` rule checks
the endpoint header declaration even for a direct root with no member steps.
Input and directionless roots remain readable. Kernel negatives exclude
missing declarations, the wrong nominal kind, and scalar/struct endpoints.
The raw navigation datatype is not claimed to certify global schema validity.

Constructive mixed-store and direct empty-header witnesses demonstrate that
the theorems are usable. Runtime answers independently distinguish all four
sibling validity combinations. Non-value Run sentinels and all relevant
stored roots are checked; the universal unchanged-Run theorem is stronger
than this finite observer. The real Index.build/Frame.forBlock example is
correctly described as a finite initialization witness, not an initializer
theorem. No Python export or new Python equivalence claim is made here.

## Independently executed checks

- Existing compiled `lean/.lake/build/bin/userTests`: exit 0, including eight
  nested and two direct validity answers, real initialization and five
  rejected constructor checks, plus all existing user suites.
- Pinned Lean stdin query importing both `P4blo.HeaderFieldTests` and
  `Tests.FieldTyping`: exit 0. A fresh `#eval HeaderFieldTests.run` passed.
- Queried all four advertised HeaderPath/HeaderRef typing/evaluation roots:
  each reports exactly `[propext, Classical.choice, Quot.sound]`, matching
  the default audit guards. No additional axiom assumption appeared.
- Reviewed public export, ordinary user test driver and default audit
  registration. `git diff --check`: exit 0.
- Compared both candidate source files against the restored isolated mutant
  copies with `cmp`: both exit 0.

The implementer's complete two-package gates and 469 required differential
checks are attributed evidence, not repeated full gates by this reviewer.

## Adversarial evidence

Inspected the captured constant/inverted source-validity proof failures:
both reach the actual arbitrary Bool equality in HeaderPath.evaluate, rather
than an unrelated syntax or shape error. These are proof rejections, not
runtime differential detections.

The well-typed caller alias from Ethernet to IPv4 passes the generic proof
and user-test compilation, then fails the independent expected Bool at
runtime for opposite sibling validities. The restored runtime log passes.
The note records exact reconstructible edits and correctly distinguishes
generic correspondence from caller intent. No fabricated replay bundle or
whole-program claim is present.

No blocking findings. The planned unified read/application checkpoint should
retain separate scalar write constraints and add actual Python return and
read-side-effect faults with complete saved/live/restored differential inputs.
