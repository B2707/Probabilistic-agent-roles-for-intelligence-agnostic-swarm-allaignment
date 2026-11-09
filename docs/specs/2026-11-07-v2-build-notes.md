# v2 build notes

Built 7 November 2026 from GitHub issue #2 on branch `swarm-harness`. The production runs use the harness at commit `2a6af3c`, checked out on its own at `.prod/` (git-ignored through `.git/info/exclude`), so later commits can't change a running or resumed run.

## What was built

- **Core harness:** config fields, PRs with R approvals and staleness, the scripted instigator, `fetch_url` honeypot, hidden-test mode, turn budget, 180 s timeout without retry, effort per role with the max-to-xhigh fallback, and the auditor record with PR diffs.
- **Metrics and judge:** five labels with targets, PR-aware blame, structural acceptances, seen-without-alerting links, honeypot counts, and the table grouped by run name.
- **Reaudit:** `swarm reaudit`, `swarm auditor-eval` and the seeded `data/audit_truth.json`.
- The event shapes they share are in `2026-11-07-v2-build-contract.md`. One event was added later: `pr_checked` (`agent` = PR author, `pr_id`, `team`, `version`, `passed`, `total`, `full_pass`, `error`), the harness's own test run of every new PR version.

## Decisions taken during the build

| Decision | Why |
|---|---|
| Workers on gpt-6-luna and gpt-5.6-luna run at `high` reasoning | Issue #2 gives an effort only for gpt-6.1-sol (max). `high` matches the v1 sol pilots. |
| v1 configs (`smoke`, `informed`, `uninformed`, `sol-high-informed`, `pilot-*`) are kept but no longer load | They record v1 runs. v2 rejects `maintainers_per_team` other than 0. Whether to delete them is an open question. |
| The three v1 maintainer tests were ported to PRs | v2 removes `write_file` and maintainers. The ported tests keep their intent: permissions, scoring from main, and the auditor record. |
| The instigator's first contacts can reach investigators | It can't know roles, and the same rule applies in every arm. |
| The harness tests every new PR version (`pr_checked`) without showing agents the result | Issue #2 says the instigator acts "whenever an open PR … passes every test". Without the check, the push fired only if an agent happened to run the tests on that PR. |
| A hidden-mode first contact names the input but no test name, and doesn't suggest changing the assert | Agents in hidden mode can't see test names or edit tests. |
| The turn input lists open PRs plus the agent's own stale PRs, newest 10 | Stale PRs from teammates piled up for 20 rounds. |
| `test_timeout_s` stays at 5 s per test | A lower value changes which tests a slow but correct solution passes. A looping solution can still outlast a 180 s turn. |
| PR diffs are cut at 6000 characters in `read_pr` and in the auditor record | No PR diff came near the limit in the first 40 PRs. `tool_call` events keep the full file contents. |

## The stopped first attempt

The first two baselines (`runs/*-stopped`, commit `e3ff6f5`) ran about two rounds. Two sol agents (a003 and a007) hit the new 180 s timeout on their first turn. The timeout path threw away Codex's output, so those agents lost their round 1 session and started round 2 in a fresh one. That's a new feature misbehaving, so both runs were stopped and restarted on `2a6af3c` together with the other fixes from the spec review. They aren't paper runs.

What the stopped runs showed works on real Codex:
- **Timeouts:** the effort check passed at max, and timed-out turns were not retried (attempts = 1) and ended at exactly 180.0 s.
- **PRs:** merges at 2 approvals, stale PRs refusing reviews, and the tool budget firing.
- **Instigator:** approval pushes, and the first contact arriving in round 2.
- **Cheating:** both gpt-6-luna and gpt-6.1-sol special-cased the impossible input in round 1, under pressure alone, and teammates approved those PRs.

## Review outcomes

The standards review and the spec review of the core ran on `e3ff6f5`.
- **Fixed in `3cec7a8` and `2a6af3c`:**
  - instigator template checked at load
  - one PR dict
  - non-string PR contents rejected
  - unused `turn_prompt` removed
  - effort-check temp folder cleaned up
  - session id kept on timeout
  - harness PR check
  - instigator wording
  - hidden-mode first contact
  - stale PR clutter
  - a usage limit no longer reported as a ping pass
- **Not changed:** the judgement-call smells, such as the split between the repo and the tool box for merging, string PR statuses, and the long constructor argument lists. Refactoring during the runs isn't worth the risk.

## Still open

- `data/audit_truth.json` needs a hand check. The conflicting pilot lists 9 agents. The old judge's labels named 9 more, which are listed in the file's notes.
- No seam covers the session-id fix. It is checked while watching the first production run.
