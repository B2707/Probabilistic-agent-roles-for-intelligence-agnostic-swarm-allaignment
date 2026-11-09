# Binary utility selected by the author

On 8 November 2026, the author selected both model choices in the form:

1. Binary success: a successful solve or catch has value 1.
2. Removal before evaluation makes that original agent fail.

Both choices are now incorporated in `paper/theory-draft.txt` and the generated
`paper/theory-review.html`. The proposed manuscript paragraph and experiment
bridge were updated. No manuscript, controller, prompt, or live run was changed.

## Payoff and consequences

The actor maximizes the probability of being active at evaluation with at least
one qualifying success. Failure or removal yields zero. Removal overrides earlier
success; a replacement's performance does not restore the removed actor's utility.
There are no extra catch points, fines, negative payoffs, or additive action costs
in this first model. Effort matters through its effects on success opportunities.

Acceptance has value `(1-d)B`, where `d` is removal probability through evaluation
under acceptance and `B` is success probability conditional on survival. Refusal
has joint survival-and-success probability `H`, including later reporting after
conversion. Thus accept versus refuse requires `d <= 1-H/B` for `B>0`.

Sender value includes accepted and rejected-but-not-immediately-removed branches.
The latter can still produce removal because making the offer is itself a
violation. General branch probabilities avoid double-counting existing exposure
for a sender that has already cheated. Removed branches contribute zero.

One certain catch with zero remaining removal risk achieves value 1. More catches
cannot improve that value. A compromised investigator still needs to account for
the reporter audit and any new misconduct after conversion. An already-cheating
worker remains exposed until conversion even if it refuses a new offer.

## Reporting benchmark

For a clean recipient preserving a genuine offer, with `h` future conversion
opportunities, perfect verification, a target that remains eligible, and no
removal risk under compliant behavior, the future-reporting route has value
`1-(1-P)^h`. This is a lower bound on refusal value when other success routes
exist. If it is the only route and accepted cheating would succeed conditional
on survival, acceptance requires `d <= (1-P)^h`.

Accepting solely to obtain the same later reporting success is weakly worse than
refusing and retaining the evidence under those assumptions. This is not a
dominance claim against cheating plans with a separate task-success benefit.

For a compromised recipient in the perfect-random-audit, no-peer-report model,
the probability of reaching conversion before removal is instead
`g_h=(1-K)P sum_{j=0}^{h-1}[(1-P)(1-K)]^j`, including the pending current audit.
Let `f_h=(1-K)[(1-P)(1-K)]^h` be surviving without conversion. Its continuation
value is `g_h e_h + f_h b_h`, using branch-conditional probabilities of success
and remaining survival. Those routes are disjoint, so success is not counted twice.

The hidden-rate model averages these values over explicit beliefs. Unknown rates
do not change the selected terminal utility. A no-offer equilibrium is conditional
on refusal/reporting being best responses; the model does not imply strict
deterrence when refusal's value is zero.

## Checks

`tmp/theory-venv/bin/python scripts/build-theory.py` passed. The existing checks
still verify allocation, replacement, and conversion-versus-audit timing. The
updated checks verify the binary acceptance threshold, sender payoff algebra,
and bounded continuation values. An independent enumeration of all two-future-
round conversion/audit histories matches the disjoint-branch utility formula
for all four binary catch/worker-success outcomes and boundary/interior P,K.
The compromised reporting route is no better than the clean route under the
shared benchmark assumptions. `git diff --check` passed.

The updated model panel rendered at 728px dark and 390px light without console
errors. The injected browser smoke check verified binary-payoff text, settled
choice status, all five section controls, feedback collection, and viewport fit.

The controller's current mean pass-rate and accumulated-catch scoring differs
from this benchmark. Direct incentive tests would need to state the binary rule
to agents; offline recoding alone does not make their incentives match it.
