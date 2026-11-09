#!/bin/bash
# Bader, 9 Nov 02:19: C seeds 1 and 2 run, C seed 3 waits (paused on his Mac). Resumes every unended laptop C seed-1/2
# run that has no live process, from its last saved turn, and restarts the C resume watcher for those four arms only.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git show origin/main:scripts/laptop_resume_c_s1_s2.sh > scripts/laptop_resume_c_s1_s2.sh && bash scripts/laptop_resume_c_s1_s2.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs; P=$M/.prod
log() { echo "$(date '+%F %T') resume_c_s1_s2: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
cd "$M" || exit 1

for a in Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2; do
  for d in "$R/$a"-2*/; do
    [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
    case $n in *-stopped) continue ;; esac
    has_ended "$d" && { log "$n already completed"; continue; }
    pgrep -f -- "swarm (run|resume).*$d" >/dev/null && { log "$n already running"; continue; }
    ( cd "$P" && nohup python3 "$M/scripts/detach.py" uv run swarm resume "$d" >> "$d.log" 2>&1 < /dev/null & )
    log "resumed $n"; note "laptop_resume_c_s1_s2: resumed $n (C seeds 1-2 run, seed 3 waits on the Mac)"
    sleep 15
  done
done
old=$(pgrep -f 'runs/resume_watch-c.sh' || true); [ -n "$old" ] && kill $old 2>/dev/null
cp scripts/resume_watch.sh "$R/resume_watch-c.sh"
WAIT=150 MAX=30 PROD="$P" nohup python3 scripts/detach.py /bin/bash "$R/resume_watch-c.sh" \
  Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2 >> "$R/queue.log" 2>&1 < /dev/null &
log "resume watcher restarted for the four C seed-1/2 arms"
sleep 20
echo "===== live"; ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE 'runs/[^ ]+' | sort -u
echo "===== done"
