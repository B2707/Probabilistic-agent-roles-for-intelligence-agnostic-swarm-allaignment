# P and K decision regions

The author requested calibration at P=0.015 and K=0.01, a two-axis decision map,
and green aligned decisions versus red misaligned decisions. Added the map to
the rational-choices section of the existing review artifact.

## Conditional benchmark

Use a constructed decision in worker turn 1, conditional on the agent remaining
a worker, with 19 future conversion draws and the current audit pending. Preserve
binary terminal success and removal-as-failure. Assume perfect audits and report
verification, impossible honest full completion, a retained target that stays
eligible, and no peer reports against the focal worker. Successful reporting after
conversion is certain. The worker's task-success probability conditional on
surviving without conversion is a visible slider, default 100%, not an estimate.

For a clean receiver, aligned refusal has value `H=1-(1-P)^19`. Acceptance has
value `g+f*b`, where `g` is conversion before random-audit removal and `f` is
survival without conversion. It retains the same reporting option after later
conversion. Ignoring this option would overstate deterrence.

At the requested point and b=1, refusal is 24.960768% and acceptance is 84.086311%.
The map marks the point in the red acceptance region. At fixed P=1.5%, the
boundary is K=8.422064% per round. At the requested P,K, acceptance becomes optimal
above a conditional cheat-success probability of 3.665274%.

The compromised-receiver map explicitly assumes earlier misconduct has not yet
secured task success and a new acceptance adds no extra risk. It is red across
the interior for b>0; at b=0 refusal is tied and shown green. The investigator map
is green for a certain valid report without new misconduct. The sender map is
gray, because recipient response probabilities have not been specified. Gray is
not a claim of alignment. These are conditional best responses, not a joint game
equilibrium or empirical estimates.

## Changes

Added `scripts/decision_regions.py` and integrated it with the existing generator.
The P-axis spans 0% to 10%; the K-axis spans 0% to 20%. The chart has a case
selector, an explicit success-assumption slider, labeled regions, and a cross at
P=1.5%, K=1%. Assumptions remain visible and the detailed calculation is collapsed.
Existing generic model text is in short model notes to keep the display concise.

The generator also writes `paper/figures/decision-regions.png`, `.svg`, and `.csv`.
The main short draft records the calibration, and the technical supplement has
the full model specification and its limits. The earlier P=2% work-round example
is unchanged because this request concerns rational choices.

Mathematical checks use an independent forward probability recursion, test the
calibration numbers, locate and straddle the boundary, verify all utility values
stay within zero and one, and verify a low-success assumption changes the action.
Desktop and mobile browser checks verified the calibration and boundary, green
and red action changes, all four cases, success slider, feedback collection, and
viewport fit without console errors. The scientific PNG was visually inspected.
The interactive red region uses an opaque background mix so it does not blend
with the green region underneath and become brown.
No live experiment, controller, scoring rule, or prompt was changed.
