#!/bin/bash
# Bader's Mac now runs Cn100-6-luna-s3 and Cn100-61-sol-s3 (as -b2 configs, 9 Nov 02:0x), so the laptop's C queue must
# not start them too. Stops the queue's starter shell (never a shell that is minding a live run) and, if
# Cn100-61-sol-s2 has not started yet, relaunches the queue for that one arm only. Safe to run more than once.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git show origin/main:scripts/laptop_c_queue_trim.sh > scripts/laptop_c_queue_trim.sh && bash scripts/laptop_c_queue_trim.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs; P=$M/.prod
SLOTS=${SLOTS:-5}
log() { echo "$(date '+%F %T') c_queue_trim: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
cd "$M" || exit 1

for a in Cn100-6-luna-s3 Cn100-61-sol-s3; do
  ls -d "$R/$a"-2* >/dev/null 2>&1 && log "WARNING: $a already has a run folder here: $(ls -d "$R/$a"-2*). Tell Claude before doing anything else."
done
for p in $(pgrep -f 'runs/arm_queue-c.sh'); do
  if pgrep -P "$p" -f 'swarm (run|resume)' >/dev/null; then log "kept $p (it is minding a live run)"
  else kill "$p" 2>/dev/null && log "stopped $p"; fi
done
sleep 2
if ls -d "$R"/Cn100-61-sol-s2-2* >/dev/null 2>&1; then log "Cn100-61-sol-s2 already started; no queue needed"
else
  cp scripts/arm_queue.sh "$R/arm_queue-c.sh"
  RESUME=0 SLOTS=$SLOTS SLOT_MATCH="-(luna|sol|terra)" RUN_SLOTS=$SLOTS RETRY_WAIT=60 RETRIES=6 PROD="$P" ARM_GROUPS="Cn100-61-sol-s2" \
    LABEL_ARGS="--judge-model claude/claude-opus-5-5 --judge-effort xhigh --concurrency 8" \
    nohup uv run python scripts/detach.py /bin/bash "$R/arm_queue-c.sh" >> "$R/queue.log" 2>&1 < /dev/null &
  sleep 2; log "C queue relaunched for Cn100-61-sol-s2 only, $SLOTS slots (pid $(pgrep -f 'runs/arm_queue-c.sh' | head -1))"
fi
note "laptop_c_queue_trim: laptop C queue now starts only Cn100-61-sol-s2; Cn100-6-luna-s3 and Cn100-61-sol-s3 run on Bader's Mac (-b2)"
echo "===== live"; ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE 'runs/[^ ]+' | sort -u
echo "===== done"
