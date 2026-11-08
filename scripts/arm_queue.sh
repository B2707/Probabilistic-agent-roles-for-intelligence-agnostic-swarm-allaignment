#!/bin/bash
# Production queue, detached from any agent session.
#
# 1. Resumes every v2 run under runs/ that hasn't ended and isn't still running, all at once (skipped with RESUME=0).
# 2. Runs the arm groups from the pinned checkout .prod/, one group at a time, every arm in a group at once
#    (each arm uses its config's `concurrency` Codex sessions).
# 3. Waits for the given PIDs (runs started elsewhere), so their labels come out of this queue too.
# 4. Labels every ended v2 run that has no labels yet, LABEL_FIRST first, at most LABEL_JOBS at once (see below).
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
# SLOTS=n starts a group's arms one at a time, in the order given, each once fewer than n runs are live on this
# machine (from any queue), so it never runs more than n at once. A run counts while going or while waiting to resume
# after a usage stop. RUN_SLOTS=m caps runs the same way (kept so older launch lines still work). Without SLOTS a group
# starts all at once. SLOT_MATCH=<regex> makes SLOTS count only runs whose folder names match, while RUN_SLOTS still
# counts every run. Adaption runs use no ChatGPT account (Bader, 8 Nov 04:30: a 3rd slot for the mixed swarms), so luna
# (luna, sol, terra) queues run with SLOTS=2 SLOT_MATCH="-(luna|sol|terra)" RUN_SLOTS=3 and mixed-swarm queues with
# SLOTS=1 SLOT_MATCH=-mix RUN_SLOTS=3.
# Label jobs don't take run slots: Opus labels use no ChatGPT account (Bader, 8 Nov 04:30). The label phase runs at most
# LABEL_JOBS (default 2) label jobs at once on this machine, counting other queues' jobs. LABEL_FIRST="run-a run-b"
# (names under runs/) labels those first, then every other run in name order.
# It checks every SLOT_POLL seconds and waits SLOT_SETTLE seconds after each start so the new task is counted. Queues
# take turns through a lock (runs/.slot-lock) to start a run or a label job, so two never fill the same free slot. A
# queue takes the lock only once a slot is free and checks again under it; it never holds the lock while it waits.
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
# Runs: distinct runs under $R with a live `swarm run` or `swarm resume` process (uv and its python child count once),
# plus runs waiting to resume.
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
# $1 (optional): count only runs whose folder names match this regex.
live_runs() {
  { ps -axo command= | grep -E 'swarm (run|resume) ' | grep -v grep | grep -oE "$R/[^ /]+"; waiting_runs; } |
    sort -u | sed 's#.*/##' | grep -E -- "${1:-.}" | wc -l | tr -d ' '
}
# Live label jobs on this machine, from any queue.
label_jobs() {
  ps -axo command= | grep -E 'swarm label ' | grep -v grep | grep -oE "$R/[^ /]+" | sort -u | wc -l | tr -d ' '
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
# Wait until the check "$@" passes, then take the slot lock and check again; return holding the lock.
take_slot() {
  while :; do
    until "$@"; do sleep "${SLOT_POLL:-60}"; done
    slot_lock
    "$@" && return 0
    slot_unlock
  done
}
run_slot_free() { [ "$(live_runs "${SLOT_MATCH:-}")" -lt "$SLOTS" ] && [ "$(live_runs)" -lt "${RUN_SLOTS:-$SLOTS}" ]; }
label_slot_free() { [ "$(label_jobs)" -lt "${LABEL_JOBS:-2}" ]; }
needs_label() { is_v2 "$1" && has_ended "$1" && [ ! -f "$1/labels.jsonl" ] && ! is_live "swarm label $1"; }

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
      take_slot run_slot_free
      log "slot free ($(live_runs "${SLOT_MATCH:-}") of $SLOTS${SLOT_MATCH:+ $SLOT_MATCH} runs, $(live_runs) of ${RUN_SLOTS:-$SLOTS} in all): starting $arm"
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

todo=()
for n in ${LABEL_FIRST:-}; do todo+=("$R/$n"); done
for d in "$R"/*/; do
  d=${d%/}
  case " ${LABEL_FIRST:-} " in *" $(basename "$d") "*) continue ;; esac
  todo+=("$d")
done
pids=()
for d in ${todo[@]+"${todo[@]}"}; do
  case $(basename "$d") in *-stopped|pilot-*) continue ;; esac
  needs_label "$d" || continue
  take_slot label_slot_free
  if ! needs_label "$d"; then slot_unlock; continue; fi
  log "labeling $(basename "$d") ($(label_jobs) of ${LABEL_JOBS:-2} label jobs live)"
  label_run "$d" & pids+=($!)
  sleep "${SLOT_SETTLE:-60}"; slot_unlock
done
log "labeling ${#pids[@]} runs"
for p in ${pids[@]+"${pids[@]}"}; do wait "$p"; done
publish
log "queue done"
