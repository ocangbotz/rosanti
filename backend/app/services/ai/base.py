"""`ILLMProvider` — the interface every AI/LLM backend implements.

Two capabilities only: plain text generation (for the market narrator) and
vision generation (for screenshot analysis). Keeping the interface this
narrow means swapping providers (or adding a second one) never touches
`narrator.py` or `screenshot_analyzer.py` — those modules only know how to
build prompts and parse responses, never how to talk to a specific API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ILLMProvider(ABC):
    @abstractmethod
    async def generate_text(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1024
    ) -> str:
        """Return the model's plain-text completion for a text-only prompt."""

    @abstractmethod
    async def generate_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        media_type: str,
        max_tokens: int = 1500,
    ) -> str:
        """Return the model's plain-text completion for a prompt that includes
        a single image (e.g. an uploaded chart screenshot)."""
