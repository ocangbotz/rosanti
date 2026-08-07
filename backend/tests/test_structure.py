from app.analysis.structure import analyze_market_structure, detect_swing_points
from app.core.constants import TradeDirection
from tests.factories import (
    make_ranging_ohlcv,
    make_trend_then_reversal_ohlcv,
    make_trending_up_ohlcv,
)


def test_detect_swing_points_finds_both_kinds():
    df = make_trend_then_reversal_ohlcv(n=260)
    points = detect_swing_points(df)
    kinds = {p.kind for p in points}
    assert len(points) > 0
    assert "HIGH" in {k.value for k in kinds}
    assert "LOW" in {k.value for k in kinds}


def test_swing_points_are_ordered_by_index():
    df = make_trend_then_reversal_ohlcv(n=260)
    points = detect_swing_points(df)
    indices = [p.index for p in points]
    assert indices == sorted(indices)


def test_uptrend_produces_bullish_structure_and_bos():
    df = make_trending_up_ohlcv(n=260)
    result = analyze_market_structure(df)
    assert result.trend == TradeDirection.BUY
    assert len(result.bos_events) >= 1
    assert all(e.direction == TradeDirection.BUY for e in result.bos_events)


def test_trend_then_reversal_produces_a_choch():
    df = make_trend_then_reversal_ohlcv(n=260)
    result = analyze_market_structure(df)
    # A clean up-move followed by a clean down-move must, at minimum,
    # register a CHOCH marking the switch from bullish to bearish structure.
    assert len(result.choch_events) >= 1
    assert result.choch_events[0].direction == TradeDirection.SELL


def test_last_bos_and_choch_reflect_most_recent_event():
    df = make_trend_then_reversal_ohlcv(n=260)
    result = analyze_market_structure(df)
    if result.bos_events:
        assert result.last_bos == result.bos_events[-1]
    if result.choch_events:
        assert result.last_choch == result.choch_events[-1]


def test_ranging_market_may_stay_neutral_or_flip_repeatedly():
    df = make_ranging_ohlcv(n=260)
    result = analyze_market_structure(df)
    # No strong assertion on direction (ranging markets are noisy by
    # construction) — the important invariant is that it doesn't crash and
    # produces internally consistent, chronologically ordered events.
    bos_times = [e.time for e in result.bos_events]
    choch_times = [e.time for e in result.choch_events]
    assert bos_times == sorted(bos_times)
    assert choch_times == sorted(choch_times)
