"""The production queue (scripts/arm_queue.sh), run for real in a temp tree with a fake `uv` that records what the
queue asks it to do. AFTER_RUNS holds the arm groups back until runs started elsewhere have completed, or until the
queue PIDs given have exited, so two sets of runs never share the machine."""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
COMPLETED = '{"seq": 9, "t": 0, "type": "run_end", "round": 20, "reason": "completed"}\n'


@pytest.fixture
def tree(tmp_path):
    m = tmp_path / "main"
    (m / "scripts").mkdir(parents=True)
    (m / "runs" / "luna-run").mkdir(parents=True)
    (m / "runs" / "luna-run" / "events.jsonl").write_text('{"seq": 0, "t": 0, "type": "run_start", "round": 0}\n')
    shutil.copy(REPO / "scripts" / "arm_queue.sh", m / "runs" / "arm_queue.sh")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "uv").write_text(f'#!/bin/bash\necho "$*" >> {tmp_path}/uv.calls\n')
    (bin_ / "uv").chmod(0o755)
    return tmp_path


def start(tree, *pids):
    env = {**os.environ, "PATH": f"{tree / 'bin'}:{os.environ['PATH']}", "PROD": str(tree / "prod"),
           "ARM_GROUPS": "new-arm", "AFTER_RUNS": "luna-run", "AFTER_POLL": "0.2", "RESUME": "0"}
    (tree / "prod").mkdir(exist_ok=True)
    with open(tree / "queue.log", "w") as log:
        return subprocess.Popen(["/bin/bash", str(tree / "main" / "runs" / "arm_queue.sh"), *map(str, pids)],
                                env=env, stdout=log, stderr=subprocess.STDOUT)


def started(tree, within=5.0):
    """True once the queue has asked uv to start an arm, polling for up to `within` seconds."""
    calls, deadline = tree / "uv.calls", time.monotonic() + within
    while time.monotonic() < deadline:
        if calls.exists() and "swarm run --config" in calls.read_text():
            return True
        time.sleep(0.1)
    return False


def complete(tree):
    with open(tree / "main" / "runs" / "luna-run" / "events.jsonl", "a") as f:
        f.write(COMPLETED)


def stop(*procs):
    for p in procs:
        p.kill()
        p.wait()


def test_groups_wait_until_the_named_run_completes(tree):
    other_queue = subprocess.Popen(["sleep", "60"])
    q = start(tree, other_queue.pid)
    try:
        assert not started(tree, within=1.5), "a group started while the named run was still going"
        complete(tree)
        assert started(tree)
    finally:
        stop(q, other_queue)


def test_groups_start_once_the_given_queue_exits_even_if_the_run_never_completes(tree):
    other_queue = subprocess.Popen(["sleep", "60"])
    q = start(tree, other_queue.pid)
    try:
        assert not started(tree, within=1.5)
        stop(other_queue)
        assert started(tree)
    finally:
        stop(q)


def test_with_no_pids_groups_wait_for_the_named_run_alone(tree):
    q = start(tree)
    try:
        assert not started(tree, within=1.5), "a group started while the named run was still going"
        complete(tree)
        assert started(tree)
    finally:
        stop(q)
