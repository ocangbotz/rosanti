"""Turns a computed `MarketAnalysis` (+ optional `TradeSetupProposal`) into a
natural-language paragraph a trader can read at a glance.

This is deliberately a *narration* layer, not a decision-making one: the
LLM is given only the already-computed facts and is instructed to describe
them, never to invent a price, indicator value, or structural event that
isn't explicitly present in the prompt. All the actual analysis happened
upstream in `app/analysis/` and `app/strategies/` — see docs/ARCHITECTURE.md
§1 for why this separation is the whole point of the product.
"""

from __future__ import annotations

from app.analysis.schemas import MarketAnalysis
from app.services.ai.base import ILLMProvider
from app.strategies.schemas import TradeSetupProposal

SYSTEM_PROMPT = """You are a professional trading analyst assistant embedded in a trading \
platform. You will be given a set of already-computed market facts \
(indicators, market structure, liquidity, levels, session, volatility) and \
optionally a proposed trade setup with its confidence score and reasons.

Your job is ONLY to explain these facts in clear, concise natural language \
(3-6 sentences) — you are a narrator, not an analyst deciding the trade. Rules:
1. Never invent a price, indicator value, or event that is not explicitly \
given to you in the facts below.
2. Never give direct financial advice ("you should buy/sell"); instead, \
describe what the data shows and why it is significant.
3. If a trade setup is provided, explain why it is valid by referencing its \
listed reasons, and state the risk/reward plainly.
4. If no valid setup is provided, explain in one or two sentences why the \
market does not currently show enough confluence for a trade idea.
5. Write in a professional, measured tone — no hype, no emojis, no \
exclamation marks."""


def _format_analysis_facts(analysis: MarketAnalysis) -> str:
    ind = analysis.indicators
    structure = analysis.structure
    lines = [
        f"Symbol: {analysis.symbol} ({analysis.timeframe.value})",
        f"Current price: {ind.price:.5f}",
        f"EMA20/50/200: {ind.ema20:.5f} / {ind.ema50:.5f} / {ind.ema200:.5f} "
        f"(trend alignment: {ind.ema_trend_bias.value})",
        f"RSI(14): {ind.rsi14:.1f} ({ind.rsi_state.replace('_', ' ')})",
        f"MACD line/signal/histogram: {ind.macd_line:.5f} / {ind.macd_signal:.5f} / "
        f"{ind.macd_histogram:.5f}",
        f"ATR(14): {ind.atr14:.5f}",
        f"Volume vs 20-period average: {ind.relative_volume:.1f}x"
        + (" (volume spike)" if ind.is_volume_spike else ""),
        f"Market structure trend: {structure.trend.value}",
    ]
    if structure.last_bos:
        lines.append(
            f"Last Break of Structure (BOS): {structure.last_bos.direction.value} at "
            f"{structure.last_bos.price:.5f}"
        )
    if structure.last_choch:
        lines.append(
            f"Last Change of Character (CHOCH): {structure.last_choch.direction.value} at "
            f"{structure.last_choch.price:.5f}"
        )

    if analysis.liquidity.sweeps:
        latest_sweep = analysis.liquidity.sweeps[-1]
        lines.append(
            f"Most recent liquidity sweep: {latest_sweep.direction.value} bias, swept level "
            f"{latest_sweep.swept_level:.5f}"
        )
    unmitigated_obs = [ob for ob in analysis.liquidity.order_blocks if not ob.mitigated]
    if unmitigated_obs:
        ob = unmitigated_obs[-1]
        lines.append(
            f"Nearest unmitigated order block: {ob.direction.value} zone "
            f"{ob.bottom:.5f}-{ob.top:.5f}"
        )
    unfilled_fvgs = [fvg for fvg in analysis.liquidity.fair_value_gaps if not fvg.filled]
    if unfilled_fvgs:
        fvg = unfilled_fvgs[-1]
        lines.append(
            f"Nearest unfilled fair value gap: {fvg.direction.value} gap "
            f"{fvg.bottom:.5f}-{fvg.top:.5f}"
        )

    lines.append(
        f"Session: {analysis.session.session.value} (overlap: {analysis.session.is_overlap})"
    )
    lines.append(
        f"Volatility regime: {analysis.volatility.regime.value} "
        f"(ATR percentile {analysis.volatility.atr_percentile:.0f})"
    )
    return "\n".join(f"- {line}" for line in lines)


def _format_setup_facts(setup: TradeSetupProposal | None) -> str:
    if setup is None:
        return (
            "No valid trade setup was generated for this analysis "
            "(confidence too low or conflicting signals)."
        )

    reason_lines = "\n".join(f"  - {r.description} (weight {r.weight:.0f})" for r in setup.reasons)
    return (
        f"Proposed setup: {setup.direction.value} {setup.symbol}\n"
        f"- Entry: {setup.entry_price:.5f}\n"
        f"- Stop loss: {setup.stop_loss:.5f}\n"
        f"- Take profit: {setup.take_profit:.5f}\n"
        f"- Risk/reward: 1:{setup.risk_reward:.2f}\n"
        f"- Confidence score: {setup.confidence_score:.0f}%\n"
        f"- Reasons:\n{reason_lines}"
    )


def build_prompt(
    analysis: MarketAnalysis, setup: TradeSetupProposal | None = None
) -> tuple[str, str]:
    """Builds (system_prompt, user_prompt). Exposed as a pure function so it
    can be unit-tested without making a network call."""
    user_prompt = (
        "Here are the computed market facts:\n\n"
        f"{_format_analysis_facts(analysis)}\n\n"
        f"{_format_setup_facts(setup)}\n\n"
        "Write the natural-language summary now, following the rules above."
    )
    return SYSTEM_PROMPT, user_prompt


class MarketNarrator:
    def __init__(self, provider: ILLMProvider):
        self._provider = provider

    async def narrate(
        self, analysis: MarketAnalysis, setup: TradeSetupProposal | None = None
    ) -> str:
        system_prompt, user_prompt = build_prompt(analysis, setup)
        return await self._provider.generate_text(system_prompt, user_prompt, max_tokens=512)
