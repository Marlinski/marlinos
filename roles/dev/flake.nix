{
  # The dev role's tools, from nixpkgs, pinned by flake.lock: toolchains, language servers and
  # formatters, network tools. marlinos installs it into the user's Nix profile (as "dev");
  # nix flake update here + commit moves every machine to the same new versions.
  # C/C++ compilers (clang, llvm, gcc) stay on pacman: they must match the system's libraries.
  description = "marlinos dev role";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in {
      packages.x86_64-linux.default = pkgs.buildEnv {
        name = "marlinos-dev";
        paths = with pkgs; [
          # toolchains (rustup keeps installing Rust itself, under RUSTUP_HOME)
          go
          rustup
          nodejs
          python3
          uv
          inotify-tools
          opencode

          # language servers, formatters
          lua-language-server
          (lib.hiPrio rust-analyzer)   # over rustup's proxy of the same name
          gopls
          pyright
          ruff
          typescript
          typescript-language-server
          bash-language-server
          yaml-language-server
          marksman
          taplo
          stylua
          prettier
          shfmt

          # network tools (mtr and wireshark stay on pacman: they need raw-socket capabilities)
          nmap
          traceroute
          iperf3
          tcpflow

          # per-project environments: direnv + nix-direnv (use flake in an .envrc)
          direnv
          nix-direnv
        ];
      };
    };
}
