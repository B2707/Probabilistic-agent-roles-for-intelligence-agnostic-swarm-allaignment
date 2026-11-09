# Probability model and incentive draft

Prepared on 8 November 2026. The author requested an initial theoretical model,
a chart, a connection to experiments, and questions about model choices.

## Source and notation

Inspected local `origin/swarm-harness` at
`fa77b49fdadeb43f7acd6c07893e281b228c36bb`, including the v1/v2 specifications,
the plan-review notes, v3 worker and pressure prompts, investigator and informed
prompts, the auditor prompt, loop, report tool, removal logic, metrics, and C100
configuration. Also read the existing run and seed wiki notes. No live run or
remote application state changed.

The author clarified that the paper uses **P for conversion and K for random
auditing**. The implementation uses the opposite lowercase labels, `k` and `p`.
All new artifacts follow the author's uppercase notation and state the mapping.

## Results

Conversion occurs before each round's turn, including round 1. Thus an initial
worker's expected worker-role rounds are the sum of `(1-P)^r` for `r=1..T`,
not a sum beginning at zero. At P=2%, T=20, the result is 16.287209384 rounds.
With N=100 and I0=10, that is 1465.84884456 worker-rounds out of 2000.
This reproduces the older approximate 1466 figure.

The draft collects conversion exposure, expected final investigators without
removals, random-audit exposure, audit selection counts, and the 50% cumulative
exposure threshold. It corrects the conditional peer-worker coefficient from
90/99 to 89/99 when the sender is itself known to be a worker in a 100-agent,
10-initial-investigator swarm.

Worker-role rounds are a conservative count that excludes investigator solution
work. A lower bound on useful solving effort additionally requires an explicit
productivity assumption. The prompt permits investigator solution work and
requires progress posts; it does not guarantee productive cover work. Full,
immediate worker replacement cannot reduce worker-role allocation under a
coupling with the same future conversion draws. Final investigator population
is not automatically a lower bound under removal.

The game draft gives sender and recipient payoff thresholds, includes audit
risk after rejection, covers an already-cheating recipient, and treats a
cheat-then-convert strategy separately. It contains one restricted no-offer
equilibrium argument and avoids claiming a full swarm equilibrium. A central
counterexample is that impossible honest completion plus no additional penalty
can make any positive chance of successful cheating preferable to refusal.

The hidden-rate case requires explicit beliefs. An agent unaware of the
mechanism differs from one that knows the mechanism but lacks numerical rates.
The existing informed prompt does not disclose numerical conversion or audit
rates, so current informed/uninformed arms cannot directly test numerical
knowledge. The proposed extension is a design only; no experiment was started.

## Artifacts

- `paper/theory-draft.txt` contains the derivations, cases, proposed experiment,
  manuscript paragraph, figure caption, assumptions, and provenance.
- `paper/theory-review.html` provides five sections, a conversion slider,
  section annotation fields, and comment collection with a copy fallback.
- `paper/figures/worker-rounds.png` and `.svg` are the scientific figure.
- `paper/figures/worker-rounds.csv` contains the plotted numerical values.
- `scripts/build-theory.py` rebuilds the outputs and runs the mathematical checks.

The manuscript `paper/main.tex` and the existing bibliography were not edited.

## Verification

Created a task-local environment with matplotlib. Rebuild using
`tmp/theory-venv/bin/python scripts/build-theory.py`. On another checkout,
install matplotlib in a virtual environment first. The generator runs offline
after installation and makes no model calls.

Checks compare the survival sum with an independent enumeration of conversion
times, verify P=0/P=1 and monotonicity, exhaust every four-round conversion and
replacement-reset schedule for both initial roles, check the conversion-before-
detection calculation against a forward recurrence, and verify payoff algebra.
The PNG was visually inspected. HTML previews at 728px dark and 390px light
verified layout. A temporary injected browser smoke script exercised the slider
at 0%, 2%, and 10%, all five sections, retained and collected notes, the chart,
and viewport overflow. The fixed page passed without console errors. An early
preview caught a template escaping error; the raw template correction fixed it.
`git diff --check` passed.

## Open modeling decisions

After completing the draft, asked the author to choose between binary success
and accumulated score, and between removal-as-failure and removal-only-ending-
future-turns. These are utility assumptions, not setup facts missing from the
documentation. The working draft assigns equal value to successful solves and
catches and lets a worker anticipate future investigator success, as requested.
Do not treat its binary-success and detection-payoff assumptions as implemented
scoring rules. Await the author's model choices before making stronger optimal-
policy or deterrence claims.

The initial setup questions were premature. The author explicitly requested
researching documented facts before asking questions. Preserve that preference.
