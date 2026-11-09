# Neuron to Graph research

Researched 8 November 2026. The user asked what Neuron to Graph is and how it connects to a previous sprint. No matching reference appeared in a local text search. Public primary sources identify the project as Neuron to Graph, also called N2G or Neuron2Graph.

N2G builds a readable representation of the text patterns that activate an individual language-model neuron. It starts with strongly activating examples, removes unnecessary context, measures which text pieces matter, and tests substitutions proposed by DistilBERT. It stores the resulting patterns in a branching search structure and produces a simplified graph for people to inspect. The structure can also predict activations on new text, allowing researchers to check its predictions against the actual neuron's responses. The graph's nodes represent text pieces and activation conditions.

The original sprint connection is Alex Foote's project, "Investigating Neuron Behaviour via Dataset Example Pruning and Local Search," listed among the winners of Apart's November 2022 interpretability hackathon. The later N2G project develops the same pruning and example-diversification approach into graph representations. The repository identifies a short paper accepted at the RTML workshop at ICLR 2023 and a longer May 2023 preprint. This establishes a public historical connection; the particular sprint reference the user saw was not supplied.

The longer paper evaluates a six-layer SoLU language model, which uses a neuron design intended to make neurons easier to interpret. It reports approximately 48 hours to generate graphs for every neuron on one Tesla T4 GPU. Its evaluation uses the top 20 activating examples per neuron, split into 10 training and 10 test examples. This evidence supports a method for approximating individual neuron responses within that experimental setting. The authors identify complex neuron behaviour, limited example coverage, and neurons responding to multiple unrelated patterns as limitations. Their case studies include programming import syntax and repeated text sequences. These graphs alone do not establish the causal effect of a neuron on a model's final answer.

Primary sources:

- [Official project page](https://n2g.apartresearch.com/).
- [Apart's November 2022 hackathon results](https://apartresearch.com/news/results-from-the-interpretability-hackathon).
- [Longer May 2023 paper](https://arxiv.org/abs/2305.19911), especially sections 3, 4.1, and 5 of the [PDF](https://arxiv.org/pdf/2305.19911).
- [Short April 2023 paper](https://arxiv.org/abs/2304.12918).
- [Official repository and examples](https://github.com/apartresearch/Neuron2Graph).

Checks consisted of reading the official project page, original hackathon results, paper methodology and limitations, and repository README. This was a literature lookup; the code was not executed. A search result for an Apart fundraising testimonial mentioned the project's origin, but its current URL redirects to the contact page. Use the accessible original hackathon results for provenance.
