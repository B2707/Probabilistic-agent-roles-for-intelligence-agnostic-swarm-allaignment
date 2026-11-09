#!/bin/bash
# Cuts the usage-stop retry wait of queues that are already running from 600 s to FAST_WAIT seconds (default 60), so a
# stopped run doesn't sit stale for 10 minutes. Every FAST_POLL seconds (default 10) it finds
# `sleep 600` processes whose parent is an arm_queue*.sh bash (the wait in retry_run) and kills each one once it has
# slept FAST_WAIT seconds. The queue then resumes the run itself, so a run is never resumed twice. It kills only those
# sleeps, never a queue, a run or another sleep.
#
# Start one per machine, detached:
#   cp scripts/fast_resume.sh runs/fast_resume.sh
#   nohup python3 scripts/detach.py /bin/bash runs/fast_resume.sh >> runs/queue.log 2>&1 < /dev/null &
set -u
log() { echo "$(date '+%F %T') fast_resume $$: $*"; }
secs() { awk -F'[-:]' '{n=NF; t=$n+60*$(n-1); if(n>=3) t+=3600*$(n-2); if(n>=4) t+=86400*$(n-3); print t}' <<< "$1"; }

log "start: queue retry waits cut from 600s to ${FAST_WAIT:-60}s"
while :; do
  ps -axo pid=,ppid=,etime=,command= | awk '$4 == "sleep" && $5 == "600" && NF == 5 {print $1, $2, $3}' |
    while read -r pid ppid et; do
      ps -o command= -p "$ppid" 2>/dev/null | grep -q 'arm_queue' || continue
      s=$(secs "$et")
      [ "$s" -ge "${FAST_WAIT:-60}" ] || continue
      kill "$pid" 2>/dev/null && log "ended retry wait after ${s}s (sleep $pid, queue subshell $ppid); the queue resumes now"
    done
  sleep "${FAST_POLL:-10}"
done
