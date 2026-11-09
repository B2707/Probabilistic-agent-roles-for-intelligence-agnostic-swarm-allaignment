#!/bin/bash
# Bader, 9 Nov 02:23: only C seed 1 runs (Cn100-6-luna-s1, Cn100-61-sol-s1). Pauses the laptop's C seed-2 runs with
# TERM (no run_end; `uv run swarm resume runs/<run>` continues each later) and marks them .watch-failed so no watcher
# resumes them. Restarts the C resume watcher for the two seed-1 arms only.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git show origin/main:scripts/laptop_c_s1_only.sh > scripts/laptop_c_s1_only.sh && bash scripts/laptop_c_s1_only.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs; P=$M/.prod
log() { echo "$(date '+%F %T') c_s1_only: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
cd "$M" || exit 1

for p in $(pgrep -f 'runs/arm_queue') $(pgrep -f 'runs/resume_watch-c.sh'); do kill "$p" 2>/dev/null && log "stopped shell $p"; done
sleep 1
for a in Cn100-6-luna-s2 Cn100-61-sol-s2; do
  for d in "$R/$a"-2*/; do
    [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
    echo "paused by Bader 9 Nov 02:23; do not auto-resume" > "$d.watch-failed"
    pids=$(pgrep -f -- "swarm (run|resume).*$d" || true)
    [ -n "$pids" ] && kill -TERM $pids 2>/dev/null
    for i in $(seq 1 15); do pgrep -f -- "swarm (run|resume).*$d" >/dev/null || break; sleep 1; done
    rnd=$(grep -o '"type": "round_start", "round": [0-9]*' "$d/events.jsonl" | tail -1 | grep -o '[0-9]*$')
    log "paused $n at round ${rnd:-?}"; note "laptop_c_s1_only: paused $n at round ${rnd:-?}; only C seed 1 runs"
  done
done
cp scripts/resume_watch.sh "$R/resume_watch-c.sh"
WAIT=150 MAX=30 PROD="$P" nohup python3 scripts/detach.py /bin/bash "$R/resume_watch-c.sh" \
  Cn100-6-luna-s1 Cn100-61-sol-s1 >> "$R/queue.log" 2>&1 < /dev/null &
log "resume watcher restarted for Cn100-6-luna-s1 and Cn100-61-sol-s1 only"
sleep 3
echo "===== live (should be the two seed-1 runs only)"; ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE 'runs/[^ ]+' | sort -u
echo "===== done"
