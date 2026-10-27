# the Nix profile (dev role tools), when there is one, before the system's; direnv for .envrc files
test -d ~/.nix-profile/bin; and fish_add_path -g ~/.nix-profile/bin
command -q direnv; and direnv hook fish | source
