import json

import pytest

from app.core.exceptions import AIProviderError
from app.services.ai.base import ILLMProvider
from app.services.ai.screenshot_analyzer import ScreenshotAnalyzer, _extract_json

VALID_REPORT = {
    "detected_trend": "bullish",
    "detected_support": [1.0950, 1.0900],
    "detected_resistance": [1.1050],
    "suggested_entry": 1.0980,
    "suggested_stop_loss": 1.0940,
    "suggested_take_profit": 1.1050,
    "mistakes": ["stop loss placed too tight relative to recent volatility"],
    "risk_notes": "Risk/reward is acceptable but the stop is inside recent noise.",
    "full_report": "The chart shows a bullish structure reclaiming support near 1.0950...",
}


class _FakeVisionProvider(ILLMProvider):
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.received_image: bytes | None = None
        self.received_media_type: str | None = None

    async def generate_text(self, system_prompt, user_prompt, max_tokens=1024) -> str:
        raise NotImplementedError

    async def generate_vision(
        self, system_prompt, user_prompt, image_bytes, media_type, max_tokens=1500
    ) -> str:
        self.received_image = image_bytes
        self.received_media_type = media_type
        return self.response_text


def test_extract_json_from_plain_json():
    text = json.dumps(VALID_REPORT)
    assert _extract_json(text) == VALID_REPORT


def test_extract_json_from_markdown_fence():
    text = f"```json\n{json.dumps(VALID_REPORT)}\n```"
    assert _extract_json(text) == VALID_REPORT


def test_extract_json_from_surrounding_prose():
    text = f"Sure, here is the analysis:\n{json.dumps(VALID_REPORT)}\nLet me know if you need more."
    assert _extract_json(text) == VALID_REPORT


def test_extract_json_raises_on_invalid_json():
    with pytest.raises(AIProviderError):
        _extract_json("this is not json at all")


@pytest.mark.asyncio
async def test_analyze_returns_validated_result():
    provider = _FakeVisionProvider(json.dumps(VALID_REPORT))
    analyzer = ScreenshotAnalyzer(provider)

    result = await analyzer.analyze(b"fake-image-bytes", "image/png", symbol_hint="EURUSD")

    assert result.detected_trend == "bullish"
    assert result.detected_support == [1.0950, 1.0900]
    assert result.suggested_entry == 1.0980
    assert result.mistakes == VALID_REPORT["mistakes"]
    assert result.raw_model_response == VALID_REPORT
    assert provider.received_image == b"fake-image-bytes"
    assert provider.received_media_type == "image/png"


@pytest.mark.asyncio
async def test_analyze_raises_on_missing_required_field():
    incomplete = dict(VALID_REPORT)
    del incomplete["full_report"]
    provider = _FakeVisionProvider(json.dumps(incomplete))
    analyzer = ScreenshotAnalyzer(provider)

    with pytest.raises(AIProviderError):
        await analyzer.analyze(b"fake-image-bytes", "image/png")


@pytest.mark.asyncio
async def test_analyze_includes_symbol_hint_in_user_prompt():
    provider = _FakeVisionProvider(json.dumps(VALID_REPORT))
    analyzer = ScreenshotAnalyzer(provider)
    # Wrap generate_vision to capture the user_prompt actually sent.
    captured = {}
    original = provider.generate_vision

    async def spy(system_prompt, user_prompt, image_bytes, media_type, max_tokens=1500):
        captured["user_prompt"] = user_prompt
        return await original(system_prompt, user_prompt, image_bytes, media_type, max_tokens)

    provider.generate_vision = spy  # type: ignore[method-assign]

    await analyzer.analyze(b"bytes", "image/png", symbol_hint="GBPJPY")
    assert "GBPJPY" in captured["user_prompt"]
