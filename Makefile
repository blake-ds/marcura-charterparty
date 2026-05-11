SHELL := /bin/bash

# Every target here is a *command*, not a file — declare them PHONY so GNU
# Make never short-circuits when a same-named directory exists (the original
# bug: `make eval` was a no-op because the top-level `eval/` directory shadowed
# the target and CI passed without running the evaluator).
.PHONY: uv_install install upgrade \
        format lint type-check test test_integration precommit \
        run verify eval \
        clean

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

uv_install: # install uv if missing
	curl -LsSf https://astral.sh/uv/install.sh | sh

install: # sync workspace + install pre-commit hook
	uv sync --all-packages
	uv run pre-commit install

upgrade: # upgrade lockfile + sync
	uv lock --upgrade
	uv sync --all-packages

# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------

format: # auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

lint: # check only — used by CI
	uv run ruff check .
	uv run ruff format --check .

type-check:
	uv run ty check

test:
	uv run pytest -m "not integration"

test_integration:
	uv run pytest -m integration -v

precommit: # run all hooks against tracked files
	uv run pre-commit run --all-files

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

run: # extract clauses → output/clauses.json + output/clauses.html
	uv run python -m extractor --pdf voyage-charter-example.pdf --out output

verify: # same as run, with the optional Azure LLM verifier pass
	uv run python -m extractor --pdf voyage-charter-example.pdf --out output --verify

eval: # deterministic correctness check vs golden file
	uv run python -m extractor.eval

# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------

clean:
	rm -rf .pytest_cache .ruff_cache .ty_cache dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
