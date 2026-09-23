# XDP compile-only draft review

Independent structural/safety review on 2026-09-23 of `p4blo-xdp-build`.
**Clear for an experimental branch commit/push to obtain native CI evidence;
not accepted for main integration yet.** No image build, kernel operation,
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
