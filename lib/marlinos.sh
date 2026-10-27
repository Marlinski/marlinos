# Shared functions for the marlinos scripts. Sourced, not run.
#
# A machine is built from layers, applied in order:
#   common/  ->  roles/<role>/ (listed in hosts/<host>/host.conf)  ->  hosts/<host>/
# Each layer may contain:
#   packages.txt  aur.txt  services.txt   lists, one item per line, # comments (@USER@ in services)
#   config/<app>  -> ~/.config/<app>      (symlinked)
#   home/<file>   -> ~/<file>             (symlinked)
#   bin/<script>  -> ~/.local/bin/<script> (symlinked)
#   system/...    -> /...                 (copied as root, @USER@ replaced in text files, backed up)
#   src/          sources that generate files elsewhere in the layer (not applied)
#   flake.nix     a Nix environment, installed into the user's Nix profile (named after the layer)
# The host layer is also linked as ~/.config/marlinos/host, for files like hypr.conf.
#
# Scripts run as the user and call sudo for system steps. sudo is asked once up front;
# if it fails we stop (no retry loops: they trigger faillock and lock the account).

set -euo pipefail

REPO=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)
STAMP=$(date +%F-%H%M%S)
SYS_BACKUP=/var/backups/marlinos/$STAMP
HOME_BACKUP=$HOME/archive/pre-marlinos/$STAMP

HOST=${MARLINOS_HOST:-$(cat /etc/hostname)}
HOST_DIR=$REPO/hosts/$HOST

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }

# Layer directories for this machine, in apply order
layers() {
  echo "$REPO/common"
  if [[ -f $HOST_DIR/host.conf ]]; then
    local ROLES=()
    # shellcheck source=/dev/null
    source "$HOST_DIR/host.conf"
    local r
    for r in "${ROLES[@]}"; do
      [[ -d $REPO/roles/$r ]] || { warn "unknown role '$r' in $HOST_DIR/host.conf"; exit 1; }
      echo "$REPO/roles/$r"
    done
    echo "$HOST_DIR"
  fi
}

describe() {
  local l out=()
  for l in $(layers); do out+=("${l#$REPO/}"); done
  echo "host '$HOST': ${out[*]}"
  [[ -f $HOST_DIR/host.conf ]] || warn "no hosts/$HOST/host.conf: only common/ applies (set the hostname or MARLINOS_HOST)"
}

need_sudo() {
  step "sudo (asked once)"
  sudo -v || { warn "sudo failed, stopping"; exit 1; }
  # keep the timestamp fresh without ever prompting (-n), stop when the script exits
  while true; do sudo -n -v 2>/dev/null; sleep 50; done &
  SUDO_KEEPALIVE=$!
  trap 'kill $SUDO_KEEPALIVE 2>/dev/null || true' EXIT
}

# Items from a list file name across all layers (comments and blanks stripped)
layer_list() {
  local name=$1 l
  for l in $(layers); do
    [[ -f $l/$name ]] || continue
    sed 's/#.*//; s/\s//g' "$l/$name" | grep . || true
  done
}

missing_packages() { layer_list "$1" | while read -r p; do pacman -Q "$p" &>/dev/null || echo "$p"; done; }

install_repo_packages() {
  step "Packages (official repos)"
  local missing
  mapfile -t missing < <(missing_packages packages.txt)
  if ((${#missing[@]})); then
    info "installing: ${missing[*]}"
    sudo pacman -S --needed --noconfirm "${missing[@]}"
  else
    info "all present"
  fi
}

ensure_yay() {
  command -v yay &>/dev/null && return
  step "Bootstrap yay"
  sudo pacman -S --needed --noconfirm git base-devel
  local tmp
  tmp=$(mktemp -d)
  git clone --depth 1 https://aur.archlinux.org/yay-bin.git "$tmp/yay-bin"
  (cd "$tmp/yay-bin" && makepkg -si --noconfirm)
  rm -rf "$tmp"
}

install_aur_packages() {
  step "Packages (AUR)"
  ensure_yay
  local missing
  mapfile -t missing < <(missing_packages aur.txt)
  if ((${#missing[@]})); then
    info "installing: ${missing[*]}"
    yay -S --needed --noconfirm "${missing[@]}"
  else
    info "all present"
  fi
}

# Copy each layer's system/ into /. Changed files are diffed and backed up first.
apply_system_files() {
  step "System files"
  local changed=() l src dst tmp
  for l in $(layers); do
    [[ -d $l/system ]] || continue
    while IFS= read -r -d '' src; do
      dst=${src#$l/system}
      tmp=$(mktemp)
      if grep -Iq . "$src"; then   # text: fill in @USER@
        sed "s/@USER@/$USER/g" "$src" >"$tmp"
      else                         # binary (images...): as is
        cp "$src" "$tmp"
      fi
      if ! sudo cmp -s "$tmp" "$dst"; then
        if sudo test -e "$dst"; then
          sudo install -Dm644 "$dst" "$SYS_BACKUP$dst"
          if grep -Iq . "$tmp"; then sudo diff -u "$dst" "$tmp" | sed 's/^/    /' || true; fi
        fi
        sudo install -Dm644 "$tmp" "$dst"
        info "installed $dst (from ${l#$REPO/})"
        changed+=("$dst")
      fi
      rm -f "$tmp"
    done < <(find "$l/system" -type f -print0)
  done
  if ((${#changed[@]} == 0)); then
    info "up to date"
    return 0
  fi
  if sudo test -d "$SYS_BACKUP"; then info "previous versions in $SYS_BACKUP"; fi

  if printf '%s\n' "${changed[@]}" | grep -q '^/etc/systemd/'; then
    sudo systemctl daemon-reload
  fi
  if printf '%s\n' "${changed[@]}" | grep -qE '^(/etc/(plymouth|mkinitcpio|kernel/)|/usr/share/plymouth/)'; then
    sudo mkinitcpio -P
  fi
  if printf '%s\n' "${changed[@]}" | grep -qE '^/etc/(default/grub|grub.d/)'; then
    sudo grub-mkconfig -o /boot/grub/grub.cfg
  fi
  if printf '%s\n' "${changed[@]}" | grep -q '^/etc/modprobe.d/'; then
    warn "modprobe options changed: reboot to apply"
  fi
}

# GRUB loads a microcode image only once grub.cfg is regenerated
ensure_grub_microcode() {
  [[ -f /boot/grub/grub.cfg ]] || return 0
  ls /boot/*-ucode.img &>/dev/null || return 0
  sudo grep -q -- '-ucode.img' /boot/grub/grub.cfg && return 0
  step "GRUB: add CPU microcode"
  sudo grub-mkconfig -o /boot/grub/grub.cfg
}

# /etc/resolv.conf -> systemd-resolved's stub, once resolved is enabled (common/services.txt).
# NetworkManager then hands it each connection's DNS; connections stay up through the switch.
ensure_resolved_stub() {
  systemctl is-enabled -q systemd-resolved 2>/dev/null || return 0
  [[ $(readlink /etc/resolv.conf) == ../run/systemd/resolve/stub-resolv.conf ]] && return 0
  step "DNS: systemd-resolved"
  sudo systemctl start systemd-resolved
  sudo ln -sf ../run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
  sudo nmcli general reload conf,dns-rc
  info "/etc/resolv.conf -> systemd-resolved"
}

enable_services() {
  step "Services"
  local u
  for u in $(layer_list services.txt); do
    u=${u//@USER@/$USER}   # syncthing@@USER@.service
    if [[ $(systemctl is-enabled "$u" 2>/dev/null) != enabled ]]; then
      sudo systemctl enable --now "$u"
      info "enabled and started $u"
    fi
  done
  info "ok"
}

# Symlink src -> dst; a real file or foreign link at dst is moved to $HOME_BACKUP
link_one() {
  local src=$1 dst=$2
  [[ -L $dst && $(readlink "$dst") == "$src" ]] && return 0
  if [[ -e $dst || -L $dst ]]; then
    mkdir -p "$(dirname "$HOME_BACKUP/${dst#$HOME/}")"
    mv "$dst" "$HOME_BACKUP/${dst#$HOME/}"
    info "backed up ~/${dst#$HOME/}"
  fi
  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  info "linked ~/${dst#$HOME/} -> ${src#$REPO/}"
}

link_configs() {
  step "Config links"
  local l f
  for l in $(layers); do
    for f in "$l"/config/*; do [[ -e $f ]] && link_one "$f" ~/.config/"$(basename "$f")"; done
    for f in "$l"/home/.[!.]*; do [[ -e $f ]] && link_one "$f" ~/"$(basename "$f")"; done
    for f in "$l"/bin/*; do [[ -e $f ]] && link_one "$f" ~/.local/bin/"$(basename "$f")"; done
  done
  for f in "$REPO"/bin/*; do link_one "$f" ~/.local/bin/"$(basename "$f")"; done
  if [[ -d $HOST_DIR ]]; then link_one "$HOST_DIR" ~/.config/marlinos/host; fi
  info "ok"
}

# Each layer's flake.nix: added to the user's Nix profile, or upgraded to what its flake.lock pins
install_nix_profiles() {
  command -v nix &>/dev/null || return 0
  local l name nixc=(nix --extra-experimental-features 'nix-command flakes')
  "${nixc[@]}" store info >/dev/null   # the first connection makes the daemon create /nix/store
  for l in $(layers); do
    [[ -f $l/flake.nix ]] || continue
    name=$(basename "$l")
    step "Nix profile: $name (${l#$REPO/})"
    if "${nixc[@]}" profile list --json | jq -e --arg n "$name" '.elements | has($n)' >/dev/null; then
      "${nixc[@]}" profile upgrade "$name"
    else
      "${nixc[@]}" profile add "path:$l"
    fi
    info "ok"
  done
}

check_hyprland_config() {
  [[ -e ~/.config/hypr/hyprland.conf ]] && command -v Hyprland &>/dev/null || return 0
  step "Hyprland config check"
  Hyprland --verify-config -c ~/.config/hypr/hyprland.conf 2>&1 | tail -1 | sed 's/^/    /'
}

reload_session() {
  [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]] || return 0
  if hyprctl reload >/dev/null; then info "Hyprland reloaded"; fi
}

report() {
  step "Report"
  local listed unmanaged pacnew
  listed=$(mktemp)
  { layer_list packages.txt; layer_list aur.txt; } | sort -u >"$listed"
  unmanaged=$(pacman -Qeq | sort | comm -23 - "$listed" | wc -l)
  info "explicit packages not in any layer: $unmanaged (see: marlinos-unlisted)"
  rm -f "$listed"

  pacnew=$( (find /etc -name '*.pacnew' 2>/dev/null || true) | wc -l)
  if ((pacnew)); then
    info ".pacnew files to merge in /etc: $pacnew"
  fi

  if [[ ! -d /usr/lib/modules/$(uname -r) ]]; then
    warn "kernel updated (running $(uname -r) is no longer installed): reboot"
  fi
  describe | sed 's/^/    /'
}
