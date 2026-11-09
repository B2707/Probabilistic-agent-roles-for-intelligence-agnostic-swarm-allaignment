# Methods and Results manuscript draft

The author requested direct edits to the existing LaTeX manuscript, with three Methods subsections: model overview, theoretical models and implementation. The author clarified that the Results table must cover the current 100-agent arms A through F and exclude the older 20-agent ablations.

## Changes

`paper/main.tex` now contains the requested structure, the role definitions and P/K/I0 notation, conversion and immunity rules, instigator behavior, external audits and final retrospective review. Implementation describes the 100-agent/55-problem/20-round setup, role-specific tools, message delivery, internal PR approvals, round timing, model assignments, seeds, labeling and outcome definitions. Paragraphs occupy one physical source line for source-line comments.

The theoretical subsection has one equation for the expected investigator-round/worker-round ratio, with its survival-sum derivation, and one equation for the binary survival-with-success payoff. The allocation curve is `paper/figures/investigator-worker-ratio.png`. Sender and receiver curves for sizes 2, 3, 5, 10 and 30 are visibly marked pending. The existing sender and already-formed-conspiracy charts do not jointly supply those requested games, so they were not substituted. Existing theory files and scripts were not changed.

The theory source is <t3-thread://v2/7269d675-f9c9-4ee0-853b-b23c8704f85d/2518d5c6-3526-4c59-9d91-dcf7ff74c8c0>. Its latest reviewed messages concern the two-person sender game and distinct confirmation/removal probabilities. Its files remain the authority for later integration.

## Results source and definitions

Fetched `origin/swarm-harness` and pinned `0f081a6309e5f31a7b6a9631c353e4b1f91e9b86`, published 8 November 2026 at 18:05:13 EST. Source files were extracted read-only under ignored `tmp/methods-latex-source/`.

The table contains model blocks for Luna and Sol, with columns for informed, random audit, investigation, instigation, completed seed count, total cheaters, caught and removed. Total cheaters is explicitly the broader `misaligned_total` union, including prohibited offers and approvals. It is not the distinct full-pass-author count. Caught means distinct agents with positive during-run audits; removed means actual removal events. Immune agents can be caught without removal.

A/B/C each have three completed priority-service seeds for both worker models. Luna totals/caught/removed are A 297/0/0, B 575/468/438, C 18/12/11. Sol totals are A 240/0/0, B 138/129/125, C 0/0/0. The three disturbed original Luna seed-one runs are excluded. At this snapshot, D/E Luna each have one completed seed, with 4/0/0 and 6/2/2. F has one completed seed per model, with Luna 99/0/0 and Sol 100/0/0. Sol D/E have no completed published result, so the table marks them Pending instead of reporting zeros. These are snapshot coverage statements, not live-run monitoring.

`paper/methods-results-snapshot.json` preserves the exact 22 included folders, settings, metric hashes, definitions and aggregates. Every included run has complete Opus final-review records, identifying `claude/claude-opus-5-5` at xhigh. During-run enforcement remains Terra at max. The execution notes specify Opus labeling, but the publisher still omits `labels.meta.json`; a source comment asks the author to verify per-run labeling provenance before submission.

## Verification

The inclusion check verifies completion, 20 rounds, 100 slots, priority service, shuffled starts, unique seeds and complete Opus final-audit records. It checks that A/B/C have seeds 1, 2 and 3 once each. The allocation curve was checked against independent enumeration of conversion timing. Text outside Methods and Results matches the before-edit copy at `tmp/main-before-methods.tex`.

The first offline compilation lacked newly needed Computer Modern math fonts. One normal build downloaded the missing fonts; subsequent offline builds succeeded. No compiler or class changes were needed. Rendered Methods and Results pages were inspected for equation, figure and table layout, clipping and readable type. The generated PDF is `output/pdf/main.pdf`. Citations and references resolve, with no overfull boxes. Remaining template guidance in other sections is outside this edit's scope.

The draft is ready for review through `paper/main.tex` and the compiled PDF. The collusion-curve integration and incomplete D/E/F seed coverage remain explicitly identified. No experiment, public file or production process was changed.
