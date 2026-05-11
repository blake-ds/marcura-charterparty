# Documentation

The original Marcura assignment is preserved verbatim at [`task.md`](task.md).

## Approach

A deterministic PyMuPDF parser does the heavy lifting: it walks each page character-by-character with bounding boxes, intersects them with the thin rectangles that encode strike-through, splits Part II into its three numbering ranges (SHELLVOY 5 / Shell Additional Clauses / Essar Rider Clauses), and assembles `(id, title, text)` candidates whose every word can be traced back to a glyph on the source page. An optional Azure-hosted LLM verifier reviews the candidates as HTML-tagged structured input and logs suspicious boundaries — but never rewrites text.

## Index

| Page | What it covers |
|------|----------------|
| [`site/index.html`](site/index.html) | **Hand-crafted single-file visual showcase — the one-shot view** |
| [`architecture.md`](architecture.md) | Full pipeline write-up: strike-through removal, sections, LLM verifier, eval |
| [`development.md`](development.md) | Setup, commands, CI |
| [`task.md`](task.md) | Original Marcura assignment (verbatim) |

Markdown is the canonical source of truth; the HTML page is a hand-crafted snapshot for the human reviewer.
