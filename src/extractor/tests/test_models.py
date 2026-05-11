"""Tests for our Clause adapter logic — id format, wire-format projection."""

from extractor.models import Clause, Section


def _clause(**overrides) -> Clause:
    base = {
        "section": Section.SHELLVOY,
        "ordinal": 1,
        "title": "Condition Of vessel",
        "text": "Owners shall exercise due diligence.",
        "page_start": 6,
        "page_end": 6,
    }
    base.update(overrides)
    return Clause(**base)


def test_id_uses_section_prefix() -> None:
    """The chosen disambiguation: ``<section>-<ordinal>``."""
    assert _clause(section=Section.SHELLVOY, ordinal=1).id == "shellvoy-1"
    assert _clause(section=Section.ADDITIONAL, ordinal=1).id == "additional-1"
    assert _clause(section=Section.ESSAR, ordinal=22).id == "essar-22"


def test_to_spec_dict_drops_provenance_fields() -> None:
    """Wire format must match the README contract — and *only* it."""
    assert set(_clause().to_spec_dict().keys()) == {"id", "title", "text"}


def test_title_and_text_validators_strip_whitespace() -> None:
    clause = _clause(title="  Condition Of vessel  ", text="\n  Owners shall.  \n")
    assert clause.title == "Condition Of vessel"
    assert clause.text == "Owners shall."
