# Decisions

Newest first. One line of what, one line of why.

## 2026-10-27: passwords off Google, remote help
- **Passwords: KeePassXC**, one database (`~/.local/share/keepass/Passwords.kdbx`, out of sight),
  imported from Google Password Manager and the old password notes. The browsers' own password
  managers are off (Firefox and Chrome policies); the KeePassXC-Browser extension is installed in
  both, connected through native-messaging manifests shipped in `system/` (so KeePassXC never
  writes its own into the browser profiles). The phone uses KeePassDX on the same file.
- **Sync: Syncthing over the mesh only** (`bin/sync-mesh`): no global/local discovery, relays,
  NAT punching or usage reports; each peer is `tcp://<name>.mesh:22000`, so nothing syncs
  outside WireGuard and no third-party server learns the devices. The folder keeps the last 10
  versions of each file, a cheap undo for a bad merge. Device IDs and keys stay in each machine's
  Syncthing state, not in the repo.
- **Syncthing runs as the system template unit `syncthing@<user>`**: `services.txt` accepts
  `@USER@`, and install now enables *and starts* the listed services.
- **Remote help: GNOME desktop sharing (RDP)** on jeanne, of her own session, reachable only on
  the mesh (her firewalld zone for the tunnel allows rdp); `remote-help <host>` opens it in
  Remmina. No password is kept in cleartext anywhere: it lives in the keyrings.
- **tmux and screen in Tokyo Night, no plugins** (`common/config/tmux/tmux.conf`, `common/home/.screenrc`):
  the existing key bindings kept (prefix Ctrl+Space, Alt shortcuts), a pill-style bar, popups for
  lazygit and a scratch shell; prefix s stays tmux's session tree with previews. screen 5 takes `#RRGGBB` colors (`truecolor on`).
- **Bluetooth: bluetui** (a TUI, like nmtui) instead of blueman, and no tray applets: Remmina's
  is hidden by `config/autostart/remmina-applet.desktop` (`Hidden=true`) and its tray setting off.
- **Music: the official Spotify app** (AUR), tiled like any window. The bar shows a monochrome
  note (`bin/music-status`, from its MPRIS) instead of a logo; click or Super+M opens it or jumps
  to it, right click plays/pauses, scroll skips. The TUIs were tried first: spotify_player's
  built-in second login is rejected by Spotify (October 2026, aome510/spotify-player#1107), and
  ncspot was slow and clumsy.
- **Dev tools from Nix** (`roles/dev/flake.nix`, pinned by `flake.lock`): toolchains (go,
  rustup, node, python, uv), language servers and formatters, network tools (nmap, traceroute,
  iperf3, tcpflow), direnv + nix-direnv. One `buildEnv` installed into the user's Nix profile as
  `dev`; marlinos-install/update add or upgrade it (any layer may carry a `flake.nix`). Same
  versions on every machine; `nix flake update` in `roles/dev` + commit moves them all. Per-project
  shells: a `flake.nix` in the project and `use flake` in its `.envrc`.
  Stays on pacman: clang/llvm (build against the system's libraries; a Nix `cc` on PATH would
  break AUR builds), mtr and wireshark (raw-socket capabilities set by their packages), docker
  (a system service), the GUI editors. The x230 keeps `/nix` on `/home` (`nix.mount`): its `/`
  is small.
- **Cheat sheets: `cheat <topic>`** (`common/bin/cheat`, data in `common/config/cheat/*.cheat`):
  one renderer, plain data files (`command :: description`, `## section`, `> note`), Tokyo Night
  colors, wrapped to the terminal width (never horizontal scrolling), columns on wide screens,
  `less` when taller than the screen. The Hyprland sheet reads the `bind(...)` lines of the live
  config. Each sheet has a launcher entry (Super+Space, "<topic> cheat sheet").
- **Hyprland config in Lua** (`hyprland.lua`, `hosts/<host>/hypr.lua`): Hyprland 0.56 warns at
  login that the `.conf` format is removed in 0.57. Same settings and keys, one `bind()` helper
  that keeps the descriptions; scripts and hypridle send Lua dispatchers and read `hyprctl clients -j`.
- **tmux activity:** a background window with new output has its name in bold yellow, no extra mark.

## 2026-10-27: package lists, shell, dev role
- **Every installed package is listed in a layer, or it goes.** `marlinos-unlisted` is the review: what isn't listed is removed (or marked as a dependency when something listed needs it). Cleaned both machines (x230: 280 unlisted, from 2013 on).
- **Official repos first, the AUR only when nothing else exists** (wl-screenrec, google-chrome, claude-code, minix's printer driver, urbanterror): AUR packages are unreviewed build scripts. Nix or Flatpak may replace these later.
- **New `roles/dev`** (both laptops): go, rustup, node, python + uv, clang/llvm, docker, network tools, VS Code, opencode, emacs. `config/environment.d/50-dev.conf` moves every toolchain under the XDG dirs (`~/.local/share/{cargo,rustup,go}`, `~/.cache/{npm,go/mod}`, binaries in `~/.local/bin`); `dev-clean` lists and deletes build dirs untouched for 30 days.
- **fish for typing, bash for the rest**: bash stays the login shell (tty1 autologin starts Hyprland from `~/.bash_profile`) and runs scripts; `~/.bashrc` hands interactive sessions to fish. Built-in autosuggestions, highlighting, completions: no plugin framework. Starship prompt, Tokyo Night.
- **Emacs from built-ins only** (modus-vivendi tinted Tokyo Night, fido, completion-preview, which-key, eglot): looks right on first start, downloads nothing.
- **Firefox next to Chrome**, hardened by `/etc/firefox/policies/policies.json` (no telemetry, studies, Pocket, sponsored content or ad measurement; strict tracking protection; uBlock Origin). Brave would need the AUR.
- **Audio: pipewire on every desktop** (x230 leaves PulseAudio).

## 2026-10-26: minix host
- **Minix Z300 = desktop role + home server** (docker, k3s), converted in place (no reinstall). It's managed remotely over ssh, so every boot change must fail safe.
- **Splash is its own role** (`roles/splash`: plymouth + keep the last frame), out of `roles/desktop`, since layers only add. **Each host draws its own theme**: hutong lives in `hosts/x230`; minix has homelab (`hosts/minix/src/homelab`), its own desk at night with the cat asleep on the Minix box, the router, and a monitor scrolling the server's status.
- **Boot: stock `linux` as a UKI, systemd-boot.** Its AMI firmware ignores `BootNext` and moves `\EFI\BOOT\BOOTX64.EFI` ("UEFI OS") back to the front of BootOrder, so that file *is* systemd-boot. One-shot tests use `bootctl set-oneshot`.
- **`panic=10 rd.emergency=reboot`** on the kernel command line: an initramfs failure reboots instead of hanging a headless box.
- **Wifi: NetworkManager + iwd, power save off.** ssh reaches it over wifi. NetworkManager config changes apply at next boot; never restart NM remotely.
- **sshd on 4242, keys only**, with a fail2ban jail on that port. k3s comes from its install script, not a package.
- **Firewall: one nftables table** (`/etc/nftables/firewall.nft`, `table inet firewall`, IPv4 + IPv6) loaded by `firewall.service`, replacing ufw and a frozen iptables snapshot that left IPv6 wide open. Internet: ssh 4242 + ping. LAN: + k3s API, port 4444 (tcp/udp, for ad-hoc nc and test servers), mDNS/SSDP; docker-published ports and k3s host ports only from private ranges. docker and k3s keep their own iptables-nft tables; this table only adds drops. Not `nftables.service`: it flushes the whole ruleset on stop.
- **WireGuard hub** (`wg-quick@wg0`, 10.77.0.0/24, udp 51821 forwarded by the Freebox; 51820 is left to the Freebox's own WireGuard server). Split tunnel: peers reach minix and each other, not the internet through it. Public keys in the repo, private keys only on each machine (`/etc/wireguard/wg0.key`, loaded by `PostUp`). Peers that can't make their own key (phone, jeanne's ThinkPad) get one made on minix, in `/etc/wireguard/clients/`. Peer-to-peer goes through minix: a `FORWARD -i wg0 -o wg0` accept, since docker sets the FORWARD policy to DROP.
- **Mesh DNS: `*.mesh`** (`jeanne.mesh`, `x230.mesh`; `*.minix.mesh` all point to minix) from dnsmasq on 10.77.0.1, wg0 only. Split DNS: every machine runs systemd-resolved (common layer, NetworkManager hands it per-link DNS), and wg0's PostUp sends only `~mesh` there, so each wifi keeps its own DNS (captive portals). The Android app can't split: the phone sends all DNS to minix while its tunnel is up, and dnsmasq forwards the rest.
- **Never suspends** (`sleep.conf.d/no-sleep.conf`): the desktop role's 30 min idle suspend put it to sleep and cut ssh. Screen off and lock still apply.
- **Reboots must finish on their own.** `stop-k3s-pods.service` runs `k3s-killall.sh` at shutdown, after k3s has stopped (k3s leaves its pods running, and the shutdown then waited on them and hung). Stop timeout 30 s, and the hardware watchdog resets a reboot stuck for 2 min.
- **The splash lasts until the server is up** (plymouth-quit after network-online, docker, k3s): otherwise it quits after ~4 s and uwsm prints "waiting for graphical.target" until k3s is ready. k3s gets a 3 min start timeout so it can't hold the splash forever.

## 2026-10-26: layers (hardware-agnostic)
- **common → roles → host layers**, same shape each (packages, aur, services, config, home, bin, system). Lets the Minix Z300 reuse everything, as a server (`ROLES=()`) or a desktop (`ROLES=(desktop)`). That's still undecided.
- **Host id = hostname.** Renamed this machine `archlinux` → `x230`. DMI names are unreliable on mini PCs ("Default string").
- **Per-host Hyprland bits** in `hosts/<host>/hypr.lua` (was `hypr.conf`), run last.
- **Audio:** this machine runs PulseAudio (pipewire is installed too). pipewire-pulse is not forced; switching is an open item.

## 2026-10-26: install/update scripts
- **One update command, ours:** `bin/marlinos-update`. It's plain and readable: pacman, yay, then the same idempotent steps as install. No migration framework: the repo state *is* the desired state, re-applied each time.
- **sudo asked once, never retried.** Unattended sudo retry loops trip faillock and lock the account.
- **System files are whole files copied from `system/`**, with a diff shown and a backup kept. No sed-editing of /etc.
- **Per-host layer** (`hosts/x230/`): the iwlwifi/i915 modprobe options, firmware, intel-ucode, libva-intel-driver (Ivy Bridge HD 4000 → i965 VA-API).
- **intel-ucode added** (wasn't installed): CPU microcode fixes; GRUB is regenerated to load it.
- **pacman.conf is not managed yet** (host-specific CacheDir `/home/pacman-cache`).

## 2026-10-26: foundations
- **No config framework.** Only Arch repos + AUR, no foreign package repo or mirror, no unattended migration scripts. Everything installed is something we chose.
- **Configs live in this repo**, symlinked into `~/.config` by `bin/marlinos-link`. One place to edit, git history for every change.
- **Login:** getty autologin on tty1 + `~/.bash_profile` starts `uwsm start hyprland.desktop` (no `exec`: a Hyprland crash drops to a shell, not a login loop). hyprlock protects the session.
- **Hyprland config is one file** (`config/hypr/hyprland.lua` since 2026-10-27, `hyprland.conf` before). It's small enough to read top to bottom.
- **Launcher: fuzzel.** Walker 2 needs the elephant daemon + provider plugins; fuzzel is one binary that reads .desktop files.
- **Theme: Tokyo Night colors written directly in each config.** No theme switcher, no symlink layer. Palette: bg `#1a1b26`, fg `#c0caf5`, blue `#7aa2f7`, grey `#414868`, red `#f7768e`, yellow `#e0af68`.
- **No wallpaper:** solid background (`misc:background_color`). Nothing to run, nothing to download.
- **Keyboard:** `us` + compose on CapsLock, as before.
- **Idle:** dim 4 min, lock 5 min, screen off 5.5 min, suspend 30 min.
- **Volume/brightness:** plain `wpctl` and `brightnessctl` bindings, no OSD daemon.
- **Commits:** no AI co-author trailers (see AGENTS.md).

## Open
- x230 has no firewall (minix has one): a laptop firewall for roles/desktop.
- Replace the remaining AUR packages (Nix? Flatpak? the vendors' own installers?).
- 45 `.pacnew` files in /etc to merge (some from 2013).
- `/etc/modprobe.d/modprobe.conf` i915 options (`i915_enable_rc6`, `i915_enable_fbc`, `lvds_downclock`) date from 2013 and are obsolete on current kernels; review.
- Wifi card crashes (Intel 2200): memtest86+, `11n_disable=2` test, or swap for an Intel 6205.
