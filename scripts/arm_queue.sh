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
# Usage, from anywhere:  [ARM_GROUPS="armA armB armC;armD"] [PROD=<checkout>] scripts/arm_queue.sh [PID...] >> runs/queue.log 2>&1
# Start it with scripts/detach.py so it survives the agent session that launched it, and run a copy (runs/arm_queue.sh)
# so a later edit or `git pull` never rewrites the file bash is reading. No ARM_GROUPS means no new runs.
# PROD picks the pinned checkout that runs `swarm` (default .prod/), so a second queue can run newer code next to it.
# Pass a running queue's PID to make this one label only after that queue is done, so two queues never label one run.
# AFTER_RUNS="run-a run-b" (names under runs/) holds the groups back until those runs have completed, or until every
# PID given (if any) has exited, so new runs never share the machine with the ones still going. It checks every
# AFTER_POLL seconds.
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

label_run() {
  (cd "$P" && uv run swarm label "$1" > "$1.label.log" 2>&1)
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
  for arm in $group; do run_arm "$arm" & pids+=($!); done
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
  if is_v2 "$d" && has_ended "$d" && [ ! -f "$d/labels.jsonl" ]; then label_run "$d" & pids+=($!); fi
done
log "labeling ${#pids[@]} runs"
for p in ${pids[@]+"${pids[@]}"}; do wait "$p"; done
publish
log "queue done"
