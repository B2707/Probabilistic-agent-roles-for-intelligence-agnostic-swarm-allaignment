#!/usr/bin/env python3
"""Check the untouched LaTeX template against the frozen Google Docs export.

Requires PyMuPDF only for inspection; ordinary compilation needs only Tectonic.
Writes page PNGs and a JSON record to tmp/pdfs/layout-check/ for visual review.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "paper/reference/google-doc.pdf"
CANDIDATE = ROOT / "output/pdf/template.pdf"
OUTPUT = ROOT / "tmp/pdfs/layout-check"


def tokens(page: pymupdf.Page) -> list[str]:
    # Ignore PDF extraction's zero-width list separators and punctuation spacing.
    return re.findall(r"\w+", page.get_text().replace("\u200b", "").lower())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    reference = pymupdf.open(REFERENCE)
    candidate = pymupdf.open(CANDIDATE)
    if len(reference) != len(candidate):
        raise SystemExit(f"Page count differs: {len(reference)} vs {len(candidate)}")
    pages = []
    for index, (original, result) in enumerate(zip(reference, candidate), 1):
        original_tokens, result_tokens = tokens(original), tokens(result)
        size_matches = tuple(original.rect) == tuple(result.rect)
        text_matches = original_tokens == result_tokens
        for prefix, page in (("reference", original), ("latex", result)):
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
                OUTPUT / f"{prefix}-{index}.png"
            )
        pages.append({
            "page": index,
            "size_points": list(result.rect)[2:],
            "size_matches": size_matches,
            "text_and_page_break_matches": text_matches,
            "reference_tokens": len(original_tokens),
            "latex_tokens": len(result_tokens),
        })
    report = {
        "reference_sha256": sha256(REFERENCE),
        "latex_sha256": sha256(CANDIDATE),
        "pages": pages,
        "note": "Text/page-size checks supplement visual review; they do not prove pixel identity.",
    }
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not all(p["size_matches"] and p["text_and_page_break_matches"] for p in pages):
        raise SystemExit("Template differs from reference. Inspect the rendered pages.")
    print(f"All {len(pages)} pages preserve the reference text and page sizes. PNGs: {OUTPUT}")


if __name__ == "__main__":
    main()
