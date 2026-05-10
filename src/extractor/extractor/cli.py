"""CLI entrypoint for the extractor.

Run end-to-end:

```
uv run python -m extractor --pdf voyage-charter-example.pdf --out output
```

Add ``--verify`` to invoke the optional Azure-hosted LLM verifier (configured
via ``.env``); skip it for an offline, deterministic-only run.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from extractor.output import write_html, write_json
from extractor.pipeline import extract_clauses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="extractor",
        description="Extract clauses from a charter party PDF into JSON + HTML.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("voyage-charter-example.pdf"),
        help="Path to the charter party PDF (default: voyage-charter-example.pdf).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output"),
        help="Directory to write clauses.json and clauses.html (default: output).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run the optional Azure LLM verifier after extraction.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(levelname)s %(name)s — %(message)s",
    )
    # Quiet third-party HTTP-trace loggers — they would otherwise dump headers,
    # bodies, and timings on every Azure call.
    for noisy in ("azure", "openai", "httpx", "urllib3", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    log = logging.getLogger("extractor")

    if not args.pdf.exists():
        log.error("PDF not found: %s", args.pdf)
        return 1

    verifier = _build_verifier(log) if args.verify else None
    clauses = extract_clauses(args.pdf, verifier=verifier)

    json_path = args.out / "clauses.json"
    html_path = args.out / "clauses.html"
    write_json(clauses, json_path)
    write_html(clauses, html_path)

    log.info("Extracted %d clauses → %s", len(clauses), json_path)
    log.info("Browseable view → %s", html_path)
    return 0


def _build_verifier(log: logging.Logger):  # noqa: ANN202 — returns a callable, kept light
    """Build the Azure LLM verifier; degrade gracefully if not configured."""
    try:
        from llm.verifier import build_verifier
    except ImportError:
        log.warning("--verify requested but the 'llm' package is unavailable; skipping.")
        return None
    try:
        return build_verifier()
    except Exception:
        log.exception("Failed to build verifier; skipping verification.")
        return None


if __name__ == "__main__":
    sys.exit(main())
