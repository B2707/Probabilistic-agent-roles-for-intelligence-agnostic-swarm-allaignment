#!/bin/bash
# Keeps resuming runs that their queue gave up on.
#
# arm_queue.sh resumes a run that stops on a usage limit (exit 3) up to RETRIES times, then leaves it. Under heavy
# ChatGPT throttling a run can need more. This watcher takes over: every POLL seconds it looks at each run dir under
# runs/ whose name starts with one of the given prefixes (dirs ending in -stopped are skipped), and resumes a run when
#   - it has not completed,
#   - no process for it is alive (no `swarm run` or `swarm resume`), and
#   - its last event is a usage-limit stop at least WAIT seconds old (default 150: a queue resumes after 60 s, or after
#     about 70 s when fast_resume.sh cuts an older queue's 600 s wait, so a run still in its queue's hands is never
#     touched; run fast_resume.sh next to any queue started before RETRY_WAIT defaulted to 60).
# A resumed run that stops again holds its slot: arm_queue counts a run stopped in the last SLOT_HOLD (1200) seconds
# as waiting, and WAIT is under that, so no queue starts a new run into its slot.
# A run that is not live and did not stop on a usage limit (a crash) is logged once and left alone, and so is a run
# whose resume failed to start (exit other than 0 or 3, such as 127 when `uv` is missing from PATH).
# Each run gets at most MAX (default 30) resumes from this watcher. It never exits on its own; kill its PID.
#
# Usage: PROD=<checkout> nohup python3 scripts/detach.py /bin/bash runs/resume_watch.sh PREFIX... >> runs/queue.log 2>&1 < /dev/null &
# Run a copy under runs/ so a later edit or `git pull` never rewrites the file bash is reading.
set -u
M=$(cd "$(dirname "$0")/.." && pwd)
P=${PROD:-$M/.prod}
R=$M/runs
WAIT=${WAIT:-150}
POLL=${POLL:-60}
MAX=${MAX:-30}
export PYTHONUNBUFFERED=1

log() { echo "$(date '+%F %T') resume_watch $$: $*"; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
is_live() { pgrep -f -- "$1" >/dev/null; }
stopped_on_limit() { tail -1 "$1/events.jsonl" 2>/dev/null | grep -q '"type": "run_end", "round": [0-9]*, "reason": "usage_limit"'; }

noted=" "  # runs already logged as crashed, space-separated
log "start from $P; watching prefixes: $*; WAIT=${WAIT}s MAX=$MAX"
while :; do
  for pre in "$@"; do
    for d in "$R/$pre"-2*/; do
      [ -d "$d" ] || continue
      d=${d%/}; name=$(basename "$d")
      case $name in *-stopped) continue ;; esac
      [ -f "$d/events.jsonl" ] || continue
      [ -f "$d.watch-failed" ] && continue
      has_ended "$d" && continue
      is_live "$d" && continue
      if ! stopped_on_limit "$d"; then
        case $noted in *" $name "*) ;; *) log "$name is not live and did not stop on a usage limit; leaving it"; noted="$noted$name " ;; esac
        continue
      fi
      age=$(( $(date +%s) - $(stat -f %m "$d/events.jsonl") ))
      [ "$age" -ge "$WAIT" ] || continue
      n=$(cat "$d.watch-resumes" 2>/dev/null || echo 0)
      if [ "$n" -ge "$MAX" ]; then
        case $noted in *" $name "*) ;; *) log "$name hit $MAX watcher resumes; leaving it"; noted="$noted$name " ;; esac
        continue
      fi
      n=$((n + 1)); echo "$n" > "$d.watch-resumes"
      log "$name stopped ${age}s ago and no queue resumed it; resume $n of $MAX"
      ( cd "$P" && uv run swarm resume "$d" >> "$d.log" 2>&1; rc=$?; log "resumed $name exit $rc"
        if [ $rc -ne 0 ] && [ $rc -ne 3 ]; then echo $rc > "$d.watch-failed"; log "$name resume failed (exit $rc); leaving it"; fi ) &
    done
  done
  sleep "$POLL"
done
