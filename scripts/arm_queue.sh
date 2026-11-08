#!/bin/bash
# Production queue for issue #2, detached from any agent session.
#
# 1. Waits for the given PIDs (runs already going). Any run under runs/ that hasn't ended is resumed.
# 2. Runs the remaining arms two at a time (10 Codex sessions each) from the pinned checkout .prod/.
# 3. Labels every ended v2 run that has no labels yet, two at a time.
# 4. Publishes results/ and pushes after every step (scripts/publish_results.py --push).
# Stops if a run doesn't complete (usage limit); continue it with `uv run swarm resume runs/<run>`.
#
# Usage, from anywhere:  [ARM_PAIRS=...] scripts/arm_queue.sh [PID...] >> runs/queue.log 2>&1
set -u
M=$(cd "$(dirname "$0")/.." && pwd)
P=$M/.prod
R=$M/runs
# Arm pairs, run one pair at a time: ARM_PAIRS="armA armB;armC armD" (default: the issue #2 arms D to F2).
IFS=';' read -r -a ARMS <<< "${ARM_PAIRS:-D-planted-6-luna E-audits-only-6-luna;F1-hidden-baseline-6-luna F2-hidden-informed-6-luna}"
export PYTHONUNBUFFERED=1

log() { echo "$(date '+%F %T') $*"; }
publish() { (cd "$M" && uv run python scripts/publish_results.py --push) 2>&1 | sed 's/^/    /'; }
is_v2() { grep -q '"pr_approvals"' "$1/config.json" 2>/dev/null; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }

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

log "queue start; waiting for PIDs: $*"
for pid in "$@"; do while kill -0 "$pid" 2>/dev/null; do sleep 15; done; done

for d in "$R"/*/; do
  d=${d%/}
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  if is_v2 "$d" && ! has_ended "$d"; then
    resume_run "$d" || { publish; log "stopping: $(basename "$d") did not complete"; exit 3; }
  fi
done
publish

for pair in "${ARMS[@]}"; do
  set -- $pair
  run_arm "$1" & a=$!
  run_arm "$2" & b=$!
  wait $a; ra=$?
  wait $b; rb=$?
  publish
  if [ $ra -ne 0 ] || [ $rb -ne 0 ]; then log "stopping: a run did not complete"; exit 3; fi
done

todo=()
for d in "$R"/*/; do
  d=${d%/}
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  if is_v2 "$d" && has_ended "$d" && [ ! -f "$d/labels.jsonl" ]; then todo+=("$d"); fi
done
log "labeling ${#todo[@]} runs"
i=0
while [ $i -lt ${#todo[@]} ]; do
  label_run "${todo[$i]}" & a=$!
  if [ $((i + 1)) -lt ${#todo[@]} ]; then label_run "${todo[$((i + 1))]}"; fi
  wait $a
  i=$((i + 2))
done
publish
log "queue done"
