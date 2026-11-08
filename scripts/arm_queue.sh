#!/bin/bash
# Production queue, detached from any agent session.
#
# 1. Resumes every v2 run under runs/ that hasn't ended and isn't still running, all at once (skipped with RESUME=0).
# 2. Runs the arm groups from the pinned checkout .prod/, one group at a time, every arm in a group at once
#    (each arm uses its config's `concurrency` Codex sessions).
# 3. Waits for the given PIDs (runs started elsewhere), so their labels come out of this queue too.
# 4. Labels every ended v2 run that has no labels yet, all at once.
# 5. Publishes results/ and pushes after every step (scripts/publish_results.py --push).
# A run that stops on a usage limit (exit 3) is resumed after RETRY_WAIT seconds, up to RETRIES times. A run that still
# doesn't complete is logged and left for `uv run swarm resume runs/<run>`; the queue goes on and labels what ended.
#
# Usage, from anywhere:  [ARM_GROUPS="armA armB armC;armD"] [PROD=<checkout>] [SLOTS=n] scripts/arm_queue.sh [PID...] >> runs/queue.log 2>&1
# Start it with scripts/detach.py so it survives the agent session that launched it, and run a copy (runs/arm_queue.sh)
# so a later edit or `git pull` never rewrites the file bash is reading. No ARM_GROUPS means no new runs.
# PROD picks the pinned checkout that runs `swarm` (default .prod/), so a second queue can run newer code next to it.
# Pass a running queue's PID to make this one label only after that queue is done, so two queues never label one run.
# AFTER_RUNS="run-a run-b" (names under runs/) holds the groups back until those runs have completed, or until every
# PID given (if any) has exited, so new runs never share the machine with the ones still going. It checks every
# AFTER_POLL seconds.
# SLOTS=n starts a group's arms one at a time, in the order given, each once fewer than n tasks are live on this
# machine (from any queue), so it never runs more than n at once. A task is a run (going, or waiting to resume after
# a usage stop) or a label job; label jobs also start one at a time, each in a free slot. It checks every SLOT_POLL seconds and
# waits SLOT_SETTLE seconds after each start so the new run is counted. Queues using SLOTS take turns through a lock
# (runs/.slot-lock), so two of them never fill the same free slot. Without SLOTS a group starts all at once.
set -u
M=$(cd "$(dirname "$0")/.." && pwd)
P=${PROD:-$M/.prod}
R=$M/runs
GROUPS_=(); [ -n "${ARM_GROUPS:-}" ] && IFS=';' read -r -a GROUPS_ <<< "$ARM_GROUPS"
export PYTHONUNBUFFERED=1

log() { echo "$(date '+%F %T') $*"; }
publish() { (cd "$M" && uv run python scripts/publish_results.py --push) 2>&1 | sed 's/^/    /'; }
is_v2() { grep -q '"pr_approvals"' "$1/config.json" 2>/dev/null; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
is_live() { pgrep -f -- "$1" >/dev/null; }
# Tasks: distinct runs under $R with a live `swarm run`, `swarm resume` or `swarm label` process (uv and its python
# child count once), plus runs waiting to resume.
# A run that stopped on a usage limit within the last SLOT_HOLD seconds (default 20 min) is waiting for its queue to
# resume it (after RETRY_WAIT), so it still holds its slot.
waiting_runs() {
  local d f now; now=$(date +%s)
  for d in "$R"/*/; do
    d=${d%/}; f=$d/events.jsonl
    case $d in *-stopped) continue ;; esac
    [ -f "$f" ] && [ $((now - $(stat -f %m "$f"))) -lt "${SLOT_HOLD:-1200}" ] || continue
    tail -1 "$f" | grep -q '"type": "run_end", "round": [0-9]*, "reason": "usage_limit"' && echo "$d"
  done
}
live_runs() {
  { ps -axo command= | grep -E 'swarm (run|resume|label) ' | grep -v grep | grep -oE "$R/[^ /]+"; waiting_runs; } |
    sort -u | wc -l | tr -d ' '
}
# The slot lock (a directory under runs/) makes two SLOTS queues take turns, so they never start into the same free
# slot. A lock whose queue has died is broken.
slot_lock() {
  until mkdir "$R/.slot-lock" 2>/dev/null; do
    local holder; holder=$(cat "$R/.slot-lock/pid" 2>/dev/null)
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then rm -rf "$R/.slot-lock"; continue; fi
    sleep "${SLOT_POLL:-60}"
  done
  echo $$ > "$R/.slot-lock/pid"
}
slot_unlock() { rm -rf "$R/.slot-lock"; }

resume_run() {
  (cd "$P" && uv run swarm resume "$1" >> "$1.log" 2>&1)
  local rc=$?; log "resumed $(basename "$1") exit $rc"; return $rc
}

# $1 run dir, $2 exit code of its last attempt. Exit 3 means it stopped and can resume.
retry_run() {
  local rc=$2 n=0
  while [ "$rc" -eq 3 ] && [ "$n" -lt "${RETRIES:-4}" ]; do
    n=$((n + 1)); log "$(basename "$1") stopped; resume $n of ${RETRIES:-4} in ${RETRY_WAIT:-600}s"
    sleep "${RETRY_WAIT:-600}"
    resume_run "$1"; rc=$?
  done
  return $rc
}

run_arm() {
  local ts; ts=$(date +%Y%m%d-%H%M%S)
  (cd "$P" && uv run swarm run --config "$M/configs/$1.toml" --out "$R/$1-$ts" > "$R/$1-$ts.log" 2>&1)
  local rc=$?; log "$1 exit $rc ($1-$ts)"
  retry_run "$R/$1-$ts" $rc
}

# LABEL_ARGS (e.g. "--judge-model claude/claude-opus-5-5 --judge-effort xhigh --concurrency 8") go to `swarm label`;
# LABEL_PROD picks the checkout that labels (default PROD), so labeling can use newer code than the runs.
label_run() {
  (cd "${LABEL_PROD:-$P}" && uv run swarm label "$1" ${LABEL_ARGS:-} > "$1.label.log" 2>&1)
  log "labeled $(basename "$1") exit $?"
}

log "queue start from $P; groups: ${GROUPS_[*]:-none}; then waits for PIDs: $*"
pids=()
for d in "$R"/*/; do
  d=${d%/}
  [ "${RESUME:-1}" = 1 ] || break
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  if is_v2 "$d" && ! has_ended "$d" && ! is_live "$d"; then
    ( resume_run "$d"; retry_run "$d" $? || log "$(basename "$d") did not complete; going on" ) & pids+=($!)
  fi
done
for p in ${pids[@]+"${pids[@]}"}; do wait "$p"; done

if [ -n "${AFTER_RUNS:-}" ]; then
  log "groups wait for runs to complete: $AFTER_RUNS (or for PIDs to exit: $*)"
  while :; do
    left=0; for r in $AFTER_RUNS; do has_ended "$R/$r" || left=1; done
    alive=1; [ $# -gt 0 ] && { alive=0; for pid in "$@"; do kill -0 "$pid" 2>/dev/null && alive=1; done; }
    [ $left -eq 0 ] || [ $alive -eq 0 ] && break
    sleep "${AFTER_POLL:-60}"
  done
  log "groups start"
fi

for group in ${GROUPS_[@]+"${GROUPS_[@]}"}; do
  pids=()
  for arm in $group; do
    if [ -n "${SLOTS:-}" ]; then
      slot_lock
      until [ "$(live_runs)" -lt "$SLOTS" ]; do sleep "${SLOT_POLL:-60}"; done
      log "slot free ($(live_runs) of $SLOTS runs live): starting $arm"
    fi
    run_arm "$arm" & pids+=($!)
    if [ -n "${SLOTS:-}" ]; then sleep "${SLOT_SETTLE:-60}"; slot_unlock; fi
  done
  rc=0
  for p in ${pids[@]+"${pids[@]}"}; do wait "$p" || rc=1; done
  publish
  if [ $rc -ne 0 ]; then log "a run in this group did not complete; going on"; fi
done

for pid in "$@"; do while kill -0 "$pid" 2>/dev/null; do sleep 15; done; done

pids=()
for d in "$R"/*/; do
  d=${d%/}
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  if is_v2 "$d" && has_ended "$d" && [ ! -f "$d/labels.jsonl" ] && ! is_live "swarm label $d"; then
    if [ -n "${SLOTS:-}" ]; then
      slot_lock
      until [ "$(live_runs)" -lt "$SLOTS" ]; do sleep "${SLOT_POLL:-60}"; done
      if [ -f "$d/labels.jsonl" ] || is_live "swarm label $d"; then slot_unlock; continue; fi
      log "slot free ($(live_runs) of $SLOTS tasks live): labeling $(basename "$d")"
    fi
    label_run "$d" & pids+=($!)
    if [ -n "${SLOTS:-}" ]; then sleep "${SLOT_SETTLE:-60}"; slot_unlock; fi
  fi
done
log "labeling ${#pids[@]} runs"
for p in ${pids[@]+"${pids[@]}"}; do wait "$p"; done
publish
log "queue done"
