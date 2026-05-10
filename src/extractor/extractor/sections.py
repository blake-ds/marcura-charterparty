"""Locate the three numbering ranges that make up Part II.

Part II is the concatenation of three boilerplate documents — SHELLVOY 5
standard clauses, Shell Additional Clauses (Feb 1999), and Essar Rider Clauses
(Dec 2006) — each restarting at clause 1. The section boundary is identified by
header text on the first page of the new section; everything before the next
header is owned by the current section.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from extractor.models import Section
from extractor.pdf import Page

_PART_II_MARKER = "PART II"
_ADDITIONAL_MARKER = "SHELL ADDITIONAL CLAUSES"
_ESSAR_MARKER = "Essar Rider Clauses"
# Section markers must sit in the top band of a page — that is what marks them
# as a *heading*. The phrase "Part II" also appears mid-body on page 1 ("subject
# to Part I and Part II"), and we must not treat that as a section start.
_HEADER_BAND_FRACTION = 0.15


class SectionRange(BaseModel):
    """One section's inclusive page span (1-indexed)."""

    model_config = ConfigDict(frozen=True)

    section: Section
    page_start: int
    page_end: int

    def contains(self, page_number: int) -> bool:
        return self.page_start <= page_number <= self.page_end


def detect_sections(pages: tuple[Page, ...]) -> tuple[SectionRange, ...]:
    """Return the inclusive page range for each of the three sections."""
    shellvoy_start = _find_first_page(pages, _PART_II_MARKER)
    additional_start = _find_first_page(pages, _ADDITIONAL_MARKER)
    essar_start = _find_first_page(pages, _ESSAR_MARKER)

    if shellvoy_start is None or additional_start is None or essar_start is None:
        missing = [
            label
            for label, val in (
                ("SHELLVOY", shellvoy_start),
                ("ADDITIONAL", additional_start),
                ("ESSAR", essar_start),
            )
            if val is None
        ]
        raise ValueError(f"Could not locate section markers in PDF: {missing}")

    last_page = pages[-1].number
    return (
        SectionRange(
            section=Section.SHELLVOY,
            page_start=shellvoy_start,
            page_end=additional_start - 1,
        ),
        SectionRange(
            section=Section.ADDITIONAL,
            page_start=additional_start,
            page_end=essar_start - 1,
        ),
        SectionRange(
            section=Section.ESSAR,
            page_start=essar_start,
            page_end=last_page,
        ),
    )


def _find_first_page(pages: tuple[Page, ...], marker: str) -> int | None:
    """Return the 1-indexed page number whose top header contains ``marker``.

    A "header" is the visible text in the top :data:`_HEADER_BAND_FRACTION` of
    the page; this excludes incidental matches further down (e.g. the body of
    page 1 mentions "Part II" as part of a sentence). Strike-through is
    filtered out so we don't false-match a struck phrase elsewhere.
    """
    needle = marker.casefold()
    for page in pages:
        cutoff = page.height * _HEADER_BAND_FRACTION
        header = "".join(c.text for c in page.visible_chars() if c.y_mid < cutoff)
        if needle in header.casefold():
            return page.number
    return None
