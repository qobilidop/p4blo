# Original xdp-filter compile profile

Compile-only infrastructure for `xdp-filter-ethernet-allow-v1`.
It does **not** execute a BPF program or validate a p4blo port. Kernel load,
map creation, test-run, pinning and interface attachment are out of scope.

Build with `docker build -t p4blo-xdp-build tests/oracle/xdp`, then run
`P4BLO_REQUIRE_XDP_BUILD=1 uv run pytest tests/test_xdp_build.py`.
Use `P4BLO_XDP_BUILD_IMAGE` for an isolated worktree's tag. Without the
required flag a missing image is an explicit skip, not successful evidence.
An available but failing image always fails the test.

## Inputs and license boundary

The Dockerfile pins Ubuntu's multiarchitecture index digest, authenticated
Ubuntu archive snapshot `20260921T000000Z`, a checksum-pinned Mozilla CA
bundle, and both upstream source archives by commit and SHA-256. No latest
APT repository is consulted. TLS and archive signature checks stay enabled.
The CA bundle retains its upstream MPL-2.0 notice. Full unchanged upstream
sources and notices are retained in the runtime image under `/opt/src` and
the checksum-verified archives under `/opt/archives`.

- xdp-tools `f27ea2a83fd4fcce8968f627b25493950aaf5c44`:
  archive SHA-256 `b83d1a74deacf2ba48ee50798bb38a389ddda402967413c6c2ad1389daed3c16`.
- libbpf `09b9e83102eb8ab9e540d36b4559c55f3bcdb95d`:
  archive SHA-256 `f94a66ab80e79aa11e15409479d8bc2572649f0ef25dbd2daf503ea5b05067ad`.

The selected unchanged `xdpfilt_alw_eth.c` declares its BPF program GPL;
xdp-tools and libbpf retain their own licenses. The new inspector is
Apache-2.0 source linked with the separately licensed pinned libbpf. This
gate builds locally/in CI; it does not publish an image or settle downstream
redistribution obligations. No native dependency enters the Python package.

## Checked boundary

Clang 18 compiles the little-endian BPF object twice in the same environment,
and byte comparison must pass. This is same-build repeatability, not a proof
of cross-architecture or independent-host reproducibility. Compiler/package
versions, dependency list, command script, object digest, ELF description and
disassembly are saved in `/opt/artifacts`.

The Python reader checks a restricted ELF64/BPF profile: program function,
license/features, BTF presence and exact map-reference relocations. A small
native inspector opens the object with the pinned libbpf without loading it.
It checks one XDP program, the two per-CPU map layouts/capacities, statistics
record aliases, priority 10 and XDP_PASS chain setting. Program/map/BTF FDs
must remain unloaded. `strace -f -e trace=bpf` additionally rejects **any**
attempted BPF syscall, successful or not, including negative test paths.

The runtime gate runs as UID 65534, with no network, all capabilities
dropped, no-new-privileges, a read-only root, bounded `/tmp` tmpfs, memory
and process limits. It changes no host kernel settings and mounts no host
interface or BPF filesystem. If tracing is unavailable under that profile,
the gate fails; it does not add privileges to manufacture a pass.

Negative tests reject truncated/wrong-machine/wrong-endian/license objects,
a structurally intact wrong-capacity map and a wrong BTF statistics alias.
Separate host tests reject malformed or ambiguously typed inspector JSON.
These validate selected observer failure modes, not a general ELF verifier,
instruction-level correctness, Linux verifier acceptance or datapath behavior.

## Current evidence

Clean-runner CI [35900039992](https://github.com/qobilidop/p4blo/actions/runs/35900039992)
at `63ec6d1` passes all **10 required tests**, without skips. This includes
the four native object checks, both compilations, syscall tracing and
negative BTF/map tests under the documented runtime restrictions. Compiler:
Ubuntu Clang 18.1.3 (1ubuntu1), build platform `x86_64-linux-gnu`.
Object SHA-256:
`a86cd47b5da7289766dcaa2a7a729b5b963bf3be14c513409f5220e67d1b0421`.
The downloaded repeat object is byte-identical and both accompanying source
archives match their pinned hashes. This digest records that build, not an
architecture-independent expected binary hash.

The first branch run failed a test-fixture anchor shared by DWARF/BTF and
non-root access to source archives. Fixes target the unique BTF string and
make only the public archives readable; no runtime restriction was relaxed.
CI retains object/provenance and corresponding sources for 14 days. Rebuild
from the tracked pins after artifact expiry; no temporary archive is a
required build input. Local Docker capacity still prevents rebuilding the
final image here: nine host tests pass and the local native gate explicitly
skips. Native acceptance comes from required CI, not that skip.
