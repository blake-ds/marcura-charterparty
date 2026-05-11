"""Settings tests — only our routing logic, not Pydantic's plumbing."""

from llm.settings import LLMSettings


def test_foundry_prefix_classification() -> None:
    """Routing decides which Azure surface to talk to. Test the seam."""
    s = LLMSettings(_env_file=None)  # ty: ignore[unknown-argument]
    assert s.is_foundry_deployment("DeepSeek-V4-Flash") is True
    assert s.is_foundry_deployment("grok-4-1-fast-non-reasoning") is True
    assert s.is_foundry_deployment("gpt-5.4-nano") is False
    assert s.is_foundry_deployment("gpt-5.4-mini") is False


def test_configured_flags_combine_endpoint_and_key() -> None:
    """Both halves required — neither alone counts as configured."""
    s = LLMSettings(
        _env_file=None,  # ty: ignore[unknown-argument]
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="",
    )
    assert s.azure_openai_configured is False

    s2 = LLMSettings(
        _env_file=None,  # ty: ignore[unknown-argument]
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="secret",
    )
    assert s2.azure_openai_configured is True
