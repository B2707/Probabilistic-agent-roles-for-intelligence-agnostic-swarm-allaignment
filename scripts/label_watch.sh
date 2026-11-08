#!/bin/bash
# Labels every run on this machine as soon as it completes.
#
# Every POLL seconds it looks for v2 runs under runs/ that completed and have no labels.jsonl and no live label job
# (dirs ending in -stopped and pilot-* are skipped), LABEL_FIRST (names under runs/) first, then the rest in name order.
# It starts one label job per free label slot: at most LABEL_JOBS (default 2) `swarm label` jobs at once on this
# machine, counting jobs from any queue. Label jobs don't take run slots (Opus labels use no ChatGPT account, Bader,
# 8 Nov 04:30). Starts go through the slot lock (runs/.slot-lock), like scripts/arm_queue.sh, so the two never start
# into the same free slot. After each job it publishes results/ and pushes. A run whose labeling failed MAX_FAILS
# times (default 2) is logged and left alone; labels.partial.jsonl keeps finished batches, so a retry costs little.
# It never exits on its own; kill its PID.
#
# Usage: LABEL_PROD=<checkout> LABEL_ARGS="--judge-model claude/claude-opus-5-5 --judge-effort xhigh --concurrency 8" \
#   [LABEL_FIRST="run-a run-b"] nohup python3 scripts/detach.py /bin/bash runs/label_watch.sh >> runs/queue.log 2>&1 < /dev/null &
# Run a copy under runs/ so a later edit or `git pull` never rewrites the file bash is reading.
set -u
M=$(cd "$(dirname "$0")/.." && pwd)
R=$M/runs
LP=${LABEL_PROD:-$M/.prod}
POLL=${POLL:-60}
export PYTHONUNBUFFERED=1

log() { echo "$(date '+%F %T') label_watch $$: $*"; }
publish() { (cd "$M" && uv run python scripts/publish_results.py --push) 2>&1 | sed 's/^/    /'; }
is_v2() { grep -q '"pr_approvals"' "$1/config.json" 2>/dev/null; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
is_live() { pgrep -f -- "$1" >/dev/null; }
label_jobs() {
  ps -axo command= | grep -E 'swarm label ' | grep -v grep | grep -oE "$R/[^ /]+" | sort -u | wc -l | tr -d ' '
}
label_slot_free() { [ "$(label_jobs)" -lt "${LABEL_JOBS:-2}" ]; }
fails() { cat "$1.label-fails" 2>/dev/null || echo 0; }
needs_label() {
  is_v2 "$1" && has_ended "$1" && [ ! -f "$1/labels.jsonl" ] && ! is_live "swarm label $1" &&
    [ "$(fails "$1")" -lt "${MAX_FAILS:-2}" ]
}
slot_lock() {
  until mkdir "$R/.slot-lock" 2>/dev/null; do
    local holder; holder=$(cat "$R/.slot-lock/pid" 2>/dev/null)
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then rm -rf "$R/.slot-lock"; continue; fi
    sleep 5
  done
  echo $$ > "$R/.slot-lock/pid"
}
slot_unlock() { rm -rf "$R/.slot-lock"; }

label_run() {
  (cd "$LP" && uv run swarm label "$1" ${LABEL_ARGS:-} > "$1.label.log" 2>&1)
  local rc=$?
  log "labeled $(basename "$1") exit $rc"
  if [ $rc -ne 0 ]; then
    echo $(( $(fails "$1") + 1 )) > "$1.label-fails"
    [ "$(fails "$1")" -ge "${MAX_FAILS:-2}" ] && log "$(basename "$1") failed labeling ${MAX_FAILS:-2} times; leaving it (see $1.label.log)"
  fi
  publish
}

log "start from $LP; LABEL_JOBS=${LABEL_JOBS:-2}; first: ${LABEL_FIRST:-none}; args: ${LABEL_ARGS:-none}"
while :; do
  todo=()
  for n in ${LABEL_FIRST:-}; do todo+=("$R/$n"); done
  for d in "$R"/*/; do
    d=${d%/}
    case " ${LABEL_FIRST:-} " in *" $(basename "$d") "*) continue ;; esac
    todo+=("$d")
  done
  for d in ${todo[@]+"${todo[@]}"}; do
    case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
    needs_label "$d" || continue
    label_slot_free || break
    slot_lock
    if label_slot_free && needs_label "$d"; then
      log "labeling $(basename "$d") ($(label_jobs) of ${LABEL_JOBS:-2} label jobs live)"
      label_run "$d" &
      sleep "${SLOT_SETTLE:-30}"
    fi
    slot_unlock
  done
  sleep "$POLL"
done
