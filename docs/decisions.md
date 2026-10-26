# Decisions

Newest first. One line of what, one line of why.

## 2026-10-26: minix host
- **Minix Z300 = desktop role + home server** (docker, k3s), converted in place (no reinstall). It's managed remotely over ssh, so every boot change must fail safe.
- **Splash is its own role** (`roles/splash`: plymouth + keep the last frame), out of `roles/desktop`, since layers only add. **Each host draws its own theme**: hutong lives in `hosts/x230`; minix has homelab (`hosts/minix/src/homelab`), its own desk at night with the cat asleep on the Minix box, the router, and a monitor scrolling the server's status.
- **Boot: stock `linux` as a UKI, systemd-boot.** Its AMI firmware ignores `BootNext` and moves `\EFI\BOOT\BOOTX64.EFI` ("UEFI OS") back to the front of BootOrder, so that file *is* systemd-boot. One-shot tests use `bootctl set-oneshot`.
- **`panic=10 rd.emergency=reboot`** on the kernel command line: an initramfs failure reboots instead of hanging a headless box.
- **Wifi: NetworkManager + iwd, power save off.** ssh reaches it over wifi. NetworkManager config changes apply at next boot; never restart NM remotely.
- **sshd on 4242, keys only**, with a fail2ban jail on that port. k3s comes from its install script, not a package.
- **Never suspends** (`sleep.conf.d/no-sleep.conf`): the desktop role's 30 min idle suspend put it to sleep and cut ssh. Screen off and lock still apply.
- **Reboots must finish on their own.** `stop-k3s-pods.service` runs `k3s-killall.sh` at shutdown, after k3s has stopped (k3s leaves its pods running, and the shutdown then waited on them and hung). Stop timeout 30 s, and the hardware watchdog resets a reboot stuck for 2 min.
- **The splash lasts until the server is up** (plymouth-quit after network-online, docker, k3s): otherwise it quits after ~4 s and uwsm prints "waiting for graphical.target" until k3s is ready. k3s gets a 3 min start timeout so it can't hold the splash forever.

## 2026-10-26: layers (hardware-agnostic)
- **common → roles → host layers**, same shape each (packages, aur, services, config, home, bin, system). Lets the Minix Z300 reuse everything, as a server (`ROLES=()`) or a desktop (`ROLES=(desktop)`). That's still undecided.
- **Host id = hostname.** Renamed this machine `archlinux` → `x230`. DMI names are unreliable on mini PCs ("Default string").
- **Per-host Hyprland bits** in `hosts/<host>/hypr.conf`, sourced last.
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
- **Hyprland config is one file** (`config/hypr/hyprland.conf`). It's small enough to read top to bottom.
- **Launcher: fuzzel.** Walker 2 needs the elephant daemon + provider plugins; fuzzel is one binary that reads .desktop files.
- **Theme: Tokyo Night colors written directly in each config.** No theme switcher, no symlink layer. Palette: bg `#1a1b26`, fg `#c0caf5`, blue `#7aa2f7`, grey `#414868`, red `#f7768e`, yellow `#e0af68`.
- **No wallpaper:** solid background (`misc:background_color`). Nothing to run, nothing to download.
- **Keyboard:** `us` + compose on CapsLock, as before.
- **Idle:** dim 4 min, lock 5 min, screen off 5.5 min, suspend 30 min.
- **Volume/brightness:** plain `wpctl` and `brightnessctl` bindings, no OSD daemon.
- **Commits:** no AI co-author trailers (see AGENTS.md).

## Open
- Undecided apps and services: docker, printing (cups/avahi), apps (signal, spotify, chrome, localsend, nautilus, viewers), swayosd/hyprsunset/yaru. Login-attempt and firewall policy to define.
- Package list reconciliation (`marlinos-unlisted`): 321 explicit packages not in any list (lots from 2013–2025), review and remove or list them.
- 45 `.pacnew` files in /etc to merge (some from 2013).
- `/etc/modprobe.d/modprobe.conf` i915 options (`i915_enable_rc6`, `i915_enable_fbc`, `lvds_downclock`) date from 2013 and are obsolete on current kernels; review.
- Wifi card crashes (Intel 2200): memtest86+, `11n_disable=2` test, or swap for an Intel 6205.
- nvim config (LazyVim starter in `~/.config/nvim`) not yet in the repo.
- Audio: move from PulseAudio to pipewire-pulse (what Arch recommends now)?
