"""Azure client factories — one for each provider surface.

The two surfaces speak different protocols:

- Azure OpenAI    → ``openai.AzureOpenAI`` against ``/openai/deployments/<n>``.
- Azure Foundry   → ``azure.ai.inference.ChatCompletionsClient`` against ``/models``.

Both are wrapped behind a tiny :class:`ChatClient` adapter so the verifier can
talk to one interface regardless of the deployment chosen.
"""

from __future__ import annotations

from typing import Protocol

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import (
    JsonSchemaFormat,
)
from azure.ai.inference.models import (
    SystemMessage as FoundrySystemMessage,
)
from azure.ai.inference.models import (
    UserMessage as FoundryUserMessage,
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from pydantic import BaseModel, ConfigDict, PrivateAttr

from llm.settings import LLMSettings


class ChatClient(Protocol):
    """Minimal chat surface used by the verifier."""

    def chat(
        self,
        *,
        deployment: str,
        system: str,
        user: str,
        json_schema: dict | None = None,
    ) -> str: ...


class AzureOpenAIChatClient(BaseModel):
    """Wraps :class:`openai.AzureOpenAI` for ``gpt-…`` deployments."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: LLMSettings
    _client: AzureOpenAI | None = PrivateAttr(default=None)

    def _ensure(self) -> AzureOpenAI:
        if self._client is None:
            if not self.settings.azure_openai_configured:
                raise RuntimeError(
                    "Azure OpenAI is not configured — set MARCURA_AZURE_OPENAI_ENDPOINT "
                    "and MARCURA_AZURE_OPENAI_API_KEY."
                )
            self._client = AzureOpenAI(
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                azure_endpoint=self.settings.azure_openai_endpoint,
            )
        return self._client

    def chat(
        self,
        *,
        deployment: str,
        system: str,
        user: str,
        json_schema: dict | None = None,
    ) -> str:
        client = self._ensure()
        kwargs: dict = {
            "model": deployment,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "reasoning_effort": self.settings.azure_openai_reasoning_effort,
        }
        if json_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "verifier_response", "schema": json_schema, "strict": True},
            }
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


class AzureFoundryChatClient(BaseModel):
    """Wraps :class:`azure.ai.inference.ChatCompletionsClient` for partner deployments."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: LLMSettings
    _client: ChatCompletionsClient | None = PrivateAttr(default=None)

    def _ensure(self) -> ChatCompletionsClient:
        if self._client is None:
            if not self.settings.azure_foundry_configured:
                raise RuntimeError(
                    "Azure Foundry is not configured — set MARCURA_AZURE_FOUNDRY_ENDPOINT "
                    "and MARCURA_AZURE_FOUNDRY_API_KEY."
                )
            self._client = ChatCompletionsClient(
                endpoint=self.settings.azure_foundry_endpoint.rstrip("/") + "/models",
                credential=AzureKeyCredential(self.settings.azure_foundry_api_key),
            )
        return self._client

    def chat(
        self,
        *,
        deployment: str,
        system: str,
        user: str,
        json_schema: dict | None = None,
    ) -> str:
        client = self._ensure()
        messages = [FoundrySystemMessage(content=system), FoundryUserMessage(content=user)]
        kwargs: dict = {
            "messages": messages,
            "model": deployment,
            "model_extras": {"reasoning_effort": self.settings.azure_foundry_reasoning_effort},
        }
        if json_schema is not None:
            kwargs["response_format"] = JsonSchemaFormat(
                name="verifier_response", schema=json_schema, strict=True
            )
        response = client.complete(**kwargs)  # ty: ignore[unresolved-attribute]
        return response.choices[0].message.content or ""


def build_chat_client(deployment: str, settings: LLMSettings) -> ChatClient:
    """Pick the right client for the given deployment."""
    if settings.is_foundry_deployment(deployment):
        return AzureFoundryChatClient(settings=settings)
    return AzureOpenAIChatClient(settings=settings)
