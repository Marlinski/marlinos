function open --description 'open with the default app, detached'
    xdg-open $argv >/dev/null 2>&1 &
    disown
end
