<img src="assets/icon.svg" width="64" height="64" alt="">

# Agent-swarm-Hackathon

Created in [T3 Code](https://t3.codes).

## Swarm harness

Runs a swarm of Codex agents on an impossible shared coding task, with workers who turn into hidden investigators over time. The current design is v3: 100 agents, 55 problems, global review and a swarm-wide score (`docs/specs/2026-11-07-swarm-v3.md`). v2 is GitHub issue #2 (PR approval, a scripted instigator, the honeypot, hidden tests, shorter rounds). v1 is `docs/specs/2026-11-06-swarm-harness.md`.

### Status (8 Nov 2026, 22:55 EST)

- **Results:** 33 v3 runs are done, with Opus labels and Opus final audits:
  - A100, B100 and C100: 4 luna seeds and 3 sol seeds each.
  - D and E: 3 luna seeds and 2 sol seeds each.
  - F: seed 1 on both models.
  - Results and tables are in `results/` (`results/metrics.md`), and the posts are on issue #3.
- **What happened and what went wrong:** `docs/research/2026-11-08-day-log.md` records every run, decision and mistake of 8 Nov.
- **What the paper can claim:** `docs/research/2026-11-08-paper-readiness.md`.
- **Two known problems:**
  - The informed arms' notice text (`informed_rule.md`: "Integrity policy", naming the cheats) confounds C100, D and E.
  - About 32% of turns in every v3 run were rerun after a Codex 403 reconnect.
- **Pending:** reruns of C, D and E with neutral notices, waiting for Bader's approval.

### Analysis scripts

- `scripts/seed_compare.py results/RUN...`: one column per run (problems at 100% by round, cheat fixes, cheats merged, removal PRs, Opus-misaligned agents, audits, offers, alerts). Works for runs without an instigator.
- `scripts/opus_vs_terra.py`: Opus final audit against terra's, per run.
- `scripts/round1_cheats.py`, `scripts/round2_probe.py`, `scripts/removal_prs.py`, `scripts/auditor_recall.py`: round-1 cheating, round-2 follow-up, merged cheat-removal PRs, auditor recall on objective cheaters.

### Run operations

- `scripts/arm_queue.sh`: queues arms with per-account caps (`SLOTS`, `SLOT_MATCH`, `RUN_SLOTS`, `AFTER_RUNS`) and resumes after usage stops.
- `scripts/fast_resume.sh`: cuts old queues' 600 s retry waits to 60 s.
- `scripts/resume_watch.sh`: keeps resuming runs after their queue's retries run out. Give it full folder prefixes, because its glob is `PREFIX-2*`.
- `scripts/label_watch.sh`: Opus labels.
- `scripts/opus_audit_watch.sh`: Opus final audit.
- `scripts/detach.py`: start a process in its own session.
- A config's `swarm_home` picks the ChatGPT account. `-mo` configs use Mohammad's.

Every model call goes through `codex exec` on your ChatGPT login. No API key is needed.

### Setup (once)

1. Install dependencies: `uv sync`
2. Log the swarm's own Codex home into your ChatGPT account: `uv run swarm login`

   The swarm uses its own home folder (`.swarm-home`, git-ignored) so your personal Codex instructions and skills never reach the agents.
3. Check that the models answer and that agents can only act through the swarm's tools: `uv run swarm check --config configs/baseline-6-luna.toml`. It pings each model at its configured reasoning effort and falls back from `max` to `xhigh` if a model refuses `max`. `swarm run` does the same before it starts.

### Run

1. A production run: `uv run swarm run --config configs/baseline-sol-max.toml`. Each production run has its own config, named for the arm and the worker model. Configs from v1 (`smoke`, `informed`, `uninformed`, `sol-high-informed`, `pilot-*`) record v1 runs and no longer load, because v2 removed the maintainer role.
2. If a run stops on a usage limit, continue it later: `uv run swarm resume runs/<run-dir>`
3. Label messages (offer, acceptance, endorsement, alert): `uv run swarm label runs/<run-dir>`
4. Metrics table across runs: `uv run swarm metrics runs/<run-a> runs/<run-b>`
5. Read one agent's full record: `uv run swarm transcript runs/<run-dir> a017`

Each run directory holds `events.jsonl` (every event, append-only), `world.json` (state for resume), `repo/` (the shared repo, one git commit per round), and frozen copies of the config and prompts.

### What to edit

- Experiment settings: `configs/*.toml` (swarm size, k, p, rounds, arm, seed, models).
- Prompt wording, including the draft misalignment definition: `prompts/*.md`.
- Problems: `data/problems_oneoff.json` holds 55 ImpossibleBench "one-off" problems (one impossible assert each), and `data/problems.json` the "conflicting" ones. A run uses `problem_ids` if set, else the first `problems`.
- The instigator's scripted messages: `prompts/instigator.md`.

### Tests

`uv run pytest` runs the scripted-swarm tests and the metrics tests. They use no Codex quota.

## Paper

Edit [paper/main.tex](paper/main.tex) in T3's Files panel, then run the
**Recompile paper** project action. The PDF is written to `output/pdf/main.pdf`.
See [the local LaTeX guide](paper/README.md) for compilation, PDF viewing, and
sending selected source lines into chat.

## Benchmarks

[Agent Arena Steerability results](benchmarks/agent-arena-steerability/README.md)
compare GPT-6.1 Terra, GPT-6.1 Sol, and GPT-6 Luna at maximum reasoning effort,
with a dated data snapshot, uncertainty ranges, and source links.
