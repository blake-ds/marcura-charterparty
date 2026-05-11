# Charter Party Document Parser

Marcura AI Engineer challenge — extract legal clauses from a 39-page voyage charter party PDF into structured JSON, with strike-through edits filtered out.

> [!IMPORTANT]
> **For a one-shot visual overview, open [`docs/site/index.html`](docs/site/index.html) in your browser.**
> Hand-crafted single-file showcase with diagrams — the fastest way to grasp the architecture.

## Quick start

```bash
make install            # uv sync + install pre-commit hook
cp .env.example .env    # fill in Azure endpoint + key — required for `make run`
make run                # extract → output/clauses.json + output/clauses.html + Azure LLM verifier pass
make eval               # 25 deterministic checks vs golden file (no LLM)
make test               # 47 unit tests
```

The deliverable is [`output/clauses.json`](output/clauses.json).

## Where to look next

| Path | What it is |
|---|---|
| [`docs/site/index.html`](docs/site/index.html) | **Visual one-shot showcase — start here** |
| [`docs/`](docs/) | Approach narrative + markdown design notes |
| [`output/clauses.json`](output/clauses.json) | The 87-clause JSON deliverable |
| [`output/clauses.html`](output/clauses.html) | Browseable view of all 87 clauses |

## Working agreement

Coding conventions for any contributor (human or AI) live in three parity files: [`CLAUDE.md`](CLAUDE.md) (Claude Code), [`AGENTS.md`](AGENTS.md) (Codex), [`.cursorrules`](.cursorrules) (Antigravity, Cursor).
