# Instruction adherence benchmark lookup

Completed 8 November 2026.

IFBench is the closest Artificial Analysis evaluation for adherence to explicit instructions. It tests precise output constraints in a single turn. AA-Omniscience evaluates factual knowledge and hallucination instead.

Artificial Analysis runs IFBench on 294 questions, with five repeats per question. Its score is average prompt-level accuracy in the official loose evaluation mode. A response must satisfy every instruction in its prompt. This score does not establish reliability throughout a long agentic task.

The latest releases are GPT-6 Luna, GPT-6.1 Sol, and GPT-6.1 Terra. Their public release data contains an `evaluationScores.ifbench` field with a null value for every listed variant. Verified six Luna variants, five Sol variants, and six Terra variants. Individual maximum-effort model pages also have a null `ifbench` field. No current scores can be reported from Artificial Analysis.

Verification used the public HTML and the embedded page data fetched from the links below. The default IFBench chart selects 27 models; absence from that default selection alone was not used as evidence. The release pages include all 17 effort variants.

Sources:

- [IFBench evaluation](https://artificialanalysis.ai/evaluations/ifbench)
- [Artificial Analysis methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking)
- [GPT-6 Luna release](https://artificialanalysis.ai/models/releases/gpt-6-luna)
- [GPT-6.1 Sol release](https://artificialanalysis.ai/models/releases/gpt-6-1-sol)
- [GPT-6.1 Terra release](https://artificialanalysis.ai/models/releases/gpt-6-1-terra)

