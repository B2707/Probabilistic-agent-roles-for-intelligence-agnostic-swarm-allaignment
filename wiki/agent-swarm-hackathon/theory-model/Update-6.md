# Partner conversion added to the original decision chart

The author asked to include a partner's conversion in the original clean-worker
chart, then questioned what had created the original green region. Checked the
code: green had represented the focal worker's own future reporting chance versus
acceptance's random-audit risk. Partner reporting and already-present hidden
investigators were both excluded. The later conspiracy model had partner risk,
but the original chart had not been updated with it. Acknowledged the omission.

## Correction

Replaced `scripts/decision_regions.py`'s worker comparison with a joint model of
the focal worker and n guilty worker partners. It includes own conversion and
immunity, partners converting and reporting earlier misconduct, simultaneous
conversion, random audits of everyone, and targets disappearing before the focal
worker can report. Clean refusal cannot be validly punished by partner reports.
A converted partner remains a usable target for confirmation of prior misconduct
even though immune to removal, consistent with the inspected harness rules.

The default has two other partners, all currently workers, P=1.5%, K=1%, 19
future conversions, and partners reporting. Acceptance secures an evaluated task
reward with probability b, default 100%; that reward stays valid through
evaluation. With b=0, conversion alone does not win if every target was removed.
The retained-target guarantee in the original chart was removed consistently
from both action branches.

The corrected default values are 54.854694% acceptance, 24.741648% clean refusal,
and 18.001453% already-guilty refusal. If partners stay silent, acceptance is
84.086311% and clean refusal remains 24.741648%. Seven reporting partners make
clean refusal preferable at the same P,K. At P=3%, K=1%, two reporting partners
give 43.637648% refusal versus 43.346365% acceptance.

The current K boundary at P=1.5% is 10.282031% with two reporting partners, versus
12.139705% with two silent partners. Do not compare these directly with the old
8.422064% boundary without acknowledging the target-availability correction:
audits can remove the agents the clean worker hoped to catch.

## Interface and verification

The original two-axis chart now exposes partner count and reporting policy, in
addition to task-reward success. It still explicitly conditions on partners being
workers now; it does not infer the prior probability of an initial investigator.
Partner counts include a one-partner toy case, the two-partner PR case, and larger
groups up to 29 other partners. Sender uncertainty and the investigator case
retain their stated scopes. The figure and CSV now record the partner assumptions.

An independent finite-state recursion checks the closed-form sums over surviving
partner counts and a protected investigator target. It matches at boundary and
interior P,K, horizons 0/2/19, partner counts 1/2/5, and reward probabilities
0/0.5/1. For reward probability 1, the acceptance value also matches the separate
conspiracy model at group size n+1, including large groups. Regression checks
ensure peer reporting lowers acceptance, sufficient partners can change the
action, and displayed action rows have a single crossing over tested controls.

The short draft and supplement Section 8 are updated. Supplement Section 6 is
marked historical and superseded. No live run, controller, prompt, or manuscript
was changed.

Desktop 728px dark and mobile 390px light browser checks passed without console
errors. They verified the new calibration and boundary, low-K green case, partner
count and report/silence controls, one-partner and large-coalition cases, reward
probability, all role cases, four-section navigation, notes, and viewport fit.
The updated paper PNG was visually inspected; its zero-utility contour is drawn
from the full probability surface so it reaches the zero-audit axis correctly.
