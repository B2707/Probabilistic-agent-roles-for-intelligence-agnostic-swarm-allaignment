# PR review and merging in C100

Checked 8 November 2026 at published commit `6b7b6e3320bd95d082c3731e999274b3723ef1c1`.

C100 uses `swarm_wide = true` and `pr_approvals = 2`. Its worker prompt describes PRs as the route to the experiment's shared main. These are internal experiment PRs; merging them does not publish a GitHub PR or deploy a public service.

`swarm/tools.py`, `review_pr`, rejects self-review, accepts reviews across problem assignments in swarm-wide mode, and calls `_merge` immediately when two distinct agents have approved an open PR whose base files are still current. `swarm/repo.py`, `review`, deduplicates approvers. Updating a PR clears approvals. Both workers and investigators have the review tool, and an investigator's approval is not required.

The merge condition does not require an investigator sign-off or a separate integrity-auditor verdict. Tests run when a PR is opened or updated, and agents can inspect diffs and run tests, but passing tests and doing those review actions are not enforced as conditions for approval. `swarm/loop.py` processes report-triggered and random audits after the round's agent turns. Consequently a PR can merge during the turns before an audit removes its author or approvers. Removing an agent does not itself roll back already merged files in the audit-processing code.

The latest published seed-1 live snapshot, 00:47 EST, says C100 resumed and is running at round 5, with 25 merges, all cross-problem, one problem at a full pass, and three removals. The published summaries still do not identify the full-pass PR or its reviewers. The rules establish the approval route, but not those reviewers' reasoning or whether they knowingly approved cheating.

Sources: `configs/C100-6-luna.toml`; `prompts/worker_swarm.md`; `swarm/tools.py` lines 236–278; `swarm/repo.py` lines 193–231; `swarm/loop.py` lines 89–100 and 291–335; `results/live.md`.

## Approval evidence and run age

At 00:54 EST on 8 November, the remote head was `8069036b761bc517b6c1a6096b9acbf95427ba6d`. The Mac's live snapshot remained 00:47 EST, about seven minutes old. The current seed-1 run started at 23:00 EST on 7 November, about one hour and 54 minutes earlier. This is elapsed time and includes a machine restart and quota interruptions; it is not uninterrupted model runtime.

The full-pass score is for the experiment's main, and the enforced code-update route requires two approvals. This supports an inference that its PR received two approvals. Its actual `pr_reviewed` and `pr_merged` records are still unpublished, so reviewer identities and investigator status cannot yet be verified directly. Do not present the live score as if individual approval records had been inspected.
