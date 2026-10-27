# The systemd user environment (~/.config/environment.d/*.conf: KEY=VALUE, $HOME expanded) for
# shells that didn't come from the desktop session, like ssh logins.
for f in ~/.config/environment.d/*.conf
    test -f $f; or continue
    for line in (string match -rv '^\s*(#|$)' < $f)
        set -l kv (string split -m1 = $line)
        set -q $kv[1]; and continue
        set -gx $kv[1] (string replace -a '$HOME' $HOME (string replace -a '${HOME}' $HOME $kv[2]))
    end
end
