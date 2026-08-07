from app.analysis.liquidity import (
    detect_fair_value_gaps,
    detect_liquidity_sweeps,
    detect_order_blocks,
)
from app.analysis.structure import analyze_market_structure, detect_swing_points
from app.core.constants import TradeDirection
from tests.factories import make_trend_then_reversal_ohlcv, make_trending_up_ohlcv


def test_order_blocks_align_with_bos_direction():
    df = make_trending_up_ohlcv(n=260)
    structure = analyze_market_structure(df)
    blocks = detect_order_blocks(df, structure.bos_events)
    assert all(ob.direction == TradeDirection.BUY for ob in blocks)
    assert all(ob.top >= ob.bottom for ob in blocks)


def test_order_blocks_are_a_subset_of_bos_events_or_fewer():
    df = make_trend_then_reversal_ohlcv(n=260)
    structure = analyze_market_structure(df)
    blocks = detect_order_blocks(df, structure.bos_events)
    assert len(blocks) <= len(structure.bos_events)


def test_fair_value_gaps_have_valid_ranges():
    df = make_trend_then_reversal_ohlcv(n=260)
    fvgs = detect_fair_value_gaps(df)
    assert all(gap.top >= gap.bottom for gap in fvgs)
    assert all(isinstance(gap.filled, bool) for gap in fvgs)


def test_liquidity_sweeps_have_wick_beyond_swept_level():
    df = make_trend_then_reversal_ohlcv(n=260)
    points = detect_swing_points(df)
    sweeps = detect_liquidity_sweeps(df, points)
    for sweep in sweeps:
        if sweep.direction == TradeDirection.SELL:
            assert sweep.wick_price > sweep.swept_level
        else:
            assert sweep.wick_price < sweep.swept_level
