"""End-to-end tests against the sample PDF shipped with the repo.

These exercise the deterministic core (no LLM), so they're fast (~1s) and
reproducible. The sample PDF is committed at the repo root.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from extractor.models import Section

from extractor import extract_clauses

PDF = Path(__file__).resolve().parents[3] / "voyage-charter-example.pdf"


@pytest.fixture(scope="session")
def clauses():
    if not PDF.exists():
        pytest.skip(f"Sample PDF missing: {PDF}")
    return extract_clauses(PDF)


def test_total_count(clauses) -> None:
    assert len(clauses) == 87


def test_section_counts(clauses) -> None:
    counts = {s.value: 0 for s in Section}
    for c in clauses:
        counts[c.section.value] += 1
    assert counts == {"shellvoy": 38, "additional": 28, "essar": 21}


def test_ids_unique_and_prefixed(clauses) -> None:
    ids = [c.id for c in clauses]
    assert len(set(ids)) == len(ids)
    for clause in clauses:
        assert clause.id.startswith(("shellvoy-", "additional-", "essar-"))


def test_clause_one_anchor(clauses) -> None:
    first = next(c for c in clauses if c.id == "shellvoy-1")
    assert first.title == "Condition Of vessel"
    assert first.text.startswith("Owners shall exercise due diligence")
    assert first.text.endswith("accept 29 February 2000 as a valid date.")


def test_struck_phrases_filtered_out(clauses) -> None:
    all_text = " ".join(c.text for c in clauses)
    forbidden = (
        "Has tanks coated as follows",
        "or if such loss or damage was caused by an act of war",
        "use due diligence to keep the tanks, lines and pumps of the vessel clean",
    )
    leaked = [phrase for phrase in forbidden if phrase in all_text]
    assert leaked == []


def test_replacement_text_kept(clauses) -> None:
    """The bold replacement clause 2 should survive after strike removal."""
    second = next(c for c in clauses if c.id == "shellvoy-2")
    assert second.title == "Cleanliness Of tanks"
    assert "always clean for the cargo" in second.text


def test_essar_section_starts_at_one(clauses) -> None:
    essar = [c for c in clauses if c.section is Section.ESSAR]
    assert essar[0].id == "essar-1"
    assert "INTERNATIONAL REGULATIONS" in essar[0].title.upper()


def test_clause_44_construction_is_present(clauses) -> None:
    """Clause 44 *Construction* completes the SHELLVOY 1..44 range."""
    construction = next((c for c in clauses if c.id == "shellvoy-44"), None)
    assert construction is not None
    assert construction.title == "Construction"


def test_shellvoy_22_title_does_not_leak_struck_neighbour(clauses) -> None:
    """Regression: clause 21 was wholly struck; its title must not be merged into 22."""
    twenty_two = next(c for c in clauses if c.id == "shellvoy-22")
    assert twenty_two.title == "Ice"
    assert "Over age" not in twenty_two.title


def test_essar_22_present_with_split_anchor_token(clauses) -> None:
    """Regression: the PDF prints "22" then ".BILL OF LADING …" as separate tokens."""
    e22 = next((c for c in clauses if c.id == "essar-22"), None)
    assert e22 is not None
    assert e22.title == "BILL OF LADING FIGURES"


def test_essar_21_does_not_swallow_essar_22(clauses) -> None:
    """Regression: before the anchor fix, essar-21's body absorbed essar-22's content."""
    e21 = next(c for c in clauses if c.id == "essar-21")
    assert "BILL OF LADING FIGURES" not in e21.text
    assert not re.search(r"\d+\s*\.\s*BILL OF LADING", e21.text)


def test_essar_16_single_line_clause_kept(clauses) -> None:
    """Regression: a single-line clause used to be dropped because below-anchor body was empty."""
    e16 = next((c for c in clauses if c.id == "essar-16"), None)
    assert e16 is not None
    assert "voyage instructions" in e16.text


def test_strike_fragments_do_not_leak_from_additional_clauses(clauses) -> None:
    """Mid-word and structural fragments from struck content must not appear.

    Note: ``"Legal proceedings have been commenced against Owners"`` is *not*
    on this list. Its line is only ~2% struck (just the ``b)`` prefix), so it
    is faithful visible text from the PDF, not a strike-through fragment.
    """
    all_text = " ".join(c.text for c in clauses)
    forbidden = (
        "that vessel will not exceed a maximum freeboard",
        "Freight payment Clause 5",
        "operations in Sydney during the hours of darkness",
        "disconnecting of hoses to Recommence",
        ", , Worldscale",
    )
    assert [fragment for fragment in forbidden if fragment in all_text] == []


def test_wholly_replaced_additional_clauses_are_dropped(clauses) -> None:
    """Per manual ground-truth review of every Part II page, these Additional
    clauses had their title struck *and* their body wholly replaced — visible
    glyphs that survive in the PDF are mid-line artefacts of strike rectangles
    ending short, not real clause text. They must not appear in the output.
    """
    by_id = {c.id: c for c in clauses}
    dropped_ords = {2, 12, 20, 21, 31, 32, 33, 34, 35, 36, 37, 39, 40, 41, 42}
    leaked = [ord_ for ord_ in dropped_ords if f"additional-{ord_}" in by_id]
    assert leaked == [], f"these wholly-replaced clauses leaked into output: {leaked}"


def test_partial_strike_visible_replacements_are_kept(clauses) -> None:
    a3 = next(c for c in clauses if c.id == "additional-3")
    a6 = next(c for c in clauses if c.id == "additional-6")
    assert "for the duration of this Charter." in a3.text
    assert "Worldscale charges / dues;" in a6.text
    assert ", , Worldscale" not in a6.text


def test_essar_11_keeps_acronym_title(clauses) -> None:
    e11 = next(c for c in clauses if c.id == "essar-11")
    assert e11.title == "I.S.M. CLAUSE"
    assert e11.text.startswith("From the date of coming into force")


def test_essar_18_heading_only_clause_kept(clauses) -> None:
    e18 = next(c for c in clauses if c.id == "essar-18")
    assert e18.title == "CLINGAGE – NOT APPLICABLE FOR THIS CHARTER"
    assert e18.text == ""


def test_essar_21_keeps_lowercase_continuation(clauses) -> None:
    e21 = next(c for c in clauses if c.id == "essar-21")
    assert "forthcoming voyage" in e21.text
    assert e21.text.endswith("tank washing held prior loading.")


def test_shellvoy_13_partial_strike_fragment_removed(clauses) -> None:
    c13 = next(c for c in clauses if c.id == "shellvoy-13")
    assert "disconnecting of hoses to Recommence" not in c13.text
    assert "Recommence two hours after disconnection" in c13.text
