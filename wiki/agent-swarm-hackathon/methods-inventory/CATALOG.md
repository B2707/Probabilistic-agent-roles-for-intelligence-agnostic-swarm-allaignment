# Methods manuscript handoff

Read [Update-3.md](Update-3.md) for the theory graph placement and [Update-2.md](Update-2.md) for the LaTeX draft, table sources and checks. [Update-1.md](Update-1.md) preserves the earlier inventory snapshot.

The current deliverable is `paper/main.tex`, with three Methods subsections and the current 100-agent A–F Results table, compiled to `output/pdf/main.pdf`. Text outside Methods and Results was preserved. The author will review the draft through source-line comments.

Results are pinned to `swarm-harness` commit `0f081a6309e5f31a7b6a9631c353e4b1f91e9b86`, 8 November 2026 at 18:05:13 EST. `paper/methods-results-snapshot.json` records the 22 included completed runs and exact aggregates. A/B/C have three seeds per model. D/E/F show actual available coverage, with Sol D/E marked Pending. Older 20-agent ablations and disturbed original Luna seed-one runs are excluded.

The theory subsection contains the expected role-round ratio and binary payoff equations. Its allocation curve is `paper/figures/investigator-worker-ratio.png`. Figure 2 now embeds `paper/figures/sender-game.png`, the referenced two-agent sender/receiver game, with its conditional assumptions and b/H definitions. Larger-coalition sender/receiver games for sizes 3, 5, 10 and 30 are not supplied by that figure. Existing theory files and figure assets are unchanged. Do not substitute the already-formed-conspiracy chart for a sender/receiver game.

Preserve the distinction between broader misconduct totals, distinct full-pass authors, positive during-run catches and actual removals. Included final reviews are Opus xhigh; enforcement is Terra max. Per-run post-run-label metadata is still absent from the published records and is flagged in a source comment. Compilation, source-scope checks, run inclusion checks, allocation checks and visual inspection passed. No experiment state or public content was changed.
