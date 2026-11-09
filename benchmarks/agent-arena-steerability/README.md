# Agent Arena Steerability results

Snapshot published **4 November 2026**, retrieved **8 November 2026**. All three models use maximum reasoning effort. [results.json](results.json) preserves the source values at full precision.

| Model | Gain over the average model, percentage points | 95% confidence interval | Scored sessions | Scored observations |
|---|---:|---|---:|---:|
| GPT-6.1 Terra | +15.18 | +13.80 to +16.57 | 13,928 | 118,771 |
| GPT-6.1 Sol | +13.29 | +12.19 to +14.39 | 19,075 | 96,131 |
| GPT-6 Luna | +4.19 | +3.62 to +4.77 | 137,601 | 1,200,732 |

## What the score measures

Steerability measures the correction an agent requires from its user during real tasks, including coding, research, and document creation. The current definition rewards turns requiring no correction and penalizes repeated corrections more heavily than corrections resolved immediately. This makes it a practical proxy for task adherence, rather than a direct check of every instruction.

Each score estimates the effect of using that model instead of Arena's average model. Higher is better. The values above are relative gains, not absolute compliance percentages. The source JSON stores scores as fractions; multiply the score and its interval bounds by 100 to obtain the percentage-point values above.

Terra has the highest estimate among these three, with an individual confidence interval that overlaps Sol's. Both intervals are well above Luna's. These intervals describe uncertainty around each estimate; their overlap alone does not establish a pairwise significance result.

Models are randomly assigned to real Arena sessions. The comparison reflects Arena's tools, workflow mix, and current model pool. Maximum reasoning is a shared setting label, not a guarantee of equal compute or cost. Session counts here are the sessions scored for steerability, not the overall leaderboard's session totals. Observations include multiple turns from a session.

## Sources and provenance

- [Official leaderboard](https://arena.ai/leaderboard/agent)
- [Current signal definitions](https://arena.ai/resources/agent-arena-signals)
- [Evaluation methodology](https://arena.ai/blog/agent-arena-methodology)
- [Score interpretation](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode)
- [Official dataset](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset), configuration `agent_steerability`, split `latest`, category `overall`.

The JSON contains the three selected source records, without modifying their field names or numeric values. The dataset uses [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); attribution is to Arena / `lmarena-ai`. This repository stores published results and did not run the benchmark. The `latest` source endpoint changes over time; use the saved JSON for this dated snapshot.

[Research notes](../../wiki/agent-swarm-hackathon/instruction-adherence-benchmark/Update-3.md) record the benchmark selection. [The chart](../../wiki/agent-swarm-hackathon/instruction-adherence-benchmark/steerability.html) shows the estimates and uncertainty ranges.
