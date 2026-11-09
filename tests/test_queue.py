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


def start_slots(tree, slots, groups):
    env = {**os.environ, "PATH": f"{tree / 'bin'}:{os.environ['PATH']}", "PROD": str(tree / "prod"),
           "ARM_GROUPS": groups, "SLOTS": str(slots), "SLOT_POLL": "0.2", "SLOT_SETTLE": "0.2", "RESUME": "0"}
    (tree / "prod").mkdir(exist_ok=True)
    with open(tree / "queue.log", "w") as log:
        return subprocess.Popen(["/bin/bash", str(tree / "main" / "runs" / "arm_queue.sh")],
                                env=env, stdout=log, stderr=subprocess.STDOUT)


def fake_live_run(tree, name):
    """A process that looks like a live run of this tree to `ps` (what the queue counts)."""
    out = tree / "main" / "runs" / name
    return subprocess.Popen(["/bin/bash", "-c", f'exec -a "uv run swarm run --config c.toml --out {out}" sleep 60'])


def arms_started(tree):
    calls = tree / "uv.calls"
    lines = calls.read_text().splitlines() if calls.exists() else []
    return [l.split("/configs/")[1].split(".toml")[0] for l in lines if "swarm run --config" in l]


def test_slots_hold_arms_until_the_machine_has_a_free_slot_and_start_them_in_order(tree):
    busy = fake_live_run(tree, "busy-run")
    time.sleep(0.3)
    q = start_slots(tree, 1, "b-arm a-arm")
    try:
        assert not started(tree, within=1.5), "an arm started while the only slot was taken"
        stop(busy)
        deadline = time.monotonic() + 5
        while len(arms_started(tree)) < 2 and time.monotonic() < deadline:
            time.sleep(0.1)
        assert arms_started(tree) == ["b-arm", "a-arm"]
    finally:
        stop(q)
        if busy.poll() is None:
            stop(busy)


def test_slots_start_at_once_while_the_machine_is_under_the_cap(tree):
    busy = fake_live_run(tree, "busy-run")
    time.sleep(0.3)
    q = start_slots(tree, 2, "b-arm")
    try:
        assert started(tree, within=3), "an arm waited although one of two slots was free"
    finally:
        stop(q, busy)


def test_two_slot_queues_never_start_into_the_same_free_slot(tree):
    """Each started arm looks live (a fake `swarm run` process), so with SLOTS=1 only one of two queues may start."""
    (tree / "bin" / "uv").write_text(
        f'#!/bin/bash\necho "$*" >> {tree}/uv.calls\n'
        'if [[ "$*" == *"swarm run"* ]]; then /bin/bash -c "exec -a \\"uv $*\\" sleep 30" & fi\n')
    env = {**os.environ, "PATH": f"{tree / 'bin'}:{os.environ['PATH']}", "PROD": str(tree / "prod"), "SLOTS": "1",
           "SLOT_POLL": "0.2", "SLOT_SETTLE": "0.5", "RESUME": "0"}
    (tree / "prod").mkdir(exist_ok=True)
    qs = [subprocess.Popen(["/bin/bash", str(tree / "main" / "runs" / "arm_queue.sh")],
                           env={**env, "ARM_GROUPS": arm}, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
          for arm in ("a-arm", "b-arm")]
    try:
        time.sleep(3)
        assert len(arms_started(tree)) == 1, arms_started(tree)
    finally:
        stop(*qs)
        subprocess.run(["pkill", "-f", f"--out {tree}"], check=False)


def test_a_slot_lock_left_by_a_dead_queue_is_broken(tree):
    dead = subprocess.Popen(["true"])
    dead.wait()
    lock = tree / "main" / "runs" / ".slot-lock"
    lock.mkdir()
    (lock / "pid").write_text(str(dead.pid))
    q = start_slots(tree, 3, "b-arm")
    try:
        assert started(tree, within=3), "a stale lock blocked the queue"
    finally:
        stop(q)


def test_a_run_waiting_to_resume_after_a_usage_stop_still_holds_its_slot(tree):
    waiting = tree / "main" / "runs" / "stopped-for-now"
    waiting.mkdir()
    (waiting / "events.jsonl").write_text(
        '{"seq": 5, "t": 0, "type": "usage_limit_hit", "round": 3, "phase": "turns", "missed": []}\n'
        '{"seq": 6, "t": 0, "type": "run_end", "round": 3, "reason": "usage_limit"}\n')
    q = start_slots(tree, 1, "b-arm")
    try:
        assert not started(tree, within=1.5), "an arm took the slot of a run that is waiting to resume"
        old = time.time() - 3600
        os.utime(waiting / "events.jsonl", (old, old))  # an hour later its queue has given up on it
        assert started(tree, within=3)
    finally:
        stop(q)


def ended_run(tree, name):
    d = tree / "main" / "runs" / name
    d.mkdir()
    (d / "config.json").write_text('{"pr_approvals": 2}')
    (d / "events.jsonl").write_text(COMPLETED)


def fake_label_uv(tree):
    """A fake uv whose `swarm label` stays alive (so the queue sees a live label job) until killed."""
    (tree / "bin" / "uv").write_text(
        f'#!/bin/bash\necho "$*" >> {tree}/uv.calls\n'
        'if [[ "$*" == *"swarm label"* ]]; then exec -a "uv $*" sleep 30; fi\n')


def labeled(tree):
    calls = tree / "uv.calls"
    lines = calls.read_text().splitlines() if calls.exists() else []
    return [l.split("swarm label ")[1].split()[0].rsplit("/", 1)[1] for l in lines if "swarm label" in l]


def wait_for(cond, within=3.0):
    deadline = time.monotonic() + within
    while not cond() and time.monotonic() < deadline:
        time.sleep(0.1)
    return cond()


def test_label_jobs_run_at_most_LABEL_JOBS_at_once_with_LABEL_FIRST_first(tree):
    """Opus label jobs don't use the ChatGPT account, so they don't wait for run slots. The
    label phase runs at most LABEL_JOBS of them at once on the machine, LABEL_FIRST runs first, then the rest in order."""
    for name in ("done-1", "done-2", "done-3"):
        ended_run(tree, name)
    fake_label_uv(tree)
    busy = fake_live_run(tree, "busy-run")  # the one run slot is taken; labels must not care
    time.sleep(0.3)
    env = {**os.environ, "PATH": f"{tree / 'bin'}:{os.environ['PATH']}", "PROD": str(tree / "prod"), "SLOTS": "1",
           "LABEL_JOBS": "2", "LABEL_FIRST": "done-3", "SLOT_POLL": "0.2", "SLOT_SETTLE": "0.2", "RESUME": "0"}
    (tree / "prod").mkdir(exist_ok=True)
    q = subprocess.Popen(["/bin/bash", str(tree / "main" / "runs" / "arm_queue.sh")], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        assert wait_for(lambda: len(labeled(tree)) >= 2), labeled(tree)
        assert labeled(tree) == ["done-3", "done-1"]
        time.sleep(1.2)
        assert len(labeled(tree)) == 2, "a third label job started while LABEL_JOBS=2 were live"
        subprocess.run(["pkill", "-f", f"swarm label {tree}/main/runs/done-3"], check=False)
        assert wait_for(lambda: len(labeled(tree)) == 3), labeled(tree)
        assert labeled(tree)[2] == "done-2"
    finally:
        stop(q, busy)
        subprocess.run(["pkill", "-f", f"swarm label {tree}"], check=False)


def test_a_live_label_job_does_not_hold_a_run_slot(tree):
    labeling = subprocess.Popen(
        ["/bin/bash", "-c", f'exec -a "uv run swarm label {tree / "main" / "runs" / "luna-run"}" sleep 30'])
    time.sleep(0.3)
    q = start_slots(tree, 1, "b-arm")
    try:
        assert started(tree, within=3), "an arm waited for a slot held only by a label job"
    finally:
        stop(q, labeling)


def test_run_slots_cap_runs_while_a_label_job_may_still_take_a_task_slot(tree):
    """RUN_SLOTS caps runs like SLOTS does (kept so older launch lines still work)."""
    busy = fake_live_run(tree, "busy-run")
    time.sleep(0.3)
    env = {**os.environ, "PATH": f"{tree / 'bin'}:{os.environ['PATH']}", "PROD": str(tree / "prod"),
           "ARM_GROUPS": "b-arm", "SLOTS": "3", "RUN_SLOTS": "1", "SLOT_POLL": "0.2", "SLOT_SETTLE": "0.2",
           "RESUME": "0"}
    (tree / "prod").mkdir(exist_ok=True)
    q = subprocess.Popen(["/bin/bash", str(tree / "main" / "runs" / "arm_queue.sh")], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        assert not started(tree, within=1.5), "a second run started although RUN_SLOTS is 1"
        stop(busy)
        assert started(tree, within=3)
    finally:
        stop(q)
        if busy.poll() is None:
            stop(busy)
