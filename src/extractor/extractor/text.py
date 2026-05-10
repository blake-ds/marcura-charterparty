"""Reading-order text reconstruction from a stream of glyphs.

The PDF carries no logical structure for clauses — only positioned glyphs. To
turn a set of glyphs back into legible prose we group them into visual lines
(by ``(page, y)`` with a small tolerance), sort each line left-to-right, and
join lines with a space. A wider-than-usual vertical gap is treated as a
paragraph break and emitted as a blank line (``\\n\\n``). Cross-page transitions
also count as paragraph breaks — the visual continuation of a clause across
pages should still read as a paragraph boundary.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from extractor.pdf import Char

_LINE_Y_TOLERANCE = 2.0  # glyphs within this many points share a visual line
_PARAGRAPH_GAP_RATIO = 1.6  # gap > this × median line height = paragraph break

# A "line" is identified by its (page, rounded-y) tuple.
LineKey = tuple[int, int]
Line = tuple[LineKey, list[Char]]


def chars_to_text(chars: Iterable[Char]) -> str:
    """Concatenate ``chars`` in reading order; collapse stray whitespace."""
    lines = _group_into_lines(chars)
    if not lines:
        return ""

    threshold = _paragraph_threshold(lines)
    parts: list[str] = []
    for index, ((page, y), line_chars) in enumerate(lines):
        line_text = "".join(c.text for c in sorted(line_chars, key=lambda c: c.x0))
        if index == 0:
            parts.append(line_text)
            continue
        prev_page, prev_y = lines[index - 1][0]
        if page != prev_page or (y - prev_y) > threshold:
            parts.append("\n\n" + line_text)
        else:
            parts.append(" " + line_text)

    text = "".join(parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n\n *", "\n\n", text)
    return text.strip()


def _group_into_lines(chars: Iterable[Char]) -> list[Line]:
    buckets: dict[LineKey, list[Char]] = {}
    for char in chars:
        page = char.page
        rounded_y = round(char.y_mid)
        key: LineKey = (page, rounded_y)
        for (existing_page, existing_y), bucket in buckets.items():
            if existing_page == page and abs(existing_y - rounded_y) <= _LINE_Y_TOLERANCE:
                bucket.append(char)
                break
        else:
            buckets[key] = [char]
    return sorted(buckets.items())


def _paragraph_threshold(lines: list[Line]) -> float:
    """``min_intra_page_gap × _PARAGRAPH_GAP_RATIO``.

    Min beats median here because paragraph breaks contaminate the median in
    small samples (e.g. two intra-page gaps ``[12, 48]`` would yield a median
    of 48, missing the obvious break). The minimum approximates the typical
    line height; outliers above it are the paragraph boundaries.
    """
    gaps: list[int] = []
    for i in range(len(lines) - 1):
        (cur_page, cur_y), _ = lines[i]
        (next_page, next_y), _ = lines[i + 1]
        if cur_page == next_page:
            gaps.append(next_y - cur_y)
    if not gaps:
        return float("inf")
    return min(gaps) * _PARAGRAPH_GAP_RATIO
