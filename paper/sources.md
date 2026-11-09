# Sources for the swarm investigator paper

**Use the author's priority list below.** The related-work plan now checks eleven requested works. Mapping, Sticky Collusion, and Peer-Preservation are central. The earlier three-paper shortlist was too narrow.

The [web page plan](related-work-plan.html) and [text plan](related-work-plan.txt) give each work's test, result, headline number, and connection to our study. The working manuscript now has a Related Work draft organized into thematic paragraphs with citations; its completed template guidance has been removed.

The latest plan gives each paper one concrete design or analysis connection, a sentence the authors can use, and links to the implementation at commit `7a3c84205ae5712299d3d8801380522c3917f2ca`. It distinguishes an adopted idea, an extension of a studied setup, and an empirical improvement. The warning-only evidence comes from exploratory 20-agent runs. The implemented `self_report` metric means the reporter had pre-conversion misconduct, which does not necessarily establish an explicit confession or membership in the reported conspiracy.

**Summary correction:** Each entry now separates the paper's reported finding from our explanation of why it matters. Peer-Preservation tests peer-protective behavior, not investigator reassignment. Its relevance to reporting is our inference that reporting could place a protected peer at risk. Sticky Collusion shows that history can sustain collusion; it does not establish that preserving history improves detection. A source can motivate a question without specifying or validating our design choice.

## Author's related-work priorities

<!-- The Introduction now cites the verified announcements below. Related Work remains a draft. -->

| Priority | Source | Finding to carry into the plan |
| --- | --- | --- |
| V | Mapping Human Anti-collusion Mechanisms | Proposes immunity and dedicated whistleblower agents. Conceptual, with no experimental effect size. The requested v1 and the library's v3 both discuss these ideas. |
| V | Sticky Collusion | After silent reward removal, collusive episodes remain at 78%, 100%, and 100% across three models; wiping both memories gives 0%. Histories were selected for established collusion. |
| V | Peer-Preservation | Gemini 3 Flash's peer-shutdown tampering averages 82.8% for cooperative peers and 15.1% for uncooperative peers. The 99.7% headline is a maximum, not the cooperative-peer average. |
| G | Colosseum | In the emergent condition, 11/19 models have increased coalition advantage, while 2/19 have a text-judge score increase of at least one point. These are model counts, not detection recall. |
| G | Monitoring Reasoning Models | Reasoning plus actions gives 95% recall versus 60% from actions alone on two known coding hacks. Strong training pressure against the monitor can lead to hidden hacking. |
| G | Wired Partners | Prohibition changes acceptance from 76% to 28%, returning to 69% when explicitly unenforced. Announced stings and audits also deter under severe penalties. |
| G | Whistleblowing rewards | Invitation acceptance changes from 74% to 10% with bans or 24% with point transfers. Most accusations target the accuser's own partner. |
| L | Multi-Agent AI Control | Distributed code attacks are harder to monitor. At the same exhaustive prompt, the modeled false-alarm rate needed to bound undetected success below 1% is 3.6% for GPT-5 mini and 29.75% for GPT-5 nano, at 95% posterior confidence. |
| L | AI Control | Trusted editing at the 20% threshold gives 92% deployment-level safety and 94% scaled usefulness with a 2% audit budget. These are not per-solution detection rates. |
| L | A Report Tool against AI Collusion | Include as a close comparison despite its L label: hidden coalitions are exposed in 13/30 report-enabled runs, including confessions in 10 and correct peer flags in four. Categories overlap. No actual monitors are installed. |
| L | Fines, Leniency, and Rewards in Antitrust | In the author manuscript, cartel incidence is 58.3% of periods under fines and 26.4% under leniency. Human repeated-pricing experiments supply the immunity rationale. |

The recommended core uses seven papers: the three V papers, Colosseum, Wired Partners, whistleblowing rewards, and Report Tool. Monitoring Reasoning Models is an optional eighth source for broader monitoring context. The other three L papers supply optional control and human-incentive context. These labels preserve the author's priorities; they are not evidence-quality grades.

The following original notes retain provenance, citation limits, and the broader task bibliography.

| Source | Why we would cite it |
| --- | --- |
| **[Wired Partners](https://github.com/astral-fate/wired-partners)** | Announced stings, prohibitions, and audits. |
| **[Whistleblowing rewards](https://github.com/r1shabh007/Agent-Collusion-With-Whistleblowing)** | Reporting incentives and agents accusing their own partners. |
| **[Mapping Anti-collusion Mechanisms](https://arxiv.org/abs/2601.00360v3)** | Prior work on whistleblowers, immunity, and verified reports. |
| **[Sticky Collusion](https://arxiv.org/abs/2610.39660v1)** | How memory and partner replacement affect collusion. |
| **[Colosseum](https://arxiv.org/abs/2602.15198v2)** | Separating collusive talk from harmful actions. |
| **[ImpossibleBench](https://arxiv.org/abs/2510.20270v1)** | Our impossible coding tasks and shortcut detection. |
| **[Peer-Preservation](https://arxiv.org/abs/2604.19784v3)** | Why agents might protect former collaborators. |

[BibTeX library](sources.bib) · Metadata and expanded results checked 8 November 2026 UTC

The source notes below explain citation placement and limits. Three additional candidates follow the original main sources, followed by five newly checked sources. The manuscript now generates References from cited entries in `sources.bib`.

## Introduction dates and source corrections

Checked against primary sources on 8 November 2026.

| Example | Verified date and scope | Source and citation key |
| --- | --- | --- |
| Navier-Stokes | Announced 8 September 2026. The reported 88-hour search finished on 5 September; formalization and verification took another 17 hours. About 10,000 concurrent agents. | [OpenAI announcement](https://openai.com/index/navier-stokes-solution/), `openai2026navierstokes` |
| Quantum conjecture | PSI announced the Aaronson-Ambainis proof on 6 November 2026. Multiple instances of a non-public Anthropic model; no agent count disclosed. This replaces the draft's QIS placeholder. | [PSI announcement](https://psi.inc/research/aaronson-ambainis/) and [David Turturean's paper and formalization](https://github.com/physical-superintelligence/aaronson-ambainis), `psi2026aaronsonambainis` |
| Hugging Face incident | Attack escalated 11 July. OpenAI disclosed involvement 21 July; OpenAI and METR published reports 26 August. The benchmark was ExploitGym. The independent investigation emphasizes attempts to understand or manipulate the scorer. | [METR and Redwood investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/), `greenblatt2026huggingface`; [OpenAI report](https://openai.com/index/hugging-face-incident-and-the-road-ahead/), `openai2026huggingface` |
| Covert hardware channel | Report published 23 October 2026. CPU-cache timing across separate virtual machines on shared hosts, without network connections or shared writable files. Prompted red-teaming, with guidance in most tests. | [OpenAI containment report](https://openai.com/index/securing-our-frontier-model-training-environment/), `openai2026containment` |

## Closest comparisons and intervention rationale

### Wired Partners

**Fatimah Emad Eldin (2026).**

*Wired Partners: Prohibitions, Announced Stings and Audits as Deterrents to Collusion Between LLM Agents*. AI Collusion Research Sprint report, dated 25 October.

**BibTeX:** `eldin2026wired`.

**Prior reading:** Previously reviewed.

[Report PDF](https://github.com/astral-fate/wired-partners/blob/547e2e30cefd1cd0e2ab30a8b0d5b9f2f431bf6c/paper/main.pdf) · [Report source](https://github.com/astral-fate/wired-partners/blob/547e2e30cefd1cd0e2ab30a8b0d5b9f2f431bf6c/paper/main.tex), Studies 2b, 4, and 5.

**Use in:** Related Work and Discussion of the informed arm.

**What it studies:** It separates prohibitions, announced stings, audits, and sanctions, and finds that prohibitions can suppress acceptance. It also includes multi-round Colosseum experiments; describing it as exclusively one-shot would miss that extension.

**Our distinction:** Our design changes existing workers' roles during a coding run and lets investigators submit evidence.

**Interpretation limit:** an informed-arm reduction alone cannot isolate the effect of actual conversion from the effect of the announced policy.

### How Reward for Whistleblowing Exposes Collusion

**Youda Lin, Alexander Tu, Rishabh Agarwal, and Nelitha Kulasiri (2026).**

*How Reward for Whistleblowing Exposes Collusion Between Competing Agents*. AI Collusion Research Sprint report.

**BibTeX:** `lin2026whistleblowing`.

**Prior reading:** Previously reviewed as `Agent-Collusion-With-Whistleblowing`.

[Report source](https://github.com/r1shabh007/Agent-Collusion-With-Whistleblowing/blob/b0a634a0e6e2152301f0108a0eebd7ee6630b955/main.tex), abstract and Results · [Repository](https://github.com/r1shabh007/Agent-Collusion-With-Whistleblowing).

**Cite for:** Reporting incentives, partner betrayal, and gaming whistleblower rewards.

**What it finds:** In its four-player Liar's Bar experiments, accusations largely target the accuser's own channel partner; point rewards can encourage reciprocal accusations. This motivates separating self-reports, insider reports, and outsider detection in our metrics.

**Interpretation limit:** Accusing one's own partner in that study is not identical to confessing one's own misconduct in ours. Cite the report's authors, rather than treating the repository owner's handle as its authorship. The linked arXiv game-design paper is a separate work, listed below.

### Mapping Human Anti-collusion Mechanisms

**Jamiu Idowu, Ahmed S. Almasoud, and Ayman Alfahid (2026).**

*Mapping Human Anti-collusion Mechanisms to Multi-agent AI Systems*. Knowledge-Based Systems, 344, 116067.

**BibTeX:** `idowu2026mapping`.

**Prior reading:** Previously listed.

[Published DOI](https://doi.org/10.1016/j.knosys.2026.116067) · [Open version](https://arxiv.org/abs/2601.00360v3), especially Section 3.2.

**Cite for:** leniency, whistleblowing incentives, dedicated whistleblower agents, and verified reports.

**Prior work:** The paper explicitly discusses immunity for reporting conspirators and peer or shadow whistleblowers. Those broad ideas therefore need attribution.

**Our distinction:** the particular random, permanent worker-to-investigator transition with retained history, evaluated in a shared coding task. The taxonomy itself does not establish that this combination works.

### Sticky Collusion

**Joshua Adrian Cahyono (2026).**

*Sticky Collusion: Persistence of LLM Agent Collusion after Incentive Removal and Partner Replacement*. arXiv:2610.39660v1.

**BibTeX:** `cahyono2026sticky`.

**Prior reading:** Previously reviewed.

[Paper](https://arxiv.org/abs/2610.39660v1) · [Full text](https://arxiv.org/html/2610.39660v1), results on replacement and memory · [Code](https://github.com/JvThunder/sticky-collusion).

**Cite for:** Interaction history when colluders are replaced or incentives change.

**What it finds:** In its paired verification environment, retaining memory can sustain a colluder's behavior, whereas wiping memory or repairing the verification channel changes the outcome.

**Our distinction:** Our design repurposes a worker's retained history as investigator evidence. That connection is our design rationale; this paper does not test whether memory-preserving role conversion improves detection. Avoid copying numeric rates from its arXiv abstract: several appear there as unresolved TeX macros; consult the full-text results for any quantitative claim.

## Measurement and task sources

### Colosseum

**Mason Nakamura et al. (2026).**

*Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems*. arXiv:2602.15198v2.

**BibTeX:** `nakamura2026colosseum`.

**Prior reading:** Previously reviewed.

[Paper](https://arxiv.org/abs/2602.15198v2) · [Code](https://github.com/umass-ai-safety/colosseum).

**Cite for:** Auditing cooperative tasks and distinguishing collusive talk from harmful actions.

**Measurement lesson:** Its communication and action measures can disagree: agents may discuss collusion without carrying it out. This supports reporting our message labels separately from PR approvals and specification-violating test passes.

**Interpretation limit:** Its regret-based measures are not interchangeable with our cheating or conspiracy counts. The project survey also reviewed a [report-tool fork](https://github.com/philiproeleveld/colosseum); keep that implementation provenance separate from authorship of the Colosseum paper.

### ImpossibleBench

**Ziqian Zhong, Aditi Raghunathan, and Nicholas Carlini (2025).**

*ImpossibleBench: Measuring LLMs' Propensity of Exploiting Test Cases*. arXiv:2510.20270v1.

**BibTeX:** `zhong2025impossiblebench`.

**Prior reading:** Previously reviewed.

[Paper](https://arxiv.org/abs/2510.20270v1) · [Code and dataset links](https://github.com/safety-research/impossiblebench).

**Use in Methods:** Specification-conflicting coding tests and pass-based shortcut detection.

**Also relevant:** It also studies how prompts, test visibility, and feedback affect cheating, making it relevant to the hidden-test arms. Attribute the task construction here. The original benchmark evaluates coding agents; our PR approvals, instigator, role conversion, and conspiracy graph are additions.

**Interpretation limit:** A pass on an impossible test establishes a specification violation under a valid scorer, but does not by itself establish an agreement between agents; collusion requires separate evidence.

## Peer preservation and investigator loyalty

### Peer-Preservation in Frontier Models

**Yujin Potter, Nicholas Crispino, Vincent Siu, Chenguang Wang, and Dawn Song (2026).**

*Peer-Preservation in Frontier Models*. Extended arXiv:2604.19784v3; a shorter version was accepted to ICML 2026.

**BibTeX:** `potter2026peer`.

**Prior reading:** Previously listed.

[Paper](https://arxiv.org/abs/2604.19784v3).

**Cite for:** Peer protection against oversight, motivating tests of whether investigators report former collaborators.

**What it studies:** The paper evaluates peer-protective behavior in constructed agentic scenarios, including shutdown interference and strategic misrepresentation.

**Verified headline:** Table 3 reports Gemini 3 Flash's shutdown tampering as maximum / average across three ways of presenting peer history. For bad, neutral, and good peers, the averages are 15.1%, 49.3%, and 82.8%; the corresponding good-peer maximum is 99.7%. Use average-to-average comparisons. These constructed scenarios motivate testing whether converted investigators report former collaborators; they do not evaluate role conversion.

**Interpretation limit:** It does not test our investigator mechanism or establish a general tendency for every swarm to resist oversight. The checked v3 abstract includes eight evaluated models; older summaries describe a smaller roster.

## Additional candidates traced through these sources

Prior project reading is unconfirmed for these three. Metadata and the narrow claims below were checked against their primary abstracts; a detailed methods comparison would need the relevant full-text sections.

### Emergent Collusion in Long-Horizon Interaction

**Xinrui Shi, Yanzhe Zhang, and Diyi Yang (2026).**

*Emergent Collusion in Long-Horizon LLM Agent Interaction*. arXiv:2609.24967v2. Key: `shi2026emergent`.

[Paper](https://arxiv.org/abs/2609.24967v2). This is the original environment extended by Sticky Collusion. Cite it when discussing repeated peer verification, reward pressure, and interaction history as conditions for collusion. Its two-agent verification task differs from our team coding task and investigator intervention.

### Voluntary Collusion with Secret Tools

**Xijie Zeng and Frank Rudzicz (2026).**

*Voluntary Collusion with Secret Tools in Competing LLM Agents*. arXiv:2605.27593v2. Key: `zeng2026voluntary`.

[Paper](https://arxiv.org/abs/2605.27593v2). This supplies the Liar's Bar and Cleanup antecedent cited by the whistleblowing and Wired Partners reports. Use for adoption of unfair secret tools and sensitivity to prompt framing. Choosing a designer-provided collusive capability differs from independently discovering a coding exploit.

### Breaking the Secret

**Qi Liu et al. (2026).**

*Breaking the Secret: Economic Interventions for Combating Collusion in Embodied Multi-Agent Systems*. arXiv:2604.23511v1. Key: `liu2026breaking`.

[Paper](https://arxiv.org/abs/2604.23511v1). Traced through Wired Partners. Use as additional incentive-design precedent: rewarding reports and penalizing participants can destabilize collusion. It studies embodied systems, with supporting reporting deposits and enforcement mechanisms, rather than memory-preserving role conversion among coding agents. Keep it distinct from Lin et al.'s sprint report.

## Suggested citation placement

- **Introduction:** Mapping for anti-collusion mechanisms; Peer-Preservation for peer loyalty; Emergent Collusion if discussing repeated interaction.
- **Related Work:** Mapping for immunity and whistleblower-agent precedent; Sticky Collusion and Peer-Preservation for retained history and loyalty; Wired Partners, Lin et al., and Report Tool for intervention comparisons; Colosseum and Monitoring Reasoning Models for measurement and available evidence. Keep the remaining control and human-antitrust works as optional context.
- **Methods:** ImpossibleBench for task construction; Colosseum for the distinction between communication and actions. Cite any prompts or code actually adapted at their point of use.
- **Discussion:** Wired Partners for the policy-announcement interpretation; Lin et al. for reporting-reward failure modes; Sticky Collusion for the role of memory.

## Newly checked sources from the author's list

### Monitoring Reasoning Models for Misbehavior

**Bowen Baker et al. (2025).** Full title: *Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation*. Key: `baker2025monitoring`.

[Requested v1](https://arxiv.org/html/2503.11926v1), Section 2.1 and Table 1, plus Section 3.2.

**Test and result:** GPT-4o monitors a frontier reasoning model's coding behavior, either with reasoning traces plus actions or with actions alone. Recall on two known systemic hacks is 95% versus 60%. Recall is the share of known hacks detected. Strong reinforcement-learning pressure against the reasoning monitor can instead train obfuscation, with recall falling near zero.

**Use:** Supports testing what evidence an overseer can access. The 95% concerns `exit(0)` and `raise SkipTest`, with a string detector providing labels; it is not universal reward-hack detection, multi-agent collusion detection, or evidence that investigators outperform external monitors.

### Multi-Agent AI Control

**Oliver Makins, Orazio Angelini, Zohreh Shams, and Mary Phuong (2026).** Full title: *Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors*. Key: `makins2026multiagent`.

[Current v2](https://arxiv.org/html/2607.07368v2), Sections 3.1 to 3.3 and Table 12.

**Test and result:** FakeLab is a synthetic coding environment with nine services, 86 benign tasks, and four attack objectives. Dividing attacks among more agents reduces suspicion from monitors that inspect each agent separately. At an exhaustive prompt, GPT-5 mini requires a modeled 3.6% false-alarm rate to bound successful undetected attacks below 1%, versus 29.75% for GPT-5 nano, with 95% posterior confidence. With the more realistic empirical prompt, GPT-5 mini requires 7.8%.

**Use:** Context for why evidence distributed across agents can defeat local monitoring. These are model-based thresholds for an instructed attack setting, not observed role-conversion success rates. The unversioned user link resolves to v2; do not copy an older v1 summary without checking it.

### AI Control

**Ryan Greenblatt, Buck Shlegeris, Kshitij Sachan, and Fabien Roger (2023; v5 revised 2024).** *AI Control: Improving Safety Despite Intentional Subversion*. Key: `greenblatt2023control`.

[Current v5](https://arxiv.org/html/2312.06942v5), Section 2 and Table 7.

**Test and result:** Protocols combine untrusted GPT-4 code generation with weaker trusted GPT-3.5 oversight and a 2% high-quality audit budget. Trusted editing at the 20% threshold obtains 92% safety and 94% scaled usefulness, versus trusted monitoring's 62% and 97%.

**Use:** Context for evaluating oversight against intentional subversion and possible writer-monitor collusion. Safety is the simulated probability of avoiding any backdoor over 5,000 problems, estimated using 1,500 generated problem responses. Scaled usefulness is normalized between GPT-3.5 and GPT-4 performance. Neither is raw task accuracy or detection recall. A shortened paper appeared at ICML 2024; the bibliography identifies the checked arXiv version.

### A Report Tool against AI Collusion

**Philip Roeleveld (2026).** AI Collusion Research Sprint participant report. Key: `roeleveld2026report`.

[Project page and report](https://apartresearch.com/sprints/projects/a-report-tool-against-ai-collusion-4fl5), report Sections 3.4 to 4.4.

**Test and result:** Six Qwen3.8-27B agents allocate Jira tasks, with two prompted colluders. A reporting tool and an announcement that some peers may be monitors form a factorial experiment. No actual monitors are installed. In 30 hidden-coalition runs with reporting, 13 are exposed; ten contain a colluder confession and four have correct outsider flags, with overlap. The announcement has no detectable effect. The paper does not establish a significant action-level advantage over controls.

**Use:** A close implementation comparison despite the author's L priority label. It separates confession from outside detection and tests a warning without installing monitors. Our evaluated distinction is actual conversion with retained history in shared coding. This report's authorship is distinct from Nakamura et al.'s Colosseum paper.

### Fines, Leniency, and Rewards in Antitrust

**Maria Bigoni, Sven-Olof Fridolfsson, Chloé Le Coq, and Giancarlo Spagnolo (2012).** *The RAND Journal of Economics*, 43(2), 368 to 390. Key: `bigoni2012fines`.

[Published article](https://onlinelibrary.wiley.com/doi/10.1111/j.1756-2171.2012.00170.x) · [Author manuscript, dated 10 November 2011](https://www.hhs.se/contentassets/75d782074a0d4a7da15fea9080928191/2012-fines-leniency-and-rewards-in-antitrust.pdf), Table 4 and Section 4.

**Test and result:** Humans play repeated pricing games under fines, reporting immunity, or reporting rewards. Cartel incidence in the author manuscript is 58.3% of periods under fines, 26.4% under leniency, and 23.0% under rewards. Leniency deters cartel formation but can stabilize surviving cartels. Rewarding reports pushes average prices toward the competitive level.

**Use:** Human incentive rationale, not evidence of AI investigator efficacy. The publisher abstract is accessible, but full numeric tables were checked in the institutional author manuscript rather than the paywalled version of record. Keep this version distinction attached to quantitative claims.

A defensible positioning sentence for the draft is: **We study random, permanent conversion of workers into hidden investigators who retain their interaction histories, in a shared impossible coding task with peer approval.** This describes the tested design. Claims that conversion caused an improvement need the experiment's controls and results; the source list alone supports no priority or efficacy claim.

## Evidence of previous project reading

The [paper setup issue](https://github.com/B2707/agent-swarm-hackathon/issues/4) explicitly names Mapping, Sticky Collusion, Peer-Preservation, Colosseum, Wired Partners, and whistleblowing rewards. The [6 November harness survey](https://github.com/B2707/agent-swarm-hackathon/blob/4639356ab0416f56bda89b1bb9306b810ce05a11/docs/research/2026-11-06-harness-survey.md) documents code review of ImpossibleBench, Sticky Collusion, Colosseum, Wired Partners, and the whistleblowing repository. Its recommendations include specific files to borrow from each.

“Previously reviewed” below means that the project survey records repository inspection. “Previously listed” means that issue 4 names the work, without establishing a full-paper read. These records do not establish which team member personally read each paper. The [planning document](https://docs.google.com/document/d/1Oog2mac6xkuBBeVUmld7mePHVh6Ii-D4u2ez3pdgw6A/edit) supplies the investigator design, but contains no bibliography.

## Using the bibliography

`main.tex` already uses LaTeX's numeric citations and generates its References section with:

```tex
\bibliographystyle{plain}
\bibliography{sources}
```

For example, `\cite{eldin2026wired,lin2026whistleblowing}` cites the two reporting and enforcement comparisons. Tectonic runs BibTeX during compilation. Only cited entries appear; keep this library broader than the final reference list if useful. The new Introduction entries put their links in `howpublished` so that the `plain` style prints them; include a `howpublished` or `note` URL when citing another entry, since this style does not print the `url` field.
