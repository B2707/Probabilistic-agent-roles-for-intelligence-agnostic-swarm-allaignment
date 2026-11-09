# Completed C100 seed-one removal investigation

Checked 8 November 2026 at source commit `89c1910135fa812da1855dc8a02f64efec198931` on `origin/swarm-harness`.

The user reports that C100 seed one finished with two cheaters, both removed. The published `results/live.md`, generated at 02:17 EST, confirms run `C100-6-luna-20261107-230001` completed round 20. It records 60 reports and three total removals. Three total removals does not identify which two agents the dashboard counts as cheaters or establish why any removal occurred.

The current run's raw events, config, world state, labels and metrics are absent from the published branch. `results/metrics.md` still has only its header. The older stopped C100 run and archived 20-agent runs cannot answer this question.

The dashboard provides the necessary read-only endpoints: `/api/run/<run>`, `/api/run/<run>/feed`, `/api/run/<run>/agent/<agent>` and `/api/run/<run>/event/<seq>`. Its documented public host is `https://baders-macbook-pro.tail9fc878.ts.net/`. An unauthenticated request to `/api/health` returned HTTP 401. The GitHub connector also returned 404 for accessible repository files, so source inspection used `git fetch` and `git show`. No linked-environment tool was callable. Local Tailscale is stopped and belongs to a different tailnet from the run host.

A private dashboard-token request timed out. Attribution remains unverified. Do not claim an investigator, collusion target, self-report or random audit caused either cheater's removal.

To finish once access is available, identify the two cheaters from the dashboard, retrieve their removal and audit events, follow each audit's triggers to report records, and determine each reporter's role at the report time. Inspect prior messages to distinguish a collusion target from an unrelated worker. Preserve the distinction between the immediate removal trigger and other reports about the same agent. Do not modify the running experiment or publish results merely to obtain these records.
