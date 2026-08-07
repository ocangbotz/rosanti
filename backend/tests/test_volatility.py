from app.analysis.volatility import classify_volatility
from app.core.constants import VolatilityRegime
from tests.factories import make_ohlcv, make_trending_up_ohlcv


def test_volatility_percentile_is_between_0_and_100():
    df = make_trending_up_ohlcv(n=200)
    info = classify_volatility(df)
    assert 0 <= info.atr_percentile <= 100
    assert info.atr >= 0


def test_last_candle_of_lookback_window_hits_highest_percentile():
    # A sudden volatility expansion in the final candles should push the
    # latest ATR reading toward the top of its own percentile window.
    df = make_ohlcv(n=200, trend_segments=[(180, 0.0002), (20, 0.006)], noise_scale=0.0003, seed=42)
    info = classify_volatility(df, lookback=100)
    assert info.regime in {VolatilityRegime.HIGH, VolatilityRegime.EXTREME}
