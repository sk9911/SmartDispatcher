#!/bin/zsh
cd "/var/folders/y7/9h6hg8gd22gdfnv3l3_dfdrw0000gn/T/tmp.nH5olDMmot/regret" || exit 99
run() { local name=$1; shift; local t0=$(date +%s); echo "=== $name start $(date '+%H:%M:%S')"; "$@"; local rc=$?; local t1=$(date +%s); echo "=== $name rc=$rc elapsed=$((t1-t0))s end $(date '+%H:%M:%S')"; return $rc; }
run sync uv sync || exit 1
run fetch uv run regret fetch || exit 2
run compute uv run regret compute || exit 3
run report env REGRET_BLOCK_NETWORK=1 uv run regret report || exit 4
echo "=== ALL OK"
