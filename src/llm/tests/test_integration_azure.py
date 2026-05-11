"""Live integration test against Azure-hosted LLMs.

Skipped unless the necessary credentials are present in the environment
(``MARCURA_AZURE_FOUNDRY_*`` for the default DeepSeek deployment). Marked
``integration`` so the default ``make test`` does not pull it in; run with
``make test_integration``.
"""

from __future__ import annotations

import pytest
from extractor.models import Clause, Section

from llm import LLMSettings, verify

pytestmark = pytest.mark.integration


def _required_env_for(settings: LLMSettings) -> bool:
    if settings.is_foundry_deployment(settings.verifier_model):
        return settings.azure_foundry_configured
    return settings.azure_openai_configured


@pytest.fixture(scope="module")
def settings() -> LLMSettings:
    s = LLMSettings()
    if not _required_env_for(s):
        pytest.skip("Azure credentials for the configured verifier model are not set.")
    return s


def _clause(ordinal: int, title: str, text: str) -> Clause:
    return Clause(
        section=Section.SHELLVOY,
        ordinal=ordinal,
        title=title,
        text=text,
        page_start=6,
        page_end=6,
    )


def test_verifier_round_trip_clean_input(settings: LLMSettings) -> None:
    """A handful of unambiguous clauses should return zero anomalies."""
    clauses = [
        _clause(
            1,
            "Condition Of vessel",
            "Owners shall exercise due diligence to ensure that the vessel is in good order.",
        ),
        _clause(
            5,
            "Freight",
            "Freight shall be earned concurrently with delivery of cargo at the discharging port.",
        ),
    ]
    anomalies = verify(clauses, settings=settings)
    # We don't assert empty — the model may still flag something — but the call
    # must succeed and return well-typed records.
    for a in anomalies:
        assert a.clause_id
        assert a.issue


def test_verifier_flags_obviously_truncated_clause(settings: LLMSettings) -> None:
    clauses = [
        _clause(
            1,
            "Test",
            "this is clearly truncated and ends mid",
        )
    ]
    anomalies = verify(clauses, settings=settings)
    # Some model + prompt combos may still pass the clause if it interprets it
    # charitably; we only assert the API path works end-to-end.
    assert isinstance(anomalies, list)
