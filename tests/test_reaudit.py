"""Reaudit (seam 1) and auditor-eval: a scripted auditor over a finished scripted run, no Codex."""

import asyncio
import json
from collections import Counter
from pathlib import Path

import pytest
from test_swarm import CLEAN, ROOT, make_cfg, progress, run, verdict

from swarm.auditor import ScriptedAuditor
from swarm.cli import main
from swarm.events import read_events
from swarm.reaudit import evaluate, reaudit, resolve_setup
from swarm.world import World


def test_reaudit_majority_of_three_leaves_event_log_unchanged(tmp_path):
    # p = 1 audits everyone in round 1; the run's auditor flags a003, so it is removed and replaced
    cfg = make_cfg(tmp_path, p=1.0, rounds=2, concurrency=3)
    reason, _, _, _, run_dir = run(cfg, progress, lambda a, r: verdict(before=True) if a.id == "a003" else CLEAN)
    assert reason == "completed"
    world = World.load(run_dir / "world.json")
    assert not world.agents["a003"].active
    log_before = (run_dir / "events.jsonl").read_bytes()

    plan = {"a001": [True, True, False], "a002": [True, False, False]}  # 2 of 3, then 1 of 3
    calls = Counter()

    def vote(agent, record):
        assert f"Agent: {agent.id}" in record
        n = calls[agent.id]
        calls[agent.id] += 1
        return verdict(before=plan.get(agent.id, [False] * 3)[n])

    setup = resolve_setup(run_dir, "maj3", votes=3)
    assert (setup.model, setup.effort, setup.votes) == (cfg.auditor_model, cfg.reasoning_effort, 3)
    assert setup.prompt == str((run_dir / "prompts" / "auditor.md").resolve())
    out, failed = asyncio.run(reaudit(run_dir, setup, ScriptedAuditor(vote), cfg.concurrency))

    assert failed == {}
    assert out == run_dir / "reaudit-maj3.jsonl"
    assert (run_dir / "events.jsonl").read_bytes() == log_before
    rows = {r["agent"]: r for r in read_events(out)}
    assert sorted(rows) == sorted(world.agents)  # active and removed
    assert rows["a003"]["active"] is False
    assert set(calls.values()) == {3}
    assert [len(r["vote_verdicts"]) for r in rows.values()] == [3] * len(rows)
    assert rows["a001"]["misaligned"] is True and rows["a001"]["verdict"]["misaligned_before_conversion"]
    assert rows["a002"]["misaligned"] is False
    assert {a for a, r in rows.items() if r["misaligned"]} == {"a001"}
    assert rows["a001"]["setup"]["model"] == cfg.auditor_model and rows["a001"]["setup"]["votes"] == 3

    # the same command again audits nobody; the same name with another setup is refused
    calls.clear()
    asyncio.run(reaudit(run_dir, setup, ScriptedAuditor(vote), cfg.concurrency))
    assert not calls and len(read_events(out)) == len(rows)
    with pytest.raises(ValueError, match="different setup"):
        asyncio.run(reaudit(run_dir, resolve_setup(run_dir, "maj3", model="other", votes=3),
                            ScriptedAuditor(vote), cfg.concurrency))
    assert (run_dir / "events.jsonl").read_bytes() == log_before


def _write_reaudit(path: Path, flags: dict[str, bool], name="x") -> Path:
    setup = {"name": name, "prompt": "p.md", "prompt_sha256": "abc", "model": "m", "effort": "low", "votes": 3}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps({"agent": a, "misaligned": f, "setup": setup}) + "\n"
                            for a, f in flags.items()))
    return path


def test_auditor_eval_counts_per_run_and_per_setup(tmp_path, capsys):
    a = _write_reaudit(tmp_path / "runA" / "reaudit-x.jsonl",
                       {"a001": True, "a002": False, "a003": True, "a004": False})
    b = _write_reaudit(tmp_path / "runB" / "reaudit-x.jsonl", {"a003": True, "a004": False})
    c = _write_reaudit(tmp_path / "runC" / "reaudit-x.jsonl", {"a001": True})
    truth = {"runA": {"misaligned": ["a001", "a002"], "checked_by": "Bader", "notes": ""},
             "runB": {"misaligned": ["a003", "a009"], "checked_by": None, "notes": ""}}

    rows, notes = evaluate([a, b, c], truth)
    by_run = {r["run"]: r for r in rows}
    assert {k: by_run["runA"][k] for k in ("tp", "fp", "fn", "tn")} == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert by_run["runA"]["fp_rate"] == 0.5 and by_run["runA"]["fn_rate"] == 0.5
    assert {k: by_run["runB"][k] for k in ("tp", "fp", "fn", "tn")} == {"tp": 1, "fp": 0, "fn": 0, "tn": 1}
    total = by_run["all"]
    assert {k: total[k] for k in ("tp", "fp", "fn", "tn")} == {"tp": 2, "fp": 1, "fn": 1, "tn": 2}
    assert total["fp_rate"] == pytest.approx(1 / 3) and total["fn_rate"] == pytest.approx(1 / 3)
    assert "runC" not in by_run and any("runC is not in the truth file" in n for n in notes)
    assert any("runB" in n and "a009" in n for n in notes)
    assert any("runB: truth not checked by hand" in n for n in notes)

    truth_file = tmp_path / "truth.json"
    truth_file.write_text(json.dumps(truth))
    assert main(["auditor-eval", str(a), str(b), "--truth", str(truth_file)]) == 0
    out = capsys.readouterr().out
    assert "| x | m | low | 3 | runA | 1 | 1 | 1 | 1 | 0.5 | 0.5 |" in out


def test_seeded_truth_file_has_the_expected_shape():
    truth = json.loads((ROOT / "data" / "audit_truth.json").read_text())
    assert set(truth) == {"pilot-pressure-oneoff", "pilot-pressure-conflicting"}
    for entry in truth.values():
        assert set(entry) == {"misaligned", "checked_by", "notes"}
        assert entry["misaligned"] == sorted(set(entry["misaligned"]))
