import numpy as np
import pandas as pd
import pytest

from app.analysis.indicators import atr, compute_indicator_snapshot, ema, macd, rsi
from app.core.constants import TradeDirection
from tests.factories import make_ranging_ohlcv, make_trending_up_ohlcv


def test_ema_converges_to_constant_series():
    series = pd.Series([10.0] * 50)
    result = ema(series, period=10)
    assert result.iloc[-1] == pytest.approx(10.0)


def test_rsi_is_100_for_strictly_increasing_series():
    series = pd.Series(np.linspace(1.0, 2.0, 50))
    result = rsi(series, period=14)
    assert result.iloc[-1] > 99.0


def test_rsi_is_0_for_strictly_decreasing_series():
    series = pd.Series(np.linspace(2.0, 1.0, 50))
    result = rsi(series, period=14)
    assert result.iloc[-1] < 1.0


def test_rsi_bounded_between_0_and_100():
    df = make_ranging_ohlcv(n=200)
    result = rsi(df["close"], period=14).dropna()
    assert (result >= 0).all()
    assert (result <= 100).all()


def test_macd_histogram_is_difference_of_lines():
    df = make_trending_up_ohlcv(n=200)
    macd_line, signal_line, hist = macd(df["close"])
    diff = (macd_line - signal_line).dropna()
    hist_clean = hist.dropna()
    pd.testing.assert_series_equal(diff, hist_clean, check_names=False)


def test_atr_is_non_negative():
    df = make_trending_up_ohlcv(n=200)
    result = atr(df, period=14).dropna()
    assert (result >= 0).all()


def test_indicator_snapshot_bullish_trend_has_buy_bias():
    df = make_trending_up_ohlcv(n=260)
    snapshot = compute_indicator_snapshot(df)
    assert snapshot.ema_trend_bias == TradeDirection.BUY
    assert snapshot.ema20 > snapshot.ema50 > snapshot.ema200


def test_indicator_snapshot_volume_spike_flag_is_boolean():
    df = make_trending_up_ohlcv(n=260)
    snapshot = compute_indicator_snapshot(df)
    assert isinstance(snapshot.is_volume_spike, bool)
    assert snapshot.relative_volume > 0
