# Introduction dates and references

Completed 8 November 2026. The user requested missing dates, internet verification of the introduction's references, and corrections.

The dated evidence and direct primary-source links are in [the source notes](../../../paper/sources.md#introduction-dates-and-source-corrections). Five entries were added to [sources.bib](../../../paper/sources.bib), preserving the existing related-work library.

The introduction in [main.tex](../../../paper/main.tex) now names PSI's Aaronson-Ambainis conjecture, ExploitGym, and CPU-cache communication. It distinguishes attack, disclosure, and report dates. The incident's motivation follows the independent investigation. The hardware example identifies the prompted red-teaming setting. PSI's sources do not disclose an agent count, so the text uses multiple model instances. Typographical errors were corrected. The abstract and its quantified result placeholders were preserved.

The manuscript now generates its numeric citations and References section through BibTeX. Tectonic's `plain` style prints the five entries' links through `howpublished`. The README and source notes describe this setup.

## Verification

`sh scripts/build-paper.sh` passed. `LATEX_OFFLINE=1 sh scripts/build-paper.sh` also passed after caching the bibliography style. The resulting [main.pdf](../../../output/pdf/main.pdf) has seven pages. Citations resolve and all five source URLs are PDF link annotations. Rendered pages 3, 5, and 6 were visually inspected. The introduction and bibliography have no clipping or overlap. A literal double-hyphen rendering from the class's disabled ligatures was fixed in the two mathematical names before the final build.

No experiment numbers were filled. Contribution items and other sections remain drafts. Existing files were being edited by another thread during the work; edits were limited to the relevant paragraphs and bibliography additions.
