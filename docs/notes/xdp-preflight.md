# xdp-filter: source and execution-environment preflight

Read-only audit, 2026-09-23. No BPF program was loaded or run, no network
configuration was changed, no tools were installed, and no container was
given additional capabilities. This is a concrete implementation path,
not completed original-program execution evidence.

## Pins and licensing

Resolve `xdp-project/xdp-tools` main to
`f27ea2a83fd4fcce8968f627b25493950aaf5c44`, obtained with:

```sh
git ls-remote https://github.com/xdp-project/xdp-tools.git refs/heads/main
```

Its `lib/libbpf` submodule is
`09b9e83102eb8ab9e540d36b4559c55f3bcdb95d`, confirmed through the Git tree
API, not assumed from the libbpf main branch. These two revisions should
be the source pins for the first oracle build.

The repository is mixed-license; use the individual SPDX headers, not one
blanket license. The actual [`xdpfilt_alw_eth.c`](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/xdpfilt_alw_eth.c),
[`xdpfilt_prog.h`](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/xdpfilt_prog.h)
and statistics headers are GPL-2.0. The parser helper is dual-licensed
GPL-2.0-or-later OR BSD-2-Clause. Preserve upstream notices/license texts
with any vendored originals. Keep oracle inputs distinct from our own
implementation; do not silently copy a GPL implementation into differently
licensed project code. A manual port's distribution/licensing treatment
needs explicit review before redistribution, rather than an assumption
that changing the language removes obligations.
[Upstream license description](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/LICENSE)

## Proposed first named profile

**`xdp-filter-ethernet-allow-v1`**: compile the existing, unmodified upstream
`xdpfilt_alw_eth.c` translation unit. It explicitly selects Ethernet
filtering and default-allow, and disables IPv4, IPv6, UDP and TCP matching.
This is an upstream feature build, not an invented simplified algorithm.
Default-deny can follow as the companion existing `xdpfilt_dny_eth.c`
build once the first profile passes.

Profile conditions:

- One fresh program/maps instance per experiment; sequential requests on
  one fixed CPU; no simultaneous data-plane or control-plane operations.
- Explicit map initialization and insert/delete/update events between
  requests. Map entries and all observable counters are part of the input
  and result contract, not hidden harness state.
- Compare action number, returned packet bytes and complete logical map
  state after every request. Keep ABORTED, DROP and PASS distinct even
  when two of them both mean “not forwarded” in a higher-level adapter.
- No interface attachment, dispatcher, CLI equivalence, throughput claim,
  hardware offload, concurrency guarantee or live-frame test mode.
- Input packet bounds should initially match the eventual kernel harness
  limits and be stated explicitly after execution preflight. Do not
  silently pad malformed inputs or treat syscall rejection as XDP_ABORTED.

The source checks destination MAC before source MAC and returns after the
first matching rule. Matching increments the packed 64-bit rule value by
64, preserving low flag bits modulo unsigned overflow. Rules live in a
10,000-entry per-CPU hash map; verdict statistics use a per-CPU array. A
full Ethernet header is required. No IP/transport parsing occurs in this
feature build, so malformed higher-layer payloads still reach MAC matching.
[Datapath source](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/xdpfilt_prog.h),
[flag definitions](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/common_kern_user.h)

The shared Ethernet helper scans up to four VLAN tags, but incomplete tags
end that scan without returning an error. In this Ethernet-only profile
the resulting inner EtherType/cursor is unused; preserve MAC matching for
truncated VLAN payloads rather than inventing a rejection. This
simplification needs an explicit observational-equivalence argument, not
an assumption that every parser check is relevant to every feature build.
[Parser helper](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/headers/xdp/parsing_helpers.h)

Statistics count both packets and total input bytes for the actual verdict.
Keep the 64-bit wrapping behavior. Read all CPU slots; initialize all slots
consistently and prove/test only the chosen CPU changes. Summed totals
alone would hide an observer that reads the wrong CPU's rule values.
[Statistics implementation](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/headers/xdp/xdp_stats_kern.h),
[record layout](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/headers/xdp/xdp_stats_kern_user.h)

Confidence: **high** that this is an authentic useful upstream profile;
**medium** that it is the best first XDP example. Its small parser isolates
map/state/oracle integration before IPv4 options, IPv6 extensions, ARP/ND
and multi-feature early returns. Revisit if map support dominates the work
or the firewall stage already supplies enough infrastructure for a TCP
profile at comparable cost. Full-datapath support remains a later audit.

## What the upstream tests provide

[`tests/test-xdp-filter.sh`](https://github.com/xdp-project/xdp-tools/blob/f27ea2a83fd4fcce8968f627b25493950aaf5c44/xdp-filter/tests/test-xdp-filter.sh)
tests feature loading, native/SKB modes, allow/deny policy, rule additions
and removals, addresses, ports and CLI output. Ethernet tests use IPv6 ping
in network namespaces, check packet capture results, then add/remove source
and destination MAC rules. These are valuable behavior scenarios, but not
standalone byte fixtures or an existing BPF_PROG_RUN differential harness.
They were inspected, **not executed** in this audit.

Carry their add/match/delete scenarios into deterministic packet fixtures,
then extend beyond them: both source and destination rules matching,
nonmatching direction bits, equal source/destination addresses, zero and
maximum counter values, repeated packets, truncated headers/tags, arbitrary
EtherTypes, configuration replacement, and stale-state observer mutants.

## Read-only local environment findings

Docker reports Linux `6.8.0-100-generic`, architecture `aarch64`, AppArmor,
default seccomp and cgroup namespaces. The host being macOS does **not**
prevent using its Linux VM as the kernel execution oracle.

Two candidate local images were inspected and launched only with
`--read-only --network none`, no added capabilities and `/bin/sh` as
entrypoint:

| Image | Actual image ID | Finding |
|---|---|---|
| `bpf-tv-dev` | `sha256:4943dfdaae6e854231ca3964332af323f19bb6aced9e30df40388f731a40edf3` | native arm64, Ubuntu 24.04.4; GCC/make/binutils/Python present; no clang, bpftool, pkg-config or standard libbpf headers |
| `vsc-bpf-tv-15b6c69fb835322d34c45a65dc8feef417bc7b3c5ece5305ee7052138b8b5b87` | `sha256:f487bab8a8e08ecf0e5ff77ce8a84979164f143b2af66206e7b108d8a59cbbaf` | native arm64; GCC present; no clang, bpftool, pkg-config or standard libbpf headers |

The ordinary `bpf-tv-dev` container exposed:

```text
/sys/kernel/btf/vmlinux: readable, 6961162 bytes
/proc/sys/kernel/unprivileged_bpf_disabled: 2
CapEff / CapBnd: 00000000a80425fb
Seccomp: 2; Seccomp_filters: 1
possible CPUs: 0-11; allowed CPUs: 0-11
ulimit -l: 8192
```

The effective/bounding mask does not contain CAP_BPF, CAP_NET_ADMIN or
CAP_SYS_ADMIN. Root inside this default container does not imply those
capabilities. `/sys/fs/bpf` was read-only; an FD-only harness need not use
that mount at all. No `bpftool feature probe` was run: that probe can itself
try to load programs/create maps and would exceed read-only scope.

These checks do not establish that program loading works. Linux 6.8's
XDP loading path requires BPF authority and network-admin authority (with
the documented SYS_ADMIN alternatives); the existing container lacks
both. Seccomp/LSM policy may be a further constraint. Do not change the
global unprivileged-BPF sysctl or jump to a privileged container.
[Linux 6.8 loading checks](https://github.com/torvalds/linux/blob/v6.8/kernel/bpf/syscall.c)

## Recommended kernel-oracle harness

Build a small **external test tool**, not a native dependency of the pure
Python `p4blo` package. Prefer libbpf's `bpf_prog_test_run_opts` API over a
sequence of `bpftool prog load` commands: a single process can own all FDs,
map changes, packet calls and observations, then release everything on
exit without mounting bpffs or pinning resources.
[Pinned libbpf API](https://github.com/libbpf/libbpf/blob/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d/src/bpf.h)

Suggested lifecycle:

1. Open the original compiled object and select only the intended program.
   For every map, clear its auto-pin path before load with
   `bpf_map__set_pin_path(map, NULL)`; the pinned libbpf implementation
   supports clearing it. Do not reuse an existing globally named map.
2. Load without attaching to an interface. Enumerate named maps, check
   their actual type/key/value sizes/capacity against the profile, and
   initialize fresh per-CPU state. Fail closed on layout drift.
3. Pin the userspace process to one allowed CPU and use `repeat = 1`.
   Keep test flags zero: Linux 6.8's XDP path rejects flags other than its
   live-frame flag, so do not assume the generic ON_CPU test flag works
   here. Record the chosen CPU and all slots in observations.
4. Feed exact packet buffers; retain the syscall result separately from
   the BPF action. Return exact bytes/length plus complete maps after each
   request. Apply explicit controller updates between requests.
5. Close the object/FDs on success, errors and timeout. No pin, link,
   interface attachment or live-frame flag should exist to outlive it.

[Map pin-path API](https://github.com/libbpf/libbpf/blob/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d/src/libbpf.h),
[implementation](https://github.com/libbpf/libbpf/blob/09b9e83102eb8ab9e540d36b4559c55f3bcdb95d/src/libbpf.c),
[Linux 6.8 XDP test-run implementation](https://github.com/torvalds/linux/blob/v6.8/net/bpf/test_run.c)

Normal BPF_PROG_RUN returns the action instead of sending/dropping real
network traffic. Map mutations still need observation; the statement
“no live packet effects” must not be interpreted as “no persistent map
effects.” Explicitly forbid `BPF_F_TEST_XDP_LIVE_FRAMES`.
[Kernel testing documentation](https://docs.kernel.org/bpf/bpf_prog_run.html)

`bpftool prog run` remains a useful diagnostic alternative: it accepts
packet/context files and returns the BPF result, but its typical separate
load/run workflow introduces persistent object ownership that the
single-process FD harness avoids.
[bpftool documentation](https://github.com/libbpf/bpftool/blob/main/docs/bpftool-prog.rst)

## Concrete next steps, not a host-platform blocker

1. Add a dedicated reproducible oracle image: pin a multi-architecture base,
   xdp-tools and its libbpf submodule, and the compiler/library inputs.
   Required build tools include BPF-capable clang/LLVM, C compiler, make,
   libelf/zlib development inputs and the selected upstream headers. Build
   the existing feature object without rewriting its datapath. This can
   be implemented and compile-tested without BPF-loading authority.
2. Implement the FD-only adapter, strict protocol, layout checks, cleanup,
   negative tests and replay artifacts. Keep C/libbpf confined to the
   optional oracle infrastructure. Confidence: high on this boundary.
3. Perform an explicitly scoped execution preflight with only the needed
   capability additions, initially CAP_BPF and CAP_NET_ADMIN, network none,
   no interface attachment and no host mounts. Check whether the existing
   seccomp policy admits the BPF syscall before considering a narrowly
   adjusted profile. Do not silently fall back to SYS_ADMIN/privileged or
   disable security globally. **This capability-bearing execution has not
   been attempted or authorized by this read-only audit.**
4. If this VM's security policy cannot support that scoped run, use a
   dedicated Linux CI runner/VM with the same pinned build and protocol.
   Keep building the p4blo maps, XDP result adapter and Lean/Python
   conformance in the meantime; absence of original execution evidence
   stays an explicit acceptance gap, never a passing skip.
5. Model associative maps and verdict statistics through small general
   extern contracts with readable eDSL operations, not an opaque
   `run_xdp_filter` extern. Read/write value semantics can replace BPF
   value-pointer mutation for this single-threaded profile, but that
   correspondence needs its own argument and tests. Confidence: medium on
   exact API; revisit for larger profiles needing concurrent updates/LRU.
6. Add scoped proofs and adversarial tests. Particularly useful mutants:
   check source first, update both matching counters, erase configuration
   between requests, read the wrong CPU slot, change counter increment,
   normalize ABORTED into DROP, or count output bytes instead of input
   bytes. Broaden from Ethernet allow to deny, then TCP/UDP/IP only after
   the state/observer boundary is validated.

Checks performed: upstream source/test/helper inspection, source/submodule
pin resolution, Docker image metadata, nonprivileged read-only container
tool/kernel/capability inspection, and `git diff --check`. Tool-inventory
commands deliberately exposed missing commands (exit 127); these are not
successful execution tests. No compile, verifier, BPF_PROG_RUN, upstream
integration suite or new Lean/Python implementation test ran in this audit.
