"""End-to-end orchestration: PDF in, ``list[Clause]`` out.

The pipeline is intentionally linear and side-effect free. Section detection
selects the page ranges; the appropriate parser is dispatched per range. The
optional ``verifier`` callable, if supplied, is invoked once with the full
list of candidates and may return advisory anomalies — it never mutates the
clauses themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from extractor import inline, shellvoy
from extractor.models import Clause, Section
from extractor.pdf import Page, load_pages
from extractor.sections import SectionRange, detect_sections


def extract_clauses(
    pdf_path: Path | str,
    *,
    verifier: Callable[[list[Clause]], None] | None = None,
) -> list[Clause]:
    """Parse the charter party PDF and return the extracted clauses.

    ``verifier`` is invoked (after extraction) with the final list, allowing
    callers to plug in the optional Azure-hosted LLM check without coupling
    the deterministic core to it.
    """
    pages = load_pages(Path(pdf_path))
    sections = detect_sections(pages)

    clauses: list[Clause] = []
    for section_range in sections:
        section_pages = tuple(p for p in pages if section_range.contains(p.number))
        clauses.extend(_parse_section(section_range, section_pages))

    if verifier is not None:
        verifier(clauses)
    return clauses


def _parse_section(section_range: SectionRange, section_pages: tuple[Page, ...]) -> list[Clause]:
    if section_range.section is Section.SHELLVOY:
        return shellvoy.parse(section_pages)
    return inline.parse(section_pages, section_range.section)
