#!/bin/bash
# Moves the laptop's swarm Codex home (.prod/.swarm-home-mohammad) onto Bader's second ChatGPT account (the one the
# Mac's -b2 runs use) and resumes the five runs the locked account stranded (9 Nov 01:0x, locked until 15 Nov).
# The runs resume in place: same run folders, same Codex home path, same rollouts. Only auth.json changes.
#   1. Stops the queues and watchers that were retry-looping on the locked account.
#   2. Moves the locked account's auth.json aside and runs a device login in the foreground: enter the code shown in a
#      browser signed into the NEW account.
#   3. `swarm check` on the new login; stops here if it fails.
#   4. Resumes the five interrupted runs (C first) and starts a C queue for the C arms with no run folder yet, which
#      starts each one once fewer than SLOTS runs are live. Starts a resume watcher for all of them.
# Usage, on the laptop:  cd ~/.t3/projects/agent-swarm-hackathon && git fetch -q origin && git merge -q --ff-only origin/main && bash scripts/laptop_switch_b2.sh
set -u
M=$(cd "$(dirname "$0")/.." && pwd); R=$M/runs; P=$M/.prod
SLOTS=${SLOTS:-5}
CFG=configs/Cn100-6-luna-s1.toml
log() { echo "$(date '+%F %T') switch_b2: $*"; }
note() { echo "---- $(date '+%F %T') $*" >> "$R/queue.log"; }
has_ended() { grep -q '"type": "run_end", "round": [0-9]*, "reason": "completed"' "$1/events.jsonl" 2>/dev/null; }
is_live() { pgrep -f -- "$1" >/dev/null; }
cd "$M" || exit 1

echo "===== 1. stop the retry loops"
for s in arm_queue-de.sh arm_queue-c.sh resume_watch-de.sh resume_watch-c.sh after_c.sh; do
  pids=$(pgrep -f "runs/$s" || true)
  [ -n "$pids" ] && { kill $pids 2>/dev/null; log "stopped $s ($(echo $pids))"; }
done
for i in $(seq 1 12); do
  ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep >/dev/null || break
  sleep 5
done
if ps -axo command= | grep -E 'swarm (run|resume)' | grep -v grep; then log "a swarm process is still alive (above); stopping here"; exit 1; fi
log "no swarm process alive"
note "laptop_switch_b2: stopped the queues and watchers retry-looping on the locked account"

echo "===== 2. device login to the new account"
H=$(cd "$P/.swarm-home-mohammad/.codex" && pwd -P) || { log "no Codex home at $P/.swarm-home-mohammad/.codex"; exit 1; }
if [ -f "$H/auth.json" ]; then
  mv "$H/auth.json" "$H/auth.json.locked-account-bak-$(date +%Y%m%d-%H%M%S)"
  log "locked account's auth.json moved aside in $H"
fi
echo ">>> Open the URL below in a browser signed into the NEW account and enter the code. <<<"
( cd "$P" && uv run swarm login --config "$CFG" --device ) || { log "login failed"; exit 1; }
[ -f "$H/auth.json" ] || { log "login finished but $H/auth.json is missing"; exit 1; }
note "laptop_switch_b2: .swarm-home-mohammad now logged into Bader's second ChatGPT account (same as the Mac -b2 runs)"

echo "===== 3. check"
( cd "$P" && uv run swarm check --config "$CFG" ) || { log "swarm check failed; nothing resumed"; exit 1; }

echo "===== 4. resume the five runs, queue the rest of C"
for a in Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Dn100-6-luna-s1 En100-6-luna-s1; do
  for d in "$R/$a"-2*/; do
    [ -d "$d" ] || continue; d=${d%/}; n=$(basename "$d")
    case $n in *-stopped) continue ;; esac
    has_ended "$d" && continue; is_live "$d" && continue
    ( cd "$P" && nohup python3 "$M/scripts/detach.py" uv run swarm resume "$d" >> "$d.log" 2>&1 < /dev/null & )
    log "resumed $n"; note "laptop_switch_b2: resumed $n on the new account"
    sleep 20
  done
done
todo=""
for a in Cn100-61-sol-s2 Cn100-6-luna-s3 Cn100-61-sol-s3; do
  ls -d "$R/$a"-2* >/dev/null 2>&1 || todo="$todo $a"
done
if [ -n "$todo" ]; then
  cp scripts/arm_queue.sh "$R/arm_queue-c.sh"
  RESUME=0 SLOTS=$SLOTS SLOT_MATCH="-(luna|sol|terra)" RUN_SLOTS=$SLOTS RETRY_WAIT=60 RETRIES=6 PROD="$P" ARM_GROUPS="${todo# }" \
    LABEL_ARGS="--judge-model claude/claude-opus-5-5 --judge-effort xhigh --concurrency 8" \
    nohup uv run python scripts/detach.py /bin/bash "$R/arm_queue-c.sh" >> "$R/queue.log" 2>&1 < /dev/null &
  sleep 2; log "C queue started for:${todo}, $SLOTS slots (pid $(pgrep -f 'runs/arm_queue-c.sh' | head -1))"
  note "laptop_switch_b2: C queue for${todo}, SLOTS=$SLOTS"
fi
cp scripts/resume_watch.sh "$R/resume_watch-c.sh"
WAIT=150 MAX=30 PROD="$P" nohup python3 scripts/detach.py /bin/bash "$R/resume_watch-c.sh" \
  Cn100-6-luna-s1 Cn100-61-sol-s1 Cn100-6-luna-s2 Cn100-61-sol-s2 Cn100-6-luna-s3 Cn100-61-sol-s3 Dn100-6-luna-s1 En100-6-luna-s1 \
  >> "$R/queue.log" 2>&1 < /dev/null &
log "resume watcher started"
pgrep -x caffeinate >/dev/null || { nohup python3 scripts/detach.py caffeinate -dimsu >/dev/null 2>&1 < /dev/null & log "caffeinate started"; }

sleep 30
echo "===== live"; ps -axo pid,command= | grep -E 'swarm (run|resume)' | grep -v grep | grep -oE 'runs/[^ ]+' | sort -u
echo "===== done. Paste this output back to Claude."
