"""Synthetic OHLCV generators used across the test suite.

Real market data isn't available in CI, and structure/liquidity detection
needs *shaped* price action (clear swings, a trend, a reversal) rather than
pure random noise to exercise meaningfully — so these build deterministic,
seeded synthetic candles with a known shape instead of mocking broker calls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd


def make_ohlcv(
    n: int = 260,
    start_price: float = 1.1000,
    start_time: datetime | None = None,
    timeframe_minutes: int = 60,
    seed: int = 7,
    trend_segments: list[tuple[int, float]] | None = None,
    noise_scale: float = 0.0006,
    base_volume: float = 1000.0,
) -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame with a piecewise-linear drift.

    `trend_segments` is a list of (length, drift_per_candle) pairs — e.g.
    `[(120, 0.0009), (140, -0.0011)]` produces a clean uptrend followed by a
    clean downtrend, which is what structure/BOS/CHOCH detection needs to
    have something real to find.
    """
    rng = np.random.default_rng(seed)
    start_time = start_time or datetime(2024, 1, 1, tzinfo=UTC)

    if trend_segments is None:
        trend_segments = [(n, 0.0004)]

    drifts: list[float] = []
    for length, drift in trend_segments:
        drifts.extend([drift] * length)
    while len(drifts) < n:
        drifts.append(drifts[-1] if drifts else 0.0)
    drifts = drifts[:n]

    closes = [start_price]
    for i in range(1, n):
        noise = rng.normal(0, noise_scale)
        closes.append(closes[-1] + drifts[i] + noise)
    closes = np.array(closes)

    opens = np.empty(n)
    opens[0] = start_price
    opens[1:] = closes[:-1]

    wick_noise = np.abs(rng.normal(0, noise_scale * 1.2, size=n))
    highs = np.maximum(opens, closes) + wick_noise
    lows = np.minimum(opens, closes) - wick_noise

    volumes = base_volume + rng.normal(0, base_volume * 0.15, size=n)
    spike_idxs = rng.choice(n, size=max(n // 25, 1), replace=False)
    volumes[spike_idxs] *= rng.uniform(1.8, 2.8, size=len(spike_idxs))
    volumes = np.abs(volumes)

    times = [start_time + timedelta(minutes=timeframe_minutes * i) for i in range(n)]

    return pd.DataFrame(
        {
            "time": times,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


def make_trending_up_ohlcv(n: int = 260, seed: int = 7) -> pd.DataFrame:
    return make_ohlcv(n=n, trend_segments=[(n, 0.0009)], seed=seed)


def make_trend_then_reversal_ohlcv(n: int = 260, seed: int = 11) -> pd.DataFrame:
    up_len = n // 2
    down_len = n - up_len
    return make_ohlcv(n=n, trend_segments=[(up_len, 0.0011), (down_len, -0.0013)], seed=seed)


def make_ranging_ohlcv(n: int = 260, seed: int = 3) -> pd.DataFrame:
    return make_ohlcv(n=n, trend_segments=[(n, 0.0)], noise_scale=0.0009, seed=seed)
