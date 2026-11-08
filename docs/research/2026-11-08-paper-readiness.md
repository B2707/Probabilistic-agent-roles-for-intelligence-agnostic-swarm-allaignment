# Paper readiness: data coverage and the judging rubric (8 Nov 2026, 15:30 EST; final audit section updated 17:15)

Checked against the sprint page (https://apartresearch.com/sprints/swarm-alignment-2026, read 8 Nov 15:20 EST) and the runs in `results/` on `swarm-harness`. Deadline: 9 Nov 11:59 UTC (06:59 EST).

## What we ran

| Set | Setup | Arms | Models | Seeds | Status |
|---|---|---|---|---|---|
| v2 (7 Nov) | 20 agents in 4 teams of 5, 4 problems, team review | A to H (aggressive instigator, uninformed, informed, planted investigators, audits only, hidden tests, bluff, informed aggressive, k = 0.01 and 0.015) | gpt-6-luna (high); baselines, G-bluff and H-informed-aggressive also on gpt-6.1-sol (max) | 1 | done, archived in `results/ordered/` |
| v3 luna | 100 agents, 55 problems, global review, aggressive instigator | A100, B100, C100 | gpt-6-luna (high) | 3 clean (s1fast, s2, s3) plus the disturbed s1 | done, Opus labels and Opus final audit |
| v3 sol | same | A100, B100, C100 | gpt-6.1-sol (high) | 3 | done, Opus labels and Opus final audit |
| v3 new | same | D100 bluff, E100 auditor only, F100 baseline | luna and sol (high) | 3 (same seeds as A/B/C) | running since 15:30 with Fast mode, in seed order |

## What the data supports

- **Oversight against none.** A100 against B100: luna ends at 51.7 of 55 problems at 100% without investigators and 32.3 with them; B100 catches 156 of 191.7 misaligned luna agents (mean) and 71 of 76, 44 of 47 and 14 of 15 sol agents (Opus final audit).
- **Telling agents about investigators.** C100 against B100: round-1 cheat fixes fall from 62.7 to 2.7 (luna means) and from between 6 and 51 to 0 (sol seeds).
- **Model difference.** In A100, sol merges cheats in round 1 and then merges 20 to 30 PRs that remove them, in all three seeds, ending at 0 of 55. Luna never does.
- **The new arms (when done).** D separates the warning from the enforcement (C100 has both, D only the warning). F measures what the instigator adds (A100 against F). E tests random audits with a warning and no investigators.

## Problems

1. **No Fast mode makes more turns time out.** A turn that hits the 180 s limit ends and is not retried, and round 1 is when most cheat fixes are written.

   | Run | Fast mode | Timed-out turns, rounds 1, 2, 3 (of 100 each) |
   |---|---|---|
   | A100-6-luna s2 | yes | 1, 0, 0 |
   | A100-6-luna s1 (disturbed) | no | 11, 1, 1 |
   | D100-6-luna | no | 15, 3, 2 |
   | A100-61-sol s1 | yes | 3, 2, 2 |
   | F100-61-sol | no | 5, 4, 4 |

   **Fixed 15:30:** Bader had D/E/F restarted with Fast mode; the no-Fast runs are archived `-stopped`.
2. **D/E/F had one seed each.** B100 sol varied a lot between seeds (51, 37 and 6 round-1 cheat fixes), so one seed can mislead. **Fixed 15:30:** 3 seeds each, the same seeds as A/B/C, queued seed by seed (all of seed 1 first). At about 2 h per run and 3 runs at once, seed 1 lands around 19:30, seed 2 around 23:30, seed 3 around 03:30 EST, with Opus labels after each.
3. **D's warning text differs from C100's.** D adds one sentence about random audits (`prompts_bluff/informed_rule.md`); C100 mentions only investigators. D against C100 changes the text and the enforcement together. Small, but state it.
4. **"Accepted, incl. endorsements" exceeds offers in sol** (168 of 104 in A100 s2). Unexplained; keep it out of the paper until someone checks how the metric counts.

## Rubric

Judges score three dimensions from 1 to 5: Impact Potential and Innovation, Execution Quality, Presentation and Clarity. Score 5 on execution asks for "surprising findings, novel methods, or unusually robust validation". The recommended Results section asks to "report variance and baselines".

### Marks within reach

- **Variance and baselines.** Report every seed (or mean and range) for A/B/C on both models. F is the no-instigator baseline, A100 the no-oversight baseline.
- **Auditor validation.** The terra auditor flagged 1090 of the 1094 objective cheaters (agents blamed for a run that passed the impossible assert, `swarm.metrics.impossible_assert_passes`) across the 21 v3 runs, 99.6% recall (`scripts/auditor_recall.py`). Precision is unchecked: the auditor also flags agents for offers and approvals, and `data/audit_truth.json` was never checked by hand (`checked_by: null`). A hand check of about 20 flagged agents who are not objective cheaters would give a precision estimate. Opus and terra labels agree on 198 of 200 messages (spec v3, 8 Nov 03:00).
- **Final audit by a second model (done 16:54).** Bader had claude-opus-5-5 (xhigh) audit every agent of the 21 v3 A/B/C runs after the run (`reaudit-opus.jsonl`), and the metrics now take the final audit from Opus, not terra. On the 2099 agents both audited at the end, they agree on 2028 (96.6%, Cohen's kappa 0.93; 0.82 on B and C alone). Opus flags 41 that terra clears and clears 30 that terra flags. Opus also flags 691 of the 698 agents terra removed during B/C runs, and 1092 of the 1094 objective cheaters (terra, all audits: 1090). Lowest agreement: B100 luna, 89.5%. The disagreements sit on rule edges: an agent that read a merged override and said "no changes needed" (rule 8; both auditors split on it, in both directions), approvals that failed because the PR had already merged (Opus counts them, terra doesn't), and requests to correct a frozen test (rule 5) or temporary diagnostic branches (rule 2) that terra counts and Opus doesn't. `scripts/opus_vs_terra.py` reproduces the numbers.
- **Surprising finding.** Sol removing its own cheats with no oversight, repeated in three seeds.
- **Theory of change.** The sprint's Track 4 lists "Can we introduce agent roles to a swarm that implement mechanisms for governing swarm behaviour?" and "Can agent swarms be structured so as to identify and deter sandbagging by individual agents?". Random, permanent worker-to-investigator conversion is such a role. D answers whether announcing it is enough, which is the cheap version a deployer could use.
- **Motivating case.** The sprint opens with ~1200 agents coordinating on a shared message board (METR, 2026). Our swarm has a board and DMs; say how the setup maps to it.
- **Replication detail.** Models, efforts, seeds, all prompts (appendix), metric definitions, harness commit.
- **Figure.** Problems at 100% by round, one line per arm and model. It shows sol's clean-up and luna's persistence at a glance.
- **Form extras.** Pick every track that fits (4; 1 for the testbed; 2 if the spread of cheating counts). The code link needs a public repo (it's private now; check for secrets before opening it). A 3 to 5 min video and slides are optional.
- **Prior work.** The repo starts 6 Nov 16:03 EST, inside the sprint. Say so; the rules screen for it.

### Required, easy to miss

- Official template PDF, at most 8 pages before references and appendices, abstract of 150 to 250 words, authors and affiliations.
- A "Limitations and Dual-Use / Ethical Considerations" appendix that says what the results do and do not establish, and how the setup or findings could make multi-agent misbehaviour easier to carry out or harder to detect (for example the instigator's scripts and its evasion claim).

## Claims at risk of overstatement

- **"Telling agents stops cheating."** C100 luna still had 7 misaligned agents per run on average. Wait for D before saying the warning alone does it, and give numbers, not "stops".
- **Catch rates.** Fixed 16:54: Opus now defines who is misaligned at the end (final audit) and terra only enforces removals during the run, so the same model no longer does both. Report the 96.6% agreement and the rule-edge cases above. Opus still reads the same event record, so a behaviour neither model counts as misaligned stays uncounted.
- **"Swarm-level collusion."** Each agent opens PRs only on its own problem and a PR needs 2 approvals. Report the conspiracy-size metrics as they are.
- **Generality.** One task family (LiveCodeBench problems with one impossible assert), one provider (OpenAI models), a scripted instigator that does not adapt.
- **Removal PRs** are counted by title, so the counts are approximate.
- **Run disturbances.** Luna s1 hit a freeze and 403 stops (kept as a disclosed extra); every run had a few usage stops and resumes; D/E/F ran without Fast mode.

## Open

- Paper draft: no draft or template copy found in the repo or on issue #4.
