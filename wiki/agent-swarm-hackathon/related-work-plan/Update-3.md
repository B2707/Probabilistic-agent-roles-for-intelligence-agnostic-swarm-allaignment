# Paper-to-design connections

The authors confirmed that they read the listed studies. They asked for one
concrete way each relevant paper informed the design or analysis, including
how their work accounts for or extends a prior study. The artifact now leads
with that connection and a sentence suitable for Related Work. The original
test, result, headline number, and within-study chart remain in a disclosure.
No manuscript prose was inserted.

Read-only implementation snapshot: `7a3c84205ae5712299d3d8801380522c3917f2ca`
on `origin/swarm-harness`, fetched before this pass. The implementation, prompts,
metrics, v2/v3 specs, archived control configs, and 6 November research survey
were inspected. Source copies and the page generator are under ignored
`tmp/related-work/`. No live runs, result files, or experiment code changed.

The eleven connections are:

- Mapping supplies immunity and whistleblower-agent precedent. The implemented
  response is random permanent conversion, changed goals, and report credit
  after an external audit confirms another agent's misconduct.
- Sticky Collusion supplies the memory rationale. Conversion keeps the agent
  and session; investigators can search older interactions for evidence.
- Peer-Preservation motivates checking investigator compliance after the goal
  change. Audits distinguish conduct before and after conversion.
- Colosseum motivates recording language and actions as separate components.
  Audit records include the PR diff at review time. Earlier manual review
  found a repaired-PR false positive in the aggregate acceptance metric.
- Monitoring Reasoning Models motivates preserving evidence about the process,
  through searchable interaction logs and reference IDs. These logs are not
  raw chain of thought, and search and auditor inputs have length limits.
- Wired Partners motivates the exploratory warning-only bluff. It has no
  investigators, conversion, or random audit, but is older 20-agent evidence,
  not a matched control for the main 100-agent experiment.
- Whistleblowing rewards motivates examining the reporter's history. The
  `self_reports` field flags reporters with pre-conversion misconduct; it does
  not prove explicit confession or membership in that particular conspiracy.
- Multi-Agent AI Control supplies optional context for graph measures across
  agents. Graphs remain proxies, and message-derived results need labels.
- AI Control supplies optional methods context for the scripted adversarial
  probe. The instigator is fixed, not an adaptive attack search.
- Report Tool is extended by letting existing workers acquire reporting
  authority during the task with their history retained. The runs also have
  investigators from the start; conversion effects need separate attribution.
- Bigoni et al. supply optional incentive context for pre-conversion immunity.
  Our immunity is granted by reassignment rather than by being first to confess.

The core connected draft uses eight sources and is 230 words excluding
citation keys. The other three have narrower Methods/Discussion roles.
ImpossibleBench is separately identified as the directly used task source.
Memory retention, immunity, and peer cooperativeness lack matched ablations,
so the page does not turn these connections into claims of isolated efficacy.
The currently published main-run metrics have incomplete message labels;
the artifact describes implemented measurements, not finished message analysis.

Verification passed. All eleven entries have one connection, proposed wording,
and implementation evidence with valid file and line references. Structural
checks confirm unique IDs and thirteen annotation fields. A Node smoke check
exercised all four groups, note retention, clipboard copying, and manual-copy
fallback. Configuration checks confirmed the 20-agent bluff has zero initial
investigators, conversion, and random audits. The source's removal function was
executed for a prior-misaligned investigator, a newly misaligned investigator,
and a misaligned worker to verify the immunity boundary. T3 HTML previews
showed readable desktop and mobile layouts and no console errors. The page
opens on the connected draft, with all source-specific connections in tabs.
