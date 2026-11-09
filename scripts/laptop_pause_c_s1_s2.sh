#!/bin/bash
# Bader, 9 Nov 02:16: only C seed 3 runs now (Cn100-6-luna-s3-b2 and Cn100-61-sol-s3-b2 on his Mac), so the account's
# rate limit goes to them. Pauses every C seed-1 and seed-2 run on the laptop with TERM: no run_end is written, so no
# watcher or queue resumes them, and `uv run swarm resume runs/<run>` continues each from its last saved turn later.
# Stops the laptop's C queue and C resume watcher first, so nothing restarts or starts a run while this runs.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git show origin/main:scripts/laptop_pause_c_s1_s2.sh > scripts/laptop_pause_c_s1_s2.sh && bash scripts/laptop_pause_c_s1_s2.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs
log() { echo "$(date '+%F %T') pause_c_s1_s2: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
cd "$M" || exit 1

for s in arm_queue resume_watch-c.sh; do
  for p in $(pgrep -f "runs/$s"); do kill "$p" 2>/dev/null && log "stopped $s shell $p"; done
done
sleep 1
for a in Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2; do
  for d in "$R/$a"-2*/; do
    [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
    pids=$(pgrep -f -- "swarm (run|resume).*$d" || true)
    if [ -z "$pids" ]; then log "$n not running"; continue; fi
    kill -TERM $pids 2>/dev/null
    for i in $(seq 1 15); do pgrep -f -- "swarm (run|resume).*$d" >/dev/null || break; sleep 1; done
    rnd=$(grep -o '"type": "round_start", "round": [0-9]*' "$d/events.jsonl" | tail -1 | grep -o '[0-9]*$')
    log "paused $n at round ${rnd:-?}"; note "laptop_pause_c_s1_s2: paused $n at round ${rnd:-?} (TERM, no run_end); only C seed 3 runs now (Mac)"
  done
done
echo "===== still live (should be empty)"; ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE 'runs/[^ ]+' | sort -u
echo "===== done"
