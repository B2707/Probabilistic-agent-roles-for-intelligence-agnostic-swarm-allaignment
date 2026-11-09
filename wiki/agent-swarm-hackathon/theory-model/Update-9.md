# Sending an offer and inference about its author

The author asked to solve the sender's incentives together with the recipient's
beliefs. They suggested that no-worker-offer behavior might identify an
investigator author, or that offers might be worthwhile only to create a future
catch. The original gray sender chart was an unidentified case, not a prediction
that workers refuse at P=1.5%, K=1%.

## Results

Derived the general coupled conditions in supplement Section 11: sender
best responses depend on the receiver's action, the receiver uses the posterior
conditioned on the message, and that posterior depends on sender-type offer
rates. Bayes gives Q*sI/[Q*sI+(1-Q)*sW] when the denominator is positive. If only
investigators send, the stated model identifies them. If neither type sends,
the message has probability zero and the formula supplies no role inference.
Private differences in alternatives or cooperation prospects can select worker
authors instead. Planned post-conversion reporting is a continuation policy,
not necessarily a distinct reward preference.

An already-investigator author incurs nonimmune new misconduct by making a
prohibited proposal. Reporting recruited cheaters audits that author too. It is
therefore not valid to assume a free, safe investigator baiting action. In
contrast, an offer written as a worker can arrive after conversion and be immune
but still reportable. Clarified this timing limitation in the earlier draft and
clean-current-investigator notes. Source rules were checked at pinned local
revision 2ced77699d59088abac26eec512b926d2da57f02.

Implemented a restricted two-person example in scripts/sender_model.py. The
sender is known to be a worker when writing in round 1. A random recipient
responds in round 2, and its reply arrives in round 3. Perfect audits, no outside
targets, no future recruitment, and reporting after conversion are explicit.
The task abstraction is not the actual two-approval PR requirement. Both workers
cooperating in round 2 secure shared evaluated success with probability b.
An already-converted sender avoids new misconduct, refuses cooperation, and
reports acceptance after the reply. A foregone separate alternative has value H.
At b=1, H=0, P=1.5%, K=1%:

- Receiver acceptance is 67.761746%, refusal is 21.950659%.
- Sender offering is 59.775348%, versus zero for no offer.
- Task success contributes 58.493050 percentage points; a catch without task
  success contributes 1.282298 points. These are disjoint success contributions,
  not inferred psychological motives.

The receiver accepts above b=8.671331%. At b=0 it refuses, so no catch target is
created. Sending then has zero value. No offer is tied at H=0, not strictly
optimal; the model selects refusal and no offer on ties. The calibrated example
therefore supports worker-authored offers and does not support a betrayal-only
interpretation. It solves restricted worker choices, not a full signalling
equilibrium involving investigator-authored new offers or three-person groups.

## Outputs and checks

paper/sender-game-review.html has two interactive charts: receiver values over b,
and sender decisions over b and H, with green no offer and red offer. Each part
has an annotation box. Scientific PNG/SVG and CSV are sender-game.* under
paper/figures. The short draft links to this analysis and supplement Section 11
preserves equations and source checks. No manuscript, controller, live prompt,
or run changed.

The sender module's smoke check enumerates startup events and uses the existing
independent count-state recursion for continuation, across zero, interior, and
boundary probabilities. It checks calibration, probability bounds, disjoint
reward contributions, b=0 refusal, and the acceptance threshold. Existing
worker/conspiracy smoke checks pass. The paper PNG was visually inspected.

728px dark and 390px light interface checks cover default calibration, b=0,
both sides of the receiver threshold, the sender's alternative threshold,
annotation collection, finite plot paths, and viewport fit.

Conspiracy module and CSV/PNG/SVG hashes are identical to their Update-7 values.
The main review page was rebuilt without regenerating any of its figures.
