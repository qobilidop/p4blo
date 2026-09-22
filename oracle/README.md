# The oracle

Claim 2 of [design.md](../docs/design.md#the-four-claims): the corpus
programs, printed to P4 under the v1model shim, match the reference
interpreter packet for packet on an external oracle. The oracle is
[P4-SpecTec](https://github.com/kaist-plrg/p4-spectec)'s simulator, the
P4 specification's own mechanization, driven through its `sim` command
on the same STF vectors `python/p4blo/stf.py` replays on the Python
interpreter. It is built by `oracle/build.sh`, driven by `oracle/run.py`,
and asserted by `tests/test_oracle.py`, which skips without a binary and
runs in its own CI job, `.github/workflows/oracle.yml`, because the
OCaml toolchain is heavy and only the oracle needs it.

| | |
|---|---|
| Pinned commit | `2730cfd9e74048bb5439da0f8afcef124079a064` (2026-09-22, "Merge pull request #320 from kaist-plrg/fix-batch-1") |
| Its p4c submodule | `6b7ec98e77dfc71c6e1309d9a76183cb31f35a8a`, of which only `p4include/` is fetched |
| Toolchain | OCaml 5.1.0 through opam, the package set at the top of `build.sh` |
| Architecture | `v1model`; the shim is `printer.standard_metadata_binding` |

The pin lives in one place, `P4_SPECTEC_COMMIT` in `build.sh`; the CI
cache key reads it from there.

## Building

`build.sh` clones the pinned commit into `$P4BLO_ORACLE_DIR` (default
`~/.cache/p4blo/p4-spectec`), fetches `p4c/p4include` at the submodule's
pin, creates the opam switch, installs the packages, runs `make build`
as the upstream README says, stamps the result with the commit, and
prints the path of the `p4spectec` binary. Every step checks its own
result first, so rerunning it is cheap and a partial failure resumes
where it stopped.

It needs `git`, `make`, a C compiler, `opam` 2.1 or newer, and libgmp's
headers plus `pkgconf`, which the opam packages under `bignum` probe
for. opam is deliberately not in the flake (design.md, "Testing
strategy"), so:

```
# Ubuntu (what CI does)
sudo apt-get install -y opam libgmp-dev pkg-config
oracle/build.sh

# With Nix, on Linux or macOS
nix-shell -p opam gmp pkgconf --run oracle/build.sh
```

opam's root defaults to `~/.opam`; set `OPAMROOT` to put it elsewhere.
Under Nix the binary links against the Nix store's libgmp, so it keeps
working as long as that path is not garbage-collected. The first build
compiles OCaml and Jane Street's `core`; on an M-series Mac it took
about six minutes: two for the switch, two for the packages, two for
`make build`. A rerun with the stamp in place returns in milliseconds.

## Running

```
uv run python oracle/run.py corpus/forwarder/forwarder.txtpb corpus/forwarder/*.stf
uv run pytest tests/test_oracle.py -v
```

`run.py` finds the binary through `$P4BLO_ORACLE_BIN`, else
`$P4BLO_ORACLE_DIR/p4spectec`, else the default directory above, and
takes the spec (`spec/`) and the include directory (`p4c/p4include/`)
from the checkout the binary sits in. For each vector file it prints the
program with `print_program` into a temporary directory, translates the
vector (below), and runs, from the checkout,

```
p4spectec sim spec -arch v1model -i p4c/p4include -p <program>.p4 -stf <vector>.stf
```

The simulator prints `[PASS] Transmitted (<port>) <hex>` for every
expectation it matched and `passed` at the end, exit 0. `run.py` reports
one verdict per vector:

- **pass**: every expectation matched, nothing left over.
- **fail**: a divergence. The simulator says `expected (<port>) <hex> but
  got (<port>) <hex>` when an output on the expected port differs, and
  at the end of the file `[FAIL] Remaining packets to be matched` for
  output nobody expected and `[FAIL] Expected packets to be output` for
  an expectation nothing satisfied.
- **error**: the oracle could not judge: a syntax error in the printed
  program or the vector, a construct the simulator does not support, a
  crash, a timeout. Reported as a failure too, labeled, because it
  leaves the claim unchecked, but it is not a disagreement.

The process exits non-zero on anything but pass and prints the exact
command for the first vector that did not pass. `tests/test_oracle.py`
is parametrized over every `corpus/*/*.stf` and fails with `DIVERGENCE`
or `ORACLE ERROR (not a divergence)` in the message, so a red CI run
says which it was.

## The STF dialect

p4blo's vectors (documented in `python/p4blo/stf.py`) are a subset of
p4c's STF, and the simulator's grammar (`p4spec/lib/stf/parser.mly`)
parses all of it: bare or qualified table and action names, dotted key
names such as `hdr.ipv4.dstAddr`, `*` nibbles in `expect`, `$` for an
exact length, `wait`, comments. Its runner, though, gives three things
a meaning of its own, found by running the forwarder's vectors as they
are (`miss`, `non_ipv4` and `too_short` passed; `forward` and
`lpm_precedence` did not). `run.py` therefore re-renders every `add`
and `setdefault` line from its parsed form, resolved against the
program, and passes everything else through verbatim:

- **`no_packet` is dropped.** The simulator parses it but its runner
  rejects it as "not yet supported". Its end-of-file check flags any
  output that no `expect` claimed, which is exactly what `no_packet`
  asserts here (an unexpected output would surface as `[FAIL] Remaining
  packets to be matched`), so the assertion survives without the line.
- **lpm prefixes become wildcards at the key's full width.** An lpm
  value written `value/len`, p4c's full-width value with a prefix
  length, is read by the spec's `_SLASH` rule
  (`spec/9-arch/9.1-table-interface.watsup`) with its bytes reversed
  and shifted up by the remaining width; that fits exactly one p4c
  vector, `lpm_ebpf.stf`'s `0x010a/16` on a little-endian address, and
  makes `0x0a000200/24` miss. The wildcard forms are read as p4c's
  `makeLpm` normalizes them, so `0x0a000200/24` is rendered
  `0x0a0002**`, and a prefix that is not nibble-aligned in binary,
  `0b0000101000000000000000**********` for `/22`. The width is the
  key's, taken from the program, because the simulator casts value and
  mask to the key type and a shorter mask would zero-extend.
- **lpm entries get their prefix length as priority.** The spec has no
  longest-prefix rule: an lpm entry is matched like a ternary one, and
  when several entries match, `$select_action`
  (`spec/8-dynamic/8.09.1-eval-control-table.watsup`) sorts the matches
  by priority and takes the largest (unless the table sets
  `largest_priority_wins = false`), failing with "relation
  V1Model_ingress failed ... function select_action failed" when any
  match has no priority. Checked: with the priorities swapped against
  the prefix lengths, the shorter prefix won. So on a table with an lpm
  key and no ternary key, `run.py` writes the prefix length as the
  entry's priority, which is also what p4testgen's vectors do. This
  means the oracle confirms the forwarder's outputs but does not
  independently check the longest-prefix rule of `docs/semantics.md`;
  the translation supplies it. BMv2, whose lpm tables are real, would.
- **Action arguments are written in decimal** and key values at full
  width in hex, or binary where a ternary mask is not nibble-aligned;
  the simulator reads all three radixes.

`run.py` prints a note for each line it changed, and
`tests/test_oracle.py` pins the rendering.

The comparison semantics differ slightly and are worth knowing. p4blo
matches a packet's outputs to the `expect` lines that follow it, in
order; the simulator keeps one queue of unclaimed outputs and one of
unmet expectations, matched by port as they arrive, and only fails at
the end of the file on what is left. The vectors here have at most one
output per packet, so the two agree; a vector relying on the order of
several outputs from one packet would be checked less strictly by the
oracle than by p4blo.

Dropping `no_packet` opens a gap of the same kind, in theory. Because
the simulator matches by port from one queue of unclaimed outputs as
expectations arrive, a vector of the shape `packet A; no_packet; packet
B; expect 1 X` passes on the oracle when A wrongly emits X on port 1 and
B emits nothing: the stray output of A is claimed by the expectation
written for B, and nothing is left over at the end of the file. p4blo
fails the same vector at the `no_packet`. No corpus vector has that
shape: the one `no_packet` in the corpus, in `forwarder/miss.stf`, is
in a single-packet file, where the end-of-file check is exact. A
future vector could have it, and a stray output that happens to equal
a later expectation is unlikely rather than impossible. It is
accepted for now because the alternative, a translation that also
asserts ordering with an `expect` after each `packet` for whatever
p4blo produced, would make the oracle judge p4blo's outputs rather
than the vector's; the differential sweep against Lean checks whole
outputs per packet and has no such gap.

## Results

2026-09-22, at the pinned commit, on the five forwarder vectors: all
pass. Each `sim` run takes well under a second on an M-series Mac,
spec elaboration included; the whole `tests/test_oracle.py` runs in
about four seconds.

## Known gaps of the shim and the simulator

- **Checksums.** The forwarder's vectors carry an IPv4 header checksum
  that is deliberately wrong (the checksum extern is deferred;
  `corpus/forwarder/README.md`). The shim prints empty
  `MyVerifyChecksum` and `MyComputeChecksum` controls, so the simulator
  neither checks nor recomputes it: it carried the field through
  unchanged and matched the expected output, exactly as the reference
  interpreter does. It did not drop or reject the packets, so nothing
  about the vectors has to change on the oracle's account; when the
  checksum extern lands, both sides will change together.
- **Const lpm entries.** The printer writes a table's `const entries`
  for an lpm key as `value &&& mask` without priorities. Given the
  tie-breaking above, a packet that matches two such entries would make
  the simulator fail the same way `lpm_precedence` first did. No corpus
  program has const lpm entries yet; when one does, the printer will
  have to print `priority = <prefix length>` on them (the printer is
  outside this directory's scope).
- **Flood.** The metadata contract's `flood` has no v1model mapping and
  is not checked by the oracle (design.md, "Risks").
- **Registers from STF.** The simulator's v1model backend rejects
  `register_read`, `register_write` and `register_reset` ("not
  implemented for the v1model simulator"); p4blo's dialect has none, so
  a stateful program's register state can only be observed through
  packets.
- **Ternary priorities.** The simulator takes the `add` priority with
  larger winning, the convention `docs/semantics.md` fixed and the one
  p4c's runner has; unverified on a real ternary table until the acl
  program lands.
- **Unchecked constructs.** Only what the forwarder uses has been run:
  extract, select, lpm table with action data, `mark_to_drop`,
  `egress_spec`, emit of a valid and of an invalid header, a parser
  rejection with `PacketTooShort`. Header stacks, `verify`, registers,
  counters and the `hash`-based checksum are exercised when their corpus
  programs arrive; an unsupported construct shows up as an `error`
  verdict, labeled `ORACLE ERROR` by the test.
- **A harmless warning.** Every run prints
  `warning[elab/dec-missing-clauses]: function `sink` has no clauses
  defined` from the spec itself; `run.py` ignores it and it does not
  affect the verdict.
