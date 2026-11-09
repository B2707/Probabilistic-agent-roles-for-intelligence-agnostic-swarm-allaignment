# Current hidden-investigator risk

The author clarified that "instigator" means an already hidden investigator,
not the scripted experimental contractor. Added that current-role uncertainty to
the clean-worker decision chart while retaining future partner conversion.
The conspiracy-size module and CSV, PNG, and SVG have identical SHA-256 hashes to
before this change. Their conditioning and measurements are unchanged.

## Model

Let Q be the belief that one unknown current contact is an investigator. The
other n-1 partners are known guilty workers, and the focal agent is a clean
worker. Each action's value is the Q-weighted average of the current-worker and
current-investigator branches. Section 8 remains the worker-only branch;
Section 9 of `paper/theory-derivations.txt` gives this extension.

The reference prior is [I0+(N-I0-n)P]/(N-n). At N=100, I0=10, n=2, one completed
conversion draw, and P=1.5%, Q=11.5510204%. It conditions on the focal and other
known workers, not on message contents. The interface also permits a custom
posterior and a known-worker Q=0 comparison. The reference prior varies with P;
a custom Q stays fixed across the P–K chart.

The current investigator is compliant, refuses the cooperation needed to earn
the cheating task reward, and reports observed acceptance. It is not itself a
catch target. The default leaves the other guilty workers available. A reply via
direct message arrives next round, so focal conversion can grant immunity before
the report. Acceptance can then win through a catch with probability
(1-K)P[1-K^(n-1)]. A same-round visible-acceptance option makes that branch zero.
An alternative lets the investigator immediately clear all other guilty targets;
then both modeled action values in this branch are zero. At Q=1 these are ties,
shown gray, rather than evidence of strict deterrence.

A verified prohibited proposal authored by the unknown contact has zero
likelihood under the compliant-investigator branch. Its posterior Q is therefore
zero in this restricted model. The roster prior cannot be treated as the
posterior after reading such an offer. Allowing investigator entrapment through
new prohibited conduct needs its own reporter-audit/removal model. The current
unknown contact can instead be a prospective collaborator or observer of a
proposal made by another participant. This scope is stated in the artifact.

## Calibration

At P=1.5%, K=1%, n=2, h=19, reporting worker partners, certain task reward
conditional on worker cooperation, next-round reply, and Q_ref:

- Acceptance gives 48.688235% survival with success.
- Refusal gives 24.527785%.
- The K boundary at P=1.5% is about 9.193035% per round.

Setting Q=0 exactly recovers 54.854694% acceptance and 24.741648% refusal, with
K boundary 10.282031%. The conspiracy individual-success curve still has
54.854694% at size 3 because it conditions on an already formed group of guilty
workers. The current-role layer applies only to the clean-worker case. The
already-cheating case retains its worker-only scope; the investigator's knowledge
of earlier guilt is not specified. Sending remains unidentified without response
and fallback assumptions.

## Verification and outputs

The implementation remains in `scripts/decision_regions.py`. Independent
finite-state recursion verifies its worker branch. An enumeration of current
audit, next conversion, and target survival verifies the current-investigator
acceptance branch. Checks cover Q=0 regressions, probability bounds, reference
prior, same- versus next-round evidence, removed-target ties, and the single
boundary used by the plot. A larger temporary parameter grid checked both
reporting policies, reply timings, and target assumptions without extra crossings.
Existing conspiracy and work-round smoke checks also pass.

728px dark and 390px light previews passed without console errors. Browser smoke
checks exercised role beliefs, partner count/reporting, both evidence timings,
all-targets-cleared and one-investigator ties, task success, all four agent
situations, conspiracy controls and numeric regressions, all section tabs,
comment collection, and viewport fit. The PNG was visually inspected.

Updated the short draft, appended supplement Section 9, rebuilt only the decision
PNG/SVG/CSV and the annotatable HTML page. No controller, prompt, empirical run,
or manuscript changed. The direct-message timing and investigator instructions
were checked at pinned harness revision
`2ced77699d59088abac26eec512b926d2da57f02` using the local source history.
