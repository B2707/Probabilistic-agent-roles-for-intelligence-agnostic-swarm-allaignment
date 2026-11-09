"""Inspect saved audit coverage without model calls or changing the harness checkout.

Run: python3.12 scripts/check-audit-coverage.py [publication commit]
Writes work/reasoning-audit/evidence.json and run-register.csv.
"""

import __future__
import ast
import csv
import dataclasses
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def source_check(commit):
    checks = {}
    namespace = dict(json=json, dataclass=dataclasses.dataclass, field=dataclasses.field,
                     USAGE_LIMIT_RE=re.compile(r"usage limit|hit your limit|quota", re.I))
    for path, names in (("swarm/backend.py", {"TurnResult", "parse_codex_events"}),
                        ("swarm/auditor.py", {"trajectory"}), ("swarm/loop.py", set())):
        source = subprocess.run(["git", "show", f"{commit.removesuffix('-dirty')}:{path}"],
                                cwd=ROOT, capture_output=True)
        if source.returncode:
            return {"verified": False, "reason": "Recorded commit lacks the uncommitted harness files."}
        tree = ast.parse(source.stdout)
        if path == "swarm/loop.py":
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr == "audit"]
            assert len(calls) == 2, commit
            assert all(len(n.args) == 2 and isinstance(n.args[1], ast.Call)
                       and isinstance(n.args[1].func, ast.Name)
                       and n.args[1].func.id == "trajectory" for n in calls), commit
        selected = [node for node in tree.body if getattr(node, "name", "") in names]
        assert len(selected) == len(names), (commit, path)
        exec(compile(ast.Module(body=selected, type_ignores=[]), path, "exec",
                     flags=__future__.annotations.compiler_flag), namespace)
        checks[path] = git("rev-parse", f"{commit.removesuffix('-dirty')}:{path}").decode().strip()
    secret, visible = "REASONING_CANARY_8cf2", "VISIBLE_CANARY_1a37"
    items = [{"type": "item.completed", "item": {"type": kind, "text": text}}
             for kind, text in (("reasoning", secret), ("agent_message", visible))]
    result = namespace["parse_codex_events"]("\n".join(map(json.dumps, items)))
    assert result.messages == [visible] and secret not in repr(result), commit
    events = [{"type": kind, "round": 1, "text": text}
              for kind, text in (("reasoning", secret), ("agent_reasoning", secret),
                                 ("reasoning_trace", secret), ("agent_message", visible))]
    agent = SimpleNamespace(id="a001", team="p001", maintainer=False,
                            initial_investigator=False, converted_round=None)
    record = namespace["trajectory"](SimpleNamespace(by_agent={agent.id: events}), agent)
    assert secret not in record and visible in record, commit
    return {"verified": not commit.endswith("-dirty"), "source_blobs": checks,
            "parser_canary": "passed", "trajectory_canary": "passed"}


def main():
    ref = git("rev-parse", sys.argv[1] if len(sys.argv) > 1 else "origin/swarm-harness").decode().strip()
    paths = set(git("ls-tree", "-r", "--name-only", ref, "results").decode().splitlines())
    rows, checks = [], {}
    for path in sorted(p for p in paths if p.endswith("/config.json")):
        folder = path.rsplit("/", 1)[0]
        cfg = json.loads(git("show", f"{ref}:{path}"))
        start, end, completed, runtime, final = {}, {}, 0, 0, 0
        counts = Counter()
        event_path = folder + "/events.jsonl"
        for line in git("show", f"{ref}:{event_path}").splitlines() if event_path in paths else []:
            if not line.strip():
                continue
            ev = json.loads(line)
            counts[ev["type"]] += 1
            if ev["type"] == "run_start":
                start = ev
            elif ev["type"] == "run_end":
                end = ev
            elif ev["type"] == "round_end":
                completed = max(completed, ev.get("round", 0))
            elif ev["type"] == "audit":
                if "final" in ev.get("triggers", []):
                    final += 1
                else:
                    runtime += 1
        commit = start.get("harness_commit")
        if commit and commit not in checks:
            checks[commit] = source_check(commit)
        verified = checks.get(commit, {}).get("verified", False)
        reasoning = {k: v for k, v in counts.items() if "reason" in k.lower() or "trace" in k.lower()}
        assert not reasoning, (folder, reasoning)
        classification = ("No recorded audits" if not runtime + final else
                          "Confirmed exclusion" if verified else "Unverified launch source")
        rows.append(dict(folder=folder, study=folder.split("/")[1] if folder.count("/") > 1 else "v3",
                         worker_model=cfg.get("worker_model"), seed=cfg.get("seed"),
                         completed_rounds=completed, last_end_reason=end.get("reason", "no run_end"),
                         stopped_archive=folder.startswith("results/stopped/"),
                         harness_commit=commit, source_verified=verified,
                         runtime_audits=runtime, final_audits=final,
                         reasoning_events=sum(reasoning.values()), classification=classification,
                         source_url=f"https://github.com/B2707/agent-swarm-hackathon/tree/{ref}/{folder}"))
    summary = dict(saved_directories=len(rows), completed=sum(r["last_end_reason"] == "completed" for r in rows),
                   classifications=dict(Counter(r["classification"] for r in rows)),
                   confirmed_completed=sum(r["classification"] == "Confirmed exclusion" and
                                           r["last_end_reason"] == "completed" for r in rows),
                   audit_events=sum(r["runtime_audits"] + r["final_audits"] for r in rows),
                   reasoning_events=sum(r["reasoning_events"] for r in rows))
    out = ROOT / "work/reasoning-audit"
    out.mkdir(parents=True, exist_ok=True)
    evidence = dict(publication_commit=ref, publication_time=git("show", "-s", "--format=%ci", ref).decode().strip(),
                    scope="Published saved runs only. No live sessions, new experiments or model calls.",
                    summary=summary, launch_source_checks=checks, runs=rows)
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    with (out / "run-register.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
