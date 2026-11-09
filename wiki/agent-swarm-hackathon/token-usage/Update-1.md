# Recorded tokens per agent-round

Analyzed publication `5105e7843f60e64b3d2ad7af697754fb15ed1ffc`, dated November 8, 2026 at 16:22 EST. No experiment, model call, production file, published result or manuscript was changed.

Selected nine completed primary A/B/C runs for each of GPT-6.1 Sol and GPT-6 Luna, seeds 1, 2 and 3. Each model contributes 18,000 agent-rounds, with workers and investigators included. Both use high worker reasoning effort. Excluded the publisher's three disturbed original Luna seed-1 extras, archived runs, partial runs, scripted contractor and separate auditor/judge calls.

The `model_usage` fields are cumulative session counters. Subtracted successive snapshots within each agent/session and summed the increments. Every field was monotonic in all selected sessions. A separate check verified that the increments telescope to the sum of the final counters per session. Divided by all completed agent-rounds, including rounds without a usage snapshot. A later snapshot can cover work from a missing earlier record.

| Mean tokens per agent-round | GPT-6.1 Sol | GPT-6 Luna |
| --- | ---: | ---: |
| Input | 420,590.70 | 267,778.40 |
| Cached input, included in input | 408,845.75 | 259,112.88 |
| Uncached input | 11,744.95 | 8,665.52 |
| Output | 831.28 | 835.02 |
| Reasoning, included in output | 275.29 | 441.87 |
| Input plus output | 421,421.98 | 268,613.42 |

Sol has 576 empty usage records among 18,310 backend invocations; 71 known sessions end with missing usage after their final snapshot. Of those, 69 are in B seed 1, one timeout is in B seed 2 and one Bad Request is in B seed 2. Luna has 59 empty usage records among 18,019 invocations, all with a later same-session snapshot. Backend retry code can discard preceding attempts' usage, so these are recorded averages rather than exact billed costs. Retries, timeout work after the last snapshot and separate auditor/judge calls can add unknown usage. Cached input and reasoning must not be added to their parent totals a second time.

Reproduce with `python3 scripts/analyze-token-usage.py 5105e7843f60e64b3d2ad7af697754fb15ed1ffc`. The script uses only the standard library and Git objects. Its smoke check covers cumulative subtraction, a missing intermediate snapshot, session replacement and denominator counting. Assertions verify all 18 complete runs, three seeds per arm, 2,000 distinct agent-rounds per run, model identity, monotonic counters and subset constraints. The comparison includes local feedback annotations.

Artifacts: `work/token-usage/evidence.json`, `work/token-usage/runs.csv`, and `work/token-usage/tokens-per-agent-round.html`.

Visual QA passed at 728px with sections collapsed and at 390px with the full method and annotation form expanded. Both previews had no console messages. A Node smoke check verified empty-note validation, saved feedback, clipboard copying and the clipboard-unavailable fallback. An HTML diagnostic verified unique IDs, chart segment proportions and displayed totals against the evidence.
