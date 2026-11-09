# Replay progress, retries and process ownership

The user instructed that no ongoing run outside this thread may be shut down. The only process explicitly stopped was this thread's own initial replay driver, PID 66552. Before signalling it, the diagnostic verified the exact replay command and confirmed zero child requests in flight. No other process was signalled. All completed verdicts and every returned attempt's usage remain in the replay journal.

A one-call HTTP transport diagnostic was launched after 41 completed verdicts. A turn interruption ended it before a result or usage was captured. This is recorded as one unmeasured diagnostic call. It is not a completed audit and is not substituted for any planned verdict. No HTTP transport change is retained.

The user then explicitly accepted continued progress through 403 responses and requested programmatic accounting. The replay resumed with the original default transport, Terra/max/priority and concurrency 25. At the first subsequent progress check, 52 of 1,758 audits had completed, reaching Sol A seed 3 round 5. There were 29 failed attempts among 81 returned attempts at that check. These are preliminary counts.

Continuation now runs in its own process session and uses a file lock to prevent a second supervisor. Supervisor PID 71995 waits for this thread's current driver PID 71705 to exit before resuming missing audits. It never signals processes. The launch and execution journals save ownership and process IDs. Once resumed, the supervisor retries only missing pairs with backoff; a true account quota stops it with saved progress rather than selecting another model.

Raw `attempts.jsonl` preserves every returned attempt's usage, duration and error. `backoffs.jsonl` records waits for subsequent invocations. `attempts.csv` categorizes 403s and exposes usage fields for programmatic analysis. Reported cost includes failed attempts with usage; the single interrupted diagnostic is explicitly unmeasured. Timings include returned retry work and measured batch waits. No model, effort or tier has been changed, and no production run or original event log is modified.

The report's chart rendering passed desktop preview with no console errors. A Node smoke check passed for both six-run charts, run/agent finding selection, saved annotations, clipboard copying and its fallback. The supervisor's single-instance lock was exercised by a second invocation, which exited without starting model calls.
