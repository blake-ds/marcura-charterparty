"""Verifier unit tests — uses an in-process fake :class:`ChatClient`.

The Azure-hitting integration test lives separately and is marked
``@pytest.mark.integration`` so it stays out of the default ``make test`` run.
"""

from __future__ import annotations

import json
import logging

import llm.verifier as verifier_mod
import pytest
from extractor.models import Clause, Section
from llm.clients import ChatClient
from llm.verifier import build_verifier, verify


class _FakeClient:
    """Minimal in-memory implementation of :class:`ChatClient`."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.last_user: str = ""
        self.last_system: str = ""
        self.last_kwargs: dict = {}

    def chat(
        self,
        *,
        deployment: str,
        system: str,
        user: str,
        json_schema: dict | None = None,
    ) -> str:
        self.last_system = system
        self.last_user = user
        self.last_kwargs = {"deployment": deployment, "json_schema": json_schema}
        return self.response


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


def test_verify_returns_empty_for_clean_response() -> None:
    fake = _FakeClient(json.dumps({"anomalies": []}))
    assert verify([_clause()], client=fake) == []


def test_verify_parses_anomalies() -> None:
    fake = _FakeClient(
        json.dumps({"anomalies": [{"id": "shellvoy-1", "issue": "title looks suspicious"}]})
    )
    out = verify([_clause()], client=fake)
    assert [(a.clause_id, a.issue) for a in out] == [("shellvoy-1", "title looks suspicious")]


def test_verify_renders_clauses_as_html_payload_with_escaping() -> None:
    fake = _FakeClient(json.dumps({"anomalies": []}))
    verify([_clause(title="Cleanliness <Of> tanks")], client=fake)
    assert '<clauses count="1">' in fake.last_user
    assert '<clause id="shellvoy-1"' in fake.last_user
    assert "<title>Cleanliness &lt;Of&gt; tanks</title>" in fake.last_user


def test_verify_passes_response_schema_through() -> None:
    fake = _FakeClient(json.dumps({"anomalies": []}))
    verify([_clause()], client=fake)
    schema = fake.last_kwargs["json_schema"]
    assert schema is not None
    assert schema["properties"]["anomalies"]["type"] == "array"


def test_build_verifier_logs_anomalies_without_raising(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The CLI hook surfaces anomalies as warnings — never as exceptions."""

    def _fake_verify(_clauses, **_kwargs):
        return [verifier_mod.Anomaly(clause_id="shellvoy-1", issue="title suspect")]

    monkeypatch.setattr(verifier_mod, "verify", _fake_verify)
    hook = build_verifier()
    with caplog.at_level(logging.WARNING):
        hook([_clause()])
    assert "title suspect" in caplog.text


def test_build_verifier_swallows_runtime_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A verifier outage must not break a deterministic extraction."""

    def _explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(verifier_mod, "verify", _explode)
    hook = build_verifier()
    with caplog.at_level(logging.ERROR):
        hook([_clause()])
    assert "Verifier call failed" in caplog.text


# Keep ChatClient importable for static checkers; the fake above does not
# inherit from it but satisfies the structural protocol.
_ = ChatClient
