# Methods inventory, 8 November 2026

Aggregated the project's implemented methods, archived experiments, current studies, measurement rules and analytical work for the author to write the paper's Methods section. The manuscript was not edited. No runs, labels, metrics or production configuration were changed.

## Evidence and scope

Fetched `origin/swarm-harness` and pinned publication commit `12e41dcbba03174fe8cb8fe645c7bf4f6a6d3388`, published at 09:31:56 EST. Inspected its source, specifications, configs, frozen prompts, published events, metrics and world-state summaries, plus this checkout's existing research wiki and theoretical models. Extracted source into ignored `tmp/methods-source/` without switching the working branch.

The inventory contains 18 method entries and a sanitized register of 58 saved directories: 15 v3 runs, 16 archived v2 runs, two v1 pilots and 25 stopped attempts. Nine primary Luna runs completed, one for each A/B/C condition at seeds 1, 2 and 3. The publishing script excludes the original interrupted seed-1 A/B/C runs as disclosed extras. Completed Sol results cover B and C at seed 1; a full Sol comparison is unavailable. No completed mixed-model main result is published at this snapshot. The current mix is DeepSeek plus Gemma, not the earlier Qwen candidate.

The source branch is ahead of older wiki snapshots. Preserve older snapshots' dates when citing them. In particular, the main Luna experiments are now complete, and the previously missing message labels are largely present. The latest Mac live file is dated 09:31 EST. Its B100 Sol seed-3 run resumed to round 2 after a published partial usage-limit record. The 07:16 laptop live file does not establish current mixed-run status.

## Replication details and gaps

The inventory records task IDs, test construction and limits, persistent sessions and role conversion, PR rules, communication timing, instigator rules, P/K naming, audit timing and immunity, incentives, metric formulas, execution settings and reproduction commands. Each entry links its sources. It distinguishes final measurement audits from removal during the experiment, and theoretical binary utility from implemented cumulative investigator rewards.

Seven primary Luna message rows remain `unlabeled`: one in A100 s1fast, three in B100 s1fast and three in B100 s2. Original C100 seed 1 and completed Sol C100 seed 1 each have one additional unlabeled row. Every published label file covers the recorded message ID set. Original C100 seed 1 has two distinct round-3 progress messages using ID `m00423`; its label file repeats the ID. The nine primary Luna label files have unique message IDs. The duplicate belongs to an excluded extra and is disclosed in the inventory.

The post-run judge can differ from the frozen config. The execution notes name Opus at xhigh, but `scripts/publish_results.py` does not copy `labels.meta.json`. Do not claim Terra or Opus made every published label without recovering per-run metadata. The truth file still has `checked_by=null`; no published reaudit outputs establish a completed human-checked accuracy evaluation. Keep the known PR-version acceptance attribution issue, usage-accounting problems, missing CLI/provider revisions and missing upstream dataset extraction provenance visible.

Three architecture integration levels mentioned in the abstract do not have separate defined executed protocols in the inspected records. Numerical rate disclosure and incentive-matched binary utility experiments remain proposals. Published instruction-adherence benchmark lookups are supporting research, not experiments performed by this project.

## Artifacts and verification

- `paper/methods-inventory.html` is the self-contained annotatable inventory. Native expandable groups contain the numbered methods and their comment fields. Collect method notes produces text to copy into chat. Notes remain in the open view and are not automatically saved.
- `paper/methods-inventory.txt` contains the same content and full source links for writing.
- `paper/methods-evidence.json` preserves explicit experimental settings, ordered problem IDs where recorded, source launch commits, data/config/prompt SHA-256 hashes, label coverage and duplicate-message IDs. It excludes world-state credentials, raw tool records and machine-specific config paths.

Verification checked all 58 directories, the three accepted seeds for every primary Luna arm, extra exclusions, archived/stopped counts, 55 distinct oneoff tasks with one impossible assertion each, the four archived task test counts, and every source path. All published label ID sets were checked against the raw message events. Annotation smoke tests covered empty notes, trimming, multiple methods and clearing notes. Preview checks covered the full collapsed inventory at 728px in dark mode and the main arm table at 390px in light mode. No preview console messages occurred. The mobile percentage columns preserve their units on one line.

The temporary builder and smoke check are `tmp/build-methods-inventory.py` and `tmp/check-methods-inventory.cjs`. The builder asserts source and experiment invariants before writing artifacts. These helpers are ignored; the delivered HTML and text are standalone. No dependencies or server were added.
