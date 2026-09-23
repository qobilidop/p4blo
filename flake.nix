{
  description = "p4blo: P4's semantic core as an IR, architecture-free";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forEachSystem (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python313 # interpreter; packages are managed by uv
            pkgs.uv
            pkgs.buf # schema lint and codegen driver
            pkgs.protobuf # protoc, used by buf's protoc_builtin plugins
            pkgs.elan # Lean toolchain manager; lean/lean-toolchain pins the version
            pkgs.nodejs # runtime for the pyright wheel, so it never downloads its own
          ];
          env = {
            # uv uses the Nix-provided interpreter instead of downloading one.
            UV_PYTHON = "${pkgs.python313}/bin/python3";
            UV_PYTHON_DOWNLOADS = "never";
          };
        };
        # What oracle/build.sh needs to build P4-SpecTec: `nix develop .#oracle
        # -c oracle/build.sh`. Kept out of the default shell because only the
        # oracle needs an OCaml toolchain.
        oracle = pkgs.mkShell {
          packages = [
            pkgs.git
            pkgs.gnumake
            pkgs.opam
            pkgs.gmp
            pkgs.pkgconf
          ];
        };
      });

      formatter = forEachSystem (pkgs: pkgs.nixfmt-rfc-style);
    };
}
