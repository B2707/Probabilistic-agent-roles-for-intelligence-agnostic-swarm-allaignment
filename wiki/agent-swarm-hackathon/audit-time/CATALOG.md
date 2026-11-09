# Audit timing handoff

Complete. See [Update-1.md](Update-1.md) for results, method, limitations and checks.

Reproduce the measurement with `python3 scripts/measure-audit-time.py 5105e7843f60e64b3d2ad7af697754fb15ed1ffc`. The script writes `work/audit-time/evidence.json` and `run-times.csv`. The corresponding annotatable comparison is `work/audit-time/audit-time.html`.

End-of-round audits take 10.5–37.0% of recorded active time in primary B100 runs and 3.7–9.8% in C100; A100 has none. Keep final audits separate. Two Sol seed-1 runs have unmarked interruption gaps and should remain qualified estimates. Three original interrupted Luna seed-1 extras are excluded from pooled summaries.

No experiment, production process, model call, public write or PR was started. No harness code was changed. Other existing workspace changes were left in place.
