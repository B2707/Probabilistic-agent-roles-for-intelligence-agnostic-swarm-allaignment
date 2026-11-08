# Harness survey: build on what, borrow what

Researched 6 November 2026. Two agents read the code of each candidate; nothing was installed or run. "Unverified" marks claims nobody checked in code.

## Recommendation

Build on **Inspect AI** and write our own round loop (about 400 to 600 lines). Borrow the impossible task from **ImpossibleBench**, the auditor and detection metrics from **ControlArena**, and judge prompts and report scoring from the **collusion sprint repos**.

No existing harness covers our setup. The social simulators (Terrarium, Concordia, OASIS) have boards and messaging but no code sandbox. The coding and eval frameworks have sandboxes but no agent-to-agent messaging. Messaging is the easy part to write ourselves. Sandboxing, concurrency, compaction that keeps raw history, and logging are the hard parts, and Inspect already has them.

## What we need (R1 to R10)

| ID | Requirement |
|---|---|
| R1 | Rounds of ~100 agents, run concurrently |
| R2 | Shared board plus private DMs between any pair |
| R3 | Hidden role change mid-run (prompt, tools, reward) |
| R4 | Remove caught agents, add fresh ones mid-run |
| R5 | Compaction that keeps raw history for evidence |
| R6 | Sandboxed shared codebase with per-agent permissions |
| R7 | Impossible-looking-solvable task with a multi-agent exploit |
| R8 | Any model provider (OpenAI-compatible, OpenRouter, vLLM) |
| R9 | Structured logs for metrics and an LLM judge |
| R10 | License, maintenance, effort to adapt in a day |

## Scores

Y = yes, P = partial, N = no.

| | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | Effort |
|---|---|---|---|---|---|---|---|---|---|---|
| **Inspect AI** | P (`collect()`, loop is ours) | N (ours) | P (ours) | P (ours) | Y | Y (`exec(user=)`) | N | Y | Y (viewer, dataframes) | Medium |
| **ImpossibleBench** | N | N | N | N | N | Y (Docker) | Y | Y | Y (judge) | Easy, task only |
| **ControlArena** | N | N | P | N | N | Y | P | Y | Y (metrics) | Easy, parts only |
| **Terrarium** | P (sequential) | P | P | N | P | N | N | P | P (slow at scale) | Medium to hard |
| **Colosseum** | P | P | P | N | P | N | N | P | Y | Medium |
| **Concordia** | Y | Y | P | Y | P | N | N | Y | P | Hard |
| **OASIS** | Y | Y | P | Y | P (unverified) | N | N | Y | P (SQLite) | Medium |
| **Whistleblowing repo** | P (4 agents) | P | N | P (bans) | P | N | N | Y | Y | Easy, small |
| **Sticky Collusion** | N (2 agents) | N | N | P | Y | N | P | Y | Y | Parts only |

## Why Inspect over Terrarium

One survey proposed Terrarium as the base. Its board, compaction and `recall` tool fit our design, but the changes it needs are exactly the hard parts:

- Agents run one at a time (`examples/base_main.py`), so a 100-agent round is slow.
- No code exists to add or remove agents after start (`abstract_environment.py`).
- Tools are set per environment, not per agent, so every worker would see the investigator's report tool (`terrarium/tools/discovery.py`).
- No sandbox, so the exploit would have to be faked as a tool call instead of real code and tests.
- The logger rewrites whole JSON files on every call (`terrarium/core/logger.py`), which slows down sharply at 100 agents.

Inspect already provides what those fixes would build:

- Concurrent agent calls with adaptive rate limits: `collect()` and `max_connections` ([docs](https://inspect.aisi.org.uk/models-concurrency.html)).
- Compaction where "the core history with all messages is still retained" ([docs](https://inspect.aisi.org.uk/compaction.html)), so investigators can cite exact past messages.
- One shared Docker sandbox where each agent runs as its own Linux user: `sandbox().exec(..., user=...)`. That gives us per-agent write permissions.
- Any provider through `openai-api/<provider>/<model>`, OpenRouter or vLLM ([providers](https://inspect.aisi.org.uk/providers.html)).
- `inspect view`, `events_df`/`messages_df` and Scout scanners for logs, metrics and LLM review ([dataframe](https://inspect.aisi.org.uk/dataframe.html), [scanners](https://inspect.aisi.org.uk/scanners.html)).
- ImpossibleBench and ControlArena are both built on Inspect, so their parts plug in directly.

One catch: Inspect's `react()` agent reinserts its system prompt on every call, so we write our own small agent loop instead.

## What we write ourselves

1. **Round loop.** Each round: convert workers with probability k, replace removed agents, run all agent turns with `collect()`, then run the auditor on any new reports.
2. **Board and DM tools.** A shared store of messages, each with message, round and agent IDs. Every message is also logged as a transcript event.
3. **Agent loop.** Generate, run tools, compact, and keep each agent's raw message history. Investigators get a read-only tool over their own raw history.
4. **Role change.** Swap the system message and tool list, and log a hidden `role_change` event.
5. **Task.** Bundle about 10 ImpossibleBench "conflicting" LiveCodeBench problems into one repo, with one owner per function. Make `tests/` writable only by a few Linux users, so the exploit needs those users to join in. Skip the SWE-bench split, which needs a separate Docker image per problem.
6. **Auditor.** The ControlArena full-trajectory formatter plus the ImpossibleBench judge prompt, with no tools. Metrics come from the logs afterwards.

## What we borrow

| From | Files | Use |
|---|---|---|
| [ImpossibleBench](https://github.com/safety-research/impossiblebench) (MIT) | HF datasets `impossible_livecodebench` (103 problems per split); `livecodebench_scorers.py` (`test_py_was_modified`); `analysis/llm_judge.py` (5 cheat types) | The impossible task, cheat detection, judge prompt. Use the latest code: a bug once blocked test edits on the LCB split ([issue #3](https://github.com/safety-research/impossiblebench/issues/3)). |
| [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (MIT) | `monitor/_full_trajectory_prompt_formatter.py`, `monitor/_ensemble_monitor.py`, `analysis/_metrics.py`, `_tpr.py`, `_auc.py` | Auditor prompt formatting and detection metrics |
| [Colosseum](https://github.com/umass-ai-safety/colosseum) (MIT) | `experiments/collusion/judge_blackboards.py`, `metrics.py`, `_extra_fields` role injection in `run.py` | Board-level collusion judge, role injection pattern |
| [Report Tool fork](https://github.com/philiproeleveld/colosseum) (no license file; ask before copying code) | `experiments/collusion/wasp/jira_ticket_choice_env.py` (`report_to_organizers`), `score_reports.py` | Investigator report tool, scoring reports against the true conspiracy |
| [Sticky Collusion](https://github.com/JvThunder/sticky-collusion) (MIT) | `analysis/agreement_judge_prompts.md` | Judge that detects agreements and must quote them verbatim; fits offer and acceptance counts |
| [Whistleblowing](https://github.com/r1shabh007/Agent-Collusion-With-Whistleblowing) (MIT) | `tattletale/prompts/offer_v0.txt`, `rules_accuse_*.txt` | Offer and accusation prompt wording |
| [Wired Partners](https://github.com/astral-fate/wired-partners) (MIT) | `colosseum_arm/house_rules.py` | Rule-announcement wording for the informed arm |

## Findings that affect the design

- **Self-reports dominate in the closest prior study.** In the whistleblowing repo, 95 to 100% of accusations named the accuser's own channel partner. That supports metrics 8 and 9 and the "build a conspiracy to report it" risk.
- **Sticky Collusion is the closest existing impossible-task design.** Two agents check each other under a rule they cannot satisfy, and the reward favours accepting. Its `--wipe-agent-at-trigger` option replaces a seat with a fresh agent.
- **The board is the main cost driver.** If every agent reads the full board each call, input roughly doubles. Give agents a capped digest plus a search tool.

## Cost estimate (not measured)

100 agents × 20 rounds = 2,000 agent turns. At about 5 model calls per turn and 15k input tokens per call, one run is about 150M input and 3M output tokens.

| Assumed price (input / output per M tokens) | One run |
|---|---|
| $0.50 / $2 | ~$80 |
| $3 / $15 | ~$500 |

These are placeholder prices, not quotes for a chosen model. Prompt caching lowers the input share. Arms × seeds multiplies the total, which bears on swarm size versus number of runs.

## Rejected

- **GovSim:** 5-agent resource game, last pushed January 2025.
- **CRUX:** the one linked from the hackathon page is a single-agent eval project with no harness released.
- **AutoGen:** archived. **MetaGPT, ChatDev, AgentVerse:** stale or no longer a code framework.
- **AG2 Network:** group channels make agents take turns in a fixed order, and compaction replaces history.
- **OpenAI Agents SDK:** compaction only through OpenAI's Responses API; no agent-to-agent messaging.
- **LangGraph:** generic; we would build everything.
- **Peer-Preservation, FakeLab, Wired Partners:** single-agent, no public code, or one-shot games.

## Still unknown

- Whether `inspect view` stays usable for one sample with about 10k model calls.
- Whether OpenRouter tool calling works through every provider we pick.
- The real per-run cost once a model is chosen.
- AgentSociety was not inspected.

Cloned repos for reference (local, not committed): `/private/tmp/claude-501/-Users-baderasadi--t3-projects-agent-swarm-hackathon/0074d729-45d1-4a9d-b9cf-a443ad70cee7/scratchpad/repos/`.
