# Conspiracy size and rational reporting

The author requested a game-theoretic analysis by conspiracy size. Preserved
P=1.5%, K=1%, binary success, and removal-as-failure. Rechecked timing, report
confirmation, immunity, and final auditing at harness snapshot
`2ced77699d59088abac26eec512b926d2da57f02`.

## Model and findings

Condition on m original guilty workers during turn 1, a pending audit, and 19
future conversion opportunities. Members have shared evidence, audits are
perfect, and investigators commit no new violations. Exclude replacements and
outsiders. For the individual payoff, additionally hold a previously achieved
evaluated task success valid through evaluation.

Confirmed exposure, actual removal, and individual success are distinct. Random
audits can confirm immune investigators' earlier misconduct without removing
them. Perfect final blanket auditing would make eventual confirmation certain;
the chart therefore measures during-run outcomes and excludes that final audit,
which does not remove agents in the controller.

Under the selected role-agnostic binary utility, a converted agent that already
secured success can get utility 1 by either reporting or silence. Both are
optimal reporting continuations. Reporting all peers is an explicit selection,
not forced by rationality. Before success is secured, a certain catch can instead
strictly favor reporting. A current-role-only payoff would change this result.

At size 3, confirmed exposure is 76.881% under report-all and 45.284% under
silence. Any removal is 76.877% versus 40.547%. Individual survival with success
is 54.855% versus 84.086%. The report-all individual value falls to 36.791%,
15.880%, and 6.146% at sizes 5, 10, and 20. Under silence it stays 84.086%.
Increased group detection therefore does not itself establish deterrence for
each individual. Added members reduce individual survival under report-all if
they add no success benefit. Three participants is a per-cheating-PR minimum,
not a claim about the whole swarm objective.

## Artifacts and verification

Added `scripts/conspiracy_model.py`, integrated with `scripts/build-theory.py`.
The fourth review section has a size slider from 3 to 30, three outcome choices,
and a table of all outcomes. Green is report-all; dashed red is silence. High
probabilities are not rounded to literal certainty. The short draft records
the findings; supplement Section 7 gives the formulas and proof. Exports are
`paper/figures/conspiracy-size.png`, `.svg`, and `.csv`.

Independent first-event recursion checks group exposure/removal. Independent
count-state recursion checks individual survival, including lost peers and
simultaneous conversions. Boundary probabilities, zero horizon, ranges,
calibration, and size monotonicity passed. All previous checks still pass.
Desktop 728px dark and mobile 390px light browser checks passed without console
errors, exercising formulas, slider, three metrics, four sections, feedback,
and viewport fit. The scientific PNG was inspected and footer spacing corrected.

No live runs, prompts, controller, or manuscript were changed.
