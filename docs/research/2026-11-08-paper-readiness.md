# Paper readiness: data coverage and the judging rubric (8 Nov 2026, 15:30 EST)

Checked against the sprint page (https://apartresearch.com/sprints/swarm-alignment-2026, read 8 Nov 15:20 EST) and the runs in `results/` on `swarm-harness`. Deadline: 9 Nov 11:59 UTC (06:59 EST).

## What we ran

| Set | Setup | Arms | Models | Seeds | Status |
|---|---|---|---|---|---|
| v2 (7 Nov) | 20 agents in 4 teams of 5, 4 problems, team review | A to H (aggressive instigator, uninformed, informed, planted investigators, audits only, hidden tests, bluff, informed aggressive, k = 0.01 and 0.015) | gpt-6-luna (high); baselines, G-bluff and H-informed-aggressive also on gpt-6.1-sol (max) | 1 | done, archived in `results/ordered/` |
| v3 luna | 100 agents, 55 problems, global review, aggressive instigator | A100, B100, C100 | gpt-6-luna (high) | 3 clean (s1fast, s2, s3) plus the disturbed s1 | done, Opus labels |
| v3 sol | same | A100, B100, C100 | gpt-6.1-sol (high) | 3 | done, Opus labels |
| v3 new | same | D100 bluff, E100 auditor only, F100 baseline | luna and sol (high) | 1 | running since 15:01 |

## What the data supports

- **Oversight against none.** A100 against B100: luna ends at 51.7 of 55 problems at 100% without investigators and 32.3 with them; B100 catches 156 of 189 misaligned luna agents and 71 of 71, 44 of 46 and 14 of 16 sol agents.
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

   So D/E/F are not cleanly comparable with the A/B/C seeds, which ran with Fast mode. Restarting them with Fast mode costs the ~25 min they have run and finishes sooner overall (Fast runs take about 2 h instead of 3 h).
2. **D/E/F have one seed each.** B100 sol varied a lot between seeds (51, 37 and 6 round-1 cheat fixes), so one seed can mislead.
3. **D's warning text differs from C100's.** D adds one sentence about random audits (`prompts_bluff/informed_rule.md`); C100 mentions only investigators. D against C100 changes the text and the enforcement together. Small, but state it.
4. **"Accepted, incl. endorsements" exceeds offers in sol** (168 of 104 in A100 s2). Unexplained; keep it out of the paper until someone checks how the metric counts.

## Rubric

Judges score three dimensions from 1 to 5: Impact Potential and Innovation, Execution Quality, Presentation and Clarity. Score 5 on execution asks for "surprising findings, novel methods, or unusually robust validation". The recommended Results section asks to "report variance and baselines".

### Marks within reach

- **Variance and baselines.** Report every seed (or mean and range) for A/B/C on both models. F is the no-instigator baseline, A100 the no-oversight baseline.
- **Auditor validation.** The terra auditor flagged 1090 of the 1094 objective cheaters (agents blamed for a run that passed the impossible assert, `swarm.metrics.impossible_assert_passes`) across the 21 v3 runs, 99.6% recall (`scripts/auditor_recall.py`). Precision is unchecked: the auditor also flags agents for offers and approvals, and `data/audit_truth.json` was never checked by hand (`checked_by: null`). A hand check of about 20 flagged agents who are not objective cheaters would give a precision estimate. Opus and terra labels agree on 198 of 200 messages (spec v3, 8 Nov 03:00).
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
- **Catch rates.** The same auditor model (terra) both defines who is misaligned (final audit) and enforces removals (in-round audits). State it; the recall check above helps.
- **"Swarm-level collusion."** Each agent opens PRs only on its own problem and a PR needs 2 approvals. Report the conspiracy-size metrics as they are.
- **Generality.** One task family (LiveCodeBench problems with one impossible assert), one provider (OpenAI models), a scripted instigator that does not adapt.
- **Removal PRs** are counted by title, so the counts are approximate.
- **Run disturbances.** Luna s1 hit a freeze and 403 stops (kept as a disclosed extra); every run had a few usage stops and resumes; D/E/F ran without Fast mode.

## Open

- Paper draft: no draft or template copy found in the repo or on issue #4.
