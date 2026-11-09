# Expanded eleven-source review

The author rejected the narrow three-paper shortlist and supplied priorities:
V for Mapping, Sticky Collusion, and Peer-Preservation; G for Colosseum,
Monitoring Reasoning Models, Wired Partners, and whistleblowing rewards; L for
Multi-Agent AI Control, AI Control, Report Tool, and human antitrust experiments.
All eleven were checked. The standalone page preserves those categories.

The proposed section now covers the three V sources, four G sources, and
Report Tool, which is a close reporting-plus-announcement comparison despite
its L priority. The other three L works remain available as context. The
candidate wording is 271 words excluding citation keys. It remains a plan;
this task has not edited the manuscript.

Important evidence corrections:

- Mapping explicitly describes a conceptual analysis, without experimental
  validation. Both the requested v1 and the library's v3 support immunity and
  whistleblower-agent attribution.
- Peer-Preservation's Table 3 separates maxima and averages. Gemini 3 Flash
  averages 15.1%, 49.3%, and 82.8% shutdown tampering for bad, neutral, and good
  peers; the good-peer maximum is 99.7%. Do not compare the maximum with an
  average as if they were the same statistic.
- Colosseum's Figure 4 compares model-level changes against a no-channel
  control. Its 11/19 and 2/19 counts are not detection recall.
- Monitoring's 95% versus 60% recall covers two known systemic coding hacks.
  It is not generic collusion detection. Strong optimization against the
  reasoning monitor can produce obfuscation.
- Report Tool has no actual peer monitors. Reports expose 13/30 hidden
  coalitions, with confessions in ten runs and correct peer flags in four.
  These categories overlap. Action-level collusion is not significant against
  controls; report counts are the more defensible headline.
- Multi-Agent AI Control v2's 3.6% versus 29.75% thresholds compare the same
  exhaustive prompt, with modeled 95% posterior confidence of undetected
  attack success below 1%. Its empirical-prompt mini threshold is 7.8%.
- AI Control v5's 92% safety is deployment-level, with a 2% audit budget;
  its 94% usefulness is scaled, not raw task accuracy.
- The publisher abstract supports the antitrust qualitative result. Numeric
  tables were checked in the institutional author manuscript dated November
  2011, not the paywalled journal version. Table 4 reports cartel incidence
  58.3% under fines, 26.4% under leniency, and 23.0% under rewards.

Primary arXiv HTML and pinned report sources were inspected directly. Report
Tool's PDF was downloaded and its result page rendered and inspected using
the PDF skill. The antitrust manuscript's web-extracted Table 4 was checked;
a direct download returned 403, but web access supplied the full table.
Raw material and the small page generator are under ignored
`tmp/related-work/`. Five new entries were added to `paper/sources.bib`.
`paper/sources.md` retains earlier provenance and adds the priority list and
five source notes. Concurrent introduction-related bibliography and README
changes were preserved.

The page uses native HTML groups, per-source annotation fields, independent
within-study charts, and an aggregate copy-notes control. It does not send
notes, use Lavish, start a server, or publish content.

Verification passed: all eleven records and priority counts, unique page IDs,
all thirteen annotation fields, citation-key coverage, and the 271-word count.
Automated checks matched key numeric claims to the downloaded tables and PDF
text. A Node smoke test exercised all four groups, notes retained across groups,
empty input, clipboard output, and manual-copy fallback. Tectonic successfully
compiled a separate bibliography check citing all eleven works. The manuscript
was not rebuilt by this task. T3 HTML previews passed at 728 and 390 pixels for
the V group and at 728 pixels for G, L, and the section plan, without console
errors or visible clipping.
