#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc

# Desktop hosts: start Hyprland on tty1 (autologin). No exec: if Hyprland dies you land in a shell.
# Quiet, so the splash frame stays clean; uwsm logs go to the journal (journalctl --user -b).
if [[ -z $WAYLAND_DISPLAY && $XDG_VTNR == 1 ]] && command -v uwsm >/dev/null && uwsm check may-start; then
  setterm --cursor off
  uwsm start hyprland.desktop >/dev/null 2>&1
  setterm --cursor on
  clear
fi
