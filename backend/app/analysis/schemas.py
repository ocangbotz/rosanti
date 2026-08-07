"""Typed result objects produced by the analysis engine.

These are plain data containers (Pydantic models, but no I/O) — the
contract between `analysis/` (pure computation) and everything downstream
(`strategies/`, the API layer, `TradeSetup.structure_snapshot`).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.core.constants import Timeframe, TradeDirection, TradingSession, VolatilityRegime


class _Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# Indicators
# --------------------------------------------------------------------------


class IndicatorSnapshot(_Model):
    price: float
    ema20: float
    ema50: float
    ema200: float
    rsi14: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    atr14: float
    volume: float
    volume_sma20: float
    relative_volume: float
    is_volume_spike: bool
    ema_trend_bias: TradeDirection  # price/EMA alignment: BUY, SELL, or NEUTRAL
    rsi_state: str  # "overbought" | "oversold" | "neutral" | "recovering_from_oversold" | ...


# --------------------------------------------------------------------------
# Market structure (swings / trend / BOS / CHOCH)
# --------------------------------------------------------------------------


class SwingKind(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


class SwingPoint(_Model):
    index: int
    time: datetime
    price: float
    kind: SwingKind


class StructureEvent(_Model):
    """A Break of Structure or Change of Character event."""

    time: datetime
    price: float
    direction: TradeDirection
    reference_swing: SwingPoint


class StructureAnalysis(_Model):
    swing_points: list[SwingPoint]
    trend: TradeDirection  # BUY = bullish structure, SELL = bearish, NEUTRAL = ranging
    bos_events: list[StructureEvent]
    choch_events: list[StructureEvent]
    last_bos: StructureEvent | None = None
    last_choch: StructureEvent | None = None


# --------------------------------------------------------------------------
# Liquidity: sweeps, order blocks, fair value gaps
# --------------------------------------------------------------------------


class LiquiditySweep(_Model):
    time: datetime
    wick_price: float
    swept_level: float
    direction: TradeDirection  # direction of the anticipated reversal


class OrderBlock(_Model):
    time: datetime
    top: float
    bottom: float
    direction: TradeDirection  # BUY = demand/bullish OB, SELL = supply/bearish OB
    mitigated: bool


class FairValueGap(_Model):
    time: datetime
    top: float
    bottom: float
    direction: TradeDirection
    filled: bool

    @property
    def midpoint(self) -> float:
        return (self.top + self.bottom) / 2


class LiquidityAnalysis(_Model):
    sweeps: list[LiquiditySweep]
    order_blocks: list[OrderBlock]
    fair_value_gaps: list[FairValueGap]


# --------------------------------------------------------------------------
# Levels: support/resistance, supply/demand zones
# --------------------------------------------------------------------------


class SRLevel(_Model):
    price: float
    kind: str  # "SUPPORT" | "RESISTANCE"
    touches: int
    last_touch_time: datetime


class SupplyDemandZone(_Model):
    top: float
    bottom: float
    kind: str  # "SUPPLY" | "DEMAND"
    formed_at: datetime
    tested: bool


class LevelsAnalysis(_Model):
    support_resistance: list[SRLevel]
    supply_demand_zones: list[SupplyDemandZone]


# --------------------------------------------------------------------------
# Session / volatility
# --------------------------------------------------------------------------


class SessionInfo(_Model):
    session: TradingSession
    is_overlap: bool
    as_of: datetime


class VolatilityInfo(_Model):
    atr: float
    atr_percentile: float
    regime: VolatilityRegime


# --------------------------------------------------------------------------
# Aggregate result
# --------------------------------------------------------------------------


class MarketAnalysis(_Model):
    symbol: str
    timeframe: Timeframe
    generated_at: datetime
    candles_analyzed: int
    indicators: IndicatorSnapshot
    structure: StructureAnalysis
    liquidity: LiquidityAnalysis
    levels: LevelsAnalysis
    session: SessionInfo
    volatility: VolatilityInfo
