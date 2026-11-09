# Messages-only audit feasibility

Checked the published source at `5105e7843f60e64b3d2ad7af697754fb15ed1ffc`. No audit was executed and no experiment code, configuration or result was changed.

The auditor currently receives a record built by `trajectory` in `swarm/auditor.py`. It includes input prompts, visible agent replies, tool arguments/results, PR diffs and review/merge activity, and authored messages. Worker reasoning is already excluded by the parser and record builder. Auditor-generated reasoning is separate from the evidence being audited.

A narrower audit can retain visible `agent_message` text and authored `message` text with IDs, rounds, recipients and role-change boundaries. `ToolBox.post_message` records DMs, board/progress posts and nonempty review comments as `message` events, so their text can be retained while removing raw `tool_call` records. Strictly removing all content transported through tools would also remove these communications. Prompts, tool results, code diffs and action records can be omitted.

This changes the evidence available for judging misconduct. The audit can assess offers, agreements and admissions in messages, but cannot reliably establish silent code cheating or whether an approved PR actually cheated without code/action evidence. An offline comparison is possible using saved events; it should not silently replace historical verdicts.

The retained worker output is input to the auditor. Filtering reduces the auditor's input, not the generation charges already incurred by the workers. The auditor still generates its own answer and, when applicable, reasoning.

Verification traced `trajectory`, `CodexAuditor.audit`, the auditor prompt, the event-log agent index, `ToolBox.review_pr` and `ToolBox.post_message` at the pinned source. No runtime change required a smoke test.
