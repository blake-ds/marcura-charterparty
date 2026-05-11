# Development

## Prerequisites

- **Python 3.13** (pinned in `.python-version`)
- **uv** — install via `make uv_install` or follow [astral-sh/uv](https://github.com/astral-sh/uv) docs
- An Azure subscription with deployed models, if you want to run the LLM verifier or integration tests. The default models are documented in `.env.example`.

## First-time setup

```bash
make install                 # uv sync + install pre-commit hook
cp .env.example .env         # then fill in Azure endpoints/keys
```

`make install` installs the workspace (root + every `src/<package>`) and registers the pre-commit hook so it runs on every commit. `.env` is gitignored and additionally guarded by gitleaks in pre-commit / CI.

## Common commands

| Command | What it does |
|---|---|
| `make install` | Sync workspace + install pre-commit hook. |
| `make format` | Auto-fix lints and format with ruff. |
| `make lint` | Check-only ruff (lint + format). Used by CI. |
| `make type-check` | Run [`ty`](https://docs.astral.sh/ty/). |
| `make test` | Run unit tests (skips integration). |
| `make test_integration` | Run integration tests (talk to Azure). |
| `make precommit` | Run all pre-commit hooks against all tracked files. |
| `make run` | Extract clauses → `output/clauses.json` + `output/clauses.html` + Azure LLM verifier pass. Requires `.env`. |
| `make eval` | Deterministic correctness check against the golden file. No LLM. |
| `make clean` | Wipe caches and build artifacts. |

## Repository layout

```
.
├── src/                     # uv workspace members (rag-chatbot pattern)
│   ├── extractor/           # deterministic PDF → clause candidates
│   └── llm/                 # Azure clients + verifier
├── docs/                    # markdown source-of-truth (this folder)
├── output/                  # the deliverable: clauses.json + clauses.html
├── src/extractor/extractor/eval/
│                             # golden file + assertions (no LLM)
├── .github/workflows/       # CI (ruff, ty, gitleaks, pytest)
├── CLAUDE.md  AGENTS.md  .cursorrules    # parity working-agreement
├── pyproject.toml           # workspace root + ruff/pytest/ty config
├── Makefile
└── .pre-commit-config.yaml
```

## Pre-commit hooks

Installed by `make install`. Hooks fail the commit; do not bypass with `--no-verify` — fix the underlying issue.

- `ruff-check` — lint + auto-fix
- `ruff-format` — format
- `gitleaks` — secret detection (no API keys allowed in commits)
- standard hygiene (end-of-file, trailing whitespace, merge conflict markers, large files, private keys)
- `actionlint` — validates GitHub Actions workflow YAML

`ty` (the type checker) runs in `make type-check` and CI but not in pre-commit, to keep commits fast.

## Browseable docs

`docs/site/index.html` is a self-contained, hand-crafted HTML snapshot of the architecture, eval, and results — open it directly in a browser. No build system, no framework. Markdown in `docs/*.md` is the canonical source of truth; the HTML page is a polished snapshot regenerated only when the docs materially change.

## CI

`.github/workflows/ci.yml` runs on every push and pull request:

1. uv setup + sync (cached)
2. `make lint`
3. `make type-check`
4. gitleaks
5. `make test` (unit tests)
6. `make eval` (deterministic correctness against the golden file)

A separate `integration` job hits Azure-hosted LLMs; it runs only on `workflow_dispatch` or commits whose message contains `[run-integration]`.

Azure secrets are wired into GitHub Environment Secrets and exposed to the workflow only for explicit integration runs.
