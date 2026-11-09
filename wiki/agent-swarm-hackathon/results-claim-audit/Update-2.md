# Revised theoretical claims and quotable discussion

The author requested a version they can cite and respond to, and clarified that
tool/channel robustness and retained worker capacity are intended theoretical
claims, with experiments showing that the selected configurations work.

Created `paper/results-discussion.txt`. It uses stable numbered points and one
sentence per source line for native T3 file comments. The response also states
the three disputed claims in ordinary chat text, so the author can quote them.
No replacement HTML visualization, local review server, manuscript edit or new
experiment was needed.

The worker-turn argument is sufficient for a conditional claim about retained
worker-role capacity. The no-removal reference expectation is 1,465.85/2,000,
or 73.29% of all available agent-turns, at N=100, I0=10, T=20 and P=2%.
The replacement coupling gives a lower bound on expected worker-role turns
only with its full-turn, next-round replacement and no-early-stop conditions.
The number is not a per-seed floor. Primary C seed 3 logs 1,453 worker rounds,
72.65%, and C's three-run average is 1,498, 74.90%. The logged count measures
agent/round turn inputs, not guaranteed productive or successfully completed
turns. The paper can report the theoretical allocation and reduced observed
exploitation at the selected settings without adding a task-quality benchmark.
A useful-output lower bound additionally needs worker productivity and
nonnegative investigator contribution assumptions.

Tool/channel robustness should be a conditional theoretical design rationale.
The conversion mechanism does not need to enumerate communication channels.
Under the independent fixed-population model, the chance at least one of m
workers converts over H rounds is 1-(1-P)^(mH), independent of channel identity.
Exposure still requires knowledge retention, reportable and verifiable evidence,
reporting incentives and enforcement. Extra tools can change those conditions.
This is a weaker defensible claim, not an arbitrary-tool empirical guarantee.

Read the original three-model benchmark thread before discussing it:
<t3-thread://v2/7269d675-f9c9-4ee0-853b-b23c8704f85d/70952f7e-71b3-4d10-9ce0-fde7e700ebc7>.
It establishes that the saved Luna/Terra/Sol numbers are Agent Arena steerability,
not three worker-model conditions in the swarm experiment. Reopened the primary
Arena signal and methodology pages. Random model assignment supports an effect
of model selection within Arena, but does not isolate intelligence from model
training and other model-specific changes or establish the prisoner's-dilemma
explanation. The saved result is useful external evidence for model-dependent
adherence, with Sol and Terra estimates above Luna's.

Fetched `origin/swarm-harness` to publication
`6b056ae31b00f8c194bba786cd5908f91f0b8aa2`, 10:29:56 EST. Inspected all 58
published run configurations. No Terra worker configuration is present; Terra
is the configured auditor/judge in the core experiments. Current completed
comparison metrics match the original 10:16 snapshot. The original aggregation
remains pinned and was not overwritten.

Verification recalculates the allocation formula, both denominators, all three
primary C worker-turn counts, the reported mean and the published model
inventory. Checked the text file for stable numbered points and readable source
line structure. The original metric attribution caveat remains in force.
