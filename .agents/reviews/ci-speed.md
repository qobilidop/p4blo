# CI speed independent review

Reviewed `80eba84..ae4fb9e` on `work/ci-speed` (rebased onto `f6c3a6e` as
`f9abcb2..26a8c04` unchanged), read-only, by an AI agent (Claude Opus 5.5)
separate from the author: `-n auto --dist loadgroup` for the Lean
differential step, and a Lake `lib`/`ir` build cache saved only from main.

## Commands and results

- `actionlint .github/workflows/lean.yml` (1.7.12): exit 0.
- `actions/cache` `restore/action.yml` and `save/action.yml` exist at the
  existing pin `0057852b…`, which `v4` and `v4.3.0` resolve to; every save
  error path in `saveImpl.ts` warns and none fails the job.
- `git grep` for elaboration-time IO in `*.lean` (`include_str`, `IO.FS`,
  `#eval`, `run_cmd`, `run_elab`): none; every file read is in a test driver
  or `Main` at run time, so a replayed `#guard_msgs` audit cannot go stale.
- Lake v4.34 traces hold output hashes and the replay log; module outputs
  live in `lib/lean` and `ir`, both cached; executables' traces live in the
  uncached `bin` and relink.

## Confirmed findings

None.

## Checked

- Key/prefix: `restore-keys` is the key up to the source hash; the
  `hashFiles` globs see only `.lean`, `lakefile.toml` and manifests; all
  dependencies are path requires, so no `.lake/packages`. The save step's
  bare `if:` implies `success()`, so a failed build is never saved;
  `github.ref == 'refs/heads/main'` is correct for the push and
  pull_request triggers. `check-lean.sh` enforces identical toolchains,
  so hashing one `lean-toolchain` is enough.
- A saved entry comes only from a passing `--wfail` build, so replayed
  logs carry no warnings; glob libraries enumerate sources, not outputs.
- xdist: `lean_binary` is per worker and read-only; `GROUPED_MODULES` stay
  on one worker under `loadgroup`; failure bundles under `.artifacts/drt/`
  are content-addressed with `exist_ok`, so parallel writes are safe.
- The pin table in `docs/workflows.md` is generic; no new row is needed.

## Nonblocking observations and their resolution

- `docs/workflows.md` did not mention the CI cache beside its warning
  about copied Lean caches: a sentence added.
- The exception was appended to a 2026-09-23 decision: made its own
  2026-09-25 entry.
- Not yet measured remotely: a restored cache only helps if Lake trusts
  trace hashes over mtimes; if not, the cost is a cold build, never a
  wrong result. The first PR after a main save shows it.
- The Actions cache is at its 10 GB limit; LRU eviction of main's Lean
  entry only means a cold build.

## Not run by the reviewer

Lake or pytest in the reviewed worktree (a gate was running) and any
remote CI. The author ran the full local gate on the rebased branch
(`check-lean.sh` and `P4BLO_REQUIRE_LEAN=1 scripts/check.sh`, 5199 passed,
the optional XDP image skipped, 4 xfailed) and the stale-`.olean`
"bad import" check recorded in `.agents/decisions.md`.
