#!/bin/bash
# Final audit by Opus: after a run ends, claude-opus-5-5 at xhigh audits every agent in it, with
# the run's own frozen auditor prompt, into RUN/reaudit-opus.jsonl. Metrics use it as the final audit once it covers
# every agent (swarm.metrics.opus_final_audit). It replaces terra's end-of-run pass, which never affects a run.
#
# Every POLL seconds it looks for completed v3 runs under runs/ (names A100- to F100- and the Cn100-, Dn100-, En100- reruns, not -stopped, not -mix) whose
# reaudit-opus.jsonl doesn't cover every agent in world.json yet, and starts `swarm reaudit` on them, at most JOBS at
# once on this machine, each with CONC audits at once. A rerun audits only the missing agents. A run whose audit
# failed MAX_FAILS times (default 3) is logged and left alone. After each job it publishes results/ and pushes.
# It never exits on its own; kill its PID.
#
# Usage: LABEL_PROD=<checkout> [JOBS=2] [CONC=8] nohup python3 scripts/detach.py /bin/bash runs/opus_audit_watch.sh \
#   >> runs/queue.log 2>&1 < /dev/null &
# Run a copy under runs/ so a later edit or `git pull` never rewrites the file bash is reading.
set -u
M=$(cd "$(dirname "$0")/.." && pwd)
R=$M/runs
LP=${LABEL_PROD:-$M/.prod-label}
POLL=${POLL:-60}
JOBS=${JOBS:-2}
CONC=${CONC:-8}
export PYTHONUNBUFFERED=1

log() { echo "$(date '+%F %T') opus_audit_watch $$: $*"; }
publish() { (cd "$M" && uv run python scripts/publish_results.py --push) 2>&1 | sed 's/^/    /'; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
agents() { python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1] + "/world.json"))["agents"]))' "$1"; }
audited() {
  [ -f "$1/reaudit-opus.jsonl" ] || { echo 0; return; }
  python3 -c 'import json,sys; print(len({json.loads(l)["agent"] for l in open(sys.argv[1]) if l.strip()}))' \
    "$1/reaudit-opus.jsonl"
}
# Runs with a live `swarm reaudit` (uv and its python child count once), however the path was written.
live_runs() { ps -axo command= | grep -E 'swarm reaudit ' | grep -v grep | grep -oE 'reaudit [^ ]+' | sed 's#.*/##' | sort -u; }
is_live() { live_runs | grep -qx -- "$(basename "$1")"; }
fails() { cat "$1.opus-fails" 2>/dev/null || echo 0; }
needs_audit() {
  has_ended "$1" && ! is_live "$1" && [ "$(fails "$1")" -lt "${MAX_FAILS:-3}" ] && [ "$(audited "$1")" -lt "$(agents "$1")" ]
}

audit_run() {
  (cd "$LP" && uv run swarm reaudit "$1" --name opus --model claude/claude-opus-5-5 --effort xhigh \
    --concurrency "$CONC" >> "$1.reaudit-opus.log" 2>&1)
  local rc=$?
  log "opus audit $(basename "$1") exit $rc ($(audited "$1") of $(agents "$1") agents)"
  if [ $rc -ne 0 ]; then
    echo $(( $(fails "$1") + 1 )) > "$1.opus-fails"
    [ "$(fails "$1")" -ge "${MAX_FAILS:-3}" ] && log "$(basename "$1") failed its Opus audit ${MAX_FAILS:-3} times; leaving it (see $1.reaudit-opus.log)"
  fi
  publish
}

log "start from $LP; JOBS=$JOBS CONC=$CONC"
while :; do
  for d in "$R"/*/; do
    d=${d%/}
    case $(basename "$d") in [A-F]100-*|[C-E]n100-*) ;; *) continue ;; esac
    case $(basename "$d") in *-stopped|*-mix*) continue ;; esac
    needs_audit "$d" || continue
    [ "$(live_runs | wc -l | tr -d ' ')" -lt "$JOBS" ] || break
    log "opus audit $(basename "$d") ($(audited "$d") of $(agents "$d") agents done)"
    audit_run "$d" &
    sleep 20
  done
  sleep "$POLL"
done
