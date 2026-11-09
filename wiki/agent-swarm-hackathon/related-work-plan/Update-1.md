# Related-work planning

The user asked for the closest work in `paper/sources.md`, organized as what
each work tested, its result, and its headline number. The template requires
both a closest-work comparison and an explanation of our design's difference.
The user explicitly requested a web page artifact without the Lavish skill.

The core shortlist is Wired Partners, Lin et al.'s whistleblowing report, and
Sticky Collusion. Mapping supplies attribution for immunity and dedicated
whistleblower agents but has no experimental headline to invent. Liu et al.
is an optional fourth comparison about financial reporting incentives.

Verification used pinned report sources, Wired Partners' generated
`paper/numbers.tex`, and the full arXiv HTML results tables. Raw downloads are
in ignored `tmp/related-work/`. Wired's main source contains numeric macros;
the generated file resolves Study 4's values to 152/200, 56/200, and 138/200.
Lin's Table 1 distinguishes invitation acceptance from offers and accusations.
Sticky's figures are episode rates after selecting histories in which collusion
already formed, not population-level emergence or detection rates.

Deliverables are `paper/related-work-plan.txt` and
`paper/related-work-plan.html`. No Lavish service or CLI session,
server, public hosting, manuscript edits, or external writes are involved.

The web page has linked source entries, independent within-study charts,
candidate section wording, a fourth optional comparison, citation-placement
notes, and a local annotation form. The form generates notes for pasting into
chat and does not transmit them. It uses the existing repository artifact's
theme conventions and native HTML controls.

Verification passed. T3 HTML previews at 728 and 390 pixels showed readable
layouts without console errors. A runnable Node smoke check exercised note
creation, appending, blank-input handling, clipboard success, and manual-copy
fallback. Structural checks confirmed unique IDs, arXiv section/table anchors,
and existing bibliography keys. The candidate section is 247 words excluding
citation keys. The finished page was displayed inline with `html_render`.
