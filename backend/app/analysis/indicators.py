"""Technical indicators computed natively on pandas Series/DataFrames.

Implemented directly against pandas/numpy (EMA, RSI, MACD, ATR, volume
metrics) rather than pulling in TA-Lib's C extension or pandas-ta: these
four formulas are simple, well-defined, and this keeps the project's only
hard dependency for indicator math being pandas/numpy — no system-level
C library to compile, no third-party package whose numpy-compat can break
underneath us. See docs/ARCHITECTURE.md for the trade-off discussion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.analysis.schemas import IndicatorSnapshot
from app.core.constants import TradeDirection


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    result = 100 - (100 / (1 + rs))
    # Where avg_loss is 0 and avg_gain > 0, RSI is 100 (pure uptrend); where
    # both are 0 (flat price), RSI is conventionally 50.
    result = result.where(avg_loss != 0, 100.0)
    result = result.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)
    return result


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, and histogram."""
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range using Wilder's smoothing."""
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    return volume.rolling(window=period, min_periods=period).mean()


VOLUME_SPIKE_THRESHOLD = 1.5  # relative volume above this = "high-volume" candle


def compute_indicator_snapshot(df: pd.DataFrame) -> IndicatorSnapshot:
    """Compute every indicator and return the latest (most recent candle) values.

    Assumes `df` has already passed through `analysis.ohlcv.validate_ohlcv`.
    """
    close = df["close"]

    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    ema200 = ema(close, 200)
    rsi14 = rsi(close, 14)
    macd_line, macd_signal, macd_hist = macd(close, 12, 26, 9)
    atr14 = atr(df, 14)
    vol_sma20 = volume_sma(df["volume"], 20)

    last_close = float(close.iloc[-1])
    last_ema20 = float(ema20.iloc[-1])
    last_ema50 = float(ema50.iloc[-1])
    last_ema200 = float(ema200.iloc[-1])
    last_rsi = float(rsi14.iloc[-1])
    last_volume = float(df["volume"].iloc[-1])
    last_vol_sma = float(vol_sma20.iloc[-1]) if not np.isnan(vol_sma20.iloc[-1]) else last_volume
    relative_volume = last_volume / last_vol_sma if last_vol_sma > 0 else 1.0

    ema_trend_bias = _ema_trend_bias(last_close, last_ema20, last_ema50, last_ema200)
    rsi_state = _rsi_state(rsi14)

    return IndicatorSnapshot(
        price=last_close,
        ema20=last_ema20,
        ema50=last_ema50,
        ema200=last_ema200,
        rsi14=last_rsi,
        macd_line=float(macd_line.iloc[-1]),
        macd_signal=float(macd_signal.iloc[-1]),
        macd_histogram=float(macd_hist.iloc[-1]),
        atr14=float(atr14.iloc[-1]),
        volume=last_volume,
        volume_sma20=last_vol_sma,
        relative_volume=relative_volume,
        is_volume_spike=relative_volume >= VOLUME_SPIKE_THRESHOLD,
        ema_trend_bias=ema_trend_bias,
        rsi_state=rsi_state,
    )


def _ema_trend_bias(price: float, ema20: float, ema50: float, ema200: float) -> TradeDirection:
    """Classic EMA stack alignment: price > EMA20 > EMA50 > EMA200 is bullish, the
    mirrored ordering is bearish, anything else is treated as neutral/mixed."""
    if price > ema20 > ema50 > ema200:
        return TradeDirection.BUY
    if price < ema20 < ema50 < ema200:
        return TradeDirection.SELL
    return TradeDirection.NEUTRAL


def _rsi_state(rsi_series: pd.Series, lookback: int = 5) -> str:
    current = float(rsi_series.iloc[-1])
    recent = rsi_series.iloc[-(lookback + 1) : -1]

    if current >= 70:
        return "overbought"
    if current <= 30:
        return "oversold"
    if len(recent) and recent.min() <= 30 and current > recent.min():
        return "recovering_from_oversold"
    if len(recent) and recent.max() >= 70 and current < recent.max():
        return "pulling_back_from_overbought"
    return "neutral"
