"""Anthropic (Claude) implementation of `ILLMProvider`, talking directly to
the Messages API over HTTP (no SDK dependency — one `httpx` call is enough
for this project's needs and keeps the dependency footprint small).
"""

from __future__ import annotations

import base64

import httpx

from app.config import Settings
from app.core.exceptions import AIProviderError
from app.services.ai.base import ILLMProvider

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicProvider(ILLMProvider):
    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise AIProviderError(
                "ANTHROPIC_API_KEY is not configured. Set it in .env to enable AI narration "
                "and screenshot analysis."
            )
        self._api_key = settings.anthropic_api_key
        self._text_model = settings.anthropic_model
        self._vision_model = settings.anthropic_vision_model
        self._timeout = settings.ai_request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

    async def _call(
        self, model: str, system_prompt: str, content: list[dict], max_tokens: int
    ) -> str:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": content}],
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    ANTHROPIC_API_URL, headers=self._headers(), json=payload
                )
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Failed to reach the Anthropic API: {exc}") from exc

        if response.status_code != 200:
            raise AIProviderError(
                f"Anthropic API returned {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        blocks = data.get("content", [])
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        if not text:
            raise AIProviderError("Anthropic API returned an empty response.")
        return text.strip()

    async def generate_text(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1024
    ) -> str:
        content = [{"type": "text", "text": user_prompt}]
        return await self._call(self._text_model, system_prompt, content, max_tokens)

    async def generate_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        media_type: str,
        max_tokens: int = 1500,
    ) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        content: list[dict] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": encoded},
            },
            {"type": "text", "text": user_prompt},
        ]
        return await self._call(self._vision_model, system_prompt, content, max_tokens)
