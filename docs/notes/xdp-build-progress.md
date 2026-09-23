# Compile-only XDP work in progress

Final native checkpoint: CI `35900039992` at `63ec6d1` passes all ten required
checks and artifact retention. `tests/oracle/xdp/README.md` records the exact
object hash, compiler and trust boundary. The notes below retain the local
capacity incident and intermediate failures; they are not pending native
acceptance instructions. Kernel execution remains outside this increment.

2026-09-23, isolated `work/xdp-build`, base `0ad1b5b`. These files are not
integrated or accepted gates. Main's Python/Lean work does not depend on them.

The Dockerfile successfully compiled unchanged pinned xdp-tools
`xdpfilt_alw_eth.c` and pinned libbpf. The native open-only inspector ran as
UID 65534 with all capabilities dropped, no network, a read-only root and
no-new-privileges. It checked the XDP program, both map layouts, BTF counter
aliases and run-configuration priority/pass chaining. No kernel load, map
creation, interface attachment or packet execution was attempted.

The latest `check.py` and Dockerfile's added `strace` dependency are **not
tested**. A subsequent build exhausted the shared Docker VM. APT reported
invalid signatures because it could not write its metadata; neither TLS nor
signature validation was disabled. The pinned snapshot approach itself had
already built successfully. Remote certificate ADD needs searchable parent
directories, hence the explicit chmod in the Dockerfile.

Only nine exact cache entries belonging to this XDP build were pruned
(977.7 MB, rebuildable). Its temporary image was exported before removal:

- Host archive: `.artifacts/xdp-compile-recovery.tar`, 268 MiB.
- SHA-256: `6962295d2da2d0fcddc4516f87940923050ff57fe5c6198666fb05c71fc99e1c`.
- Image ID: `sha256:df7471baebe3e19f94f214f9ec318280e1271b8386ed141f80be73645e84b2fa`.
- Former sole tag: `p4blo-xdp-build-root:latest`; absence checked after removal.
- Recovery: `docker image load -i <absolute archive path>`, only with enough
  VM space. The archive is supplemental recovery, not a source dependency.

No unrelated Docker images, containers, volumes or caches were removed.
The VM had only 440 MiB available afterward. Do not rebuild until sufficient
space is available; coordinate with ongoing BMv2 tests. Broad cleanup or VM
configuration changes require user authority.

Next implementation steps:

1. Reduce steady-state image footprint with a separate runtime stage. Keep
   exact source archives/licenses, compiler/package/dependency provenance
   and the produced object. The build still needs adequate temporary space.
2. Compile twice and compare object bytes; save provenance rather than only
   printing it. Do not claim cross-host/architecture reproducibility from
   two same-container compiles.
3. Execute `check.py` with a bounded writable tmpfs. Trace attempted BPF
   syscalls, not just final unloaded FDs. Do not weaken the capability or
   seccomp profile merely to make tracing pass.
4. Add strict typed/duplicate-key JSON checking and negative ELF/map/BTF
   fixtures. Test malformed input, wrong profile and inspector failures.
5. Add an optional local/required CI gate, independent review and complete
   documentation of pins and limitations before integrating.

This remains compile/metadata evidence only. Kernel execution and actual
original-program behavioral equivalence are separate later obligations.

## Clean-runner alternative

Rather than broaden local cleanup authority, finish this compile-only gate
on isolated branch `work/xdp-build` using a dedicated GitHub workflow. It
does not change main until native CI and final independent review pass.
Experimental review is recorded in `reviews/xdp-build.md`. The workflow
uploads object/provenance plus both corresponding source archives for 14
days. Current local evidence: nine host checks, explicit missing-image skip,
ruff/pyright/actionlint, and structural positive/five negative checks on the
recovered prior object. The first host test invocation exposed a wrong
package import; it was fixed and rerun. No native skip is counted as a pass.
