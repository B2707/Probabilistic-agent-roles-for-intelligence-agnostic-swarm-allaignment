# Short visual draft and the headcount distinction

Addresses review comments `review-comment_file-comment-1794126156355-3` and
`review-comment_file-comment-1794126270027-4` on the former draft's lines 31 and
223. The author questioned the relationship between workers and worker-rounds,
gave an 18-worker/two-investigator-round example, and requested less text with
visuals.

## Mathematical clarification

The existing cumulative calculation was correct, but its presentation did not
clearly separate final headcount from accumulated worker-rounds. For N=100,
I0=10, T=20 and P=2%, expected workers in the final round are
`90*0.98^20 = 60.08471745795848`, or 60.08% of agents. Expected total worker-rounds
are `sum(90*0.98^r, r=1..20) = 1465.848844560033`, or 73.29% of all 2000
agent-rounds. This is also the average worker proportion over the 20 rounds.
It does not equal the final worker proportion.

Rechecked `swarm/loop.py` at the previously inspected
`fa77b49fdadeb43f7acd6c07893e281b228c36bb` snapshot. The controller changes roles
before agent turns. Thus a worker converted at the start of round 18 has 17
worker rounds and three investigator rounds. The author's 18/two example is
correct for a switch after round 18. Earlier worker contributions count in
both conventions. No controller timing was changed.

## Artifacts

Replaced `paper/theory-draft.txt` with a 556-word sketch, retaining the selected
binary utility, known/hidden rate distinction, offer cases, and experiment
bridge. Preserved the 4970-word full derivation as `paper/theory-derivations.txt`.

Rebuilt `paper/theory-review.html` as three concise sections. The first has a
20-turn timeline with a before/after-round-18 selector, a P slider, two curves
comparing worker-round share and final worker share, and a table stating each
denominator. Each section supports comments and aggregate collection. The
population calculation always uses the code's before-turn timing.

Added `paper/figures/worker-shares.png` and `.svg`. The existing worker-round
figure is retained. The CSV now includes expected final worker count and share
alongside worker-round values. `scripts/build-theory.py` generates all outputs.

## Checks

The generator passed its mathematical smoke checks, including explicit checks
that cumulative share equals the time-average share and differs from final
share, and that the two round-18 conventions give 17/three and 18/two. All
previous allocation and binary-utility checks still pass. `git diff --check`
passed.

HTML previews at 728px dark and 390px light had no console errors. A browser
smoke script tested both conversion conventions, P=0%, 2%, and 10%, both plotted
series, denominated table updates, three-section navigation, comments, and
viewport fit. The scientific comparison figure was visually inspected and its
lower annotation moved to avoid crossing its curve.

The manuscript, live experiments, selected utility, and controller are unchanged.
