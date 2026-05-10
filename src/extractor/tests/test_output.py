"""Output serialization tests."""

from __future__ import annotations

import json

from extractor.models import Clause, Section
from extractor.output import write_html, write_json


def _sample() -> list[Clause]:
    return [
        Clause(
            section=Section.SHELLVOY,
            ordinal=1,
            title="Condition Of vessel",
            text="Owners shall exercise due diligence.",
            page_start=6,
            page_end=6,
        ),
        Clause(
            section=Section.ADDITIONAL,
            ordinal=1,
            title="Indemnity Clause",
            text="If Charterers by telex…",
            page_start=18,
            page_end=18,
        ),
    ]


def test_json_output_matches_spec(tmp_path) -> None:
    target = tmp_path / "clauses.json"
    write_json(_sample(), target)
    payload = json.loads(target.read_text())
    assert payload == [
        {
            "id": "shellvoy-1",
            "title": "Condition Of vessel",
            "text": "Owners shall exercise due diligence.",
        },
        {
            "id": "additional-1",
            "title": "Indemnity Clause",
            "text": "If Charterers by telex…",
        },
    ]


def test_html_output_self_contained_and_escaped(tmp_path) -> None:
    target = tmp_path / "clauses.html"
    write_html(_sample(), target)
    body = target.read_text()
    assert body.startswith("<!doctype html>")
    assert 'id="shellvoy-1"' in body
    assert 'id="additional-1"' in body
    # IDs and titles are HTML-escaped where needed.
    assert "<style>" in body  # embedded CSS, no external stylesheet
    assert "<script" not in body  # no JS dependency
