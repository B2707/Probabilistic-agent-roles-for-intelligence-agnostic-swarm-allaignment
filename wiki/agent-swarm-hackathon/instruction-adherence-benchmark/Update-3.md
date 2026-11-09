# Broader comparison using Agent Arena Steerability

Completed 8 November 2026. The user accepted the Retell comparison and requested a better benchmark.

Agent Arena's Steerability signal is a better practical fit for broad agent-task adherence. Its real workflows include coding, debugging, research, document creation, and data analysis. The current definition scores every judged assistant turn by the amount of user correction it requires. Getting the task right without a correction helps. A resolved correction incurs less penalty than a correction that must be repeated. This is a proxy for how much a user must intervene, rather than a direct audit of every instruction.

Verified the official `lmarena-ai/leaderboard-dataset` dataset, `agent_steerability` configuration, `latest` split. All three entries below use maximum reasoning and have publication date 4 November 2026.

| Model | Gain over baseline, percentage points | 95% interval | Scored sessions | Scored observations |
|---|---|---|---|---|
| GPT-6.1 Terra | +15.1824 | +13.7996 to +16.5653 | 13,928 | 118,771 |
| GPT-6.1 Sol | +13.2892 | +12.1901 to +14.3882 | 19,075 | 96,131 |
| GPT-6 Luna | +4.1943 | +3.6211 to +4.7674 | 137,601 | 1,200,732 |

The scores are percentage-point treatment effects against Arena's average-model baseline. They are not the percentage of tasks in which the model follows instructions. Models are randomly assigned to real sessions; Arena estimates the effect of substituting a particular model. Scores are relative to the current model pool and can change as that pool changes. The same reasoning label also does not imply the same cost or compute budget.

Terra has a slightly higher point estimate than Sol, with overlapping individual confidence intervals. Both have intervals far above Luna's. Avoid making an unsupported pairwise significance claim from overlapping individual intervals alone.

The per-signal scored-session counts differ from the overall leaderboard's total sessions. Use the counts above when describing the evidence for steerability.

Sources:

- [Current leaderboard](https://arena.ai/leaderboard/agent)
- [Current signal definitions](https://arena.ai/resources/agent-arena-signals)
- [Methodology](https://arena.ai/blog/agent-arena-methodology)
- [Score interpretation](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode)
- [Official dataset](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset)

Further research found a source for the previously unverified Luna MultiChallenge score of 51.49. BenchmarkList links it to [Inception's Mercury 3 launch](https://www.inceptionlabs.ai/blog/introducing-mercury-3). This is a different evaluator from Scale's direct Sol and Terra entries. Do not combine those into an equal-setting, single-evaluator comparison. Octavus AAB has useful Sol and Luna instruction-following results but no current Terra result. LiveBench 1.0 likewise lacks a verified Terra instruction-following result. Arena's Alignment Index is directly relevant to unauthorized scope expansion but its current October 16 data predates Terra and has no Terra entry.

The [steerability chart](steerability.html) presents the complete comparison. Retell remains a useful secondary check for voice-agent conversations.
