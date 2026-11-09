# Local LaTeX paper

Open `paper/main.tex` in T3 Code's **Files** panel. This is the editable paper,
including the required **Limitations and Dual-Use / Ethical Considerations**
appendix. `output/pdf/main.pdf` is its compiled output.

## Edit, compile, and ask about a line

1. Edit `main.tex` directly in the Files panel. T3 autosaves changes to disk.
2. Open **Thread details → Project scripts → Recompile paper** and click Run.
   The action is already registered on this computer. It runs the existing
   local Tectonic installation, without Overleaf or an account.
3. Open **Files → output → pdf → main.pdf** to inspect the PDF in a file tab
   named `main.pdf`. If a browser tab at `127.0.0.1` shows **Not Found**, close
   that browser tab and open the file from Files again. Browser asset links
   expire; refreshing an expired address does not renew it. Recompiling still
   writes the PDF to the same local path.
4. Click a source line number, or drag across line numbers to select a range.
   Enter your request in **Comment**, then choose **Comment**. T3 adds a
   `main.tex L…` context chip to this chat's composer. Send the message when ready.
   This is local chat context; it does not post a GitHub review.

The line-comment flow was exercised in the installed T3 desktop app: selecting
the title line and choosing Comment created the expected composer chip. The
temporary check was removed without sending a message.

`t3.json` also contains both build actions so another checkout can import them
under **Settings → Code → Projects → Actions**. The second action,
**Recompile official template**, builds the reference edition.

## Start writing

- Set `\ApartTitle`, edit the author names and affiliations, and remove unused
  author rows. Each `\ApartAuthorRow` accepts two or three entries. Two entries
  produce two centered columns; use `{}` to keep an empty slot in a three-column row.
- Replace the abstract with 150–250 words. Remove the placeholder's
  `\linebreak` and `\uline` commands when writing your own abstract.
- Replace `\guidance{...}` with ordinary LaTeX paragraphs for upright body text.
  `\blankline` preserves the Doc's blank paragraphs; adjust these as you write.
- Uncomment `\ApartGuidancefalse` to remove the yellow instruction box.
- Use `\section{...}` for numbered sections and `\section*{...}` for unnumbered
  headings. Subsections, equations, figures, tables, labels, and citations use
  ordinary LaTeX. `graphicx`, `amsmath`, `booktabs`, and `hyperref` are loaded.
- Complete the required ethics appendix. Its guidance is a placeholder, not a
  statement about completed research.

## Terminal builds

From the repository root:

```sh
sh scripts/build-paper.sh           # output/pdf/main.pdf
sh scripts/build-paper.sh template  # output/pdf/template.pdf
LATEX_OFFLINE=1 sh scripts/build-paper.sh
```

Builds generally take about a second on this computer. The offline flag uses
only Tectonic's local cache; both editions were successfully built this way.
A first build on a new machine may download TeX packages into Tectonic's cache.
An unsuccessful compile preserves the previous good PDF and writes diagnostics
to `paper/build/main.log` (or `template.log`).

Old Standard TT Regular, Bold, and Italic are bundled in `fonts/` with their SIL
Open Font License. The yellow instruction box uses macOS's installed Arial.
Other machines without Arial use TeX Gyre Heros for that guidance box; remove
the box for submission. The paper's body fonts stay bundled and consistent.

## Research sources

[sources.md](sources.md) collects citation candidates, their relevance,
limits on what they support, and evidence of prior project review.
[sources.bib](sources.bib) contains verified citation metadata, including the
introduction's dated announcements and incident reports. `main.tex` uses
`\cite{citation-key}` and a BibTeX bibliography. Recompile paper updates both
citations and the References section, which lists only cited entries.

[The related-work plan](related-work-plan.html) reviews the author's eleven
prioritized sources, with verified results, headline numbers, and source notes.
It connects each paper to a concrete choice in the design or analysis.
[A text copy](related-work-plan.txt) includes the proposed section wording.

## Template source and layout check

The request is in [issue 4](https://github.com/B2707/agent-swarm-hackathon/issues/4),
which links to the production work in
[issue 3](https://github.com/B2707/agent-swarm-hackathon/issues/3).

The [official Google Doc](https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/edit)
and the user's copied Doc had identical document bodies when inspected on
November 8, 2026 UTC. `reference/google-doc.pdf` is the untouched PDF export of
that copy. `template.tex` builds the same content and omits the added ethics
appendix so its four pages can be compared directly with the official layout.
The working paper adds that appendix as a fifth page.

The check covers letter pages, 72-point margins, the title rules, six-author
grid, abstract, footnote, yellow instruction box, heading sizes and colors,
paragraph and list spacing, section order, and page breaks. Every page preserves
the reference's text. Rasterized pages were inspected for clipping and overlap.
Minor differences from Google's renderer remain in font shaping and underlines;
the output is a LaTeX reproduction, not an official publisher-supplied class.

Optional, reproducible inspection (PyMuPDF is needed only for this check):

```sh
python3 -m venv tmp/pdf-venv
tmp/pdf-venv/bin/pip install pymupdf
tmp/pdf-venv/bin/python scripts/check-paper-layout.py
```

This comparison is intended for the untouched template. After you start writing,
the text and page-break comparison will naturally differ from the reference.

The [sprint guidelines](https://apartresearch.com/sprints/swarm-alignment-2026)
request a PDF using the official template, at most eight pages before references
and appendices, plus the required ethics appendix. They do not explicitly
approve a LaTeX recreation. This setup matches the layout; organizer acceptance
of a recreated template remains unconfirmed.
