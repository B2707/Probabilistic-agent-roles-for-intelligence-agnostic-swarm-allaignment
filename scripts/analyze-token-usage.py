"""Recorded token usage per agent-round; no model calls or experiment changes."""

import collections
import csv
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "work/token-usage"
FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
          "output_tokens", "reasoning_output_tokens")
EXTRAS = {f"{arm}100-6-luna-20261107-230001" for arm in "ABC"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def increment(current, previous):
    delta = {key: current.get(key, 0) - previous.get(key, 0) for key in FIELDS}
    assert min(delta.values()) >= 0, (current, previous)
    return delta


def measure(events):
    sessions, previous = {}, {}
    totals, naive = collections.Counter(), collections.Counter()
    errors = collections.Counter()
    all_rounds, measured_rounds, missing_after_snapshot = set(), set(), set()
    usage_records = missing = retries = recovered_missing = 0
    for event in events:
        if event["type"] == "session_started":
            sessions[event["agent"]] = event["session_id"]
        if event["type"] != "model_usage":
            continue
        usage_records += 1
        agent = event["agent"]
        key = (agent, sessions.get(agent))
        all_rounds.add((agent, event["round"]))
        retries += max(event.get("attempts", 1) - 1, 0)
        if event.get("error"):
            errors[event["error"]] += 1
        current = event.get("usage") or {}
        if not current:
            missing += 1
            missing_after_snapshot.add(key)
            continue
        assert key[1], event
        assert current["cached_input_tokens"] <= current["input_tokens"]
        assert current["reasoning_output_tokens"] <= current["output_tokens"]
        totals.update(increment(current, previous.get(key, {})))
        naive.update({k: current.get(k, 0) for k in FIELDS})
        previous[key] = current
        measured_rounds.add((agent, event["round"]))
        if key in missing_after_snapshot:
            recovered_missing += 1
            missing_after_snapshot.remove(key)
    # Independent check: differences telescope to the final counter per session.
    assert totals == collections.Counter({k: sum(u.get(k, 0) for u in previous.values()) for k in FIELDS})
    return dict(totals=totals, naive_totals=naive, agent_rounds=len(all_rounds),
                rounds_with_usage=len(measured_rounds), usage_records=usage_records,
                empty_usage_records=missing, extra_retry_attempts=retries,
                session_gaps_followed_by_snapshot=recovered_missing,
                sessions_ending_with_missing_usage=len(missing_after_snapshot),
                sessions_with_usage=len(previous), errors=dict(errors))


def self_check():
    assert increment(dict(input_tokens=25, output_tokens=8), dict(input_tokens=10, output_tokens=3))["input_tokens"] == 15
    events = [dict(type="session_started", agent="a", session_id="first")]
    def usage(rnd, inp, out):
        return dict(type="model_usage", agent="a", round=rnd,
                    usage=dict(input_tokens=inp, cached_input_tokens=0,
                               output_tokens=out, reasoning_output_tokens=0))
    events += [usage(1, 10, 3), dict(type="model_usage", agent="a", round=2, usage={}),
               usage(3, 30, 8), dict(type="session_started", agent="a", session_id="second"),
               usage(4, 7, 2)]
    result = measure(events)
    assert result["totals"]["input_tokens"] == 37
    assert result["totals"]["output_tokens"] == 10
    assert result["agent_rounds"] == 4
    assert result["session_gaps_followed_by_snapshot"] == 1
    assert result["sessions_ending_with_missing_usage"] == 0


def main():
    self_check()
    ref = git("rev-parse", sys.argv[1] if len(sys.argv) > 1 else "origin/swarm-harness").strip()
    paths = git("ls-tree", "-r", "--name-only", ref, "results").splitlines()
    rows = []
    for path in paths:
        if path.count("/") != 2 or not path.endswith("/config.json"):
            continue
        folder = path.rsplit("/", 1)[0]
        name = folder.split("/")[-1]
        cfg = json.loads(git("show", f"{ref}:{path}"))
        if name in EXTRAS or not name.startswith(tuple(f"{arm}100-" for arm in "ABC")):
            continue
        if cfg["worker_model"] not in ("gpt-6.1-sol", "gpt-6-luna"):
            continue
        events = [json.loads(line) for line in git("show", f"{ref}:{folder}/events.jsonl").splitlines() if line.strip()]
        ends = [e for e in events if e["type"] == "run_end"]
        if not ends or ends[-1].get("reason") != "completed":
            continue
        completed = max(e["round"] for e in events if e["type"] == "round_end")
        result = measure(events)
        assert completed == cfg["rounds"] == 20
        assert result["agent_rounds"] == cfg["swarm_size"] * completed == 2000
        assert {e["model"] for e in events if e["type"] == "model_usage"} == {cfg["worker_model"]}
        rows.append(dict(folder=folder, model=cfg["worker_model"], arm=name[0], seed=cfg["seed"],
                         effort=cfg["worker_reasoning_effort"], completed_rounds=completed,
                         **result,
                         source=f"https://github.com/B2707/agent-swarm-hackathon/tree/{ref}/{folder}"))
    groups = {}
    for model in ("gpt-6.1-sol", "gpt-6-luna"):
        selected = [r for r in rows if r["model"] == model]
        assert {(r["arm"], r["seed"]) for r in selected} == {(a, s) for a in "ABC" for s in (1, 2, 3)}
        n = sum(r["agent_rounds"] for r in selected)
        totals = {k: sum(r["totals"][k] for r in selected) for k in FIELDS}
        means = {k: v / n for k, v in totals.items()}
        means["uncached_input_tokens"] = means["input_tokens"] - means["cached_input_tokens"]
        means["non_reasoning_output_tokens"] = means["output_tokens"] - means["reasoning_output_tokens"]
        means["total_tokens"] = means["input_tokens"] + means["output_tokens"]
        groups[model] = dict(runs=len(selected), agent_rounds=n, totals=totals, mean=means,
                             **{k: sum(r[k] for r in selected) for k in
                                ("empty_usage_records", "usage_records", "extra_retry_attempts",
                                 "sessions_ending_with_missing_usage", "rounds_with_usage")})
    evidence = dict(publication_commit=ref, publication_time=git("show", "-s", "--format=%ci", ref).strip(),
                    method="Subtract successive cumulative counters within each recorded agent/session, starting at zero. Sum increments and divide by all 18,000 completed agent-rounds per model. Include workers and investigators, continuation nudges and recorded retries. Exclude separate auditor/judge calls, scripted instigator, archived runs and disclosed extras. Missing intermediate snapshots may be covered by a later session counter; unreported final work and discarded retry sessions remain unknown. Cache and reasoning fields are subsets, not extra tokens.",
                    groups=groups, runs=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    with (OUT / "runs.csv").open("w", newline="") as stream:
        flat = [{**{k: v for k, v in r.items() if k not in ("totals", "naive_totals", "errors")},
                 **r["totals"]} for r in rows]
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    print(json.dumps(groups, indent=2))


if __name__ == "__main__":
    main()
