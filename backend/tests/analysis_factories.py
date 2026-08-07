"""Hand-built `MarketAnalysis` fixtures for deterministic strategy-layer
tests, where we need exact control over which confluence factors are
present rather than whatever a synthetic OHLCV run happens to produce.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.analysis.schemas import (
    FairValueGap,
    IndicatorSnapshot,
    LevelsAnalysis,
    LiquidityAnalysis,
    LiquiditySweep,
    MarketAnalysis,
    OrderBlock,
    SessionInfo,
    SRLevel,
    StructureAnalysis,
    StructureEvent,
    SupplyDemandZone,
    SwingKind,
    SwingPoint,
    VolatilityInfo,
)
from app.core.constants import Timeframe, TradeDirection, TradingSession, VolatilityRegime

NOW = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)


def make_indicator_snapshot(
    *,
    price: float = 1.1050,
    ema20: float = 1.1040,
    ema50: float = 1.1020,
    ema200: float = 1.1000,
    rsi14: float = 55.0,
    rsi_state: str = "neutral",
    macd_line: float = 0.0008,
    macd_signal: float = 0.0004,
    macd_histogram: float = 0.0004,
    atr14: float = 0.0015,
    is_volume_spike: bool = False,
    relative_volume: float = 1.0,
    ema_trend_bias: TradeDirection = TradeDirection.BUY,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        price=price,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi14=rsi14,
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        atr14=atr14,
        volume=1200.0,
        volume_sma20=1000.0,
        relative_volume=relative_volume,
        is_volume_spike=is_volume_spike,
        ema_trend_bias=ema_trend_bias,
        rsi_state=rsi_state,
    )


def make_swing(index: int, price: float, kind: SwingKind, minutes_ago: int = 120) -> SwingPoint:
    return SwingPoint(
        index=index,
        time=NOW.fromtimestamp(NOW.timestamp() - minutes_ago * 60),
        price=price,
        kind=kind,
    )


def make_bullish_market_analysis(
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    *,
    with_liquidity_sweep: bool = True,
    with_order_block: bool = True,
    with_volume_spike: bool = True,
) -> MarketAnalysis:
    """A market analysis where every confluence factor points BUY."""
    swing_low = make_swing(100, 1.1000, SwingKind.LOW, minutes_ago=180)
    swing_high = make_swing(120, 1.1080, SwingKind.HIGH, minutes_ago=90)

    bos = StructureEvent(
        time=NOW, price=1.1085, direction=TradeDirection.BUY, reference_swing=swing_high
    )

    structure = StructureAnalysis(
        swing_points=[swing_low, swing_high],
        trend=TradeDirection.BUY,
        bos_events=[bos],
        choch_events=[],
        last_bos=bos,
        last_choch=None,
    )

    sweeps = (
        [
            LiquiditySweep(
                time=NOW, wick_price=1.0995, swept_level=1.1000, direction=TradeDirection.BUY
            )
        ]
        if with_liquidity_sweep
        else []
    )
    order_blocks = (
        [
            OrderBlock(
                time=NOW, top=1.1045, bottom=1.1030, direction=TradeDirection.BUY, mitigated=False
            )
        ]
        if with_order_block
        else []
    )
    liquidity = LiquidityAnalysis(
        sweeps=sweeps,
        order_blocks=order_blocks,
        fair_value_gaps=[
            FairValueGap(
                time=NOW, top=1.1055, bottom=1.1048, direction=TradeDirection.BUY, filled=False
            )
        ],
    )

    levels = LevelsAnalysis(
        support_resistance=[
            SRLevel(price=1.1000, kind="SUPPORT", touches=2, last_touch_time=NOW),
            SRLevel(price=1.1150, kind="RESISTANCE", touches=2, last_touch_time=NOW),
        ],
        supply_demand_zones=[
            SupplyDemandZone(top=1.1045, bottom=1.1030, kind="DEMAND", formed_at=NOW, tested=False),
        ],
    )

    indicators = make_indicator_snapshot(
        rsi_state="recovering_from_oversold" if with_volume_spike else "neutral",
        is_volume_spike=with_volume_spike,
        relative_volume=2.1 if with_volume_spike else 1.0,
        ema_trend_bias=TradeDirection.BUY,
    )

    return MarketAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        generated_at=NOW,
        candles_analyzed=260,
        indicators=indicators,
        structure=structure,
        liquidity=liquidity,
        levels=levels,
        session=SessionInfo(session=TradingSession.LONDON, is_overlap=False, as_of=NOW),
        volatility=VolatilityInfo(atr=0.0015, atr_percentile=50.0, regime=VolatilityRegime.NORMAL),
    )


def make_flat_market_analysis(
    symbol: str = "EURUSD", timeframe: Timeframe = Timeframe.H1
) -> MarketAnalysis:
    """A market analysis with no meaningful confluence in either direction —
    used to test that the generator correctly refuses to propose a trade."""
    indicators = make_indicator_snapshot(
        rsi14=50.0,
        rsi_state="neutral",
        macd_line=0.0,
        macd_signal=0.0,
        macd_histogram=0.0,
        ema_trend_bias=TradeDirection.NEUTRAL,
        is_volume_spike=False,
    )
    structure = StructureAnalysis(
        swing_points=[],
        trend=TradeDirection.NEUTRAL,
        bos_events=[],
        choch_events=[],
        last_bos=None,
        last_choch=None,
    )
    liquidity = LiquidityAnalysis(sweeps=[], order_blocks=[], fair_value_gaps=[])
    levels = LevelsAnalysis(support_resistance=[], supply_demand_zones=[])

    return MarketAnalysis(
        symbol=symbol,
        timeframe=timeframe,
        generated_at=NOW,
        candles_analyzed=260,
        indicators=indicators,
        structure=structure,
        liquidity=liquidity,
        levels=levels,
        session=SessionInfo(session=TradingSession.OFF_HOURS, is_overlap=False, as_of=NOW),
        volatility=VolatilityInfo(atr=0.0010, atr_percentile=50.0, regime=VolatilityRegime.NORMAL),
    )
