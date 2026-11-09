# Token usage handoff

Completed recorded-usage comparison for one agent for one round, split by GPT-6.1 Sol and GPT-6 Luna. Use nine completed primary A/B/C runs at seeds 1/2/3 per model, all at high worker reasoning effort. Publication snapshot: `5105e7843f60e64b3d2ad7af697754fb15ed1ffc`. The current task did not alter experiment code, model usage collection, paper or published results.

Results per 18,000 agent-rounds per model: Sol averages 420,590.70 input and 831.28 output tokens, total 421,421.98. Luna averages 267,778.40 input and 835.02 output tokens, total 268,613.42. Cache is included in input and reasoning is included in output. Most input is cached. Sol's recorded total is about 1.57 times Luna's, mainly because of input processing.

Reproduce with `python3 scripts/analyze-token-usage.py 5105e7843f60e64b3d2ad7af697754fb15ed1ffc`. The script subtracts successive cumulative session snapshots and verifies the totals by telescoping to each final session counter. Do not use the naive sum of published cumulative records. Include workers, investigators, nudges and captured retry work. Exclude disturbed original seed-1 extras, archived/partial runs and separate auditor/judge calls.

Limit: these are recorded averages, not exact costs. Sol has 71 sessions with unrecorded final usage, while all of Luna's empty records have later snapshots. Both can omit discarded retry work. Do not convert to precise dollar costs without recovering full session usage and separate audit/judge usage.

Evidence and per-run register are `work/token-usage/evidence.json` and `work/token-usage/runs.csv`. Annotatable comparison: `work/token-usage/tokens-per-agent-round.html`. Implementation smoke and dataset checks pass. Visual QA passed at 728px and 390px with no console messages; annotation validation, saved state, copy and fallback checks passed.
