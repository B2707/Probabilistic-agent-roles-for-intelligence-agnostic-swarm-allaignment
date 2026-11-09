#!/bin/bash
# One-shot recovery after the laptop dropped off the network (9 Nov 01:00 to 01:30). Safe to run more than once.
#   1. Reports sleep/wake, live runs, and each Cn100 run's round and last-event age.
#   2. Rewrites runs/after_c.sh so that after the C queue exits it only RESUMES the two paused D/E luna seed-1 runs
#      and starts no new arms (the six remaining D/E arms run on Bader's Mac as -b2 configs). Relaunches it.
#   3. Starts caffeinate so the laptop stays awake.
#   4. If the C queue (runs/arm_queue-c.sh) is dead: resumes every unended Cn100 run that has no live process, and
#      relaunches the C queue for the C arms that have no run folder yet. Never touches Dn/En runs.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git merge -q --ff-only origin/main && bash scripts/laptop_recover.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs; P=$M/.prod
log() { echo "$(date '+%F %T') recover: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
is_live() { pgrep -f -- "$1" >/dev/null; }
cd "$M" || exit 1

echo "===== 1. state"; uptime
pmset -g log 2>/dev/null | grep -iE '(Sleep|Wake|DarkWake).*(due to|Entering)' | tail -5
echo "--- live swarm processes"; ps -axo pid,command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE '^ *[0-9]+|runs/[^ ]+' | paste - - || echo "(none)"
for d in "$R"/Cn100-*-2*/ "$R"/Dn100-*-2*/ "$R"/En100-*-2*/; do
  [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
  rnd=$(grep -o '"type": "round_start", "round": [0-9]*' "$d/events.jsonl" | tail -1 | grep -o '[0-9]*$')
  age=$(( $(date +%s) - $(stat -f %m "$d/events.jsonl") ))
  st=running; is_live "$d" || st=NOT-RUNNING; has_ended "$d" && st=completed
  last=$(tail -1 "$d/events.jsonl" | grep -o '"reason": "[a-z_]*"' || true)
  echo "  $n  round=${rnd:-?}  last_event=${age}s ago  $st ${last}"
done
echo "--- helpers"; pgrep -fl 'arm_queue-c|resume_watch-c|after_c|label_watch|opus_audit_watch|dashboard|caffeinate' | cut -c1-120 || echo "(none)"

echo "===== 2. after_c.sh: resume only"
if [ -f "$R/after_c.sh" ]; then
  if grep -q 'ARM_GROUPS=""' "$R/after_c.sh"; then log "after_c.sh already has an empty arm list"
  else
    cp "$R/after_c.sh" "$R/after_c.sh.bak-$(date +%H%M%S)"
    sed -i '' -E 's/ARM_GROUPS="[^"]*"/ARM_GROUPS=""/' "$R/after_c.sh"
    bash -n "$R/after_c.sh" || { log "after_c.sh failed bash -n; restored"; cp "$R"/after_c.sh.bak-* "$R/after_c.sh"; exit 1; }
    log "after_c.sh arm list emptied"
  fi
  grep -n 'ARM_GROUPS=' "$R/after_c.sh" | head -3
  old=$(pgrep -f 'runs/after_c.sh' || true)
  [ -n "$old" ] && { kill $old 2>/dev/null; sleep 1; log "stopped old after_c ($old)"; }
  nohup python3 scripts/detach.py /bin/bash "$R/after_c.sh" >> "$R/queue.log" 2>&1 < /dev/null &
  sleep 1; log "after_c relaunched, pid $(pgrep -f 'runs/after_c.sh' | head -1)"
  note "after_c.sh now only resumes the two paused D/E luna seed-1 runs; the six remaining D/E arms run on Bader's Mac (-b2) (laptop_recover.sh)"
else log "no runs/after_c.sh found"; fi

echo "===== 3. caffeinate"
pgrep -x caffeinate >/dev/null && log "caffeinate already running" || { nohup python3 scripts/detach.py caffeinate -dimsu >/dev/null 2>&1 < /dev/null & sleep 1; log "caffeinate started, pid $(pgrep -x caffeinate | head -1)"; }

echo "===== 4. C queue and C runs"
if pgrep -f 'runs/arm_queue-c.sh' >/dev/null; then log "C queue alive; it manages the C runs. Nothing to resume here."
else
  log "C queue is DEAD. Resuming unended Cn100 runs with no live process."
  for d in "$R"/Cn100-*-2*/; do
    [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
    case $n in *-stopped) continue ;; esac
    has_ended "$d" && continue; is_live "$d" && continue
    ( cd "$P" && nohup python3 "$M/scripts/detach.py" uv run swarm resume "$d" >> "$d.log" 2>&1 < /dev/null & )
    log "resumed $n"; note "laptop_recover: resumed $n after the outage"
    sleep 20
  done
  todo=""
  for a in Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2 Cn100-6-luna-s3 Cn100-61-sol-s3; do
    ls -d "$R/$a"-2* >/dev/null 2>&1 || todo="$todo $a"
  done
  if [ -n "$todo" ]; then
    cp scripts/arm_queue.sh "$R/arm_queue-c.sh"
    RESUME=0 SLOTS=3 SLOT_MATCH="-(luna|sol|terra)" RUN_SLOTS=3 RETRY_WAIT=60 RETRIES=6 PROD="$P" ARM_GROUPS="${todo# }" \
      LABEL_ARGS="--judge-model claude/claude-opus-5-5 --judge-effort xhigh --concurrency 8" \
      nohup uv run python scripts/detach.py /bin/bash "$R/arm_queue-c.sh" >> "$R/queue.log" 2>&1 < /dev/null &
    sleep 2; log "C queue relaunched for:${todo} (pid $(pgrep -f 'runs/arm_queue-c.sh' | head -1))"
    note "laptop_recover: C queue relaunched for${todo}"
  fi
  pgrep -f 'runs/resume_watch-c.sh' >/dev/null || {
    cp scripts/resume_watch.sh "$R/resume_watch-c.sh"
    WAIT=150 MAX=30 PROD="$P" nohup python3 scripts/detach.py /bin/bash "$R/resume_watch-c.sh" Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2 Cn100-6-luna-s3 Cn100-61-sol-s3 >> "$R/queue.log" 2>&1 < /dev/null &
    log "C resume watcher relaunched"; }
fi
echo "===== done. Paste this whole output back to Claude."
