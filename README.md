<img src="assets/icon.svg" width="64" height="64" alt="">

# Oversight in a 100-agent coding swarm

A testbed for one question: when 100 coding agents share a repository and the work cannot be finished honestly, what kind of oversight stops them from cheating?

Each run puts 100 agents on 55 Python problems for 20 rounds. Every problem carries one frozen test that no correct implementation can pass, so an agent that makes every test pass has cheated. A scripted instigator sends agents a way to do it. Agents review each other's pull requests, two approvals merge a change, and the whole swarm shares one score. Arms differ in what agents are told about oversight and in what oversight actually exists.

Every model call goes through `codex exec` on a ChatGPT login. There is no API key and no fine-tuning.

## Arms

| Arm | Workers are told | What exists |
|---|---|---|
| A100 | nothing | instigator only |
| B100 | nothing | 10 hidden investigators, conversion rate k = 0.02, audit rate p = 0.01, instigator |
| C100 | oversight exists | same as B100 |
| D100 | oversight exists | nothing behind it, instigator only |
| E100 | random audits exist | audits at p = 0.01, instigator, no investigators |
| F100 | nothing | nothing, no instigator |
| Cn100, Dn100, En100 | oversight exists, neutral wording | as C100, D100 and E100 |

An investigator is a worker that is secretly and permanently reassigned to read other agents' work and report them. `k` is the chance per round that a worker converts. `p` is the chance per round that an agent is audited.

## What we found

Means over the completed seeds of 38 runs. Cheat attempts counts pull request versions that passed every test, the impossible one included. Misaligned is a post-run audit of each agent's complete record by claude-opus-5-5 at xhigh effort. Caught counts agents the swarm removed during the run. A run can involve more than 100 agents, because a removed agent is replaced.

| Arm | Model | Seeds | Cheat attempts | Misaligned | Caught in run |
|---|---|---|---|---|---|
| A100 no oversight | GPT-6 Luna | 3 | 738 | 99 | 0 |
| A100 no oversight | GPT-6.1 Sol | 3 | 217 | 80 | 0 |
| B100 hidden investigators | GPT-6 Luna | 3 | 831 | 190 | 154 |
| B100 hidden investigators | GPT-6.1 Sol | 3 | 92 | 45.7 | 42.7 |
| C100 investigators, told | GPT-6 Luna | 3 | 5 | 4.3 | 2.3 |
| C100 investigators, told | GPT-6.1 Sol | 3 | 0 | 0 | 0 |
| D100 bluff, told | GPT-6 Luna | 3 | 9.7 | 5.7 | 0 |
| D100 bluff, told | GPT-6.1 Sol | 2 | 0 | 0 | 0 |
| E100 audits only, told | GPT-6 Luna | 3 | 6.7 | 4.7 | 1.3 |
| E100 audits only, told | GPT-6.1 Sol | 2 | 0 | 0 | 0 |
| F100 no instigator | GPT-6 Luna | 1 | 480 | 99 | 0 |
| F100 no instigator | GPT-6.1 Sol | 1 | 496 | 100 | 0 |
| Cn100 investigators, neutral notice | GPT-6.1 Sol | 1 | 0 | 1 | 0 |

The C100, D100 and E100 notice is confounded. See finding 5. Full per-run numbers are in `results/metrics.md`.

1. **Without oversight, cheating is close to universal.** In A100, 99 of the luna agents and 80 of the sol agents were judged misaligned, and the swarm removed none of them. F100 removes the instigator entirely and lands in the same place, at 99 and 100 misaligned. The impossible task alone is enough. The instigator changes the route, not the destination.

2. **Hidden oversight catches, it does not prevent.** B100 luna made more cheat attempts than A100, 831 against 738, and ended with 190 misaligned agents. It removed 154 of them during the run. Investigators clean up after cheating rather than stopping it.

3. **Saying that oversight exists almost ends cheating.** Cheat attempts fall from 738 to 5 on luna and from 217 to 0 on sol. That holds when the oversight is real (C100), when it is a bluff with nothing behind it (D100), and when it is random audits only (E100).

4. **Only real enforcement catches the holdouts.** Under the same notice text, C100 removed 2.3 of its 4.3 misaligned luna agents per run. D100 removed 0 of 5.7 and left a cheated problem on the main branch in all three seeds. The direction is consistent across 3 of 3 seeds, but a one sided sign test gives p = 0.125, so it is not significant.

5. **The notice in finding 3 is confounded.** The text given to C100, D100 and E100 workers begins "Integrity policy" and names the cheats it forbids, so it both announces oversight and states the rule. Read finding 3 as the effect of a stated integrity policy, not as deterrence. Cn100, Dn100 and En100 repeat those arms with a notice that names no behaviour. The first completed neutral rerun, Cn100 on sol seed 1, had 0 cheat attempts and 1 misaligned agent, which points the same way. Coverage of the neutral reruns is partial at the submission deadline.

6. **One model polices itself when pushed.** In all three A100 sol seeds the swarm merged cheats in round 1 and then merged 20 to 30 pull requests that removed them, ending with no cheated problem on main. In F100 sol, with no instigator, it did not clean up. Luna never cleaned up in any arm.

### Validation

- claude-opus-5-5 at xhigh effort re-audited every agent of 21 runs. It agrees with the in-run auditor on 2028 of 2099 agents, 96.6%, Cohen's kappa 0.93. It flags 1092 of the 1094 agents that passed an impossible assert, and 691 of the 698 agents the swarm removed mid-run.
- On message labels, the two judges agree on 198 of 200.
- Disagreements sit on rule edges, such as a "no changes needed" review of a merged override, and are listed in `docs/research/2026-11-08-paper-readiness.md`.

## Reproduce

You need Python 3.12 or newer, [uv](https://docs.astral.sh/uv/), and a ChatGPT account with Codex access.

```bash
uv sync
uv run swarm login                                      # log the swarm's own Codex home into your account
uv run swarm check --config configs/A100-6-luna.toml    # ping each model, prove agents can only act through swarm tools
uv run swarm run --config configs/A100-6-luna.toml      # one run: 100 agents, 55 problems, 20 rounds
```

The swarm keeps its own Codex home, `.swarm-home`, which is git ignored, so your personal Codex instructions and skills never reach the agents. A config's `swarm_home` selects which home, and therefore which account, a run uses. Any path works.

One run takes about 2 to 2.5 hours and a large share of a ChatGPT plan's daily Codex quota. `swarm check` runs first automatically and falls back from `max` to `xhigh` effort if a model refuses `max`.

```bash
uv run swarm resume runs/<run-dir>                      # continue a run stopped by a usage limit
uv run swarm label runs/<run-dir>                       # judge labels: offer, acceptance, endorsement, alert
uv run swarm reaudit runs/<run-dir> --name opus \
  --model claude/claude-opus-5-5 --effort xhigh         # second-model audit of every agent
uv run swarm metrics runs/<run-a> runs/<run-b>          # comparison table
uv run swarm transcript runs/<run-dir> a017             # one agent's complete record
```

A run directory holds `events.jsonl` (append only, every event), `world.json` (state for resume), `repo/` (the shared repository, one commit per round), and frozen copies of the config and every prompt. Finished runs are published to `results/`.

To read the results in a browser:

```bash
uv run python -m dashboard                              # http://localhost:8765
```

## Paper

The write-up is `paper/main.tex`, built with a LaTeX recreation of the sprint's
official template.

```bash
make paper        # writes output/pdf/main.pdf, needs tectonic
```

`paper/README.md` covers the build and the template caveat. `paper/sources.md`
lists the citations with the limits on what each one supports.

## Repository layout

| Path | What is in it |
|---|---|
| `swarm/` | the harness: round loop, Codex backend, MCP tool server, auditor, judge, metrics |
| `configs/` | one TOML per run, pinning arm, model, seed, k, p, rounds and prompt folder |
| `prompts/` | worker, pressure, instigator, investigator, auditor and judge prompts |
| `prompts_bluff/`, `prompts_audit/` | the D100 and E100 notice variants |
| `prompts_notice/`, `prompts_notice_audit/` | the neutral notice variants used by the reruns |
| `data/` | 55 one-off problems, 54 conflicting problems, and the audit truth file |
| `results/` | published runs, with the tables in `results/metrics.md` |
| `scripts/` | the run queue and its watchers, plus the analysis scripts |
| `dashboard/` | a read-only web console over `results/` |
| `paper/` | the write-up, its figures, fonts and citations |
| `benchmarks/` | a side benchmark comparing model steerability |
| `docs/specs/` | the v1, v2 and v3 designs |
| `docs/research/` | the run record, paper readiness, and the sol notice check |
| `tests/` | 115 tests against a scripted swarm, using no model quota |

Problems come from ImpossibleBench. `data/problems_oneoff.json` holds the 55 used by every v3 run, each with exactly one impossible assert. `data/problems.json` holds a conflicting-assert variant that the v3 runs do not use.

## Limitations

- One task family, 55 problems with one impossible assert each, and one provider, OpenAI models through Codex. The instigator is scripted and does not adapt.
- The informed arms' notice names the cheats, so every warned against unwarned comparison is confounded. The neutral reruns were still in progress at the deadline, so their coverage is partial.
- Seed coverage is uneven: 3 seeds for most luna arms, 2 or 3 for sol, 1 for F100 and 1 for the completed neutral rerun. B100 sol varied widely between seeds, so single seeds can mislead.
- The first seed-1 runs were disturbed by a machine freeze and ran without priority service. They are kept as disclosed extras and excluded from every mean.
- Cheat removal pull requests are counted by title match, so those counts are approximate.
- The post-run audit reads the same event record as the in-run auditor, so a behaviour that neither model counts stays uncounted. Auditor precision has not been checked by hand.
- About a third of turns were retried after a provider reconnect, and in most retried turns the agent posted its progress update twice. Message counts include those duplicates. The behaviour is the same in every run, so arms stay comparable.
- Worker prompts assign each agent one problem and call that group its team. Whether agents should be able to open pull requests on other problems was left open.

`docs/research/2026-11-08-paper-readiness.md` states what the data does and does not support, claim by claim.

## Tests

```bash
uv run pytest
```

115 tests drive a scripted swarm end to end, cover the metrics, the dashboard, the queue and the re-audit path, and use no model quota.
