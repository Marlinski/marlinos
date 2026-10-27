# Shell defaults: ~/.config/bash
source ~/.config/bash/rc

# Interactive sessions (terminals, ssh, tmux) continue in fish; bash stays the login shell, runs
# scripts and `bash -c`. Not on the tty1 login before Hyprland starts (~/.bash_profile does that),
# and not when fish itself started this bash (type `bash` in fish to get one).
if [[ $- == *i* && -z ${BASH_EXECUTION_STRING:-} && -z ${MARLINOS_NO_FISH:-} ]] && command -v fish >/dev/null &&
  [[ $(ps -o comm= -p $PPID) != fish ]] && ! [[ ${XDG_VTNR:-} == 1 && -z ${WAYLAND_DISPLAY:-} ]]; then
  shopt -q login_shell && exec fish --login
  exec fish
fi

# Add your own exports, aliases, and functions here.
#
# Make an alias for invoking commands you use constantly
# alias p='python'
