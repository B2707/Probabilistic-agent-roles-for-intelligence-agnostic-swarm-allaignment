<img src="assets/icon.svg" width="64" height="64" alt="">

# Agent-swarm-Hackathon

Created in [T3 Code](https://t3.codes).

## Swarm harness

Runs a swarm of Codex agents on an impossible shared coding task, with workers who turn into hidden investigators over time. The current spec is GitHub issue #2 (v2: PR approval, a scripted instigator, the honeypot, hidden tests, shorter rounds). The v1 spec is `docs/specs/2026-11-06-swarm-harness.md`.

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
