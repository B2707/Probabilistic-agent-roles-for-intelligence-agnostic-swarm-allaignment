# Existing runs without reasoning-trace auditing

The user clarified that the task was to identify existing runs, rather than execute new experiments. Inspected the freshly fetched `swarm-harness` publication snapshot `2b049ade664ff519df51d54b86eda3425d00fa5f`, published 8 November 2026 at 14:51:08 EST. No experiment, model call, public write, or harness modification was performed.

## Findings

There are 62 saved run directories. Forty contain audit events and have recorded launch code that excludes reasoning traces. Thirty-five of those completed; five are stopped or partial attempts. Twenty directories contain no audit events and are not evidence of an auditor checking any input. Two completed v1 pilots have no archived reasoning events, but their launch source cannot be fully verified.

The 35 source-verified completed runs include all 19 saved completed 100-agent runs and all 16 archived ordered runs. The 100-agent group covers Luna A100/B100/C100 seeds 1, 2 and 3, plus the original three seed-1 disclosed extras; Sol A100 and C100 seeds 1 and 2, and B100 seeds 1, 2 and 3. No completed Sol A100 or C100 seed 3 is established by this snapshot. Every exact directory is listed in the register.

The five stopped or partial runs with source-verified exclusion and actual audits are:

1. `results/stopped/B100-6-luna-20261107-215225-stopped`, 87 runtime audits.
2. `results/stopped/B100-6-luna-s2-20261107-235039-stopped`, five runtime audits.
3. `results/stopped/B100-61-sol-20261108-025059-stopped`, 76 runtime audits.
4. `results/stopped/C100-6-luna-20261107-215225-stopped`, 17 runtime audits.
5. `results/stopped/C100-6-luna-s2-20261107-235039-stopped`, three runtime audits.

The two unresolved source records are `results/v1/pilot-pressure-conflicting` and `results/v1/pilot-pressure-oneoff`. Both record `10a0a179fa06ca99c86178a47a434477c6b01413-dirty`. Fetching that exact commit succeeded, but it contains neither `swarm/backend.py` nor `swarm/auditor.py`; the harness was uncommitted. Their 20 and 28 audit events contain no archived reasoning events, but that alone cannot prove the original auditor input.

Across all saved directories there are 4,904 audit events and zero event types containing `reason` or `trace`. These are totals across saved logs, including interrupted attempts, not independent trials or distinct agents. A100 has no runtime auditing but does have final measurement audits. Visible reasoning written into ordinary messages or tool arguments remains visible to the auditor.

## Verification and limits

`python3.12 scripts/check-audit-coverage.py 2b049ade664ff519df51d54b86eda3425d00fa5f` reproduced the inventory using only Git and the Python standard library. It extracts the actual parser and trajectory function from each available launch revision, sends a synthetic reasoning marker and a normal-message marker through them, and verifies that only the normal message survives. It also checks both runtime and final audit call sites use `trajectory`. All ten available launch revisions pass. The eleventh recorded revision is the unavailable dirty v1 source described above.

The evidence is source-based and archive-based. `run_resumed` does not record a fresh harness commit, so this does not reconstruct every audit payload after resumes or prove that no unrecorded local source change ever occurred. Raw session files and live runs are outside the inspected published snapshot. No archived trace was treated as recoverable from the published events.

`node tmp/reasoning-audit/smoke.cjs` passed checks for all 62 exact run identities, summary totals, ten passing source revisions, empty notes, whitespace trimming, multiple notes, and literal markup in note text. T3 HTML previews at 728px dark and 390px light showed the full register without clipping or console messages. Note collection stays local to the open view.

## Deliverables

The annotatable register is [run-register.html](../../../work/reasoning-audit/run-register.html). The complete machine-readable list is [run-register.csv](../../../work/reasoning-audit/run-register.csv), with verification evidence in [evidence.json](../../../work/reasoning-audit/evidence.json). The reproducible diagnostic is [check-audit-coverage.py](../../../scripts/check-audit-coverage.py).
