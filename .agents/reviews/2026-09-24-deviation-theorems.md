# Review: C4 deviation theorems

Commit reviewed: merge `bc4b8bc` (branch `work/deviation-theorems`: `662746e`,
`08d3388`, `2fdaf54`), with a look at the follow-up `e2c6ec1`. Date: 2026-09-24.
Reviewer: independent and read-only. The experiments ran in
`/Users/qobilidop/my/work/p4blo-wt/deviation-theorems`. Every edit was
restored byte for byte (checked with `cmp` against saved copies), and
`git status --porcelain` and `git diff --stat` were empty at the end. The
restored `P4bloIR.DeviationLaws` and `ProofAudit` were rebuilt with exit 0.

## Summary

The 39 theorems are about the production definitions. All of them build
with no `sorry`, no `native_decide` and no `unsafe`, and each premise can be
met: I built a concrete instance for every theorem. `ProofAudit.lean`
covers exactly the 39 public theorems, and each uses only `propext`,
`Classical.choice` and `Quot.sound`. Three of the builder's mutants
reproduce as semantic proof failures at the named theorems. There are no
confirmed defects in the proofs.

The main weakness is that several statements are relative to other
production helpers, and the theorems do not pin those helpers down. Three
of my own mutants survive the whole module:

- `prefixLength` returning 0 (the LPM table then picks the first matching
  entry installed, not the longest prefix).
- `keyValueMatches` accepting every LPM key.
- `equalList` ignoring field values.

With each of these mutants, the text in the ledger and in `docs/assurance.md`
("longest prefix wins", "compares the fields") is false, yet every theorem
still holds. Four other points:

- The test module overstates its coverage of premises.
- Four ledger entries classed *refines undefined* have no theorem, which
  conflicts with the C4 brief and the merge subject.
- `ASSURANCE.md` calls `rank` "independently defined", but `rank` is built
  on `Installed.prefixLength`.
- One assurance row claims an induction that is not stated as a theorem.

## Confirmed defects (with reproducers)

None in the proofs or the audits. The documentation overclaims are listed
under Documentation.

## Statements weaker than their entries

1. **LPM: "longest prefix wins" depends on the production `prefixLength`.**
   The theorems are `lookup_hit` (`DeviationLaws.lean:733`) and
   `lookup_longest_prefix` (`:780`), both through `rank` (`:616`).
   - **Reproducer (mutant D):** in `Tables.lean:102`, change
     `| .lpm _ len => n + len` to `| .lpm _ _ => n`.
   - **Result:** `lake build P4bloIR.DeviationLaws` exits 0.
   - **Why it survives:** every entry now has rank 0, so the bound
     `rank e' ≤ rank e` is trivially true. `beats` is never true, and the
     lookup returns the first matching entry installed.
   - **Consequence:** the ledger's LPM prose and the `assurance.md` row
     ("with the longest total prefix") are only as good as `prefixLength`,
     and nothing proves that function.
   - **Suggested fix:** a one-line law such as
     `prefixLength {keys := ks, ..} = Σ lpm lengths`, or at least one on a
     single-`lpm`-key entry, e.g.
     `prefixLength ⟨[.exact a, .lpm v l], _, _⟩ = l`.

2. **LPM: "whose prefix covers the key value" depends on the production
   `keyValueMatches`.** `Matches` (`:611`) is defined with
   `Installed.keyValueMatches`.
   - **Reproducer (mutant E):** in `Tables.lean:95-97`, replace the LPM arm
     with `| .lpm _ _ => true`.
   - **Result:** the build exits 0. `lookup_hit`, `lookup_miss` and
     `lookup_longest_prefix` all still hold.
   - **Also:** `Matches` uses `zip`, so if an entry has fewer keys than the
     lookup key, the extra key positions are never checked. That matches
     production behaviour, but nothing states it.
   - **Suggested fix:** a law for the LPM arm, e.g.
     `keyValueMatches (.lpm v l) k = (k.value >>> (k.width - l) == v >>> (k.width - l))`
     stated against an independent description.

3. **Header equality on two valid headers depends on `equalList`.**
   `header_equal_valid` (`:75`) only says the result is `Value.equalList fa fb`.
   - **Reproducer (mutant G):** in `Value.lean:166`, change the cons arm to
     `| _ :: xs, _ :: ys => equalList xs ys`.
   - **Result:** the build exits 0.
   - **Consequence:** the docstring's "equal exactly when their fields are,
     fieldwise" and the ledger's "compares the fields" are not what the
     theorem proves. Fix: add
     `equalList (x :: xs) (y :: ys) = (equal x y && equalList xs ys)`, and
     the empty cases.

4. **`!=` is not covered.** Everything is stated for `.eq`. The `.ne` arm
   of `evaluate` (`Eval.lean`) could negate something else, e.g. drop the
   `!`, and no deviation theorem would notice. The Header equality entry
   is about `==`, but the Comparison entry defines both.

5. **Parser loop bound.**
   - As disclosed, reaching a revisit is not proved.
   - Beyond that, the ledger's sentence "Sub-parser states count as states
     of the enclosing run, so a sub-parser applied twice without consumption
     in between is a timeout" has no theorem.
   - The ledger's "as long as the cursor advanced" is implemented and proved
     as "the cursor differs from the recorded one" (`enterState_first`,
     `:559`). The two agree only if the cursor never moves backwards, which
     is not stated.
   - What is proved does match the implementation, including a revisit
     through a second state: I checked A, then B, then A at one cursor as a
     composition of `enterState_first`, `enterState_first` and
     `enterState_revisit`.

6. **`lastIndex_empty` and `lastIndex_nonempty` (`:292`, `:299`) are pure
   arithmetic on `Bits.wrap`.** No evaluator mutant can kill them. Their
   force comes only through `evaluate_lastIndex` (`:282`), which restates the
   definition's expression `Bits.wrap 32 (next + 2^32 - 1)` directly.
   Together they are correct. On its own, `evaluate_lastIndex` would also
   reject a harmless rewrite of the definition.

7. **Zero values.** Only bits, boolean, error and a one-level header whose
   fields are all bits or boolean are covered. The ledger's "first member
   for enums" and "recursively zero value … for compound types" are not.
   The assurance row says so ("Zero enums, structs and stacks beyond their
   header elements"), so this is disclosed and not a defect.

8. **Push/pop are laws on stack values only.** They do not go through the
   statement's write-back, and the pop laws assume `next ≤ S`. Both points
   are disclosed and match the statements.

## Vacuity checks

Every instance below was checked by
`lake env lean rv-devlaws/Instances.lean` and `rv-devlaws/Lpm.lean`
(scratch files, exit 0). Each discharges the theorem's premises as stated,
not a special case of them. "Test" means the repository's
`spec/ir/Tests/DeviationLaws.lean` already has a theorem-level instance.
Only 5 of the 39 theorems have one; see Documentation, item 1.

| Theorem | Premise instance | Verdict |
|---|---|---|
| `header_equal_*` (4) | no premises | non-vacuous. Survivor G shows the valid case is relative to `equalList` |
| `evaluate_eq`, `evaluate_eq_invalid_headers`, `evaluate_eq_valid_invalid` | Test: `x == y` and `v == x` read from variables | inhabited |
| `zeroHeader_eq` | `index` with `H = {a: bit<8>, f: bool}`, giving `hz` | inhabited |
| `zero_bits`, `zero_boolean`, `zero_error` | no premises, `rfl` | fine |
| `elementOf_out_of_range`, `evaluate_index_out_of_range` | Test: `hs[5]` on a 2-element stack | inhabited |
| `readLValue_index_out_of_range` | mine: `readLValue (.var "hs")`, index `5`, `nextIndex 1` | inhabited |
| `writeLValue_index_out_of_range` | mine: write `.bool true` (not a header) to `hs[5]` | inhabited |
| `writeLValue_member_out_of_range` | mine: `hs[5].a := 7`, `fieldIndex? "H" "a" = some 0` | inhabited |
| `evaluate_lastIndex`, `evaluate_last_empty` | Test: `nextIndex 0` | inhabited |
| `evaluate_last_nonempty`, `lastIndex_nonempty` | mine: `nextIndex 1` of 2 elements | inhabited |
| `pushFront_spec`, `pushFront_clamp`, `popFront_spec`, `popFront_clamp`, `*_eq` | mine: `hz` from `zeroHeader_eq`; `n = 1` and `n = 5`, `next = 1` | inhabited |
| `evaluate_shl_large`, `evaluate_shr_large` | mine: `bit<8> 3 << bit<32> 9`, `>> 3000` (above 2048) | inhabited |
| `write_fits`, `toBytes_padded` | mine: empty emitter, write 12 bits `0xabc` | inhabited |
| `enterState_revisit` | Test: visits `("", "loop") ↦ 8`, cursor 8 | inhabited |
| `enterState_first`, `enterState_again` | mine: empty visits; `h` supplied by `enterState_first` | inhabited |
| `step_state_revisit` | mine: `default` scope, work `[state loop]`, recorded cursor 8 | inhabited |
| `lookup_hit`, `lookup_longest_prefix` | mine: table `c.t` with one `lpm` key, entries `10/8 → short` and `10.1/16 → long`, key `10.1.2.3`; lookup computed by `rfl` to hit `long` | inhabited, with two matching entries of different lengths |
| `lookup_miss` | mine: same table, key `11.0.0.0`, which misses | inhabited |

Survivor mutants (all semantic, all with build exit 0):

| Mutant | Theorems it survives |
|---|---|
| D `prefixLength ≡ 0` | `lookup_hit`, `lookup_longest_prefix`, `lookup_miss` |
| E LPM `keyValueMatches ≡ true` | the same three |
| G `equalList` ignores field values | `header_equal_valid` and all `evaluate_eq*` |

Candidates I reasoned about that do **not** survive:

- `equal` comparing type names: fails `header_equal_invalid`, whose `s, t`
  are arbitrary.
- An out-of-range write that writes back the unchanged stack: fails
  `writeLValue_index_out_of_range`, which requires the exact run.
- `enterState` keyed on state name only, ignoring the block.
- `enterState` timing out on any earlier visit, whatever the cursor: fails
  `enterState_first`.
- `push_front` using the zero of another type.
- `beats` with `≥`: killed, but only by the private `beats_iff`, not by
  any public statement.

One survivor was not tested: changing `natToBytes` and `bytesToNat` to the
same byte order together, both production code, would leave
`toBytes_padded` true as stated. Existing lemmas in `Theorems` would
probably reject it first.

## Mutation results

Each mutant was applied alone by a script that replaces an anchor asserted
to occur exactly once. The build was `lake build P4bloIR.DeviationLaws`,
followed by a restore and a `cmp`. Logs are in the scratchpad at
`rv-devlaws/mut-*.log`.

| # | Mutant | Source | Build | First failure | Kind |
|---|---|---|---|---|---|
| A | `Value.equal` header arm `if va != vb then false else equalList fa fb` | builder #1 | exit 1 | `DeviationLaws.lean:52:68` unsolved goals, `header_equal_invalid` | semantic |
| B | `popFront` nextIndex `size - n`, binder `_nextIndex` | builder #7 | exit 1 | `:410:2` `rfl` failed, `popFront_eq` | semantic |
| C | `beats` prefix comparison `<` | builder #9 | exit 1 | `:620:76` unsolved goals, private `beats_iff` | semantic |
| D | `prefixLength` counts nothing | mine | exit 0 | none | survivor (Statements item 1) |
| E | LPM `keyValueMatches` always true | mine | exit 0 | none | survivor (item 2) |
| G | `equalList` cons arm drops `equal x y` | mine | exit 0 | none | survivor (item 3) |

A, B and C match the builder's report exactly. None of the failures is a
lint.

## Documentation

1. **`spec/ir/Tests/DeviationLaws.lean:5-7` overclaims.** It says "Concrete
   runs that meet the premises of the deviation laws, so that none of them
   is vacuous". Only five theorems are instantiated at theorem level
   (lines 55-76). Push/pop and the emitter are checked only by executable
   `check`s, which do not discharge the premises. The other ~30 theorems
   have no instance. All premises are in fact inhabited (the table above),
   so the fix is to add instances or narrow the sentence. The scratch
   instances can be copied from `rv-devlaws/Instances.lean` and `Lpm.lean`.

2. **Four ledger entries classed *refines undefined* have no theorem, and
   nothing records their exclusion.** The entries are: Host entries are
   canonical (`ir-semantics.md` about line 619), Entries name their action
   (about 640), Binding (about 715) and Where an implementation closes
   something (about 745). This conflicts with:
   - C4 in the plan: "for every *refines undefined* and *deviates* entry";
   - the merge subject "laws for every closed behavior";
   - the opening of `impl/lean/ASSURANCE.md`'s new section: "on the cases
     the ledger classes as *deviates* or *refines undefined*".

   Binding and the extern-model entries arguably belong to `spec/arch`, and
   the two installation rules are validation, not evaluation. Either way,
   the exclusion should be recorded in `.agents/decisions.md`, or C4 marked
   as covering ten of fourteen entries.

3. **`impl/lean/ASSURANCE.md`, mutant 9** says `beats_iff` "ties `beats` to
   the independently defined `rank` of `lookup_hit`". `rank` is independent
   of `beats`, but not of `prefixLength`, as survivor D shows. Suggest
   "defined without `beats`".

4. **`docs/assurance.md`, `DeviationLaws.toBytes_padded, write_fits` row**
   says "for every emitter built by fitting writes". `write_fits` is a
   single step, and the induction is only described in its docstring. It is
   true and a short proof, but not a stated theorem. Either state it
   (a `List.foldl` of fitting writes from `{}`) or say "one fitting write
   at a time preserves the premise".

5. **`docs/assurance.md`, lookup row.** The claim "matching every key with
   the longest total prefix" should say, under "does not establish", that
   `keyValueMatches` and `prefixLength` are used, not specified.

6. **`docs/assurance.md`, lastIndex row.** "element `nextIndex - 1`
   otherwise" needs `1 ≤ nextIndex ≤ size` and a stack evaluation that
   leaves the run unchanged. Both are premises of `evaluate_last_nonempty`.
   It is minor, but "otherwise" reads as "for every non-zero `nextIndex`".

7. **Assurance rows omit some theorem names.** `evaluate_eq`,
   `header_equal_invalid_valid`, `evaluate_eq_valid_invalid`,
   `elementOf_out_of_range`, `readLValue_index_out_of_range`,
   `lastIndex_nonempty`, `pushFront_eq`, `popFront_eq`, `wrap_zero_value`
   and `enterState_first` are not named in any row. They are all in
   `ProofAudit.lean`, so this is cosmetic.

8. **Docstrings** all open with a plain one-sentence claim. The exception
   is `header_equal_valid`, whose "fieldwise" is more than it proves (item
   3 above). The "does not establish" sentences otherwise match the
   statements.

9. **The `Lean:` lines in the ledger** cite theorems that exist and state
   what their entries say, apart from the gaps under "Statements weaker".
   `e2c6ec1` correctly adds `lookup_hit` to the Ternary entry and
   `lookup_miss` to the default-action entry.

## Anything else

- **Audit:** the set of `^theorem` names in `DeviationLaws.lean` equals the
  set of `#print axioms P4bloIR.DeviationLaws.*` in `ProofAudit.lean`
  (`diff` is empty; 39 each). `ProofAudit` is a default Lake target, and
  it rebuilt with exit 0 after the restore.
- **`decide`** appears only in the tests, on `2 ≤ 5` and `2 < 2^32`. `rfl`
  on `zero_*` unfolds one `zeroWith` step. Nothing hides a large
  computation.
- **Base commit:** `ASSURANCE.md` names `103649e`, which is an ancestor of
  `662746e`.
