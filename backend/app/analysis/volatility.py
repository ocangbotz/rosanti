"""Volatility regime classification based on the ATR's percentile rank
against its own recent history — a simple, robust way to say "is this pair
unusually choppy or calm right now" without hardcoding per-symbol thresholds.
"""

from __future__ import annotations

import pandas as pd

from app.analysis.indicators import atr
from app.analysis.schemas import VolatilityInfo
from app.core.constants import VolatilityRegime

DEFAULT_LOOKBACK = 100


def _classify(percentile: float) -> VolatilityRegime:
    if percentile >= 95:
        return VolatilityRegime.EXTREME
    if percentile >= 75:
        return VolatilityRegime.HIGH
    if percentile >= 25:
        return VolatilityRegime.NORMAL
    return VolatilityRegime.LOW


def classify_volatility(
    df: pd.DataFrame, atr_period: int = 14, lookback: int = DEFAULT_LOOKBACK
) -> VolatilityInfo:
    atr_series = atr(df, atr_period).dropna()
    if atr_series.empty:
        return VolatilityInfo(atr=0.0, atr_percentile=50.0, regime=VolatilityRegime.NORMAL)

    window = atr_series.iloc[-lookback:]
    current = float(window.iloc[-1])
    percentile = float((window <= current).mean() * 100)

    return VolatilityInfo(atr=current, atr_percentile=percentile, regime=_classify(percentile))
