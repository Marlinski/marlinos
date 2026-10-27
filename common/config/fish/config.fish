# marlinos: fish is the interactive shell (bash stays the login shell and runs scripts;
# ~/.bashrc hands interactive sessions over to fish). Autosuggestions, syntax highlighting and
# completions are built in: no plugins.
status is-interactive || exit

set -g fish_greeting
fish_add_path -g ~/.local/bin

set -gx EDITOR nvim
set -gx SUDO_EDITOR nvim
set -gx BAT_THEME ansi

# Tokyo Night
set -g fish_color_normal c0caf5
set -g fish_color_command 7dcfff
set -g fish_color_keyword bb9af7
set -g fish_color_quote e0af68
set -g fish_color_redirection c0caf5
set -g fish_color_end ff9e64
set -g fish_color_error f7768e
set -g fish_color_param 9d7cd8
set -g fish_color_comment 565f89
set -g fish_color_operator 9ece6a
set -g fish_color_escape bb9af7
set -g fish_color_autosuggestion 565f89
set -g fish_color_valid_path --underline
set -g fish_color_selection --background=283457
set -g fish_color_search_match --background=283457
set -g fish_pager_color_progress 565f89
set -g fish_pager_color_prefix 7dcfff
set -g fish_pager_color_completion c0caf5
set -g fish_pager_color_description 565f89

# files
alias ls 'eza -lh --group-directories-first --icons=auto'
alias lsa 'ls -a'
alias lt 'eza --tree --level=2 --long --icons --git'
alias lta 'lt -a'
alias ff "fzf --preview 'bat --style=numbers --color=always {}'"
abbr -a .. 'cd ..'
abbr -a ... 'cd ../..'
abbr -a .... 'cd ../../..'

# tools (abbreviations expand as you type, so history shows the real command)
abbr -a g git
abbr -a gs 'git status -sb'
abbr -a gd 'git diff'
abbr -a gl 'git log --oneline --graph -20'
abbr -a gcm 'git commit -m'
abbr -a gcam 'git commit -a -m'
abbr -a gcad 'git commit -a --amend'
abbr -a d docker
abbr -a k kubectl
abbr -a decompress 'tar -xzf'

# the bigger helpers stay bash functions (config/bash/functions); fish calls them through bash
for fn in iso2sd format-drive transcode-video-1080p transcode-video-4K img2jpg img2jpg-small img2png
    function $fn --inherit-variable fn
        bash -c 'source ~/.config/bash/functions; "$@"' $fn $fn $argv
    end
end

type -q zoxide; and zoxide init fish --cmd cd | source
type -q fzf; and fzf --fish | source
type -q mise; and mise activate fish | source
type -q starship; and starship init fish | source

# this machine: hosts/<host>/config.fish, if it has one
test -f ~/.config/marlinos/host/config.fish; and source ~/.config/marlinos/host/config.fish
