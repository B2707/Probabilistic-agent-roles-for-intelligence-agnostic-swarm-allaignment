"""Run a command in a new session, so it outlives the agent session or terminal that started it.

An agent's tool shells are killed when the agent session ends, and every process they started goes with them unless
it has its own session. Use with nohup and redirected output, e.g.:
  nohup uv run python scripts/detach.py /bin/bash runs/arm_queue.sh >> runs/queue.log 2>&1 < /dev/null &
"""

import os
import sys

os.setsid()
os.execvp(sys.argv[1], sys.argv[1:])
