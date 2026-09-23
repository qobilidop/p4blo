# XDP compile-only draft review

Independent structural/safety review on 2026-09-23 of `p4blo-xdp-build`.
**Final disposition: clear for main integration of the compile-only gate**,
after the successful corrected native CI and independent artifact checks
recorded below. Remove the temporary experimental branch trigger and retain
the explicitly bounded claims. No local image build, kernel operation,
capability change or Docker execution was performed by this reviewer.

## Safety and reproducibility

The source path compiles unchanged pinned `xdpfilt_alw_eth.c`; no patching of
upstream input or production Python dependency is introduced. Source archives
are pinned by revision and SHA-256, matching the independently fetched hashes
from the earlier build plan. The base image digest, dated Ubuntu snapshot,
checksum-pinned certificate bootstrap and signed APT metadata avoid floating
package acquisition. Disabling historical metadata expiration does not
disable signatures or HTTPS. Build/package/compiler/dependency provenance
is retained in the image; double compilation compares exact object bytes,
without claiming cross-host/architecture reproducibility.

The inspector calls libbpf's object-open/metadata APIs, not load, attach,
map-create, pin or packet-test APIs. It checks program/map/BTF file descriptors
remain unloaded and interprets pin-by-name metadata without creating pins.
Runtime is nonroot, no network, read-only root, all capabilities dropped,
no-new-privileges, bounded noexec temporary storage and resource/time limits.
No host mounts, interface access, deployment action or privileged fallback.

The new strace check follows descendants and rejects attempted `bpf` syscalls,
not merely successful ones or final fd state. The trace is checked before
interpreting native failure, so a negative fixture cannot mask an attempted
kernel operation behind its expected diagnostic. If tracing is blocked under
the default runtime policy, CI must fail rather than add capabilities or
weaken seccomp to make the check pass.

The GitHub job uses read-only repository permissions and pinned action commits.
The temporary `work/xdp-build` push selector serves the isolated experiment;
remove it before integration as planned. The runner label itself is floating,
but compiler/object dependencies are inside the pinned image. No deployment
or workflow capability escalation is present.

## Check quality and limitations

The restricted ELF parser checks identity, machine, section layout, exact
license/feature profile, program symbol, BTF presence, map relocation names
and instruction offsets. Native inspection checks both full map layouts,
statistics aliases/types and BTF-encoded run configuration. It does not
claim general ELF validation, instruction semantics, verifier acceptance,
kernel execution or behavioral equivalence to a p4blo translation.

Negative fixtures distinguish malformed structural files from objects that
pass structural checks but fail native BTF/map checks. Native negatives must
exit 1 with their specific diagnostic, not just crash. Metadata JSON rejects
duplicates, unexpected keys and bool/int coercion. Expected libbpf warnings
are narrowly matched, not broadly ignored.

The initial test import used `oracle.xdp.check`; root corrected it to the
repository's explicit `tests.oracle.xdp.check` after collection failure. The
corrected import was independently inspected and imported successfully.

## Actual evidence and remaining obligations

Independently invoked **nine pure checks**, covering strict inspector JSON
and malformed ELF prefixes: exit 0. No native/strace claim is inferred from
these tests. Root reports local pytest **nine passed / one explicit missing-
image skip**, plus ruff/format, pyright and actionlint success. Prior native
compilation/open-only inspection and recovered-object checks are separately
recorded historical evidence, not validation of the new runtime stage.

Before main acceptance, CI must build the final multi-stage image and run
the required gate with **no Docker skip**, proving strace succeeds with the
unchanged restrictions, both compiles agree, and real native map/BTF mutants
fail for the intended reasons. Record actual results and any portability
changes, retain useful object/provenance evidence, and rerun ordinary merged
repository gates. Do not reuse a cached prior-image success as this evidence.

## First CI correction review

The alias negative originally required `rx_packets` to occur exactly once
in the entire object, but both DWARF and BTF carry it. The correction first
extracts `.BTF`, replaces the unique alias within that section, then replaces
the entire unique BTF payload in the object. Existing length/uniqueness guards
and structural acceptance remain intact; it now tests the intended native
metadata failure instead of failing fixture construction. Reviewed read-only.

Artifact retention now uploads object/provenance and exact source archives
for 14 days through a pinned action, not a container image. The nonroot tar
step exposed remote ADD's default root-only archive permissions. This was
independently identified from the Dockerfile and confirmed by actual CI:
the directories were traversable but the two archive files were not readable.
The narrow fix sets those two public source files to 0644 during build,
without changing runtime user/capabilities/seccomp. This follows the documented
[remote ADD permissions](https://docs.docker.com/reference/dockerfile/).

Both corrections are **clear for experimental fix commits**. Root reports
first native CI ran the final build/repeat comparison, baseline tracing,
structural negatives and wrong-capacity negative successfully, then failed
the alias fixture and artifact capture as described. That is attributed
partial CI evidence, not a fully green gate or independently repeated native
test. The corrected job still must pass before main acceptance.

## Final native CI and artifact acceptance

Independently queried the GitHub run metadata and complete job log for
[run 35900039992](https://github.com/qobilidop/p4blo/actions/runs/35900039992),
head `63ec6d1ee8f2cf866d00007f8be6b78592d9d2bb`: successful image build,
required offline gate, artifact capture and artifact upload. The log enables
`P4BLO_REQUIRE_XDP_BUILD=1` and shows **10 passed, no skips**, including the
actual native positive/negative container gate. That gate requires all four
inner unittest checks to pass, preserving the reviewed nonroot/capability/
network/readonly restrictions and zero attempted BPF syscalls. This is
native CI evidence inspected by the reviewer, not a local native rerun.

Independently checked the downloaded artifact without Docker or extraction:

- All 15 tar entries have safe relative paths in `artifacts/` or `archives/`
  and regular-file/directory types; every extracted file matches its tar
  member byte for byte.
- Both object copies are byte-identical. Object SHA-256 is
  `a86cd47b5da7289766dcaa2a7a729b5b963bf3be14c513409f5220e67d1b0421`,
  also matching the retained hash file.
- Both upstream archive hashes match their pinned Dockerfile values:
  xdp-tools `b83d1a74deacf2ba48ee50798bb38a389ddda402967413c6c2ad1389daed3c16`;
  libbpf `f94a66ab80e79aa11e15409479d8bc2572649f0ef25dbd2daf503ea5b05067ad`.
- Retained build script and native inspector source exactly match the reviewed
  CI commit. Provenance reports Clang 18.1.3 (1ubuntu1) and
  `x86_64-linux-gnu`.
- The object passes the restricted ELF profile locally: 30 sections and
  1,064 code bytes. Five structural negative mutations fail as intended.
  Both native-negative fixtures independently construct changed objects that
  still pass the structural reader; their actual native rejection evidence
  comes from the successful required CI gate, not this host-only check.

No remaining blocker for this bounded infrastructure increment. Main's local
missing-image skip must remain distinguished from this required CI success.
This does not establish Linux verifier acceptance, kernel loading, packet
execution, or behavioral equivalence of an XDP translation; those remain
separate later work with their own authority and verification requirements.
