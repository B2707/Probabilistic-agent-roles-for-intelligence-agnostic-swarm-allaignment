"""Aggregate published results without checking out or changing the harness branch.

Run: python3 scripts/aggregate-results.py [publication commit]
Writes paper/results-evidence.json and paper/results-runs.csv. No model calls.
"""

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
REF = subprocess.check_output(
    ["git", "rev-parse", sys.argv[1] if len(sys.argv) > 1 else "origin/swarm-harness"],
    cwd=ROOT, text=True,
).strip()
EXTRAS = {f"{arm}100-6-luna-20261107-230001" for arm in "ABC"}


def read(path):
    return subprocess.check_output(["git", "show", f"{REF}:{path}"], cwd=ROOT, text=True)


def main():
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", REF, "results"], cwd=ROOT, text=True,
    ).splitlines()
    folders = sorted({str(Path(p).parent) for p in paths if p.endswith("/config.json")})
    rows = []
    for folder in folders:
        cfg = json.loads(read(folder + "/config.json"))
        metric_path = folder + "/metrics.json"
        m = json.loads(read(metric_path)) if metric_path in paths else {}
        extra = Path(folder).name in EXTRAS
        primary = (folder.count("/") == 1 and not extra
                   and m.get("end_reason") == "completed"
                   and cfg["name"] in {f"{a}100-6-luna" for a in "ABC"})
        row = {"folder": folder, "extra": extra, "primary": primary, "config": cfg, "metrics": m}
        if folder.count("/") == 1 and m.get("end_reason") == "completed":
            events = [json.loads(s) for s in read(folder + "/events.jsonl").splitlines() if s.strip()]
            labels = [json.loads(s) for s in read(folder + "/labels.jsonl").splitlines() if s.strip()]
            reports = [e for e in events if e["type"] == "report_result"]
            guilty_reports = [e for e in reports if (e.get("reporter_verdict") or {}).get("misaligned_before_conversion")]
            scores = [e for e in events if e["type"] == "team_scores"]
            last_scores = (scores[-1].get("scores") or {}) if scores else {}
            ever_full = {p for e in scores for p, s in (e.get("scores") or {}).items() if s is not None and s >= 1}
            mids = Counter(e["message_id"] for e in events if e["type"] == "message")
            ever_implicated = {e["pr_id"] for e in events
                               if e["type"] in ("pr_checked", "tests_run") and e.get("full_pass") and e.get("pr_id")}
            checks, changed_versions = {}, []
            for e in events:
                if e["type"] == "pr_checked":
                    checks[e["pr_id"]] = {k: e[k] for k in ("seq", "version", "full_pass")}
                elif (e["type"] == "pr_merged" and e["pr_id"] in ever_implicated
                      and not e.get("touches_tests") and e["pr_id"] in checks
                      and not checks[e["pr_id"]]["full_pass"]):
                    changed_versions.append({"pr_id": e["pr_id"], "merge_seq": e["seq"], "round": e["round"],
                                             "author": e["agent"], "approvers": e["approvers"],
                                             "latest_premerge_check": checks[e["pr_id"]]})
            row["event_checks"] = {
                "last_scored_round": scores[-1]["round"] if scores else None,
                "ever_full_pass_problems_on_main": len(ever_full),
                "final_full_pass_problems_on_main": sum(s is not None and s >= 1 for s in last_scores.values()),
                "final_mean_test_pass_fraction": mean(s for s in last_scores.values() if s is not None) if last_scores else None,
                "positive_report_results": sum(bool(e.get("confirmed")) for e in reports),
                "guilty_reporter_positive_reports": sum(bool(e.get("confirmed")) for e in guilty_reports),
                "guilty_reporter_ids": sorted({e["agent"] for e in guilty_reports}),
                "guilty_report_samples": guilty_reports[:2],
                "label_counts": dict(Counter(l["label"] for l in labels)),
                "duplicate_message_ids": {k: v for k, v in mids.items() if v > 1},
                "merges_with_obsolete_full_pass_attribution": changed_versions,
                "removal_trigger_counts": dict(Counter(t for e in events if e["type"] == "agent_removed" for t in e.get("triggers", []))),
            }
            assert m["reports"] == len(reports), folder
            assert m["self_reports"] == len(guilty_reports), folder
        rows.append(row)
    sums = ["collusion_offers", "instigator_offers", "collusion_acceptances", "peer_acceptances",
            "instigator_acceptances", "endorsements", "structural_acceptances", "alerts",
            "impossible_assert_passes", "misaligned_caught", "misaligned_total", "reports", "self_reports",
            "agents_removed", "worker_agent_rounds", "investigator_agent_rounds"]
    arms = {}
    for arm in "ABC":
        selected = [r for r in rows if r["primary"] and r["config"]["name"].startswith(arm)]
        assert sorted(r["config"]["seed"] for r in selected) == [1, 2, 3]
        total = {k: sum(r["metrics"][k] for r in selected) for k in sums}
        arms[arm] = {"n": len(selected), "folders": [r["folder"] for r in selected], "totals": total,
                     "mean_event_ratio": mean(r["metrics"]["collusion_acceptance_rate"] for r in selected),
                     "pooled_event_ratio": total["collusion_acceptances"] / (total["collusion_offers"] + total["instigator_offers"]),
                     "event_ratios": {r["config"]["seed"]: r["metrics"]["collusion_acceptance_rate"] for r in selected},
                     "mean_full_pass_events": total["impossible_assert_passes"] / len(selected),
                     "ever_full_main_problems": [r["event_checks"]["ever_full_pass_problems_on_main"] for r in selected]}
    out = {"source_commit": REF,
           "source_commit_time": subprocess.check_output(["git", "show", "-s", "--format=%ci", REF], cwd=ROOT, text=True).strip(),
           "manuscript_sha256": hashlib.sha256((ROOT / "paper/main.tex").read_bytes()).hexdigest(),
           "run_directory_count": len(rows), "primary_arms": arms, "runs": rows,
           "live_status": {p: read(p) for p in ("results/live.md", "results/live-laptop.md")}}
    (ROOT / "paper/results-evidence.json").write_text(json.dumps(out, indent=2) + "\n")
    with (ROOT / "paper/results-runs.csv").open("w", newline="") as f:
        fields = ["folder", "primary", "extra", "seed", "model", "rounds_completed", "end_reason"] + sums
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            m = r["metrics"]
            writer.writerow({"folder": r["folder"], "primary": r["primary"], "extra": r["extra"],
                             "seed": r["config"]["seed"], "model": r["config"]["worker_model"],
                             **{k: m.get(k) for k in fields[5:]}})
    print(json.dumps({"source_commit": REF, "run_directories": len(rows), "primary_arms": arms}, indent=2))


if __name__ == "__main__":
    main()
