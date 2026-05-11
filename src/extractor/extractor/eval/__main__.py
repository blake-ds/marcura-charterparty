"""Module entry point: ``python -m extractor.eval``."""

from __future__ import annotations

import sys

from extractor.eval.runner import main

if __name__ == "__main__":
    sys.exit(main())
