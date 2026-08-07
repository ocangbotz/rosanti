"""Chart screenshot analysis via a vision-capable LLM.

A user uploads a chart image; the model is instructed to return a strict
JSON object describing what it sees (trend, support/resistance, a possible
entry/SL/TP, common mistakes visible in the setup, and risk notes) plus a
short natural-language report. The JSON contract is what makes this usable
programmatically — free-form prose from a vision model can't be safely
stored into structured journal fields, so the prompt is deliberately
strict about the expected shape and the parser is deliberately strict
about rejecting anything that doesn't match it.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.core.exceptions import AIProviderError
from app.services.ai.base import ILLMProvider
from app.services.ai.schemas import ScreenshotAnalysisResult

SYSTEM_PROMPT = """You are a professional trading chart analyst. You will be shown a \
screenshot of a trading chart (candlesticks, and possibly indicators drawn on it). \
Analyze it and respond with ONLY a single JSON object — no markdown, no prose \
outside the JSON — matching exactly this schema:

{
  "detected_trend": "bullish" | "bearish" | "ranging",
  "detected_support": [<price levels you can read off the chart, as numbers>],
  "detected_resistance": [<price levels you can read off the chart, as numbers>],
  "suggested_entry": <number or null>,
  "suggested_stop_loss": <number or null>,
  "suggested_take_profit": <number or null>,
  "mistakes": [<short strings describing visible mistakes in the setup shown, \
if any — e.g. "no stop loss visible", "entry chasing an extended move", \
"stop loss too tight relative to volatility", "poor risk/reward ratio">],
  "risk_notes": "<one or two sentences on the risk profile of what's shown>",
  "full_report": "<a complete, professional 4-8 sentence report covering trend, \
key levels, the trade idea if one is visible, and risk>"
}

Only report price levels and structures you can actually read from the image. \
If you cannot confidently determine a value, use null (for numbers) or an \
empty list/string, rather than guessing. Respond with ONLY the JSON object."""

USER_PROMPT_TEMPLATE = (
    "Analyze this trading chart screenshot{symbol_clause} and return the JSON report "
    "as instructed."
)


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    candidate = fence_match.group(1) if fence_match else stripped

    if not candidate.lstrip().startswith("{"):
        brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if brace_match:
            candidate = brace_match.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIProviderError(
            f"The AI provider's screenshot analysis was not valid JSON: {exc}"
        ) from exc


class ScreenshotAnalyzer:
    def __init__(self, provider: ILLMProvider):
        self._provider = provider

    async def analyze(
        self, image_bytes: bytes, media_type: str, symbol_hint: str | None = None
    ) -> ScreenshotAnalysisResult:
        symbol_clause = f" of {symbol_hint}" if symbol_hint else ""
        user_prompt = USER_PROMPT_TEMPLATE.format(symbol_clause=symbol_clause)

        raw_text = await self._provider.generate_vision(
            SYSTEM_PROMPT, user_prompt, image_bytes, media_type, max_tokens=1500
        )
        parsed = _extract_json(raw_text)

        try:
            return ScreenshotAnalysisResult(**parsed, raw_model_response=parsed)
        except (TypeError, ValidationError) as exc:
            raise AIProviderError(f"Screenshot analysis response was malformed: {exc}") from exc
