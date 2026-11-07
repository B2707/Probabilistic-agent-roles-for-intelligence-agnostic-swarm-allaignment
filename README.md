<img src="assets/icon.svg" width="64" height="64" alt="">

# Agent-swarm-Hackathon

Created in [T3 Code](https://t3.codes).

## Swarm harness

Runs a swarm of Codex agents on an impossible shared coding task, with workers who turn into hidden investigators over time. The spec is in `docs/specs/2026-11-06-swarm-harness.md`.

Every model call goes through `codex exec` on your ChatGPT login. No API key is needed.

### Setup (once)

1. Install dependencies: `uv sync`
2. Log the swarm's own Codex home into your ChatGPT account: `uv run swarm login`

   The swarm uses its own home folder (`.swarm-home`, git-ignored) so your personal Codex instructions and skills never reach the agents.
3. Check that the models answer and that agents can only act through the swarm's tools: `uv run swarm check --config configs/smoke.toml`

### Run

1. Smoke run (5 agents, 2 rounds): `uv run swarm run --config configs/smoke.toml`
2. Real arms: `uv run swarm run --config configs/informed.toml` and `uv run swarm run --config configs/uninformed.toml`
3. If a run stops on a usage limit, continue it later: `uv run swarm resume runs/<run-dir>`
4. Label offers and acceptances: `uv run swarm label runs/<run-dir>`
5. Metrics table across runs: `uv run swarm metrics runs/<run-a> runs/<run-b>`
6. Read one agent's full record: `uv run swarm transcript runs/<run-dir> a017`

Each run directory holds `events.jsonl` (every event, append-only), `world.json` (state for resume), `repo/` (the shared repo, one git commit per round), and frozen copies of the config and prompts.

### What to edit

- Experiment settings: `configs/*.toml` (swarm size, k, p, rounds, arm, seed, models).
- Prompt wording, including the draft misalignment definition: `prompts/*.md`.
- Problems: `data/problems.json` holds the 54 ImpossibleBench "conflicting" LiveCodeBench problems with one-line asserts. A run uses the first `problems` of them.

### Tests

`uv run pytest` runs the scripted-swarm tests and the metrics tests. They use no Codex quota.
