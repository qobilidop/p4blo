# Review: A4, single-block execution on P4-SpecTec

Commit reviewed: `b5c40ff` (merge of `work/single-block`, tip `da0ba7f`, five
commits on `8c674fc`). Date: 2026-09-24. Reviewer: independent, read-only.
Everything was run in `/Users/qobilidop/my/work/p4blo-wt/single-block` with
`P4BLO_ORACLE_DIR=/Users/qobilidop/.cache/p4blo/p4-spectec-single-block`.
Neither tree was modified. Scratch scripts are `rv_*.py` in the
reviewer's scratchpad.

## Summary

The runner does what it claims. The comparison works at the level of
SpecTec's architecture-free rules. `p4blo.watsup` mirrors
`9.A-v1model.watsup` rule for rule without `standard_metadata`, and it calls
each block through the same `Stmt_eval` of `main.<b>.apply(...)` that
V1Model uses. The semantics being judged is therefore
`Call_eval/parserApplyMethodCallee` and `controlApplyMethodCallee` with
`Copy_in`/`Copy_out`. The patch changes no existing behavior. The checkout
equals the pin plus the patch, byte for byte. The baseline result is 55
passed and 3 strict xfails in 34 s.

The weak point is the stack-invalidation classifier. It accepts every
`next_index` difference on its vector, and a real `push_front` bug slips
through it (reproducer below). The CRC classifier cannot hide a register
bug, but it hides any bug in the Python CRC binding's handling of odd-byte
CRC32. The JSON boundary is faithful for every well-typed value, including
stacks whose `nextIndex` differs from the valid count and invalid headers
that carry fields. On the OCaml side it does not validate input. State is
refused across sessions but not across programs.

## Confirmed defects

1. **The stack classifier hides a wrong `nextIndex` after `push_front`.**
   `tests/test_oracle_block.py:228-230` tags every `next_index` difference
   `STACK_INDEX`, and lines 463-464 accept a vector whose findings are all
   tagged. The ledger's deviation is narrower: SpecTec pops to `S - n`,
   while push is P4's `min(nextIndex + n, S)` on both sides
   (`docs/ir-semantics.md` ~line 300-312).
   Reproducer: `rv_mutants.py` with `RV_MUTANT=push`, which replaces
   `p4blo.interp.stmt.push_front` with a version that does not advance
   `next_index`. It runs as a pytest plugin:
   `nix develop -c env RV_MUTANT=push PYTHONPATH=<scratch> P4BLO_ORACLE_DIR=... uv run pytest -p rv_mutants tests/test_oracle_block.py`.
   Result: **the whole file passes** (18 passed, 3 xfailed among the vector
   tests, exit 0). On `stacks/header-stack-ops-bmv2.stf` the mutant adds 4
   genuine findings, all absorbed by the tag, for example
   `line 66 control headers.h2.next_index python 1 spectec 2`. The baseline
   has only the 2 pop findings. `tests/test_interp_control.py` catches this
   mutant, but the block comparison does not.
   Fix: use the approach the CRC classifier already uses. Rerun the vector
   with a Python model of the deviation (`$invalidate_value` keeps fields,
   pop gives `S - n`) and require zero findings. Alternatively, accept a
   `next_index` difference only when SpecTec's value is `S - n` right after
   a pop.
2. **Extern state is not bound to a program.** `pipe.ml:692-709`
   (`import_state`) checks only the session tag. Reproducer (`rv_state.py`):
   take the `state` from a `stateful` control reply (register `main.c.r`,
   256 cells of `bit<8>`), rename its object to `register_bounds`'s
   `main.c.r` (4 cells of `bit<32>`), and send it with a `register_bounds`
   parser request in the same session. It is **accepted**, and the reply
   shows `r` with 256 `bit<8>` cells. An object whose JSON is garbage
   (`{"garbage": 1}`) is also accepted at import. `observe_externs`
   (`pipe.ml:647-672`, `| _ -> None`) then silently drops that object from
   `externs`. The test harness never does either of these, so no reported
   result is affected, but README "The block runner" says state "belongs to
   the process that produced it", and that promise is weaker than it reads.
   Fix: put the program path or its digest in the state. Also fail when an
   object's state does not parse as `object_state`.
3. **`of_json` accepts values outside their type.** Reproducer
   (`rv_boundary.py`, raw requests on `stacks`), all of which are accepted
   and echoed back:
   - `next_index` 7 on a 5-deep stack;
   - `next_index` -1, which is built with `Value.Make.nat`;
   - `"value": "300"` for a `bit<8>` field;
   - a header whose `type` is `"bogus_t"`, which comes back as `h3_t`
     because the type is taken from the template.

   The cause is `pipe.ml:232-243` (bits width is checked, but the range is
   not), 259-269 (the header's `type` is ignored), 270-275 (the struct's
   `type` is ignored) and 276-291 (`next_index` is unchecked). `to_json` in
   `block.py` never produces such values, so the comparison is unaffected.
   A third client could still get ill-formed IL values without an error.

## Architectural decisions the p4blo architecture makes

| Decision | Where documented |
|---|---|
| One block per request, and the caller chains blocks | README "The block runner"; `pipe.ml` header; `p4blo.p4` header |
| `hdr`/`meta` are recreated with `Var_init` (`$default`) on every request, then overwritten from the request (a parser's `hdr` is never written: it is `out`) | The `$default` of an `out` parameter is in the ledger (~line 178). That the parser's `hdr` global is not taken from the request is **undocumented** (harmless) |
| Parser metadata input is zero plus `ingress_port`. The control gets `parser_error` written in between | `tests/test_oracle_block.py` docstring; README ("chained as the switch chains them") |
| On reject, `hdr`/`meta` after copy-out are returned with `accepted: false` and the `REJECT` error | README lists the outputs; the copy-out itself is a §8 rule |
| On accept, `error` is the constant `NoError`, not read from the spec (`pipe.ml:819-822`) | **undocumented** |
| `consumed_bits` is `packet_in.idx`; the rest of the packet (payload) is not modelled | README (outputs) |
| Deparser bytes are zero-padded to a byte; `bits` is returned but never compared (`test_oracle_block.py:407`) | Padding: README. That `bits` is not compared: **undocumented** |
| Extern families and their initial state are V1Model's OCaml code (`Register.init`, `Counter.init`, `Func.hash`, `Core.Func.verify`) | README, assurance paragraph, decision |
| Counter byte counts would use the request's own packet (empty for control and deparser). All printed counters are `packets`, so this is moot | **undocumented** (moot today) |
| Entries are reinstalled on every request from STF text through `run.translate`. V1Model's `transform_stf_stmt` (block-name rewrite, `$valid$` → `isValid()`) is **not** applied (`pipe.ml:363`, `Fun.id`) | Translation: README and decision. The missing `transform_stf_stmt`: **undocumented**; see Anything else |
| Per-request order: import state, install entries, `packet_in`, `packet_out`, globals, write arguments | **undocumented** (not observable with today's externs) |
| An extern state of `null` is the program's post-instantiation state | README (`state ... or null`) |

## Boundary faithfulness

A round trip through a real control and deparser (`rv_boundary.py`,
`stacks`) used a stack with `next_index = 3`, only elements 0 and 4 valid,
invalid elements carrying non-zero fields, and invalid `h1`/`h3` carrying
fields. The values came back unchanged. SpecTec's control output equals
Python's. The deparser emitted `0210200902142409` (64 bits) on both sides,
so only valid elements were emitted. This matches the ledger entries "reading
a field of an invalid header" and "emit of an invalid header". Enums and
errors (`rv_enum.py`: forwarder plus an `enum Color` and an `error` field
added to metadata) also round-trip, and SpecTec agrees with Python. No corpus
program declares an enum, so this path is untested by the suite. Booleans
are covered by the forwarder's `drop`. Struct fields are matched by name, so
reordered JSON is accepted, which is not lossy. Nothing is lost for
well-typed values. The only lossiness is the unchecked input listed under
defect 3, plus `observe_spectec`'s fallback `int(bool(value))` for a
non-bits register cell (`test_oracle_block.py:296`), which is unreachable
today.

## Classifier analysis

- **Stack invalidation: can hide a real bug.** See defect 1. The
  `STACK_FIELD` tag also absorbs any difference in an element that is
  invalid on both sides, whatever caused it. A `setInvalid`-clears-fields
  mutant (`RV_MUTANT=inv`) happened not to change this vector's outputs,
  and `vlan_gateway/gateway.stf` caught it. The tag is still broader than
  the ledger entry. Only elements vacated by push or pop should qualify.
- **Padded CRC32: cannot hide a register bug, but can hide a CRC-binding
  bug.** The modeled rerun must give zero findings. A register mutant
  (`RV_MUTANT=reg`, writes to index ≥ 2 land on `index ^ 1`) fails both
  firewall vectors with "DIVERGENCE beyond the padded-CRC32 model", as well
  as `register_bounds/bounds.stf` and `firewall/pinhole.stf`.
  `PaddedCRC32.call` (`test_oracle_block.py:313-320`), however, discards
  `CRC.call`'s result for odd-byte widths and recomputes
  `crc32(b"\0" + payload)` itself. A mutant confined to `CRC.call` on
  odd-byte CRC32 (`RV_MUTANT=crc`, which hashes the reversed payload)
  therefore **passes the whole file**: the modeled run has 0 findings.
  `tests/test_crc.py::test_dynamic_authoring_execution_and_observation`
  catches it. Fix: before replacing the result, assert that it equals
  `crc32(payload)`, so the model changes only the padding and still checks
  the binding.

## Build and patch

- The checkout at `~/.cache/p4blo/p4-spectec-single-block` is the pin
  `2730cfd` plus exactly the patch. Its tracked diff plus the new files has
  the same `+`/`-` lines as `0001-p4blo-block-architecture.patch` (1221
  lines each). The stamp `2730cfd… c40e195b…` equals a recomputed digest.
- `build.sh` runs under `set -euo pipefail`. `git apply` (line 101) fails
  the build on a bad patch, and the stamp has already been removed (line 97
  or so), so an unpatched tree is never stamped. The digest covers each
  patch's name and content (line 61), and the CI cache key includes
  `tests/oracle/patches/**`.
- Line 99 cleans untracked files only under `p4spec/`. A stray untracked
  file in `spec/` (the directory every oracle elaborates) would survive
  into a "pin + patch" build. This is minor: use `git clean -fdx`
  excluding `_build`, `p4c` and the binary, or at least clean `spec` too.
- The `sim` path is unchanged. `build.ml` gains one match arm, and the
  functor is applied only in that arm. `main.ml` gains one command.
  `p4blo.watsup` lives outside `spec/` and is passed only to `block`. No
  existing behavior changes.
- `BlockOracle.missing()` (`block.py:136`) checks that `p4blo.watsup`
  exists, but not the stamp's patch digest. A checkout built from an older
  patch and pointed to by `P4BLO_ORACLE_DIR`/`BIN` is used silently.

## Sensitivity

The vector tests (`-k blocks_agree`) were run under five monkeypatched
mutants loaded as a pytest plugin. The worktree was not edited.

| Mutant | Caught by |
|---|---|
| `sub`: `a - b - 1` (the builder's) | forwarder/forward, forwarder/lpm_precedence, tutorial_firewall/collisions, tutorial_firewall/connection (beyond the model), load_balancer/dispatch, router/route: **6** |
| `perr`: the parser always reports `NoError` (the builder's) | forwarder/too_short, parser_error, verify_error/issue1824, vlan_gateway/gateway, load_balancer/dispatch, router/route: **6** |
| `reg`: register write to `index ^ 1` for index ≥ 2 | register_bounds/bounds, tutorial_firewall ×2, firewall/pinhole: **4** |
| `push`: `push_front` leaves `nextIndex` | **none** (hidden by the stack classifier) |
| `crc`: odd-byte CRC32 binding hashes the reversed payload | **none** (hidden by the padding model) |

README line 408 says the builder's two mutants were caught by "four and
six" vectors. Here both were caught by six. The difference is probably in
the exact mutant, but the sentence should name which mutant got which count.

## Cleanup requests

- `test_oracle_block.py:286-300`: `observe_spectec` keys objects by their
  last name component. Two instances with the same IR name in different
  blocks would collide silently. Assert that the keys are unique, and raise
  instead of using the `int(bool(...))` fallback.
- `test_oracle_block.py:238-242`: `_NAMES` is a module-global cache keyed
  by type name and shared across programs. It is correct only because
  `compare_vector` refills it first. Pass the index instead.
- Compare the deparser's `bits` with the bit count Python emits, or say in
  the README that sub-byte emission is not compared.
- `main.ml` `block_command`: `let* _ = P4spectec.build_sim ...` exists only
  for the side effect of setting `Pipe.server` (`pipe.ml:42-49, 894`).
  Say so in a comment, or return the server from the module.
- The `block` command has no `-trace` flag. A6 (localization) will need
  one.
- Document the accept → `NoError` constant and the per-request
  initialization order in the README's block-runner section.

## Anything else

- The p4blo architecture uses `transform_stf_stmt = Fun.id` and does not
  reuse V1Model's STF rewrites. Tables resolve today through `Table.find_table`'s
  unqualified fallback (`MyIngress.ipv4_lpm` becomes `ipv4_lpm`). A table
  name used in two blocks (which the STF convention qualifies), or a
  `$valid$` key name, would behave differently on the block runner than on
  the pipeline runner. No corpus program has either (checked with
  `rv_dups.py`), so this is latent.
- `test_oracle_block.py` claims to chain blocks "as the switch chains
  them", but `Switch.run` drops a packet whose parser consumed a non-whole
  number of bytes before running the control. The harness runs the control
  anyway. Both sides get the same inputs, so nothing is hidden, but the
  sentence overstates it.
- Extern state carries the spec's source regions (absolute paths into the
  checkout) inside every register cell's type. This makes the state large
  and ties it to the machine. It is harmless with the session tag.
- Readability is good overall. `pipe.ml` explains its value table and its
  STF encoding copy (verified identical to `make.ml`'s `run_stf_stmt`,
  including `String.escaped` only on `add`), and `block.py` states the
  protocol in one place.
