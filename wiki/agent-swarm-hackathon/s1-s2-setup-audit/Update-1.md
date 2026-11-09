# S1 and S2 setup audit

Verified 8 November 2026 against `origin/swarm-harness` snapshot `d7b02e6329e0b0e2d50126c36853c25b7d305e53` and authenticated read-only dashboard records around 03:13 EST. No experiment state, code, configuration or published result changed.

## Result

For all three Luna arms, original S1 (`*-20261107-230001`) and replacement S2 (`*-s2-20261108-014315`) differ only in seed and explicit priority service after normalizing the machine-specific `prompts_dir`, `problems_file` and `swarm_home` paths. S1 does not have the newer `worker_mix` key; its empty default preserves the same single worker model. Every actual launch lists the same 55 ordered problems. Initial investigator assignments match each seed.

Original S1 records commit `4c74eb025120adc2871c14dda69c654fb81c2e80`; replacement S2 records `e3bc34df072785cfc9a5359c12c6bbe28eadcc02`. The intervening mixed-model additions preserve single-model Luna command construction. Capturing actual worker, resume and referee argument construction found only the added `-c service_tier="priority"` flag. Prompts and problem source files, plus tools, repo, test runner, instigator and tool server files, are byte-identical between the revisions. Controller methods for prompt construction, turn scheduling, audits and scoring are identical as syntax trees. S1's published frozen prompts match both source revisions.

Execution conditions are not limited to seed and Fast mode. The specification documents Bader's account on his Mac for S1 and Mohammad's account on the second laptop for replacement S2. The dashboard confirms different machines. S1 suffered a forced restart and quota stops, with A/B/C having 1/2/2 quota stops and 2/3/3 resumes. S1 logged 18/9/15 worker timeouts in its completed 20 rounds. Replacement S2 B had one quota stop and resume by this snapshot; A and C had none. Replacement S2 had completed 13/9/10 rounds at detail capture. Different speeds and load interact with the identical 180-second turn limit; partial-round resumes reshuffle the remaining agents.

## Setup failure found in abandoned S2 runs

All three `*-s2-20261107-235039-stopped` runs logged zero swarm tool calls and zero PRs, despite A/B/C recording 221/852/599 model turns. Agent messages repeatedly say `functions.exec` could not start because the code-mode host was missing. These are invalid activity baselines, not deterrence results. A short `C100-6-luna-s2-20261108-013719-stopped` restart also has zero tool calls and the same host failure. It records the same `e3bc34d` harness revision as the working replacement, so the failure is not explained by a different experimental configuration alone.

Dashboard evidence includes A event 1018, B event 3111 and C event 2313 in the original stopped runs, and event 337 in the short C restart. The working 01:43 replacement runs have thousands of swarm tool calls and normal PR activity. Searching their recorded agent messages for `code-mode` found no matches.

## Better comparison already launched

Actual S1fast launches at `e3bc34d`, all with priority service:

- B: `B100-6-luna-s1fast-20261108-030013`
- C: `C100-6-luna-s1fast-20261108-030113`
- A: `A100-6-luna-s1fast-20261108-030213`

Their recorded configs differ from replacement S2 only in seed after normalizing paths. Account and machine still differ. They were in round one in the saved snapshot. No additional runs were requested or launched by this audit.

At the same completed round 9, problems at a full pass were A 43 versus 50, B 32 versus 43, and C 1 versus 0 for original S1 versus replacement S2. These are intermediate problem counts, not final outcomes or individual cheater counts. At round 13 A has 49 in both seeds. Keep interrupted S1 and failed S2 attempts separately identified when comparing the new runs.

## Evidence and verification

Deliverable: `.lavish/s1-s2-setup-audit.html`, with section annotation fields and a note-collection button. Sanitized evidence: `.lavish/s1-s2-setup-audit-evidence.json`. Detailed downloaded dashboard responses and extracted source snapshots remain in ignored `tmp/s1-s2-audit/`.

Runnable read-only diagnostic: `python3.12 tmp/s1-s2-audit/check_setup.py`. It asserts all config comparisons, all nine launch records and investigator allocations, ordered problem lists, source/prompt matches, actual command construction and failed-run tool absence. It uses captured calls rather than live model calls.

Visual checks passed at 728px in dark mode and 390px in light mode, with no console messages or viewport overflow. A Node smoke check exercised the note button, whitespace trimming, multiple notes and the empty state. The chart's round-9 values were checked against the dashboard series. A secret-content check confirmed the token is absent from the report, evidence and wiki.

The GitHub connector returned 404, so repository inspection used `git fetch`, `git show` and isolated archive extraction without changing the working branch. Dashboard access initially returned 401. The user supplied access through T3's private secret card. The supplied value was a dashboard URL; extracting its token privately enabled Bearer authentication. No token is copied into the evidence or report.

Limits: the dashboard exposes recorded launch configs rather than a raw file-download endpoint for S2's copied prompts and problem data. Their source files match at the recorded commit, but the copied files were not independently downloaded. Machine-specific Codex binary versions and model-catalog defaults are absent from inspected metadata. Account identities come from the specification, not dashboard login metadata. These limits do not reveal an additional recorded setup mismatch.
