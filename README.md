# Charter Party Document Parser

Marcura AI Engineer challenge — extract legal clauses from a 39-page voyage charter party PDF into structured JSON, with strike-through edits filtered out.

The original assignment is preserved verbatim at [`docs/task.md`](docs/task.md).

## Quick start

```bash
make install            # uv sync + install pre-commit hook
cp .env.example .env    # only needed for `make run_verify` (Azure LLM)
make run                # extract → output/clauses.json + output/clauses.html
make eval               # deterministic correctness check vs golden file
make test               # unit tests
```

The deliverable is [`output/clauses.json`](output/clauses.json). A browseable [`output/clauses.html`](output/clauses.html) view is also produced. Open [`docs/site/index.html`](docs/site/index.html) for the architecture write-up.

## Approach in one paragraph

A deterministic PyMuPDF parser does the heavy lifting: it walks each page character-by-character with bounding boxes, intersects them with the thin rectangles that encode strike-through, splits Part II into its three numbering ranges (SHELLVOY 5 / Shell Additional Clauses / Essar Rider Clauses), and assembles `(id, title, text)` candidates whose every word can be traced back to a glyph on the source page. An optional Azure-hosted LLM verifier reviews the candidates as HTML-tagged structured input and logs suspicious boundaries — but never rewrites text. See [`docs/architecture.md`](docs/architecture.md) for the full pipeline.

## Documentation

The `docs/` folder is the project's source of truth.

- [`docs/README.md`](docs/README.md) — index and dual-format philosophy
- [`docs/architecture.md`](docs/architecture.md) — pipeline, sections, LLM role, eval
- [`docs/glossary.md`](docs/glossary.md) — maritime + technical terms
- [`docs/development.md`](docs/development.md) — setup, commands, CI
- [`docs/site/index.html`](docs/site/index.html) — hand-crafted single-file showcase

## Working agreement

Coding conventions for any contributor (human or AI) live in three parity files: [`CLAUDE.md`](CLAUDE.md) (Claude Code), [`AGENTS.md`](AGENTS.md) (Codex), [`.cursorrules`](.cursorrules) (Antigravity, Cursor).
