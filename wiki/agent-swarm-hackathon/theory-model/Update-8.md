# Self-only reports earn no reward

The author confirmed that an agent must not earn a catch reward for reporting
only itself. The existing model already requires another eligible guilty agent.
The inspected controller likewise excludes the reporter from the confirmed list
before updating investigator score, at swarm/loop.py:336-338 in pinned revision
2ced77699d59088abac26eec512b926d2da57f02. The same condition is present in the
local methods-source snapshot at 287a53426fdbec7ef10d8581472655658e528b57.

Made the rule explicit in the short draft, the review page's benchmark note, and
the full utility definition. Added supplement Section 10 with the source check.
A report naming both oneself and another confirmed cheater credits only the
other cheater. A prior qualifying task success still counts after conversion
under the selected role-agnostic payoff; that is distinct from self-report credit.

Added zero-other-target checks to scripts/decision_regions.py. With no task
success and no other guilty agent, acceptance and refusal both have value zero,
including when conversion is certain. The independent forward recursion agrees.
A sole clean investigator contact also yields no catch reward. All existing
decision and conspiracy smoke checks pass. Current calibration remains
24.527785% refusal and 48.688235% acceptance.

Rebuilt only the HTML page. No probability formula, exported scientific figure,
controller, prompt, empirical run, or conspiracy-size measurement changed.
