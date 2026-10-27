function compress --description 'dir -> dir.tar.gz'
    set -l d (string trim -r -c / $argv[1])
    tar -czf $d.tar.gz $d
end
