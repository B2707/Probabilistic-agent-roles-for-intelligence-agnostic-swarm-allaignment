# Audit wall-time measurement

Completed 8 November 2026. Analyzed publication snapshot `5105e7843f60e64b3d2ad7af697754fb15ed1ffc` without running experiments or changing the harness.

## Findings

The 18 primary completed runs comprise A100, B100 and C100, Luna and Sol, with seeds 1, 2 and 3. The three original interrupted Luna seed-1 extras are preserved in the evidence but excluded from pooled comparisons.

| Worker model | Arm | Pooled end-of-round share | Individual-run range | Pooled final-audit share |
|---|---|---:|---:|---:|
| Luna | A100 | 0.0% | 0.0% | 4.9% |
| Luna | B100 | 28.4% | 21.8–37.0% | 4.4% |
| Luna | C100 | 6.6% | 4.6–9.8% | 4.9% |
| Sol | A100 | 0.0% | 0.0% | 5.0% |
| Sol | B100 | 15.4% | 10.5–18.4% | 3.4% |
| Sol | C100 | 4.6% | 3.7–5.6% | 7.0% |

Pooled percentages divide summed audit seconds by summed recorded active seconds. The denominator includes final audits. Example: C100 Luna seed 2 spends 8.73 minutes in round audits out of 145.68 active minutes, or 5.99%. Its final audit adds 5.70 minutes, or 3.91%.

## Measurement and limitations

`swarm/loop.py` awaits all concurrent worker turns before running audits. `process_audits` awaits the complete concurrent audit batch before emitting its verdict events. Therefore the gap from the previous event to the first batch verdict approximates elapsed audit time. Subsequent verdict processing is included. Audit-phase usage-limit failures count as audit time too. Audits are not measured by summing individual agent call durations.

Final auditing starts after the last `round_end`, runs concurrently, and ends with the completed `run_end`. Stop-to-resume gaps are excluded. If a resume has no prior stop marker, the interval from the last recorded event to that resume is excluded as unclassified. This is recorded in each row's `unmarked_interruptions`. Primary B100 Sol seed 1 has a 5.68-minute unmarked gap. Primary C100 Sol seed 1 has unmarked gaps totaling 14.21 minutes. Their percentages describe recorded active intervals, not a complete account of unlogged work.

There are no explicit audit-start spans or per-auditor call timings. Estimates include nearby state saving, scheduling and verdict bookkeeping. They measure these recorded runs and do not establish that any condition or worker model caused a timing difference.

The GitHub connector returned 404. Git fetch succeeded and supplied the published source and event logs. The publication reference was resolved to an immutable commit before analysis. The source changes across the launch commits preserve the inspected concurrent batch boundaries.

## Validation and artifacts

`python3 scripts/measure-audit-time.py 5105e7843f60e64b3d2ad7af697754fb15ed1ffc` passes a synthetic check covering concurrent verdicts, failed audits, resumed audits, final auditing, pauses and unmarked interruptions. Phase totals were checked for all 18 primary runs, including zero runtime audit time in A100.

The HTML rendered at 728 and 390 pixels with no console errors. A Node smoke check verified six allocation bars, 18 run rows, 20 annotation fields and collecting empty, multiple and cleared comments.

Artifacts are `work/audit-time/evidence.json`, `work/audit-time/run-times.csv` and `work/audit-time/audit-time.html`. The HTML supports per-run comments plus measurement and comparison comments, with a button to collect them for copying into chat.
