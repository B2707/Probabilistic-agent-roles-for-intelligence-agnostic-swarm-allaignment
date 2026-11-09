# S1 and S2 setup audit handoff

Complete. Read [Update-1.md](Update-1.md) for evidence and verification. Repository snapshot is `d7b02e6329e0b0e2d50126c36853c25b7d305e53`; authenticated dashboard records were captured around 03:13 EST on 8 November 2026.

Across A/B/C, actual original S1 versus replacement S2 launch configs differ only in seed and explicit priority service after normalizing machine paths and the new empty `worker_mix` default. Original S1 uses `4c74eb0`; replacement S2 and new S1fast use `e3bc34d`. Source prompts/data and core experimental logic match; captured Luna/referee commands differ only by the priority flag. All nine ordered problem lists and initial investigator allocations were verified.

Do not call execution conditions identical. Accounts and machines differ, original S1 suffered a forced restart and quota interruptions, and S2 B also stopped and resumed once by this snapshot. Original S1 completed 20 rounds; replacement S2 had completed A/B/C 13/9/10. Same turn timeouts do not imply equal work when execution speed differs.

The abandoned S2 `20261107-235039-stopped` runs are invalid comparisons. All three had zero swarm tool calls despite hundreds of model turns, and agents reported a missing code-mode host. A short 01:37 restart also failed. The working replacement is `*-s2-20261108-014315`, with thousands of tool calls and normal PR activity. The audit did not repair or change any run.

S1fast runs `B...030013`, `C...030113`, `A...030213` already launched before this audit. Their actual configs and commits match replacement S2 except seed and machine paths. Use them for the closer comparison, while keeping interrupted S1 and failed S2 distinct. They were still in their first round in the snapshot.

Deliverables: `.lavish/s1-s2-setup-audit.html`, an annotated report shown through T3 HTML rendering; `.lavish/s1-s2-setup-audit-evidence.json`, sanitized evidence. Reproducible diagnostics and full fetched responses are in ignored `tmp/s1-s2-audit/`; run `python3.12 tmp/s1-s2-audit/check_setup.py`. Layout, annotation logic, chart values and secret exclusion passed verification.

No unresolved access blocker remains. Limits remain for S2's copied prompt/data bytes and machine-specific Codex versions/default model catalog, which the inspected dashboard metadata does not expose. Account identity is documented in the specification, while machine identity is confirmed by the dashboard. Never copy the token or its private file into future artifacts.
