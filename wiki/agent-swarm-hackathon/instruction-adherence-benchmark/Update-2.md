# Equivalent benchmark with published scores

Completed 8 November 2026. The user requested an equivalent benchmark after the Artificial Analysis publication gap.

Retell vCX has an instruction-following component with published results for all three current models:

| Model | Reasoning effort | Accuracy | Passed | Evaluated |
|---|---|---|---|---|
| GPT-6.1 Sol | low | 88.5% | 885 | 1,000 |
| GPT-6.1 Terra | none | 87.1% | 871 | 1,000 |
| GPT-6 Luna | none | 73.7% | 737 | 1,000 |

Verified the standard variants in the public HTML's embedded data. Each entry has `scores.instruction_following` fields for accuracy, pass, fail, and evaluated. These are instruction-following scores, not the site's average across instruction following, grounding, tool calling, and colloquial style. Each model has 1,000 evaluated instruction-following cases.

Retell tests difficult multi-turn conversations drawn from real production scenarios. The benchmark concerns voice agents and customer conversations. These results are useful evidence of instruction adherence in that setting, rather than a universal probability of complying with arbitrary coding tasks. Effort settings differ, so the results do not establish a comparison at equal reasoning effort. Retell runs the benchmark itself.

Sources:

- [Retell vCX benchmark and score data](https://bench.retellai.com/)
- [OpenAI's description of Retell's benchmark](https://openai.com/index/retell-ai/)

Scale MultiChallenge was also investigated. Its primary leaderboard reports Sol at 81.95 and Terra at 74.20, but has no Luna entry in its current public page data. Aggregators report Luna at 51.5 without establishing matching primary-source provenance, so that partial comparison was not used.

The accompanying [comparison](comparison.html) presents the verified Retell scores.
