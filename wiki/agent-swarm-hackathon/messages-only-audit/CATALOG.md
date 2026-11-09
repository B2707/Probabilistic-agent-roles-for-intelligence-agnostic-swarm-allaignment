# Messages-only audit handoff

Feasibility answered; not implemented or run. Source snapshot: `5105e7843f60e64b3d2ad7af697754fb15ed1ffc`.

Worker reasoning is already excluded from existing audits. A messages-only record can retain `agent_message` and `message` text plus provenance and role-change boundaries, removing turn prompts, raw calls/results, PR diffs and action events. Messaging-tool payloads must remain if DMs, board posts, progress updates and review comments are wanted; those are separately logged as `message` events.

Main tradeoff: communication can establish offers, agreements and admissions, but missing code/action context can prevent verification of implemented cheating and knowingly approving it. Existing auditor rules expect the complete record, so any actual experiment should explicitly define the narrower evidence scope and handle insufficient evidence. Do not overwrite historical verdicts as part of a comparison.

Worker output becomes auditor input. Filtering saves auditor input processing, while auditor answer/reasoning and prior worker generation remain separate costs. No model calls, experiment changes or result mutations were performed.
