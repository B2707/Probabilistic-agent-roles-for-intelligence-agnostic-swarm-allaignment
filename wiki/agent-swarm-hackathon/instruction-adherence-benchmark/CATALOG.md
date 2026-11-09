# Instruction adherence benchmark handoff

Completed 8 November 2026. See [Update 1](Update-1.md) for the Artificial Analysis lookup, [Update 2](Update-2.md) for Retell, and [Update 3](Update-3.md) for the broader recommendation.

The reusable repo results are in [benchmarks/agent-arena-steerability](../../../benchmarks/agent-arena-steerability/README.md), with full-precision source records in `results.json`. [Update 4](Update-4.md) records the save and verification. The root README links to these results.

The strongest complete practical comparison found is Agent Arena Steerability. On the November 4, 2026 official leaderboard, all at maximum reasoning, Terra gains 15.18 percentage points over the average-model baseline, Sol 13.29, and Luna 4.19. The respective 95% intervals are 13.80 to 16.57, 12.19 to 14.39, and 3.62 to 4.77. These are relative effects on a steering-effort signal, not absolute compliance rates. The current method rewards needing no corrections and penalizes repeated corrections. [Chart](steerability.html).

Get current values from the official `lmarena-ai/leaderboard-dataset`, configuration `agent_steerability`, split `latest`. The model identifiers are `GPT-6.1 Terra (Max)`, `GPT-6.1 Sol (Max)`, and `GPT-6 Luna (Max)`. Current signal definitions take priority over older help text that describes only success after a correction.

The delivered comparison uses [Retell vCX](https://bench.retellai.com/), specifically its instruction-following component. GPT-6.1 Sol with low reasoning scores 88.5%, GPT-6.1 Terra with no reasoning scores 87.1%, and GPT-6 Luna with no reasoning scores 73.7%. The underlying public data reports 885, 871, and 737 passes out of 1,000 evaluated cases respectively. [The comparison](comparison.html) shows these values.

Retell tests multi-turn customer conversations drawn from production. These are benchmark-specific rates from Retell's own evaluation, and the models use different effort settings. Do not interpret them as universal compliance probabilities or maximum-effort model comparisons.

IFBench measures precise single-turn instruction following. AA-Omniscience measures factual knowledge and hallucination.

Artificial Analysis has no published IFBench result in its current page data for GPT-6 Luna, GPT-6.1 Sol, or GPT-6.1 Terra. All 17 effort variants have a null score. Do not substitute the overall Intelligence Index, infer percentages from other benchmarks, or treat a null score as zero.

If revisiting, inspect `evaluationScores.ifbench` on each public release page. Individual model pages expose `ifbench` directly. The default IFBench chart omits many models, so inspect the release data before concluding that a result is unavailable.
