#!/usr/bin/env bash
# Build P4-SpecTec's simulator at the commit p4blo pins, and print the path of
# the resulting `p4spectec` binary. Idempotent: every step checks its own
# result first, so rerunning after a cache hit or a partial failure only does
# what is missing. See tests/oracle/README.md.
#
# Needs: git, make, a C compiler, opam (2.1 or newer), and libgmp with its
# headers plus pkgconf, which zarith's opam packages probe for. See
# README.md#development for external-tool setup options.
#
# Environment:
#   P4BLO_ORACLE_DIR   where P4-SpecTec is cloned and built
#                      (default ~/.cache/p4blo/p4-spectec)
#   OPAMROOT           opam's root, honored by opam itself (default ~/.opam)
set -euo pipefail

P4_SPECTEC_REPO=https://github.com/kaist-plrg/p4-spectec
# The pinned commit: 2026-09-22, "Merge pull request #320 from
# kaist-plrg/fix-batch-1". The CI cache key reads it from here, so it is
# the one place to bump.
P4_SPECTEC_COMMIT=2730cfd9e74048bb5439da0f8afcef124079a064
P4C_REPO=https://github.com/p4lang/p4c
# The opam package universe is pinned too, so the same versions of every
# OCaml dependency are chosen on every machine. Bump together with the
# P4-SpecTec commit when its build needs newer packages.
OPAM_REPO=https://github.com/ocaml/opam-repository
OPAM_REPO_COMMIT=6261f3c853ae417b354c06496e8458053131f14b
SWITCH=5.1.0
# What README.md and p4spectec.dockerfile install, plus ppx_let, which the
# dune-project lists and the README omits.
PACKAGES=(
    dune
    'menhir=20240715'
    'menhirLib=20240715'
    bignum
    core
    core_unix
    bisect_ppx
    yojson
    ppx_deriving_yojson
    ppx_let
    uucp
    uuseg
    uutf
)

DIR="${P4BLO_ORACLE_DIR:-$HOME/.cache/p4blo/p4-spectec}"
STAMP="$DIR/.p4blo-built"
BINARY="$DIR/p4spectec"

log() { printf '[tests/oracle/build] %s\n' "$*" >&2; }

# A finished build is stamped with its commit; a matching stamp means there
# is nothing to do, and opam need not even be installed (the CI cache hit).
if [ -x "$BINARY" ] && [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$P4_SPECTEC_COMMIT" ]; then
    echo "$BINARY"
    exit 0
fi

for tool in git make opam; do
    command -v "$tool" >/dev/null || { log "$tool is not on the path"; exit 1; }
done

# 1. The pinned commit of P4-SpecTec, fetched shallowly.
if [ ! -d "$DIR/.git" ]; then
    log "cloning P4-SpecTec into $DIR"
    mkdir -p "$DIR"
    git -C "$DIR" init -q
    git -C "$DIR" remote add origin "$P4_SPECTEC_REPO"
fi
if [ "$(git -C "$DIR" rev-parse HEAD 2>/dev/null || true)" != "$P4_SPECTEC_COMMIT" ]; then
    log "checking out $P4_SPECTEC_COMMIT"
    git -C "$DIR" fetch -q --depth 1 origin "$P4_SPECTEC_COMMIT"
    git -C "$DIR" checkout -q --detach "$P4_SPECTEC_COMMIT"
fi

# 2. The p4c submodule, which the simulator needs only for p4c/p4include
#    (core.p4, v1model.p4). A sparse, blobless, shallow checkout of that
#    directory at the pinned submodule commit instead of the whole of p4c.
P4C_COMMIT=$(git -C "$DIR" ls-tree HEAD p4c | awk '{ print $3 }')
P4C_DIR="$DIR/p4c"
if [ "$(git -C "$P4C_DIR" rev-parse HEAD 2>/dev/null || true)" != "$P4C_COMMIT" ] \
    || [ ! -f "$P4C_DIR/p4include/v1model.p4" ]; then
    log "checking out p4c/p4include at $P4C_COMMIT"
    mkdir -p "$P4C_DIR"
    [ -d "$P4C_DIR/.git" ] || git -C "$P4C_DIR" init -q
    git -C "$P4C_DIR" remote get-url origin >/dev/null 2>&1 \
        || git -C "$P4C_DIR" remote add origin "$P4C_REPO"
    git -C "$P4C_DIR" sparse-checkout set p4include
    git -C "$P4C_DIR" fetch -q --depth 1 --filter=blob:none origin "$P4C_COMMIT"
    git -C "$P4C_DIR" checkout -q --detach "$P4C_COMMIT"
fi

# 3. The opam switch and its packages.
if ! opam var root >/dev/null 2>&1; then
    log "initializing opam at opam-repository $OPAM_REPO_COMMIT"
    opam init --bare --no-setup --disable-sandboxing -y "git+$OPAM_REPO#$OPAM_REPO_COMMIT"
else
    opam repository set-url default "git+$OPAM_REPO#$OPAM_REPO_COMMIT" >/dev/null 2>&1 || true
    opam update -q default >/dev/null 2>&1 || true
fi
if ! opam switch list --short 2>/dev/null | grep -qx "$SWITCH"; then
    log "creating the OCaml $SWITCH switch (compiles OCaml; takes a while)"
    opam switch create "$SWITCH" -y
fi
# --assume-depexts: the caller installed libgmp and pkg-config (see the top
# of this file); otherwise opam wants to run apt or brew itself, which fails
# non-interactively and does not know about nix.
log "installing opam packages"
opam install -y --assume-depexts --switch="$SWITCH" "${PACKAGES[@]}"

# 4. The build, exactly as the README says. The Makefile runs dune through
#    `opam exec --switch=5.1.0`, so no `eval $(opam env)` is needed.
log "building p4spectec"
rm -f "$STAMP"
make -C "$DIR" build >&2
[ -x "$BINARY" ] || { log "make build did not produce $BINARY"; exit 1; }
echo "$P4_SPECTEC_COMMIT" > "$STAMP"
echo "$BINARY"
