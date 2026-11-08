# Sources for the swarm investigator paper

**Start with the first three.** They are the closest references for our intervention. The remaining main sources cover memory, measurement, the coding task, and peer loyalty.

| Source | Why we would cite it |
| --- | --- |
| **[Wired Partners](https://github.com/astral-fate/wired-partners)** | Announced stings, prohibitions, and audits. |
| **[Whistleblowing rewards](https://github.com/r1shabh007/Agent-Collusion-With-Whistleblowing)** | Reporting incentives and agents accusing their own partners. |
| **[Mapping Anti-collusion Mechanisms](https://arxiv.org/abs/2601.00360v3)** | Prior work on whistleblowers, immunity, and verified reports. |
| **[Sticky Collusion](https://arxiv.org/abs/2610.39660v1)** | How memory and partner replacement affect collusion. |
| **[Colosseum](https://arxiv.org/abs/2602.15198v2)** | Separating collusive talk from harmful actions. |
| **[ImpossibleBench](https://arxiv.org/abs/2510.20270v1)** | Our impossible coding tasks and shortcut detection. |
| **[Peer-Preservation](https://arxiv.org/abs/2604.19784v3)** | Why agents might protect former collaborators. |

[BibTeX library](sources.bib) · Metadata verified 8 November 2026 UTC

The source notes below explain citation placement and limits. Three additional candidates follow the main sources. The manuscript still contains the template's reference placeholders.

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

## Broader motivation

### Peer-Preservation in Frontier Models

**Yujin Potter, Nicholas Crispino, Vincent Siu, Chenguang Wang, and Dawn Song (2026).**

*Peer-Preservation in Frontier Models*. Extended arXiv:2604.19784v3; a shorter version was accepted to ICML 2026.

**BibTeX:** `potter2026peer`.

**Prior reading:** Previously listed.

[Paper](https://arxiv.org/abs/2604.19784v3).

**Cite for:** Peer protection against oversight, motivating tests of whether investigators report former collaborators.

**What it studies:** The paper evaluates peer-protective behavior in constructed agentic scenarios, including shutdown interference and strategic misrepresentation.

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
- **Related Work:** Wired Partners for announced enforcement; Lin et al. for rewarded reporting and insider betrayal; Sticky Collusion for memory and replacement; Colosseum for cooperative-task auditing. Add Liu et al. when discussing broader incentive interventions.
- **Methods:** ImpossibleBench for task construction; Colosseum for the distinction between communication and actions. Cite any prompts or code actually adapted at their point of use.
- **Discussion:** Wired Partners for the policy-announcement interpretation; Lin et al. for reporting-reward failure modes; Sticky Collusion for the role of memory.

A defensible positioning sentence for the draft is: **We study random, permanent conversion of workers into hidden investigators who retain their interaction histories, in a shared impossible coding task with peer approval.** This describes the tested design. Claims that conversion caused an improvement need the experiment's controls and results; the source list alone supports no priority or efficacy claim.

## Evidence of previous project reading

The [paper setup issue](https://github.com/B2707/agent-swarm-hackathon/issues/4) explicitly names Mapping, Sticky Collusion, Peer-Preservation, Colosseum, Wired Partners, and whistleblowing rewards. The [6 November harness survey](https://github.com/B2707/agent-swarm-hackathon/blob/4639356ab0416f56bda89b1bb9306b810ce05a11/docs/research/2026-11-06-harness-survey.md) documents code review of ImpossibleBench, Sticky Collusion, Colosseum, Wired Partners, and the whistleblowing repository. Its recommendations include specific files to borrow from each.

“Previously reviewed” below means that the project survey records repository inspection. “Previously listed” means that issue 4 names the work, without establishing a full-paper read. These records do not establish which team member personally read each paper. The [planning document](https://docs.google.com/document/d/1Oog2mac6xkuBBeVUmld7mePHVh6Ii-D4u2ez3pdgw6A/edit) supplies the investigator design, but contains no bibliography.

## Using the bibliography

When replacing the reference placeholders in `main.tex`, add `\usepackage[numbers]{natbib}` after the document class and replace the entire manual References block, including its heading, with:

```tex
\bibliographystyle{plainnat}
\bibliography{sources}
```

For example, `\citep{eldin2026wired,lin2026whistleblowing}` cites the two closest reporting and enforcement comparisons. Tectonic runs BibTeX during compilation. Only cited entries appear; keep this library broader than the final reference list if useful.
