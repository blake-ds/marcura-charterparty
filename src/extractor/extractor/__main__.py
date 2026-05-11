"""Module entry point so ``python -m extractor`` runs the CLI."""

from __future__ import annotations

import sys

from extractor.cli import main

if __name__ == "__main__":
    sys.exit(main())
