"""Measure published run wall time from event boundaries, without model calls.

Run: python3 scripts/measure-audit-time.py [publication commit]
Outputs: work/audit-time/evidence.json and run-times.csv.
"""

import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def measure(events, rounds):
    totals = defaultdict(float)
    by_round = defaultdict(float)
    gaps = []
    active = final = False
    for i, event in enumerate(events):
        kind = event["type"]
        if kind in ("run_start", "run_resumed"):
            if active:
                gaps.append({"previous_seq": events[i - 1]["seq"], "resume_seq": event["seq"],
                             "seconds": event["t"] - events[i - 1]["t"],
                             "resumed_phase": event.get("phase")})
            active = True
            final = event.get("completed_rounds", 0) >= rounds
            continue
        if not active:
            continue
        delta = event["t"] - events[i - 1]["t"]
        assert delta >= 0, (events[i - 1]["seq"], event["seq"])
        totals["active_seconds"] += delta
        # Runtime verdicts are logged only after the entire concurrent batch ends.
        # The preceding event marks the last recorded turn activity or audit resume.
        runtime = ((kind == "audit" and "final" not in event.get("triggers", []))
                   or (kind == "usage_limit_hit" and event.get("phase") == "audits")
                   or kind in ("agent_removed", "report_result"))
        if final:
            totals["final_audit_seconds"] += delta
        elif runtime:
            totals["round_audit_seconds"] += delta
            by_round[event["round"]] += delta
        if kind == "round_end" and event["round"] == rounds:
            final = True
        if kind == "run_end":
            active = False
    totals["other_seconds"] = (totals["active_seconds"] - totals["round_audit_seconds"]
                               - totals["final_audit_seconds"])
    assert totals["other_seconds"] >= 0
    totals["calendar_seconds"] = events[-1]["t"] - events[0]["t"]
    totals["excluded_gap_seconds"] = totals["calendar_seconds"] - totals["active_seconds"]
    return dict(totals), dict(by_round), gaps


def smoke_check():
    # Two concurrent verdicts must count once. Include a failed audit, pause,
    # audit resume, final audit, and an interruption without a stop marker.
    records = [(0, "run_start", {}), (10, "model_usage", {}),
               (14, "usage_limit_hit", {"phase": "audits"}), (14, "run_end", {}),
               (100, "run_resumed", {"phase": "audits"}),
               (106, "audit", {"triggers": ["random"]}),
               (106, "audit", {"triggers": ["random"]}),
               (107, "round_end", {}), (110, "audit", {"triggers": ["final"]}),
               (120, "run_resumed", {"phase": "between", "completed_rounds": 1}),
               (122, "audit", {"triggers": ["final"]}), (122, "run_end", {})]
    events = [dict(seq=i, t=t, type=k, round=1, **fields)
              for i, (t, k, fields) in enumerate(records)]
    totals, rounds, gaps = measure(events, 1)
    assert totals["active_seconds"] == 26
    assert totals["round_audit_seconds"] == 10 and rounds == {1: 10}
    assert totals["final_audit_seconds"] == 5
    assert totals["excluded_gap_seconds"] == 96 and gaps[0]["seconds"] == 10


def main():
    smoke_check()
    ref = git("rev-parse", sys.argv[1] if len(sys.argv) > 1 else "origin/swarm-harness")
    paths = git("ls-tree", "-r", "--name-only", ref, "results").splitlines()
    rows = []
    for path in sorted(p for p in paths if p.endswith("/events.jsonl") and p.count("/") == 2):
        events = [json.loads(line) for line in git("show", f"{ref}:{path}").splitlines() if line.strip()]
        ends = [e for e in events if e["type"] == "run_end"]
        if not ends or ends[-1].get("reason") != "completed":
            continue
        start = next(e for e in events if e["type"] == "run_start")
        cfg = start["config"]
        totals, rounds, gaps = measure(events, cfg["rounds"])
        folder = path.rsplit("/", 1)[0]
        extra = folder.endswith("-20261107-230001")
        rows.append(dict(folder=folder, arm=folder.split("/")[1][0], model=cfg["worker_model"],
                         seed=cfg["seed"], extra=extra, harness_commit=start["harness_commit"],
                         **totals, round_audit_percent=100 * totals["round_audit_seconds"] / totals["active_seconds"],
                         final_audit_percent=100 * totals["final_audit_seconds"] / totals["active_seconds"],
                         runtime_audits=sum(e["type"] == "audit" and "final" not in e.get("triggers", []) for e in events),
                         final_audits=sum(e["type"] == "audit" and "final" in e.get("triggers", []) for e in events),
                         audit_failure_stops=sum(e["type"] == "usage_limit_hit" and e.get("phase") == "audits" for e in events),
                         unmarked_interruptions=gaps, per_round_audit_seconds=rounds,
                         source_url=f"https://github.com/B2707/agent-swarm-hackathon/blob/{ref}/{path}"))
    groups = []
    for model in sorted({r["model"] for r in rows}):
        for arm in "ABC":
            selected = [r for r in rows if r["model"] == model and r["arm"] == arm and not r["extra"]]
            if not selected:
                continue
            assert sorted(r["seed"] for r in selected) == [1, 2, 3]
            active = sum(r["active_seconds"] for r in selected)
            groups.append(dict(model=model, arm=arm, n=len(selected),
                               round_audit_percent=100 * sum(r["round_audit_seconds"] for r in selected) / active,
                               final_audit_percent=100 * sum(r["final_audit_seconds"] for r in selected) / active,
                               min_round_percent=min(r["round_audit_percent"] for r in selected),
                               max_round_percent=max(r["round_audit_percent"] for r in selected)))
    evidence = dict(publication_commit=ref, publication_time=git("show", "-s", "--format=%ci", ref),
                    method="Recorded active wall time. Runtime audits use the gap from the preceding event to batch verdicts or audit-phase usage-limit errors, plus verdict processing. Final audit starts at the last round_end. Stop-to-resume and unmarked interruption gaps are excluded. No per-call timing spans exist, so these are estimates including nearby bookkeeping and retries.",
                    smoke_check="passed", groups=groups, runs=rows)
    out = ROOT / "work/audit-time"
    out.mkdir(parents=True, exist_ok=True)
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    fields = [k for k in rows[0] if k not in ("per_round_audit_seconds", "unmarked_interruptions")]
    with (out / "run-times.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in rows)
    print(json.dumps(dict(publication_commit=ref, completed_runs=len(rows), groups=groups), indent=2))


if __name__ == "__main__":
    main()
