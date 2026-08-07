"""Confluence scoring engine.

This is the heart of "never blindly generate signals": every point of
confidence is attached to a named, human-readable `Reason` derived from the
deterministic `MarketAnalysis` computed in `app/analysis/`. Nothing here
guesses — it only tallies concrete, already-computed facts.

Scoring is direction-specific: BUY and SELL each accumulate their own score
from the same analysis, and the caller (see `setup_generator.py`) picks
whichever direction clears the confidence threshold — or neither, if the
market doesn't show enough alignment either way.
"""

from __future__ import annotations

from app.analysis.schemas import MarketAnalysis
from app.core.constants import TradeDirection
from app.schemas.setup import Reason
from app.strategies.schemas import ConfluenceResult

# Point weights per confluence factor. Chosen so that a "textbook" setup
# (structure + trend + liquidity + volume all agreeing) lands in the
# high-80s/90s, while a single factor alone never crosses the default
# MIN_CONFIDENCE_THRESHOLD on its own.
WEIGHT_BOS = 20.0
WEIGHT_CHOCH = 18.0
WEIGHT_EMA_TREND = 15.0
WEIGHT_LIQUIDITY_SWEEP = 15.0
WEIGHT_ORDER_BLOCK = 10.0
WEIGHT_FVG = 6.0
WEIGHT_VOLUME_SPIKE = 8.0
WEIGHT_RSI_CONDITION = 8.0
WEIGHT_MACD_MOMENTUM = 8.0
WEIGHT_SUPPLY_DEMAND_ZONE = 8.0

MAX_CONFIDENCE = 100.0

# How many of the most recent candles a liquidity sweep / order block / FVG
# must have formed within to still be considered "live" confluence rather
# than stale history.
RECENCY_WINDOW_CANDLES = 15

# How close (in ATR multiples) price must be to a zone for it to count as
# "current" confluence rather than a level far away from the action.
ZONE_PROXIMITY_ATR_MULT = 1.5


def _recent(event_time, analysis: MarketAnalysis, window: int = RECENCY_WINDOW_CANDLES) -> bool:
    """True if `event_time` falls within the last `window` candles' worth of
    the analyzed timeframe, relative to `generated_at`. Works for both plain
    `datetime` and `pandas.Timestamp` inputs — both support subtraction into
    a duration with `.total_seconds()`, so no type-specific conversion is
    needed (and none is safe to assume either way after Pydantic validation)."""
    delta_minutes = (analysis.generated_at - event_time).total_seconds() / 60
    return 0 <= delta_minutes <= analysis.timeframe.minutes * window


class ConfluenceScorer:
    """Scores a `MarketAnalysis` for both BUY and SELL, with reasons."""

    def score(self, analysis: MarketAnalysis) -> tuple[ConfluenceResult, ConfluenceResult]:
        buy_reasons = self._score_direction(analysis, TradeDirection.BUY)
        sell_reasons = self._score_direction(analysis, TradeDirection.SELL)

        buy_score = min(sum(r.weight for r in buy_reasons), MAX_CONFIDENCE)
        sell_score = min(sum(r.weight for r in sell_reasons), MAX_CONFIDENCE)

        return (
            ConfluenceResult(
                direction=TradeDirection.BUY, confidence=buy_score, reasons=buy_reasons
            ),
            ConfluenceResult(
                direction=TradeDirection.SELL, confidence=sell_score, reasons=sell_reasons
            ),
        )

    def _score_direction(self, analysis: MarketAnalysis, direction: TradeDirection) -> list[Reason]:
        reasons: list[Reason] = []
        verb = "Bullish" if direction == TradeDirection.BUY else "Bearish"

        structure = analysis.structure
        if structure.last_bos and structure.last_bos.direction == direction:
            reasons.append(
                Reason(
                    factor="structure_bos",
                    description=(
                        f"{verb} Break of Structure (BOS) confirmed at "
                        f"{structure.last_bos.price:.5f}."
                    ),
                    direction=direction,
                    weight=WEIGHT_BOS,
                )
            )
        if structure.last_choch and structure.last_choch.direction == direction:
            reasons.append(
                Reason(
                    factor="structure_choch",
                    description=(
                        "Change of Character (CHOCH) signals a shift toward "
                        f"{direction.value} bias."
                    ),
                    direction=direction,
                    weight=WEIGHT_CHOCH,
                )
            )

        indicators = analysis.indicators
        if indicators.ema_trend_bias == direction:
            reasons.append(
                Reason(
                    factor="ema_trend_alignment",
                    description="Price and EMA20/50/200 stack are aligned with the "
                    f"{direction.value.lower()} trend.",
                    direction=direction,
                    weight=WEIGHT_EMA_TREND,
                )
            )

        if direction == TradeDirection.BUY and indicators.rsi_state == "recovering_from_oversold":
            reasons.append(
                Reason(
                    factor="rsi_recovery",
                    description="RSI is recovering from oversold territory, favoring buyers.",
                    direction=direction,
                    weight=WEIGHT_RSI_CONDITION,
                )
            )
        if (
            direction == TradeDirection.SELL
            and indicators.rsi_state == "pulling_back_from_overbought"
        ):
            reasons.append(
                Reason(
                    factor="rsi_pullback",
                    description="RSI is pulling back from overbought territory, favoring sellers.",
                    direction=direction,
                    weight=WEIGHT_RSI_CONDITION,
                )
            )

        macd_bullish = (
            indicators.macd_line > indicators.macd_signal and indicators.macd_histogram > 0
        )
        macd_bearish = (
            indicators.macd_line < indicators.macd_signal and indicators.macd_histogram < 0
        )
        if (direction == TradeDirection.BUY and macd_bullish) or (
            direction == TradeDirection.SELL and macd_bearish
        ):
            reasons.append(
                Reason(
                    factor="macd_momentum",
                    description=f"MACD momentum supports the {direction.value.lower()} case "
                    "(line/signal cross with confirming histogram).",
                    direction=direction,
                    weight=WEIGHT_MACD_MOMENTUM,
                )
            )

        for sweep in reversed(analysis.liquidity.sweeps):
            if sweep.direction == direction and _recent(sweep.time, analysis):
                reasons.append(
                    Reason(
                        factor="liquidity_sweep",
                        description=(
                            f"Liquidity sweep detected at {sweep.swept_level:.5f} — stops were "
                            "run before price reversed in this direction."
                        ),
                        direction=direction,
                        weight=WEIGHT_LIQUIDITY_SWEEP,
                    )
                )
                break

        atr = max(analysis.volatility.atr, 1e-9)
        price = indicators.price
        for ob in reversed(analysis.liquidity.order_blocks):
            if ob.direction != direction or ob.mitigated:
                continue
            distance = min(abs(price - ob.top), abs(price - ob.bottom))
            if distance <= atr * ZONE_PROXIMITY_ATR_MULT:
                reasons.append(
                    Reason(
                        factor="order_block_confluence",
                        description=(
                            f"Price is trading near an unmitigated {direction.value.lower()} "
                            f"order block ({ob.bottom:.5f}-{ob.top:.5f})."
                        ),
                        direction=direction,
                        weight=WEIGHT_ORDER_BLOCK,
                    )
                )
                break

        for fvg in reversed(analysis.liquidity.fair_value_gaps):
            if fvg.direction != direction or fvg.filled:
                continue
            distance = min(abs(price - fvg.top), abs(price - fvg.bottom))
            if distance <= atr * ZONE_PROXIMITY_ATR_MULT:
                reasons.append(
                    Reason(
                        factor="fair_value_gap",
                        description=(
                            f"An unfilled {direction.value.lower()} fair value gap sits near "
                            f"current price ({fvg.bottom:.5f}-{fvg.top:.5f})."
                        ),
                        direction=direction,
                        weight=WEIGHT_FVG,
                    )
                )
                break

        zone_kind = "DEMAND" if direction == TradeDirection.BUY else "SUPPLY"
        for zone in reversed(analysis.levels.supply_demand_zones):
            if zone.kind != zone_kind:
                continue
            distance = min(abs(price - zone.top), abs(price - zone.bottom))
            if distance <= atr * ZONE_PROXIMITY_ATR_MULT:
                reasons.append(
                    Reason(
                        factor="supply_demand_zone",
                        description=f"Price is reacting to a {zone_kind.lower()} zone "
                        f"({zone.bottom:.5f}-{zone.top:.5f}).",
                        direction=direction,
                        weight=WEIGHT_SUPPLY_DEMAND_ZONE,
                    )
                )
                break

        if indicators.is_volume_spike:
            candle_is_bullish = indicators.price >= indicators.ema20 or macd_bullish
            aligned = (direction == TradeDirection.BUY and candle_is_bullish) or (
                direction == TradeDirection.SELL and not candle_is_bullish
            )
            if aligned:
                reasons.append(
                    Reason(
                        factor="volume_spike",
                        description="High-volume breakout confirms conviction behind the move "
                        f"(relative volume {indicators.relative_volume:.1f}x average).",
                        direction=direction,
                        weight=WEIGHT_VOLUME_SPIKE,
                    )
                )

        return reasons
