# Building the paper

`main.tex` is the paper. `apart.cls` recreates the sprint's official template in
LaTeX, and `template.tex` builds the unmodified template for comparison.

## Build

You need [Tectonic](https://tectonic-typesetting.github.io/). On macOS:
`brew install tectonic`.

```sh
make paper                          # writes output/pdf/main.pdf
sh scripts/build-paper.sh template  # writes output/pdf/template.pdf
LATEX_OFFLINE=1 make paper          # use only Tectonic's local cache
```

A build takes about a second once Tectonic has its cache. The first build on a
new machine downloads TeX packages into that cache. A failed compile keeps the
last good PDF and writes diagnostics to `paper/build/main.log`. Set
`TECTONIC_BIN` if Tectonic is not on your `PATH`.

## Writing in it

- Set `\ApartTitle`, then edit the author rows. Each `\ApartAuthorRow` takes two
  or three entries. Use `{}` to leave a slot empty in a three-column row.
- The abstract must be 150 to 250 words. Remove the placeholder's `\linebreak`
  and `\uline` commands when you replace it.
- Replace each `\guidance{...}` block with ordinary LaTeX paragraphs. A
  `\guidance` block is template instruction text, not a statement about this
  research, so none may survive into the submitted PDF.
- Uncomment `\ApartGuidancefalse` to hide the yellow instruction box.
- `graphicx`, `amsmath`, `booktabs` and `hyperref` are loaded. Sections,
  figures, tables, labels and citations work as usual.
- The ethics appendix is required and must be written, not left as guidance.

## Fonts

Old Standard TT Regular, Bold and Italic are bundled in `fonts/` under the SIL
Open Font License (`fonts/OFL.txt`). The yellow instruction box uses Arial where
it is installed and TeX Gyre Heros elsewhere. That box is removed for
submission, so the difference does not reach the final PDF.

## Sources

`sources.md` lists the citation candidates with their relevance and the limits
on what each one supports. `sources.bib` holds the verified metadata. `main.tex`
cites with `\cite{key}`, and the References section lists only cited entries.

## Template caveat

The [sprint guidelines](https://apartresearch.com/sprints/swarm-alignment-2026)
ask for a PDF in the official template, at most eight pages before references
and appendices, plus the ethics appendix. `apart.cls` matches that layout at
letter size with 72 point margins, the title rules, the author grid, the
abstract and footnote, and the heading sizes and colours. It is a LaTeX
reproduction rather than a publisher-supplied class, and font shaping and
underlines still differ slightly from Google's renderer. The organisers have not
confirmed that a recreated template is acceptable.
