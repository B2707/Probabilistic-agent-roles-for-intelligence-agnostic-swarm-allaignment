# Completed Sol comparison; Luna stopped by request

The user ended the experiment after the three Sol runs. All 744 planned Sol interim audits are complete. The remaining Luna work and automatic continuation are stopped. At the stop check, neither this thread's driver nor supervisor was running; no orphan Codex audit process was found by this task's unique schema path or call-directory ownership. No other ongoing run was stopped. A persistent `stop-requested.json` marker prevents this replay's `run` and `continue` commands from starting model calls.

The final comparison uses only the completed Sol A seed 3, B seed 3 and C seed 2 runs. The 159 completed Luna verdicts remain in the original raw journal and are excluded from Sol reports and costs. No saved experiment, original verdict, removal, replacement, role or downstream conversation was changed. No final audit was executed.

| Sol run | Original interim audits | Messages-only audits | Original flagged agents | Replay flagged agents | Original audit minutes, estimated | Replay batch minutes | Median successful call, seconds | Replay API-equivalent USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A seed 3 | 0 | 234 | 0 | 72 | 0.0 | 47.3 | 36.5 | 19.48 |
| B seed 3 | 102 | 300 | 14 | 14 | 16.0 | 18.7 | 28.4 | 15.22 |
| C seed 2 | 24 | 210 | 0 | 0 | 5.4 | 34.1 | 25.8 | 9.84 |

Sol A had no original interim auditing, so its 72 additional flags reflect added coverage. Sol B has equal distinct-agent counts but different identities: 10 agents were flagged by both methods, four only by the original and four only by the replay. On the 102 matched B agent/round cases, five verdicts disagree; the original flagged 14 cases and the replay 11. C agrees on all 24 matched cases, with no flags. Overall, 121 of 126 matched verdicts agree, 96.0%. Original auditor judgments are a comparison baseline, not verified ground truth.

Recorded Sol API-equivalent cost is $44.5421768, including $4.392332 from 53 returned attempts with 403 errors. There are 797 returned Sol attempts for 744 completed audits. Every returned Sol attempt has usage. The largest reported input count per attempt is 93,113 tokens, below the documented 272K long-context pricing threshold; cache-write counts are zero. Prices use requested priority/Fast Terra rates of $2/M uncached input, $0.10/M cached input and $10/M output. These are API-equivalent estimates for ChatGPT-login calls, not an invoice. One interrupted HTTP diagnostic on a Sol job has no captured usage and is explicitly excluded from measured cost. Partial Luna work already performed is also outside the Sol-only cost.

Original cost is unavailable because the harness did not retain auditor usage. Original interim time is estimated from event boundaries; new batch time is measured and includes retries and the initial pilot. These are different audit schedules and historical service conditions, so the results cannot isolate the effect of filtering. The reported 403 count concerns returned CLI attempts; any internal reconnecting within a successful CLI attempt is included in latency but not separately itemized.

The first new removal-eligible flag is in round 1 for both A and B. There are 225 later A audit observations and 279 later B observations whose histories could differ if the new findings caused removal. C has no such divergence. The per-audit CSV flags these later cases. All observations were retained, as requested.

Final files are `sol-report.html`, `sol-summary.json`, `sol-comparisons.csv`, `sol-attempts.csv` and `sol-verdicts.jsonl` in `work/messages-only-replay/`. Original six-run raw journals, manifest, prepared records and partial Luna data remain intact. Rebuild the Sol report without model calls using `tmp/messages-only-replay-venv/bin/python scripts/replay-message-audits.py summary --scope sol`.

Validation passed for the exact 744-job ID set, unique verdicts, record and prompt hashes, Terra/max/priority settings, all evidence quotations and conversion periods, token subset constraints, CSV row counts and stop guards. Desktop preview at 728px and mobile preview at 390px had no console errors. UI smoke checks passed for three-run charts, completed scope, zero-finding cases, agent selection, saved annotations, copy and fallback. No new model calls were made during finalization.
