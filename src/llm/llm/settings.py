"""Pydantic-settings reading the ``MARCURA_…`` env vars / ``.env`` file.

The module is import-side-effect free; ``LLMSettings()`` instantiates and
reads. Splitting the settings out of the verifier makes both halves trivial
to test in isolation.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """All LLM-related configuration, sourced from ``.env`` or shell env."""

    model_config = SettingsConfigDict(
        env_prefix="MARCURA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    azure_openai_endpoint: str = Field(default="", description="Azure OpenAI account endpoint.")
    azure_openai_api_key: str = Field(default="", description="Azure OpenAI API key.")
    azure_openai_api_version: str = Field(default="2025-04-01-preview")
    azure_openai_reasoning_effort: str = Field(default="medium")

    azure_foundry_endpoint: str = Field(default="", description="Azure Foundry inference endpoint.")
    azure_foundry_api_key: str = Field(default="", description="Azure Foundry API key.")
    azure_foundry_reasoning_effort: str = Field(default="medium")

    verifier_model: str = Field(
        default="DeepSeek-V4-Flash",
        description="Deployment to call from the verifier.",
    )

    @property
    def azure_openai_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def azure_foundry_configured(self) -> bool:
        return bool(self.azure_foundry_endpoint and self.azure_foundry_api_key)

    def is_foundry_deployment(self, deployment: str) -> bool:
        """Foundry deployment names start with the partner-lab prefix."""
        prefixes = ("deepseek", "grok", "mistral", "llama", "cohere")
        return deployment.casefold().startswith(prefixes)
