# Compile-only XDP oracle preparation

Read-only design check, 2026-09-23, extending `xdp-preflight.md`. No tools
were installed, containers built, BPF objects compiled or kernel objects
loaded. No capabilities, networking, mounts or global policy changed.
This is a proposed implementation, not successful compile/verifier evidence.

## Smallest useful increment

Build the unchanged upstream `xdpfilt_alw_eth.c` directly, using its original
includes and the upstream BPF compilation flags. Do not build the xdp-filter
CLI, libxdp dispatcher, upstream integration tests or kernel loader.
The [translation unit](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/xdpfilt_alw_eth.c)
itself chooses Ethernet filtering/default allow and disables other match
families. Do not recreate that choice with a patched/synthetic C program.

The [upstream object rule](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/lib/common.mk)
is a single clang invocation, separate from its userspace dependencies.
The full configure path checks additional libraries/tooling which are not
needed to compile this one translation unit. Preserve the selected source
and consumed headers byte-for-byte, including licenses.

Recommended organization: one optional `tests/oracle/xdp/` build context and
one `tests/test_xdp_build.py` gate. Keep native tooling outside the pure-Python
package. Do not add a parallel top-level project or runtime service.
Confidence: high on scope, medium on final image packaging until built.

## Pins, tools and headers

Retain the preflight's xdp-tools revision
`f27ea2a83fd4fcce8968f627b25493950aaf5c44` and exact libbpf submodule revision
`09b9e83102eb8ab9e540d36b4559c55f3bcdb95d`. Rechecked the recursive Git tree:
the latter really is the gitlink, not a guessed libbpf release.

Downloaded to memory and hashed during this audit, with no source files
written:

| Immutable archive URL | Bytes | SHA-256 |
|---|---:|---|
| [xdp-tools](https://codeload.github.com/xdp-project/xdp-tools/tar.gz/f27ea2a83fd4fcce8968f627b25493950aaf5c44) | 391427 | `b83d1a74deacf2ba48ee50798bb38a389ddda402967413c6c2ad1389daed3c16` |
| [libbpf](https://codeload.github.com/libbpf/libbpf/tar.gz/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d) | 1037103 | `f94a66ab80e79aa11e15409479d8bc2572649f0ef25dbd2daf503ea5b05067ad` |

Compilation needs:

- A pinned BPF-enabled clang plus matching `llvm-readelf`, `llvm-objdump`
  and `llvm-objcopy`. Clang/LLVM 18 on Ubuntu noble is a reasonable first
  candidate, not a compiler version tested by this audit.
- Pinned Linux UAPI headers (`linux-libc-dev` on Ubuntu), including the
  architecture's `asm/` include directory. Do not mount host kernel headers.
- The original xdp-tools `headers/` directory, placed before system headers:
  it supplies `xdp/*` and intentionally shadows several `linux/*` files.
- The three consumed libbpf source headers, staged as `bpf/bpf_helpers.h`,
  `bpf/bpf_helper_defs.h`, and `bpf/bpf_endian.h`. They are not supplied by
  xdp-tools' `headers/bpf/`. Preserve their exact pinned bytes. A header-only
  staging step avoids building native libbpf just for compilation.
- Shell/archive/checksum utilities; a small Python manifest checker is
  optional. GCC, libelf/zlib development packages, pkg-config, bpftool and
  libxdp are not required merely to emit/disassemble this object.

The [libbpf helper header](https://github.com/libbpf/libbpf/blob/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d/src/bpf_helpers.h)
uses Linux integer definitions already included by the datapath. This is
not a CO-RE/vmlinux.h build: no `/sys/kernel/btf/vmlinux` input is needed.
All protocol UAPI headers referenced by the unchanged
[parser helper](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/headers/xdp/parsing_helpers.h)
must still be available even when optimizer-eliminated functions are unused.

For reproducibility, either derive the Linux image/toolchain closure from
the repository's locked nixpkgs, or use a digest-pinned multiarchitecture
Ubuntu base with one fixed archive snapshot for **every** apt operation.
[Ubuntu's snapshot service](https://snapshot.ubuntu.com/) supports the latter.
A base digest plus floating `apt-get install` is insufficient. Record the
actual compiler/header package versions and architecture alongside the
object hash. The base digest/snapshot or Nix image derivation still needs
to be chosen and tested by implementation; none is invented in this plan.

## Proposed compilation contract

In a fixed container build directory, invoke the equivalent of:

```text
clang-18 --target=bpfel -O2 -g -std=gnu2x -fno-stack-protector
  -Wall -Werror -Wno-unused-value -Wno-pointer-sign
  -Wno-compare-distinct-pointer-types -Wno-visibility
  -I/opt/src/xdp-tools/headers -I/opt/bpf-headers
  -I/usr/include/<pinned-linux-multiarch-tuple>
  -ffile-prefix-map=/opt/src=/src -fdebug-prefix-map=/opt/src=/src
  -c /opt/src/xdp-tools/xdp-filter/xdpfilt_alw_eth.c
  -o /opt/artifacts/xdpfilt_alw_eth.o
```

Flags derive from [upstream defines](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/lib/defines.mk).
Explicit `bpfel` fixes the existing little-endian profile across amd64 and
arm64 hosts. Do not silently add newer BPF CPU/ISA features or architecture
tracing macros. Capture the dependency/preprocessor manifest and verify
all includes come from the pinned source/header/compiler closure. An
explicitly omitted upstream userspace configuration macro must be shown
irrelevant to this object, not assumed so for future feature builds.

Build twice in controlled clean output paths and compare normalized object
hashes, with fixed debug paths and timestamps where applicable. Distinguish
reproducible inputs from proven cross-architecture byte identity; the latter
requires actually comparing both architecture builds. A single successful
build establishes neither kernel acceptance nor packet behavior.

## Meaningful offline validation

Fail closed on missing/wrong/truncated objects. Check ELF64 little-endian,
relocatable `EM_BPF`; nonempty executable `xdp` section and intended function
`xdpfilt_alw_eth`; `.BTF`, `.BTF.ext`, `.maps`, license and feature metadata.
Disassembly and relocation parsing must succeed with no unexpected external
symbols. Record, rather than initially invent, the pinned instruction count.

From the [original datapath](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/xdpfilt_prog.h)
and [feature definitions](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/common_kern_user.h),
require `license` bytes `GPL\0` and the `features` section's 32-bit value
`0x30` (allow plus Ethernet only). Preserve `.xdp_run_config`: its priority
10 and PASS chain flag 1 are encoded in BTF types, not ordinary integer
section contents. Do not compare its zeroed bytes as if they were values.

For a stronger first gate, build a tiny **open-only** inspector against the
pinned libbpf. Add native C compiler/make, libelf development files and zlib
development files; pkg-config is convenient or use explicit link flags.
The [libbpf Makefile](https://github.com/libbpf/libbpf/blob/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d/src/Makefile)
supports a static-only build. The inspector opens the ELF, iterates program,
map and BTF metadata, then closes it. It must never call load, create-map,
attach, pin, test-run or feature-probe APIs.

Require these complete user-map layouts:

| Map | Type | Key bytes | Value bytes | Capacity |
|---|---|---:|---:|---:|
| `filter_ethernet` | PERCPU_HASH | 6 | 8 | 10000 |
| `xdp_stats_map` | PERCPU_ARRAY | 4 | 16 | 5 |

The statistics layout is independently specified by its
[record header](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/headers/xdp/xdp_stats_kern_user.h)
and [map declaration](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/headers/xdp/xdp_stats_kern.h).
Enumerate all maps, including any internal metadata maps: use an explicit
allowlist, not a filter which hides extra state. The two source maps declare
pin-by-name; preserve that metadata without creating a pin.

Pinned [libbpf open-file implementation](https://github.com/libbpf/libbpf/blob/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d/src/libbpf.c)
separates ELF/BTF/map-description processing from loading. It may emit
informational messages about custom xdp-tools metadata sections. Inspect
and narrowly classify those messages; do not convert arbitrary warnings or
parse failure into success. Assert all map/program FDs remain unopened.

Run the validation image nonroot, `--read-only --network none --cap-drop ALL`
with no host mounts and no-new-privileges. If scratch space is needed, use
a bounded tmpfs. A deny-BPF-syscall sandbox or syscall-trace assertion is
useful additional evidence, never a reason to add capabilities or relax
seccomp. Negative fixtures should remove BTF, corrupt map widths/capacity,
select the deny/wrong-feature object, or truncate ELF and require failure.

## Handoff

Start with source/header provenance plus object/feature checks; preferably
include the open-only map inspector before calling the build profile ready.
Keep the optional dependency increase explicit. This artifact validates
compilability and object shape, not verifier acceptance, maps at runtime,
CPU-slot behavior, actions or packets. Those remain the separate FD-only
execution work in `xdp-preflight.md`, with its authorization/security and
licensing boundaries unchanged.
