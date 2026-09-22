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
          ];
          env = {
            # uv uses the Nix-provided interpreter instead of downloading one.
            UV_PYTHON = "${pkgs.python313}/bin/python3";
            UV_PYTHON_DOWNLOADS = "never";
          };
        };
      });

      formatter = forEachSystem (pkgs: pkgs.nixfmt-rfc-style);
    };
}
