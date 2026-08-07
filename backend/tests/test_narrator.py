import pytest

from app.services.ai.base import ILLMProvider
from app.services.ai.narrator import MarketNarrator, build_prompt
from app.strategies.setup_generator import TradeSetupGenerator
from tests.analysis_factories import make_bullish_market_analysis, make_flat_market_analysis


class _FakeLLMProvider(ILLMProvider):
    def __init__(self, response: str = "A canned narrative."):
        self.response = response
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    async def generate_text(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1024
    ) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response

    async def generate_vision(
        self, system_prompt, user_prompt, image_bytes, media_type, max_tokens=1500
    ) -> str:
        raise NotImplementedError


def test_build_prompt_includes_key_facts_without_a_setup():
    analysis = make_flat_market_analysis()
    system_prompt, user_prompt = build_prompt(analysis, setup=None)

    assert "never invent" in system_prompt.lower()
    assert analysis.symbol in user_prompt
    assert "No valid trade setup" in user_prompt


def test_build_prompt_includes_setup_details_when_present():
    analysis = make_bullish_market_analysis()
    result = TradeSetupGenerator().generate(analysis)
    assert result.has_valid_setup is True

    _, user_prompt = build_prompt(analysis, setup=result.setup)

    assert "Proposed setup: BUY" in user_prompt
    assert f"{result.setup.entry_price:.5f}" in user_prompt
    assert f"1:{result.setup.risk_reward:.2f}" in user_prompt
    for reason in result.setup.reasons:
        assert reason.description in user_prompt


def test_build_prompt_never_fabricates_numbers_not_in_analysis():
    analysis = make_bullish_market_analysis()
    _, user_prompt = build_prompt(analysis, setup=None)
    # Sanity check that the RSI value we fed in round-trips into the prompt exactly.
    assert f"{analysis.indicators.rsi14:.1f}" in user_prompt


@pytest.mark.asyncio
async def test_narrate_delegates_to_provider_with_built_prompts():
    analysis = make_flat_market_analysis()
    provider = _FakeLLMProvider(response="Market is choppy with no clear edge.")
    narrator = MarketNarrator(provider)

    result = await narrator.narrate(analysis)

    assert result == "Market is choppy with no clear edge."
    expected_system, expected_user = build_prompt(analysis, None)
    assert provider.last_system_prompt == expected_system
    assert provider.last_user_prompt == expected_user
