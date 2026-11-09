#!/bin/bash
# Bader, 9 Nov 02:10: stop everything that is not C, C must land before the deadline.
#   1. Stops the laptop's queue starter shells (never a shell that is minding a live run), so no arm starts while this runs.
#   2. Pauses Dn100-6-luna-s1 and En100-6-luna-s1 with TERM. No run_end is written, so no watcher or queue resumes
#      them; `uv run swarm resume runs/<run>` continues each from its last saved turn later.
#   3. Restarts the resume watcher for the laptop's C runs only.
#   4. Starts Cn100-61-sol-s2 (the last C arm; the Mac runs Cn100 luna and sol seed 3) unless it already has a folder.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git show origin/main:scripts/laptop_c_only.sh > scripts/laptop_c_only.sh && bash scripts/laptop_c_only.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs; P=$M/.prod
SLOTS=${SLOTS:-4}
log() { echo "$(date '+%F %T') c_only: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
cd "$M" || exit 1

echo "===== 1. queue starters"
for p in $(pgrep -f 'runs/arm_queue'); do
  if pgrep -P "$p" -f 'swarm (run|resume)' >/dev/null; then log "kept $p (it is minding a live run)"
  else kill "$p" 2>/dev/null && log "stopped queue shell $p"; fi
done
for a in Cn100-6-luna-s3 Cn100-61-sol-s3; do
  ls -d "$R/$a"-2* >/dev/null 2>&1 && log "WARNING: $a has a run folder here too: $(ls -d "$R/$a"-2*). Tell Claude."
done

echo "===== 2. pause D and E"
for a in Dn100-6-luna-s1 En100-6-luna-s1; do
  for d in "$R/$a"-2*/; do
    [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
    pids=$(pgrep -f -- "swarm (run|resume).*$d" || true)
    if [ -z "$pids" ]; then log "$n not running"; continue; fi
    for p in $pids; do pp=$(ps -o ppid= -p "$p" | tr -d ' '); ps -o command= -p "$pp" | grep -q 'arm_queue\|resume_watch' && kill "$pp" 2>/dev/null; done
    kill -TERM $pids 2>/dev/null
    for i in $(seq 1 12); do pgrep -f -- "swarm (run|resume).*$d" >/dev/null || break; sleep 1; done
    rnd=$(grep -o '"type": "round_start", "round": [0-9]*' "$d/events.jsonl" | tail -1 | grep -o '[0-9]*$')
    log "paused $n at round ${rnd:-?} ($(echo $pids))"; note "laptop_c_only: paused $n at round ${rnd:-?} (TERM, no run_end) so C finishes first"
  done
done

echo "===== 3. resume watcher, C only"
old=$(pgrep -f 'runs/resume_watch-c.sh' || true); [ -n "$old" ] && kill $old 2>/dev/null
cp scripts/resume_watch.sh "$R/resume_watch-c.sh"
WAIT=150 MAX=30 PROD="$P" nohup python3 scripts/detach.py /bin/bash "$R/resume_watch-c.sh" \
  Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2 >> "$R/queue.log" 2>&1 < /dev/null &
log "resume watcher restarted for the four laptop C arms"

echo "===== 4. last C arm"
if ls -d "$R"/Cn100-61-sol-s2-2* >/dev/null 2>&1; then log "Cn100-61-sol-s2 already started"
else
  cp scripts/arm_queue.sh "$R/arm_queue-c.sh"
  RESUME=0 SLOTS=$SLOTS SLOT_MATCH="-(luna|sol|terra)" RUN_SLOTS=$SLOTS RETRY_WAIT=60 RETRIES=6 PROD="$P" ARM_GROUPS="Cn100-61-sol-s2" \
    LABEL_ARGS="--judge-model claude/claude-opus-5-5 --judge-effort xhigh --concurrency 8" \
    nohup uv run python scripts/detach.py /bin/bash "$R/arm_queue-c.sh" >> "$R/queue.log" 2>&1 < /dev/null &
  log "C queue started for Cn100-61-sol-s2"; note "laptop_c_only: C queue for Cn100-61-sol-s2 only, SLOTS=$SLOTS"
fi
sleep 75
echo "===== live"; ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE 'runs/[^ ]+' | sort -u
echo "===== done"
