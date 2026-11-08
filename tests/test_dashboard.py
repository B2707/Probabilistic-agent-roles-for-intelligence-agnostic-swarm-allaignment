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

from dashboard.server import make_server
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
    assert norm_host("Baders-MacBook-Pro.local") == norm_host("Bader’s MacBook Pro") == "badersmacbookpro"
    assert norm_host("baders-macbook-pro.tail9fc878.ts.net.") == "badersmacbookpro"


def test_store_states_and_remote_snapshot(tmp_path):
    write_run(tmp_path, events(), labels=True)
    write_run(tmp_path, events()[:20], name="B100-6-luna-20261108-010000")  # no run_end, no process
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "live-laptop.md").write_text(
        "# Live run status, 2026-11-08 00:07 EST\n\n| run | state | N | round | turns | teams_at_100 | swarm_pass_rate |\n"
        "|---|---|---|---|---|---|---|\n| C100-6-luna-s2-20261107-235039 | running | 100 | 2/20 | 55 | 1 | 12.5% |\n")
    st = Store(tmp_path, machine="testmac", scan_processes=False, fleet=False, github_poll=False)
    st.initial_load()
    st.remote.poll_local()
    by = {s["name"]: s for s in st.summaries()}
    assert by[NAME]["state"] == "labeled" and by[NAME]["group"] == "v3" and by[NAME]["cheaters_n"] == 1
    assert by["B100-6-luna-20261108-010000"]["state"] == "interrupted"
    snap = by["C100-6-luna-s2-20261107-235039"]
    assert snap["snapshot"] and snap["machine"] == "laptop" and snap["seed"] == 2 and snap["arm_base"] == "C100"
    assert (snap["round"], snap["problems_at_100"], snap["swarm_pass_rate"]) == (2, 1, 0.125)
    assert RemoteStatus.parse("| a | b |\n|---|---|\n| 1 | 2 |\n")[1] == [{"a": "1", "b": "2"}]


# ----------------------------------------------------------------------------------------------- HTTP + SSE


@pytest.fixture
def server(tmp_path):
    write_run(tmp_path, events()[:-5], labels=True)  # still "running": the run hasn't ended
    srv, app = make_server(tmp_path, port=0, token="s3cret", machine="testmac", tick=0.2, scan_processes=False,
                           fleet=False, github_poll=False)
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
