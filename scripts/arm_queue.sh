#!/bin/bash
# Production queue, detached from any agent session.
#
# 1. Resumes every v2 run under runs/ that hasn't ended and isn't still running.
# 2. Runs the arm groups from the pinned checkout .prod/, one group at a time, every arm in a group at once
#    (each arm uses its config's `concurrency` Codex sessions).
# 3. Waits for the given PIDs (runs started elsewhere), so their labels come out of this queue too.
# 4. Labels every ended v2 run that has no labels yet, all at once.
# 5. Publishes results/ and pushes after every step (scripts/publish_results.py --push).
# Stops if a run doesn't complete (usage limit); continue it with `uv run swarm resume runs/<run>`.
#
# Usage, from anywhere:  [ARM_GROUPS="armA armB armC;armD"] [PROD=<checkout>] scripts/arm_queue.sh [PID...] >> runs/queue.log 2>&1
# PROD picks the pinned checkout that runs `swarm` (default .prod/), so a second queue can run newer code next to it.
# Pass a running queue's PID to make this one label only after that queue is done, so two queues never label one run.
set -u
M=$(cd "$(dirname "$0")/.." && pwd)
P=${PROD:-$M/.prod}
R=$M/runs
IFS=';' read -r -a GROUPS_ <<< "${ARM_GROUPS:-D-planted-6-luna E-audits-only-6-luna;F1-hidden-baseline-6-luna F2-hidden-informed-6-luna}"
export PYTHONUNBUFFERED=1

log() { echo "$(date '+%F %T') $*"; }
publish() { (cd "$M" && uv run python scripts/publish_results.py --push) 2>&1 | sed 's/^/    /'; }
is_v2() { grep -q '"pr_approvals"' "$1/config.json" 2>/dev/null; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
is_live() { pgrep -f -- "$1" >/dev/null; }

run_arm() {
  local ts; ts=$(date +%Y%m%d-%H%M%S)
  (cd "$P" && uv run swarm run --config "$M/configs/$1.toml" --out "$R/$1-$ts" > "$R/$1-$ts.log" 2>&1)
  local rc=$?; log "$1 exit $rc ($1-$ts)"; return $rc
}

resume_run() {
  (cd "$P" && uv run swarm resume "$1" >> "$1.log" 2>&1)
  local rc=$?; log "resumed $(basename "$1") exit $rc"; return $rc
}

label_run() {
  (cd "$P" && uv run swarm label "$1" > "$1.label.log" 2>&1)
  log "labeled $(basename "$1") exit $?"
}

log "queue start from $P; groups: ${GROUPS_[*]:-none}; then waits for PIDs: $*"
for d in "$R"/*/; do
  d=${d%/}
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  if is_v2 "$d" && ! has_ended "$d" && ! is_live "$d"; then
    resume_run "$d" || { publish; log "stopping: $(basename "$d") did not complete"; exit 3; }
  fi
done

for group in "${GROUPS_[@]}"; do
  pids=()
  for arm in $group; do run_arm "$arm" & pids+=($!); done
  rc=0
  for p in "${pids[@]}"; do wait "$p" || rc=1; done
  publish
  if [ $rc -ne 0 ]; then log "stopping: a run did not complete"; exit 3; fi
done

for pid in "$@"; do while kill -0 "$pid" 2>/dev/null; do sleep 15; done; done

pids=()
for d in "$R"/*/; do
  d=${d%/}
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  if is_v2 "$d" && has_ended "$d" && [ ! -f "$d/labels.jsonl" ]; then label_run "$d" & pids+=($!); fi
done
log "labeling ${#pids[@]} runs"
for p in "${pids[@]}"; do wait "$p"; done
publish
log "queue done"
