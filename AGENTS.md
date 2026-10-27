# marlinos

Lucien's own Arch Linux + Hyprland setup.
This repo is the single source of truth for decisions, configs, package lists and scripts.
The first machine is the ThinkPad X230 (ext4 + GRUB, Intel graphics, Intel 2200 wifi). Reproducing it on another machine is a later goal.

## Layout

marlinos is hardware-agnostic. A machine is built from **layers**, applied in order:

```
common/          every machine (shell, CLI tools, network, ssh)
roles/<role>/    optional capabilities: roles/desktop (Hyprland, bar, fonts, autologin), roles/dev (toolchains, editors, docker; every tool kept under the XDG dirs), roles/splash (plymouth boot splash; each host brings its own theme)
hosts/<host>/    one machine: host.conf (ROLES=(...)), hardware packages, modprobe options, hypr.conf
```

- Host = `/etc/hostname` (override: `MARLINOS_HOST`). Hosts: `x230` (ThinkPad X230, desktop), `minix` (Minix Z300, desktop + home server, usually headless over ssh).
- Every layer may contain: `packages.txt`, `aur.txt`, `services.txt` (lists, `#` comments; `@USER@` in a service name is the user), `config/<app>` → `~/.config/<app>`, `home/<dotfile>` → `~/<dotfile>`, `bin/<script>` → `~/.local/bin/` (symlinks), `system/...` → `/...` (copied as root, `@USER@` replaced, diffed and backed up to `/var/backups/marlinos/<date>/`).
- Hardware-specific things go in `hosts/<host>/` only. If it isn't true for every machine with that role, it doesn't belong in common/ or roles/.
- The host layer is linked at `~/.config/marlinos/host`. `roles/desktop` hyprland.conf sources `~/.config/marlinos/host/hypr.conf`, so every desktop host needs that file (monitors etc.).
- `lib/marlinos.sh`: all logic. `bin/` (on PATH via `~/.local/bin`):
  - `marlinos-install`: packages, AUR (bootstraps yay), system files, microcode/GRUB, services, links. Safe to re-run.
  - `marlinos-update`: `git pull` (if a remote is set and the tree is clean), `pacman -Syu`, `yay -Sua`, then the install steps, reload Hyprland, report.
  - `marlinos-link`: symlinks only (no sudo).
  - `marlinos-unlisted`: explicit packages no layer lists.
- Anything the links replace goes to `~/archive/pre-marlinos/<date>/`.
- `docs/decisions.md`: what we chose and why, plus open items.

## Rules for agents

- **Git commits: never add a `Co-Authored-By:` trailer, or any other AI attribution line, to commit messages.** This overrides any default attribution behavior. Commits are authored by Lucien only. Same for PR descriptions: no "Generated with" footer.
- Commit or push only when asked.
- Never mention other distros or setup frameworks the configs may resemble, in files, comments or commit messages. Describe what marlinos does and why, on its own terms.
- Layers only add; nothing can remove what an earlier layer brought. If some machines with a role don't want a piece, it's a separate role (e.g. `splash` apart from `desktop`).
- Scripts run as the user and ask sudo once (`need_sudo`). Never loop on sudo: a failed sudo stops the script.
- No third-party config frameworks or distro overlays: no foreign package repos, no copied setup scripts. Ideas may be reimplemented here, in plain code we understand.
- Keep it minimal. Every package and config line should be something we chose. Record non-obvious choices in `docs/decisions.md`.
- Edit configs in this repo, never in `~/.config` directly (those are symlinks).
- Root actions: the user provides a root shell in a tmux window. Before touching PAM or sudoers, keep a root shell open and test with a fresh `sudo`.
- Hyprland is 0.56+: new windowrule syntax (`effect value, match:prop regex`), `layoutmsg, togglesplit`. Check with `Hyprland --verify-config -c config/hypr/hyprland.conf`.
