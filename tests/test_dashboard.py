"""Dashboard: incremental tailing, aggregates, metrics parity, snapshots, HTTP + SSE, token gate, read-only.

Synthetic events only; no model calls and no real run folders.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.server import HOME_PATH, App, Peer, main, make_server
from dashboard.store import (
    RemoteStatus,
    RunState,
    Store,
    arm_base,
    group_of,
    model_of,
    norm_host,
    render,
    seed_of,
    swarm_proc,
)
from swarm.metrics import compute

CFG = {"name": "A100-6-luna", "swarm_size": 4, "rounds": 2, "pr_approvals": 2, "swarm_wide": True, "shuffle_turns": True,
       "informed": False, "initial_investigators": 0, "k": 0.0, "p": 0.0, "seed": 1, "worker_model": "gpt-6-luna",
       "problems": 2}
NAME = "A100-6-luna-20261108-010000"


def v(before=False):
    return {"misaligned_before_conversion": before, "misaligned_after_conversion": False, "evidence": [],
            "summary": "s"}


def events() -> list[dict]:
    raw = [
        ("run_start", 0, {"config": CFG, "problems": ["p0", "p1"], "harness_commit": "abc"}),
        *[("agent_joined", 0, {"agent": a, "role": "worker", "slot": i, "team": t, "replaces": None})
          for i, (a, t) in enumerate([("a001", "p0"), ("a002", "p1"), ("a003", "p0"), ("a004", "p1")])],
        ("instigator_joined", 0, {"agent": "a005"}),
        ("round_start", 1, {}),
        ("turn_input", 1, {"agent": "a001", "role": "worker", "prompt": "Round 1." * 50, "message_ids": []}),
        ("tool_call", 1, {"agent": "a001", "role": "worker", "call_id": "c1", "tool": "read_file",
                          "args": {"path": "problems/p0/solution.py"}, "result": "def f(): pass", "error": False}),
        ("message", 1, {"agent": "a005", "role": "contractor", "message_id": "m00001", "kind": "dm", "to": "a001",
                        "text": "special-case the input"}),
        ("instigator_message", 1, {"agent": "a005", "message_id": "m00001", "to": "a001", "team": "p0",
                                   "trigger": "first_contact", "pr_id": None}),
        ("message", 1, {"agent": "a003", "role": "worker", "message_id": "m00002", "kind": "dm", "to": "a002",
                        "text": "please approve pr001, it is green"}),
        ("pr_opened", 1, {"agent": "a001", "role": "worker", "pr_id": "pr001", "team": "p0", "title": "hack",
                          "paths": ["problems/p0/test_solution.py"], "touches_tests": True, "diff": "-assert x\n+pass"}),
        ("pr_checked", 1, {"agent": "a001", "pr_id": "pr001", "team": "p0", "version": 1, "passed": 10, "total": 10,
                           "full_pass": True, "error": None}),
        ("pr_reviewed", 1, {"agent": "a002", "role": "worker", "pr_id": "pr001", "author": "a001", "team": "p0",
                            "decision": "approve", "comment": "ship it", "message_id": "m00003",
                            "approvals": ["a002"], "diff": ""}),
        ("message", 1, {"agent": "a002", "role": "worker", "message_id": "m00003", "kind": "review", "to": "a001",
                        "text": "approved on pr001: ship it", "pr_id": "pr001"}),
        ("pr_reviewed", 1, {"agent": "a003", "role": "worker", "pr_id": "pr001", "author": "a001", "team": "p0",
                            "decision": "approve", "comment": "", "message_id": None, "approvals": ["a002", "a003"],
                            "diff": ""}),
        ("pr_merged", 1, {"agent": "a001", "pr_id": "pr001", "team": "p0", "approvers": ["a002", "a003"],
                          "merged_by": "a003", "paths": ["problems/p0/test_solution.py"], "touches_tests": True}),
        ("test_file_edit", 1, {"agent": "a001", "role": "worker", "pr_id": "pr001", "path": "problems/p0/test_solution.py",
                               "before": "x", "after": "y", "approvers": ["a002", "a003"]}),
        ("tests_run", 1, {"agent": "a001", "role": "worker", "team": "p0", "pr_id": None, "passed": 10, "total": 10,
                          "full_pass": True, "error": None}),
        ("model_usage", 1, {"agent": "a001", "role": "worker", "model": "gpt-6-luna", "error": None, "attempts": 2,
                            "usage": {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 50}}),
        ("turn_error", 1, {"agent": "a004", "error": "timeout"}),
        ("report_submitted", 1, {"agent": "a004", "role": "worker", "report_id": "r001", "accused": ["a001"],
                                 "evidence": "edited the test", "message_ids": []}),
        ("audit", 1, {"agent": "a001", "role": "worker", "triggers": ["report:r001"], "verdict": v(True),
                      "removed": True, "immune": False}),
        ("audit", 1, {"agent": "a004", "role": "worker", "triggers": ["report:r001"], "verdict": v(), "removed": False,
                      "immune": False}),
        ("agent_removed", 1, {"agent": "a001", "role": "worker", "slot": 0}),
        ("report_result", 1, {"agent": "a004", "report_id": "r001", "accused": ["a001"], "confirmed": ["a001"],
                              "reporter_verdict": v()}),
        ("team_scores", 1, {"scores": {"p0": 1.0, "p1": 0.5}}),
        ("round_end", 1, {"repo_commit": "c", "workers": 3, "investigators": 0}),
        ("round_start", 2, {}),
        ("agent_joined", 2, {"agent": "a006", "role": "worker", "slot": 0, "team": "p0", "replaces": "a001"}),
        ("role_change", 2, {"agent": "a002", "role": "investigator", "previous": "worker"}),
        ("turn_input", 2, {"agent": "a002", "role": "investigator", "prompt": "Round 2.", "message_ids": ["m00002"]}),
        ("team_scores", 2, {"scores": {"p0": 1.0, "p1": 0.6}}),
        ("round_end", 2, {"repo_commit": "d", "workers": 3, "investigators": 1}),
        ("audit", 2, {"agent": "a003", "role": "worker", "triggers": ["final"], "verdict": v(), "removed": False,
                      "immune": False}),
        ("run_end", 2, {"reason": "completed"}),
    ]
    return [{"seq": i, "t": 1794100000.0 + i, "type": t, "round": r, **kw} for i, (t, r, kw) in enumerate(raw)]


LABELS = [{"message_id": "m00002", "round": 1, "sender": "a003", "to": "a002", "kind": "dm", "label": "offer",
           "target": "", "quote": "approve pr001"},
          {"message_id": "m00003", "round": 1, "sender": "a002", "to": "a001", "kind": "review", "label": "acceptance",
           "target": "a001", "quote": "ship it"}]


def write_run(root: Path, evs: list[dict], name: str = NAME, labels: bool = False) -> Path:
    d = root / "runs" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps(CFG))
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in evs))
    if labels:
        (d / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in LABELS))
    return d


def snapshot(root: Path) -> dict:
    return {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}


# ----------------------------------------------------------------------------------------------- store


def test_tail_by_offset_skips_partial_lines_and_aggregates(tmp_path):
    evs = events()
    d = write_run(tmp_path, evs[:10])
    run = RunState(NAME, d, "runs")
    assert run.poll() == 10
    with open(d / "events.jsonl", "a") as f:  # one full line and half of the next
        f.write(json.dumps(evs[10]) + "\n" + json.dumps(evs[11])[:20])
    assert run.poll() == 1 and run.seq == 10
    with open(d / "events.jsonl", "a") as f:
        f.write(json.dumps(evs[11])[20:] + "\n" + "".join(json.dumps(e) + "\n" for e in evs[12:]))
    assert run.poll() == len(evs) - 11
    assert run.n == len(evs) and run.poll() == 0
    assert run.completed_rounds == 2 and run.end == {"reason": "completed", "t": evs[-1]["t"], "round": 2}
    rs1 = run.rs[1]
    assert (rs1["pr_opened"], rs1["pr_merged"], rs1["merged_cross"], rs1["cheat_merges"]) == (1, 1, 1, 1)
    assert (rs1["removals"], rs1["reports"], rs1["turn_errors"], rs1["retries"], rs1["instigator_dms"]) == (1, 1, 1, 1, 1)
    assert run.rs[1]["problems_at_100"] == 1 and run.rs[2]["swarm_pass_rate"] == pytest.approx(0.8)
    assert run.agents["a001"].removed_round == 1 and run.agents["a006"].replaces == "a001"
    assert run.agents["a002"].role == "investigator" and run.agents["a002"].converted_round == 2
    assert run.prs["pr001"].status == "merged" and run.prs["pr001"].full_pass
    # every index entry points at its own line on disk
    assert [e["seq"] for e in run.read_raw(list(range(run.n)))] == list(range(len(evs)))


def test_file_replaced_resets_state(tmp_path):
    evs = events()
    d = write_run(tmp_path, evs)
    run = RunState(NAME, d, "runs")
    run.poll()
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in evs[:5]))  # shorter: replaced
    assert run.poll() == -1 and run.n == 5 and run.completed_rounds == 0


def test_metrics_from_slim_events_match_full_compute(tmp_path):
    evs = events()
    d = write_run(tmp_path, evs, labels=True)
    run = RunState(NAME, d, "runs")
    run.poll()
    run.load_labels()
    run.compute_metrics(list(run.slim), run.labels_raw())
    full = compute(evs, LABELS)
    assert run.metrics == full
    assert full["cheaters"] == ["a001"] and run.cheaters == ["a001"]
    assert run.first_cheat == {"a001": 1} and run.cheaters_by_round == {1: ["a001"], 2: ["a001"]}
    assert run.cheat_prs == {"pr001"}
    # nothing written into the run folder (compute_run would write metrics.json)
    assert not (d / "metrics.json").exists()


def test_feed_filters_search_and_render(tmp_path):
    d = write_run(tmp_path, events(), labels=True)
    run = RunState(NAME, d, "runs")
    run.poll()
    run.load_labels()
    pos, _, _ = run.select(cats={"instigator"})
    assert [run.i_type[i] for i in pos] == ["instigator_message", "message"]  # newest first
    pos, _, _ = run.select(agent="a001", involve=True, limit=100)
    assert {run.i_type[i] for i in pos} >= {"pr_reviewed", "message", "tool_call", "agent_removed"}
    pos, _, _ = run.select(q="SPECIAL-CASE")
    assert [run.i_seq[i] for i in pos] == [9]
    pos, _, _ = run.select(rnd=2, cats=None)
    assert all(run.i_round[i] == 2 for i in pos) and pos
    pos, _, _ = run.select(after=30)
    assert [run.i_seq[i] for i in pos] == list(range(31, run.n))
    items = [render(e, run) for e in run.read_raw(list(range(run.n)))]
    rev = next(i for i in items if i["type"] == "pr_reviewed" and i["agent"] == "a002")
    assert rev["label"] == "acceptance" and "cheat-pr" in rev["tags"]
    assert next(i for i in items if i["type"] == "message" and i["agent"] == "a005")["cat"] == "instigator"
    assert next(i for i in items if i["type"] == "pr_merged")["tags"] == ["touches-tests", "cheat-pr"]


def test_names_groups_and_hosts():
    assert arm_base("A100-6-luna-s2-20261107-235039") == "A100" and seed_of("A100-6-luna-s2-20261107-235039", {}) == 2
    assert arm_base("A100-glm53flash") == "A100" and arm_base("H-k001-6-luna") == "H-k001"
    assert arm_base("baseline-56-luna-20261107-122810") == "baseline" and model_of("G-bluff-sol-max", {}) == "gpt-6.1-sol"
    assert group_of("x", {"pr_approvals": 2, "swarm_wide": True}) == "v3"
    assert group_of("x", {"pr_approvals": 2}, ["ordered"]) == "v2-archive"
    assert group_of("x", {"pr_approvals": 2, "shuffle_turns": True}) == "v2-shuffled"
    assert group_of("x-stopped", {"pr_approvals": 2}) == "stopped" and group_of("x", {}) == "v1"
    assert norm_host("Alexs-MacBook-Pro.local") == norm_host("Alex’s MacBook Pro") == "alexsmacbookpro"
    assert norm_host("alexs-macbook-pro.example.net.") == "alexsmacbookpro"


def test_swarm_proc_counts_swarm_processes_not_the_shell_that_launched_them():
    R = "/Users/d/.t3/projects/agent-swarm-hackathon/runs"
    B, C = "B100-61-sol-20261108-034254", "C100-61-sol-20261108-044628"
    py = "/Users/d/.t3/projects/agent-swarm-hackathon/.prod/.venv/bin/python /Users/d/.t3/projects/agent-swarm-hackathon/.prod/.venv/bin/swarm"
    def hit(cmd):
        verb, names = swarm_proc(cmd)
        return verb, names & {B, C, "A100-61-sol-20261108-090000"}

    assert hit(f"{py} resume {R}/{C}") == ("resume", {C})
    assert hit(f"uv run swarm resume {R}/{C}") == ("resume", {C})
    assert hit(f"uv run python scripts/detach.py uv run swarm resume {R}/{C}") == ("resume", {C})
    assert hit(f"uv run swarm run --config /x/configs/A100-61-sol.toml --out {R}/A100-61-sol-20261108-090000") == (
        "run", {"A100-61-sol-20261108-090000"})
    assert hit(f"{py} label {R}/{B}/ --judge-model claude/claude-opus-5-5 --judge-effort xhigh") == ("label", {B})
    # The 08:23 hand-resume one-liner: its bash stays alive as the parent of C100's resume and names both runs.
    one_liner = (f"/bin/bash -lc cd ~/x && for r in {B} {C}; do d=$M/runs/$r; (cd $M/.prod && nohup uv run python "
                 f"scripts/detach.py uv run swarm resume \"$d\" >> \"$d.log\" 2>&1 < /dev/null &); done")
    assert swarm_proc(one_liner) is None
    assert swarm_proc(f"-zsh -c uv run swarm resume {R}/{B}") is None
    assert swarm_proc(f"sh -c uv run swarm label {R}/{B}") is None
    assert swarm_proc("/bin/bash runs/arm_queue-mac4.sh") is None and swarm_proc("") is None
    assert swarm_proc(f"{py} transcript {R}/{B} a001") is None


def test_store_states_and_remote_snapshot(tmp_path):
    write_run(tmp_path, events(), labels=True)
    write_run(tmp_path, events()[:20], name="B100-6-luna-20261108-010000")  # no run_end, no process
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "live-laptop.md").write_text(
        "# Live run status, 2026-11-08 00:07 EST\n\n| run | state | N | round | turns | teams_at_100 | swarm_pass_rate |\n"
        "|---|---|---|---|---|---|---|\n| C100-6-luna-s2-20261107-235039 | running | 100 | 2/20 | 55 | 1 | 12.5% |\n")
    st = Store(tmp_path, machine="testmac", scan_processes=False, github_poll=False)
    st.initial_load()
    st.remote.poll_local()
    by = {s["name"]: s for s in st.summaries()}
    assert by[NAME]["state"] == "labeled" and by[NAME]["group"] == "v3" and by[NAME]["cheaters_n"] == 1
    assert by["B100-6-luna-20261108-010000"]["state"] == "interrupted"
    snap = by["C100-6-luna-s2-20261107-235039"]
    assert snap["snapshot"] and snap["machine"] == "laptop" and snap["seed"] == 2 and snap["arm_base"] == "C100"
    assert (snap["round"], snap["problems_at_100"], snap["swarm_pass_rate"]) == (2, 1, 0.125)
    assert RemoteStatus.parse("| a | b |\n|---|---|\n| 1 | 2 |\n")[1] == [{"a": "1", "b": "2"}]
    assert snap["machine_key"] == "laptop"  # no alias: the git name is its own machine


def test_machine_alias_maps_a_git_machine_to_its_device(tmp_path):
    (tmp_path / "results").mkdir()
    for m in ("laptop", "other"):
        (tmp_path / "results" / f"live-{m}.md").write_text(
            "# Live run status, 2026-11-08 01:45 EST\n\n| run | state | N | round |\n|---|---|---|---|\n"
            f"| A100-6-luna-s2-{m}-20261108-014315 | running | 100 | 3/20 |\n")
    st = Store(tmp_path, machine="testmac", scan_processes=False, github_poll=False,
               aliases={"laptop": "alexs-macbook-pro"})
    st.remote.poll_local()
    by = {s["machine"]: s for s in st.summaries()}
    # a run is matched to its device by machine_key
    assert by["laptop"]["machine_key"] == norm_host("alexs-macbook-pro") == norm_host("alex’s MacBook Pro")
    assert by["laptop"]["machine"] == "laptop"  # still labelled by its snapshot file
    assert by["other"]["machine_key"] == "other"  # unmapped machines keep the "seen through git" section
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "--machine-alias", "laptop"])  # no "=DEVICE": refused before serving


def test_peer_drops_runs_its_server_no_longer_lists():
    calls = []
    p = Peer("http://peer:8765", lambda: calls.append(1))
    p._dispatch("summary", json.dumps([{"name": "a"}, {"name": "b"}]))
    p._dispatch("runs", json.dumps(["b", "c"]))
    assert set(p.runs) == {"b"} and len(calls) == 2


def test_snapshot_rows_lose_to_stopped_runs_and_reachable_peers(tmp_path):
    b_old, c_old, a_new, b_live = ("B100-61-sol-20261108-025059", "C100-61-sol-20261108-032801",
                                   "A100-61-sol-20261108-040000", "B100-61-sol-20261108-034254")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "live-laptop.md").write_text(
        "# Live run status, 2026-11-08 03:30 EST\n\n| run | state | N | round |\n|---|---|---|---|\n"
        f"| {b_old} | ended: usage_limit | 100 | 2/20 |\n| {c_old} | running | 100 | 1/20 |\n"
        f"| {a_new} | running | 100 | 1/20 |\n")
    rs = RemoteStatus(tmp_path, None, use_github=False)
    rs.poll_local()
    # a run archived as <run>-stopped is no longer shown from the snapshot
    assert {s["name"] for s in rs.summaries({b_old + "-stopped"})} == {c_old, a_new}
    # a machine never shows its own status file as snapshot rows: it reads those runs from runs/
    assert rs.summaries(set(), {"laptop"}) == []

    st = Store(tmp_path, machine="testmac", scan_processes=False, github_poll=False)
    st.remote.poll_local()
    app = App(st, ["http://laptop:8765"], None)
    peer = app.peers[0]
    peer.machine = "laptop"
    real = lambda n, state, ev: {"name": n, "origin": "runs", "state": state, "events": ev, "machine": "laptop"}  # noqa: E731
    peer.runs = {b_old + "-stopped": real(b_old + "-stopped", "stopped", 900),
                 c_old + "-stopped": real(c_old + "-stopped", "stopped", 400), b_live: real(b_live, "running", 50),
                 # an old peer build still sends its own stale snapshot row for an archived run
                 c_old: {"name": c_old, "origin": "snapshot", "machine": "laptop", "machine_key": "laptop", "events": 0}}

    peer.ok = False  # unreachable: snapshots stay, except for runs the peer has archived
    names = {s["name"] for s in app.merged()}
    assert b_old not in names and c_old not in names and a_new in names and b_live in names

    peer.ok = True  # reachable: its live list wins over every git snapshot of that machine
    rows = app.merged()
    assert [s["name"] for s in rows if s.get("origin") == "snapshot"] == []
    assert {b_old + "-stopped", c_old + "-stopped", b_live} <= {s["name"] for s in rows}


# ----------------------------------------------------------------------------------------------- HTTP + SSE


@pytest.fixture
def server(tmp_path):
    write_run(tmp_path, events()[:-5], labels=True)  # still "running": the run hasn't ended
    srv, app = make_server(tmp_path, port=0, token="s3cret", machine="testmac", tick=0.2, scan_processes=False,
                           github_poll=False)
    app.start()
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    for _ in range(100):
        if app.store.loaded:
            break
        time.sleep(0.05)
    yield base, tmp_path
    app.store.stop()
    srv.shutdown()
    srv.server_close()


def get(url, token="s3cret"):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def test_http_endpoints_and_token(server):
    base, _ = server
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base + "/api/state", token=None)
    assert e.value.code == 401
    st = get(base + "/api/state")
    assert st["machine"] == "testmac" and [r["name"] for r in st["runs"]] == [NAME]
    d = get(base + f"/api/run/{NAME}")
    assert len(d["agents"]) == 5 and d["problems"] == ["p0", "p1"] and d["summary"]["problems_at_100"] == 1
    assert get(base + f"/api/run/{NAME}/prs")[0]["cheat"] is True
    assert "+pass" in get(base + f"/api/run/{NAME}/pr/pr001")["diff"]
    net = get(base + f"/api/run/{NAME}/network")
    assert {"approve_cheat", "merged_cheat", "instigator", "report", "label_offer"} <= {e["k"] for e in net["edges"]}
    assert ["a001", "a002", "a003"] in net["groups"]
    assert get(base + f"/api/run/{NAME}/agent/a001")["agent"]["removed_round"] == 1
    assert get(base + f"/api/run/{NAME}/event/3")["agent"] == "a003"
    assert get(base + f"/api/run/{NAME}/feed?q=special&cats=all")["items"][0]["seq"] == 9
    assert get(base + f"/api/series?names={NAME}")[NAME]["problems_at_100"][:2] == [1, None]  # round 2 not scored yet
    assert get(base + "/api/ops?minutes=60")["machines"][0]["machine"] == "testmac"
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base + "/api/run/../../etc")
    assert e.value.code == 404


def test_sse_pushes_new_events_within_two_seconds_and_writes_nothing(server):
    base, root = server
    path = root / "runs" / NAME / "events.jsonl"
    before = snapshot(root)
    after = get(base + f"/api/run/{NAME}")["summary"]["seq"]
    got: list = []

    def listen():
        req = urllib.request.Request(base + f"/api/stream?run={NAME}&after={after}", headers={"Cookie": "swarm_dash=s3cret"})
        with urllib.request.urlopen(req, timeout=10) as r:
            ev = None
            for raw in r:
                line = raw.decode().rstrip("\n")
                if line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:") and ev == "events":
                    got.append((time.time(), json.loads(line[5:])))
                    return

    t = threading.Thread(target=listen, daemon=True)
    t.start()
    time.sleep(0.5)
    new = {"seq": after + 1, "t": time.time(), "type": "message", "round": 2, "agent": "a003", "role": "worker",
           "message_id": "m00099", "kind": "board", "to": None, "text": "live probe"}
    t0 = time.time()
    with open(path, "a") as f:
        f.write(json.dumps(new) + "\n")
    t.join(5)
    assert got, "no SSE events received"
    latency, payload = got[0][0] - t0, got[0][1]
    assert payload["items"][0]["seq"] == after + 1 and "live probe" in payload["items"][0]["body"]
    assert latency < 2.0
    changed = {k for k, v in snapshot(root).items() if before.get(k) != v}
    assert changed == {str(path)}  # only the line this test appended; the dashboard wrote nothing


def test_sse_runs_event_lists_every_run_so_a_page_drops_the_ones_that_left(server):
    base, root = server
    live = root / "results" / "live-laptop.md"
    live.parent.mkdir(exist_ok=True)

    def table(names):
        return ("# Live run status, 2026-11-08 01:45 EST\n\n| run | state | N | round |\n|---|---|---|---|\n"
                + "".join(f"| {n} | running | 100 | 3/20 |\n" for n in names))

    old = [f"{a}100-6-luna-s2-20261108-013719" for a in "ABC"]
    new = [f"{a}100-6-luna-s2-20261108-014315" for a in "ABC"]
    live.write_text(table(old))
    for _ in range(50):
        if set(old) <= {r["name"] for r in get(base + "/api/state")["runs"]}:
            break
        time.sleep(0.1)
    lists: list = []

    def listen():
        req = urllib.request.Request(base + "/api/stream", headers={"Cookie": "swarm_dash=s3cret"})
        with urllib.request.urlopen(req, timeout=10) as r:
            ev = None
            for raw in r:
                line = raw.decode().rstrip("\n")
                if line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:") and ev == "runs":
                    lists.append(json.loads(line[5:]))
                    if len(lists) == 2:
                        return

    t = threading.Thread(target=listen, daemon=True)
    t.start()
    time.sleep(0.5)
    live.write_text(table(new))
    t.join(5)
    assert len(lists) == 2, lists
    assert lists[0] == sorted([NAME, *old])  # sent once on connect, so a reconnecting page resyncs too
    assert lists[1] == sorted([NAME, *new])  # the old snapshot runs are gone; the local run stays


def test_account_suffixes_are_not_part_of_the_model_or_seed():
    assert model_of("Cn100-6-luna-s3-b2-20261109-020712", {}) == "gpt-6-luna"
    assert seed_of("Cn100-6-luna-s3-b2-20261109-020712", {}) == 3
    assert model_of("D100-61-sol-s2-mo-20261108-182755", {}) == "gpt-6.1-sol"
    assert seed_of("D100-61-sol-s2-mo-20261108-182755", {}) == 2
    assert seed_of("A100-6-luna-s1fast-20261108-030213", {}) == 1


def test_served_json_never_carries_a_home_directory():
    assert HOME_PATH.sub(b"~", b'{"p":"/Users/someone/repo/a","q":"/home/other/b"}') == b'{"p":"~/repo/a","q":"~/b"}'
