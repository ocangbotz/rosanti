"""Selects the active `ILLMProvider` implementation based on `Settings.ai_provider`."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.core.exceptions import AIProviderError
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import ILLMProvider


def get_llm_provider(settings: Settings | None = None) -> ILLMProvider:
    settings = settings or get_settings()
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(settings)
    raise AIProviderError(f"Unsupported AI_PROVIDER: {settings.ai_provider!r}")
