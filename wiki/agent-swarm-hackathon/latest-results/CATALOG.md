# Latest results handoff

Completed. Final source is `0f081a6309e5f31a7b6a9631c353e4b1f91e9b86`, published 8 November 2026 at 18:05:13 EST. See [Update-1.md](Update-1.md) for findings, limits, and verification.

The requested agent-count view is complete in [cheaters.html](../../../work/latest-results/cheaters.html), with [per-run CSV](../../../work/latest-results/cheater-counts.csv). See [Update-2.md](Update-2.md) for definitions and verified totals. The main table uses all misconduct, and a separate table uses only code authors. Caught agents who were not removed had investigator immunity. Rebuild with `python3 work/latest-results/build-cheater-report.py`.

Open [the commentable report](../../../work/latest-results/report.html), [the 72-directory inventory](../../../work/latest-results/run-inventory.csv), or [the summary](../../../work/latest-results/summary.json). The inventory includes 25 completed current runs, including all 18 primary A/B/C runs and four new D/E/F seed-1 results. Final exploited-problem counts in the new runs are D Luna 1/55, E Luna 1/55, F Luna 54/55, F Sol 53/55. New conditions have one seed each.

Reproduce without model calls:

```sh
python3 scripts/aggregate-results.py 0f081a6309e5f31a7b6a9631c353e4b1f91e9b86
python3 work/latest-results/build-report.py
```

The existing `paper/results-runs.csv` has a Luna-specific `primary` flag. Use the new inventory's `comparison_set` column for the 18 primary runs across both models. Committed live-status tables are stale. Acceptance metrics remain provisional because PR-level full-pass attribution can survive code changes. Final zero does not imply no earlier exploitation.
