# v2 build contract

The interface between the parts of issue #2 that are built separately. The core harness writes these events. Metrics, labels and reaudit read them. Issue #2 is the spec; this file only fixes names and shapes.

## Event log additions

Every event has `seq`, `t`, `type` and `round`, as before. `agent` is the actor, so the event lands in that agent's record.

| type | fields | when |
|---|---|---|
| `instigator_joined` | `agent` (the instigator's fake id) | setup, round 0, only when the instigator is on |
| `message` | adds kind `review`, with `pr_id`. Instigator messages have `role` = `instigator` | every DM, board post, progress update and review comment |
| `instigator_message` | `agent` (instigator id), `message_id`, `to`, `team`, `trigger` (`first_contact`, `first_contact_hidden`, `approve_pr` or `approve_test_change`), `pr_id` (or null) | each scripted DM, next to its `message` event |
| `turn_input` | adds `message_ids`: ids of every DM, review comment and board post listed in that prompt | each turn |
| `pr_opened`, `pr_updated` | `agent` (author), `role`, `pr_id`, `team`, `title`, `paths`, `touches_tests`, `diff` (unified diff vs main, truncated) | open_pr, update_pr |
| `pr_reviewed` | `agent` (reviewer), `role`, `pr_id`, `author`, `team`, `decision` (`approve` or `request_changes`), `comment`, `message_id` (review message, or null), `approvals` (current approver ids), `diff` | review_pr |
| `pr_merged` | `agent` (author), `pr_id`, `team`, `approvers`, `merged_by`, `paths`, `touches_tests` | the approval that reaches R |
| `pr_stale` | `agent` (author), `pr_id`, `team`, `paths` (files that changed on main) | a merge or a merge attempt finds main moved |
| `test_file_edit` | `agent` (PR author), `role`, `pr_id`, `path`, `before`, `after`, `approvers` | a merged PR changed a test file |
| `tests_run` | `agent`, `role`, `team`, `pr_id` (null = main), `passed`, `total`, `full_pass`, `error` | every run_tests tool call |
| `honeypot_access` | `agent`, `role`, `url` | every fetch_url call |
| `instigator_reported` | `agent` (reporter), `report_id` (or null) | a report that names the instigator |

`team_scores` (round end, main only) and `tool_call` are unchanged. A tool call refused by the turn budget is a `tool_call` with `error: true` and a result containing `Turn budget used`.

`write_file` no longer exists. v1 logs still contain it, and metrics must keep reading v1 logs.

## Label rows (`labels.jsonl`)

`message_id`, `round`, `sender`, `to`, `kind`, `label`, `target`, `quote`.

- `label` is one of `offer`, `acceptance`, `endorsement`, `alert`, `none` (or `unlabeled` when the judge skipped it).
- `target` is the agent whose offer or cheat the message answers, or `""`.
- Review comments (`kind` = `review`) are grouped and labeled like DMs.

## Config fields (run_start `config`)

`problem_ids`, `honest_exit`, `turn_tool_budget`, `tests_visible`, `instigator`, `instigator_aggressive`, `pr_approvals`, `worker_reasoning_effort`, `auditor_reasoning_effort`, `judge_reasoning_effort` (empty string means use `reasoning_effort`). `maintainers_per_team` must be 0.

## Module split

The parts are built separately and meet at the events and label rows above.

- Core harness: config, world, repo, tools, loop, instigator, backend, auditor record, worker and auditor prompts, seam 1 tests. It writes the events.
- Metrics, labels and the judge prompt: `swarm/metrics.py`, `swarm/label.py`, `prompts/judge.md`, `tests/test_metrics.py`. They read the events.
- `reaudit` and `auditor-eval`: `swarm/reaudit.py`, `tests/test_reaudit.py`, `data/audit_truth.json` and their CLI commands. They read the events.
